#!/usr/bin/env python3
"""Matched analysis of already graded frozen A/B/C outputs; no new grader."""
import argparse
import collections
import hashlib
import json
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nfl_v2.shared_subgroups import packet_rows
from nfl_v2.paired_uncertainty import paired_losses
from tools import grade_saved_week8 as core

SOURCE = ROOT / 'reports/abc-championship/local-week8-final-v1/SCORES.json'
FAMILIES = ('v2-availability-abc-shadow-v1:empirical',
            'v2-availability-abc-shadow-v1:ordered_leaf_cdf:law')
DECIDED = ('WIN', 'LOSS')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, x):
    with p.open('x') as f:
        json.dump(x, f, indent=2, allow_nan=False)
        f.write('\n')


def key(r):
    return (r['game_id'], r['player_id'], r['target'], str(r['line']),
            r['source_head'], r['source_server_clock'], r['decision_time'], r['line_from'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--retained-grades', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    out = args.out.resolve()
    out.mkdir(exist_ok=False)
    start, cpu = time.monotonic(), time.process_time()
    scores = json.loads(SOURCE.read_bytes())
    selected = [s for s in scores if s.get('history_regime') == 'H-MULTI'
        and s.get('product_id') == 'lower_median' and s.get('base_procedure_id') in FAMILIES]
    meta = {s['method_key']:s for s in selected if s['side'] == 'Combined'}
    assert len(meta) == 60
    protocol = dict(schema='B-frozen-availability-final-offer-pair-v1',
        frozen_before_new_pairwise_calculation_utc=datetime.now(timezone.utc).isoformat(),
        audit_TXT_sha256='720b464f8077d3a483a4a73245690071866b7757fb6d20763c2ea8d931061795',
        score_source=str(SOURCE.relative_to(ROOT)), score_source_sha256=sha(SOURCE),
        retained_grade_source_sha256=sha(args.retained_grades), code_sha256=sha(Path(__file__)),
        unchanged_procedures=list(FAMILIES), histories=['H-MULTI'], product='lower_median',
        selection_rule='P1_UNROUNDED_POINT_VS_RETAINED_THRESHOLD',
        registered_changes=['B_MINUS_A:samefittedmodel/qualifiedfresherqueryinputs',
                            'C_MINUS_B:originalseparatelyregisteredrefit/priors'],
        fixed_source_choice='AlreadyfinalretainedWeek8common-offerrows;notchosenfromnewscores',
        panel='Existingall-methodcommon-offermask;ownfullsourcecoverageoutsideitnotestablishedhere',
        outcome_version='NFLVERSE_20261103_FINAL', captured_games=13, full_schedule_games=14,
        missing_game='2026_WEEK8_THURSDAY_NOT_CAPTURED', categories_without_offers=['anytime_td','nick-chart-ppr-v1'],
        no_new_NFL_fits=True, no_new_grading=True, no_new_predictions=True,
        limits=dict(wall_seconds=120, cpu_seconds=120, max_RSS_bytes=1073741824, new_private_row_bytes=0))
    save(out / 'FROZEN_PROTOCOL.json', protocol)
    pools = collections.defaultdict(dict)
    for r in packet_rows(args.retained_grades):
        mid = r.get('method_key')
        if mid not in meta:
            continue
        k = key(r)
        if k in pools[mid]:
            raise ValueError('duplicate retained opportunity within procedure')
        pools[mid][k] = r
    own = []
    for mid, s in meta.items():
        rr = list(pools[mid].values())
        assert len(rr) == s['selection_metrics']['selection_pool_count']
        ss = {z['side']:z for z in selected if z['method_key'] == mid}
        for side, z in ss.items():
            sub = [r for r in rr if r['selected_side'] and (side == 'Combined' or r['selected_side'] == side)]
            assert sum(r['statistical_state'] == 'WIN' for r in sub) == z['selection_metrics']['WIN']
            assert sum(r['statistical_state'] == 'LOSS' for r in sub) == z['selection_metrics']['LOSS']
        numeric = [r for r in rr if r['actual'] is not None and r['prediction'] is not None
                   and r['participation'] == 'VERIFIED_PLAYED_POSITIVE_PHYSICAL']
        record = dict(target=s['target'], procedure_id=s['procedure_id'], base_procedure_id=s['base_procedure_id'],
            method_key=mid, availability_arm=s['availability_arm'], history='H-MULTI', output='lower_median',
            rule='P1', season=2026, actual_weeks=[8], eligible_in_common_panel=len(rr),
            side_records={side:dict(selected=z['forecast_rows'], wins=z['selection_metrics']['WIN'],
                losses=z['selection_metrics']['LOSS'], decided=z['n'],
                hit_rate=z['selection_metrics']['WIN']/z['n'] if z['n'] else None,
                status_counts=z['selection_metrics']['status_counts']) for side,z in ss.items()},
            numerical_panel='Sameknown-outcomeoffered-playerrows;notnativeparticipantpanel',
            numeric_n=len(numeric), mae=sum(abs(r['prediction']-r['actual']) for r in numeric)/len(numeric) if numeric else None,
            bias=sum(r['prediction']-r['actual'] for r in numeric)/len(numeric) if numeric else None,
            fallback_counts=dict(collections.Counter(r.get('fallback') for r in rr)),
            games=len({r['game_id'] for r in rr}),
            evidence='RETAINED_EARLY_FORECAST_PLUS_LATER_PROVIDER_LABELLED_LINES;TIMING_UNVERIFIED_DIAGNOSTIC',
            prices_or_profit=None, source_score_sha256=protocol['score_source_sha256'])
        assert record['side_records']['Combined']['wins'] == sum(record['side_records'][x]['wins'] for x in ('over','under'))
        assert record['side_records']['Combined']['losses'] == sum(record['side_records'][x]['losses'] for x in ('over','under'))
        own.append(record)
    rows = []
    for family in FAMILIES:
        for target in sorted({s['target'] for s in meta.values()}):
            mids = {s['availability_arm']:mid for mid,s in meta.items() if s['target'] == target and s['base_procedure_id'] == family}
            for cand, comp in (('B','A'),('C','B')):
                ca, co = pools[mids[cand]], pools[mids[comp]]
                assert set(ca) == set(co)
                keys = sorted(k for k in ca if ca[k]['statistical_state'] in DECIDED and co[k]['statistical_state'] in DECIDED)
                for k in keys:
                    assert ca[k]['actual'] == co[k]['actual'] and ca[k]['line'] == co[k]['line']
                views = {
                    'FULL_SYSTEM_ON_EXISTING_COMMON_MASK':keys,
                    'PAIR_KNOWN_NONFALLBACK':[k for k in keys if ca[k].get('fallback') == co[k].get('fallback') == 'none'],
                    'PAIR_ANY_KNOWN_FALLBACK':[k for k in keys if all(r.get('fallback') not in (None,'UNKNOWN_NOT_RETAINED') for r in (ca[k],co[k]))
                        and any(r.get('fallback') != 'none' for r in (ca[k],co[k]))],
                }
                for view, kk in views.items():
                    for metric in ('STATISTICAL_SELECTED_SIDE_LOSS_RATE','MAE'):
                        loss = (lambda r:float(r['statistical_state'] == 'LOSS')) if metric != 'MAE' else (lambda r:abs(r['prediction']-r['actual']))
                        u = paired_losses([loss(ca[k]) for k in kk],[loss(co[k]) for k in kk],[8]*len(kk),[k[0] for k in kk])
                        r = dict(target=target, procedure_id=meta[mids[cand]]['procedure_id'],
                            comparator_procedure_id=meta[mids[comp]]['procedure_id'], product_id='lower_median', comparator_product_id='lower_median',
                            population='EXISTING_ALL_METHOD_COMMON_OFFER_MASK', season=2026, history_regime='H-MULTI',
                            comparator_history_regime='H-MULTI', policy_id='P1_FROZEN_AVAILABILITY_'+cand+'_VS_'+comp,
                            contrast=cand+'_MINUS_'+comp, fallback_view=view, metric=metric, n=len(kk),
                            candidate_error=u['candidate_error'], comparator_error=u['comparator_error'], delta=u['delta'],
                            relative_error_change=u['relative_error_change'], uncertainty=u,
                            candidate_wins=sum(ca[k]['statistical_state'] == 'WIN' for k in kk),
                            comparator_wins=sum(co[k]['statistical_state'] == 'WIN' for k in kk),
                            membership_sha256=hashlib.sha256(json.dumps(kk,separators=(',',':')).encode()).hexdigest(),
                            alwaysOver_wins=sum(ca[k]['actual'] > ca[k]['line'] for k in kk),
                            alwaysUnder_wins=sum(ca[k]['actual'] < ca[k]['line'] for k in kk),
                            same_selection_rule=True, actual_weeks=[8],
                            history_limit='Originalfrozenavailabilitymechanisms;notnewlearnerororiginalissuedpropselections. '
                                'Fullsystemiswithintheexistingsharedmask;outside-maskcoverageunknown. '
                                'SourcecaptureupperboundqualifiesfresherW7only;notauthenticatedoldpublicationtimes. '
                                'Oneexposedweek;gameintervalsdescriptive,nomultiplicityadjustment;notfiveweekprimaryqualification.')
                        rows.append(r)
    save(out / 'OWN_POLICY_RECORDS.json', own)
    save(out / 'INDEX_BOUND_PAIRED_ANALYSIS.json', rows)
    core.write_csv(out / 'PAIRED_COMPARISONS.csv', rows)
    receipt = dict(state='COMPLETE_NEW_MATCHED_ANALYSIS_OF_EXISTING_FINAL_GRADES',
        at_utc=datetime.now(timezone.utc).isoformat(), source_protocol_sha256=sha(out / 'FROZEN_PROTOCOL.json'),
        original_methods=len(own), side_records_reconciled=len(selected), paired_comparison_views=len(rows),
        new_NFL_fits=0, new_model_inference=0, new_forecasts=0, new_grades=0, new_test_weeks=0,
        full_current_or_historical_championship_complete=False, no_private_row_copies=True,
        resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,
                       peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
    assert receipt['resources']['wall_seconds'] < 120 and receipt['resources']['peak_RSS_bytes'] < 1073741824
    save(out / 'RUN_RECEIPT.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
