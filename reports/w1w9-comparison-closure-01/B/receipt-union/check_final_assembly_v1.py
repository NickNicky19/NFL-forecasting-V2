#!/usr/bin/env python3
"""Check root assembly against separate saved-row/aggregate calculations."""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import numpy as np
from verify_final_union_v1 import load, sha, native_view, combine


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native-rows', required=True)
    parser.add_argument('--assembly-root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    here = Path(__file__).parent
    assembly = Path(args.assembly_root)
    native = load(args.native_rows)['rows']
    tables = load(assembly / 'TABLES.json')
    early = load(here / 'A84_PUBLIC_ARITHMETIC_AND_SCOPE_V1.json')['records']
    expectations = load(here / 'INDEPENDENT_E3_F2_NINE_WEEK_EXPECTATIONS_V1.json')['records']
    counts = collections.Counter()
    problems = []

    def check(expected, actual, label):
        counts['assertions'] += 1
        equal = abs(expected - actual) < 1e-10 if isinstance(expected, float) else expected == actual
        if not equal:
            problems.append({'label': label, 'expected': expected, 'actual': actual})

    def view(model, policy, week):
        matches = [r for r in tables if r['model_key'] == model and r['policy'] == policy
                   and str(r['week_view']) == str(week)]
        assert len(matches) == 1, (model, policy, week)
        return matches[0]

    def compare(expected, actual, label):
        counts['records_compared'] += 1
        for field in ['eligible', 'selected', 'decided']:
            check(expected[field], actual[field], label + '.' + field)
        check(expected['wins'], actual['COMBINED']['wins'], label + '.wins')
        check(expected['losses'], actual['COMBINED']['losses'], label + '.losses')
        for side in ['OVER', 'UNDER']:
            for index, field in enumerate(['wins', 'losses']):
                # Empty own-side pools remain N/A in canonical records.
                canonical = actual[side][field]
                if not actual[side]['decided'] and canonical is None:
                    canonical = 0
                check(expected[side][index], canonical, label + '.' + side + '.' + field)
        if expected['numerical']:
            for key in ['MAE', 'MSE', 'bias']:
                check(expected['numerical'][key], actual['numerical'][key], label + '.' + key)
        else:
            check(0, actual['numerical']['scored'], label + '.no_invented_point')
        for key in ['Brier', 'three_state_log_loss']:
            check(expected['probability'][key], actual['probability'][key], label + '.' + key)

    for expected in expectations:
        model, policy = expected['model_key'], expected['policy']
        key = 'ALL' if expected['sensitivity'] == 'PRIMARY' else 'ANNUAL_PLUS_NATIVE_DK_ONLY'
        canonical = view(model, policy, key)
        compare(expected, canonical, model + ':' + policy + ':' + key)
        check(list(range(1, 10)), canonical['actual_weeks'], 'actual_weeks')
        check(119, canonical['games'], 'games')
        if key == 'ALL':
            for week in expected['weekly']:
                compare(week, view(model, policy, week['week']), model + ':' + policy + ':' + str(week['week']))

    # Independently reconstruct FTN proper scores from early binary loss sums
    # plus native strict-binary events, rather than averaging source Briers blindly.
    for model in ['B0', 'B1', 'B2']:
        for output, policy in [('mean', 'P1_MEAN'), ('lower_median', 'P1_LOWER_MEDIAN'),
                               ('P2', 'P2_STATISTICAL_LAW')]:
            source = [r for r in early if r['candidate_id'] == 'B-FTN-BALL-QUALITY-COMPLETION-v1:' + model + '::' + output
                      and r['week_view'] != 'ALL']
            assert len(source) == 4
            transformed = [{'n': r['eligible'], 'week': int(r['week_view']),
                            'sides': {s: [r[s]['wins'] or 0, r[s]['losses'] or 0] for s in ['OVER', 'UNDER']},
                            'numerical': r['numerical'], 'probability': r['probability']}
                           for r in source]
            for dk_only, key in [(False, 'ALL'), (True, 'ANNUAL_PLUS_NATIVE_DK_ONLY')]:
                expected = combine(transformed + [native_view(native, model, policy, dk_only=dk_only)], output != 'P2')
                compare(expected, view(model, policy, key), model + ':' + policy + ':' + key)
            for r in transformed:
                expected = combine([r], output != 'P2')
                compare(expected, view(model, policy, r['week']), model + ':' + policy + ':' + str(r['week']))
            for week in range(5, 10):
                expected = combine([native_view(native, model, policy, week)], output != 'P2')
                compare(expected, view(model, policy, week), model + ':' + policy + ':' + str(week))

    primary = [r for r in tables if r['week_view'] == 'ALL' and r['model_key'] in ['B0', 'B1', 'B2', 'E3', 'F2']]
    commitments = primary[0]['source_part_commitments']
    for r in primary:
        check(commitments, r['source_part_commitments'], r['model_key'] + '.same_nine_masks')
        for key in ['unavailable', 'unknown', 'abstentions']:
            check(0, r[key], r['model_key'] + '.' + key)
    for pair in load(assembly / 'PAIRED_COMPARISONS.json'):
        blocks = pair['weekly_paired_sums_counts']
        check(list(range(1, 10)), [b['week'] for b in blocks], 'paired_actual_weeks')
        n = sum(b['n'] for b in blocks)
        check(n, pair['n'], 'paired_n')
        check(-sum(b['loss_difference_sum'] for b in blocks) / n,
              pair['accuracy_change'], 'paired_delta')
        generator = np.random.default_rng(1703)
        resampled = []
        for _ in range(500):
            sample = generator.integers(0, 9, 9)
            resampled.append(sum(blocks[i]['loss_difference_sum'] for i in sample) /
                             sum(blocks[i]['n'] for i in sample))
        lo, hi = map(float, np.quantile(resampled, [.025, .975]))
        for expected, actual in zip([lo, hi], pair['loss_difference_interval95']):
            check(expected, actual, 'paired_bootstrap')

    bindings = load(assembly / 'INPUT_BINDINGS_V1.json')
    root = assembly.parents[3]
    for name, expected in bindings['inputs'].items():
        check(expected, sha(root / name), 'root_input_hash:' + name)
    check(bindings['code_sha256'], sha(root / 'tools/assemble_w1w9_completion.py'), 'assembly_code_binding')
    result = {
        'id': 'B_INDEPENDENT_FINAL_UNION_CHECK_v1',
        'state': 'PASS_WITH_STATED_SCOPE' if not problems else 'FAIL',
        'counts': dict(counts), 'problems': problems,
        'assembly_hashes': {p.name: sha(p) for p in assembly.iterdir() if p.is_file()},
        'checked': ['E3/F2 own sides, weekly/cumulative numerical and probability loss arithmetic',
                    'B0/B1/B2 independent saved-row sides, grades, numerical errors and binary probability losses',
                    'Shared nine weekly masks and 226-opportunity primary board; 225-row native-Sleeper exclusion',
                    'Existing paired whole-week 500-draw seed-1703 calculation', 'Root input/code bindings'],
        'limits': ['No protected A rows, independent source clocks or model fits accessed.',
                   'Mask equality is verification of owner commitments, not independently inspected private membership.',
                   'E3=R0 alias relies on owner code/feature receipt.',
                   'No cross-source AUC, early multiclass Brier or pooled tail quantile invented.',
                   'Only named complete B products checked; unavailable later A controls remain partial.',
                   'PAIR scope is the supplied FTN contrast set; this is not independent E3/F2 row-disagreement recovery.',
                   'Tier-B actual-source diagnostics, not original issuance, ordinary-main proof or production admission.'],
        'new_source_fetches': 0, 'new_fits': 0, 'new_forecasts': 0, 'canonical_writes': 0,
        'script_sha256': sha(__file__),
    }
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'state': result['state'], **dict(counts), 'problems': problems[:4]}))


if __name__ == '__main__':
    main()
