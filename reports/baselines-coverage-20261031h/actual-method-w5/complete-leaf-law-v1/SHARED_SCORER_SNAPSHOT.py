"""Append complete retained-leaf P2 laws through the existing exact grader."""
import argparse,collections,gzip,hashlib,json,math,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as core,scoring
from nfl_v2.saved_leaf_law_lookup import from_payload
from nfl_v2.shared_subgroups import canonical,sha,now,write
from tools.numerical_championship import csvwrite
VERSION='v2-complete-retained-leaf-law-actual-threshold-v1'

def prepare(a):
 if a.output.exists()or a.private_output.exists():raise ValueError('fresh law-coverage outputs required')
 a.output.mkdir(parents=True);a.private_output.mkdir(parents=True);pp=json.loads((a.parent/'FROZEN_PROTOCOL.json').read_bytes());receipt=json.loads((a.parent/'RUN_RECEIPT.json').read_bytes())
 p=dict(version=VERSION,panel=a.panel,at=now(),state='FROZEN_BEFORE_NEW_LEARNED_LAW_DIRECTIONS_AND_PROPER_SCORES',code_sha256=sha(__file__),core_sha256=sha(core.__file__),scoring_sha256=sha(scoring.__file__),lookup_code_sha256=sha(Path(scoring.__file__).with_name('saved_leaf_law_lookup.py')),parent_protocol_sha256=sha(a.parent/'FROZEN_PROTOCOL.json'),parent_main_scores_sha256=sha(a.parent/'SCORES.json'),parent_grade_sha256=sha(a.parent_private/'GRADED_METHOD_ROWS.json.gz'),parent_plans_sha256=sha(a.parent_private/'FROZEN_SELECTIONS_AND_K.json.gz'),augmentation_sha256=sha(a.augmentation),augmentation_member=a.augmentation.name,law_lookup_receipt_sha256=sha(a.root/'reports/completion-20261031g/law-recovery/v1/RUN_RECEIPT.json'),outer_offers=receipt['source_offers'],week=6 if a.panel=='W6'else 7,rolling=a.panel!='F7',selection='P2choose higher P(Y>line) vsP(Y<line),tiesabstain; nochange P1/GLM or oldprobabilities. Merge newly recovered learnedhistogram law with alreadyretained eligiblefallback law vectors for sameoriginalrecipe.',proper='Alleligiblelaws includingdirectionties scored halfmulticlassBrierOverUnderPush andcategoricalactualregionlogloss; truezeros→Infinity, no smoothing.',conditioning='MODELED_APPEARANCE',bookmaker_nonvoid_conditioning='UNESTABLISHED',numeric_rule='CDFprobabilities mustbein[-1e-12,1+1e-12],sum1±1e-12; onlymachineepsilonboundary dust canonicalized to0/1, thennormalized. No substantive tailfloor or forecast/line rounding.',K='K6/10/20 percategory/procedure/history,Combined/Over/Under. F7fixed13gameasof; W6/W7rollinggreedybatches,onlyavailablecandidates,remainingslots. Rankselectedwinprobability/stablesourceindex. Freeze beforenewactualgrading.',comparison='Reuseparentmatchedwebsite/raw/original/alwayscontrolmask views, alreadyhaveK; no duplicatedcontrol grading. Fullsourceuniverse/missingforecasts retained.',exposure='Alreadyexposed research football outcomes/quotes; newlearned-law propermetrics frozenbeforecalculation, not untouchedholdout.',budget=dict(wall_seconds=300,max_RSS_bytes=1073741824,max_private_bytes=16777216,max_threads=2),new_fits=0,new_model_inference=0,new_issued_forecasts=0,Week8_outcomes_read=0)
 write(a.output/'FROZEN_PROTOCOL.json',p);(a.output/'SOURCE_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(dict(state=p['state'],sha256=sha(a.output/'FROZEN_PROTOCOL.json'))))

def run(a):
 p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes());start,cpu=time.monotonic(),time.process_time()
 if sha(__file__)!=p['code_sha256']or sha(core.__file__)!=p['core_sha256']or sha(a.augmentation)!=p['augmentation_sha256']:raise ValueError('frozen lawcoverage source changed')
 def guard():
  if time.monotonic()-start>300 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('bounded lawcoverage wave')
 old=json.loads(gzip.decompress((a.parent_private/'FROZEN_SELECTIONS_AND_K.json.gz').read_bytes()));oldg=json.loads(gzip.decompress((a.parent_private/'GRADED_METHOD_ROWS.json.gz').read_bytes()));base={};groups=collections.defaultdict(dict);pointmasks={}
 for tag,pl in old['plans'].items():
  t,proc,h,product=pl['recipe']
  for r in oldg['graded'][tag]:base[r['source_row_index']]=r
  if 'ordered_leaf_cdf'not in proc and 'c02'not in proc:continue
  k=(t,proc,h)
  if pl['rule']=='P1':
   ids={r['source_row_index']for r in pl['rows']if r['admitted']}
   if k in pointmasks and pointmasks[k]!=ids:raise ValueError('mean/median admission mismatch')
   pointmasks[k]=ids
  elif pl['rule']=='P2':
   for r in pl['rows']:
    if r['admitted']:groups[k][r['source_row_index']]=dict(probabilities=r['probabilities'],source='REUSED_ELIGIBLE_FALLBACK_LAW')
 aug=json.loads(gzip.decompress(a.augmentation.read_bytes()));learned=0
 for r in aug['rows']:
  k=(r['target'],r['procedure_id'],r['history_regime']);idx=r['source_row_index'];b=base[idx]
  if(r['game_id'],r['player_id'],r['population'],r['position'])!=(b['game_id'],b['player_id'],b['population'],b['position']):raise ValueError('law source identity mismatch')
  if scoring.exact_decimal(r['line'])!=scoring.exact_decimal(b['line']):raise ValueError('law line mismatch')
  if idx in groups[k]:raise ValueError('learned/fallback law duplicated')
  law=from_payload(r['params']);L=scoring.exact_decimal(b['line']);n=int(L.to_integral_value(rounding='ROUND_FLOOR'));f=law.cdf(n);under=law.cdf(n-1)if L==n else f;pp=dict(over=1-f,under=under,push=f-under if L==n else 0.)
  if min(pp.values())< -1e-12 or max(pp.values())>1+1e-12 or abs(sum(pp.values())-1)>1e-12:raise ValueError('law probability complement failure')
  pp={s:max(0.,min(1.,v))for s,v in pp.items()};total=sum(pp.values());pp={s:v/total for s,v in pp.items()};groups[k][idx]=dict(probabilities=pp,source='RECOVERED_SAVED_LEAF_IDS_HISTOGRAM_NO_MODEL_INFERENCE');learned+=1
 plans={};Kplans=[];controls=[]
 for k,dd in sorted(groups.items()):
  t,proc,h=k
  if set(dd)!=pointmasks[k]:raise ValueError('complete law coverage differs from parentadmitted point mask')
  tag='LEAF-'+hashlib.sha256(canonical([a.panel,k])).hexdigest()[:18];rows=[]
  for idx,b in sorted(base.items()):
   if b['target']!=t:continue
   pp=dd[idx]['probabilities']if idx in dd else None;side='over'if pp and pp['over']>pp['under']else'under'if pp and pp['under']>pp['over']else None;rows.append(dict(source_row_index=idx,admitted=pp is not None,probabilities=pp,selected_side=side,rank=max(pp['over'],pp['under'])if pp else None,decision_time=b.get('source_server_clock',b['server_retained_by']),source=dd[idx]['source']if idx in dd else'UNAVAILABLE'))
  plans[tag]=dict(recipe=k,rows=rows)
  ids=sorted(dd)
  for ctag,cp in old['controls'].items():
   if cp['target']==t and cp['admitted_ids']==ids:controls.append(dict(method_id=tag,control_id=ctag,control=cp['control'],parent_score_sources='Parent main and supplemental score manifest; sameadmittedmask/Kcontrols retained'))
  for scope in('Combined','over','under'):
   rr=[r for r in rows if r['selected_side']and(scope=='Combined'or r['selected_side']==scope)]
   for K in(6,10,20):
    if p['rolling']:
     chosen=[]
     for clock in sorted({r['decision_time']for r in rr}):chosen.extend(sorted((r for r in rr if r['decision_time']==clock),key=lambda r:(-r['rank'],r['source_row_index']))[:max(0,K-len(chosen))])
    else:chosen=sorted(rr,key=lambda r:(-r['rank'],r['source_row_index']))[:K]
    Kplans.append(dict(method_id=tag,K=K,scope=scope,eligible=len(rr),source_indices=[r['source_row_index']for r in chosen]))
 frozen=gzip.compress(canonical(dict(plans=plans,Kplans=Kplans,controls=controls)),mtime=0)
 with(a.private_output/'FROZEN_LAW_DIRECTIONS_K.json.gz').open('xb')as f:f.write(frozen)
 write(a.output/'SELECTION_FREEZE_RECEIPT.json',dict(at=now(),before_new_proper_score_and_grade=True,sha256=sha(a.private_output/'FROZEN_LAW_DIRECTIONS_K.json.gz'),procedures_history_target_laws=len(plans),topK_lists=len(Kplans)))
 # Official outcomes and old source grades were not used to select directions/K.
 graded={};proper=[];lossmap={};scores=[];checks=[];cohorts=core.cohort_names(list(base.values()))
 def metrics(rr):
  losses=[lossmap[r['method_id'],r['source_row_index']]for r in rr if(r['method_id'],r['source_row_index'])in lossmap];n=len(losses);inf=sum(x[1]=='Infinity'for x in losses);return dict(n=n,brier=math.fsum(x[0]for x in losses)/n if n else None,log_loss='Infinity'if inf else math.fsum(x[1]for x in losses)/n if n else None,infinite_log_losses=inf,conditioning='MODELED_APPEARANCE',bookmaker_nonvoid_conditioning='UNESTABLISHED',score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',null_reason=None if n else'NO_QUALIFIED_LAW_AND_ACTUAL_ROWS')
 for tag,pl in plans.items():
  rr=[];t,proc,h=pl['recipe']
  for z in pl['rows']:
   b=base[z['source_row_index']];state='ABSTAIN'if z['selected_side']is None else'UNKNOWN_PARTICIPATION'if b['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL'else'MISSING_ACTUAL'if b['actual']is None else scoring.threshold_crossing(b['actual'],b['line'],z['selected_side'],target=t);r=dict(b,**z,method_id=tag,statistical_state=state,settlement_state='UNRESOLVED_CONTRACT',ranking_point=None,net_return=None);rr.append(r)
   if z['admitted']and b['actual']is not None and b['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL':
    y='over'if scoring.exact_decimal(b['actual'])>scoring.exact_decimal(b['line'])else'under'if scoring.exact_decimal(b['actual'])<scoring.exact_decimal(b['line'])else'push';pp=z['probabilities'];loss=.5*sum((pp[s]-int(s==y))**2 for s in('over','under','push'));log=-math.log(pp[y])if pp[y]>0 else'Infinity';lossmap[tag,z['source_row_index']]=(loss,log)
  graded[tag]=rr;pm=metrics(rr);proper.append(dict(record_id='LEAF-PROB-'+tag,record_kind='prop_threshold_probability_evaluation',procedure_id=proc+':known-target-time-v1',history_regime=h,product_id='actual_line_categorical_law',law_coverage_version='COMPLETE_RETAINED_LEAF_AND_FALLBACK_V1',target=t,population='original_full_provider_labelled_offer_pool',season=2026,week=p['week'],evaluation_seasons=[2026],evaluation_weeks=[p['week']],evaluation_panel_id=VERSION+':'+a.panel,n=pm['n'],forecast_rows=len(rr),admitted_forecast_rows=sum(r['admitted']for r in rr),brier=pm['brier'],log_loss=pm['log_loss'],infinite_log_losses=pm['infinite_log_losses'],mae=None,mse=None,probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',bookmaker_nonvoid_conditioning='UNESTABLISHED',evidence='NEW_EXPERIMENT_RESTORED_SAVED_LAW_LOOKUP',null_reason=pm['null_reason'],source_law='ExactsavedleafIDs→retainednormalizedhistogram+5%originalsupportprior, no newmodel execution; parameters andclocks sourcebound.'))
  def emit(pool,chosen,cohort,K=None,scope=None,rankeligible=None):
   views=[]
   for side in('over','under','Combined'):
    zz=[r for r in chosen if side=='Combined'or r['selected_side']==side];s=core.score_row(zz,pool,strategy=tag,target=t,cohort=cohort,side=side,K=K,rank_scope=scope,rank_eligible=rankeligible);s.update(record_id='LEAF-SELECT-'+hashlib.sha256(canonical([a.panel,tag,cohort,K,scope,side])).hexdigest()[:24],procedure_id=proc+':known-target-time-v1',history_regime=h,product_id='saved_complete_leaf_law',law_coverage_version='COMPLETE_RETAINED_LEAF_AND_FALLBACK_V1',decision_rule='P2',method_id=tag,evaluation_panel_id=VERSION+':'+a.panel,time_panel_id='2026W'+str(p['week'])+('_ROLLING_T90_14GAMES'if p['rolling']else'_FIXED_F_13GAMES'),season=2026,week=p['week'],evaluation_seasons=[2026],evaluation_weeks=[p['week']],selection_evidence='RETROSPECTIVE_RULE_REPLAY',source_vintage='Current/revisedfootballinputs plus authenticated snapshot metadata; exactconditionalappearance law, no sportsbooksettlementclaim');s['selection_metrics']['probability_scores']=metrics(zz);s['selection_metrics'].update(admitted_forecast_opportunities=sum(r['admitted']for r in pool),unavailable_forecast_opportunities=sum(not r['admitted']for r in pool),admitted_rule_abstentions=sum(r['admitted']and r['selected_side']is None for r in pool));scores.append(s);views.append(s)
   core.check_triplet(views);checks.append([tag,cohort,K,scope])
  for cohort in cohorts:
   pool=[r for r in rr if core.in_cohort(r,cohort)];emit(pool,[r for r in pool if r['selected_side']],cohort)
  lookup={r['source_row_index']:r for r in rr}
  for k in Kplans:
   if k['method_id']==tag:emit(rr,[lookup[i]for i in k['source_indices']],'ROLLING_GREEDY_TOP_PICK_SUBSET'if p['rolling']else'FIXED_PARTIAL_WEEK_TOP_PICK_SUBSET',k['K'],k['scope'],k['eligible'])
  guard()
 blob=gzip.compress(canonical(dict(graded=graded,proper_losses=[dict(method_id=k[0],source_row_index=k[1],brier=v[0],log_loss=v[1])for k,v in lossmap.items()])),mtime=0)
 with(a.private_output/'GRADED_COMPLETE_LEAF_LAWS.json.gz').open('xb')as f:f.write(blob)
 if sum(x.stat().st_size for x in a.private_output.iterdir()if x.is_file())>16777216:raise RuntimeError('private lawderivative cap')
 main=[r for r in scores if r['cohort_id']=='ALL'and r['K']is None]+proper;write(a.output/'SCORES.json',main);supp=[]
 for target in core.TARGETS:
  ss=[r for r in scores if r['target']==target and not(r['cohort_id']=='ALL'and r['K']is None)];folder=a.output/('category-'+target);folder.mkdir();write(folder/'SCORES.json',ss);supp.append(dict(path=(folder/'SCORES.json').resolve().relative_to(a.root).as_posix(),sha256=sha(folder/'SCORES.json'),rows=len(ss)))
 write(a.output/'SUPPLEMENTAL_SCORE_ARTIFACTS.json',supp);write(a.output/'MATCHED_PARENT_CONTROL_LINKS.json',controls);write(a.output/'SIDE_RECONCILIATION.json',dict(triplets=len(checks),checks=checks));csvwrite(a.output/'ALL_METHOD_SIDES.csv',[r for r in main if r['record_kind']=='prop_selection_evaluation']);csvwrite(a.output/'ALL_LAW_SCORES.csv',proper)
 rec=dict(state='COMPLETE_RETAINED_LEAF_ACTUAL_THRESHOLD_P2_COVERAGE_EXTENSION',at=now(),panel=a.panel,source_offers=p['outer_offers'],newly_recovered_learned_law_rows=learned,allqualified_law_and_actual_rows=len(lossmap),complete_procedure_history_target_laws=len(plans),main_score_views=len(main),supplement_score_views=sum(r['rows']for r in supp),score_views=len(main)+sum(r['rows']for r in supp),score_sha256=sha(a.output/'SCORES.json'),private_derivative_bytes=sum(x.stat().st_size for x in a.private_output.iterdir()if x.is_file()),new_fits=0,new_model_inference=0,new_issued_forecasts=0,new_NFL_observations=0,Week8_outcomes_read=0,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024));write(a.output/'RUN_RECEIPT.json',rec);print(json.dumps(rec))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--panel',choices=('F7','W6','W7'),required=True);p.add_argument('--parent',type=Path,required=True);p.add_argument('--parent-private',type=Path,required=True);p.add_argument('--augmentation',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--private-output',type=Path,required=True);a=p.parse_args();prepare(a)if a.action=='prepare'else run(a)
