"""Append retained availability contrasts; preserve every prior analysis row."""
import collections
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

from tools.check_analysis_index_coverage import read_bound

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'reports/audit-remediation-20261105-v1/B'


def digest(body):
    return hashlib.sha256(body).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def compressed_binding(path, body):
    stored = gzip.compress(body, compresslevel=9, mtime=0)
    path.write_bytes(stored)
    return dict(path=str(path.relative_to(ROOT)), sha256=digest(stored),
                bytes=len(stored), compression='gzip', uncompressed_bytes=len(body),
                uncompressed_sha256=digest(body))


def main():
    pointer_path = ROOT / 'registries/CURRENT_RESULTS_INDEX.json'
    pointer = json.loads(pointer_path.read_bytes())
    previous = pointer['derived_comparison_manifest']
    prior = json.loads(read_bound(previous))
    old = json.loads(read_bound(prior['records_json']))
    relative = str((PACKAGE / 'availability-final-matched-v3/INDEX_BOUND_PAIRED_ANALYSIS.json').relative_to(ROOT))
    source_body = (ROOT / relative).read_bytes()
    source_hash = digest(source_body)
    source = json.loads(source_body)
    assert len(source) == 240
    registry_path = ROOT / 'registries/ANALYSIS_ARTIFACTS.json'
    registry = json.loads(registry_path.read_bytes())
    assert registry == prior['inputs']
    records = []
    for i, row in enumerate(source):
        u = row['uncertainty']
        identity = (row['procedure_id'], row['product_id'], row['target'], row['population'],
                    row['season'], row['history_regime'], row['policy_id'], row['metric'],
                    row['contrast'], row['fallback_view'], None, None,
                    row['comparator_procedure_id'], row['comparator_history_regime'])
        projected = {key: None for key in old[0]}
        projected.update(
            analysis_id='PAIR-' + digest(json.dumps([relative, identity], separators=(',', ':')).encode())[:20],
            kind='DERIVED_PAIRED_LOSS_ANALYSIS',
            state='PAIRED_LOSS_SCORED' if row['n'] else 'NO_SUPPORTED_PAIRED_ROWS',
            procedure_id=row['procedure_id'], product_id=row['product_id'], target=row['target'],
            population=row['population'], season=row['season'], history_regime=row['history_regime'],
            policy_id=row['policy_id'], contrast=row['contrast'], view=row['fallback_view'],
            metric=row['metric'], n=row['n'], candidate_error=row.get('candidate_error'),
            comparator_error=row.get('comparator_error'), absolute_error_change=row.get('delta'),
            relative_error_change=row.get('relative_error_change'),
            membership_sha256=row.get('membership_sha256'), week_clusters=u.get('week_clusters'),
            week_interval=u.get('week_interval'), week_interval_status=u.get('week_interval_status'),
            game_cluster_se=u.get('game_cluster_sensitivity_se'), history_status=row['history_limit'],
            precision_status='Native precision is separately bound; these paired views add no NFL observations.',
            source_artifact=relative, source_artifact_sha256=source_hash, source_row_index=i,
            new_fits=0, new_forecasts=0, new_NFL_observations=0,
            candidate_history_regime=row['history_regime'],
            comparator_history_regime=row['comparator_history_regime'],
            comparator_procedure_id=row['comparator_procedure_id'],
            comparator_product_id=row['comparator_product_id'])
        records.append(projected)
    merged = old + records
    assert merged[:len(old)] == old
    assert len({row['analysis_id'] for row in merged}) == len(merged)
    destination = PACKAGE / 'paired-analysis-index-v1'
    destination.mkdir(exist_ok=False)
    rb = compressed_binding(destination / 'PAIRED_ANALYSES.json.gz',
                            (json.dumps(merged, separators=(',', ':'), allow_nan=False) + '\n').encode())
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=list(merged[0]))
    writer.writeheader()
    for row in merged:
        writer.writerow({key: json.dumps(value, separators=(',', ':'), allow_nan=False)
                         if isinstance(value, (dict, list)) else value for key, value in row.items()})
    cb = compressed_binding(destination / 'PAIRED_ANALYSES.csv.gz', buffer.getvalue().encode())
    registry.append(dict(artifact=relative, sha256=source_hash, rows=len(source),
                         state='DERIVED_PAIRED_ANALYSIS_SCORED_WITH_EMPTY_STATES_RETAINED',
                         new_univariate_forecast_views=0))
    manifest = dict(prior, inputs=registry, record_count=len(merged),
                    status_counts=dict(collections.Counter(row['state'] for row in merged)),
                    records_json=rb, records_csv=cb, previous_manifest=previous,
                    old_records_preserved=len(old), new_records=len(records))
    mp = destination / 'ANALYSIS_MANIFEST.json'
    save(mp, manifest)
    save(registry_path, registry)
    pointer['derived_comparison_manifest'] = dict(path=str(mp.relative_to(ROOT)), sha256=digest(mp.read_bytes()))
    save(pointer_path, pointer)
    print(json.dumps(dict(old_records_preserved=len(old), new_pairs=len(records),
                          total=len(merged), new_NFL_observations=0)))


if __name__ == '__main__':
    main()
