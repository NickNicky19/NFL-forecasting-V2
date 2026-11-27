#!/usr/bin/env python3
"""Independent arithmetic expectations; no author scorer/model imports."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt') as handle:
            return json.load(handle)
    return json.loads(Path(path).read_text())


def nzero(value):
    return 0 if value is None or value == '' else int(value)


def early_view(row, family):
    if family == 'F2':
        return {
            'week': int(row['week']), 'n': int(row['eligible']),
            'sides': {side: [nzero(row[side]['wins']), nzero(row[side]['losses'])]
                      for side in ['OVER', 'UNDER']},
            'numerical': row['numerical'], 'probability': row['probability'],
            'mask': row['eligible_mask_sha256'],
        }
    return {
        'week': int(row['week_view']), 'n': int(row['eligible']),
        'sides': {side: [nzero(row[side.lower() + '_wins']),
                         nzero(row[side.lower() + '_losses'])]
                  for side in ['OVER', 'UNDER']},
        'numerical': {key: (float(row['numeric_' + key]) if row['numeric_' + key] else None)
                      for key in ['MAE', 'MSE', 'bias']},
        'probability': {key: float(row['law_' + key])
                        for key in ['Brier', 'three_state_log_loss']},
        'mask': row['eligible_mask_sha256'],
    }


def native_view(rows, model, policy, week=None, dk_only=False):
    selected = [row for row in rows if row['model_key'] == model
                and row['policy'] == policy
                and (week is None or int(row['week']) == week)
                and (not dk_only or row['line_from'] == 'dk')]
    sides = {'OVER': [0, 0], 'UNDER': [0, 0]}
    errors, binary_losses, log_losses = [], [], []
    for row in selected:
        assert row['available'] and not row['technical_unavailable']
        actual, line = row['actual'], row['line']
        assert actual is not None and math.isfinite(actual) and math.isfinite(line)
        assert row['appearance'] == 'PLAYED'
        probabilities = row['probs']
        assert all(value >= 0 and math.isfinite(value) for value in probabilities.values())
        assert abs(sum(probabilities.values()) - 1) < 1e-12
        if policy == 'P2_STATISTICAL_LAW':
            delta = probabilities['over'] - probabilities['under']
        else:
            delta = row['point'] - line
        side = 'OVER' if delta > 0 else 'UNDER' if delta < 0 else None
        assert side == row['selected_side'] and side is not None
        assert actual != line  # No realized pushes in this declared panel.
        win = (actual > line) == (side == 'OVER')
        assert row['status'] == ('WIN' if win else 'LOSS')
        sides[side][0 if win else 1] += 1
        binary_losses.append((probabilities['over'] - int(actual > line)) ** 2)
        event = 'over' if actual > line else 'under'
        log_losses.append(-math.log(probabilities[event]))
        if policy != 'P2_STATISTICAL_LAW':
            errors.append(row['point'] - actual)
    return {
        'n': len(selected), 'sides': sides,
        'numerical': None if not errors else {
            'MAE': sum(map(abs, errors)) / len(errors),
            'MSE': sum(value * value for value in errors) / len(errors),
            'bias': sum(errors) / len(errors)},
        'probability': {'Brier': sum(binary_losses) / len(selected),
                        'three_state_log_loss': sum(log_losses) / len(selected)},
    }


def combine(views, has_numeric):
    n = sum(view['n'] for view in views)
    sides = {side: [sum(view['sides'][side][index] for view in views)
                    for index in [0, 1]] for side in ['OVER', 'UNDER']}
    wins, losses = [sum(value[index] for value in sides.values()) for index in [0, 1]]
    assert wins + losses == n
    return {
        'eligible': n, 'selected': n, 'decided': n, 'wins': wins, 'losses': losses,
        'rate': wins / n, 'OVER': sides['OVER'], 'UNDER': sides['UNDER'],
        'numerical': None if not has_numeric else {
            key: sum(view['numerical'][key] * view['n'] for view in views) / n
            for key in ['MAE', 'MSE', 'bias']},
        'probability': {
            key: sum(view['probability'][key] * view['n'] for view in views) / n
            for key in ['Brier', 'three_state_log_loss']},
    }


def expectations(native_rows, receipt_dir):
    r0 = load(receipt_dir / 'EXISTING_R0_R3_EARLY_WEEKLY_VIEWS_V1.json')['rows']
    f2 = load(receipt_dir / 'EXISTING_F2_EARLY_WEEKLY_VIEWS_V1.json')['records']
    rows = load(native_rows)['rows']
    base = {(r['game_id'], r['player_id']): r for r in rows
            if r['model_key'] == 'B0' and r['policy'] == 'P1_MEAN'}
    assert len(base) == 142
    for row in rows:
        if row['model_key'] in ['E3', 'F2']:
            compare = base[(row['game_id'], row['player_id'])]
            for field in ['actual', 'line', 'appearance', 'season', 'week', 'line_from']:
                assert row[field] == compare[field]
    results = []
    for family, source_rows in [('E3', r0), ('F2', f2)]:
        for output, policy in [('mean', 'P1_MEAN'), ('lower_median', 'P1_LOWER_MEDIAN'),
                               ('P2', 'P2_STATISTICAL_LAW')]:
            raw_early = [r for r in source_rows if r['candidate_id'].endswith('::' + output)
                         and (family == 'F2' or ':R0::' in r['candidate_id'])]
            early = sorted([early_view(r, family) for r in raw_early], key=lambda r: r['week'])
            assert [v['week'] for v in early] == [1, 2, 3, 4]
            assert [v['n'] for v in early] == [10, 25, 26, 23]
            for dk_only in [False, True]:
                late = native_view(rows, family, policy, dk_only=dk_only)
                assert late['n'] == (141 if dk_only else 142)
                combined = combine(early + [late], output != 'P2')
                combined.update(model_key=family, output=output, policy=policy,
                                sensitivity='DK_ONLY' if dk_only else 'PRIMARY',
                                games=119, weeks=list(range(1, 10)),
                                weekly=[dict(week=view['week'], **combine([view], output != 'P2'))
                                        for view in early] + [
                                    dict(week=week, **combine([native_view(rows, family, policy, week, dk_only)],
                                                             output != 'P2'))
                                    for week in range(5, 10)])
                results.append(combined)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native-rows', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    here = Path(__file__).parent
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    result = {
        'id': 'B_INDEPENDENT_E3_F2_NINE_WEEK_EXPECTATIONS_v1',
        'state': 'INDEPENDENT_EXPECTATIONS_READY_FOR_CANONICAL_COMPARISON',
        'records': expectations(args.native_rows, here),
        'input_hashes': {
            'native_graded_rows': sha(args.native_rows),
            'early_R0_views': sha(here / 'EXISTING_R0_R3_EARLY_WEEKLY_VIEWS_V1.json'),
            'early_F2_views': sha(here / 'EXISTING_F2_EARLY_WEEKLY_VIEWS_V1.json')},
        'scope': 'Own-side and metric arithmetic; independently grades saved native row values. No author scorer imported.',
        'limits': ['A raw rows, clocks and fitted models remain owner-local.',
                   'E3=R0 procedure alias relies on executing owner feature/code receipt; not independent historical fit reproduction.',
                   'Binary strict-Over Brier only. Early three-state Brier and cross-source AUC remain unknown.',
                   'Tail quantiles are not aggregated from quantiles.',
                   'This does not add offers, NFL games, original issuance or release admission.'],
        'new_source_fetches': 0, 'new_fits': 0, 'canonical_writes': 0,
        'script_sha256': sha(__file__),
    }
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'state': result['state'], 'records': len(result['records'])}))


if __name__ == '__main__':
    main()
