"""Independent arithmetic audit of A's public owner-local C point replay.

No football rows, author scorer or inference code are used. This cannot verify
the private offer-to-forecast join or reproduce row-resampled uncertainty.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path


def same(a, b):
    if a is None or b is None:
        assert a is b, (a, b)
    else:
        assert math.isclose(a, b, abs_tol=1e-11, rel_tol=1e-11), (a, b)


def audit(source, headline):
    body = source.read_bytes()
    data = json.loads(body)
    scores = data['scores']
    keys = [(r['procedure_id'], r['product'], r['source_panel'], str(r['week_view'])) for r in scores]
    assert len(keys) == len(set(keys)) == 96
    cells = dict(zip(keys, scores))
    side_partitions = constants = weekly = source_splits = numeric = 0
    counts = ('selected', 'wins', 'losses', 'decided')

    def count(r, field):
        return 0 if r[field] is None else r[field]

    def check(r):
        nonlocal side_partitions
        o, u, c = (r[k] for k in ('OVER', 'UNDER', 'COMBINED'))
        for name in counts:
            assert count(c, name) == count(o, name) + count(u, name)
        for v in (o, u, c):
            assert count(v, 'wins') + count(v, 'losses') == v['decided']
            same(v['rate'], v['wins'] / v['decided'] if v['decided'] else None)
        states = r['states']
        assert sum(states.values()) == r['eligible']
        assert states.get('WIN', 0) == count(c, 'wins')
        assert states.get('LOSS', 0) == count(c, 'losses')
        assert r['eligible'] == c['selected'] + r['unavailable'] + r['abstentions']
        assert c['selected'] == c['decided'] + states.get('UNKNOWN_PARTICIPATION', 0)
        same(r['coverage'], c['selected'] / r['eligible'] if r['eligible'] else None)
        side_partitions += 1

    for r in scores:
        check(r)
        for c in r['constants'].values():
            check(c)
            constants += 1
        n = r['numerical_on_same_offered_rows']
        assert n['scored'] == r['COMBINED']['decided']
        assert sum(x['rows'] for x in r['forecast_availability_by_outer_outcome']) == r['eligible']
        assert sum(r['outer_outcome_states_independent_of_forecast'].values()) == r['eligible']

    for (procedure, product, panel, week), r in cells.items():
        if week == 'ALL':
            children = [cells[procedure, product, panel, str(w)] for w in range(1, 8)]
            weekly += 1
            assert r['actual_scored_weeks'] == [int(x['week_view']) for x in children if x['COMBINED']['decided']]
            for name in ('eligible', 'unavailable', 'abstentions', 'fallback_outputs', 'learned_outputs'):
                assert r[name] == sum(x[name] for x in children)
            for side in ('OVER', 'UNDER', 'COMBINED'):
                for name in counts:
                    assert count(r[side], name) == sum(count(x[side], name) for x in children)
            parent_states = Counter(r['states'])
            child_states = sum((Counter(x['states']) for x in children), Counter())
            assert parent_states == child_states
            n = r['numerical_on_same_offered_rows']['scored']
            for metric in ('MAE', 'MSE', 'bias'):
                total = math.fsum(x['numerical_on_same_offered_rows'][metric] * x['numerical_on_same_offered_rows']['scored']
                                 for x in children if x['numerical_on_same_offered_rows']['scored'])
                same(r['numerical_on_same_offered_rows'][metric], total / n if n else None)
                numeric += 1
        if panel == 'ALL':
            children = [cells[procedure, product, p, week] for p in ('ANNUAL_NAMED_NJ', 'SITE_RECORDED_DK_JURISDICTION_UNKNOWN')]
            for name in ('eligible', 'unavailable', 'abstentions'):
                assert r[name] == sum(x[name] for x in children)
            for side in ('OVER', 'UNDER', 'COMBINED'):
                for name in counts:
                    assert count(r[side], name) == sum(count(x[side], name) for x in children)
            source_splits += 1

    headlines = list(csv.DictReader(headline.open()))
    assert len(headlines) == 4
    for h in headlines:
        r = cells[h['procedure'], h['product'], 'ALL', 'ALL']
        for side, prefix in (('OVER', 'Over'), ('UNDER', 'Under'), ('COMBINED', 'combined')):
            for key, field in (('wins', 'W'), ('losses', 'L'), ('decided', 'N')):
                assert int(h[f'{prefix}_{field}']) == r[side][key]
            same(float(h[f'{prefix}_rate']), r[side]['rate'])
        same(float(h['MAE_same_offered']), r['numerical_on_same_offered_rows']['MAE'])
        same(float(h['RMSE_same_offered']) ** 2, r['numerical_on_same_offered_rows']['MSE'])
        same(float(h['bias_same_offered']), r['numerical_on_same_offered_rows']['bias'])

    for p in data['paired']:
        assert p['common_decided'] == 667
        assert p['common_mask_sha256'] == 'b84a7cfca0df5449af90b7b747df536081f34ef5656d62920dc920c02873d3d4'
        l = cells[p['left'], p['product'], 'ALL', 'ALL']
        assert l['COMBINED']['wins'] == p['left_wins']
        if p['right'].startswith('ALWAYS_'):
            right = l['constants'][p['right'][7:]]
        else:
            right = cells[p['right'], p['product'], 'ALL', 'ALL']
        assert right['COMBINED']['wins'] == p['right_wins']
        assert p['win_change'] == p['left_wins'] - p['right_wins']

    return {
        'state': 'PASS_INDEPENDENT_PUBLIC_AGGREGATE_ARITHMETIC_ONLY',
        'source_sha256': hashlib.sha256(body).hexdigest(),
        'headline_sha256': hashlib.sha256(headline.read_bytes()).hexdigest(),
        'checked_score_cells': len(scores), 'checked_constant_cells': constants,
        'checked_side_partitions': side_partitions, 'weekly_cumulative_groups': weekly,
        'source_split_groups': source_splits, 'weighted_numerical_identities': numeric,
        'headline_rows': len(headlines), 'paired_arithmetic_cells': len(data['paired']),
        'coverage': {'eligible': 733, 'available': 678, 'unavailable': 55, 'decided': 667,
                     'selected_unknown': 11, 'outer_unknown': 66, 'games': 81, 'actual_weeks': list(range(1, 8))},
        'independent_private_join_or_mask_hash_reproduction': 'UNKNOWN_NO_PRIVATE_ROWS_AVAILABLE',
        'bootstrap_reproduction': 'NOT_EXECUTED_NO_PERMITTED_GAME_ROWS;reported_intervals_retained',
        'new_fits': 0, 'new_inference': 0, 'new_NFL_observations': 0,
        'new_C_admission': 'NOT_C_AUTHORITY',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--headline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.source, args.headline)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
