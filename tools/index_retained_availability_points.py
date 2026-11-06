#!/usr/bin/env python3
"""Retain native errors on the already qualified final offered-player masks.

Uses the existing point scorer. Original forecasts, decisions and labels are
read-only; this adds numeric evaluation views, not NFL outcomes or a new grader.
"""
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
from nfl_v2.scoring import point_metrics
from nfl_v2.shared_subgroups import packet_rows
from tools.compare_retained_availability_final_offers import key


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, x):
    with p.open('x') as f:
        json.dump(x, f, indent=2, allow_nan=False)
        f.write('\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--retained-grades', required=True, type=Path)
    ap.add_argument('--comparison-root', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    a.out.mkdir(exist_ok=False)
    start, cpu = time.monotonic(), time.process_time()
    source = a.comparison_root / 'OWN_POLICY_RECORDS.json'
    own = json.loads(source.read_bytes())
    selected = {r['method_key']:r for r in own}
    protocol = dict(at_utc=datetime.now(timezone.utc).isoformat(),
        source_own_records=str(source.relative_to(ROOT)) if source.is_absolute() else str(source),
        source_own_records_sha256=sha(source), retained_grades_sha256=sha(a.retained_grades),
        scorer='nfl_v2.scoring.point_metrics', scorer_sha256=sha(ROOT / 'nfl_v2/scoring.py'),
        new_forecasts=0, new_grades=0, new_NFL_fit_calls=0,
        evaluation_kind='Newnumericpointscoreviewsontheexistingactual-linecommonmask;old180selectionviewsreused',
        all12scope='10ordinaryoffertargetsscored;ATD/exactchartoffersunavailable',
        forecast_source_and_cutoff='OriginalfrozenearlyWeek8capture;laterretainedproviderlabelledthresholds. Timingunverifieddiagnostic.',
        limits=dict(wall_seconds=60,max_RSS_bytes=1073741824,new_private_row_bytes=0))
    save(a.out / 'FROZEN_PROTOCOL.json', protocol)
    by = collections.defaultdict(list)
    for r in packet_rows(a.retained_grades):
        if r.get('method_key') in selected:
            by[r['method_key']].append(r)
    scores = []
    for mid, m in selected.items():
        rr = by[mid]
        numeric = [r for r in rr if r['actual'] is not None and r['prediction'] is not None
                   and r['participation'] == 'VERIFIED_PLAYED_POSITIVE_PHYSICAL']
        if len({key(r) for r in rr}) != len(rr):
            raise ValueError('duplicate numeric offer')
        stats = point_metrics([r['prediction'] for r in numeric],[r['actual'] for r in numeric],m['target'])
        assert stats['n'] == m['numeric_n']
        assert stats['mae'] == m['mae'] and stats['bias'] == m['bias']
        errors = [abs(r['prediction'] - r['actual']) for r in numeric]
        counts = {'exact_rate':dict(numerator=sum(e == 0 for e in errors), denominator=len(errors))}
        for t in (1,5,10):
            counts['abs_lt_'+str(t)] = dict(numerator=sum(e < t for e in errors),denominator=len(errors))
            counts['abs_le_'+str(t)] = dict(numerator=sum(e <= t for e in errors),denominator=len(errors))
        for v in counts.values():
            v['rate'] = v['numerator']/v['denominator'] if v['denominator'] else None
        record = dict(record_id='B-AUDIT-AVAIL-POINT-'+mid,
            record_kind='forecast_evaluation_view', procedure_id=m['procedure_id'],
            procedure_family_id=m['base_procedure_id'], target=m['target'], history_regime='H-MULTI',
            product_id='lower_median', policy_id='FROZEN_AVAILABILITY_'+m['availability_arm'],
            information_policy='ORIGINAL_REGISTERED_AVAILABILITY_'+m['availability_arm'],
            population='EXISTING_ALL_METHOD_COMMON_OFFER_MASK', position='ALL',
            evaluated_positions=sorted({r['position'] for r in rr}),
            season=2026, week=8, evaluation_seasons=[2026], evaluation_weeks=[8],
            fallback_view='FULL_SYSTEM_WITHIN_COMMON_OFFER_MASK', period='REG',
            evaluation_panel_id='B-RETAINED-AVAILABILITY-W8-FINAL-MATCHED-v1',
            horizon='ORIGINAL_EARLY_CAPTURE_PLUS_RETAINED_LATER_THRESHOLD',
            source_vintage='ORIGINAL_SAVED_FORECASTS;CURRENT_REVISED_20261103_FINAL_LABELS;QUOTE_CLOCK_UNVERIFIED',
            evidence='NEW_EXPERIMENT_SAVED_ROW_REPLAY', forecast_rows=len(rr),
            fallback_rows=sum(r.get('fallback') != 'none' for r in rr),
            scored_fallback_rows=sum(r.get('fallback') != 'none' for r in numeric),
            label_state_counts=dict(collections.Counter(r['label_state'] for r in rr)),
            unique_games=len({r['game_id'] for r in numeric}),
            unique_players=len({r['player_id'] for r in numeric}),
            unique_player_games=len({(r['game_id'],r['player_id']) for r in numeric}),
            membership_sha256=hashlib.sha256(json.dumps(sorted(key(r) for r in numeric),separators=(',',':')).encode()).hexdigest(),
            precision_counts=counts, new_fits=0, **stats)
        scores.append(record)
    save(a.out / 'SCORES.json', scores)
    save(a.out / 'RUN_RECEIPT.json', dict(state='COMPLETE_NATIVE_ERRORS_RETAINED_WITH_REGISTERED_PRECISION',
        at_utc=datetime.now(timezone.utc).isoformat(), score_views=len(scores),
        source_comparison_rows_unchanged=True,new_NFL_observations=0,new_NFL_fit_calls=0,new_forecasts=0,
        wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        one_exposed_test_week_not_five=True))
    print(json.dumps(dict(new_numeric_evaluation_views=len(scores),new_NFL_fit_calls=0,new_NFL_observations=0)))


if __name__ == '__main__':
    main()
