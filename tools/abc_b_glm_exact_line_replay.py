"""Restore saved parametric laws at C's exact lines; reuse B settlement engine."""
import collections,hashlib,json,math,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import abc_b_c_bound_replay as a
from tools import grade_saved_week8 as existing
from nfl_v2 import full_provider_prop_replay as shared,scoring
from nfl_v2.distribution_laws import Law
def metrics(rr):
 valid=[r for r in rr if r.get('probabilities')is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];losses=[];logs=[]
 for r in valid:
  state='over'if scoring.exact_decimal(r['actual'])>scoring.exact_decimal(r['line'])else'under'if scoring.exact_decimal(r['actual'])<scoring.exact_decimal(r['line'])else'push';p=r['probabilities'];losses.append(.5*sum((p[s]-int(s==state))**2 for s in ['over','under','push']));logs.append(-math.log(p[state])if p[state]>0 else math.inf)
 return dict(n=len(valid),brier=math.fsum(losses)/len(losses)if losses else None,log_loss='Infinity'if any(math.isinf(x)for x in logs)else math.fsum(logs)/len(logs)if logs else None,infinite_log_losses=sum(math.isinf(x)for x in logs),conditioning='MODELED_APPEARANCE',bookmaker_nonvoid_conditioning='UNESTABLISHED',score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',null_reason=None if valid else'NO_QUALIFIED_LAW_AND_ACTUAL_ROWS')
def main(private,snapshot,chunks):
 start=time.monotonic();out=ROOT/'reports/abc-championship/continuation-20261103-v4';out.mkdir(exist_ok=False);a.OUT=out
 p=dict(id='B-C-SAVED-GLM-EXACT-LINE-LAW-v1',at_utc=datetime.now(timezone.utc).isoformat(),C_ref=a.CREF,C_protocol_sha256=a.sha(snapshot/'reports/abc-championship/PROTOCOL-v2-C-1.json'),
  admission='B_OWNER_LOCAL_C_BOUND_NOT_C_ADMITTED',scope='All4Cqualifiedcategories/W2-W3/all4existingGLMpolicy arms; restored parametric/fallback parameters, no fitted model decoding, no new fit or coefficient inference.',
  selection='P2 choose higher exact-line Pover/Punder, absolute difference<=1e-12 ties abstain, missing law technical unavailable. MODELED_APPEARANCE, not authenticated bookmaker nonvoid.',
  probability='Use original Law CDF. Integer L:k =>under F(k-1),push F(k)-F(k-1),over1-F(k); fractional=>underF(floorL),over1-F(floorL),push0. Signed yards retained; only epsilon dust canonicalized. Zero mass log loss Infinity, no clipping.',
  controls='Neutral50/50 only halfpoint/no-push identical masks; C earlier-estimated prevalence/P2/P3 on exact same qualified masks. No evaluated-outcome calibration; marketprobabilities unavailable.',
  timing='Same C diagnostic last-recorded-line/kickoff reconstruction; actual quote availability unverified; existing revised-source7dayfeature rule retained.',
  budget=dict(new_fits=0,new_model_inference=0,max_wall_seconds=120,max_private_bytes=8388608,threads=1),known_exposure=True,new_original_picks=0)
 a.save(out/'FROZEN_PACKAGE.json',p);c,_=a.c_rows(snapshot);byoffer=collections.defaultdict(dict)
 for r in c:byoffer[r['offer_id']][r['method_id']]=r
 offers={oid:d['P2_LAW']for oid,d in byoffer.items()};laws=collections.defaultdict(dict);bindings=[]
 for file in sorted(chunks.glob('W0[23]-*-regularized_glm_law.json.gz')):
  j=a.load(file)
  if not j['rows']or j['rows'][0]['target']not in ['pass_yd','rush_yd','rec','rec_yd']:continue
  bindings.append(dict(member_id=file.name,sha256=a.sha(file),bytes=file.stat().st_size))
  for r in j['rows']:
   if r['population']!='primary'or r['product_id']!='mean':continue
   key=(r['procedure_id'],r['policy_id'],r['target']);laws[key][r['game_id'],r['player_id']]=r
 scores=[];proper=[];baselines=[];paired=[];allrows=[];checks=collections.Counter()
 for (proc,policy,target),lookup in sorted(laws.items()):
  name='B::'+proc+'::'+policy+'::P2_EXACT_LINE_CDF-v1';pool=[];first=next(iter(lookup.values()))
  for oid,q in sorted(offers.items()):
   if q['category']!=target:continue
   b=lookup.get((q['game_id'],q['player_id']));pp=None
   if b:
    assert b['cutoff']==a.instant(q['decision_UTC'])and(b['latest_feature_available']is None or b['latest_feature_available']<b['cutoff'])and b['position']==q['position']
    assert q['actual']is None or b['actual']is None or q['actual']==b['actual']
    ref=b.get('law_reference')or{};params=ref.get('parametric')or ref.get('fallback_prior')
    if params:
     law=Law(**params);summary=b['distribution_summary'];assert abs(law.mean-summary['mean'])<1e-9 and law.quantile(.5)==summary['lower_median'];checks['retained_mean_median_parity']+=1
     L=scoring.exact_decimal(q['line']);k=int(L.to_integral_value(rounding='ROUND_FLOOR'));f=law.cdf(k);u=law.cdf(k-1)if L==k else f;pp=dict(over=1-f,under=u,push=f-u if L==k else 0.)
     assert min(pp.values())>=-1e-12 and max(pp.values())<=1+1e-12 and abs(sum(pp.values())-1)<1e-12
     pp={s:max(0.,min(1.,v))for s,v in pp.items()};total=sum(pp.values());pp={s:v/total for s,v in pp.items()};checks['complement']+=1
   side=None if pp is None or abs(pp['over']-pp['under'])<=1e-12 else'over'if pp['over']>pp['under']else'under'
   row=dict(offer_id=oid,source_row_index=oid,game_id=q['game_id'],player_id=q['player_id'],target=target,season=2026,week=q['week'],position=q['position'],line=q['line'],prediction=None,raw_prediction=None,side=side,original_side=None,source_cohorts=[],actual=q['actual'],participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL'if q['appearance']=='PLAYED'else'UNKNOWN',outcome_state='final',fallback=b['fallback']if b else None,probabilities=pp,method_key=name,decision_time=q['decision_UTC'],kickoff=q['kickoff_UTC'],evidence_tier=a.TIER,law_parameters=params if b and params else None)
   g=shared.grade([row],strategies=('original',))[0]
   if pp is None:g['statistical_state']='UNAVAILABLE_FORECAST'
   pool.append(g)
  allrows+=pool
  for wk in ['ALL','2','3']:
   rr=[r for r in pool if wk=='ALL'or r['week']==int(wk)];panel='B_OWNER_LOCAL_C_PINNACLE_W2_W3_'+wk
   vv=a.score(rr,name,target,wk,dict(history_regime=first['history_regime'],information_policy=first['information_policy'],product_id='actual_line_categorical_law',base_procedure_id=proc,decision_rule='P2',probability_conditioning='MODELED_APPEARANCE',bookmaker_nonvoid_conditioning='UNESTABLISHED'),panel)
   for v in vv:
    v['strategy']='P2';sub=[r for r in rr if r['selected_side']and(v['side']=='Combined'or r['selected_side']==v['side'])];v['selection_metrics']['probability_scores']=metrics(sub)
   scores+=vv;pm=metrics(rr);proper.append(dict(record_id='ABC-B-GLM-PROB-'+hashlib.sha256(json.dumps([name,target,wk]).encode()).hexdigest()[:24],record_kind='prop_threshold_probability_evaluation',procedure_id=name,history_regime=first['history_regime'],product_id='actual_line_categorical_law',target=target,season=2026,week=wk,evaluation_seasons=[2026],evaluation_weeks=sorted({r['week']for r in rr}),evaluation_panel_id=panel,evidence='REPRODUCED_FROM_DATA',evidence_tier=a.TIER,forecast_rows=len(rr),admitted_forecast_rows=sum(r['probabilities']is not None for r in rr),probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',bookmaker_nonvoid_conditioning='UNESTABLISHED',**{k:pm[k]for k in ['n','brier','log_loss','infinite_log_losses','null_reason']}))
   mask={r['offer_id']for r in rr if r['probabilities']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'}
   for cid in ['NEUTRAL_HALFPOINT_50_50','EARLIER_PREVALENCE_V8','P2_LAW','P3_DIRECT']:
    cr=[]
    for r in rr:
     if r['offer_id']not in mask:continue
     q=byoffer[r['offer_id']].get(cid)
     if cid=='NEUTRAL_HALFPOINT_50_50':
      if scoring.exact_decimal(r['line'])%1!=scoring.exact_decimal('.5'):continue
      pp=dict(over=.5,under=.5,push=0.)
     elif q is None or q.get('p_over')is None:continue
     else:pp={s:q['p_'+s]for s in ['over','under','push']}
     cr.append(dict(r,probabilities=pp))
    cp=metrics(cr);own=metrics([r for r in rr if r['offer_id']in {x['offer_id']for x in cr}]);baselines.append(dict(target=target,procedure_id=name,week_view=wk,control=cid,n=cp['n'],candidate_brier=own['brier'],control_brier=cp['brier'],brier_delta=own['brier']-cp['brier']if cp['n']else None,conditioning='MODELED_APPEARANCE',null_reason=cp['null_reason']))
   for cid in ['ALWAYS_OVER','ALWAYS_UNDER','EARLIER_PREVALENCE_V8','P3_DIRECT']:
    cr=[dict(r,statistical_state=r['status'],selected_side=r['selected_side'].lower()if r['selected_side']in ['OVER','UNDER']else None)for r in c if r['category']==target and r['method_id']==cid and(wk=='ALL'or r['week']==int(wk))];paired.append(a.pair(rr,cr,target,name,cid,wk,panel))
 a.save(out/'SCORES.json',scores+proper);a.save(out/'PROBABILITY_BASELINES.json',baselines);a.save(out/'PAIRED_CONTROLS.json',paired);a.save(out/'INPUT_BINDINGS.json',bindings);a.save(out/'SIDE_TABLE.json',existing.wide(scores));existing.write_csv(out/'SIDE_TABLE.csv',existing.wide(scores))
 a.gzsave(private/'B_OWNER_LOCAL_C_GLM_LAW_ROWS_V4.json.gz',dict(rows=allrows));file=private/'B_OWNER_LOCAL_C_GLM_LAW_ROWS_V4.json.gz';assert file.stat().st_size<p['budget']['max_private_bytes']
 a.save(out/'PRIVATE_DERIVATIVE_MANIFEST.json',dict(safe_id='B_OWNER_LOCAL_C_GLM_LAW_ROWS_V4',sha256=a.sha(file),bytes=file.stat().st_size,rows=len(allrows),offhost_restored=False))
 a.save(out/'RUN_RECEIPT.json',dict(new_fits=0,new_model_inference=0,restored_parametric_laws=len(allrows),new_issued_forecasts=0,actual_weeks=[2,3],law_category_history_cells=len(laws),side_views=len(scores),probability_views=len(proper),checks=dict(checks),wall_seconds=time.monotonic()-start,code_sha256=a.sha(__file__),law_code_sha256=a.sha(ROOT/'nfl_v2/distribution_laws.py')))
 print(json.dumps(dict(laws=len(laws),side_views=len(scores),proper_views=len(proper),seconds=time.monotonic()-start)))
if __name__=='__main__':main(*map(Path,sys.argv[1:4]))
