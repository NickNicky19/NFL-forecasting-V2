"""Separate NB special-function and own-side arithmetic verification."""
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
from scipy.special import betainc


def read(path):
    path = Path(path)
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--private-rows', type=Path, required=True)
    ap.add_argument('--source-bindings', type=Path, required=True)
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    root = here.parents[3]
    out = here / 'native-attempts'
    rows = read(args.private_rows)['rows']
    tables = read(out / 'TABLES_V1.json')
    checks = 0
    model_checks = 0
    max_error = 0.
    for row in rows:
        side = row['selected_side']
        if side in ['OVER', 'UNDER']:
            state = 'PUSH' if row['actual'] == row['line'] else 'WIN' if (row['actual'] > row['line']) == (side == 'OVER') else 'LOSS'
        else:
            state = 'ABSTAIN' if side == 'ABSTAIN' else 'UNAVAILABLE_FORECAST'
        assert row['status'] == state
        checks += 1
    predictions = {}
    for week in range(5, 10):
        path = root / f'reports/player-context-matchup-01/B/qb-wave-v1/predictions/2026-W{week:02}.json.gz' if week < 9 else out.parents[1] / 'modern-completion-extension/PREDICTIONS_2026_W09.json.gz'
        for r in read(path)['rows']:
            if r['method'] == 'COMMON_EXPOSURE' and r['target'] == 'pass_att':
                predictions[r['game_id'], r['player_id']] = r
    for row in rows:
        if row['model_key'] != 'COMMON_EXPOSURE':
            continue
        pred = predictions[row['game_id'], row['player_id']]
        mean, shape = pred['law']['mean'], pred['law']['shape']
        p = shape / (shape + mean)
        threshold = math.floor(row['line'])
        cdf = float(betainc(shape, threshold + 1, p))
        max_error = max(max_error, abs(cdf - row['probs']['under']))
        assert abs(cdf - row['probs']['under']) < 1e-12
        median = next(k for k in range(256) if float(betainc(shape, k + 1, p)) >= .5)
        assert median == pred['lower_median']
        assert abs(mean - pred['mean']) < 1e-12
        assert pred['latest_source_available'] < pred['feature_cutoff']
        model_checks += 1
    aggregate_checks = 0
    for table in tables:
        chosen = [r for r in rows if r['policy'] == table['policy']]
        if table['week_view'].isdigit():
            chosen = [r for r in chosen if r['week'] == int(table['week_view'])]
        elif table['week_view'] == 'DK_ONLY':
            chosen = [r for r in chosen if r['line_from'] == 'dk']
        assert len(chosen) == table['eligible']
        for side in ['OVER', 'UNDER', 'COMBINED']:
            pool = [r for r in chosen if r['selected_side'] in ['OVER', 'UNDER']] if side == 'COMBINED' else [r for r in chosen if r['selected_side'] == side]
            wins, losses = [sum(r['status'] == state for r in pool) for state in ['WIN', 'LOSS']]
            assert table[side]['decided'] == wins + losses
            assert table[side]['wins'] == (wins if wins + losses else None)
            assert table[side]['losses'] == (losses if wins + losses else None)
            assert table[side]['selected'] == len(pool)
            aggregate_checks += 4
        errors = [r['point'] - r['actual'] for r in chosen if r['point'] is not None]
        for name in ['MAE', 'MSE', 'bias']:
            expected = sum(abs(v) if name == 'MAE' else v * v if name == 'MSE' else v for v in errors) / len(errors) if errors else None
            actual = table['numerical'][name]
            assert expected == actual or (expected is not None and actual is not None and abs(expected - actual) < 1e-12)
            aggregate_checks += 1
    selected = [r for r in rows if r['policy'] == 'P2_STATISTICAL_LAW']
    reliability = []
    for low in [i / 10 for i in range(5, 10)]:
        chosen = [r for r in selected if low <= max(r['probs']['over'], r['probs']['under']) < low + .1 or low == .9 and max(r['probs']['over'], r['probs']['under']) == 1]
        if chosen:
            reliability.append(dict(lower=low, upper=round(low + .1, 1), n=len(chosen),
                                    predicted=sum(max(r['probs']['over'], r['probs']['under']) for r in chosen) / len(chosen),
                                    wins=sum(r['status'] == 'WIN' for r in chosen),
                                    accuracy=sum(r['status'] == 'WIN' for r in chosen) / len(chosen)))
    protocol = read(out / 'FROZEN_PROTOCOL_V1.json')
    assert protocol['source_code_sha256'] == sha(here / 'score_native_attempts_v1.py')
    source_paths = read(args.source_bindings)
    for binding in protocol['source_bindings']:
        assert sha(source_paths[str(binding['week'])]) == binding['sha256']
    # The row source hashes bind private outcomes/offers without exporting them.
    result = dict(id='B_NATIVE_ATT_INDEPENDENT_VERIFICATION_v1', state='PASS_WITH_STATED_SCOPE',
                  independent_manual_grades=checks, law_checks=model_checks,
                  independent_aggregate_checks=aggregate_checks,
                  max_nb_special_function_cdf_difference=max_error,
                  P2_selected_confidence_reliability=reliability,
                  P90='0 selections; N/A accuracy, not 90 percent achieved.',
                  source_labels=dict(collections.Counter(r['line_from'] for r in selected)),
                  source_hashes_verified=True,
                  checked='Separate manual side/grade/count and scipy.special beta-integral NB CDF vs finite recurrence. No author C grader used for reference calculation.',
                  limits=['No new raw official outcome, authentic source-vintage or quote-time verification.',
                          'Source-qualification evidence is the named root code receipt, not retained raw bookmaker response.',
                          'Native W5-W9 only; earlier annual panel is not unioned.',
                          'No new feature construction, fit, original issuance or admission.'],
                  new_HTTP=0, new_fits=0,
                  tables_sha256=sha(out / 'TABLES_V1.json'),
                  script_sha256=sha(__file__))
    target = out / 'INDEPENDENT_VERIFICATION_V1.json'
    if target.exists():
        raise FileExistsError(target)
    target.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['state', 'independent_manual_grades', 'law_checks', 'independent_aggregate_checks', 'max_nb_special_function_cdf_difference']}))


if __name__ == '__main__':
    main()
