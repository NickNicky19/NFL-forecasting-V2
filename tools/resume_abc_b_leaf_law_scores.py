"""Resume scoring completed retained-law rows; never repeat histogram lookup."""
import collections,gzip,hashlib,json,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import abc_b_c_bound_replay as a,abc_b_glm_exact_line_replay as g,grade_saved_week8 as existing
from nfl_v2 import scoring
def main(source,snapshot,out):
 start=time.monotonic();out.mkdir(exist_ok=False);parent=ROOT/'reports/abc-championship/leaf-law-continuation-20261104-v1';failure=a.load(parent/'FAILED_ATTEMPT_RECEIPT.json');assert a.sha(source)==failure['private_sha256']
 protocol=dict(id='B-C-RETAINED-LEAF-LAW-SCORING-RESUME-v2',at_utc=datetime.now(timezone.utc).isoformat(),parent_protocol=str((parent/'FROZEN_PACKAGE.json').relative_to(ROOT)),parent_protocol_sha256=a.sha(parent/'FROZEN_PACKAGE.json'),failed_attempt_sha256=a.sha(parent/'FAILED_ATTEMPT_RECEIPT.json'),completed_rows_sha256=a.sha(source),code_sha256=a.sha(__file__),source_C_ref=a.CREF,core_protocol_sha256='fa19581487519a854948269bc1ce328cbbcdc734afee2464f1ff778d1ff241a1',budget=dict(new_fits=0,new_model_inference=0,new_histogram_lookup=0,max_new_private_bytes=0,max_wall_seconds=180),task='Reuse all completed v1 rows, preserve its post-write budget failure; add public aggregates only, not another private copy. No repeated models, histograms, forecasts or source collection.',source_metadata='Check both training feature availability names explicitly; missing alias never means no feature consumption. Bind every model/chunk to v1 preflight. Absent-source fallback metadata normalized to NOT_RETAINED, not learned output.',evidence_tier=a.TIER,population='Full C board with retained B retrospective primary-query support; not complete original ex-ante issuance.',selection='Frozen original P2 exact-line higher Over/Under probability,1e-12 tie abstention. Conditional modelled appearance; settlement/prices/void probability unverified.',new_holdout=False,production_changes=False)
 a.save(out/'FROZEN_PACKAGE.json',protocol)
 raw=a.load(source)['rows'];assert len(raw)==15488;groups=collections.defaultdict(list);metadata={};normalizations=0
 original=a.load(parent/'FROZEN_PACKAGE.json');fitbindings={r['fit_receipt']:r for r in original['fits']};fitchecks=[]
 for fit,b in fitbindings.items():
  f=a.load(ROOT/fit);assert a.sha(ROOT/fit)==b['fit_sha256'];times={k:f.get(k)for k in ['latest_training_label_available','latest_training_feature_available','latest_training_consumed_feature_available']};cutoff=a.instant(f['fit_cutoff_utc']);assert all(v is None or v<=cutoff for v in times.values())
  fitchecks.append(dict(fit_receipt=fit,fit_sha256=b['fit_sha256'],model=b['model'],training_membership_sha256=b['training_membership_sha256'],fit_cutoff_utc=f['fit_cutoff_utc'],training_availability_fields=times,training_latest_eligible=True))
 for originalrow in raw:
  r=dict(originalrow)
  if r['probabilities']is None and r['fallback']is None:r['fallback']='NOT_RETAINED';normalizations+=1
  key=(r['method_key'],r['target']);groups[key].append(r)
  if r['fit_receipt']:
   f=a.load(ROOT/r['fit_receipt']);meta=r['method_key'].split('::');policy=meta[-2];metadata[key]=dict(history_regime=f['history_regime'],information_policy='STRICT-CURRENT'if policy.endswith('STRICT')else'COMMON-2022-MEMORY',product_id='actual_line_categorical_law',base_procedure_id='::'.join(meta[1:-2]),decision_rule='P2',probability_conditioning='MODELED_APPEARANCE',bookmaker_nonvoid_conditioning='UNESTABLISHED',fallback_metadata_scope='ALL_OUTER_QUERIES;source-absent states unknown,not learned or intentionalabstention')
 assert len(groups)==64
 c,_=a.c_rows(snapshot);byoffer=collections.defaultdict(dict)
 for r in c:byoffer[r['offer_id']][r['method_id']]=r
 for r in raw:
  q=byoffer[r['offer_id']]['P2_LAW'];assert(q['game_id'],q['player_id'],q['category'],q['line'],q['actual'])==(r['game_id'],r['player_id'],r['target'],r['line'],r['actual']);assert a.instant(r['decision_time'])==a.instant(q['decision_UTC'])
  if r['selected_side']and r['actual']is not None:assert scoring.threshold_crossing(r['actual'],r['line'],r['selected_side'],target=r['target'])==r['statistical_state']
 scores=[];proper=[];pairs=[];baselines=[];masks=[]
 for (name,target),pool in sorted(groups.items()):
  for wk in ['ALL','2','3']:
   rr=[r for r in pool if wk=='ALL'or r['week']==int(wk)];panel='B_C_PINNACLE_RETAINED_LEAF_LAWS_'+wk;meta=metadata[name,target];ss=a.score(rr,name,target,wk,meta,panel)
   for v in ss:v['strategy']='P2';v['selection_metrics']['probability_scores']=g.metrics([r for r in rr if r['selected_side']and(v['side']=='Combined'or r['selected_side']==v['side'])])
   scores+=ss;pm=g.metrics(rr);proper.append(dict(record_id='ABC-B-LEAF-PROB-'+hashlib.sha256(json.dumps([name,target,wk]).encode()).hexdigest()[:24],record_kind='prop_threshold_probability_evaluation',procedure_id=name,history_regime=meta['history_regime'],product_id='actual_line_categorical_law',target=target,season=2026,week=wk,evaluation_seasons=[2026],evaluation_weeks=sorted({r['week']for r in rr}),evaluation_panel_id=panel,evidence='REPRODUCED_FROM_DATA',evidence_tier=a.TIER,forecast_rows=len(rr),admitted_forecast_rows=sum(r['probabilities']is not None for r in rr),probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',bookmaker_nonvoid_conditioning='UNESTABLISHED',**{k:pm[k]for k in ['n','brier','log_loss','infinite_log_losses','null_reason']}))
   mask={r['offer_id']for r in rr if r['probabilities']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'};masks.append(dict(procedure_id=name,target=target,week=wk,n=len(mask),safe_C_offer_ids=sorted(mask),sha256=hashlib.sha256(json.dumps(sorted(mask),separators=(',',':')).encode()).hexdigest()))
   for cid in ['NEUTRAL_HALFPOINT_50_50','EARLIER_PREVALENCE_V8','P2_LAW','P3_DIRECT']:
    cr=[]
    for r in rr:
     if r['offer_id']not in mask:continue
     if cid=='NEUTRAL_HALFPOINT_50_50':
      if scoring.exact_decimal(r['line'])%1!=scoring.exact_decimal('.5'):continue
      cp=dict(over=.5,under=.5,push=0.)
     else:
      q=byoffer[r['offer_id']].get(cid)
      if q is None or q.get('p_over')is None:continue
      cp={s:q['p_'+s]for s in ['over','under','push']}
     cr.append(dict(r,probabilities=cp))
    cm=g.metrics(cr);own=g.metrics([r for r in rr if r['offer_id']in {x['offer_id']for x in cr}]);baselines.append(dict(target=target,procedure_id=name,week_view=wk,control=cid,n=cm['n'],candidate_brier=own['brier'],control_brier=cm['brier'],brier_delta=own['brier']-cm['brier']if cm['n']else None))
   for cid in ['ALWAYS_OVER','ALWAYS_UNDER','EARLIER_PREVALENCE_V8','P3_DIRECT']:
    cr=[dict(r,statistical_state=r['status'],selected_side=r['selected_side'].lower()if r['selected_side']in ['OVER','UNDER']else None)for r in c if r['category']==target and r['method_id']==cid and(wk=='ALL'or r['week']==int(wk))];pairs.append(a.pair(rr,cr,target,name,cid,wk,panel))
 a.save(out/'SCORES.json',scores+proper);a.save(out/'PROBABILITY_BASELINES.json',baselines);a.save(out/'PAIRED_CONTROLS.json',pairs);a.save(out/'OWNER_LOCAL_MASKS.json',masks);a.save(out/'FIT_METADATA_QUALIFICATION.json',dict(fits=fitchecks,source_absent_fallback_states_qualified=normalizations,model_bytes_verified_in_parent_preflight=True,model_hash_verification_scope='Beforev1unpickle; thissavedrowresume doesnotdeserializeagain; independentreviewrequired forrepresentatives.'));a.save(out/'SIDE_TABLE.json',existing.wide(scores));existing.write_csv(out/'SIDE_TABLE.csv',existing.wide(scores))
 a.save(out/'PRIVATE_DERIVATIVE_MANIFEST.json',dict(safe_id='B_RETAINED_LEAF_C_LAW_ROWS',sha256=a.sha(source),bytes=source.stat().st_size,rows=len(raw),offhost_restored=False,new_private_bytes=0,reuses_preserved_failed_attempt_bytes=True))
 a.save(out/'RUN_RECEIPT.json',dict(state='COMPLETE_SAVED_LAW_SCORING_NOT_C_ADMITTED',law_cells=len(groups),actual_weeks=[2,3],side_views=len(scores),proper_views=len(proper),new_fits=0,new_model_inference=0,new_histogram_lookup=0,new_issued_forecasts=0,new_NFL_observations=0,source_offers=968,source_games=32,retained_law_row_slots=len(raw),available_laws=sum(r['probabilities']is not None for r in raw),new_private_derivative_bytes=0,parent_retained_private_bytes=source.stat().st_size,source_absent_fallback_metadata_qualified=normalizations,wall_seconds=time.monotonic()-start,code_sha256=a.sha(__file__)))
 assert time.monotonic()-start<=180
 print(json.dumps(dict(cells=len(groups),side_views=len(scores),proper_views=len(proper),new_private_bytes=0,wall_seconds=time.monotonic()-start)))
if __name__=='__main__':main(*map(Path,sys.argv[1:4]))
