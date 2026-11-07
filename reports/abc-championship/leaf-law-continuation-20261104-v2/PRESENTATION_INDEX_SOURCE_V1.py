"""Bind new law scores to retained points and the existing paired-analysis index."""
import collections,csv,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import abc_b_c_bound_replay as a
def main(lawsource,oldprivate,out):
 scores=a.load(out/'SCORES.json');bases=a.load(out/'PROBABILITY_BASELINES.json');pairs=a.load(out/'PAIRED_CONTROLS.json');old=[]
 for v in ['v2','v3']:old+=a.load(ROOT/f'reports/abc-championship/continuation-20261103-{v}/SCORES.json')
 points={(r['procedure_id'],r['target']):r for r in old if r.get('week')=='ALL'and r.get('side')=='Combined'}
 previous=a.load(ROOT/'reports/abc-championship/continuation-20261103-v4/B_OWN_POOL_COMBINED_LEADERS.json');control={}
 for r in previous:control.setdefault(r['target'],r)
 raw=a.load(lawsource)['rows'];bylaw=collections.defaultdict(list);bypoint=collections.defaultdict(dict)
 for r in raw:bylaw[r['method_key'],r['target']].append(r)
 for f in ['B_OWNER_LOCAL_C_MATCHED_ROWS_V2.json.gz','B_OWNER_LOCAL_C_ADDITIONAL_ROWS_V3.json.gz']:
  for r in a.load(oldprivate/f)['rows']:
   key=(r['method_key'],r['target']);oldrow=bypoint[key].get(r['offer_id'])
   if oldrow:assert all(oldrow.get(k)==r.get(k)for k in ['prediction','selected_side','statistical_state'])
   bypoint[key][r['offer_id']]=r
 leaders=[];probability=[];sourcepairs=[]
 for target in ['pass_yd','rush_yd','rec','rec_yd']:
  rr=[r for r in scores if r['target']==target and r['week']=='ALL'];cc=[r for r in rr if r.get('side')=='Combined'];best=max(r['selection_metrics']['hit_rate']for r in cc)
  pp=min((r for r in rr if r['record_kind']=='prop_threshold_probability_evaluation'),key=lambda r:r['brier']);probability.append(dict(target=target,procedure_id=pp['procedure_id'],brier=pp['brier'],n=pp['n'],matched_baselines=[r for r in bases if r['target']==target and r['procedure_id']==pp['procedure_id']and r['week_view']=='ALL']))
  for r in cc:
   if r['selection_metrics']['hit_rate']!=best:continue
   name=r['procedure_id'];native=points[name.rsplit('::',1)[0]+'::lower_median',target];sides={v['side']:v for v in rr if v.get('procedure_id')==name and v.get('record_kind')=='prop_selection_evaluation'};cb=control[target];pool=bylaw[name,target];point=list(bypoint[cb['procedure_id'],target].values());assert point
   leader=dict(target=target,procedure_id=name,history=r['history_regime'],selection='P2_EXACT_LINE_CDF-v1',sides={s:dict(selected=v['forecast_rows'],wins=v['selection_metrics']['WIN'],losses=v['selection_metrics']['LOSS'],decided=v['n'],rate=v['selection_metrics']['hit_rate'])for s,v in sides.items()},eligible=r['selection_metrics']['selection_pool_count'],selected=r['forecast_rows'],unavailable=r['selection_metrics']['technical_unavailable'],unknown=r['selection_metrics']['status_counts']['UNKNOWN_PARTICIPATION'],fallback_issued=r['selection_metrics']['fallback_issued'],point_view=dict(procedure_id=native['procedure_id'],product='lower_median',mae=native['mae'],n=native['n'],source_artifact='RETAINED_PREVIOUS_POINT_SCORES_NOT_REFIT_OR_RESCORED'),strongest_previous_B_point=cb['procedure_id'],actual_weeks=[2,3],games=32,evidence_tier=a.TIER)
   for wk in ['ALL','2','3']:
    aa=[q for q in pool if wk=='ALL'or q['week']==int(wk)];bb=[q for q in point if wk=='ALL'or q['week']==int(wk)];pair=a.pair(aa,bb,target,name,cb['procedure_id'],wk,'NEW_P2_VS_PRIOR_EXPOSED_B_POINT_LEADER')
    u=pair['uncertainty'];sources=dict(procedure_id=name,comparator_procedure_id=cb['procedure_id'],product_id='actual_line_categorical_law',comparator_product_id=cb['product'],target=target,population='BPRIMARY_ON_C_ACTUAL_OFFER_BOARD',season=2026,history_regime=r['history_regime'],comparator_history_regime=cb['history'],policy_id='EXPOSED_LAW_LEADER_VS_PRIOR_POINT_LEADER_W'+wk,contrast=r['history_regime']+'_MINUS_'+cb['history'],fallback_view='full_system',metric='STATISTICAL_SELECTED_SIDE_LOSS_RATE',n=pair['common_decided'],candidate_error=u['candidate_error'],comparator_error=u['comparator_error'],delta=u['delta'],relative_error_change=u['relative_error_change'],uncertainty=u,actual_weeks=[2,3]if wk=='ALL'else[int(wk)],history_limit='Different complete procedures/products, exposed own-pool maxima; not isolated history/learner effect or earlier-executable selector.',candidate_wins=pair['candidate_wins'],comparator_wins=pair['control_wins']);sourcepairs.append(sources)
    if wk=='ALL':leader['matched_previous_B_point_pair']=pair
   leaders.append(leader)
 a.save(out/'LAW_OWN_POOL_LEADERS.json',leaders);a.save(out/'PROBABILITY_LEADERS.json',probability);a.save(out/'PAIRED_PRIOR_POINT_ANALYSIS.json',sourcepairs)
 # Append, never regenerate the retained paired analyses.
 pointer_path=ROOT/'registries/CURRENT_RESULTS_INDEX.json';pointer=a.load(pointer_path);previous_binding=pointer['derived_comparison_manifest'];prior=a.load(ROOT/previous_binding['path']);oldrecords=a.load(ROOT/prior['records_json']['path']);records=[];relative=str((out/'PAIRED_PRIOR_POINT_ANALYSIS.json').relative_to(ROOT));h=a.sha(ROOT/relative)
 for i,r in enumerate(sourcepairs):
  u=r['uncertainty'];identity=(r['procedure_id'],r['product_id'],r['target'],r['population'],r['season'],r['history_regime'],r['policy_id'],r['metric'],r['contrast'],r['fallback_view'],None,None,r['comparator_procedure_id'],r['comparator_history_regime']);q={k:None for k in oldrecords[0]}
  q.update(analysis_id='PAIR-'+hashlib.sha256(json.dumps([relative,identity],separators=(',',':')).encode()).hexdigest()[:20],kind='DERIVED_PAIRED_LOSS_ANALYSIS',state='PAIRED_LOSS_SCORED'if r['n']else'NO_SUPPORTED_PAIRED_ROWS',procedure_id=r['procedure_id'],product_id=r['product_id'],target=r['target'],population=r['population'],season=2026,history_regime=r['history_regime'],policy_id=r['policy_id'],contrast=r['contrast'],view=r['fallback_view'],metric=r['metric'],n=r['n'],candidate_error=r['candidate_error'],comparator_error=r['comparator_error'],absolute_error_change=r['delta'],relative_error_change=r['relative_error_change'],week_clusters=u['week_clusters'],week_interval=u['week_interval'],week_interval_status=u['week_interval_status'],game_cluster_se=u['game_cluster_sensitivity_se'],history_status=r['history_limit'],precision_status='No new native precision; retained point views remain linked.',source_artifact=relative,source_artifact_sha256=h,source_row_index=i,new_fits=0,new_forecasts=0,new_NFL_observations=0,candidate_history_regime=r['history_regime'],comparator_history_regime=r['comparator_history_regime'],comparator_procedure_id=r['comparator_procedure_id'],comparator_product_id=r['comparator_product_id']);records.append(q)
 merged=oldrecords+records;assert len({r['analysis_id']for r in merged})==len(merged);dest=out/'paired-analysis-index-v1';dest.mkdir(exist_ok=False);rp=dest/'PAIRED_ANALYSES.json';a.save(rp,merged);cp=dest/'PAIRED_ANALYSES.csv'
 with cp.open('w',newline='')as f:
  writer=csv.DictWriter(f,fieldnames=list(merged[0]));writer.writeheader();writer.writerows({k:json.dumps(v,separators=(',',':'))if isinstance(v,(dict,list))else v for k,v in r.items()}for r in merged)
 registry=a.load(ROOT/'registries/ANALYSIS_ARTIFACTS.json');assert registry==prior['inputs'];registry.append(dict(artifact=relative,sha256=h,rows=len(sourcepairs),state='DERIVED_PAIRED_ANALYSIS_SCORED_WITH_EMPTY_STATES_RETAINED',new_univariate_forecast_views=0));manifest=dict(prior,inputs=registry,record_count=len(merged),status_counts=dict(collections.Counter(r['state']for r in merged)),records_json=dict(path=str(rp.relative_to(ROOT)),sha256=a.sha(rp)),records_csv=dict(path=str(cp.relative_to(ROOT)),sha256=a.sha(cp)),previous_manifest=previous_binding,old_records_preserved=len(oldrecords),new_records=len(records));mp=dest/'ANALYSIS_MANIFEST.json';a.save(mp,manifest)
 (ROOT/'registries/ANALYSIS_ARTIFACTS.json').write_text(json.dumps(registry,indent=2)+'\n');pointer['derived_comparison_manifest']=dict(path=str(mp.relative_to(ROOT)),sha256=a.sha(mp));pointer_path.write_text(json.dumps(pointer,indent=2)+'\n');print(json.dumps(dict(leaders=len(leaders),new_pairs=len(records),prior_pairs_preserved=len(oldrecords))))
if __name__=='__main__':main(*map(Path,sys.argv[1:4]))
