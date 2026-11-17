"""Append four saved-row contrasts to the existing paired-analysis index."""
import collections,csv,hashlib,io,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 out=ROOT/'reports/abc-championship/continuation-20261103-v4';dest=out/'paired-analysis-index-v1';dest.mkdir(exist_ok=False)
 pointer_path=ROOT/'registries/CURRENT_RESULTS_INDEX.json';pointer=json.loads(pointer_path.read_bytes());previous=pointer['derived_comparison_manifest'];prior=json.loads((ROOT/previous['path']).read_bytes())
 oldbytes=(ROOT/prior['records_json']['path']).read_bytes();old=json.loads(oldbytes);records=[];sources=[];scores=[]
 for v in ['v2','v3','v4']:scores+=json.loads((ROOT/f'reports/abc-championship/continuation-20261103-{v}/SCORES.json').read_bytes())
 lookup={(r['procedure_id'],r['target']):r for r in scores if r.get('week')=='ALL'and r.get('side')=='Combined'}
 original=json.loads((out/'B_MATCHED_WINNER_NEXT_DISTINCT_SCORE_COMPARISONS.json').read_bytes())
 for pair in original:
  a=lookup[pair['procedure_id'],pair['target']];b=lookup[pair['control_id'],pair['target']];u=pair['uncertainty'];n=pair['common_decided'];assert a['n']==b['n']==n
  sources.append(dict(procedure_id=pair['procedure_id'],comparator_procedure_id=pair['control_id'],product_id=a['product_id'],comparator_product_id=b['product_id'],target=pair['target'],population='BPRIMARY_ON_C_ACTUAL_OFFER_BOARD',season=2026,history_regime=a['history_regime'],comparator_history_regime=b['history_regime'],policy_id='EXPOSED_OBSERVED_WINNER_VS_NEXT_DISTINCT_SCORE',contrast=a['history_regime']+'_MINUS_'+b['history_regime'],fallback_view='full_system',metric='STATISTICAL_SELECTED_SIDE_LOSS_RATE',n=n,candidate_error=u['candidate_error'],comparator_error=u['comparator_error'],delta=u['delta'],relative_error_change=u['relative_error_change'],uncertainty=u,actual_weeks=[2,3],history_limit='EXPOSED_DIFFERENT_PROCEDURE_COMPARISON_NOT_ISOLATED_HISTORY_EFFECT_OR_EARLIER_SELECTOR',candidate_wins=pair['candidate_wins'],comparator_wins=pair['control_wins'],top_ties=pair['all_top_ties']))
 source=out/'STRONGEST_B_PAIRED_ANALYSIS.json';source.write_text(json.dumps(sources,indent=2)+'\n');relative=str(source.relative_to(ROOT));source_sha=digest(source)
 for i,r in enumerate(sources):
  u=r['uncertainty'];identity=(r['procedure_id'],r['product_id'],r['target'],r['population'],r['season'],r['history_regime'],r['policy_id'],r['metric'],r['contrast'],r['fallback_view'],None,None,r['comparator_procedure_id'],r['comparator_history_regime'])
  q={k:None for k in old[0]};q.update(analysis_id='PAIR-'+hashlib.sha256(json.dumps([relative,identity],separators=(',',':')).encode()).hexdigest()[:20],kind='DERIVED_PAIRED_LOSS_ANALYSIS',state='PAIRED_LOSS_SCORED',procedure_id=r['procedure_id'],product_id=r['product_id'],target=r['target'],population=r['population'],season=2026,history_regime=r['history_regime'],policy_id=r['policy_id'],contrast=r['contrast'],view=r['fallback_view'],metric=r['metric'],n=r['n'],candidate_error=r['candidate_error'],comparator_error=r['comparator_error'],absolute_error_change=r['delta'],relative_error_change=r['relative_error_change'],week_clusters=u['week_clusters'],week_interval=u['week_interval'],week_interval_status=u['week_interval_status'],game_cluster_se=u['game_cluster_sensitivity_se'],history_status=r['history_limit'],precision_status='No newunivariateprecision; existingexactpoint/selectioncounts remainbound',source_artifact=relative,source_artifact_sha256=source_sha,source_row_index=i,new_fits=0,new_forecasts=0,new_NFL_observations=0,candidate_history_regime=r['history_regime'],comparator_history_regime=r['comparator_history_regime'],comparator_procedure_id=r['comparator_procedure_id'],comparator_product_id=r['comparator_product_id']);records.append(q)
 merged=old+records;assert len({r['analysis_id']for r in merged})==len(merged)
 recordpath=dest/'PAIRED_ANALYSES.json';recordpath.write_text(json.dumps(merged,separators=(',',':'))+'\n');csvpath=dest/'PAIRED_ANALYSES.csv'
 with csvpath.open('w',newline='')as f:
  writer=csv.DictWriter(f,fieldnames=list(merged[0]));writer.writeheader()
  for r in merged:writer.writerow({k:json.dumps(v,separators=(',',':'))if isinstance(v,(dict,list))else v for k,v in r.items()})
 registry=json.loads((ROOT/'registries/ANALYSIS_ARTIFACTS.json').read_bytes());assert registry==prior['inputs'];registry.append(dict(artifact=relative,sha256=source_sha,rows=4,state='DERIVED_PAIRED_ANALYSIS_SCORED_WITH_EMPTY_STATES_RETAINED',new_univariate_forecast_views=0))
 manifest=dict(prior,inputs=registry,record_count=len(merged),status_counts=dict(collections.Counter(r['state']for r in merged)),records_json=dict(path=str(recordpath.relative_to(ROOT)),sha256=digest(recordpath)),records_csv=dict(path=str(csvpath.relative_to(ROOT)),sha256=digest(csvpath)),previous_manifest=previous,old_records_preserved=len(old),new_records=4)
 mp=dest/'ANALYSIS_MANIFEST.json';mp.write_text(json.dumps(manifest,indent=2)+'\n');(ROOT/'registries/ANALYSIS_ARTIFACTS.json').write_text(json.dumps(registry,indent=2)+'\n');pointer['derived_comparison_manifest']=dict(path=str(mp.relative_to(ROOT)),sha256=digest(mp));pointer_path.write_text(json.dumps(pointer,indent=2)+'\n')
 print(json.dumps(dict(old_records_preserved=len(old),new_derived_comparisons=4,new_univariate_forecasts=0,new_NFL_observations=0)))
if __name__=='__main__':main()
