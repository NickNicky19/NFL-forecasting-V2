"""Verify source-bound coverage and annotation projections without recomputing forecasts."""
import argparse, collections, functools, gzip, hashlib, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];H=Path(__file__).resolve().parent.parent;PRIVATE=None
def read(p):return json.loads(p.read_bytes())
@functools.lru_cache(maxsize=128)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
@functools.lru_cache(maxsize=5)
def src(path):return read(ROOT/path)
def close(a,b):
    if a is None or b is None:assert a is b,(a,b)
    else:assert math.isclose(a,b,abs_tol=1e-12,rel_tol=1e-12),(a,b)
def main():
    global PRIVATE
    parser=argparse.ArgumentParser();parser.add_argument('--private-root',type=Path,required=True);PRIVATE=parser.parse_args().private_root
    universe={}
    for week,d in [(5,'baselines-coverage-20261031h-source'),(6,'completion-20261031g-source'),(7,'completion-20261031g-source-w7')]:
        rows=json.loads(gzip.decompress((PRIVATE/d/f'FROZEN_W{week}_METADATA.json.gz').read_bytes()))['rows'];ct=collections.Counter(r['target']for r in rows)
        universe.update({(week,k):n for k,n in ct.items()})
    coverage={};coverage_arrays=[]
    for directory in ['reference-v2','w5-reference-v1','w5-w7-cumulative-v1']:
        folder=H/'probability'/directory;byid={r['record_id']:r for r in read(folder/'SCORES.json')};rr=read(folder/'MASK_AND_OUTER_COVERAGE.json');coverage_arrays.append((directory,len(rr)))
        for c in rr:
            r=byid[c['record_id']];assert r['reference_id']=='candidate' and r['fallback_view']=='FULL'
            outer=sum(universe[w,r['target']]for w in r['evaluation_weeks']);qualified=c.get('qualified_probability_and_outcome_mask',c.get('qualified_mask_n'));assert c['outer_source_offer_universe']==outer and qualified==r['n'];assert c['unavailable_law_rows']==outer-c['admitted_law_rows']
            close(c.get('qualified_probability_mask_coverage',c.get('coverage',c.get('probability_mask_coverage'))),r['n']/outer)
            proper=[]
            if directory!='w5-w7-cumulative-v1':
                for b in c['source_records']:
                    f=ROOT/b['source_artifact'];assert sha(f)==b['source_artifact_sha256'];s=src(b['source_artifact'])[b['source_row_index']];assert s['record_id']==b['record_id'];proper.append(s)
                admitted=sum(s.get('admitted_forecast_rows',s['n'])for s in proper);assert c['admitted_law_rows']==admitted and qualified==sum(s['n']for s in proper)
            else:
                subs=[]
                for b in r['source_records']:
                    f=ROOT/b['source_artifact'];assert sha(f)==b['source_artifact_sha256'];s=src(b['source_artifact'])[b['source_row_index']];assert s['record_id']==b['record_id'];subs.append(coverage[s['record_id']])
                assert c['admitted_law_rows']==sum(s['admitted_law_rows']for s in subs)
            assert c['admitted_law_rows']>=qualified
            missing=c.get('admitted_missing_or_unknown_outcome_rows',c.get('admitted_missing_or_unknown_outcome_rows',c.get('admitted_missing_or_unknown_outcomes')));assert missing==c['admitted_law_rows']-qualified
            coverage[r['record_id']]=c
    manifest=read(H/'REPORTING_ANNOTATION_MANIFEST.json');expected=collections.defaultdict(dict);annotations=0
    for b in manifest['inputs']:
        p=ROOT/b['path'];assert sha(p)==b['sha256'];rows=read(p);assert len(rows)==b['rows'];annotations+=len(rows)
        for r in rows:
            source=r['source_artifact'];p=ROOT/source;assert sha(p)==r['source_artifact_sha256'];key=r['source_row_index'];g=expected[source].setdefault(key,dict(source_row_index=key,record_id=r['record_id']));assert g['record_id']==r['record_id']
            for field in ('precision_counts','probability_scores'):
                if field in r:g[field]=r[field]
            skip=('source_artifact','source_artifact_sha256','source_row_index','record_id')
            if 'actual_source_fallback_count'in r:
                g['law_origin_counts']={k:v for k,v in r.items()if k not in skip};assert r['actual_source_eligible_count']==r['actual_source_fallback_count']+r['actual_source_learned_count'];assert r['actual_source_scored_eligible_count']==r['actual_source_scored_fallback_count']+r['actual_source_scored_learned_count'];close(r['actual_source_fallback_rate'],r['actual_source_fallback_count']/r['actual_source_eligible_count']if r['actual_source_eligible_count']else None)
            if 'admitted_rule_abstentions'in r:
                g['denominators']={k:v for k,v in r.items()if k not in skip};assert r['eligible_pool']==r['admitted_forecast_opportunities']+r['unavailable_forecast_opportunities'];assert r['admitted_forecast_opportunities']==r['selected_any_side_in_full_pool']+r['admitted_rule_abstentions']
    projected=0;outer_projected=0
    for b in manifest['bindings']:
        p=ROOT/b['projection'];assert sha(p)==b['sha256'];z=read(p);assert len(z['rows'])==b['rows'];source=b['source_artifact'];assert sha(ROOT/source)==z['source_score_sha256'];rows=src(source);indices=set()
        for r in z['rows']:
            idx=r['source_row_index'];assert idx not in indices;indices.add(idx);s=rows[idx];assert s['record_id']==r['record_id'];projected+=1
            for k,v in expected[source].get(idx,{}).items():assert r[k]==v
            if 'outer_offer_coverage'in r:
                c=r['outer_offer_coverage'];assert c['qualified_mask_n']==s['n'];assert 0<=c['qualified_mask_n']<=c['candidate_full_qualified_mask_n']<=c['matched_candidate_admitted_law_rows']<=c['outer_offer_universe'];assert c['outer_offer_universe']==sum(universe[w,s['target']]for w in s['evaluation_weeks']);close(c['mask_over_outer_offer_fraction'],s['n']/c['outer_offer_universe']);assert sha(ROOT/c['source_coverage_artifact'])==c['source_coverage_sha256'];outer_projected+=1
        assert set(expected[source])<=indices
    errors=[];comparisons=0
    for directory in ['reference-v2','w5-reference-v1','w5-w7-cumulative-v1']:
        folder=H/'probability'/directory;file=folder/'INDEX_REFERENCE_COMPARISON_ANNOTATIONS_V1.json';z=read(file);rows=read(folder/'SCORES.json');assert z['source_score_sha256']==sha(folder/'SCORES.json')
        for a in z['rows']:
            c=a['comparison'];r=rows[a['source_row_index']]
            if c['status']=='UNESTABLISHED':continue
            comparisons+=1;assert c['paired_n']==r['n'];close(c['candidate_error'],r['brier']);u=c['uncertainty'];close(u['delta'],c['candidate_error']-c['comparator_error']);expectedrel=u['delta']/c['comparator_error']if c['comparator_error']else None
            if expectedrel is not None and not math.isclose(u.get('relative_error_change'),expectedrel,abs_tol=1e-12,rel_tol=1e-12):
                errors.append(dict(artifact=file.relative_to(ROOT).as_posix(),source_row_index=a['source_row_index'],reference_id=r.get('reference_id'),retained_relative_error_change=u.get('relative_error_change'),correct_relative_error_change=expectedrel,candidate_error=c['candidate_error'],comparator_error=c['comparator_error']))
    report=dict(state='PASS_COVERAGE_AND_REPORTING_PROJECTION_WITH_REFERENCE_RELATIVE_METADATA_CORRECTION_REQUIRED',coverage_arrays=coverage_arrays,coverage_records=len(coverage),source_annotation_rows=annotations,reporting_projection_files=len(manifest['bindings']),reporting_rows=projected,outer_coverage_projected_rows=outer_projected,baseline_comparison_annotations=comparisons,reference_reversal_relative_error_metadata_issues=len(errors),first_issue=errors[:1],canonical_score_values_changed=False,new_fits=0,new_inference=0,new_grades=0)
    with (H/'independent/COVERAGE_AND_ANNOTATION_INDEPENDENT_REVIEW_V1.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report))
if __name__=='__main__':main()
