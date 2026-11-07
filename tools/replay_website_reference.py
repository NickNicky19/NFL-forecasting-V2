#!/usr/bin/env python3
"""Replay retained Week7 website points; never acquire or infer a Week8 outcome."""
import collections, csv, gzip, hashlib, json, math, sys, time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nfl_v2 import hgb_control as source
from nfl_v2.identity import unique_gsis_bridge
from nfl_v2.scoring import point_metrics


def epoch(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def select_packets(packets, games):
    chosen = {}
    for name, packet in packets:
        capture = epoch(packet['captured_at'])
        if epoch(packet['forecast_generated_at']) > capture:
            raise ValueError('generation after capture')
        seen = set()
        for row in packet['rows']:
            if (row['season'], row['week']) != (2026, 7):
                raise ValueError('outside registered Week7 panel')
            game = games.get(str(row['game_id']))
            if game is None or epoch(row['kickoff']) != game['kickoff']:
                raise ValueError('reference schedule binding')
            key = (str(row['player_id']), str(row['game_id']), row['category'])
            if key in seen:
                raise ValueError('duplicate capture row')
            seen.add(key)
        for game_id, game in games.items():
            if capture > game['kickoff'] - 90 * 60:
                continue
            if not any(str(r['game_id']) == game_id for r in packet['rows']):
                continue
            old = chosen.get(game_id)
            if old is None or capture > old[0] or (capture == old[0] and name < old[1]):
                chosen[game_id] = (capture, name, packet)
    return chosen


def main():
    start = time.monotonic()
    public = ROOT / 'reports/continuation-20261030b/website-reference-replay-v1'
    private = Path(sys.argv[1])
    evidence = Path(sys.argv[2])
    cache = Path(sys.argv[3])
    public.mkdir(exist_ok=True)
    private.mkdir(exist_ok=True)
    admission_path = public.parent / 'WEBSITE_REFERENCE_RECOVERY_ADMISSION.json'
    admission = json.loads(admission_path.read_text())
    source_protocol = json.loads((ROOT / 'reports/continuation-20261030/distribution-wave-v2/FROZEN_PROTOCOL.json').read_text())
    rows, games, _ = source.load_source(cache, source_protocol)
    rows = [r for r in rows if (r['season'], r['week']) == (2026, 7)]
    labels = {(r['game_id'], r['player_id']): r for r in rows}
    by_espn = {g['espn']: g for g in games.values() if (g['season'], g['week']) == (2026, 7)}
    with gzip.open(cache / 'roster-week8-identity-2026.csv.gz', 'rt') as f:
        bridge = unique_gsis_bridge([(r['sleeper_id'], r['gsis_id']) for r in csv.DictReader(f)
                                    if r['season'] == '2026' and int(r['week']) <= 7 and r['sleeper_id'] and r['gsis_id']],
                                   source_id='FROZEN2026ROSTER_EXACT_IDS_WEEK_LE7')
    packets = []
    decoded = 0
    for spec in admission['source_files']:
        body = (evidence / Path(spec['path']).name).read_bytes()
        if len(body) != spec['bytes'] or hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest() != spec['git_blob_sha1']:
            raise ValueError('source blob changed')
        raw = gzip.decompress(body)
        decoded += len(raw)
        if len(raw) > admission['budget']['max_decoded_bytes_per_file'] or decoded > admission['budget']['max_decompressed_bytes']:
            raise ValueError('registered decode budget')
        envelope = json.loads(raw)
        if hashlib.sha256(source.canonical(envelope['payload'])).hexdigest() != envelope['payload_sha256']:
            raise ValueError('payload digest')
        packets.append((spec['path'], envelope['payload']))
    selected = select_packets(packets, by_espn)
    records, exclusions = [], collections.Counter()
    selected_meta = []
    for espn, (capture, name, packet) in selected.items():
        game = by_espn[espn]
        selected_meta.append(dict(game_id=game['game_id'], capture_utc=packet['captured_at'],
                                  forecast_generated_at=packet['forecast_generated_at'], public_source_path=name,
                                  recorded_horizon_seconds=game['kickoff']-capture,
                                  engine_sha256=packet['engine_sha256'], evidence_label=packet['evidence_label']))
        for r in packet['rows']:
            if str(r['game_id']) != espn:
                continue
            target = r['category']
            gsis = bridge.get(str(r['player_id']))
            actual_row = labels.get((game['game_id'], gsis))
            status = ('TARGET_NOT_COMPARABLE' if target not in source.TARGETS else
                      'NO_EXACT_ID' if gsis is None else 'NO_STAT_ROW_OR_APPEARANCE_UNKNOWN' if actual_row is None or not actual_row['played'] else
                      'POSITION_MISMATCH' if actual_row['position'] != r['position'] else 'SUPPORTED')
            for product, value in [('website_point', r.get('adjusted_projection')), ('provider_point', r.get('raw_projection'))]:
                reason = status
                if reason == 'SUPPORTED' and (not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value)):
                    reason = 'MISSING_EXPLICIT_POINT_OR_PROBABILITY'
                actual = actual_row['values'][target] if reason == 'SUPPORTED' else None
                if reason == 'SUPPORTED' and actual is None:
                    reason = 'MISSING_ACTUAL'
                if reason != 'SUPPORTED':
                    exclusions[(target, product, reason)] += 1
                position = actual_row['position'] if actual_row else r['position']
                population = ('primary' if position in source_protocol['source_role_contract']['primary'].get(target, []) else 'extended')
                records.append(dict(game_id=game['game_id'], player_id=gsis, target=target,
                                    position=position, population=population, product_id=product,
                                    prediction=value if isinstance(value, (int,float)) else None,
                                    actual=actual, status=reason, recorded_capture_utc=packet['captured_at'],
                                    source_path=name, source_timestamps_verified=r['source_timestamps_verified']))
    with gzip.open(private / 'RETAINED_REFERENCE_ROWS.json.gz', 'wt') as f:
        json.dump(records, f, separators=(',', ':'), allow_nan=False)
    # Existing candidates are frozen before this replay. No new fit or selector.
    leaders = {r['target']: r for r in json.loads((ROOT/'reports/continuation-20261030/TOP5_BY_CATEGORY_PRODUCT.json').read_text())
               if r['ranking_product'] == 'display_point' and r['rank'] == 1 and r['target'] != 'nick-chart-ppr-v1'}
    candidates = {}
    def admit(r, family):
        if str(r.get('week')) != '7': return
        t = r['target']; lead = leaders.get(t)
        if lead is None: return
        product = r.get('product_id', r.get('objective', r.get('product')))
        if r.get('history_regime') != lead['history_regime'] or product != lead['product']: return
        if ('ordered_leaf_cdf' in lead['procedure_id']) != (family == 'ordered_leaf_cdf'): return
        if lead['procedure_id'].startswith('hgb-') != (family == 'HGB'): return
        if lead['procedure_id'].startswith('empirical-') != (family == 'empirical'): return
        if r.get('actual') in (None, '') or r.get('prediction') in (None, ''): return
        key = (r['game_id'], r['player_id'], t, r['population'])
        if key in candidates: raise ValueError('duplicate matched candidate')
        candidates[key] = dict(prediction=float(r['prediction']), actual=float(r['actual']), fallback=r.get('fallback'))
    with gzip.open(evidence.parent/'distribution-wave-v2/all-predictions.csv.gz', 'rt') as f:
        for r in csv.DictReader(f):
            if r['family']=='ordered_leaf_cdf' and r['information_policy']=='COMMON-2022-MEMORY': admit(r,'ordered_leaf_cdf')
    for p in (evidence.parent/'hgb-history-v1/prediction-chunks').glob('W07-*.json.gz'):
        for r in json.loads(gzip.decompress(p.read_bytes()))['rows']: admit(r,'HGB')
    with gzip.open(evidence.parent/'empirical-history-diagnostic-v1/predictions.csv.gz', 'rt') as f:
        for r in csv.DictReader(f):
            if r['season']=='2026': admit(r,'empirical')
    groups = collections.defaultdict(list)
    for r in records:
        if r['status']=='SUPPORTED': groups[(r['target'],r['population'],r['product_id'])].append(r)
    scores, contrasts = [], []
    for (target,population,product), group in sorted(groups.items()):
        if target=='anytime_td': continue  # No authenticated probability in this source.
        offered=sum(r['target']==target and r['population']==population and r['product_id']==product for r in records)
        view = dict(procedure_id='retained-website-r0-reference-v1' if product=='website_point' else 'retained-provider-reference-v1',
                    procedure_family_id='ARCHIVED_WEBSITE_REFERENCE' if product=='website_point' else 'ARCHIVED_PROVIDER_REFERENCE',
                    target=target,product_id=product,population=population,history_regime='FIXED_ARCHIVE_NOT_RETRAINABLE',
                    record_kind='forecast_evaluation_view',evidence='REPRODUCED_FROM_DATA',season=2026,week=7,
                    evaluation_panel_id='retained-recorded-website-W7-conditional-appearance-v1',forecast_rows=offered,
                    unique_games=len({r['game_id'] for r in group}),fallback_rows=None,
                    cutoff='nearest recorded capture at or before per-gameT90; source publication clocks unverified',
                    uncertainty='one week; insufficient_week_clusters; current-vintage labels and recorded issuance unverified',
                    source_vintage='recorded_pre_game_capture_not_independently_authenticated; current_vintage_NFL_labels',
                    cohort_limit='Conditional on qualified physical appearance inside archived ex-ante issuance. All unresolved issued records retained. No same-cutoff learner claim.',
                    prediction_change_kind='original_retained_forecast_new_scoring')
        metrics=point_metrics([r['prediction'] for r in group],[r['actual'] for r in group],target)
        scores.append(dict(view,**metrics))
        paired=[]
        for r in group:
            key=(r['game_id'],r['player_id'],target,population)
            if key not in candidates:continue
            other=candidates[key]
            if other['actual']!=r['actual']:raise ValueError('candidate source actual mismatch')
            paired.append(dict(r,candidate_prediction=other['prediction'],candidate_fallback=other['fallback']))
        if not paired:continue
        pm=point_metrics([r['prediction'] for r in paired],[r['actual'] for r in paired],target)
        cm=point_metrics([r['candidate_prediction'] for r in paired],[r['actual'] for r in paired],target)
        membership=hashlib.sha256(source.canonical(sorted((r['game_id'],r['player_id'],target,population) for r in paired))).hexdigest()
        comparison=dict(status='PAIRED_RETAINED_ROWS',metric='mae',candidate_error=cm['mae'],comparator_error=pm['mae'],
                        comparator_procedure_id=view['procedure_id'],comparator_history_regime=view['history_regime'],comparator_product_id=product,
                        paired_n=len(paired),membership_sha256=membership,cutoff_policy='UNMATCHED_INFORMATION_CUTOFFS; shared-outcome diagnostic only',uncertainty=view['uncertainty'])
        lead=leaders[target]
        scores.append(dict(view,**cm,procedure_id=lead['procedure_id'],procedure_family_id='EXISTING_V2_FROZEN_LEADER',
                           product_id=lead['product'],history_regime=lead['history_regime'],
                           evaluation_panel_id='retained-website-W7-shared-outcome-reference-'+product+'-v1',
                           forecast_rows=len(paired),unique_games=len({r['game_id'] for r in paired}),
                           comparison=comparison))
        contrasts.append(dict(target=target,population=population,reference_product=product,n=len(paired),
                              reference_mae=pm['mae'],candidate_mae=cm['mae'],delta_mae=cm['mae']-pm['mae'],
                              relative_error_change=(cm['mae']-pm['mae'])/pm['mae'] if pm['mae'] else None,
                              candidate_procedure=lead['procedure_id'],history_regime=lead['history_regime'],
                              status='MATCHED_OUTCOMES_DIFFERENT_INFORMATION_CUTOFFS_NOT_AUTHENTICATED_LIVE_ISSUANCE'))
    source.immutable_json(private/'MATCHED_ROWS.json',dict(records=records,candidates=[dict(game_id=k[0],player_id=k[1],target=k[2],population=k[3],**v) for k,v in candidates.items()]))
    source.immutable_json(public/'SCORES.json',scores)
    source.immutable_json(public/'PAIRED_REFERENCE_COMPARISONS.json',contrasts)
    receipt=dict(state='COMPLETE_LIMITED_REFERENCE_REPLAY',actual_completed_at=source.now(),code_sha256=source.sha(__file__),
                 protocol_sha256=source.sha(admission_path),new_fits=0,new_forecasts=0,week8_outcomes_read=0,
                 source_packets=len(packets),selected_games=len(selected),issued_reference_views=len(records),
                 supported_reference_views=sum(r['status']=='SUPPORTED' for r in records),score_views=len(scores),
                 contrasts=len(contrasts),source_timestamp_verified_rows=sum(r['source_timestamps_verified'] is True for r in records),
                 private_rows_sha256=source.sha(private/'RETAINED_REFERENCE_ROWS.json.gz'),private_matched_sha256=source.sha(private/'MATCHED_ROWS.json'),
                 wall_seconds=time.monotonic()-start,decoded_bytes=decoded,selected_packets=selected_meta,
                 unsupported=[dict(target=k[0],product=k[1],reason=k[2],rows=v) for k,v in sorted(exclusions.items())],
                 historical_website_W1_W7_same_cutoff_comparison='UNESTABLISHED',
                 offers_or_ROI='UNESTABLISHED; self-generated thresholds and unknown prices are not authenticated offers')
    source.immutable_json(public/'RUN_RECEIPT.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in {'selected_packets','unsupported'}},indent=2))


if __name__=='__main__':main()
