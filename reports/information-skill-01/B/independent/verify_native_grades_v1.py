"""Independent frozen-output grading verification; no common grader/import.

The private retained source is supplied by --private-source, never embedded or
exported. Only aggregate counts and commitments are written by this verifier.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
import resource
import time
from datetime import datetime, timezone
from pathlib import Path

from scipy import stats


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def commitment(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--private-source', type=Path, required=True)
    a = ap.parse_args()
    start, cpu = time.monotonic(), time.process_time()
    base = Path('reports/information-skill-01/B')
    output = base/'independent/OWN_NATIVE_GRADE_VERIFICATION_V1.json'
    if output.exists():
        raise RuntimeError('Existing verification retained; no overwrite')
    source = read(a.private_source)
    source_rows = source['rows']
    # Exclude line/outcome from identity so disagreements across retained views
    # are detected rather than becoming separate convenient opportunities.
    fields = ('game_id', 'player_id', 'category', 'period', 'scoring_contract_id')
    invariant_fields = ('line', 'actual', 'season', 'week', 'position', 'line_from', 'kickoff')
    offers, view_counts = {}, collections.Counter()
    errors = []
    for row in source_rows:
        key = tuple(row[k] for k in fields)
        if key in offers:
            if any(row.get(k) != offers[key].get(k) for k in invariant_fields):
                errors.append('Retained views disagree on offer/outcome/source identity')
        else:
            offers[key] = row
        view_counts[key] += 1
    if len(offers) != 142:
        errors.append('Expected exactly142 deduplicated actual completion offers')
    official_path = Path('reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz')
    official = {(r['game_id'], r['player_id']): r for r in read(official_path)}
    explicit_known, explicit_zero, unknown_outcomes, half_points = 0, 0, 0, 0
    outcome_binding = []
    for key, offer in offers.items():
        stat = official.get(key[:2])
        if stat is None or not stat.get('target_parity') or not stat.get('physical_participation'):
            errors.append('No qualified played official completion binding')
            continue
        if offer['actual'] is None:
            unknown_outcomes += 1
        elif stat.get('official_completions') != offer['actual']:
            errors.append('Actual differs from explicit qualified official completions')
        else:
            explicit_known += 1
            explicit_zero += int(offer['actual'] == 0)
        half_points += int(float(offer['line']) % 1 == .5)
        outcome_binding.append((key, offer['line'], offer['actual'], offer['line_from']))
    parents = {}; prediction_bindings = {}
    for path in sorted((base/'wave-v1/predictions').glob('2026-*.json.gz')):
        prediction_bindings[str(path)] = sha(path)
        for row in read(path)['rows']:
            parents[row['method'], row['game_id'], row['player_id']] = row
    arms = ('SKILL_C0', 'SKILL_C1', 'SKILL_R0', 'SKILL_R1')
    policies = ('MEAN', 'MEDIAN', 'LAW')
    by_product, decisions = {}, {}

    def side(prediction, line, policy):
        if policy != 'LAW':
            value = prediction['mean' if policy == 'MEAN' else 'lower_median']
            if value is None or not math.isfinite(float(value)):
                return None
            return 'OVER' if value > line else 'UNDER' if value < line else 'ABSTAIN'
        mean, shape = prediction['law']['mean'], prediction['law']['shape']
        if not math.isfinite(mean) or not math.isfinite(shape) or mean < 0 or shape <= 0:
            return None
        k = math.floor(line)
        nbp = shape/(shape+mean)
        below = float(stats.nbinom.cdf(k-1 if float(line) == k else k, shape, nbp))
        at_or_below = float(stats.nbinom.cdf(k, shape, nbp))
        over, under = 1-at_or_below, below
        return 'OVER' if over > under else 'UNDER' if under > over else 'ABSTAIN'

    def grade(chosen, actual, line):
        if chosen is None:
            return 'UNAVAILABLE'
        if chosen == 'ABSTAIN':
            return 'ABSTAIN'
        if actual is None:
            return 'UNKNOWN'
        if actual == line:
            return 'PUSH'
        truth = 'OVER' if actual > line else 'UNDER'
        return 'WIN' if chosen == truth else 'LOSS'

    for arm in arms:
        for policy in policies:
            rows = []
            for key, offer in offers.items():
                pred = parents.get((arm, *key[:2]))
                chosen = side(pred, float(offer['line']), policy) if pred else None
                state = grade(chosen, offer['actual'], float(offer['line']))
                rows.append(dict(key=key, side=chosen, state=state, week=offer['week']))
            decisions[arm, policy] = {r['key']: r for r in rows}
            for window in ['ALL']+[str(w) for w in range(5, 10)]:
                selected = [r for r in rows if window == 'ALL' or str(r['week']) == window]
                counters = {}
                for s in ('OVER', 'UNDER', 'COMBINED'):
                    subset = [r for r in selected if s == 'COMBINED' or r['side'] == s]
                    w = sum(r['state'] == 'WIN' for r in subset)
                    l = sum(r['state'] == 'LOSS' for r in subset)
                    counters[s] = dict(wins=w, losses=l, decided=w+l, rate=w/(w+l) if w+l else None,
                                       selected=sum(r['side'] in ('OVER', 'UNDER') for r in subset))
                by_product[arm, policy, window] = dict(method=arm, policy=policy, window=window,
                    eligible=len(selected), available=sum(r['state'] != 'UNAVAILABLE' for r in selected),
                    unknown=sum(r['state'] == 'UNKNOWN' for r in selected),
                    abstentions=sum(r['state'] == 'ABSTAIN' for r in selected),
                    pushes=sum(r['state'] == 'PUSH' for r in selected), **counters)
    main_path = base/'evaluation-v2/MAIN_TABLES_V1.json.gz'
    main_rows = read(main_path)
    comparisons = []
    for key, result in by_product.items():
        arm, policy, window = key
        matches = [r for r in main_rows if (r['method'], r['policy'], str(r['week_view'])) == key]
        same = len(matches) == 1
        if same:
            row = matches[0]
            for s in ('OVER', 'UNDER', 'COMBINED'):
                for f in ('wins', 'losses', 'decided', 'selected'):
                    expected = result[s][f]
                    observed = row[s][f]
                    same &= observed == expected or row[s]['decided'] == 0 and expected == 0 and observed is None
                rate = result[s]['rate']
                same &= row[s]['rate'] is None if rate is None else math.isclose(row[s]['rate'], rate, abs_tol=1e-12)
            for f in ('eligible', 'available', 'unknown', 'abstentions'):
                same &= result[f] == row[f]
        comparisons.append(dict(method=arm, policy=policy, window=window, aggregate_identical=bool(same)))
        if not same:
            errors.append('Independent own-side grade aggregate differs: '+arm+'/'+policy+'/'+window)
    flip_results = []
    for policy in policies:
        reference = decisions['SKILL_C0', policy]
        for arm in arms[1:]:
            candidate = decisions[arm, policy]
            changed = [k for k in reference if reference[k]['side'] != candidate[k]['side']]
            transitions = collections.Counter(reference[k]['state']+'->'+candidate[k]['state'] for k in changed)
            flip_results.append(dict(candidate=arm, control='SKILL_C0', policy=policy,
                changed_sides=len(changed), changed_by_week=dict(collections.Counter(str(reference[k]['week']) for k in changed)),
                grade_transitions=dict(transitions), changed_membership_commitment=commitment(sorted(changed))))
    expectations = {
        'C1_mean_no_flips': next(x for x in flip_results if x['candidate']=='SKILL_C1' and x['policy']=='MEAN')['changed_sides']==0,
        'R0_R1_mean_four_losses_to_wins': all(next(x for x in flip_results if x['candidate']==arm and x['policy']=='MEAN')['grade_transitions']=={'LOSS->WIN':4} for arm in ['SKILL_R0','SKILL_R1']),
        'all_law_sides_identical': all(x['changed_sides']==0 for x in flip_results if x['policy']=='LAW')}
    for label, ok in expectations.items():
        if not ok:
            errors.append('Requested flip expectation not established: '+label)
    report = dict(id='B-INFORMATION-SKILL-OWN-NATIVE-GRADE-VERIFICATION-v1', UTC=datetime.now(timezone.utc).isoformat(),
        status='PASS' if not errors else 'FAILED_PRESERVED', all_passed=not errors,
        scope='Independent OWN-B strict point-crossing and directSciPy NB exact-line law direction/grade arithmetic on the same frozen native142 completion offers. No common grader, new canonical score, private-peer parity or source-clock authentication.',
        source=dict(private_source_content_SHA256=sha(a.private_source), private_source_bytes=a.private_source.stat().st_size,
                    raw_rows=len(source_rows), deduplicated_offer_count=len(offers), view_count_min=min(view_counts.values()), view_count_max=max(view_counts.values()),
                    private_source_path_or_rows_published=False, offer_outcome_binding_SHA256=commitment(sorted(outcome_binding))),
        official_label_binding=dict(path=str(official_path), SHA256=sha(official_path), explicit_qualified_known=explicit_known,
                                    explicit_qualified_zero=explicit_zero, unknown_preserved=unknown_outcomes, half_point_lines=half_points,
                                    contract='Explicit official_completions, target_parity and physical participation required; missing stats never filled from appearance.'),
        prediction_file_SHA256=prediction_bindings,
        evaluation_binding=dict(path=str(main_path), SHA256=sha(main_path)),
        code_SHA256=sha(Path(__file__)), products_verified=12, own_side_weekly_and_cumulative_comparisons=comparisons,
        aggregate_records=list(by_product.values()), own_decision_flip_results=flip_results,
        requested_expectations=expectations, failure_count=len(errors), failures=errors,
        new_fits=0, optimizer_calls=0, new_canonical_SCORES=0, new_NFL_games=0, network_reads=0,
        limits=['Same retained quote timing/main-alt limitations remain.', 'No original issuance or venue-settlement claim.',
                'C1 independent fit strict-parity failure remains separate; these checks grade the originally frozen outputs.'],
        resources=dict(CPU_seconds=time.process_time()-cpu, wall_seconds=time.monotonic()-start,
                       peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
    output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(status=report['status'], offers=len(offers), official_known=explicit_known,
                         explicit_zero=explicit_zero, comparisons=len(comparisons), flips=flip_results,
                         failure_count=len(errors), failures=errors, resource=report['resources']), indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
