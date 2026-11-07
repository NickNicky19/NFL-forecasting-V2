"""Register retained improvement results and append their paired analyses.

This does not call a model, grader, calibrator or uncertainty estimator.
"""
import collections
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import abc_b_c_bound_replay as a

OUT = ROOT / 'reports/abc-predictive-improvement-01/b-intercept-v1'


def register_scores():
    path = ROOT / 'registries/RESULT_ARTIFACTS.json'
    registry = a.load(path)
    known = {r['artifact'] for r in registry}
    sources = []
    for p in sorted(OUT.glob('*SCORES.json')):
        relative = str(p.relative_to(ROOT))
        rows = a.load(p)
        assert rows and len({r['record_id'] for r in rows}) == len(rows)
        sources.append(dict(path=relative, sha256=a.sha(p), rows=len(rows)))
        if relative in known:
            continue
        item = dict(
            artifact=relative, state='SCORED',
            kind='bounded_earlier_only_probability_repair_or_bound_saved_row_reference',
            version_note='B-owned scalar probability repair and gates, actual-line '
            'retrospective policies on separate C W2-W3 and B W8 panels. Six '
            'calibrator fits; zero new football fits, inference or issuance. '
            'Current source/quote vintage limitations, failures and losses retained. '
            'New results not yet C-admitted. Views are not independent methods.')
        if p.name == 'SCORES.json':
            item['reporting_annotations'] = str(
                (OUT / 'INDEX_REPORTING_ANNOTATIONS.json').relative_to(ROOT))
        registry.append(item)
    path.write_text(json.dumps(registry, indent=2) + '\n')
    a.save(OUT / 'NEW_CANONICAL_SCORE_MANIFEST.json', dict(
        state='REGISTERED_APPEND_ONLY', sources=sources,
        views=sum(r['rows'] for r in sources),
        by_kind=dict(collections.Counter(
            row['record_kind'] for p in OUT.glob('*SCORES.json') for row in a.load(p))),
        predictions_unchanged_by_registration=True, new_grading_or_fits=0))


def paired_sources():
    sources = []
    for p in a.load(OUT / 'PAIRED_COMPARISONS.json'):
        u = p['uncertainty']
        base = 'B::ABC-PREDICTIVE-IMPROVEMENT-01-B-INTERCEPT-v1::' + p['target']
        comparator = base + '::B0' if p['control_id'] == 'UNCHANGED_B0' else base + '::' + p['control_id']
        ch = 'H-MULTI' if p['control_id'] == 'UNCHANGED_B0' else 'EARLIER_REFERENCE'
        sources.append(dict(
            target=p['target'], procedure_id=p['procedure_id'],
            comparator_procedure_id=comparator, product_id='exact_line_probability_product',
            comparator_product_id='exact_line_probability_product' if ch == 'H-MULTI'
            else 'constant_side_or_original_prior', population='COMMON_DECIDED_ACTUAL_OFFER_ROWS',
            season=2026, history_regime='H-MULTI', comparator_history_regime=ch,
            policy_id=p['scope'] + ':W' + p['week_view'], contrast='H-MULTI_MINUS_' + ch,
            fallback_view='full_system', metric='STATISTICAL_SELECTED_SIDE_LOSS_RATE',
            n=p['common_decided'], candidate_error=u.get('candidate_error'),
            comparator_error=u.get('comparator_error'), delta=u['delta'],
            relative_error_change=u['relative_error_change'], uncertainty=u,
            actual_weeks=[2, 3] if p['week_view'] == 'ALL' else [int(p['week_view'])],
            history_limit='Complete procedure/policy comparison; common selected '
            'subset where policies differ, not full-system coverage or pure history effect. '
            'Exposed research; insufficient week clusters. Own-pool differences separately retained.',
            candidate_wins=p['candidate_wins'], comparator_wins=p['control_wins']))
    for p in a.load(OUT / 'PAIRED_PROBABILITY_ANALYSIS.json'):
        u = p['uncertainty']
        sources.append(dict(
            target=p['target'], procedure_id=p['procedure_id'],
            comparator_procedure_id=p['comparator_procedure_id'],
            product_id='exact_line_probability_product', comparator_product_id='exact_line_probability_product',
            population='COMMON_DECIDED_ACTUAL_OFFER_ROWS', season=2026,
            history_regime='H-MULTI', comparator_history_regime='H-MULTI',
            policy_id='ALL_BRIER:W' + p['week'], contrast='H-MULTI_MINUS_H-MULTI',
            fallback_view='full_system', metric='HALF_MULTICLASS_BRIER', n=p['n'],
            candidate_error=u['candidate_error'], comparator_error=u['comparator_error'],
            delta=u['delta'], relative_error_change=u['relative_error_change'],
            uncertainty=u, membership_sha256=p['membership_sha256'],
            actual_weeks=[2, 3] if p['week'] == 'ALL' else [int(p['week'])],
            history_limit='Earlier-only intercept on unchanged exact-line baseline; '
            'exposed actual-offer comparison with source-vintage limits. '
            'Descriptive game sensitivity; not selection/multiplicity adjusted.'))
    a.save(OUT / 'INDEX_BOUND_PAIRED_ANALYSIS.json', sources)
    return sources


def append_pairs(sourcepairs):
    pointer_path = ROOT / 'registries/CURRENT_RESULTS_INDEX.json'
    pointer = a.load(pointer_path)
    previous = pointer['derived_comparison_manifest']
    prior = a.load(ROOT / previous['path'])
    old = a.load(ROOT / prior['records_json']['path'])
    source = OUT / 'INDEX_BOUND_PAIRED_ANALYSIS.json'
    relative, digest = str(source.relative_to(ROOT)), a.sha(source)
    records = []
    for i, r in enumerate(sourcepairs):
        u = r['uncertainty']
        q = {k: None for k in old[0]}
        q.update(
            analysis_id='PAIR-' + hashlib.sha256(json.dumps([relative, i], separators=(',', ':')).encode()).hexdigest()[:20],
            kind='DERIVED_PAIRED_LOSS_ANALYSIS',
            state='PAIRED_LOSS_SCORED' if r['n'] else 'NO_SUPPORTED_PAIRED_ROWS',
            procedure_id=r['procedure_id'], product_id=r['product_id'], target=r['target'],
            population=r['population'], season=2026, history_regime=r['history_regime'],
            policy_id=r['policy_id'], contrast=r['contrast'], view=r['fallback_view'],
            metric=r['metric'], n=r['n'], candidate_error=r['candidate_error'],
            comparator_error=r['comparator_error'], absolute_error_change=r['delta'],
            relative_error_change=r['relative_error_change'],
            membership_sha256=r.get('membership_sha256'),
            week_clusters=u['week_clusters'], week_interval=u['week_interval'],
            week_interval_status=u.get('week_interval_status'),
            game_cluster_se=u['game_cluster_sensitivity_se'], history_status=r['history_limit'],
            precision_status='Selection/proper comparisons; ancillary original mean separately typed.',
            source_artifact=relative, source_artifact_sha256=digest, source_row_index=i,
            new_fits=0, new_forecasts=0, new_NFL_observations=0,
            candidate_history_regime=r['history_regime'],
            comparator_history_regime=r['comparator_history_regime'],
            comparator_procedure_id=r['comparator_procedure_id'],
            comparator_product_id=r['comparator_product_id'])
        records.append(q)
    merged = old + records
    assert len({r['analysis_id'] for r in merged}) == len(merged)
    dest = OUT / 'paired-analysis-index-v1'
    dest.mkdir(exist_ok=False)
    rp, cp = dest / 'PAIRED_ANALYSES.json', dest / 'PAIRED_ANALYSES.csv'
    rp.write_text(json.dumps(merged, separators=(',', ':')) + '\n')
    with cp.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(merged[0]))
        writer.writeheader()
        writer.writerows({k: json.dumps(v, separators=(',', ':'))
                          if isinstance(v, (dict, list)) else v for k, v in r.items()}
                         for r in merged)
    registry = a.load(ROOT / 'registries/ANALYSIS_ARTIFACTS.json')
    assert registry == prior['inputs']
    registry.append(dict(artifact=relative, sha256=digest, rows=len(sourcepairs),
                         state='DERIVED_PAIRED_ANALYSIS_SCORED_WITH_EMPTY_STATES_RETAINED',
                         new_univariate_forecast_views=0))
    manifest = dict(prior, inputs=registry, record_count=len(merged),
                    status_counts=dict(collections.Counter(r['state'] for r in merged)),
                    records_json=dict(path=str(rp.relative_to(ROOT)), sha256=a.sha(rp)),
                    records_csv=dict(path=str(cp.relative_to(ROOT)), sha256=a.sha(cp)),
                    previous_manifest=previous, old_records_preserved=len(old), new_records=len(records))
    mp = dest / 'ANALYSIS_MANIFEST.json'
    a.save(mp, manifest)
    (ROOT / 'registries/ANALYSIS_ARTIFACTS.json').write_text(json.dumps(registry, indent=2) + '\n')
    pointer['derived_comparison_manifest'] = dict(path=str(mp.relative_to(ROOT)), sha256=a.sha(mp))
    pointer_path.write_text(json.dumps(pointer, indent=2) + '\n')
    print(json.dumps(dict(new_pairs=len(records), prior_pairs_preserved=len(old))))


if __name__ == '__main__':
    register_scores()
    append_pairs(paired_sources())
