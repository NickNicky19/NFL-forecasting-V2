"""Verify permanent-index metadata against previously checked diagnostic masks/losses."""
import argparse,collections,gzip,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;PUB=HERE.parent/'point-offer/v1'
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):
    if a is None or b is None:assert a is b
    else:assert math.isclose(a,b,abs_tol=1e-12,rel_tol=1e-12),(a,b)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--receipt',type=Path,default=HERE/'INDEX_METADATA_INDEPENDENT_REVIEW.json');a=ap.parse_args();scores=read(PUB/'SCORES.json');byid={r['record_id']:r for r in scores};base={r['source_row_index']:r for r in read(PUB/'CURRENT_REPORTING_ANNOTATIONS_I_V1.json')['rows']};ext=read(PUB/'CONTEXT_COVERAGE_EXTENSION_V2.json');contexts=collections.defaultdict(list)
    for r in ext:contexts[r['record_id']].append(r)
    private=a.private_root/'point-prop-diagnostic-20261031i-point-offer-v1/POINT_DIAGNOSTIC_ROWS.json.gz';assert sha(private)==read(PUB/'RUN_RECEIPT.json')['private_sha256'];own=collections.Counter()
    for r in json.loads(gzip.decompress(private.read_bytes()))['rows']:
        if not r.get('population_diagnostic')and r['admitted']:own[tuple(r['recipe'])]+=1
    points={(r['target'],r['procedure_id'],r['history_regime'],r['product_id'],r['membership_sha256']):r for r in scores if r['record_kind']=='forecast_evaluation_view'and r['horizon_id']=='RETAINED_DECISION_ELIGIBLE_KNOWN_TARGET_TIME'}
    reporting=read(PUB/'INDEX_REPORTING_ANNOTATIONS_I_V3.json');assert reporting['source_score_sha256']==sha(PUB/'SCORES.json');assert len(reporting['rows'])==258;coverage_rows=links=0
    for z in reporting['rows']:
        i=z['source_row_index'];r=scores[i]
        for k,v in base[i].items():assert z[k]==v
        if r['horizon_id']=='SAME_SAVED_KICKOFF_POPULATION_DIAGNOSTIC':assert 'diagnostic_context_coverage'not in z;continue
        key=tuple(r[k]for k in ['target','procedure_id','history_regime','product_id']);point=points[(*key,r['membership_sha256'])];rr=z['diagnostic_context_coverage'];assert len(rr)==len(contexts[point['record_id']]);coverage_rows+=1
        for c,e in zip(rr,contexts[point['record_id']]):
            assert c['context']==e['context']and c['same_mask_alias']==e['same_mask_alias'];assert c['point_source_record_id']==point['record_id'];assert(c['source_offer_universe'],c['source_available_points'],c['mask_points'],c['context_outer_opportunities'],c['scored_or_selected_n'])==(84,own[key],point['forecast_rows'],e['context_outer_opportunities'],r['n']);assert 0<=r['n']<=point['forecast_rows']<=own[key]<=84;close(c['fraction_of_source'],r['n']/84);close(c['fraction_of_context'],r['n']/e['context_outer_opportunities']if e['context_outer_opportunities']else None);links+=1
    assert coverage_rows==252
    pairs=read(PUB/'PAIRED_MAE_COMPARISONS.json');bindingfile=HERE/'PAIRED_MASK_BINDINGS_V1.json';bindings={r['paired_source_row_index']:r for r in read(bindingfile)['rows']};ann=read(PUB/'INDEX_COMPARISON_ANNOTATIONS_I_V2.json');assert ann['source_score_sha256']==sha(PUB/'SCORES.json');valid=reverse=0
    for z in ann['rows']:
        r=scores[z['source_row_index']];c=z['comparison']
        if c['status']=='UNESTABLISHED':continue
        assert c['status']=='PAIRED_RETAINED_ROWS'and c['metric']=='mae'and r['record_kind']=='forecast_evaluation_view';idx=c['paired_source_row_index'];p=pairs[idx];b=bindings[idx];assert c['paired_source_sha256']==sha(PUB/'PAIRED_MAE_COMPARISONS.json');assert c['exact_mask_binding_sha256']==sha(bindingfile);assert c['membership_sha256']==r['membership_sha256']==b['membership_sha256'];assert r['n']==c['paired_n']==p['n']==b['paired_n'];rev=r['record_id']==b['focal_source_record_id']and r['record_id']!=b['candidate_source_record_id'];assert r['record_id']==b['focal_source_record_id']if rev else r['record_id']==b['candidate_source_record_id'];expected=p['comparator_error']if rev else p['candidate_error'];comp=p['candidate_error']if rev else p['comparator_error'];close(r['mae'],expected);close(c['candidate_error'],expected);close(c['comparator_error'],comp);u=c['uncertainty'];sgn=-1 if rev else 1;close(u['delta'],sgn*p['delta']);close(u['relative_error_change'],sgn*p['delta']/comp if comp else None)
        for k in ['game_normal95_sensitivity','week_interval']:
            v=p.get(k);want=None if v is None else[-v[1],-v[0]]if rev else v
            if want is None:assert u.get(k)is None
            else:
                for a1,b1 in zip(u[k],want):close(a1,b1)
        recipe=p['candidate_recipe']if rev else p['comparator_recipe'];assert[c['comparator_procedure_id'],c['comparator_history_regime'],c['comparator_product_id']]==recipe;assert u['candidate_recipe']==(p['comparator_recipe']if rev else p['candidate_recipe'])and u['comparator_recipe']==recipe;reverse+=rev;valid+=1
    assert valid==51
    receipt=dict(state='PASS_PERMANENT_INDEX_DIAGNOSTIC_METADATA',source_score_sha256=sha(PUB/'SCORES.json'),reporting_projection_sha256=sha(PUB/'INDEX_REPORTING_ANNOTATIONS_I_V3.json'),comparison_projection_sha256=sha(PUB/'INDEX_COMPARISON_ANNOTATIONS_I_V2.json'),source_vintage_rows=258,offered_context_coverage_rows=coverage_rows,offered_context_coverage_links=links,broad_kickoff_views_excluded_from_offer_denominators=6,exact_MAE_comparison_annotations=valid,reverse_orientation_annotations=reverse,all_original_scores_unchanged=True,new_scores=0,new_fits=0,new_inference=0)
    with a.receipt.open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt))
if __name__=='__main__':main()
