"""Append source-bound M2 views to the established indices; never score or fit.

Preparation is the default. Root calls --execute only after independent receipts
and final source arrays exist. Original score/pair rows and old index shards stay
immutable. The adapter supplies index field names, not different denominators.
"""
from __future__ import annotations
import argparse
import collections
import copy
import csv
import gzip
import hashlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nfl_v2.result_index import evaluation, validate_index
from tools import build_test_index_v3 as index
from tools.check_analysis_index_coverage import read_bound
from tools.register_w1w9_closure_20261114 import canonical as old_direction

BASE = Path('reports/targeted-accuracy-w1w9-01/B')
SOURCE = BASE / 'evaluation/SCORES.json'
PAIRS = BASE / 'evaluation/PAIRED_COMPARISONS_V1.json'
PROJECTION = BASE / 'INDEX_PROJECTION_V1.json.gz'
ORIGINAL_NEW_RECORDS = index.new_records


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    p = Path(path)
    body = p.read_bytes()
    return json.loads(gzip.decompress(body) if p.suffix == '.gz' else body)


def save(path, value, *, fresh=True):
    p = Path(path)
    if fresh and p.exists():
        raise FileExistsError(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    p.write_bytes(gzip.compress(body, compresslevel=9, mtime=0) if p.suffix == '.gz' else body)


def binding(path, body, *, path_key='path'):
    p = Path(path)
    if p.exists():
        raise FileExistsError(p)
    data = gzip.compress(body, compresslevel=9, mtime=0)
    p.write_bytes(data)
    return {path_key: str(p.relative_to(ROOT)), 'sha256': hashlib.sha256(data).hexdigest(),
            'bytes': len(data), 'compression': 'gzip', 'uncompressed_bytes': len(body),
            'uncompressed_sha256': hashlib.sha256(body).hexdigest()}


def fallback_count(row):
    if isinstance(row.get('attribution'), dict):
        counts = row['attribution']
        if set(counts) <= {'learned', 'fallback', 'unavailable'}:
            return counts.get('fallback', 0)
    states = row.get('fallback_states')
    if not isinstance(states, dict) or not states:
        return None
    if any(k in ('', 'None', 'null', 'UNKNOWN', None) or 'UNKNOWN' in str(k) for k in states):
        return None
    return sum(v for k, v in states.items() if k not in {'none', 'NONE', 'NOT_APPLICABLE', 'learned'})


def history_of(procedure, method='', explicit=None):
    if explicit:
        return explicit
    text = str(procedure) + ' ' + str(method)
    if 'strict-current-inputs' in text:
        return 'H-CURRENT-STRICT_2026'
    if 'RETAINED_C_E0_ENV' in text:
        return 'H-MULTI'
    if any(k in text for k in ('SAVED_RAW', 'SAVED_ADJUSTED', 'ORIGINAL_SOURCE_LEAN')):
        return 'UNKNOWN_ARCHIVED_SOURCE_PROCEDURE'
    if any(k in text for k in ('ALWAYS_OVER', 'ALWAYS_UNDER')):
        return 'NOT_APPLICABLE_CONSTANT_CONTROL'
    return 'H-RECENT_ORIGIN_RECIPE_BOUND'


def common(row):
    weeks = row.get('actual_weeks', row.get('weeks', []))
    season = row.get('season', 2026)
    return dict(record_id=row['record_id'], procedure_id=row['procedure_id'],
                target=row.get('target', row.get('category')), season=season,
                week=row.get('week_view', row.get('window', 'ALL')),
                evaluation_seasons=[season], evaluation_weeks=weeks,
                evaluation_panel_id=row['evaluation_panel_id'], position='QB',
                history_regime=history_of(row['procedure_id'], row.get('method', ''), row.get('history_regime')),
                evidence=row.get('evidence_tier', row.get('evidence', 'UNKNOWN')),
                source_vintage=row.get('source_vintage', 'CURRENT_VINTAGE_CHRONOLOGICAL_RECONSTRUCTION'),
                forecast_rows=row.get('eligible'), unique_games=row.get('games'),
                fallback_rows=fallback_count(row), uncertainty=row.get('uncertainty'),
                primary_admission=row.get('primary_admission', 'LOCAL_NOT_C_ADMITTED'))


def direction(row):
    r = copy.deepcopy(row)
    r.setdefault('model_key', r.get('method', r['procedure_id']))
    r.setdefault('week_view', r.get('window', 'ALL'))
    projected = old_direction(r)
    projected.update(common(r))
    projected['product_id'] = r.get('product_id', r['policy'])
    projected['population'] = r.get('population', 'FIXED_RETAINED_QB_ACTUAL_SOURCE_LINE_PANEL_NOT_EXANTE_ROSTER')
    stats = projected['selection_metrics']
    stats['fallback_issued'] = fallback_count(r)
    stats['source_fallback_selected'] = r.get('fallback_selected')
    stats['source_component_fallback'] = r.get('component_fallback')
    stats['source_selected_probability'] = r.get('selected_probability')
    stats['source_full_board_probability'] = r.get('probability')
    projected['fallback_rows'] = stats['fallback_issued']
    projected['registered_weeks'] = r.get('scheduled_week_domain', r.get('actual_weeks', []))
    projected['registered_week_count'] = len(projected['registered_weeks'])
    projected['selected_week_count'] = len([n for n in r.get('selected_by_week', {}).values() if n])
    projected['unique_players'] = r.get('selected_unique_players')
    projected['unique_player_games'] = r.get('selected_unique_player_games', r.get('player_games'))
    projected['decided_unique_games'] = r.get('decided_unique_games')
    # Numerical quality on all admitted forecasts is not the selected-side
    # population when a selective rule chose fewer cases.
    numeric = r.get('numerical') or {}
    if numeric.get('scored') == projected['n'] and r['policy'] in {'MEAN', 'MEDIAN', 'P1_MEAN', 'P1_LOWER_MEDIAN'}:
        projected.update(mae=numeric.get('MAE'), mse=numeric.get('MSE'), bias=numeric.get('bias'))
    else:
        projected.update(mae=None, mse=None, bias=None)
    # Event-probability views are separate source records, so never borrow a
    # full-board Brier denominator for a smaller selected-side result.
    projected.update(brier=None, log_loss=None, nll=None)
    return projected


def numerical(row):
    numeric = row.get('numerical') or {}
    n = numeric.get('scored', row.get('n'))
    projected = common(row)
    projected.update(record_kind='forecast_evaluation_view',
                     product_id=row.get('product_id', str(row.get('output', 'POINT')).upper()),
                     population=row.get('population', 'RETROSPECTIVE_QB_STAT_ROW_NUMERICAL_PANEL_NOT_EXANTE_ROSTER'),
                     n=n, coverage=dict(offered_rows=row.get('eligible'), scored_rows=n,
                                        unavailable_forecasts=row.get('unavailable'), unknown_outcomes=row.get('unknown')),
                     mae=numeric.get('MAE'), mse=numeric.get('MSE'), bias=numeric.get('bias'),
                     p90_abs=numeric.get('absolute_error_p90'), p95_abs=numeric.get('absolute_error_p95'),
                     max_abs=numeric.get('max_absolute_error'),
                     brier=None, log_loss=None, nll=row.get('count_log_loss'),
                     infinite_NLL=row.get('infinite_count_logloss_cases'),
                     source_native_count_law_events=row.get('law_events'),
                     precision_counts=row.get('precision_counts'))
    if projected['mse'] is not None:
        projected['rmse'] = projected['mse'] ** .5
    return projected


def probability(row):
    projected = dict(row)
    projected.update(common(row))
    projected.update(record_kind='prop_threshold_probability_evaluation',
                     product_id=row.get('product_id', 'EXACT_EVENT_PROBABILITY:' + str(row.get('calibration_mode', 'RAW'))),
                     population=row.get('population', 'FIXED_RETAINED_QB_EXACT_LINE_PROBABILITY_EVENTS'),
                     n=row.get('n', row.get('probability_events')),
                     coverage=dict(offered_rows=row.get('eligible'), probability_events=row.get('n', row.get('probability_events'))),
                     mae=None, mse=None, bias=None)
    if projected.get('probability_conditioning') != 'MODELED_APPEARANCE':
        raise ValueError('Probability conditioning must be explicit')
    if projected.get('probability_score_contract') != 'HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1':
        raise ValueError('Probability score contract must be explicit')
    return projected


def canonical(row):
    kind = row.get('record_kind')
    if kind in {'actual_offer_direction_evaluation', 'prop_selection_evaluation'}:
        return direction(row) if kind != 'prop_selection_evaluation' else dict(row)
    if kind == 'prop_threshold_probability_evaluation':
        return probability(row)
    if kind == 'forecast_evaluation_view':
        return numerical(row)
    raise ValueError('Unsupported M2 source score kind: ' + str(kind))


def projected_records(root, item, inputs):
    path = item.get('targeted_m2_index_projection')
    if path is None:
        yield from ORIGINAL_NEW_RECORDS(root, item, inputs)
        return
    source_body = (root / item['artifact']).read_bytes()
    source = json.loads(source_body)
    projection = read(root / path)
    assert projection['source_artifact_sha256'] == hashlib.sha256(source_body).hexdigest()
    assert len(projection['rows']) == len(source)
    for i, (row, original) in enumerate(zip(projection['rows'], source)):
        assert row['record_id'] == original['record_id']
        record = evaluation(row, item['artifact'], year_record={k: row[k] for k in ['evaluation_seasons', 'evaluation_weeks']})
        record.update(source_artifact_sha256=projection['source_artifact_sha256'],
                      source_aggregate_fields=original, source_registry_kind=item['kind'],
                      source_version_note=item['version_note'],
                      source_bound_index_projection=dict(path=path, sha256=sha(root / path), source_row_index=i, no_regrading=True))
        validate_index([record])
        yield record
    inputs.append(dict(source_artifact=item['artifact'], sha256=projection['source_artifact_sha256'], rows=len(source), kind=item['kind']))
    inputs.append(dict(source_artifact=path, sha256=sha(root / path), rows=len(source), kind='SOURCE_BOUND_INDEX_PROJECTION_NO_NEW_EVALUATIONS'))


def normalize_pairs(rows):
    normalized = []
    source_sha = sha(ROOT / PAIRS)
    for i, row in enumerate(rows):
        r = dict(row)
        n = r['n']
        if n and any(r.get(k) is None for k in ['candidate_error', 'comparator_error', 'delta']):
            raise ValueError('Unsupported nonfinite pair must retain its explicit source scope before indexing')
        candidate = r['procedure_id']
        control = r['comparator_procedure_id']
        product = r.get('product_id', r['policy'])
        control_product = r.get('comparator_product_id', r.get('control_policy', product))
        control_error = r.get('comparator_error')
        relative = r['delta'] / control_error if n and control_error not in (None, 0) else None
        normalized.append(dict(r, procedure_id=candidate, comparator_procedure_id=control,
            product_id=product, comparator_product_id=control_product,
            population=r.get('population', 'EXACT_SOURCE_BOUND_COMMON_DECIDED_QB_TARGETED_M2_PANEL'),
            season=r.get('season', 2026), history_regime=history_of(candidate, r.get('candidate', ''), r.get('history_regime')),
            comparator_history_regime=history_of(control, r.get('control', ''), r.get('comparator_history_regime')),
            contrast=candidate + '_MINUS_' + control, metric=r['metric'],
            relative_error_change=relative, membership_sha256=r.get('membership_sha256', r.get('membership_SHA256')),
            cohort_id=r.get('cohort_id', r.get('scope', 'COMMON_DECIDED')),
            position='QB', policy_id=product, fallback_view=r.get('fallback_view', 'COMMON_DECIDED'),
            history_limit=r.get('history_limit', 'Current-vintage strict7day chronological M2 reconstruction, exposed development; exact source masks and parent/dispersion fallbacks retained. Not original issuance, authentic quote timing or private peer-fit parity.'),
            original_pair_source=str(PAIRS), original_pair_source_sha256=source_sha, original_pair_row_index=i))
    return normalized


def append_analysis(pointer, normalized):
    prior_binding = pointer['derived_comparison_manifest']
    prior = json.loads(read_bound(prior_binding))
    old = json.loads(read_bound(prior['records_json']))
    registry_path = ROOT / 'registries/ANALYSIS_ARTIFACTS.json'
    registry = read(registry_path)
    assert registry == prior['inputs']
    relative = BASE / 'INDEX_BOUND_PAIRED_ANALYSIS_V1.json.gz'
    save(ROOT / relative, normalized)
    encoded = (ROOT / relative).read_bytes()
    decoded = gzip.decompress(encoded)
    source_hash = hashlib.sha256(encoded).hexdigest()
    new = []
    for i, r in enumerate(normalized):
        z = {k: None for k in old[0]}
        z.update(analysis_id='PAIR-' + hashlib.sha256(json.dumps([str(relative), i, r['procedure_id'], r['comparator_procedure_id'], r['product_id'], r['cohort_id']], separators=(',', ':')).encode()).hexdigest()[:20],
                 kind='DERIVED_PAIRED_LOSS_ANALYSIS', state='PAIRED_LOSS_SCORED' if r['n'] else 'NO_SUPPORTED_PAIRED_ROWS',
                 procedure_id=r['procedure_id'], comparator_procedure_id=r['comparator_procedure_id'],
                 product_id=r['product_id'], comparator_product_id=r['comparator_product_id'],
                 target=r['target'], population=r['population'], season=r['season'],
                 history_regime=r['history_regime'], candidate_history_regime=r['history_regime'],
                 comparator_history_regime=r['comparator_history_regime'], policy_id=r['policy_id'],
                 contrast=r['contrast'], view=r['fallback_view'], cohort_id=r['cohort_id'], position='QB',
                 metric=r['metric'], n=r['n'], candidate_error=r.get('candidate_error'),
                 comparator_error=r.get('comparator_error'), absolute_error_change=r.get('delta'),
                 relative_error_change=r.get('relative_error_change'), membership_sha256=r.get('membership_sha256'),
                 week_clusters=r.get('week_clusters'), week_interval=r.get('week_interval'),
                 week_interval_status=r.get('week_interval_status'), game_cluster_se=r.get('game_cluster_sensitivity_se'),
                 history_status=r['history_limit'], precision_status='Exact source-native paired metric; no new NFL observations.',
                 source_artifact=str(relative), source_artifact_sha256=source_hash, source_row_index=i,
                 new_fits=0, new_forecasts=0, new_NFL_observations=0)
        new.append(z)
    merged = old + new
    assert len({r['analysis_id'] for r in merged}) == len(merged)
    dest = ROOT / BASE / 'paired-analysis-index-v1'
    dest.mkdir(exist_ok=False)
    rb = binding(dest / 'PAIRED_ANALYSES.json.gz', (json.dumps(merged, separators=(',', ':'), allow_nan=False) + '\n').encode())
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=list(merged[0]))
    writer.writeheader()
    for r in merged:
        writer.writerow({k: json.dumps(v, separators=(',', ':')) if isinstance(v, (dict, list)) else v for k, v in r.items()})
    cb = binding(dest / 'PAIRED_ANALYSES.csv.gz', output.getvalue().encode())
    registry.append(dict(artifact=str(relative), sha256=source_hash, bytes=len(encoded), compression='gzip',
                         uncompressed_bytes=len(decoded), uncompressed_sha256=hashlib.sha256(decoded).hexdigest(),
                         rows=len(normalized), state='DERIVED_PAIRED_ANALYSIS_SCORED_WITH_EMPTY_STATES_RETAINED', new_univariate_forecast_views=0))
    manifest = dict(prior, inputs=registry, record_count=len(merged),
                    status_counts=dict(collections.Counter(r['state'] for r in merged)),
                    records_json=rb, records_csv=cb, previous_manifest=prior_binding,
                    old_records_preserved=len(old), new_records=len(new))
    path = dest / 'ANALYSIS_MANIFEST.json'
    save(path, manifest)
    save(registry_path, registry, fresh=False)
    pointer['derived_comparison_manifest'] = dict(path=str(path.relative_to(ROOT)), sha256=sha(path))
    return len(new), len(old)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--verification', type=Path, action='append', default=[])
    parser.add_argument('--report', default=str(BASE / 'README.md'))
    args = parser.parse_args()
    if not (ROOT / SOURCE).exists():
        if args.execute:
            raise FileNotFoundError(SOURCE)
        print(json.dumps({'state': 'PREPARED_NO_CANONICAL_MUTATIONS', 'source_pending': str(SOURCE)}))
        return
    raw = read(ROOT / SOURCE)
    assert isinstance(raw, list) and len({r['record_id'] for r in raw}) == len(raw)
    projected = [canonical(r) for r in raw]
    for row in projected:
        validate_index([evaluation(row, str(SOURCE), year_record={k: row[k] for k in ['evaluation_seasons', 'evaluation_weeks']})])
    pairs = normalize_pairs(read(ROOT / PAIRS))
    if not args.execute:
        print(json.dumps({'state': 'PREPARED_VALIDATED_NO_CANONICAL_MUTATIONS', 'score_views': len(raw), 'pairs': len(pairs)}))
        return
    if not args.verification:
        raise ValueError('Root execution requires exact independent verification receipt(s)')
    for path in args.verification:
        receipt = read(path if path.is_absolute() else ROOT / path)
        state = str(receipt.get('state', receipt.get('status', '')))
        if 'PASS' not in state:
            raise ValueError('Independent verification not passed: ' + str(path))
    pointer_path = ROOT / 'registries/CURRENT_RESULTS_INDEX.json'
    pointer = read(pointer_path)
    previous = pointer['manifest']
    old_manifest = read(ROOT / previous)
    assert old_manifest['record_count'] >= 616035
    registry_path = ROOT / 'registries/RESULT_ARTIFACTS.json'
    registry = read(registry_path)
    assert not any(r['artifact'] == str(SOURCE) for r in registry)
    export_path = ROOT / 'reports/abc-championship/EXPORT_INDEX.json'
    old_export = export_path.read_bytes()
    assert len(json.loads(old_export)['exports']) >= 1849
    assert (ROOT / args.report).exists()
    # Validate all new views before the first canonical mutation.
    save(ROOT / PROJECTION, dict(source_artifact=str(SOURCE), source_artifact_sha256=sha(ROOT / SOURCE),
                                source_rows=len(raw), transformation='Field projection only; original arrays immutable, no regrading/fitting.', rows=projected))
    registry.append(dict(artifact=str(SOURCE), state='SCORED', kind='TARGETED_M2_COHERENT_CONVERSION_DISPERSION_AND_FIXED_SELECTION_EVALUATION',
                         targeted_m2_index_projection=str(PROJECTION),
                         version_note='QB coherent conversion-distribution experiment; broad W1-9 numerical and supported2025 robustness separate from native W5-9 actual-line diagnostics. Earlier7day current-vintage policy, quote-clock/main-alt unknown, exposed development. Own selection/fallback/proper-score denominators bound; no inherited roster expansion or production activation.'))
    save(registry_path, registry, fresh=False)
    index.new_records = projected_records
    out = str(BASE / 'results-index-v1')
    result = index.write(previous=previous, output=out, reuse_prior_csv=True, compressed_delivery=True)
    pointer['previous_checkpoint'] = previous
    pointer['manifest'] = out + '/INDEX_MANIFEST.json'
    pointer['readable_checkpoint'] = args.report
    added, prior_pairs = append_analysis(pointer, pairs)
    pointer['targeted_accuracy_m2_w1w9_01'] = dict(report=args.report, score_artifact=str(SOURCE),
        source_projection=str(PROJECTION), new_source_views=len(raw), new_pairs=added,
        scope='Separate targeted M2 version. Broader historical numerical panels do not fill absent early real-line scores. No C admission or original-site activation implied.')
    save(pointer_path, pointer, fresh=False)
    assert export_path.read_bytes() == old_export
    receipt = dict(state='APPENDED_SOURCE_BOUND_M2_SCORES_AND_PAIRS', source_artifact=str(SOURCE),
        source_sha256=sha(ROOT / SOURCE), new_source_score_views=len(raw), new_pairs=added,
        old_result_records_preserved=old_manifest['record_count'], old_pairs_preserved=prior_pairs,
        old_export_index_sha256=hashlib.sha256(old_export).hexdigest(), export_index_unchanged=True,
        prior_result_manifest=previous, current_result_manifest=pointer['manifest'],
        new_scoring=0, new_fits=0, new_NFL_observations=0, index=result,
        verification_receipts=[{'path': str(p), 'sha256': sha(p if p.is_absolute() else ROOT / p)} for p in args.verification])
    save(ROOT / BASE / 'REGISTRATION_RECEIPT_V1.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
