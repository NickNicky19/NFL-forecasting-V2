"""Partition retained B W5-W7 point panels with existing scoring arithmetic."""
import collections,gzip,hashlib,json,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import abc_b_c_bound_replay as adapter,grade_saved_week8 as existing
from tools.diagnose_point_offer_disagreement import FOCAL,CONTROLS
from nfl_v2 import scoring,full_provider_prop_replay as core
from nfl_v2.shared_subgroups import canonical
def mh(keys):return hashlib.sha256(canonical(sorted(keys))).hexdigest()
def main(source):
 start=time.monotonic();out=ROOT/'reports/abc-championship/weekly-point-partition-20261104-v1';out.mkdir(exist_ok=False)
 parent=ROOT/'reports/point-prop-diagnostic-20261031i/point-offer/v1';receipt=adapter.load(parent/'RUN_RECEIPT.json');assert adapter.sha(source)==receipt['private_sha256']
 adapter.save(out/'FROZEN_PROTOCOL.json',dict(id='B_RETAINED_W5_W7_POINT_WEEK_PARTITION-v1',at_utc=datetime.now(timezone.utc).isoformat(),parent_score_sha256=adapter.sha(parent/'SCORES.json'),parent_protocol_sha256=adapter.sha(parent/'FROZEN_PROTOCOL.json'),retained_rows_sha256=adapter.sha(source),
  task='C39brequests per-week partitions of previouslyadmitted cumulativeBpointviews; exactparent masks/history/products/side rules retained. No newselection/ranking/inference or outcomeversion.',
  rules='Existing gradedP1 side and outcome states reused and checked against existing Decimalthreshold engine. Technicalunavailability distinct from equalityabstention. Original savedprecision controls not original selections.',
  scope='63parent selectiontriads/2focals:passingyards,completions; W5/W6/W7 separately. Original fullsystem/commonfull/commonlearned masks preserved; no new cohort selection.',
  horizon='INHERIT_RETAINED_DECISION_ELIGIBLE_KNOWN_TARGET_TIME;NOT Ckickoff/Pinnaclepanel; provider-labelledthresholds/quoteclocks remain qualified at oldlevel.',
  exposure='Allweeks alreadyexposed; views and controls not independentNFLobservations or an earlierselector.',budget=dict(new_fits=0,new_inference=0,new_issued_forecasts=0,max_wall_seconds=120,max_private_derivative_bytes=0)))
 data=collections.defaultdict(dict)
 for r in adapter.load(source)['rows']:
  if r.get('population_diagnostic'):continue
  key=tuple(r['recipe']);idx=(r['week'],r['source_row_index']);assert idx not in data[key];data[key][idx]=r
 possible=collections.defaultdict(dict)
 def add(key,keys):possible[key][mh(keys)]=set(keys)
 for key,dd in data.items():
  focal=(key[0],*FOCAL[key[0]]);ff=data[focal];own={k for k,r in dd.items()if r['admitted']};common={k for k in dd.keys()&ff.keys()if dd[k]['admitted']and ff[k]['admitted']};learned={k for k in common if dd[k]['fallback']=='none'and ff[k]['fallback']=='none'and key[1]not in CONTROLS}
  add(key,own);add(key,common);add(focal,common)
  if key[1]not in CONTROLS:add(key,learned);add(focal,learned)
 parents=[r for r in adapter.load(parent/'SCORES.json')if r['record_kind']=='prop_selection_evaluation'and r['side']=='Combined'];assert len(parents)==63
 scores=[];checks=[];membership=[];focal_views=[]
 for p in parents:
  key=(p['target'],p['procedure_id'],p['history_regime'],p['product_id']);dd=data[key];ids=possible[key][p['membership_sha256']];assert mh(ids)==p['membership_sha256'];own=p['cohort_id']=='OWN_DECISION_ELIGIBLE_FULL_SYSTEM';poolids=set(dd)if own else ids
  cumulative=collections.Counter();name='B::'+p['procedure_id']+'::'+p['history_regime']+'::'+p['product_id']
  for week in [5,6,7]:
   pool=[]
   for k in sorted(poolids):
    if k[0]!=week:continue
    r=dd[k];available=bool(r['admitted']and r['point']is not None);side=r['selected_side']if available else None;state=r['statistical_state']if available else'UNAVAILABLE_FORECAST'
    if side and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL':assert scoring.threshold_crossing(r['actual'],r['line'],side,target=r['target'])==state
    q=dict(r,offer_id=f"{week}:{r['source_row_index']}",source_row_index=f"{week}:{r['source_row_index']}",prediction=r['point']if available else None,raw_prediction=None,selected_side=side,statistical_state=state,fallback=r['fallback']if r['fallback']is not None else'NOT_RETAINED',method_key=name)
    pool.append(q)
    if side:cumulative[state]+=1;cumulative['selected']+=1
   panel='B_RETAINED_POINT_WEEK_PARTITION_'+p['record_id']+'_W'+str(week)
   ss=adapter.score(pool,name,p['target'],str(week),dict(history_regime=p['history_regime'],product_id=p['product_id'],base_procedure_id=p['procedure_id'],decision_rule='P1',parent_cumulative_record_id=p['record_id'],parent_context=p['cohort_id'],source_mask_sha256=mh((k for k in ids if k[0]==week))),panel)
   for s in ss:s.update(cohort_id=p['cohort_id'],horizon_id=p['horizon_id'],source_vintage='INHERIT_CURRENT_REVISED_FOOTBALL_AND_PROVIDER_THRESHOLD_TIMING_SOURCE_POLICY;NO_NEW_SOURCE_AUTHENTICATION',shared_benchmark_status='B_SOURCE_SPECIFIC_WEEK_PARTITION_AWAITING_C_INTAKE',evidence_tier='RETAINED_PROVIDER_LABELLED_POINT_RULE_REPLAY',selection_evidence='RETROSPECTIVE_RULE_REPLAY')
   scores+=ss
   valid=[r for r in pool if r['prediction']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];m=scoring.point_metrics([r['prediction']for r in valid],[r['actual']for r in valid],p['target']);errors=[abs(r['prediction']-r['actual'])for r in valid];precision={name:dict(numerator=sum((e<=t if inclusive else e<t)for e in errors),denominator=len(valid))for t in [1,5,10]for inclusive,name in [(False,'abs_lt_'+str(t)),(True,'abs_le_'+str(t))]};precision['exact_rate']=dict(numerator=sum(e==0 for e in errors),denominator=len(valid))
   scores.append(dict(record_id='B-WEEK-NATIVE-'+hashlib.sha256((p['record_id']+str(week)).encode()).hexdigest()[:24],record_kind='forecast_evaluation_view',procedure_id=name,history_regime=p['history_regime'],product_id=p['product_id'],target=p['target'],population=p['cohort_id'],season=2026,week=week,evaluation_seasons=[2026],evaluation_weeks=[week],evaluation_panel_id=panel,horizon_id=p['horizon_id'],forecast_rows=len(pool),admitted_forecast_rows=sum(r['prediction']is not None for r in pool),unavailable_forecasts=sum(r['prediction']is None for r in pool),fallback_rows=sum(r['fallback']not in ['none','NOT_RETAINED']for r in pool),fallback_unknown=sum(r['fallback']=='NOT_RETAINED'for r in pool),unique_games=len({r['game_id']for r in valid}),unique_player_games=len({(r['game_id'],r['player_id'])for r in valid}),precision_counts=precision,parent_cumulative_record_id=p['record_id'],source_vintage='UNCHANGED_PARENT_RETAINED_POINT_AND_LABEL_VERSION',evidence='REPRODUCED_FROM_DATA',**m))
   membership.append(dict(parent_record_id=p['record_id'],procedure_id=name,target=p['target'],cohort=p['cohort_id'],week=week,eligible=len(pool),admitted=sum(r['prediction']is not None for r in pool),mask_sha256=mh((k for k in ids if k[0]==week))))
   if own and key[1:]==FOCAL[key[0]]:focal_views.extend(ss)
  pm=p['selection_metrics'];assert (cumulative['WIN'],cumulative['LOSS'],cumulative['PUSH'],cumulative['selected'])==(pm['WIN'],pm['LOSS'],pm['PUSH'],p['forecast_rows']),('PARENT_COUNT_MISMATCH',key)
  checks.append(dict(parent_record_id=p['record_id'],target=p['target'],cohort=p['cohort_id'],wins=cumulative['WIN'],losses=cumulative['LOSS'],push=cumulative['PUSH'],selected=cumulative['selected'],state='WEEK_SUMS_EXACTLY_EQUAL_PARENT_CUMULATIVE'))
 adapter.save(out/'SCORES.json',scores);adapter.save(out/'WEEK_TO_PARENT_RECONCILIATION.json',checks);adapter.save(out/'WEEKLY_MEMBERSHIP_MANIFEST.json',membership);adapter.save(out/'FOCAL_WEEKLY_SIDES.json',focal_views)
 side=[r for r in scores if r['record_kind']=='prop_selection_evaluation'];adapter.save(out/'SIDE_TABLE.json',existing.wide(side));existing.write_csv(out/'SIDE_TABLE.csv',existing.wide(side))
 adapter.save(out/'RUN_RECEIPT.json',dict(state='COMPLETE_SAVED_ROW_WEEK_PARTITION_NO_NEW_OUTCOMES',at_utc=datetime.now(timezone.utc).isoformat(),parent_cumulative_triads=63,weekly_triads=189,side_views=len(side),native_views=len(scores)-len(side),actual_weeks=[5,6,7],targets=['pass_yd','pass_cmp'],source_unique_games=len({r['game_id']for dd in data.values()for r in dd.values()}),new_fits=0,new_model_inference=0,new_issued_forecasts=0,new_NFL_observations=0,new_private_derivative_bytes=0,source_rows_sha256=adapter.sha(source),parent_score_sha256=adapter.sha(parent/'SCORES.json'),code_sha256=adapter.sha(__file__),wall_seconds=time.monotonic()-start))
 print(json.dumps(dict(side_views=len(side),native_views=len(scores)-len(side),parent_checks=len(checks),focals=[dict(target=r['target'],week=r['week'],side=r['side'],wins=r['selection_metrics']['WIN'],n=r['n'])for r in focal_views])))
if __name__=='__main__':main(Path(sys.argv[1]))
