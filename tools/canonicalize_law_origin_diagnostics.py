"""Canonical source-bound full/learned/prior probability diagnostics."""
import argparse,hashlib,json,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import write,sha,now,canonical

def main(a):
 out=a.report/'fallback-diagnostic-v1'
 if out.exists():raise ValueError('fresh canonical diagnostic output required')
 out.mkdir();source=a.report/'COMPLETE_LEAF_FALLBACK_DECOMPOSITION.json';rows=json.loads(source.read_bytes());by={}
 for r in rows:by.setdefault((r['panel'],r['target'],r['procedure_id'],r['history_regime']),{})[r['view']]=r
 scores=[]
 for k,rr in sorted(by.items()):
  full,learned,prior=(rr[x]for x in('FULL_SYSTEM','LEARNED_LAW_ONLY','FALLBACK_LAW_ONLY'))
  if full['scored_law_rows']!=learned['scored_law_rows']+prior['scored_law_rows']:raise ValueError('laworigin n does not reconcile')
  if full['scored_law_rows']and not math.isclose(full['brier']*full['scored_law_rows'],sum((r['brier']or 0)*r['scored_law_rows']for r in(learned,prior)),abs_tol=1e-9):raise ValueError('laworigin loss sums do not reconcile')
  for view,r in rr.items():
   code={'FULL_SYSTEM':'FULL','LEARNED_LAW_ONLY':'LEARNED','FALLBACK_LAW_ONLY':'PRIOR'}[view];n=r['scored_law_rows'];panel,target,proc,h=k;scores.append(dict(record_id='LAW-ORIGIN-'+hashlib.sha256(canonical([k,code])).hexdigest()[:24],record_kind='prop_threshold_probability_evaluation',procedure_id=proc+':known-target-time-v1',history_regime=h,product_id='actual_line_categorical_law_origin_diagnostic',target=target,population='admitted_saved_law_opportunities',fallback_view=code,source_origin_view=view,season=2026,week=6 if panel=='W6'else 7,evaluation_seasons=[2026],evaluation_weeks=[6 if panel=='W6'else 7],evaluation_panel_id='v2-complete-leaf-origin-diagnostic:'+panel,period='full_game',n=n,forecast_rows=r['admitted_law_rows'],fallback_rows=r['admitted_law_rows']if code=='PRIOR'else 0 if code=='LEARNED'else prior['admitted_law_rows'],mae=None,mse=None,brier=r['brier'],log_loss=r['log_loss'],infinite_log_losses=r['infinite_log_losses'],probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',bookmaker_nonvoid_conditioning='UNESTABLISHED',source_artifact=source.relative_to(a.root).as_posix(),source_artifact_sha256=sha(source),evidence='DERIVED_FROM_ALREADY_SCORED_RETAINED_LAW_ROWS',selection_independent=True,diagnostic_only=True,null_reason=None if n else'NO_QUALIFIED_LAW_AND_ACTUAL_ROWS_OF_THIS_ORIGIN',new_NFL_observations=0))
 write(out/'SCORES.json',scores);write(out/'RUN_RECEIPT.json',dict(state='COMPLETE_CANONICAL_LAW_ORIGIN_DIAGNOSTICS',at=now(),code_sha256=sha(__file__),source_sha256=sha(source),score_sha256=sha(out/'SCORES.json'),score_views=len(scores),new_CDF_evaluations=0,new_direction_grades=0,new_fits=0,new_model_inference=0,new_issued_forecasts=0,new_NFL_observations=0));print(json.dumps(dict(score_views=len(scores),path=str((out/'SCORES.json').relative_to(a.root)))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--report',type=Path,required=True);a=p.parse_args();a.report=a.report.resolve();main(a)
