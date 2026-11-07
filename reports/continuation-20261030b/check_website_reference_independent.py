"""Replay retained Week7 website/projection references with independent math.

No network, fits, future outcomes or producer scoring/selection helpers.
"""
import argparse
from collections import defaultdict, Counter
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'reports/continuation-20261030'))
from check_new_wave_prefixes import load, clock, canonical

PUBLIC = ROOT / 'reports/continuation-20261030b/website-reference-replay-v1'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def close(a, b):
    assert (a is None and b is None) or (a is not None and b is not None and math.isclose(a, b, rel_tol=2e-11, abs_tol=2e-10)), (a, b)
def key(r): return r['game_id'], r['player_id'], r['target'], r['population']
def numeric(x): return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def verify(private_root, source):
    public_root = PUBLIC.parent
    admission = json.loads((public_root / 'WEBSITE_REFERENCE_RECOVERY_ADMISSION.json').read_text())
    receipt = json.loads((PUBLIC / 'RUN_RECEIPT.json').read_text())
    private = private_root / 'website-reference-replay-v1'
    assert sha(private / 'RETAINED_REFERENCE_ROWS.json.gz') == receipt['private_rows_sha256']
    assert sha(private / 'MATCHED_ROWS.json') == receipt['private_matched_sha256']
    original = json.loads(gzip.decompress((private / 'RETAINED_REFERENCE_ROWS.json.gz').read_bytes()))
    matched = json.loads((private / 'MATCHED_ROWS.json').read_text())
    assert original == matched['records']
    p = json.loads((ROOT / 'reports/continuation-20261030/distribution-wave-v2/FROZEN_PROTOCOL.json').read_text())
    rows, _, games = load(source, p)
    # Raw source helper already excludes future stats before decoding values.
    truth = {(r['game_id'], r['player_id']): r for r in rows if games[r['game_id']]['year'] == 2026 and games[r['game_id']]['week'] == 7}
    schedule = {}
    with (source / 'games.csv').open() as handle:
        for r in csv.DictReader(handle):
            if (r['game_type'], r['season'], r['week']) == ('REG', '2026', '7'):
                schedule[r['espn']] = {'game_id': r['game_id'], 'kickoff': games[r['game_id']]['kickoff']}
    id_path = source / 'roster-week8-identity-2026.csv.gz'
    identity_candidates = defaultdict(set)
    with gzip.open(id_path, 'rt') as handle:
        for r in csv.DictReader(handle):
            if r['season'] == '2026' and int(r['week']) <= 7 and r['sleeper_id'] and r['gsis_id']:
                identity_candidates[r['sleeper_id']].add(r['gsis_id'])
    bridge = {k: next(iter(v)) for k, v in identity_candidates.items() if len(v) == 1}
    selected = {}
    decoded_bytes = 0
    packets = 0
    for desc in admission['source_files']:
        path = private_root / 'website-reference-probe-v1' / Path(desc['path']).name
        blob = path.read_bytes()
        assert len(blob) == desc['bytes']
        assert hashlib.sha1(b'blob ' + str(len(blob)).encode() + b'\0' + blob).hexdigest() == desc['git_blob_sha1']
        # Bounded read rejects oversized payloads while decoding, before allocation.
        with gzip.open(path, 'rb') as handle: body = handle.read(admission['budget']['max_decoded_bytes_per_file'] + 1)
        assert len(body) <= admission['budget']['max_decoded_bytes_per_file']
        decoded_bytes += len(body)
        assert decoded_bytes <= admission['budget']['max_decompressed_bytes']
        envelope = json.loads(body)
        packet = envelope['payload']
        assert hashlib.sha256(canonical(packet)).hexdigest() == envelope['payload_sha256']
        capture = clock(packet['captured_at'])
        assert clock(packet['forecast_generated_at']) <= capture
        seen = set()
        for r in packet['rows']:
            assert (r['season'], r['week']) == (2026, 7)
            assert r['game_id'] in schedule and clock(r['kickoff']) == schedule[r['game_id']]['kickoff']
            ident = (r['player_id'], r['game_id'], r['category'])
            assert ident not in seen
            seen.add(ident)
        for event in {r['game_id'] for r in packet['rows']}:
            if capture <= schedule[event]['kickoff'] - 5400:
                candidate = (capture, desc['path'], packet)
                old = selected.get(event)
                if old is None or capture > old[0] or capture == old[0] and desc['path'] < old[1]: selected[event] = candidate
        packets += 1
    assert packets == receipt['source_packets'] == 93 and decoded_bytes == receipt['decoded_bytes']
    expected = {}
    selected_manifest = {r['game_id']: r for r in receipt['selected_packets']}
    for event, (capture, name, packet) in selected.items():
        game = schedule[event]
        assert selected_manifest[game['game_id']]['public_source_path'] == name
        for r in packet['rows']:
            if r['game_id'] != event: continue
            gsis, target = bridge.get(str(r['player_id'])), r['category']
            t = truth.get((game['game_id'], gsis))
            position = t['position'] if t else r['position']
            population = 'primary' if position in p['source_role_contract']['primary'].get(target, []) else 'extended'
            for product, field in [('website_point', 'adjusted_projection'), ('provider_point', 'raw_projection')]:
                value = r.get(field)
                status = 'TARGET_NOT_COMPARABLE' if target not in p['targets'] else 'NO_EXACT_ID' if gsis is None else 'NO_STAT_ROW_OR_APPEARANCE_UNKNOWN' if t is None or all(v is None for k, v in t['values'].items() if k != 'nick-chart-ppr-v1') else 'POSITION_MISMATCH' if t['position'] != r['position'] else 'SUPPORTED'
                if status == 'SUPPORTED' and not numeric(value): status = 'MISSING_EXPLICIT_POINT_OR_PROBABILITY'
                actual = float(t['values'][target]) if status == 'SUPPORTED' and t['values'][target] is not None else None
                if status == 'SUPPORTED' and actual is None: status = 'MISSING_ACTUAL'
                ident = (game['game_id'], gsis, target, population, product)
                assert ident not in expected
                expected[ident] = dict(actual=actual, prediction=value if isinstance(value, (int, float)) else None, status=status, position=position, source_path=name)
    checks = 0
    for r in original:
        ident = key(r) + (r['product_id'],)
        e = expected.pop(ident)
        for field in ('actual', 'prediction', 'status', 'position', 'source_path'):
            assert r[field] == e[field], (field, r[field], e[field]); checks += 1
    assert not expected and len(original) == receipt['issued_reference_views'] == 4552
    leaders_path = ROOT / 'reports/continuation-20261030/TOP5_BY_CATEGORY_PRODUCT.json'
    rank1 = [r for r in json.loads(leaders_path.read_text()) if r['ranking_product'] == 'display_point' and r['rank'] == 1 and r['target'] != 'nick-chart-ppr-v1']
    leaders = {r['target']: r for r in rank1}
    tie_counts = Counter(r['target'] for r in rank1)
    candidates = {key(r): r for r in matched['candidates']}
    original_candidates = {}
    def admit(r, family):
        if str(r.get('season', 2026)) != '2026' or str(r['week']) != '7': return
        target = r['target']; leader = leaders.get(target)
        if leader is None: return
        if r['history_regime'] != leader['history_regime']: return
        product = r.get('product_id', r.get('objective', r.get('product')))
        if product != leader['product']: return
        expected_family = 'HGB' if leader['procedure_id'].startswith('hgb-') else 'empirical' if leader['procedure_id'].startswith('empirical-') else 'ordered_leaf_cdf'
        if family != expected_family: return
        if r.get('actual') in ('', None) or r.get('prediction') in ('', None): return
        ident = key(r)
        assert ident not in original_candidates
        original_candidates[ident] = dict(prediction=float(r['prediction']), actual=float(r['actual']), fallback=r.get('fallback'))
    with gzip.open(private_root/'distribution-wave-v2/all-predictions.csv.gz', 'rt') as handle:
        for r in csv.DictReader(handle):
            if r['family'] == 'ordered_leaf_cdf' and r['information_policy'] == 'COMMON-2022-MEMORY': admit(r, 'ordered_leaf_cdf')
    for path in (private_root/'hgb-history-v1/prediction-chunks').glob('W07-*.json.gz'):
        for r in json.loads(gzip.decompress(path.read_bytes()))['rows']: admit(r, 'HGB')
    with gzip.open(private_root/'empirical-history-diagnostic-v1/predictions.csv.gz', 'rt') as handle:
        for r in csv.DictReader(handle): admit(r, 'empirical')
    assert set(candidates) == set(original_candidates)
    for ident, r in candidates.items():
        for f in ('prediction', 'actual', 'fallback'): assert r[f] == original_candidates[ident][f]; checks += 1
    groups = defaultdict(list)
    for r in original:
        if r['status'] == 'SUPPORTED': groups[(r['target'], r['population'], r['product_id'])].append(r)
    scores = json.loads((PUBLIC/'SCORES.json').read_text())
    contrasts = json.loads((PUBLIC/'PAIRED_REFERENCE_COMPARISONS.json').read_text())
    def metric(rows, field):
        errors = [r[field] - r['actual'] for r in rows]
        return dict(n=len(errors), mae=math.fsum(map(abs, errors))/len(errors), mse=math.fsum(e*e for e in errors)/len(errors), bias=math.fsum(errors)/len(errors))
    for score in scores:
        candidate = score['procedure_family_id'] == 'EXISTING_V2_FROZEN_LEADER'
        product = score['comparison']['comparator_product_id'] if candidate else score['product_id']
        rows = groups[(score['target'], score['population'], product)]
        if candidate: rows = [dict(r, candidate_prediction=candidates[key(r)]['prediction']) for r in rows if key(r) in candidates]
        m = metric(rows, 'candidate_prediction' if candidate else 'prediction')
        for field, value in m.items(): close(score[field], value); checks += 1
        close(score['rmse'], math.sqrt(m['mse'])); checks += 1
        assert score['target'] not in ('nick-chart-ppr-v1', 'fpts', 'anytime_td')
    for contrast in contrasts:
        rows = groups[(contrast['target'], contrast['population'], contrast['reference_product'])]
        rows = [dict(r, candidate_prediction=candidates[key(r)]['prediction']) for r in rows if key(r) in candidates]
        a, b = metric(rows, 'candidate_prediction'), metric(rows, 'prediction')
        for field, value in [('reference_mae', b['mae']), ('candidate_mae', a['mae']), ('delta_mae', a['mae']-b['mae']), ('relative_error_change', (a['mae']-b['mae'])/b['mae'] if b['mae'] else None)]:
            close(contrast[field], value); checks += 1
        assert contrast['n'] == len(rows)
    return dict(status='PASS_RETAINED_SELECTION_RAW_LABEL_JOIN_AND_NATIVE_ERRORS', source_packets=packets, selected_games=len(selected), decoded_bytes=decoded_bytes, retained_reference_views=len(original), supported_reference_views=sum(r['status']=='SUPPORTED' for r in original), original_candidate_rows=len(candidates), score_views=len(scores), paired_contrasts=len(contrasts), independent_checks=checks,
                leader_ties_selected_by_frozen_table_last_entry={k:n for k,n in tie_counts.items() if n>1}, source_identity_sha256=sha(id_path), frozen_leader_table_sha256=sha(leaders_path), score_sha256=sha(PUBLIC/'SCORES.json'), paired_sha256=sha(PUBLIC/'PAIRED_REFERENCE_COMPARISONS.json'),
                evidence='REPRODUCED_FROM_RETAINED_RECORDED_WEBSITE_REFERENCES; original internal clocks not independently authenticated; labels are current-vintage; historical learner information cutoffs differ',
                limitations=['One exposed week; frozen whole-panel leaders were retrospectively chosen, not a prior Week7 selector', 'Source publication, actual served values, offered lines/prices and ROI unestablished', 'No anytime probability and no parity between website fpts and Nick chart'], new_fits=0, new_forecasts=0, week8_outcomes_read=0)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-root', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    args=parser.parse_args();report=verify(args.private_root,args.source_root)
    Path(__file__).with_name('WEBSITE_REFERENCE_INDEPENDENT_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
