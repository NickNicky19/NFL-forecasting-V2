"""Bind retained I diagnostic comparisons to the existing public result index.

This metadata operation does not decode player rows or recalculate NFL losses.
"""
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nfl_v2.comparison_reporting import error_change

FOLDER = ROOT / 'reports/point-prop-diagnostic-20261031i/point-offer/v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recipe(row):
    return [row['procedure_id'], row['history_regime'], row['product_id']]


def oriented(pair, reverse=False):
    value = copy.deepcopy(pair)
    if reverse:
        for stem in ('error', 'recipe', 'infinite_rows'):
            a, b = 'candidate_' + stem, 'comparator_' + stem
            value[a], value[b] = pair[b], pair[a]
        value['delta'] = -pair['delta']
        interval = pair.get('game_normal95_sensitivity')
        value['game_normal95_sensitivity'] = None if interval is None else [-interval[1], -interval[0]]
        interval = pair.get('week_interval')
        value['week_interval'] = None if interval is None else [-interval[1], -interval[0]]
        for week in value['weekly_paired_sums_counts'].values():
            week['loss_difference_sum'] = -week['loss_difference_sum']
    change = error_change(value['candidate_error'], value['comparator_error'])
    assert math.isclose(value['delta'], change['absolute_error_change'], abs_tol=1e-12)
    value['relative_error_change'] = change['relative_error_change']
    value['relative_error_missing_reason'] = change['relative_error_missing_reason']
    return value


def reporting_annotations(rows, source):
    original_path = FOLDER / 'CURRENT_REPORTING_ANNOTATIONS_I_V1.json'
    original = json.loads(original_path.read_text())
    assert original['source_score_sha256'] == sha(source)
    coverage_path = FOLDER / 'CONTEXT_COVERAGE_EXTENSION_V2.json'
    coverage = json.loads(coverage_path.read_text())
    by_id, full = {}, {}
    for context in coverage:
        if not context['context'].startswith(('OWN_DECISION_ELIGIBLE', 'FOCAL_COMMON')):
            continue
        by_id.setdefault(context['record_id'], []).append(context)
        key = (context['target'], context['procedure_id'], context['history_regime'], context['product_id'])
        if context['context'] == 'OWN_DECISION_ELIGIBLE_FULL_SYSTEM':
            assert key not in full
            full[key] = context
    points = [row for row in rows if row['record_id'] in by_id]
    result = copy.deepcopy(original)
    added = 0
    for addition in result['rows']:
        row = rows[addition['source_row_index']]
        assert row['record_id'] == addition['record_id']
        key = (row['target'], row['procedure_id'], row['history_regime'], row['product_id'])
        if row['record_kind'] == 'forecast_evaluation_view':
            if row['record_id'] not in by_id:
                continue  # Retrospective population views are not offer coverage.
            point = row
            selected = row['n']
        else:
            matches = [point for point in points if
                       (point['target'], point['procedure_id'], point['history_regime'], point['product_id']) == key
                       and point['membership_sha256'] == row['membership_sha256']]
            assert len(matches) == 1
            point = matches[0]
            selected = row['forecast_rows']
        own = full[key]
        source_outer = own['context_outer_opportunities']
        available = own['available_point_forecasts']
        contexts = []
        for context in by_id[point['record_id']]:
            outer = context['context_outer_opportunities']
            contexts.append(dict(
                context=context['context'], point_source_record_id=point['record_id'],
                source_offer_universe=source_outer, source_available_points=available,
                mask_points=point['n'], context_outer_opportunities=outer,
                scored_or_selected_n=selected,
                fraction_of_source=selected/source_outer if source_outer else None,
                fraction_of_context=selected/outer if outer else None,
                same_mask_alias=context['same_mask_alias'],
                source_scope='Registered diagnostic availability; missing points are not confidence abstentions.',
            ))
        addition['diagnostic_context_coverage'] = contexts
        added += 1
    result['coverage_metadata_sources'] = [dict(path=coverage_path.relative_to(ROOT).as_posix(), sha256=sha(coverage_path)),
                                            dict(path=original_path.relative_to(ROOT).as_posix(), sha256=sha(original_path))]
    result['semantics'] = 'Bound vintage corrections plus explicit complete-source and conditional-mask availability; unchanged points, outcomes and scores.'
    path = FOLDER / 'INDEX_REPORTING_ANNOTATIONS_I_V3.json'
    body = json.dumps(result, indent=2) + '\n'
    if path.exists() and path.read_text() != body:
        raise ValueError('Preserve prior diagnostic reporting annotation')
    path.write_text(body)
    return path, added


def main():
    source = FOLDER / 'SCORES.json'
    rows = json.loads(source.read_text())
    pair_path = FOLDER / 'PAIRED_MAE_COMPARISONS.json'
    pairs = json.loads(pair_path.read_text())
    mask_path = FOLDER.parent.parent / 'independent/PAIRED_MASK_BINDINGS_V1.json'
    masks = json.loads(mask_path.read_text())
    assert masks['source_score_sha256'] == sha(source) and masks['source_pair_sha256'] == sha(pair_path)
    assert len(masks['rows']) == len(pairs)
    for binding in masks['rows']:
        pair = pairs[binding['paired_source_row_index']]
        assert binding['paired_source_sha256'] == sha(pair_path)
        assert binding['paired_n'] == pair['n']
        for prefix, pair_key in (('candidate', 'candidate_recipe'), ('focal', 'comparator_recipe')):
            peer = rows[binding[prefix + '_source_row_index']]
            assert peer['record_id'] == binding[prefix + '_source_record_id']
            assert peer['membership_sha256'] == binding['membership_sha256']
            assert recipe(peer) == pair[pair_key] and peer['n'] == pair['n']
    annotations = []
    paired = 0
    for index, row in enumerate(rows):
        comparison = dict(status='UNESTABLISHED', reason=(
            'Selected-side counts are separate from paired MAE; do not attribute MAE differences to selection accuracy.'
            if row['record_kind'] == 'prop_selection_evaluation' else
            'No retained paired MAE contrast covers this entire scored mask. Population-filter and matched-subset views remain separate; do not compare unmatched totals.'))
        eligible = []
        if row['record_kind'] == 'forecast_evaluation_view':
            for binding in masks['rows']:
                pair_index = binding['paired_source_row_index']
                pair = pairs[pair_index]
                forward = binding['candidate_source_row_index'] == index
                reverse = binding['focal_source_row_index'] == index
                if not (forward or reverse):
                    continue
                value = oriented(pair, reverse)
                assert math.isclose(value['candidate_error'], row['mae'], abs_tol=1e-12)
                assert binding['membership_sha256'] == row['membership_sha256']
                comp_recipe = value['comparator_recipe']
                raw_priority = reverse and comp_recipe[0] != 'SAVED_RAW_PROJECTION_DIRECTION_RETAINED_PRECISION'
                eligible.append((raw_priority, pair['context'] != 'FOCAL_COMMON_FULL_SYSTEM', pair_index, value))
        if eligible:
            _, _, pair_index, value = min(eligible, key=lambda item: item[:3])
            comp = value['comparator_recipe']
            comparison = dict(status='PAIRED_RETAINED_ROWS', metric='mae', paired_n=row['n'],
                              candidate_error=row['mae'], comparator_error=value['comparator_error'],
                              comparator_procedure_id=comp[0], comparator_history_regime=comp[1],
                              comparator_product_id=comp[2], membership_sha256=row['membership_sha256'],
                              uncertainty=value, paired_source_artifact=pair_path.relative_to(ROOT).as_posix(),
                              paired_source_sha256=sha(pair_path), paired_source_row_index=pair_index,
                              exact_mask_binding_artifact=mask_path.relative_to(ROOT).as_posix(),
                              exact_mask_binding_sha256=sha(mask_path),
                              comparator_display_rule='Focal procedure for other recipes; prefer matched saved raw for focal, otherwise first retained exact-mask contrast. Full-system before learned-only. Display order uses identities, not errors; no method-selection policy.')
            paired += 1
        annotations.append(dict(source_row_index=index, comparison=comparison))
    path = FOLDER / 'INDEX_COMPARISON_ANNOTATIONS_I_V2.json'
    body = json.dumps(dict(source_score_sha256=sha(source), identity='source_row_index',
                           semantics='Exact retained paired MAE only; no new scores or source-row execution.', rows=annotations), indent=2) + '\n'
    if path.exists() and path.read_text() != body:
        raise ValueError('Preserve existing comparison metadata; choose a new version')
    path.write_text(body)
    reporting_path, context_views = reporting_annotations(rows, source)
    registry = ROOT / 'registries/RESULT_ARTIFACTS.json'
    items = json.loads(registry.read_text())
    rel = source.relative_to(ROOT).as_posix()
    if not any(item['artifact'] == rel for item in items):
        items.append(dict(artifact=rel, state='SCORED', kind='matched_point_offer_diagnostic_saved_rows',
                          reporting_annotations=reporting_path.relative_to(ROOT).as_posix(),
                          comparison_annotations=path.relative_to(ROOT).as_posix(),
                          version_note='New MAE/bias/gap/population diagnostic on retained W5–7 points. 189 side metadata labels corrected and69 missing point vintages supplied by bound annotation; original258 source rows/losses preserved. No prediction changes, new fits, inference or captures.'))
    else:
        item = next(item for item in items if item['artifact'] == rel)
        item['reporting_annotations'] = reporting_path.relative_to(ROOT).as_posix()
        item['comparison_annotations'] = path.relative_to(ROOT).as_posix()
    registry.write_text(json.dumps(items, indent=2) + '\n')
    print(json.dumps(dict(registered_source=rel, views=len(rows), exact_paired_MAE_annotations=paired,
                          nonpaired_views=len(rows)-paired, explicit_diagnostic_coverage_views=context_views,
                          new_scientific_calculations=0)))


if __name__ == '__main__':
    main()
