"""Read-only independent replay of the five-control carry comparison.

No producer helper, refit, new prediction issuance or Week8 outcome read.
"""
import argparse
from collections import defaultdict
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'reports/continuation-20261030b/carry-strong-control-comparison-v1'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical(value): return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
def key(r): return tuple(r[k] for k in ('game_id', 'player_id', 'target', 'population'))
def decoded(path): return json.loads(gzip.decompress(path.read_bytes()))
def close(a, b):
    assert a is b or (a is not None and b is not None and math.isclose(a, b, rel_tol=1e-11, abs_tol=1e-11)), (a, b)


def verify(private):
    receipt = json.loads((PUBLIC / 'RUN_RECEIPT.json').read_text())
    file = private / 'carry-strong-control-comparison-v1/CARRY_CONTROL_ROWS.json.gz'
    assert sha(file) == receipt['private_rows_sha256']
    copied = decoded(file)['methods']
    copied = {name: {key(r): r for r in rows} for name, rows in copied.items()}
    sources = defaultdict(dict)
    source_hashes = {}
    for week in range(1, 8):
        for objective, name in [('absolute_error_point', 'collapsed_l1'), ('squared_error_mean', 'prior_best_mean')]:
            artifact = f'W{week:02d}-rush_att-H-MULTI-{objective}-FORECAST.json'
            metadata = ROOT / 'reports/continuation-20261029/hgb-history-v1' / artifact
            assert sha(metadata) == receipt['inputs'][artifact]['receipt_sha256']
            desc = json.loads(metadata.read_text())['packet']
            packet = private / 'hgb-history-v1' / desc['name']
            assert sha(packet) == desc['sha256'] == receipt['inputs'][artifact]['prediction_sha256']
            body = gzip.decompress(packet.read_bytes())
            assert hashlib.sha256(body).hexdigest() == desc['uncompressed_sha256']
            for r in json.loads(body)['rows']:
                assert int(r['week']) == week
                sources[name][key(r)] = r
            source_hashes[artifact] = sha(packet)
    selection = [
        ('empirical', 'empirical-history-diagnostic-v1/predictions.csv.gz', 'empirical_median'),
        ('role_ablation', 'count-ablation-wave-v1/PREDICTIONS_FLAT.csv.gz', 'primary_role_l1'),
        ('ordered_law', 'distribution-wave-v2/all-predictions.csv.gz', 'ordered_cdf_median'),
    ]
    for source_id, artifact, name in selection:
        path = private / artifact
        assert sha(path) == receipt['inputs'][source_id]['sha256']
        source_hashes[source_id] = sha(path)
        with gzip.open(path, 'rt', newline='') as handle:
            for r in csv.DictReader(handle):
                # Exclude future metadata before decoding any target/prediction value.
                if int(r['season']) != 2026 or int(r['week']) > 7 or r['target'] != 'rush_att' or r['history_regime'] != 'H-MULTI':
                    continue
                if name == 'empirical_median' and r['product'] != 'lower_median': continue
                if name == 'primary_role_l1' and r['procedure_id'] != 'v2-hgb-rush-att-qb-rb-specialization-v1:common-feature-memory': continue
                if name == 'ordered_cdf_median' and (r['family'] != 'ordered_leaf_cdf' or r['product_id'] != 'lower_median' or r['policy_id'] != 'H-MULTI-COMMON'): continue
                sources[name][key(r)] = r
    source_checks = 0
    reference = copied['prior_best_mean']
    for name, rows in copied.items():
        assert set(rows) == set(reference) == set(sources[name])
        assert len(rows) == 2394
        for ident, r in rows.items():
            original = sources[name][ident]
            for field in ('prediction', 'actual'):
                value = original.get(field)
                value = None if value in ('', None) else float(value)
                assert r[field] == value
                source_checks += 1
            for field in ('position', 'fallback', 'history_regime', 'population'):
                assert r[field] == original[field]
                source_checks += 1
            assert r['actual'] == reference[ident]['actual']
            assert r['position'] == reference[ident]['position']
    overlap = set.intersection(*[{k for k, r in rows.items() if r['fallback'] == 'none' and r['actual'] is not None and r['prediction'] is not None} for rows in copied.values()])
    checks = 0
    for score in json.loads((PUBLIC / 'SCORES.json').read_text()):
        name = score['record_id'].split(':')[1]
        view = score['fallback_view']
        rows = [r for k, r in copied[name].items() if r['population'] == score['population'] and
                (view == 'full_system' or view == 'own_learned_only' and r['fallback'] == 'none' or
                 view == 'fallback_only' and r['fallback'] != 'none' or view == 'all_five_learned_overlap' and k in overlap)]
        selected = [r for r in rows if r['actual'] is not None and r['prediction'] is not None]
        assert len(rows) == score['forecast_rows']
        assert len(selected) == score['n']
        assert sum(r['fallback'] != 'none' for r in rows) == score['fallback_rows']
        assert len({r['game_id'] for r in selected}) == score['unique_games']
        checks += 4
        errors = [r['prediction'] - r['actual'] for r in selected]
        for metric, values in [('mae', list(map(abs, errors))), ('bias', errors), ('mse', [e * e for e in errors])]:
            close(score[metric], math.fsum(values) / len(values) if values else None)
            checks += 1
        close(score['rmse'], math.sqrt(score['mse']) if errors else None)
        checks += 1
    contrasts = json.loads((PUBLIC / 'PAIRED_CONTRASTS.json').read_text())
    examples = {}
    for result in contrasts:
        new, old, view = result['new'], result['old'], result['view']
        keys = [k for k, r in reference.items() if r['population'] == result['population'] and r['actual'] is not None and
                (view == 'full_system' or view == 'all_five_learned_overlap' and k in overlap or
                 view == 'pair_learned_overlap' and copied[new][k]['fallback'] == copied[old][k]['fallback'] == 'none')]
        assert len(keys) == result['n']
        losses = [[abs(copied[method][k]['prediction'] - copied[method][k]['actual']) for k in keys] for method in (new, old)]
        delta = [a - b for a, b in zip(*losses)]
        averages = [math.fsum(v) / len(v) for v in losses]
        effect = math.fsum(delta) / len(delta)
        for metric, expected in [('new_mae', averages[0]), ('old_mae', averages[1]), ('paired_mae_difference', effect),
                                 ('relative_mae_improvement', -effect / averages[1] if averages[1] else None)]:
            close(result[metric], expected)
            checks += 1
        assert result['row_wins'] == sum(d < 0 for d in delta)
        assert result['row_losses'] == sum(d > 0 for d in delta)
        assert result['row_ties'] == sum(d == 0 for d in delta)
        bygame, byweek = defaultdict(list), defaultdict(list)
        for k, d in zip(keys, delta):
            bygame[k[0]].append(d)
            byweek[copied[new][k]['week']].append(d)
            if new == 'primary_role_l1' and old == 'prior_best_mean' and view == 'full_system' and result['population'] == 'primary':
                label = 'win' if d < 0 else 'loss' if d > 0 else 'tie'
                if label not in examples:
                    examples[label] = {'public_safe_id': hashlib.sha256(canonical(k)).hexdigest()[:16], 'candidate_abs_error': abs(copied[new][k]['prediction'] - copied[new][k]['actual']), 'strong_control_abs_error': abs(copied[old][k]['prediction'] - copied[old][k]['actual'])}
        g, n = len(bygame), len(keys)
        se = (sum((sum(v) - len(v) * effect) ** 2 for v in bygame.values()) * g / (g - 1)) ** .5 / n if g >= 8 else None
        close(result['game_cluster_sensitivity_se'], se)
        assert result['week_clusters'] == len(byweek)
        assert result['week_interval'] is None
        for w, values in byweek.items(): close(result['weekly_paired_deltas'][str(w)], sum(values) / len(values))
        membership = hashlib.sha256(canonical(sorted(keys))).hexdigest()
        assert result['scored_membership_sha256'] == membership
        checks += 8 + len(byweek)
    headline = [r for r in contrasts if r['new'] == 'primary_role_l1' and r['old'] == 'prior_best_mean' and r['view'] == 'full_system']
    return {'status': 'PASS', 'source_join_field_checks': source_checks, 'score_views': 40, 'paired_contrasts': len(contrasts), 'metric_and_pair_checks': checks,
            'common_queries_per_method': len(reference), 'primary_supported_n': 844, 'extended_supported_n': 1516,
            'headline_strong_comparator_results': headline, 'redacted_row_examples': examples,
            'code_sha256': sha(Path(__file__)), 'source_artifacts_sha256': source_hashes,
            'score_artifact_sha256': sha(PUBLIC / 'SCORES.json'), 'paired_artifact_sha256': sha(PUBLIC / 'PAIRED_CONTRASTS.json'),
            'interpretation': 'H-MULTI current-vintage participant diagnostic; not strongest-every-procedure claim. Positive relative_mae_improvement is the negative of relative error delta.',
            'new_fits': 0, 'new_forecasts': 0, 'week8_outcomes_read': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-root', required=True, type=Path)
    report = verify(parser.parse_args().private_root)
    Path(__file__).with_name('CARRY_STRONG_CONTROL_INDEPENDENT_REVIEW.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('source_artifacts_sha256', 'headline_strong_comparator_results')}))
