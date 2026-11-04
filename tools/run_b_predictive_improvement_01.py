"""B-owned one-parameter probability repair and earlier-confidence gating."""
import collections,gzip,hashlib,json,math,resource,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import abc_b_c_bound_replay as a,abc_b_glm_exact_line_replay as lawmetrics,grade_saved_week8 as saved
from nfl_v2 import exact_line_repair as mechanism,full_provider_prop_replay as core,scoring
from nfl_v2.paired_uncertainty import paired_losses
VERSION='ABC-PREDICTIVE-IMPROVEMENT-01-B-INTERCEPT-v1'
PT_PROCEDURE='v2-c02-explicit-lag-block-removal-leaf-cdf-v1:known-target-time-v1'
PT_CAPTURE='v2-c02-future-ordered-control-shadow-v1:c02_explicit_lag_block_removed:common-feature-memory'
HIST={5:('reports/baselines-coverage-20261031h/actual-method-w5/complete-leaf-law-v1','baselines-coverage-20261031h-w5-complete-leaf-law-v1'),6:('reports/completion-20261031g/roster/w6-complete-leaf-law-v1','completion-20261031g-w6-complete-leaf-law-v1'),7:('reports/completion-20261031g/roster/w7-complete-leaf-law-v1','completion-20261031g-w7-complete-leaf-law-v1')}
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def normalize(r,panel,oid,probabilities,decision=None,point=None):
 t=decision or r['decision_time'];kick=r['kickoff'];target=r.get('target',r.get('category'));actual=r['actual'];played=r.get('participation')
 if actual is not None:assert int(actual)==actual and actual>=0
 return dict(panel=panel,offer_id=oid,source_row_index=oid,game_id=r['game_id'],player_id=r['player_id'],target=target,season=2026,week=r['week'],position=r['position'],line=float(r['line']),prediction=point,raw_prediction=None,side=None,original_side=None,source_cohorts=[],actual=actual,participation=played,outcome_state='final',fallback=r.get('fallback','NOT_RETAINED'),probabilities=probabilities,decision_time=t,decision_epoch=mechanism.epoch(t),kickoff=kick,label_available=mechanism.epoch(kick)+mechanism.LABEL_LAG_SECONDS,price=None,net_return=None,settlement_state='UNRESOLVED_CONTRACT')
def prepare(evidence,snapshot,private,out):
 if private.exists():assert not any(private.iterdir()),'Existing private preparation must not be overwritten'
 if out.exists():assert not any(out.iterdir()),'Existing public preparation must not be overwritten'
 private.mkdir(exist_ok=True);out.parent.mkdir(parents=True,exist_ok=True);out.mkdir(exist_ok=True);bindings=[];data={}
 c,_=a.c_rows(snapshot);recs=[r for r in c if r['category']=='rec'and r['method_id']=='P3_DIRECT'];rr=[];prior=[]
 for q in recs:
  p=None if q.get('p_over')is None else{s:q['p_'+s]for s in ['over','under','push']};r=dict(q,target='rec',kickoff=q['kickoff_UTC'],participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL'if q['appearance']=='PLAYED'else'UNKNOWN');v=normalize(r,'C_REC_W2_W3',q['offer_id'],p,decision=q['decision_UTC']);rr.append(v)
  if p is not None:assert mechanism.choose(p)==q['selected_side'].lower()
  qp=next(x for x in c if x['offer_id']==q['offer_id']and x['method_id']=='EARLIER_PREVALENCE_V8');prior.append(dict(v,probabilities=None if qp.get('p_over')is None else{s:qp['p_'+s]for s in ['over','under','push']}))
 data['rec']=dict(evaluation=rr,calibration=rr,gate_oof=None,prior=prior)
 ptweeks={};ptmeta={}
 for wk,(public,folder)in HIST.items():
  path=ROOT/public/'SCORES.json';scores=a.load(path);f=evidence/folder/'GRADED_COMPLETE_LEAF_LAWS.json.gz';raw=a.load(f)['graded'];bindings.append(dict(safe_id='B_WEEK'+str(wk)+'_COMPLETE_LAW_ROWS',sha256=a.sha(f),bytes=f.stat().st_size,public_scores=str(path.relative_to(ROOT)),public_scores_sha256=a.sha(path)))
  # The baseline recipe is chosen once from Week5, not Week8 accuracy.
  if wk==5:
   candidates=[r for r in scores if r['target']=='pass_td'and r['record_kind']=='prop_threshold_probability_evaluation'and r['brier']is not None];chosen=min(candidates,key=lambda r:(r['brier'],r['procedure_id'],r['history_regime']))
   assert chosen['procedure_id']==PT_PROCEDURE and chosen['history_regime']=='H-MULTI','Versioned preregistration required if the retained earliest-period winner changes'
   data['pt_baseline_choice']=dict(rule='Lowest retainedWeek5actual-lineBrier amongeightqualifiedBaseLeaf/C02/historylaws; fixedtiebreakfullID/history. NotchosenfromW8.',procedure_id=chosen['procedure_id'],history=chosen['history_regime'],earlier_brier=chosen['brier'],earlier_n=chosen['n'],candidates=[{k:r[k]for k in ['procedure_id','history_regime','n','brier']}for r in candidates])
  meta=next(r for r in scores if r['target']=='pass_td'and r.get('side')=='Combined'and r['procedure_id']==PT_PROCEDURE and r['history_regime']=='H-MULTI');rows=raw[meta['method_id']];ptmeta[wk]=meta
  ptweeks[wk]=[normalize(r,'B_PT_W8_TRANSFER','W'+str(wk)+':'+str(r['source_row_index']),r['probabilities'])for r in rows]
  prior_score=next(r for r in scores if r['record_kind']=='prop_threshold_probability_evaluation'and r['target']=='pass_td'and r['procedure_id']==PT_PROCEDURE and r['history_regime']=='H-MULTI');assert abs(lawmetrics.metrics(ptweeks[wk])['brier']-prior_score['brier'])<1e-12
 f=evidence/'week8-grading-20261102l/WEEK8_ORIGINAL_LAW_THRESHOLD_ROWS_V2.json.gz';lawrows=a.load(f)['rows'];bindings.append(dict(safe_id='B_WEEK8_RETAINED_ORIGINAL_LAW_ROWS_V2',sha256=a.sha(f),bytes=f.stat().st_size))
 f=evidence/'abc-b-20261103/LOCAL_GRADED_ROWS.json.gz';final=[r for r in a.load(f)['rows']if r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original'];bindings.append(dict(safe_id='B_CURRENT_FINAL_WEEK8_LABEL_BINDINGS',sha256=a.sha(f),bytes=f.stat().st_size,public_receipt='reports/abc-championship/local-week8-final-v1/RUN_RECEIPT.json'))
 final={ (r['game_id'],r['player_id'],r['target'],float(r['line'])):r for r in final};wanted=[r for r in lawrows if r['target']=='pass_td'and r['procedure_id']==PT_CAPTURE and r['history_regime']=='H-MULTI'];lookup={(r['game_id'],r['player_id'],r['target'],float(r['line'])):r for r in wanted};assert len(lookup)==len(wanted)
 # Reuse an original baseline mean only if it is bound to the exact capture.
 from tools import grade_week8_captured_library as library
 means={}
 for spec in library.packet_specs(evidence/'week8-grading-20261102l',ROOT/'reports/week8-grading-20261102l'):
  if spec['capture_version']!='C02':continue
  for r in a.load(spec['source_path'])['rows']:
   if r['target']=='pass_td'and r.get('product_id')=='mean'and r['procedure_id']==PT_CAPTURE and r['history_regime']=='H-MULTI':means[r['game_id'],r['player_id'],spec['source_sha256']]=r['prediction']
 current=[];current_prior=[]
 for key,q in sorted(final.items()):
  if q['target']!='pass_td':continue
  old=lookup.get(key);point=None
  if old:
   assert mechanism.epoch(old['forecast_issued_at'])<=mechanism.epoch(q['decision_time']);assert mechanism.epoch(old['forecast_persistence_at'])<=mechanism.epoch(q['decision_time']);point=means[old['game_id'],old['player_id'],old['source_forecast_sha256']]
  r=normalize(q,'B_PT_W8_TRANSFER','W8:'+str(q['source_row_index']),old['probabilities']if old else None,point=point);r['fallback']=old['fallback']if old else'NOT_RETAINED';current.append(r);current_prior.append(dict(r,probabilities=old['prior_probabilities']if old else None))
 assert len(current)==28;freeze=min(r['decision_epoch']for r in current);assert all(r['label_available']<freeze for wk in [5,6]for r in ptweeks[wk])
 assert max(r['label_available']for r in ptweeks[5])<min(r['decision_epoch']for r in ptweeks[7]);assert all(r['decision_epoch']<freeze for r in ptweeks[7])
 data['pass_td']=dict(evaluation=current,calibration=ptweeks[6],gate_oof=ptweeks[7],prior=current_prior,calibration_freeze=freeze,baseline_selection_rows=ptweeks[5]);data['source_bindings']=bindings
 a.gzsave(private/'PREPARED_INPUT_ROWS.json.gz',data,max_bytes=4*1048576)
 protocol=dict(id=VERSION,assignment_id='ABC-PREDICTIVE-IMPROVEMENT-01',at_utc=datetime.now(timezone.utc).isoformat(),state='FROZEN_BEFORE_NEW_CALIBRATION_FITS_GATES_OR_REPAIRED_SCORES',canonical_C_ref='39b98567cc11835363e91c6a2b504bf9cae1f17a',canonical_C_protocol_id='ABC-ACTUAL-PROP-CHAMPIONSHIP-v2-C-1',canonical_C_protocol_sha256='fa19581487519a854948269bc1ce328cbbcdc734afee2464f1ff778d1ff241a1',code_sha256=a.sha(__file__),mechanism_sha256=a.sha(ROOT/'nfl_v2/exact_line_repair.py'),input_rows_sha256=a.sha(private/'PREPARED_INPUT_ROWS.json.gz'),input_sources=bindings,
  mechanism=dict(formula='CDF_g(x)=sigmoid(logit(x)-alpha);pUnder=g(pUnder0),pPush=g(pUnder0+pPush0)-g(pUnder0),pOver=1-g(pUnder0+pPush0); exact0/1endpoints preserved.',fit='Oneintercept MAP, slopefixed1;sum_game(mean_player binarylogloss)+alpha^2/(2*0.5^2),alpha[-1.5,1.5], nohyperparamsearch. Traininghalfpointactualoffers only, min20decided/5games/3eachclass; otherwise identity. Irreparablezero-probability earlierlogloss staysidentity, no clipping.',availability='Same conservativekickoff+7days STRICTLYbeforeorigin, bothsourcevintage/availability assumptions disclosed; targetgame labels neverused. No authenticatedasof source-vintage claim.',source_histories='Crec B0 P3_HGB/H-MULTI/E0_OP unchanged. PT B0 C02/H-MULTI chosenfromW5Brier; W6actual-line calibrator training; W7temporalOOFconfidence-only gate preparation; W8originalcapturedlaw/currentfinal labels. Historicalknown-target-time andoriginalfuturecapture are explicitlydifferent registeredsource/queryproducts, testedas a declaredtransferadapter, notsameexactlegacyissuance.',calibration_times='Crec perdecisionbatch eligibleprefix; PTcoeff frozenbeforefirstW8kickoff. Actual coefficientfit occursnow, simulatedorigin separate; no backdating.',numerical='Receptionsdirecteventprocedure hasno ownpointoutput. PToriginalB0mean is separatelytyped unchangedancillaryoutput, not claimedmeanofpostprocessedlaw. Probabilitypostprocessor not a fullnewoutcomelaw.',
   gate='B2confidencequantile: medianearlier temporalOOFconfidence, floor0.60,min20earlierpredictions else0.60; no outcome used tofit thissimplegate. C updatesrolling; PTgatefrozenfromW7OOFpredictionsbeforeW8. Matchcountsperatomicdecisionbatch:K=min(ceil(0.5*availablebatch),eligibleB0,eligibleB1);selecteachownhighestconfidence withstableofferIDtie. No futurebatchneeded, no forcedweakpicks. Achievedcoverage reported, not assumed50%.',
   secondary='Fixed0.60/0.70/0.80/0.90confidence thresholds, allcases; rollinggreedyK6/10/20 percategory/week and combined/Over-only/Under-only, confidencefloor0.60, earliestbatchesfillremaining slots, no replacementafteroutcomes. These are new retrospectivepolicies, not originalpicks or fixedweeklylists.',target90='Fixedp>=0.90policy; report observedW/L,n,actualcoverage. ScientificTARGET_NOT_ESTABLISHED unless lower95%dependence-aware bound>=0.90 plus existingCmin100unique decided/20games/5weeks and prespecifiedlaterconfirmation; usefulnessplanningcoverage>=10%. These are claimcriteria, not a new provisionalreleasewaitinggate.',practical='Existingownerpolicyv6 hasno universal numericaccuracy switchfloor. Predeclare+1percentagepoint fullboard ormatched-coverage as studyplanningusefulness only, not autonomousrelease/admission or posthocveto.'),
  closest_prior=dict(C_study='C-2025-OOF-CALIBRATION-v3',C_source='protocol/OOF_CALIBRATION_V3.json',difference='C usedtwo-parameter sigmoid on2025syntheticgrids/P2Leaf withweak0.001penalty; Busesoneintercept/stronggameweightedprior, actual-lineearlierlabels, CdirectorC02capture baseline and chronologicalconfidencegate. Do not claimcalibrationitselfnew.',prior_losses='Crec synthetic-grid Brier0.1172677→0.1175754;pass_td0.1462724→0.1465855. Differentnormalization/population fromactual-offerBrier; preservelosses. BGLMandall64leaf-law cumulativeBriers lostactual-line0.25neutral.',A_market='Aownsmarketreceptionlead; publicaggregate206/320vs175/320onselected2024subset is not Bprivate-row reproduction. Exactearlierline/price/model exports required; no duplicate marketfit.'),
  panels=dict(rec=dict(requested_weeks=list(range(1,9)),actual_weeks=[2,3],outer_offers=len(rr),horizon='C_KICKOFF_RECONSTRUCTION',evidence_tier=a.TIER),pass_td=dict(requested_weeks=list(range(1,9)),evaluation_weeks=[8],baseline_selection_week=5,calibration_week=6,gate_prediction_week=7,outer_offers=28,horizon='B_ORIGINAL_EARLY_CAPTURE_PLUS_RETAINED_LATER_T90_THRESHOLDS',evidence_tier='ORIGINAL_BASE_FORECAST_WITH_NEW_RETROSPECTIVE_PROBABILITY_POLICY;QUOTE_CLOCK_UNVERIFIED')),
  exposure='Allperiodsalreadyresearch-exposed; baseline architectures and studychoice are exposed. Chronologicalfits/gatesdo not createfreshholdout; no 90%promise or originalissuance claim.',budget=dict(max_calibration_fits=32,max_base_model_fits=0,max_base_model_inference=0,max_wall_seconds=120,max_CPU_seconds=180,max_RSS_bytes=1073741824,max_new_private_bytes=4194304,max_threads=2,hyperparameter_searches=0,paid_calls=0),retention='Sameapprovedowner-localBroute; boundednewprivateinputs/models/rows, publiccode/aggregate/hash only; no offhostrestoreclaim. Originalarchive/largefitrecoverygate unchanged.',production='No publication/scheduler/owneradmission/merge. Ccoordinates; A/Ctasks not duplicated; no externalmessages. Newfuturecapture requires candidate-specificsource/runtime/retention/admission underexistingownerroute.')
 a.save(out/'FROZEN_PROTOCOL.json',protocol);a.save(out/'ADOPTED_ASSIGNMENT.json',dict(assignment_id='ABC-PREDICTIVE-IMPROVEMENT-01',role='B',adoption='NormalizedBexecutionregistration, not byte-for-bytehash ofchatmessage; additive tofa195814canonicalchampionship, not a newmasterprotocol.',scope='Oneprobabilityrepairmechanism andsimpleconfidencegate; Aownsroleallocation, Cownstargetshare/NGS/commonintake.',protocol_sha256=a.sha(out/'FROZEN_PROTOCOL.json'),other_sessions_received='NOT_ASSUMED_FROM_USER_MESSAGE'))
 print(json.dumps(dict(state='PREPARED_NO_NEW_FITS',rec_rows=len(rr),pt_eval_rows=len(current),pt_calibration_rows=len(ptweeks[6]),pt_gate_rows=len(ptweeks[7]),private_bytes=(private/'PREPARED_INPUT_ROWS.json.gz').stat().st_size,protocol_sha256=a.sha(out/'FROZEN_PROTOCOL.json'))))

def run(private,out):
 start=time.monotonic();cpu=time.process_time();binding=a.load(out/'CURRENT_EXECUTION_BINDING.json')if(out/'CURRENT_EXECUTION_BINDING.json').exists()else dict(protocol='FROZEN_PROTOCOL.json',inputs='PREPARED_INPUT_ROWS.json.gz');protocol=a.load(out/binding['protocol']);assert a.sha(__file__)==protocol['code_sha256']and a.sha(ROOT/'nfl_v2/exact_line_repair.py')==protocol['mechanism_sha256'];assert a.sha(private/binding['inputs'])==protocol['input_rows_sha256'];data=a.load(private/binding['inputs']);models={};fit_calls=0;applications=0
 def model(pool,t,target):
  nonlocal fit_calls
  train=mechanism.eligible_training(pool,t);key=digest([target,sorted(r['offer_id']for r in train)])
  if key not in models:
   before=time.monotonic();m=mechanism.fit(pool,t);fit_calls+=int(m['fit_performed']);assert fit_calls<=32;m.update(model_id=key,actual_computed_at_utc=datetime.now(timezone.utc).isoformat(),fit_wall_seconds=time.monotonic()-before,target=target);models[key]=m
  return models[key]
 def applied(r,m):
  nonlocal applications
  q=mechanism.repair(r['probabilities'],m['alpha']);applications+=int(q is not None);return dict(r,probabilities=q,repair_model_id=m['model_id'],repair_state=m['state'])
 results=[];fitusage=[];curves=[];scores=[];proper=[];paired=[];diagnostics=[]
 for target in ['pass_td','rec']:
  d=data[target];history={0:[],1:[]};prepared=[]
  if target=='pass_td':
   for r in sorted(d['gate_oof'],key=lambda x:(x['decision_epoch'],x['offer_id'])):
    m=model(d['calibration'],r['decision_epoch'],target);q=applied(r,m);history[0].append(r);history[1].append(q)
   fixed=model(d['calibration'],d['calibration_freeze'],target)
  # Every atomic batch uses only its original decision-time information.
  batches=collections.defaultdict(list)
  for r in d['evaluation']:batches[r['decision_epoch']].append(r)
  kslots=collections.defaultdict(int)
  for t,batch in sorted(batches.items()):
   m=fixed if target=='pass_td'else model(d['calibration'],t,target);frozen_t=d['calibration_freeze']if target=='pass_td'else t;thresholds={k:mechanism.gate_threshold(history[k],frozen_t)for k in [0,1]};arms={0:[dict(r,repair_state='UNCHANGED_BASELINE',repair_model_id=None)for r in batch],1:[applied(r,m)for r in batch]}
   for r in arms[1]:assert m['latest_label_available']is None or m['latest_label_available']<frozen_t
   qualified={k:sorted([r for r in rr if r['probabilities']is not None and mechanism.confidence(r['probabilities'])>=thresholds[k]],key=lambda r:(-mechanism.confidence(r['probabilities']),r['offer_id']))for k,rr in arms.items()};quota=min(math.ceil(.5*sum(r['probabilities']is not None for r in batch)),len(qualified[0]),len(qualified[1]));members={k:{r['offer_id']for r in qualified[k][:quota]}for k in arms}
   for arm,rr in arms.items():
    for policy in ['ALL','B2_MATCHED_EARLIER_CONFIDENCE','CONF_0.60','CONF_0.70','CONF_0.80','CONF_0.90']+[f'ROLLING_K{k}_{side}'for k in [6,10,20]for side in ['Combined','over','under']]:
     chosen=None
     if policy.startswith('ROLLING_K'):
      quota_text,side=policy.split('_')[1:];K=int(quota_text[1:]);eligible=sorted([r for r in rr if r['probabilities']is not None and mechanism.confidence(r['probabilities'])>=.6 and(side=='Combined'or mechanism.choose(r['probabilities'])==side)],key=lambda r:(-mechanism.confidence(r['probabilities']),r['offer_id']));slot=(arm,rr[0]['week'],policy);chosen={r['offer_id']for r in eligible[:max(0,K-kslots[slot])]};kslots[slot]+=len(chosen)
     for r in rr:
      side=mechanism.choose(r['probabilities']);keep=side is not None
      if policy=='B2_MATCHED_EARLIER_CONFIDENCE':keep=r['offer_id']in members[arm]
      elif policy.startswith('CONF_'):keep=keep and mechanism.confidence(r['probabilities'])>=float(policy.split('_')[1])
      elif chosen is not None:keep=r['offer_id']in chosen
      q=dict(r,method_key=f'B::{VERSION}::{target}::B{arm}',selected_side=side if keep else None,side=side if keep else None,original_side=None,selection_policy=policy,gate_threshold=thresholds[arm]if policy=='B2_MATCHED_EARLIER_CONFIDENCE'else None)
      q=core.grade([q],strategies=('original',))[0]
      if q['probabilities']is None:q['statistical_state']='UNAVAILABLE_FORECAST';q['fallback']='NOT_RETAINED'
      results.append(q)
   fitusage.append(dict(target=target,decision_epoch=t,simulated_calibration_cutoff=frozen_t,model_id=m['model_id'],training_latest_available=m['latest_label_available'],gate_thresholds=thresholds,matched_K=quota,batch_offers=len(batch),model_state=m['state']))
   if target=='rec':
    for arm in [0,1]:history[arm]+=arms[arm]
  targetrows=[r for r in results if r['target']==target];weeks=sorted({r['week']for r in targetrows});views=[str(w)for w in weeks]+(['ALL']if len(weeks)>1 else[])
  for arm in [0,1]:
   name=f'B::{VERSION}::{target}::B{arm}';allrows=[r for r in targetrows if r['method_key']==name];policies=sorted({r['selection_policy']for r in allrows})
   for policy in policies:
    pool=[r for r in allrows if r['selection_policy']==policy]
    for wk in views:
     rr=[r for r in pool if wk=='ALL'or r['week']==int(wk)];panel=f'{VERSION}:{target}:{policy}';meta=dict(history_regime='H-MULTI',information_policy='PRESERVED_BASELINE_SOURCE_POLICY_PLUS_EARLIER_ACTUAL_LINE_CALIBRATION',product_id='exact_line_probability_product',base_procedure_id='C::P3_HGB/H-MULTI/E0_OP'if target=='rec'else'B::C02/H-MULTI_W5_SELECTED_TRANSFER_TO_W8_CAPTURE',decision_rule=policy,probability_conditioning='MODELED_APPEARANCE',bookmaker_nonvoid_conditioning='UNESTABLISHED',point_functional='NO_RECEPTION_DIRECT_POINT;PT_ORIGINAL_B0_MEAN_ANCILLARY_NOT_REPAIRED_LAW_MEAN');ss=a.score(rr,name,target,wk,meta,panel)
     for v in ss:
      v.update(strategy=policy,evidence='NEW_EXPERIMENT'if arm or policy!='ALL'else'REPRODUCED_FROM_DATA',selection_evidence='RETROSPECTIVE_RULE_REPLAY',horizon_id=protocol['panels'][target]['horizon'],cohort_id='FULL_SOURCE_OFFER_BOARD_WITH_MISSING_FORECASTS_RETAINED',actual_repair_fit_time='CURRENT_EXECUTION_NOT_HISTORICAL_ISSUANCE');sub=[r for r in rr if r['selected_side']and(v['side']=='Combined'or r['selected_side']==v['side'])];v['selection_metrics']['probability_scores']=lawmetrics.metrics(sub);v['selection_metrics']['probability_scope']='SELECTED_SUBSET;FULL_BOARD_PROPER_SCORE_SEPARATE';v['selection_metrics']['repair_identity_fallback_rows']=sum(r['probabilities']is not None and r['repair_state'].startswith('IDENTITY')for r in rr);v['selection_metrics']['source_fallback_scope']='Originalfootballfallback separatefromrepairidentityfallback; unavailablequeriesnotrepairfallback.'
     scores+=ss
     if policy=='ALL':
      pm=lawmetrics.metrics(rr);proper.append(dict(record_id='B-REPAIR-PROB-'+digest([target,arm,wk])[:24],record_kind='prop_threshold_probability_evaluation',procedure_id=name,history_regime='H-MULTI',product_id='exact_line_probability_product',target=target,season=2026,week=wk,evaluation_seasons=[2026],evaluation_weeks=weeks if wk=='ALL'else[int(wk)],evaluation_panel_id=panel,horizon_id=protocol['panels'][target]['horizon'],evidence='NEW_EXPERIMENT'if arm else'REPRODUCED_FROM_DATA',evidence_tier=a.TIER,forecast_rows=len(rr),admitted_forecast_rows=sum(r['probabilities']is not None for r in rr),probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',bookmaker_nonvoid_conditioning='UNESTABLISHED',**{k:pm[k]for k in ['n','brier','log_loss','infinite_log_losses','null_reason']}))
  for policy in sorted({r['selection_policy']for r in targetrows}):
   for wk in views:
    aa=[r for r in targetrows if r['method_key'].endswith('::B1')and r['selection_policy']==policy and(wk=='ALL'or r['week']==int(wk))];bb=[r for r in targetrows if r['method_key'].endswith('::B0')and r['selection_policy']==policy and(wk=='ALL'or r['week']==int(wk))];paired.append(a.pair(aa,bb,target,f'B::{VERSION}::{target}::B1','UNCHANGED_B0',wk,policy))
  # Full-board constants and the unmodified earlier role/prior reference.
  for cid in ['ALWAYS_OVER','ALWAYS_UNDER','EARLIER_SOURCE_PRIOR']:
   pool=[]
   for r in d['prior']if cid=='EARLIER_SOURCE_PRIOR'else d['evaluation']:
    p=r['probabilities']if cid=='EARLIER_SOURCE_PRIOR'else dict(over=.5,under=.5,push=0.);side=mechanism.choose(p)if cid=='EARLIER_SOURCE_PRIOR'else'over'if cid=='ALWAYS_OVER'else'under';q=dict(r,probabilities=p,selected_side=side,side=side,original_side=None,repair_state='REFERENCE');q=core.grade([q],strategies=('original',))[0]
    if p is None:q['statistical_state']='UNAVAILABLE_FORECAST'
    pool.append(q)
   for wk in views:
    rr=[r for r in pool if wk=='ALL'or r['week']==int(wk)];controlviews=a.score(rr,f'B::{VERSION}::{target}::{cid}',target,wk,dict(history_regime='EARLIER_REFERENCE',product_id='constant_side_or_original_prior',decision_rule=cid),f'{VERSION}:{target}:CONTROL')
    for view in controlviews:view['strategy']=cid
    scores+=controlviews
    for arm in [0,1]:
     aa=[r for r in targetrows if r['method_key'].endswith('::B'+str(arm))and r['selection_policy']=='ALL'and(wk=='ALL'or r['week']==int(wk))];paired.append(a.pair(aa,rr,target,f'B::{VERSION}::{target}::B{arm}',cid,wk,'FULL_BOARD_COMMON_DECIDED'))
  for arm in [0,1]:
   for wk in views:
    rr=[r for r in targetrows if r['method_key'].endswith('::B'+str(arm))and r['selection_policy']=='ALL'and(wk=='ALL'or r['week']==int(wk))];vv=[r for r in rr if r['probabilities']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];bins=[]
    for lo,hi in [(0,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.000000001)]:
     rows=[r for r in vv if lo<=r['probabilities']['over']<hi];bins.append(dict(lo=lo,hi=min(hi,1.),n=len(rows),mean_probability=sum(r['probabilities']['over']for r in rows)/len(rows)if rows else None,over_frequency=sum(r['actual']>r['line']for r in rows)/len(rows)if rows else None))
    from sklearn.metrics import roc_auc_score
    ys=[int(r['actual']>r['line'])for r in vv];auc=float(roc_auc_score(ys,[r['probabilities']['over']for r in vv]))if len(set(ys))==2 else None;diagnostics.append(dict(target=target,arm=arm,week=wk,n=len(vv),over_auc=auc,reliability_bins=bins,mean_predicted_over=sum(r['probabilities']['over']for r in vv)/len(vv)if vv else None,actual_over_rate=sum(ys)/len(ys)if ys else None,auc_scope='Globalmonotoneintercept preserves within-fit ranking; changingrollingfits may alter pooled ranks. Diagnostic not proof ofcausality.'))
 a.save(out/'SCORES.json',scores+proper);a.save(out/'PAIRED_COMPARISONS.json',paired);a.save(out/'DISCRIMINATION_RELIABILITY.json',diagnostics);a.save(out/'FIT_USAGE_AND_CUTOFFS.json',fitusage);a.save(out/'SIDE_TABLE.json',saved.wide(scores));saved.write_csv(out/'SIDE_TABLE.csv',saved.wide(scores))
 a.gzsave(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz',dict(models=models,rows=results),max_bytes=4194304-sum(p.stat().st_size for p in private.iterdir()if p.is_file()));privatebytes=sum(p.stat().st_size for p in private.iterdir()if p.is_file());assert privatebytes<=4194304
 a.save(out/'MODEL_MANIFEST.json',dict(models=[{k:v for k,v in m.items()if k!='alpha'}for m in models.values()],private_models_rows_sha256=a.sha(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz'),private_models_rows_bytes=(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz').stat().st_size,parameter_retention='Completecoefficients inapprovedowner-localstore; publicsafehashes andindependentverifiedcounts only; no offhostrestoreclaim.'))
 receipt=dict(state='COMPLETE_B_CONTROLLED_REPAIR_AND_GATE_EXPERIMENT_NOT_C_ADMITTED',assignment_id=VERSION,new_calibrator_fits=fit_calls,new_base_model_fits=0,new_base_model_inference=0,calibration_probability_applications=applications,new_issued_forecasts=0,new_NFL_observations=0,source_panels=['C_REC_W2_W3','B_PT_W8_TRANSFER'],side_views=len(scores),proper_views=len(proper),new_private_bytes=privatebytes,wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,code_sha256=a.sha(__file__),module_sha256=a.sha(ROOT/'nfl_v2/exact_line_repair.py'));assert receipt['wall_seconds']<=120 and receipt['cpu_seconds']<=180 and receipt['peak_RSS_bytes']<=1073741824;a.save(out/'RUN_RECEIPT.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare(*map(Path,sys.argv[2:6]))
 else:run(*map(Path,sys.argv[2:4]))
