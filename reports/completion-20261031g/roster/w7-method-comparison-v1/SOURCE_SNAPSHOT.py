"""Shared-grader threshold comparison of temporally admitted retained methods."""
from __future__ import annotations
import argparse,collections,csv,gzip,hashlib,json,math,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as core,scoring
from nfl_v2.distribution_laws import Law
from nfl_v2.shared_subgroups import packet_rows,canonical,sha,now,write
from tools.numerical_championship import csvwrite,proc_id,product_id
VERSION='v2-admitted-methods-actual-threshold-W7-20261031g-v1'
CONTROLS=('original','SAVED_ADJUSTED_POINT_DIRECTION_RETAINED_PRECISION','SAVED_RAW_PROJECTION_DIRECTION_RETAINED_PRECISION','alwaysOver','alwaysUnder')

def prepare(a):
 if a.output.exists()or a.private_output.exists():raise ValueError('fresh outputs required')
 a.output.mkdir(parents=True);a.private_output.mkdir(parents=True)
 admission=json.loads((a.admission/'RUN_RECEIPT.json').read_bytes());ap=json.loads((a.admission/'FROZEN_PROTOCOL.json').read_bytes());mask=a.admission_private/'ADMISSIBILITY_MASK.json.gz'
 if sha(mask)!=admission['mask_sha256']:raise ValueError('admission mask changed')
 p=dict(version=VERSION,state='FROZEN_BEFORE_NEW_DIRECTIONS_OR_LINE_PROBABILITY_LOSSES',at=now(),code_sha256=sha(__file__),core_sha256=sha(core.__file__),scoring_sha256=sha(scoring.__file__),law_sha256=sha(Path(scoring.__file__).with_name('distribution_laws.py')),admission_protocol_sha256=sha(a.admission/'FROZEN_PROTOCOL.json'),admission_summary_sha256=admission['summary_sha256'],mask_sha256=admission['mask_sha256'],joined_sha256=sha(a.joined),selector_sha256=sha(a.root/'reports/championship-20261030f/category-selector-v2/DECISIONS.json'),decision_time=ap['decision_time'],outer_universe=462,raw_sources=ap['raw_sources'],selection=dict(P1='Originalunrounded saved compatiblepoint >line=>Over,<line=>Under,equalityabstain; failedtiming/missingforecasts remainunavailable in fullpool.',P2='Choosehigher P(Y>line) versus P(Y<line),tieabstain; retainpushmass. Only fullsavedparametric/fallbacklaw parameters admitted; leaf_idswithoutweights unavailable.',composites='Reuse exact earlier-selected W7 choices from frozenFcategoryselector. No routing around missing/ineligible chosenforecast. Not newlearners or originalissuedpolicies.'),conditioning='STATISTICAL_CONDITIONAL_MODELED_APPEARANCE;BOOKMAKER_NONVOID_UNVERIFIED;NO_PRICE_OR_EV',probability_score='Allqualified law/outcome rows includingdirectionties: half3classBrier=0.5*sum((pj-Ij)^2); categoricallogloss=-log(actualregionmass),retainInfinity/zero mass failures. NotPMF atactualY.',topK='K6/10/20 percategory and method/control, Combined/Over-only/Under-only; fixedpartial13gameasofreconstruction at commondecisionclock, notoriginallyissued or executablebookquote. P1within-categoryabsoluteunroundedpoint-linegap; P2selectedwinprobability; stable source rowindex tie. Freeze memberships before decoding joinedactuals.',cohorts='Reuse existingF source_cohorts exactly; originalpicked/abstained and positions separate; no reranking by outcomes.',comparators='Websiteadjusted/raw/original/alwaysOver/alwaysUnder on exactsame admittedmethod masks. Dedup equalmask/control views with explicit links; fulltargetuniverse and failures separately retained.',uncertainty='Existing500wholegame bootstrapseed1703;>=8decidedgames, no weekCI(singleweek). Paired selectedcommondecisive diagnostics, notselectionadjusted.',exposure='AllF2026W7outcomes already exposed; newmethod-direction/probability scores frozenbeforecalculation, notfreshholdout.',budget=dict(wall_seconds=300,max_RSS_bytes=1073741824,max_threads=2,max_private_bytes=16777216),new_fits=0,new_inference=0,new_issued_forecasts=0,Week8_outcomes_read=0)
 write(a.output/'FROZEN_PROTOCOL.json',p);(a.output/'SOURCE_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(dict(state=p['state'],sha256=sha(a.output/'FROZEN_PROTOCOL.json'))))

def probs(params,line):
 law=Law(**{k:v for k,v in params.items()if k!='mean'},mean=params.get('mean'))
 L=scoring.exact_decimal(line);k=int(L.to_integral_value(rounding='ROUND_FLOOR'));f=law.cdf(k);integer=L==k;under=law.cdf(k-1)if integer else f;push=f-under if integer else 0.;over=1-f
 if min(over,under,push)<-1e-12 or not math.isclose(over+under+push,1,abs_tol=1e-12):raise ValueError('invalid threshold law complement')
 return dict(over=over,under=under,push=push)

def run(a):
 p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes());start,cpu=time.monotonic(),time.process_time()
 if sha(__file__)!=p['code_sha256']or sha(core.__file__)!=p['core_sha256']or sha(scoring.__file__)!=p['scoring_sha256']:raise ValueError('sealed scorer changed')
 def guard():
  if time.monotonic()-start>300 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('bounded saved-method scoring limit')
 mask=json.loads(gzip.decompress((a.admission_private/'ADMISSIBILITY_MASK.json.gz').read_bytes()))['rows'];wanted=collections.defaultdict(dict)
 for r in mask:
  if r['p1_state']=='ELIGIBLE_NEW_RETROSPECTIVE_SAVED_VECTOR':wanted[r['source_member']][r['source_row_index_in_member']]=r
 values={};laws={};read=0
 for binding in p['raw_sources']['members']:
  name=binding['member']
  if name not in wanted:continue
  file=a.private_root/name
  if sha(file)!=binding['sha256']:raise ValueError('raw source changed')
  it=packet_rows(file)if binding['kind']=='packet'else csv.DictReader(gzip.open(file,'rt'))
  for i,r in enumerate(it):
   read+=1
   if read%10000==0:guard()
   if i not in wanted[name]:continue
   m=wanted[name][i];idx=m['source_row_index'];recipe=(m['target'],m['procedure_id'],m['history_regime'],m['product_id']);values[recipe,idx]=dict(point=float(r['prediction']),fallback=m['fallback'],source_actual=r.get('actual'),source_game=r['game_id'],source_player=r['player_id'],source_population=r['population'])
   if m['p2_state']=='ELIGIBLE_COMPLETE_SAVED_PARAMETRIC_LAW':
    d=r.get('law_reference');d=json.loads(d)if isinstance(d,str)else d;params=d.get('fallback_prior',d.get('parametric'));lk=(m['target'],m['procedure_id'],m['history_regime'],'saved_parametric_law');prev=laws.get((lk,idx))
    if prev and prev['params']!=params:raise ValueError('mean/median law views conflict')
    laws[lk,idx]=dict(params=params,fallback=m['fallback'],source_actual=r.get('actual'),source_game=r['game_id'],source_player=r['player_id'],source_population=r['population'])
 guard();meta=json.loads(gzip.decompress(a.metadata.read_bytes()))['rows'];metaby={r['source_row_index']:r for r in meta};recipes=collections.defaultdict(dict)
 for r in mask:recipes[(r['target'],r['procedure_id'],r['history_regime'],r['product_id'])][r['source_row_index']]=values.get(((r['target'],r['procedure_id'],r['history_regime'],r['product_id']),r['source_row_index']))
 for (k,idx),v in laws.items():recipes[k][idx]=v
 choices=json.loads((a.root/'reports/championship-20261030f/category-selector-v2/DECISIONS.json').read_bytes());composite=[]
 for r in choices:
  if r['evaluation_week']!=7 or r['target']not in core.TARGETS:continue
  chosen=(r['target'],proc_id(r['chosen_procedure_id']),'H-MULTI',product_id(r['chosen_product_id']));k=(r['target'],'v2-chronological-category-selector:'+r['policy_id'],'H-MULTI','selected_point');recipes[k]=dict(recipes.get(chosen,{}));composite.append(dict(recipe=k,chosen_recipe=chosen,source_available_current_weeks=r['current_score_weeks_available']))
 # Freeze directions and K without official outcomes or participation.
 plans={};Kplans=[];baseline_links=[];controlplans={}
 for recipe,available in sorted(recipes.items()):
  target,proc,history,product=recipe;rule='P2'if product=='saved_parametric_law'else'P1';tag=hashlib.sha256(canonical(recipe)).hexdigest()[:18];plan=[]
  for m in meta:
   if m['category']!=target:continue
   v=available.get(m['source_row_index']);point=v.get('point')if v else None;pp=probs(v['params'],m['line'])if v and rule=='P2'else None
   side=None if v is None else('over'if pp['over']>pp['under']else'under'if pp['under']>pp['over']else None)if pp else('over'if scoring.exact_decimal(point)>scoring.exact_decimal(m['line'])else'under'if scoring.exact_decimal(point)<scoring.exact_decimal(m['line'])else None)if point is not None else None
   rank=max(pp['over'],pp['under'])if pp else float(abs(scoring.exact_decimal(point)-scoring.exact_decimal(m['line'])))if point is not None else None
   plan.append(dict(source_row_index=m['source_row_index'],selected_side=side,rank=rank,point=point,probabilities=pp,admitted=v is not None,fallback=v.get('fallback')if v else None))
  plans[tag]=dict(recipe=recipe,rule=rule,rows=plan)
  ids=sorted(r['source_row_index']for r in plan if r['admitted']);maskid=hashlib.sha256(canonical([target,ids])).hexdigest()[:18]
  for control in CONTROLS:baseline_links.append(dict(method_id=tag,control=control,control_id='CONTROL-'+maskid+'-'+control,eligible_source_indices_sha256=hashlib.sha256(canonical(ids)).hexdigest()))
  for scope in('Combined','over','under'):
   rankpool=[r for r in plan if r['selected_side']and(scope=='Combined'or r['selected_side']==scope)];ordered=sorted(rankpool,key=lambda r:(-r['rank'],r['source_row_index']))
   for K in(6,10,20):Kplans.append(dict(method_id=tag,K=K,rank_scope=scope,eligible_pool_n=len(rankpool),source_indices=[r['source_row_index']for r in ordered[:K]]))
  for control in CONTROLS:controlplans.setdefault('CONTROL-'+maskid+'-'+control,dict(target=target,admitted_ids=ids,control=control))
 frozen=gzip.compress(canonical(dict(plans=plans,Kplans=Kplans,controls=controlplans,baseline_links=baseline_links,composite_choices=composite)),mtime=0)
 with(a.private_output/'FROZEN_SELECTIONS_AND_K.json.gz').open('xb')as f:f.write(frozen)
 write(a.output/'SELECTION_FREEZE_RECEIPT.json',dict(at=now(),before_joined_actual_decode=True,sha256=sha(a.private_output/'FROZEN_SELECTIONS_AND_K.json.gz'),methods=len(plans),topK_lists=len(Kplans),matched_control_masks=len(controlplans),composite_choices=composite))
 if sha(a.joined)!=p['joined_sha256']:raise ValueError('qualified label source changed')
 joined=json.loads(gzip.decompress(a.joined.read_bytes()))['rows'];jb={r['source_row_index']:r for r in joined};graded={};probrows=[];numeric=[];checks=[];all_scores=[]
 def graded_row(idx,side,point=None,pp=None,admitted=True,fallback=None):
  r=jb[idx];state='ABSTAIN'if side is None else'UNKNOWN_PARTICIPATION'if r['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL'else'MISSING_ACTUAL'if r['actual']is None else scoring.threshold_crossing(r['actual'],r['line'],side,target=r['target'])
  return dict(r,selected_side=side,statistical_state=state,settlement_state='UNRESOLVED_CONTRACT',ranking_point=point,probabilities=pp,admitted=admitted,fallback=fallback,net_return=None)
 for tag,plan in plans.items():
  recipe=plan['recipe'];target,proc,history,product=recipe;rr=[]
  for z in plan['rows']:
   idx=z['source_row_index'];r=jb[idx];v=recipes[recipe].get(idx)
   if v:
    sy=v['source_actual'];sy=None if sy in('',None)else float(sy)
    if(v['source_game'],v['source_player'],v['source_population'])!=(r['game_id'],r['player_id'],r['population']):raise ValueError('canonical identity/population mismatch')
    if r['actual']is not None and sy!=r['actual']:raise ValueError('modern and independent source labels disagree')
   rr.append(graded_row(idx,z['selected_side'],z['point'],z['probabilities'],z['admitted'],z['fallback']))
  graded[tag]=rr
  supported=[r for r in rr if r['admitted']and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL']
  if plan['rule']=='P2':
   losses=[];logs=[];zero=0
   for r in supported:
    y='over'if scoring.exact_decimal(r['actual'])>scoring.exact_decimal(r['line'])else'under'if scoring.exact_decimal(r['actual'])<scoring.exact_decimal(r['line'])else'push';pp=r['probabilities'];b=.5*sum((pp[s]-int(s==y))**2 for s in('over','under','push'));mass=pp[y];ll=-math.log(mass)if mass>0 else math.inf;losses.append(b);logs.append(ll);zero+=mass<=0;probrows.append(dict(method_id=tag,source_row_index=r['source_row_index'],probabilities=pp,actual_class=y,half3class_brier=b,categorical_log_loss='Infinity'if ll==math.inf else ll))
   numeric.append(dict(record_id='METHOD-PROB-'+tag,record_kind='prop_threshold_probability_evaluation',procedure_id=proc+':known-target-time-v1',history_regime=history,product_id='actual_line_categorical_law',target=target,population='original_full_provider_labelled_offer_pool',season=2026,week=7,evaluation_seasons=[2026],evaluation_weeks=[7],evaluation_panel_id=VERSION,n=len(supported),forecast_rows=len(rr),admitted_forecast_rows=sum(r['admitted']for r in rr),mae=None,mse=None,brier=math.fsum(losses)/len(losses)if losses else None,log_loss='Infinity'if zero else math.fsum(logs)/len(logs)if logs else None,infinite_log_losses=zero,probability_conditioning=p['conditioning'],proper_score='half3classBrierOverUnderPush;categoricaleventlogloss',null_reason=None if losses else'NO_QUALIFIED_LAW_AND_OUTCOME_ROWS',evidence='NEW_EXPERIMENT_SAVED_ROW_RECONSTRUCTION',selection_independent=True))
  else:
   met=scoring.point_metrics([r['ranking_point']for r in supported],[r['actual']for r in supported],target);numeric.append(dict(record_id='METHOD-NUM-'+tag,record_kind='forecast_evaluation_view',procedure_id=proc+':known-target-time-v1',history_regime=history,product_id=product,target=target,population='original_full_provider_labelled_offer_pool',season=2026,week=7,evaluation_seasons=[2026],evaluation_weeks=[7],evaluation_panel_id=VERSION,forecast_rows=len(rr),admitted_forecast_rows=sum(r['admitted']for r in rr),fallback_rows=sum(r['admitted']and r['fallback']not in(None,'none')for r in rr),evidence='NEW_EXPERIMENT_SAVED_ROW_RECONSTRUCTION',**met))
  guard()
 for tag,cp in controlplans.items():
  admitted=set(cp['admitted_ids']);rr=[];control=cp['control']
  for r in joined:
   if r['target']!=cp['target']:continue
   idx=r['source_row_index'];point=r['raw_prediction']if control==core.RAW else r['prediction'];side=None if idx not in admitted else r['original_side']if control=='original'else'over'if control=='alwaysOver'else'under'if control=='alwaysUnder'else'over'if point is not None and scoring.exact_decimal(point)>scoring.exact_decimal(r['line'])else'under'if point is not None and scoring.exact_decimal(point)<scoring.exact_decimal(r['line'])else None
   rr.append(graded_row(idx,side,point,admitted=idx in admitted))
  graded[tag]=rr
 # Existing cohorts and side accounting; each control mask emitted once.
 cohorts=core.cohort_names(joined)
 for tag,rr in graded.items():
  meta_plan=plans.get(tag);iscontrol=meta_plan is None;recipe=meta_plan['recipe']if meta_plan else(controlplans[tag]['target'],'MATCHED_RETAINED_CONTROL:'+controlplans[tag]['control'],'ARCHIVED','saved_precision_control');target,proc,history,product=recipe;rule=meta_plan['rule']if meta_plan else'CONTROL'
  def emit(pool,chosen,cohort,K=None,scope=None,rankeligible=None):
   views=[]
   for side in('over','under','Combined'):
    z=[r for r in chosen if side=='Combined'or r['selected_side']==side];v=core.score_row(z,pool,strategy=tag,target=target,cohort=cohort,side=side,K=K,rank_scope=scope,rank_eligible=rankeligible);v.update(record_id='ADMIT-'+hashlib.sha256(canonical([tag,cohort,side,K,scope])).hexdigest()[:24],procedure_id=proc+(':known-target-time-v1'if not iscontrol else''),history_regime=history,product_id=product,decision_rule=rule,method_id=tag,evaluation_panel_id=VERSION,time_panel_id='2026_W7_ADMITTED_METHOD_RECONSTRUCTION_462_13_GAMES',horizon_id='ASOF_2026_10_23T174953_KNOWN_TARGET_KICKOFF',selection_evidence='RETROSPECTIVE_RULE_REPLAY',source_vintage='Qualifiedretainedthreshold/context plus current-vintage7d footballreconstruction; neveroriginalmethodissuance',probability_conditioning=p['conditioning']if rule=='P2'else None);v['selection_metrics'].update(full_offer_universe=len(pool),admitted_forecast_opportunities=sum(r['admitted']for r in pool),unavailable_forecast_opportunities=sum(not r['admitted']for r in pool),fallback_issued=sum(r['admitted']and r['fallback']not in(None,'none')for r in pool));all_scores.append(v);views.append(v)
   core.check_triplet(views);checks.append([tag,cohort,K,scope])
  for cohort in cohorts:
   pool=[r for r in rr if core.in_cohort(r,cohort)];emit(pool,[r for r in pool if r['selected_side']],cohort)
  if not iscontrol:
   lookup={r['source_row_index']:r for r in rr}
   for kp in Kplans:
    if kp['method_id']==tag:emit(rr,[lookup[i]for i in kp['source_indices']],'FIXED_PARTIAL_WEEK_TOP_PICK_SUBSET',kp['K'],kp['rank_scope'],kp['eligible_pool_n'])
  guard()
 paired=[]
 for link in baseline_links:
  rr=graded[link['method_id']];base={r['source_row_index']:r for r in graded[link['control_id']]};paired.append(dict(link,paired_selected_decisive=core.pilot.bootstrap(rr,base),scope='Same admitted input rows; bothselected/nonpush qualified outcomes for pairedhit diagnostic; completepool coverage retained separately'))
 common=[]
 for target in core.TARGETS:
  tags=[tag for tag,pl in plans.items()if pl['recipe'][0]==target and pl['rule']=='P1'];sets=[{r['source_row_index']for r in graded[tag]if r['admitted']}for tag in tags];ids=set.intersection(*sets)if sets else set();common.append(dict(target=target,methods=len(tags),common_admitted_rows=len(ids),full_offer_rows=sum(r['target']==target for r in joined),state='NO_ALL_METHOD_COMMON_INTERSECTION'if not ids else'COMMON_MASK_AVAILABLE',mask_sha256=hashlib.sha256(canonical(sorted(ids))).hexdigest()))
 blob=gzip.compress(canonical(dict(graded=graded,probability_rows=probrows)),mtime=0)
 with(a.private_output/'GRADED_METHOD_ROWS.json.gz').open('xb')as f:f.write(blob)
 if sum(x.stat().st_size for x in a.private_output.iterdir()if x.is_file())>16777216:raise RuntimeError('private derivative cap')
 write(a.output/'SCORES.json',all_scores+numeric);write(a.output/'PAIRED_CONTROL_COMPARISONS.json',paired);write(a.output/'COMMON_INTERSECTION.json',common);write(a.output/'SIDE_RECONCILIATION.json',dict(triplets=len(checks),checks=checks));csvwrite(a.output/'METHOD_SELECTION_ALL_SIDES.csv',[r for r in all_scores if r['cohort_id']=='ALL']);csvwrite(a.output/'PROBABILITY_AND_POINT_PRODUCTS.csv',numeric)
 receipt=dict(state='COMPLETE_BOUNDED_ADMITTED_METHOD_THRESHOLD_REPLAY',at=now(),protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),score_sha256=sha(a.output/'SCORES.json'),source_offers=len(joined),methods_output_recipes=len(plans),matched_control_masks=len(controlplans),score_views=len(all_scores)+len(numeric),selection_views=len(all_scores),probability_views=sum(r['record_kind']=='prop_threshold_probability_evaluation'for r in numeric),point_views=sum(r['record_kind']=='forecast_evaluation_view'for r in numeric),derived_probability_rows=len(probrows),private_derivative_bytes=sum(x.stat().st_size for x in a.private_output.iterdir()if x.is_file()),new_fits=0,new_model_inference=0,new_issued_forecasts=0,new_NFL_observations=0,Week8_outcomes_read=0,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024));write(a.output/'RUN_RECEIPT.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);p.add_argument('--private-output',type=Path,required=True);p.add_argument('--admission',type=Path,required=True);p.add_argument('--admission-private',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True);p.add_argument('--joined',type=Path,required=True);a=p.parse_args();prepare(a)if a.action=='prepare'else run(a)
