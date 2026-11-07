"""Preserve an internal diagonal check outside the scientific paired index."""
import collections,csv,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools.register_player_context_wave import BASE,read,save,sha,binding
from tools.check_analysis_index_coverage import read_bound,bound_comparison_histories

def main():
    ptr=ROOT/'registries/CURRENT_RESULTS_INDEX.json';pointer=read(ptr);failed_binding=pointer['derived_comparison_manifest'];failed=json.loads(read_bound(failed_binding));prior_binding=failed['previous_manifest'];prior=json.loads(read_bound(prior_binding));old=json.loads(read_bound(prior['records_json']))
    source=ROOT/BASE/'INDEX_BOUND_PAIRED_ANALYSIS.json';raw=read(source);kept=[];removed=[]
    for i,r in enumerate(raw):
        if r['procedure_id']==r['comparator_procedure_id']and r['product_id']==r['comparator_product_id']and r['history_regime']==r['comparator_history_regime']:
            if r['delta']!=0 or r['candidate_error']!=r['comparator_error']:raise ValueError('Nontrivial diagonal error')
            removed.append(dict(source_row_index=i,source_row=r,scope='Internal identical-method checksum, not a new scientific procedure comparison.'))
        else:
            bound_comparison_histories(r,r['contrast']);kept.append(dict(r,original_projection_row_index=i))
    assert len(removed)==1 and len(kept)==1130
    current=ROOT/BASE/'INDEX_BOUND_PAIRED_ANALYSIS_V2.json';save(current,kept);relative=str(current.relative_to(ROOT));source_hash=sha(current)
    previous_projected=json.loads(read_bound(failed['records_json']))[len(old):];by_original={i:r for i,r in enumerate(previous_projected)};projected=[]
    for i,r in enumerate(kept):
        z=dict(by_original[r['original_projection_row_index']]);z.update(source_artifact=relative,source_artifact_sha256=source_hash,source_row_index=i)
        # Source changed; retain original logical ID/provenance via an explicit link.
        z['analysis_id']='PAIR-'+__import__('hashlib').sha256(json.dumps([relative,i,z['analysis_id']],separators=(',',':')).encode()).hexdigest()[:20]
        projected.append(z)
    merged=old+projected;assert merged[:len(old)]==old
    dest=ROOT/BASE/'paired-analysis-index-v2';dest.mkdir(exist_ok=False)
    rb=binding(dest/'PAIRED_ANALYSES.json.gz',(json.dumps(merged,separators=(',',':'),allow_nan=False)+'\n').encode());buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(merged[0]));writer.writeheader()
    for r in merged:writer.writerow({k:json.dumps(v,separators=(',',':'))if isinstance(v,(dict,list))else v for k,v in r.items()})
    cb=binding(dest/'PAIRED_ANALYSES.csv.gz',buffer.getvalue().encode());registry=list(prior['inputs']);registry.append(dict(artifact=relative,sha256=source_hash,rows=len(kept),state='DERIVED_PAIRED_ANALYSIS_SCORED_WITH_EMPTY_STATES_RETAINED',new_univariate_forecast_views=0))
    manifest=dict(prior,inputs=registry,record_count=len(merged),status_counts=dict(collections.Counter(r['state']for r in merged)),records_json=rb,records_csv=cb,previous_manifest=prior_binding,old_records_preserved=len(old),new_records=len(projected),superseded_projection=failed_binding)
    mp=dest/'ANALYSIS_MANIFEST.json';save(mp,manifest);save(ROOT/'registries/ANALYSIS_ARTIFACTS.json',registry);pointer['derived_comparison_manifest']=dict(path=str(mp.relative_to(ROOT)),sha256=sha(mp));save(ptr,pointer)
    save(ROOT/BASE/'PAIRED_PROJECTION_CORRECTION_V2.json',dict(state='CURRENT_PROJECTION_CORRECTED_NO_NFL_SCORE_CHANGE',failed_check='Same-procedure/same-product diagonal is not an independent scientific contrast. Guard retained.',
        original_projection=failed_binding,original_source_sha256=sha(source),removed_from_current_projection=removed,current_projection=pointer['derived_comparison_manifest'],original_pair_sources_unchanged=True,
        numerical_scores_unchanged=True,original_predictions_unchanged=True,old19576pairs_preserved=True,current_new_scientific_comparisons=len(kept)))
    print(json.dumps(dict(old_pairs=len(old),new_pairs=len(projected),total=len(merged),internal_diagonal_checks_retained_outside_current_index=len(removed))))
if __name__=='__main__':main()
