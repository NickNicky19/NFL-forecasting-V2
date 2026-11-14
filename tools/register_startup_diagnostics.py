"""Register new startup splits and matched empirical-reference annotations.

Reads immutable aggregate scores only. No NFL fits, inference or loss replay.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/point-prop-diagnostic-20261031i/historical-startup/v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(include_current=False):
    sources = [BASE / str(year) / 'SCORES.json' for year in (2025, 2022, 2023, 2024)]
    if include_current:
        sources.append(BASE.parent / 'current-2026-v2/SCORES.json')
    if not all(path.exists() for path in sources):
        raise ValueError('Wait for each separately registered finite season wave')
    registry = ROOT / 'registries/RESULT_ARTIFACTS.json'
    items = json.loads(registry.read_text())
    manifest = []
    for source in sources:
        rows = json.loads(source.read_text())
        baseline = {}
        for index, row in enumerate(rows):
            product = 'event_probability' if row['target'] == 'anytime_td' else 'lower_median'
            if (row['fallback_view'] == 'FULL_SYSTEM'
                    and (row['procedure_id'] == 'empirical-player-history-control-v1'
                         or row['target'] == 'nick-chart-ppr-v1' and row['procedure_id'] == 'v2-qualified-partial-chart-direct-wave-v1:empirical')
                    and row['product_id'] == product):
                key = (row['target'], row['history_regime'], row['window_id'])
                assert key not in baseline
                baseline[key] = (index, row)
        annotations = []
        matched = 0
        for index, row in enumerate(rows):
            value = dict(status='UNESTABLISHED', reason='Own learned/fallback masks are not common across procedures; no unmatched baseline-relative claim.')
            key = (row['target'], row['history_regime'], row['window_id'])
            if row['fallback_view'] == 'FULL_SYSTEM' and key in baseline:
                peer_index, peer = baseline[key]
                metric = 'brier' if row['target'] == 'anytime_td' else 'mae'
                loss, reference = row.get(metric), peer.get(metric)
                if peer_index == index:
                    value['reason'] = 'Declared empirical reference itself; no independent self-comparison.'
                elif (row['n'] and row['n'] == peer['n']
                      and row['membership_sha256'] == peer['membership_sha256']
                      and row.get('source_outcome_index_sha256')
                      and row['source_outcome_index_sha256'] == peer.get('source_outcome_index_sha256')
                      and type(loss) in (float, int) and type(reference) in (float, int)
                      and math.isfinite(loss) and math.isfinite(reference)):
                    value = dict(status='PAIRED_RETAINED_ROWS', metric=metric, paired_n=row['n'],
                                 candidate_error=loss, comparator_error=reference,
                                 comparator_procedure_id=peer['procedure_id'],
                                 comparator_history_regime=peer['history_regime'],
                                 comparator_product_id=peer['product_id'],
                                 comparator_source_artifact=source.relative_to(ROOT).as_posix(),
                                 comparator_source_row_index=peer_index, comparator_record_id=peer['record_id'],
                                 membership_sha256=row['membership_sha256'],
                                 uncertainty=dict(status='NOT_RECOMPUTED_FROM_AGGREGATE_SOURCES',
                                                  reason='Exact aggregate mean difference on the same declared outcome mask; no new paired game/week interval computed.',
                                                  selection_limit='Exposed descriptive comparisons; not selection/multiplicity adjusted'),
                                 scope='Procedure-plus-information reference; empirical/current learners may use different registered feature memory. Not an isolated learner-effect estimate.')
                    matched += 1
                else:
                    value['reason'] = 'No identical nonempty supported outcome/membership mask with the declared empirical reference; no unpaired skill computed.'
            annotations.append(dict(source_row_index=index, comparison=value))
        path = source.with_name('INDEX_COMPARISON_ANNOTATIONS_V1.json')
        body = json.dumps(dict(source_score_sha256=sha(source), identity='source_row_index',
                               baseline_rule='Empirical same-history lower median; anytime-TD empirical event probability. FULL_SYSTEM exact masks only.',
                               rows=annotations), indent=2) + '\n'
        if path.exists() and path.read_text() != body:
            raise ValueError('Preserve previous startup comparison annotation')
        path.write_text(body)
        relative = source.relative_to(ROOT).as_posix()
        if not any(item['artifact'] == relative for item in items):
            items.append(dict(artifact=relative, state='SCORED', kind='historical_startup_split_of_completed_rolling_forecasts',
                              comparison_annotations=path.relative_to(ROOT).as_posix(),
                              version_note='New W1–4/W5–18 FULL/own-learned/fallback split; completed full-season fits reused. No new forecasts, fits or NFL observations. Current/revised source tier;2022 RECENT proxy and partial-chart limitations retained.'))
        manifest.append(dict(path=relative, sha256=sha(source), views=len(rows),
                             paired_fullsystem_reference_views=matched))
    registry.write_text(json.dumps(items, indent=2) + '\n')
    target = BASE / ('INDEX_REGISTRATION_RECEIPT_V2.json' if include_current else 'INDEX_REGISTRATION_RECEIPT.json')
    body = json.dumps(dict(state='SOURCE_BOUND_AGGREGATE_REGISTRATION_NO_NEW_LOSSES', sources=manifest,
                           total_new_startup_views=sum(item['views'] for item in manifest), new_fits=0, new_inference=0), indent=2) + '\n'
    if target.exists() and target.read_text() != body:
        raise ValueError('Preserve prior startup registration receipt')
    target.write_text(body)
    print(json.dumps(dict(sources=len(manifest), views=sum(item['views'] for item in manifest),
                          matched_fullsystem_references=sum(item['paired_fullsystem_reference_views'] for item in manifest))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--include-current', action='store_true')
    main(parser.parse_args().include_current)
