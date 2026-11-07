"""Saved-policy/cohort aggregation using existing scores and frozen memberships.

No forecasts, choices, ranks, fits or grades are recomputed. ALL-cohort results
already exist and are deliberately excluded from this extension.
"""
import collections
import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import abc_b_c_bound_replay as a
from tools.supplement_b_predictive_improvement_01 import hid, views, select_week


def main(private, evidence, out):
    start, cpu = time.monotonic(), time.process_time()
    payload = a.load(private / 'CALIBRATOR_MODELS_AND_ROWS.json.gz')
    rows = payload['rows']
    manifests = a.load(out / 'COHORT_MEMBERSHIP_MANIFEST.json')
    profiles = {}
    for name in ['memberships.json.gz', 'future-memberships.json.gz']:
        for m in a.load(evidence / 'pregame-cohort-scorecards-v2' / name):
            game, player, target, population = m['key']
            if target in ['rec', 'pass_td'] and population in ['primary', 'frozen_exante_feed']:
                assert (game, player, target) not in profiles
                profiles[game, player, target] = m
    scores = []
    for target in ['rec', 'pass_td']:
        source = [r for r in rows if r['target'] == target]
        baseline = {r['offer_id']: r for r in source
                    if r['method_key'].endswith('::B1') and r['selection_policy'] == 'ALL'}
        tags = {}
        for oid, r in baseline.items():
            labels = {'role_' + r['position']}
            if r['probabilities'] is not None and r['repair_state'] == 'FITTED_GAME_WEIGHTED_INTERCEPT_MAP':
                labels.add('ACTIVE_REPAIR_COMMON')
            if r['probabilities'] is not None and r['fallback'] in ['none', False]:
                labels.add('BASE_LEARNED_COMMON')
            m = profiles.get((r['game_id'], r['player_id'], target))
            if m is None or m['ranking_cutoff'] > r['decision_epoch']:
                labels.add('membership_unavailable')
            else:
                assert m['latest_available'] is None or m['latest_available'] < m['ranking_cutoff']
                labels.update(m['cohorts'])
            tags[oid] = labels
        for manifest in (m for m in manifests if m['target'] == target and m['cohort_id'] != 'SOURCE_MEMBERSHIP_CENSUS'):
            cohort = manifest['cohort_id']
            ids = sorted(oid for oid, names in tags.items() if cohort in names)
            assert len(ids) == manifest['n'] and hid(ids) == manifest['membership_sha256']
            for arm in [0, 1]:
                for policy in sorted({r['selection_policy'] for r in source} - {'ALL'}):
                    pool = [r for r in source if r['method_key'].endswith('::B' + str(arm))
                            and r['selection_policy'] == policy and r['offer_id'] in tags
                            and cohort in tags[r['offer_id']]]
                    for week in views(list(baseline.values())):
                        rr = select_week(pool, week)
                        meta = dict(
                            history_regime='H-MULTI', product_id='exact_line_probability_product',
                            decision_rule=policy, cohort_id=cohort,
                            cohort_scope='CONDITION_ON_ORIGINAL_FROZEN_MEMBERSHIP_AFTER_' +
                            'ORIGINAL_POLICY;NEVER_RERANK_OR_REPLACE_MEMBERS',
                            cohort_membership_sha256=hid(sorted(r['offer_id'] for r in rr)),
                            source_prediction_and_selection_rows_unchanged=True,
                            full_source_offer_universe=len(select_week(list(baseline.values()), week)))
                        if policy.startswith('ROLLING_K'):
                            k, side = policy.split('_')[1:]
                            meta.update(K=int(k[1:]), rank_scope='PER_CATEGORY_PER_WEEK_ROLLING_DECISION_BATCHES', rank_side_pool=side)
                        vv = a.score(rr, next(iter(baseline.values()))['method_key'][:-1] + str(arm),
                                     target, week, meta, 'B-IMPROVEMENT01-POLICY-COHORT:' + target + ':' + cohort + ':' + policy)
                        for v in vv:
                            v.update(strategy=policy, cohort_id=cohort, mae=None, mse=None,
                                     rmse=None, bias=None, p90_abs=None, p95_abs=None, max_abs=None,
                                     native_metric_null_reason='EVENT_POLICY_HAS_NO_OWN_POINT_OUTPUT',
                                     probability_scope='NO_ADDITIONAL_COHORT_PROPER_SCORE;FULL_BOARD_AND_SELECTED_PRIMARY_SCORES_RETAINED')
                        scores.extend(vv)
    path = out / 'POLICY_COHORT_SCORES.json'
    body = json.dumps(scores, indent=2, allow_nan=False) + '\n'
    assert len(body.encode()) <= 33554432, 'Public aggregate allocation exceeded before write'
    assert not path.exists()
    path.write_text(body)
    receipt = dict(
        state='SAVED_POLICY_COHORT_AGGREGATION_COMPLETE', source_rows_sha256=a.sha(private / 'CALIBRATOR_MODELS_AND_ROWS.json.gz'),
        score_sha256=a.sha(path), score_bytes=path.stat().st_size, score_views=len(scores),
        policies_per_arm=14, cohorts_per_target=20, parent_ALL_scores_not_repeated=True,
        policy_or_membership_changes=0, new_fits=0, new_forecast_inference=0,
        new_grades=0, new_private_bytes=0, new_NFL_observations=0,
        wall_seconds=time.monotonic() - start, cpu_seconds=time.process_time() - cpu,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
    assert receipt['wall_seconds'] <= 180 and receipt['peak_RSS_bytes'] <= 1073741824
    a.save(out / 'POLICY_COHORT_RECEIPT.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main(*map(Path, sys.argv[1:4]))
