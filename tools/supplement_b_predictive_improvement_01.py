"""Saved-row controls, fixed cohorts and reporting qualifications; no new fits."""
import collections,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import abc_b_c_bound_replay as a,abc_b_glm_exact_line_replay as metrics,grade_saved_week8 as saved
from nfl_v2 import full_provider_prop_replay as core,scoring
from nfl_v2.paired_uncertainty import paired_losses
def hid(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def event_loss(r):
 state='over'if r['actual']>r['line']else'under'if r['actual']<r['line']else'push';p=r['probabilities'];return .5*sum((p[s]-int(s==state))**2 for s in ['over','under','push'])
def views(rows):
 weeks=sorted({r['week']for r in rows});return [str(w)for w in weeks]+(['ALL']if len(weeks)>1 else[])
def select_week(rows,wk):return [r for r in rows if wk=='ALL'or r['week']==int(wk)]
def main(private,evidence,out):
 binding=a.load(out/'CURRENT_EXECUTION_BINDING.json');inputs=a.load(private/binding['inputs']);payload=a.load(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz');rows=payload['rows'];source=a.load(out/'SCORES.json');refs=[];referenceproper=[];cohorts=[];cohortproper=[];pairrows=[];paired_native=[];membership=[];ownpool=[]
 # A qualified source annotation fixes typing, not any selection or forecast.
 annotations=[]
 for i,r in enumerate(source):
  if r['record_kind']!='prop_selection_evaluation':continue
  addition=dict(source_row_index=i,record_id=r['record_id']);has=False
  if r.get('mae')is not None or r.get('bias')is not None:
   addition['ancillary_point_attribution']=dict(kind='ORIGINAL_B0_MEAN_REFERENCE_NOT_THIS_EVENT_PRODUCT',original_metrics={key:r.get(key)for key in ['mae','mse','rmse','bias','p90_abs','p95_abs','max_abs']});has=True
  if r['strategy'].startswith('ROLLING_K'):
   k,side=r['strategy'].split('_')[1:];addition['registered_rolling_rank']=dict(K=int(k[1:]),side_pool=side,rank_scope='PER_CATEGORY_PER_WEEK_ROLLING_DECISION_BATCHES');has=True
  p=r['selection_metrics'].get('probability_scores',{})
  if p.get('conditioning')=='MODELED_APPEARANCE'and p.get('score_contract')=='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1':addition['probability_scores']=p;has=True
  if has:annotations.append(addition)
 a.save(out/'INDEX_REPORTING_ANNOTATIONS.json',dict(source_score_sha256=a.sha(out/'SCORES.json'),predictions_and_selection_scores_unchanged=True,classification='Separateoriginalmeanancillaryproduct fromevent/controlnativeerror; expose typedrollingK andselectedsubsetpropermetrics.',rows=annotations))
 # Same-parent-selected masks: neither unknowns nor adverse outcomes disappear.
 for target in ['rec','pass_td']:
  prior={r['offer_id']:r for r in inputs[target]['prior']};evaluation=inputs[target]['evaluation'];vv=views(evaluation)
  for arm in [0,1]:
   for policy in ['ALL','B2_MATCHED_EARLIER_CONFIDENCE','CONF_0.90']:
    parent=[r for r in rows if r['target']==target and r['method_key'].endswith('::B'+str(arm))and r['selection_policy']==policy]
    for wk in vv:
     parentview=select_week(parent,wk);selected=[r for r in parentview if r['selected_side']];maskhash=hid(sorted(r['offer_id']for r in selected))
     for cid in ['ALWAYS_OVER','ALWAYS_UNDER','EARLIER_SOURCE_PRIOR']:
      cr=[]
      for r in selected:
       p=prior[r['offer_id']]['probabilities']if cid=='EARLIER_SOURCE_PRIOR'else dict(over=.5,under=.5,push=0.);side=None if p is None else('over'if p['over']>p['under']else'under'if p['under']>p['over']else None)if cid=='EARLIER_SOURCE_PRIOR'else'over'if cid=='ALWAYS_OVER'else'under'
       q=dict(r,prediction=None,raw_prediction=None,probabilities=p,selected_side=side,side=side,original_side=None);q=core.grade([q],strategies=('original',))[0]
       if p is None:q['statistical_state']='UNAVAILABLE_FORECAST'
       cr.append(q)
      name=f'B::IMPROVEMENT01::MATCHED_{cid}::PARENT_B{arm}::{policy}';panel=f'B-IMPROVEMENT01-SELECTED-MATCH:{target}:{policy}';ss=a.score(cr,name,target,wk,dict(history_regime='EARLIER_REFERENCE',product_id='matched_selected_reference',decision_rule=cid,parent_policy=policy,parent_arm='B'+str(arm),parent_source_eligible=len(parentview),parent_selected=len(selected),parent_selected_membership_sha256=maskhash,cohort_scope='SAME_PREGAME_PARENT_SELECTION;NOT_FULL_SOURCE_COVERAGE'),panel)
      for s in ss:s.update(strategy=cid,cohort_id='CONDITIONAL_PARENT_SELECTED_MASK',horizon_id='INHERIT_EXACT_PARENT_SOURCE_CLOCKS');sub=[r for r in cr if r['selected_side']and(s['side']=='Combined'or r['selected_side']==s['side'])];s['selection_metrics']['probability_scores']=metrics.metrics(sub)
      refs+=ss;pm=metrics.metrics(cr);referenceproper.append(dict(record_id='B-REF-PROB-'+hid([target,arm,policy,wk,cid])[:24],record_kind='prop_threshold_probability_evaluation',procedure_id=name,history_regime='EARLIER_REFERENCE',product_id='same_parent_selected_probability_reference',target=target,season=2026,week=wk,evaluation_seasons=[2026],evaluation_weeks=sorted({r['week']for r in cr}),evaluation_panel_id=panel,evidence='NEW_EXPERIMENT_SAVED_ROW_REFERENCE_COMPARISON',evidence_tier='INHERIT_PARENT_ACTUAL_LINE_TIMING_QUALIFICATION',forecast_rows=len(cr),admitted_forecast_rows=sum(r['probabilities']is not None for r in cr),probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',bookmaker_nonvoid_conditioning='UNESTABLISHED',parent_source_offer_rows=len(parentview),parent_selected_rows=len(selected),parent_selected_membership_sha256=maskhash,**{key:pm[key]for key in ['n','brier','log_loss','infinite_log_losses','null_reason']}))
  # Full-board proper-score paired differences, rather than selected-only scores.
  for wk in vv:
   aa={r['offer_id']:r for r in select_week([r for r in rows if r['target']==target and r['method_key'].endswith('::B1')and r['selection_policy']=='ALL'],wk)};bb={r['offer_id']:r for r in select_week([r for r in rows if r['target']==target and r['method_key'].endswith('::B0')and r['selection_policy']=='ALL'],wk)};keys=sorted(k for k in aa.keys()&bb.keys()if all(x['probabilities']is not None and x['actual']is not None and x['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'for x in [aa[k],bb[k]]))
   u=paired_losses([event_loss(aa[k])for k in keys],[event_loss(bb[k])for k in keys],[aa[k]['week']for k in keys],[aa[k]['game_id']for k in keys]);paired_native.append(dict(target=target,week=wk,metric='HALF_MULTICLASS_BRIER',procedure_id=next(iter(aa.values()))['method_key'],comparator_procedure_id=next(iter(bb.values()))['method_key'],n=len(keys),membership_sha256=hid(keys),uncertainty=u))
   for policy in ['ALL','B2_MATCHED_EARLIER_CONFIDENCE','CONF_0.90']:
    pools={arm:[r for r in select_week([r for r in rows if r['target']==target and r['method_key'].endswith('::B'+str(arm))and r['selection_policy']==policy],wk)if r['statistical_state']in ['WIN','LOSS']]for arm in [0,1]};n={arm:len(pool)for arm,pool in pools.items()};win={arm:sum(r['statistical_state']=='WIN'for r in pool)for arm,pool in pools.items()};rates={arm:win[arm]/n[arm]if n[arm]else None for arm in pools};games=sorted({r['game_id']for r in select_week(evaluation,wk)});delta=rates[1]-rates[0]if all(n.values())else None;se=None
    if delta is not None and len(games)>1:
     influence=[]
     for game in games:
      x={arm:sum(int(r['statistical_state']=='WIN')-rates[arm]for r in pool if r['game_id']==game)/n[arm]for arm,pool in pools.items()};influence.append(x[1]-x[0])
     se=math.sqrt(len(games)/(len(games)-1)*sum(x*x for x in influence))
    ownpool.append(dict(target=target,week=wk,policy=policy,raw_wins=win[0],raw_n=n[0],repaired_wins=win[1],repaired_n=n[1],hit_rate_change=delta,game_clusters=len(games),game_sensitivity_se=se,game95_sensitivity=[delta-1.96*se,delta+1.96*se]if se is not None else None,interpretation='Differentselectedpoolsmaycontribute; matchedselectioncount isnotcommonrowlearner effect. Exposeddescriptivegame-cluster sensitivity, notmultiplicityadjusted; weekclusters<=2.'))
 # Reuse existing frozen weekly player/workload ranks, not C's pick rankings.
 histpath=evidence/'pregame-cohort-scorecards-v2/memberships.json.gz';futurepath=evidence/'pregame-cohort-scorecards-v2/future-memberships.json.gz';profiles={}
 for path in [histpath,futurepath]:
  for m in a.load(path):
   game,player,target,pop=m['key']
   if target not in ['rec','pass_td']or pop not in ['primary','frozen_exante_feed']:continue
   key=game,player,target;assert key not in profiles;profiles[key]=m
 cohortnames=['ACTIVE_REPAIR_COMMON','BASE_LEARNED_COMMON','top10','top15','top20','rank1_10','rank11_15','rank16_20','rank21plus','unranked','workload_low','workload_medium','workload_high','workload_unknown','role_RB','role_WR','role_TE','role_QB','membership_unavailable']
 # Original workload labels use their exact prior spellings, never renamed bands.
 actualbands=sorted({c for m in profiles.values()for c in m['cohorts']if c.startswith('workload_')});cohortnames=[c for c in cohortnames if not c.startswith('workload_')]+actualbands
 for target in ['rec','pass_td']:
  full=[r for r in rows if r['target']==target and r['selection_policy']=='ALL'];byarm={arm:{r['offer_id']:r for r in full if r['method_key'].endswith('::B'+str(arm))}for arm in [0,1]};tags={};missing=collections.Counter()
  for oid,r in byarm[1].items():
   labels=['role_'+r['position']]
   if r['probabilities']is not None and r['repair_state']=='FITTED_GAME_WEIGHTED_INTERCEPT_MAP':labels.append('ACTIVE_REPAIR_COMMON')
   if r['probabilities']is not None and r['fallback']in ['none',False]:labels.append('BASE_LEARNED_COMMON')
   m=profiles.get((r['game_id'],r['player_id'],target))
   if m is None or m['ranking_cutoff']>r['decision_epoch']:labels.append('membership_unavailable');missing['missing'if m is None else'cutoff_later_than_decision']+=1
   else:
    assert m['latest_available']is None or m['latest_available']<m['ranking_cutoff'];labels+=m['cohorts'];missing['matched']+=1
   tags[oid]=set(labels)
  for cohort in cohortnames:
   ids=sorted(oid for oid,tt in tags.items()if cohort in tt);membership.append(dict(target=target,cohort_id=cohort,n=len(ids),membership_sha256=hid(ids),source_original_rows=len(byarm[1]),historical_membership_sha256=a.sha(histpath),future_membership_sha256=a.sha(futurepath),context='Frozenprioropportunitymeanlast3slots; historicalparticipantuniverseororiginalfuturequeryfeed. Not newfull-exantepopulation, nottop-rankedpicks.'))
   for arm in [0,1]:
    pool=[byarm[arm][oid]for oid in ids]
    for wk in views(inputs[target]['evaluation']):
     rr=select_week(pool,wk);name=f'B::ABC-PREDICTIVE-IMPROVEMENT-01-B-INTERCEPT-v1::{target}::B{arm}';panel=f'B-IMPROVEMENT01-COHORT:{target}:{cohort}';ss=a.score(rr,name,target,wk,dict(history_regime='H-MULTI',product_id='exact_line_probability_product',decision_rule='ALL',cohort_id=cohort,full_source_offer_universe=len(select_week(inputs[target]['evaluation'],wk)),cohort_membership_sha256=hid([r['offer_id']for r in rr]),cohort_scope='IDENTICAL_EX_ANTE_STATUS_OR_PREVIOUSLY_FROZEN_MEMBERSHIP;RETROSPECTIVE_SOURCE_PANEL'),panel)
     for s in ss:s.update(strategy='ALL',cohort_id=cohort);sub=[r for r in rr if r['selected_side']and(s['side']=='Combined'or r['selected_side']==s['side'])];s['selection_metrics']['probability_scores']=metrics.metrics(sub)
     cohorts+=ss
  membership.append(dict(target=target,cohort_id='SOURCE_MEMBERSHIP_CENSUS',**dict(missing)))
 a.save(out/'MATCHED_SELECTED_CONTROL_SCORES.json',refs);a.save(out/'REFERENCE_PROBABILITY_SCORES.json',referenceproper);a.save(out/'COMMON_COHORT_SCORES.json',cohorts);a.save(out/'COHORT_MEMBERSHIP_MANIFEST.json',membership);a.save(out/'PAIRED_PROBABILITY_ANALYSIS.json',paired_native);a.save(out/'OWN_POOL_CHANGE_SENSITIVITY.json',ownpool)
 # One original mean product, not two invented calibrated means.
 rr=[r for r in rows if r['target']=='pass_td'and r['selection_policy']=='ALL'and r['method_key'].endswith('::B0')and r['prediction']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];m=scoring.point_metrics([r['prediction']for r in rr],[r['actual']for r in rr],'pass_td');errors=[abs(r['prediction']-r['actual'])for r in rr];precision={name:dict(numerator=sum((e<=tol if inclusive else e<tol)for e in errors),denominator=len(rr))for tol in [1,5,10]for inclusive,name in [(False,'abs_lt_'+str(tol)),(True,'abs_le_'+str(tol))]};precision['exact_rate']=dict(numerator=sum(e==0 for e in errors),denominator=len(rr))
 a.save(out/'ANCILLARY_POINT_SCORES.json',[dict(record_id='B-IMPROVEMENT01-ORIGINAL-PT-MEAN',record_kind='forecast_evaluation_view',procedure_id='B::C02_HMULTI_ORIGINAL_W8_CAPTURED_MEAN_UNCHANGED',product_id='original_mean_ancillary_not_repaired_probability_law_mean',target='pass_td',season=2026,week=8,evaluation_seasons=[2026],evaluation_weeks=[8],evaluation_panel_id='ORIGINAL_B0_ANCILLARY_CURRENT_FINAL_LABELS',history_regime='H-MULTI',forecast_rows=28,admitted_forecast_rows=26,unavailable_forecasts=2,unique_games=len({r['game_id']for r in rr}),precision_counts=precision,evidence='REPRODUCED_FROM_ORIGINAL_SAVED_MEAN_WITH_CURRENT_FINAL_LABELS',unchanged_in_B1=True,**m)])
 target90=[]
 for target in ['rec','pass_td']:
  for arm in [0,1]:
   for wk in views(inputs[target]['evaluation']):
    r=next(r for r in source if r['target']==target and str(r['week'])==wk and r.get('side')=='Combined'and r['strategy']=='CONF_0.90'and r['procedure_id'].endswith('::B'+str(arm)));target90.append(dict(target=target,arm=arm,week=wk,selected=r['forecast_rows'],wins=r['selection_metrics']['WIN'],losses=r['selection_metrics']['LOSS'],decided=r['n'],hit_rate=r['selection_metrics']['hit_rate'],coverage=r['selection_metrics']['selection_coverage'],status='TARGET_NOT_ESTABLISHED',reason='Zeroqualifiedselections;N/Ahitrate,not100%. Alsoinsufficientweeks/games/supportforregisteredscientificclaim.'))
 a.save(out/'TARGET_90_STATUS.json',target90);a.save(out/'SUPPLEMENT_RECEIPT.json',dict(new_fits=0,new_base_inference=0,new_private_bytes=0,source_model_rows_sha256=a.sha(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz'),parent_scores_sha256=a.sha(out/'SCORES.json'),selected_control_views=len(refs),reference_probability_views=len(referenceproper),cohort_views=len(cohorts),ancillary_numeric_views=1,source_rows_not_changed=True,actual_NFL_observations_added=0))
 print(json.dumps(dict(selected_controls=len(refs),reference_proper=len(referenceproper),cohort_views=len(cohorts),ancillary_numeric=1)))
if __name__=='__main__':main(*map(Path,sys.argv[1:4]))
