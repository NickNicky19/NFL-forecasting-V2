"""Numerical diagnostics on the same retained offered-player rows; no fits."""
import collections,hashlib,json,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import abc_b_c_bound_replay as a
from nfl_v2.scoring import point_metrics
def main(private):
 start=time.monotonic();out=ROOT/'reports/abc-championship/continuation-20261103-v4/numerical-offer-panel-v1';out.mkdir(exist_ok=False)
 a.save(out/'FROZEN_PROTOCOL.json',dict(id='B-C-BOUND-SAVED-NUMERICAL-PANEL-v1',at_utc=datetime.now(timezone.utc).isoformat(),scope='Same existing B v2/v3 saved points+C corrected offer outcomes; numeric allavailableplayed rows including P1 equality abstention; no offer-derived calibration, tuning or new forecasts.',new_fits=0,new_inference=0,core='nfl_v2.scoring.point_metrics',precision='exact,strict/inclusive1/5/10 native units, each numerator/denominator retained; MAE not percentaccuracy',exposed=True,max_wall_seconds=120,max_public_bytes=8388608))
 inputs=['B_OWNER_LOCAL_C_MATCHED_ROWS_V2.json.gz','B_OWNER_LOCAL_C_ADDITIONAL_ROWS_V3.json.gz'];groups=collections.defaultdict(list);meta={};bindings=[]
 for v in ['v2','v3']:
  for r in a.load(ROOT/('reports/abc-championship/continuation-20261103-'+v+'/SCORES.json')):
   if r['week']=='ALL'and r['side']=='Combined':meta[r['procedure_id'],r['target']]=r
 for name in inputs:
  p=private/name;bindings.append(dict(safe_id=name,sha256=a.sha(p)))
  for r in a.load(p)['rows']:groups[r['method_key'],r['target']].append(r)
 scores=[]
 for (proc,target),pool in sorted(groups.items()):
  m=meta[proc,target]
  for wk in ['ALL',2,3]:
   rr=[r for r in pool if wk=='ALL'or r['week']==wk];valid=[r for r in rr if r['prediction']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];pred=[r['prediction']for r in valid];actual=[r['actual']for r in valid];metrics=point_metrics(pred,actual,target);n=metrics['n'];errors=[abs(p-y)for p,y in zip(pred,actual)]
   pc={'exact_rate':dict(numerator=sum(x==0 for x in errors),denominator=n)}
   for t in [1,5,10]:
    pc['abs_lt_'+str(t)]=dict(numerator=sum(x<t for x in errors),denominator=n);pc['abs_le_'+str(t)]=dict(numerator=sum(x<=t for x in errors),denominator=n)
   scores.append(dict(record_id='ABC-B-NUM-'+hashlib.sha256(json.dumps([proc,target,wk]).encode()).hexdigest()[:24],record_kind='forecast_evaluation_view',procedure_id=proc,history_regime=m['history_regime'],product_id=m['product_id'],information_policy=m['information_policy'],target=target,season=2026,week=wk,evaluation_seasons=[2026],evaluation_weeks=sorted({r['week']for r in rr}),evaluation_panel_id='B_C_PINNACLE_OFFERED_PLAYER_NUMERICAL_W2_W3_'+str(wk),horizon_id='KICKOFF_RECONSTRUCTION_VS_LAST_RECORDED_PREKICK_CLOSE',population='Primaryretrospectiveparticipantforecasts on fullCofferboard; missing outputs retained',forecast_rows=len(rr),supported_rows=n,missing_actual_or_output=len(rr)-n,fallback_rows=sum(r['fallback']not in ['none',None]for r in rr),unique_games=len({r['game_id']for r in valid}),unique_player_games=len({(r['game_id'],r['player_id'])for r in valid}),evidence='REPRODUCED_FROM_DATA',source_vintage='B_CURRENT_REVISED_7DAY_RECONSTRUCTION;C_CORRECTED_LABELS;QUOTE_TIMING_UNVERIFIED',shared_benchmark_status='B_OWNER_LOCAL_C_PROTOCOL_PINNED_NOT_C_ADMITTED',precision_counts=pc,**metrics))
 a.save(out/'SCORES.json',scores);a.save(out/'INPUT_BINDINGS.json',bindings);a.save(out/'RUN_RECEIPT.json',dict(new_fits=0,new_model_inference=0,new_forecasts=0,point_recipe_category_cells=len(groups),views=len(scores),source_offer_rows=968,new_NFL_observations=0,code_sha256=a.sha(__file__),core_sha256=a.sha(ROOT/'nfl_v2/scoring.py'),wall_seconds=time.monotonic()-start))
 print(json.dumps(dict(cells=len(groups),views=len(scores),seconds=time.monotonic()-start)))
if __name__=='__main__':main(Path(sys.argv[1]))
