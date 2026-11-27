"""Audit canonical score-version selection without changing the audit index."""
import collections, hashlib, json, resource, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = 'reports/continuation-20261030c/'
CORRECTION = 'reports/continuation-20261030/chart-grid-precision-correction-v1/SCORES.json'
PARTIAL = BASE + 'season-2023-v2/SCORES.json'
CONTINUATION = BASE + 'season-2023-w17-w18-continuation-v1/SCORES.json'
COMPLETE = BASE + 'season-2023-complete-replay-v1/SCORES.json'
DIMENSIONS = ('record_id','procedure_id','history_regime','policy_id','target','population','product_id','week','season','position','fallback_view','cohort_id')
SEASON_DIMS = ('procedure_id','history_regime','policy_id','target','population','product_id','week','season','position','fallback_view')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def key(row, dimensions):
    return tuple(row.get(k) for k in dimensions)

def main():
    start, cpu = time.monotonic(), time.process_time()
    manifest = ROOT / BASE / 'results-index/INDEX_MANIFEST.json'
    m = json.loads(manifest.read_bytes())
    selected = {}; all_ids = set(); kinds = collections.Counter(); excluded = {}; sources = {}
    for part in m['shards']:
        path = ROOT / part['path']
        assert digest(path) == part['sha256'] and path.stat().st_size == part['bytes']
        for row in json.loads(path.read_bytes()):
            ident = row['test_id']; assert ident not in all_ids; all_ids.add(ident); kinds[row['kind']] += 1
            artifact = row['source_artifact']
            if artifact in (PARTIAL, CONTINUATION, COMPLETE, CORRECTION) or row.get('score_version_state') or row.get('accuracy_status') == 'superseded_float_chart_grid_precision':
                selected[ident] = row
            if row.get('score_version_state'):
                excluded[ident] = dict(test_id=ident, state=row['score_version_state'], source_artifact=artifact,
                    source_artifact_sha256=row['source_artifact_sha256'], replacement_test_id=row.get('replacement_test_id'))
    complete = {}
    for row in selected.values():
        if row['source_artifact'] == COMPLETE:
            k = key(row['source_aggregate_fields'], SEASON_DIMS); assert k not in complete; complete[k] = row
    component_counts = collections.Counter()
    for ident, row in selected.items():
        if row['source_artifact'] not in (PARTIAL, CONTINUATION): continue
        raw = row['source_aggregate_fields']; other = complete[key(raw, SEASON_DIMS)]
        same_dates = row['weeks'] == other['weeks']
        if same_dates:
            assert row['n'] == other['n'] and row['metrics'] == other['metrics']
            component_counts['identical_supported_dates_and_native_metrics'] += 1
        else:
            assert set(row['weeks']) <= set(other['weeks'])
            component_counts['narrower_component_dates_not_identical_aggregate'] += 1
        excluded[ident] = dict(test_id=ident, state='ARCHIVED_COMPONENT_SCORE_VERSION', source_artifact=row['source_artifact'],
            source_artifact_sha256=row['source_artifact_sha256'], preferred_complete_test_id=other['test_id'],
            relationship='SAME_SUPPORTED_DATES_AND_NATIVE_METRICS' if same_dates else 'NARROWER_TEMPORAL_COMPONENT_NOT_SAME_EVALUATION_POPULATION',
            original_weeks=row['weeks'], complete_weeks=other['weeks'])
    correction_rows = json.loads((ROOT / CORRECTION).read_bytes())
    targets = {(row['source_artifact'],key(row['source_aggregate_fields'],DIMENSIONS)):row for row in selected.values() if row.get('accuracy_status') == 'superseded_float_chart_grid_precision'}
    by_record = {row['source_record_id']:row for row in selected.values() if row['source_artifact'] == CORRECTION}
    assert len(targets) == len(correction_rows) == len(by_record) == 1007
    changed = 0
    for correction in correction_rows:
        artifact = correction['supersedes_score_artifact']; row = targets[artifact,key(correction['supersedes_source_identity'],DIMENSIONS)]
        replacement = by_record[correction['record_id']]
        assert row['source_artifact_sha256'] == correction['supersedes_source_sha256'] == digest(ROOT / artifact)
        assert row['n'] == replacement['n'] and row['primary_error'] == replacement['primary_error']
        changed += any(correction[k] != v for k,v in correction['original_float_precision'].items())
        excluded[row['test_id']] = dict(test_id=row['test_id'],state='SUPERSEDED_FLOAT_CHART_PRECISION_SCORE_VERSION',source_artifact=artifact,
            source_artifact_sha256=row['source_artifact_sha256'],replacement_test_id=replacement['test_id'],primary_error_unchanged=True)
    counts = collections.Counter(row['state'] for row in excluded.values())
    assert counts == {'SUPERSEDED_ORIGINAL_RECIPE_CONTINUITY':176,'INVALIDATED_REQUESTED_SHARED_MASK_REFERENCE_ALIAS':1844,
        'ARCHIVED_COMPONENT_SCORE_VERSION':17540,'SUPERSEDED_FLOAT_CHART_PRECISION_SCORE_VERSION':1007}
    assert changed == 478 and len(all_ids) == m['record_count'] == 145219
    mapping = dict(schema='independent-current-score-version-selection-recommendation-v1', audit_manifest=manifest.relative_to(ROOT).as_posix(),
        audit_manifest_sha256=digest(manifest), exclusion_rows=sorted(excluded.values(),key=lambda r:r['test_id']),
        semantics='Recommendation only. ALL_AUDIT retains every original record. Exclusions choose canonical score versions, not improved forecasts. No global cross-panel ranking is authorized.')
    output = HERE / 'CURRENT_SCORE_VERSION_EXCLUSIONS_RECOMMENDATION.json'; output.write_text(json.dumps(mapping,separators=(',',':'))+'\n')
    result = dict(state='PASS_CANONICAL_VERSION_EXCLUSION_RECOMMENDATION', audit_records=len(all_ids), audit_evaluation_views=len(all_ids)-kinds['software_verification'],
        software_receipts_separate=kinds['software_verification'], recommended_excluded_evaluation_views=len(excluded), exclusion_state_counts=dict(counts),
        recommended_current_canonical_evaluation_views=len(all_ids)-kinds['software_verification']-len(excluded), component_relationship_counts=dict(component_counts),
        corrected_chart_precision_views=1007,changed_chart_tolerance_views=changed, mapping_artifact=output.relative_to(ROOT).as_posix(), mapping_sha256=digest(output),
        audit_manifest_sha256=digest(manifest), limitations=['Current canonical means preferred score version, not operational readiness or deployment.',
            'Retain separately reported/unreproduced, original replay/provider, retrospective current-vintage and software tiers.',
            'Rank only identical evaluation populations, source labels, horizons, information policies and compatible output products; zero support and unavailable comparisons stay unestablished.',
            'The broader 2025 v2 artifact retains 6183 unaffected univariate records but 1844 requested shared-mask records remain invalid. Compact v3 has a different candidate-plus-two-control mask; no blanket repair.',
            'Archived 2023 partial and continuation results remain valid for their actual weeks. Complete replay is preferred; narrower ALL aggregates cannot be called identical full-season tests.'],
        new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0,
        resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
    (HERE/'CURRENT_SELECTION_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__ == '__main__': main()
