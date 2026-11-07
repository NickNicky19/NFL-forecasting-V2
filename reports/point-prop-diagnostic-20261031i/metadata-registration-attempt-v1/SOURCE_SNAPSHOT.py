"""Bind retained I diagnostic comparisons to the existing public result index.

This metadata operation does not decode player rows or recalculate NFL losses.
"""
import copy
import hashlib
import json
import math
from pathlib import Path

from nfl_v2.comparison_reporting import error_change

ROOT = Path(__file__).resolve().parents[1]
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


def main():
    source = FOLDER / 'SCORES.json'
    rows = json.loads(source.read_text())
    pair_path = FOLDER / 'PAIRED_MAE_COMPARISONS.json'
    pairs = json.loads(pair_path.read_text())
    contexts = json.loads((FOLDER / 'CONTEXT_TO_DEDUPLICATED_SCORE.json').read_text())
    by_context = {}
    for context in contexts:
        by_context.setdefault(context['record_id'], set()).add(context['context'])
    numeric = [row for row in rows if row['record_kind'] == 'forecast_evaluation_view']
    annotations = []
    paired = 0
    for index, row in enumerate(rows):
        comparison = dict(status='UNESTABLISHED', reason=(
            'Selected-side counts are separate from paired MAE; do not attribute MAE differences to selection accuracy.'
            if row['record_kind'] == 'prop_selection_evaluation' else
            'Population-filter diagnostics are not paired model changes; inspect exact common-row contrasts separately.'))
        eligible = []
        if row['record_kind'] == 'forecast_evaluation_view':
            for pair_index, pair in enumerate(pairs):
                if pair['target'] != row['target'] or pair['context'] not in by_context.get(row['record_id'], set()):
                    continue
                forward = recipe(row) == pair['candidate_recipe']
                reverse = recipe(row) == pair['comparator_recipe'] and pair['candidate_recipe'][0] == 'SAVED_RAW_PROJECTION_DIRECTION_RETAINED_PRECISION'
                if not (forward or reverse) or pair['n'] != row['n']:
                    continue
                value = oriented(pair, reverse)
                if not math.isclose(value['candidate_error'], row['mae'], abs_tol=1e-12):
                    continue
                comp_recipe = value['comparator_recipe']
                peers = [peer for peer in numeric if peer['target'] == row['target'] and recipe(peer) == comp_recipe
                         and peer['n'] == row['n'] and peer['membership_sha256'] == row['membership_sha256']
                         and pair['context'] in by_context.get(peer['record_id'], set())
                         and math.isclose(peer['mae'], value['comparator_error'], abs_tol=1e-12)]
                if not peers:
                    raise ValueError('Paired comparison has no exact retained peer mask')
                eligible.append((pair['context'] != 'FOCAL_COMMON_FULL_SYSTEM', pair_index, value))
        if eligible:
            _, pair_index, value = min(eligible, key=lambda item: item[:2])
            comp = value['comparator_recipe']
            comparison = dict(status='PAIRED_RETAINED_ROWS', metric='mae', paired_n=row['n'],
                              candidate_error=row['mae'], comparator_error=value['comparator_error'],
                              comparator_procedure_id=comp[0], comparator_history_regime=comp[1],
                              comparator_product_id=comp[2], membership_sha256=row['membership_sha256'],
                              uncertainty=value, paired_source_artifact=pair_path.relative_to(ROOT).as_posix(),
                              paired_source_sha256=sha(pair_path), paired_source_row_index=pair_index,
                              comparator_display_rule='Focal procedure for other recipes; saved raw projection for focal. Earlier-declared roster; no outcome-dependent method selection.')
            paired += 1
        annotations.append(dict(source_row_index=index, comparison=comparison))
    path = FOLDER / 'INDEX_COMPARISON_ANNOTATIONS_I_V1.json'
    body = json.dumps(dict(source_score_sha256=sha(source), identity='source_row_index',
                           semantics='Exact retained paired MAE only; no new scores or source-row execution.', rows=annotations), indent=2) + '\n'
    if path.exists() and path.read_text() != body:
        raise ValueError('Preserve existing comparison metadata; choose a new version')
    path.write_text(body)
    registry = ROOT / 'registries/RESULT_ARTIFACTS.json'
    items = json.loads(registry.read_text())
    rel = source.relative_to(ROOT).as_posix()
    if not any(item['artifact'] == rel for item in items):
        items.append(dict(artifact=rel, state='SCORED', kind='matched_point_offer_diagnostic_saved_rows',
                          reporting_annotations=(FOLDER / 'CURRENT_REPORTING_ANNOTATIONS_I_V1.json').relative_to(ROOT).as_posix(),
                          comparison_annotations=path.relative_to(ROOT).as_posix(),
                          version_note='New MAE/bias/gap/population diagnostic on retained W5–7 points. 189 side metadata labels corrected and69 missing point vintages supplied by bound annotation; original258 source rows/losses preserved. No prediction changes, new fits, inference or captures.'))
        registry.write_text(json.dumps(items, indent=2) + '\n')
    print(json.dumps(dict(registered_source=rel, views=len(rows), exact_paired_MAE_annotations=paired,
                          nonpaired_views=len(rows)-paired, new_scientific_calculations=0)))


if __name__ == '__main__':
    main()
