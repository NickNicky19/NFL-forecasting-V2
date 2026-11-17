#!/usr/bin/env python3
"""Separately written retained-row verifier; no model/scoring imports or fits."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import resource
import statistics
import time

import numpy as np


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def packets(path):
    """Decode only an existing packet's rows in bounded chunks, independently."""
    decode = json.JSONDecoder()
    with gzip.open(path, 'rt') as f:
        buffer = ''
        while '"rows"' not in buffer:
            chunk = f.read(131072)
            if not chunk:
                raise ValueError('packet has no rows')
            buffer += chunk
        marker = buffer.index('"rows"')
        buffer = buffer[buffer.index('[', marker) + 1:]
        while True:
            buffer = buffer.lstrip(' \r\n\t,')
            if buffer.startswith(']'):
                return
            try:
                row, end = decode.raw_decode(buffer)
            except json.JSONDecodeError:
                chunk = f.read(131072)
                if not chunk:
                    raise ValueError('incomplete retained row')
                buffer += chunk
            else:
                if not isinstance(row, dict):
                    raise ValueError('nonobject retained row')
                yield row
                buffer = buffer[end:]


def model(spec):
    proc = spec['procedure_id']
    if proc == 'v2-qualified-partial-chart-direct-wave-v1:empirical':
        proc = 'empirical-player-history-control-v1'
    if proc.endswith(':common-feature-memory'):
        proc = proc[:-len(':common-feature-memory')]
    product = spec.get('product_id') or spec.get('product') or spec.get('objective')
    if product == 'empirical_mean':
        product = 'mean'
    return spec['target'], proc, spec['history_regime'], product


def number(x):
    if x in ('', None):
        return None
    result = float(x)
    assert math.isfinite(result)
    return result


def close(actual, expected, field):
    if actual is None or expected is None:
        assert actual is expected, field
    elif isinstance(expected, (int, float)):
        assert math.isclose(actual, expected, rel_tol=2e-10, abs_tol=2e-8), field
    else:
        assert actual == expected, field


def qtile(values, p):
    values = sorted(values)
    where = (len(values) - 1) * p
    lo = int(where)
    return values[lo] + (values[math.ceil(where)] - values[lo]) * (where - lo)


def check_scores(published, rows, side, spec, outer_n, membership, view):
    n = len(rows)
    errors = [row[side][0] - row[side][1] for row in rows]
    absolute = [abs(x) for x in errors]
    assert published['n'] == n
    assert published['forecast_rows'] == (outer_n if view == 'FULL_SYSTEM' else n)
    assert published['unique_games'] == len({row[0][0] for row in rows})
    assert published['evaluation_weeks'] == sorted({row[side][3] for row in rows})
    assert published['fallback_rows'] == sum(row[side][2] != 'none' for row in rows)
    assert published['membership_sha256'] == membership
    if n:
        mse = math.fsum(x * x for x in errors) / n
        metrics = dict(mae=math.fsum(absolute) / n, mse=mse, rmse=math.sqrt(mse),
                       bias=math.fsum(errors) / n, p90_abs=qtile(absolute, .9),
                       p95_abs=qtile(absolute, .95), max_abs=max(absolute))
        if spec['target'] == 'anytime_td':
            probabilities = [row[side][0] if row[side][1] else 1 - row[side][0] for row in rows]
            metrics.update(brier=mse, prevalence=math.fsum(row[side][1] for row in rows) / n,
                           log_loss='Infinity' if 0 in probabilities else math.fsum(-math.log(q) for q in probabilities) / n)
        for name, val in metrics.items():
            close(published[name], val, name)
    else:
        for field in ('mae', 'mse', 'rmse', 'bias'):
            assert published[field] is None
    grid = spec['target'] == 'nick-chart-ppr-v1' and spec['product_id'] == 'lower_median'
    if grid:
        # Retained chart medians/actuals must be exactly representable, never rounded.
        for row in rows:
            for x in (row[side][0], row[side][1]):
                z = Decimal(str(x)) * 50
                assert z == z.to_integral_value()
        tolerance_errors = [abs(Decimal(str(row[side][0])) - Decimal(str(row[side][1]))) for row in rows]
    else:
        tolerance_errors = absolute
    for name, counter in published['precision_counts'].items():
        if name == 'exact_rate':
            successes = sum(x == 0 for x in absolute)
        else:
            value = int(name.rsplit('_', 1)[1])
            successes = sum(x < value if '_lt_' in name else x <= value for x in tolerance_errors)
        assert counter['numerator'] == successes and counter['denominator'] == n, name
        close(counter['rate'], successes / n if n else None, name)
        close(published.get(name), successes / n if n else None, name)
    if 'CRPS' in published:
        close(published['CRPS'], math.fsum(row[side][4] for row in rows) / n if n else None, 'CRPS')


def check_pair(result, rows, metric):
    def loss(item):
        if metric == 'crps':
            return item[4]
        err = item[0] - item[1]
        return err * err if metric in ('mse', 'brier') else abs(err)
    a = [loss(row[1]) for row in rows]
    b = [loss(row[2]) for row in rows]
    n = len(rows)
    assert result['n'] == n
    assert result['week_clusters'] == len({row[1][3] for row in rows})
    assert result['game_clusters'] == len({row[0][0] for row in rows})
    if not n:
        assert result['status'] == 'NO_SUPPORTED_PAIRED_ROWS'
        return None
    assert all(math.isfinite(x) and x >= 0 for x in a + b)
    assert result['candidate_infinite_rows'] == result['comparator_infinite_rows'] == 0
    d = [x - y for x, y in zip(a, b)]
    delta = math.fsum(d) / n
    close(result['candidate_error'], math.fsum(a) / n, 'candidate error')
    close(result['comparator_error'], math.fsum(b) / n, 'comparator error')
    close(result['delta'], delta, 'paired delta')
    control = math.fsum(b) / n
    close(result['relative_error_change'], delta / control if control else None, 'relative delta')
    byweek, bygame = defaultdict(list), defaultdict(list)
    for row, diff in zip(rows, d):
        byweek[row[1][3]].append(diff)
        bygame[row[0][0]].append(diff)
    assert set(result['weekly_paired_sums_counts']) == {str(x) for x in byweek}
    for week, dd in byweek.items():
        check = result['weekly_paired_sums_counts'][str(week)]
        assert check['n'] == len(dd)
        close(check['loss_difference_sum'], math.fsum(dd), 'week sum')
    if len(byweek) < 8:
        assert result['week_interval'] is None
        assert result['week_interval_status'] == 'INSUFFICIENT_WEEK_CLUSTERS'
    else:
        weeks = sorted(byweek)
        draws = np.random.Generator(np.random.PCG64(1703)).integers(len(weeks), size=(500, len(weeks)))
        # Independent multiplicity vectors rather than indexing producer sum/count arrays.
        weights = np.asarray([np.bincount(dd, minlength=len(weeks)) for dd in draws])
        sums = np.asarray([math.fsum(byweek[w]) for w in weeks])
        counts = np.asarray([len(byweek[w]) for w in weeks])
        ratios = (weights @ sums) / (weights @ counts)
        interval = sorted(map(float, ratios))
        for i, p in enumerate((.025, .975)):
            close(result['week_interval'][i], qtile(interval, p), 'week interval')
    if len(bygame) >= 8:
        ss = math.fsum((math.fsum(dd) - len(dd) * delta) ** 2 for dd in bygame.values())
        se = math.sqrt(len(bygame) / (len(bygame) - 1) * ss) / n
        close(result['game_cluster_sensitivity_se'], se, 'game SE')
        close(result['game_normal95_sensitivity'][0], delta - 1.96 * se, 'game low')
        close(result['game_normal95_sensitivity'][1], delta + 1.96 * se, 'game high')
    return dict(better_rows=sum(x < 0 for x in d), worse_rows=sum(x > 0 for x in d), tied_rows=sum(x == 0 for x in d))


def check_season(protocol, root, private, year):
    public = root / str(year)
    receipt = json.loads((public / 'RUN_RECEIPT.json').read_bytes())
    assert receipt['protocol_sha256'] == sha(root / 'FROZEN_PROTOCOL.json')
    assert receipt['score_sha256'] == sha(public / 'SCORES.json')
    assert receipt['pair_sha256'] == sha(public / 'PAIRED_COMPARISONS.json')
    specs = {row['spec_id']: row for row in protocol['specs']}
    pairs = [row for row in protocol['pairs'] if row['season'] == year]
    needed = {model(specs[row[role]]) for row in pairs for role in ('candidate', 'comparator')}
    data = {key: {} for key in needed}
    scanned = 0
    for binding in next(x for x in protocol['sources'] if x['season'] == year)['members']:
        path = private / binding['member']
        assert path.stat().st_size == binding['bytes'] and sha(path) == binding['sha256']
        source = binding['source_id']
        stream = packets(path) if binding['kind'] == 'packet' else csv.DictReader(gzip.open(path, 'rt'))
        for raw in stream:
            scanned += 1
            if int(raw.get('season', year)) != year or raw.get('population') != 'primary':
                continue
            week = int(raw['week'])
            if not 1 <= week <= (7 if year == 2026 else 18):
                continue
            if source == 'empirical':
                raw['procedure_id'] = 'empirical-player-history-control-v1'
            if source == 'hgb':
                raw['procedure_id'] = 'hgb-direct-history-controls-v1:' + raw['objective']
            key = model(raw)
            if key not in needed or (year == 2025 and source == 'season' and 'qb-rb-specialization' in key[1]):
                continue
            query = tuple(raw[x] for x in ('game_id', 'player_id', 'target', 'population', 'position'))
            assert query not in data[key], 'duplicate exact query'
            distribution = raw.get('distribution_summary')
            if isinstance(distribution, str):
                distribution = json.loads(distribution) if distribution else None
            crps = number((distribution or {}).get('crps', raw.get('crps')))
            data[key][query] = (number(raw.get('prediction')), number(raw.get('actual')), raw['fallback'], week, crps)
    assert scanned == receipt['rows_scanned']
    assert sum(map(len, data.values())) == receipt['selected_recipe_query_rows']
    published_pairs = {row['comparison_id']: row for row in json.loads((public / 'PAIRED_COMPARISONS.json').read_bytes())}
    published_scores = {(row['comparison_id'], row['role']): row for row in json.loads((public / 'SCORES.json').read_bytes())}
    checked = []
    labels = {}
    for pair in pairs:
        left, right = (specs[pair[role]] for role in ('candidate', 'comparator'))
        aa, bb = data[model(left)], data[model(right)]
        assert set(aa) == set(bb)
        complete = []
        for query in sorted(aa):
            a, b = aa[query], bb[query]
            assert a[1] == b[1] and a[3] == b[3], 'label/time mismatch'
            if query in labels:
                assert labels[query] == a[1]
            labels[query] = a[1]
            if a[0] is not None and b[0] is not None and a[1] is not None:
                if pair['metric'] == 'crps':
                    assert a[4] is not None and b[4] is not None
                complete.append((query, a, b))
        for view in ('FULL_SYSTEM', 'COMMON_LEARNED', 'ANY_FALLBACK'):
            if view == 'FULL_SYSTEM':
                chosen = complete
            elif view == 'COMMON_LEARNED':
                chosen = [row for row in complete if row[1][2] == row[2][2] == 'none']
            else:
                chosen = [row for row in complete if row[1][2] != 'none' or row[2][2] != 'none']
            membership = hashlib.sha256(canonical([row[0] for row in chosen])).hexdigest()
            identity = pair['pair_id'] + ':' + view
            published = published_pairs[identity]
            assert published['membership_sha256'] == membership
            assert published['outer_rows'] == len(aa) and published['missing_rows'] == len(aa) - len(complete)
            assert published['fullsystem_n'] == len(complete)
            partitions = check_pair(published, chosen, pair['metric'])
            for role, side, spec in (('candidate', 1, left), ('comparator', 2, right)):
                check_scores(published_scores[identity, role], chosen, side, spec, len(aa), membership, view)
            if view == 'FULL_SYSTEM':
                close(published['candidate_error'], left['ranking_loss'], 'source candidate')
                close(published['comparator_error'], right['ranking_loss'], 'source comparator')
                assert published['n'] == left['n'] == right['n']
                checked.append(dict(pair_id=pair['pair_id'], target=pair['target'], product=pair['ranking_product'],
                                    purpose=pair['purpose'], candidate=left['procedure_id'], candidate_history=left['history_regime'],
                                    comparator=right['procedure_id'], comparator_history=right['history_regime'],
                                    n=published['n'], candidate_error=published['candidate_error'], comparator_error=published['comparator_error'],
                                    delta=published['delta'], week_interval=published['week_interval'], row_loss_partition=partitions))
        assert len(complete) == sum(row[1][2] == row[2][2] == 'none' for row in complete) + sum(row[1][2] != 'none' or row[2][2] != 'none' for row in complete)
    assert len(published_pairs) == len(pairs) * 3 and len(published_scores) == len(pairs) * 6
    return dict(season=year, pairs=len(pairs), independently_checked_pair_views=len(published_pairs),
                independently_checked_univariate_views=len(published_scores), source_rows_scanned=scanned,
                selected_recipe_query_rows=sum(map(len, data.values())), distinct_query_labels=len(labels),
                distinct_supported_query_labels=sum(x is not None for x in labels.values()),
                unique_games=len({x[0] for x in labels}), unique_weeks=len({v[3] for rows in data.values() for v in rows.values()}),
                source_bound_score_sha256=receipt['score_sha256'], source_bound_pairs_sha256=receipt['pair_sha256'],
                full_system_comparisons=checked)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-root', type=Path, required=True)
    parser.add_argument('--private-root', type=Path, required=True)
    parser.add_argument('--seasons', type=int, nargs='+', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    protocol = json.loads((args.public_root / 'FROZEN_PROTOCOL.json').read_bytes())
    results = []
    for year in args.seasons:
        checked = check_season(protocol, args.public_root, args.private_root, year)
        results.append(checked)
        print(json.dumps({k: checked[k] for k in ('season', 'independently_checked_pair_views', 'independently_checked_univariate_views', 'distinct_supported_query_labels')}), flush=True)
    report = dict(state='PASS_INDEPENDENT_RETAINED_NUMERICAL_JOINS_LOSSES_PARTITIONS_AND_UNCERTAINTY',
                  protocol_sha256=sha(args.public_root / 'FROZEN_PROTOCOL.json'), checked_at_utc=datetime.now(timezone.utc).isoformat(),
                  checked_seasons=results, new_fits=0, new_inference=0, new_forecasts=0, new_NFL_observations=0,
                  current2026_Week8_outcomes_read=0,
                  scope='Independent aggregation of retained eligible points/labels and retained row-CRPS summaries; not an independent raw NFL-label source or recomputation of every law/PMF. All exposed descriptive minima, not earlier-executable policy selection.',
                  limits=['2026 has seven week clusters, too few for the registered whole-week interval.',
                          '2022 RECENT is source-limited 2022 proxy, not a true 2021-plus-2022 comparison.',
                          'Missing exact prior-season D1/D2 recipes remain blocked/fit-required; no surrogate replacement.',
                          'Proper football CRPS/Brier does not establish offered-line probability or priced selection performance.'],
                  resources=dict(wall_seconds=time.monotonic() - started, peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024))
    with args.output.open('x') as f:
        json.dump(report, f, indent=2, allow_nan=False)
        f.write('\n')
    print(json.dumps(dict(state=report['state'], seasons=args.seasons, resources=report['resources'])))


if __name__ == '__main__':
    main()
