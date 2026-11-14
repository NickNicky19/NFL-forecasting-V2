"""NEW D1/D2 opponent-information ablation with unchanged ordered Leaf-CDF.

No capture is official; original source/control/model/forecast bytes stay intact.
Historical and future execution require independent protocol review and sole-worker
coordination. All target labels are previously exposed reconstruction evidence.
"""
from __future__ import annotations
import collections,csv,gzip,hashlib,json,os,pickle,platform,resource,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from . import hgb_control as src,distribution_wave_v2 as base,chart_wave as chart,availability_wave as avail
from . import ordered_information_ablation as old_recipe,qualified_defense as defense,qualified_defense_inputs as inputs,shared_subgroups as subgroup,chart_sources

VERSION='v2-qualified-position-defense-information-wave-v1'
FAMILY='ordered_leaf_cdf';CHART=chart.TARGET;TARGETS=old_recipe.TARGETS;POLICIES=base.POLICIES;GROUPS=inputs.GROUPS
canonical=src.canonical;sha=src.sha;now=src.now;write=src.immutable_json

def proc(group,policy):return VERSION+':'+group+(':strict-current-inputs'if POLICIES[policy][2]==2026 else':common-feature-memory')
def ident(r):return tuple(r[k]for k in('game_id','player_id','target','population'))
def latest(own,audit,group):
 times=[own,audit.get('latest_local_available')]
 if group=='D2':times.append(audit.get('latest_league_available'))
 return max((m for m in times if m is not None),default=None)
def load(path):return json.loads(Path(path).read_bytes())
def modules():return(src,src.empirical,base,chart,old_recipe,avail,defense,inputs,subgroup,chart_sources)

def prepare(*,source_root,control_public,control_private,chart_public,chart_private,future_queries,frozen_board,public_root,private_root,private_model_roots):
 source_root,control_public,control_private,chart_public,chart_private,future_queries,frozen_board,public_root,private_root=map(Path,(source_root,control_public,control_private,chart_public,chart_private,future_queries,frozen_board,public_root,private_root))
 if public_root.exists()or private_root.exists():raise ValueError('fresh immutable outputs required')
 if private_root.resolve().is_relative_to(Path(__file__).resolve().parents[1]):raise ValueError('private output outside publicGit required')
 old=load(control_public/'FROZEN_PROTOCOL.json');cp=load(chart_public/'FROZEN_PROTOCOL.json')
 if old['source_ids']!=cp['source_ids']:raise ValueError('source bytes differ')
 for s in old['source_ids']:
  if sha(source_root/s['name'])!=s['sha256']:raise ValueError('source hash mismatch')
 # Query/context freezing uses identities and clocks only, never forecast values.
 historical=load(control_private/'frozen-queries.json')['historical']+[q for q in load(chart_private/'frozen-queries.json')['historical']if int(q['season'])==2026 and int(q['week'])<=7]
 if len(historical)!=17968 or any(int(q.get('season',2026))!=2026 or int(q['week'])not in range(1,8)for q in historical):raise ValueError('same historical fixed panel required')
 queries=load(future_queries);asof=now();games=src.schedules(source_root/'games.csv')
 if len(queries)!=2229 or len({q['game_id']for q in queries})!=13 or any(q.get('actual')is not None or q['week']!=8 for q in queries):raise ValueError('same2229pending13gamefuturequeries required')
 if any(not avail.open_query(q,src.utc(asof).timestamp())for q in queries):raise ValueError('future T90 already closed')
 future=inputs.attach_future_context(queries,games,load(frozen_board))
 public_root.mkdir(parents=True);private_root.mkdir(parents=True);write(private_root/'frozen-queries.json',dict(historical=historical,week8=future))
 controls=[]
 for pub,priv,name in[(control_public,control_private,'all-predictions.csv.gz'),(chart_public,chart_private,'all-chart-predictions.csv.gz')]:
  receipt=load(pub/'POSTRUN_REPLAY_RECEIPT.json')
  if sha(priv/name)!=receipt['flat_prediction_sha256']:raise ValueError('control flat source binding failed')
  controls.append(dict(artifact_id=name,sha256=sha(priv/name),receipt_artifact=(pub/'POSTRUN_REPLAY_RECEIPT.json').as_posix(),receipt_sha256=sha(pub/'POSTRUN_REPLAY_RECEIPT.json')))
 future_bindings=[];private_bindings={}
 for target in TARGETS:
  for policy,(arm,fit_floor,feature_floor)in POLICIES.items():
   path=chart_public/f'W08-{policy}-ordered_leaf_cdf-FIT.json'if target==CHART else control_public/f'W08-{target}-{policy}-ordered_leaf_cdf-FIT.json';receipt=load(path);model=avail.resolve_model(receipt,private_model_roots);key=target+':'+policy
   future_bindings.append(dict(key=key,target=target,policy_id=policy,history_regime=arm,fit_floor=fit_floor,feature_floor=feature_floor,fit_cutoff_utc=receipt['fit_cutoff_utc'],training_n=receipt['training_n'],training_membership_sha256=receipt['training_membership_sha256'],receipt_artifact=path.as_posix(),receipt_sha256=sha(path),model_artifact_id=None if model is None else'MODEL-'+sha(model),model_sha256=None if model is None else sha(model)))
   private_bindings[key]=dict(receipt_path=str(path),model_path=None if model is None else str(model))
 write(public_root/'RETAINED_FUTURE_CONTROL_BINDINGS.json',future_bindings);write(private_root/'CONTROL_BINDINGS_PRIVATE.json',private_bindings)
 cr=load(chart_public/'RUN_RECEIPT.json')
 if sha(chart_private/'qualified-chart-labels.json.gz')!=cr['chart_label_packet']['sha256']:raise ValueError('chart label binding failed')
 protocol=dict(version=VERSION,state='FROZEN_BEFORE_NEW_DEFENSE_FEATURES_OR_FITS',registered_at_utc=now(),code_sha256=sha(__file__),helpers={Path(m.__file__).name:sha(m.__file__)for m in modules()},law_code_sha256=sha(Path(__file__).with_name('distribution_laws.py')),precision_code_sha256=sha(Path(__file__).with_name('precision_grid.py')),scoring_code_sha256=sha(Path(__file__).with_name('scoring.py')),source_ids=old['source_ids'],source_role_contract=old['source_role_contract'],source_vintage='current_vintage_reconstruction',frozen_queries_sha256=sha(private_root/'frozen-queries.json'),source_future_query_sha256=sha(future_queries),frozen_board_sha256=sha(frozen_board),future_control_bindings_sha256=sha(public_root/'RETAINED_FUTURE_CONTROL_BINDINGS.json'),chart_label_packet_sha256=cr['chart_label_packet']['sha256'],control_prediction_sources=controls,historical_query_cells=len(historical),future_query_cells=len(future),future_games=13,fixed_future_query_asof_utc=asof,targets=list(TARGETS),policies={k:dict(history_regime=a,fit_floor=b,feature_floor=c)for k,(a,b,c)in POLICIES.items()},groups={k:list(v)for k,v in GROUPS.items()},own_feature_columns=list(src.FEATURES),mechanism='D1adds4previous-opponent-positionqualified-populationtarget-totalmean4/coverage columns; D2retainsD1andadds5compatible-exposure-rate/κ20league-shrinkage/deviation/coverage/age columns. Same20rawownfeatures, learner,trainingmembers, priors andfallback. Differentdimensionalityaltersfeaturecompetition; no claimofidenticalrandomsplitthresholds.',prior_art='Notfirstdefensestudy: pinnedupstreambasefeatures.py rawall-positionteamallowedmean3 and8opponent-adjustedresiduals, models.pyRidgefeature-removals,NGS/scheme additions; productionR0same-positionratio/shrink/clamp exist. Newregisteredversiontestsposition-qualified4games/coverage andmatched-exposureratesonthecurrentLeafcontrol. Noidentity/equivalencetoalllegacyrecipesclaimed.',defense_population='Allqualifiedsourceidentity/positionrowswithinteamgame retained, includingphysicalappearanceunknown/missing-targetslots. A target-totalgamecompleteonlyifEVERYqualifiedrowtargetexplicit; rate numerator/denominatoruseidenticalcomplete compatible rows. QualifiedpopulationobservationsareNOTcompleteofficialteamallowedtotals, causaldefensetalent orfullroster.',denominators={t:'pass_attempts'if t in('pass_yd','pass_td','pass_cmp','pass_int')else'carries'if t=='rush_yd'else'targets'if t in('rec','rec_yd')else'carries_plus_targets'if t=='rush_rec_yd'else'qualified_appearance'for t in TARGETS},shrinkage_kappa=20.,history='Core3fitwindows with common2022own/opponent/leaguefeaturememory; STRICTonly2026labels/ownfeatures/defensefeatures/leaguepriors/transforms. No oldmodel fits orpriorshiddeninsideSTRICT; fixedarchitecturehistoricallychosen/exposed.',chronology='Sameweeklyfitcutoffs/pergamehistoricalfeaturecutoffs asoldcontrol. Sourceavailability kickoff+7days strictlyearlier, no historicalpublicationclaim. Missinglast4opponent-positiongamesconsume slots. Leagueprior strictlyearlier and featurefloorrestricted.',unchanged='32trees/depth8/minleaf30/seed1701; squared-errorleafpartition;95%leafPMF+5%samearmrole/globalprior; samecoldstartn8route, min60, nofitallzero count/singleclassflags; no richerrolefallback.',forest=base.FOREST,chart='Exactqualifiedpartial16componentlabelpolicy,35unknown2026labels retained, signedscore×50law andnative/50summary; exactmedian0.02gridprecision, meansunrounded. Chart/anytime denominatorqualifiedappearancesNOTteamTDcounts.',future='Newpartial13gamepairedresearchshadows; all2229originalqueries includingblockedidentitypreserved. Futurefeature/querycontextcutoffisnewactualasof. D1/D2fitmembers/labelwindows/rolepriors EXACToriginal00:27Week8control;48originalorderedmodelsrestoreandrefresh0refits. No freshA/B/Cavailabilitypolicy and no Week8sourceoutcomes.',historical_grid=[dict(week=w,target=t,policy_id=policy,information_group=group,state='REGISTERED')for w in range(1,8)for t in TARGETS for policy in POLICIES for group in GROUPS],future_grid=[dict(week=8,target=t,policy_id=policy,information_group=group,state='REGISTERED')for t in TARGETS for policy in POLICIES for group in GROUPS],budget=dict(max_fit_calls=768,historical_fit_opportunities=672,future_fit_opportunities=96,wall_seconds=1200,cpu_seconds=1800,max_peak_memory_bytes=2147483648,max_private_bytes=1073741824,max_source_rows=200000,max_forecast_rows=600000,max_threads=2,hyperparameter_searches=0),new_family_count=0,official_capture=False,website_published=False,week8_outcomes_read=0,previous_exposure='All2026W1-W7outcomes/methodresultsalreadyexposed; newmechanismhypothesis, notfreshconfirmation')
 write(public_root/'FROZEN_PROTOCOL.json',protocol);return protocol

def verify(public_root,private_root,source_root,verifier_receipt):
 p=load(public_root/'FROZEN_PROTOCOL.json')
 if p['code_sha256']!=sha(__file__)or p['frozen_queries_sha256']!=sha(private_root/'frozen-queries.json')or p['future_control_bindings_sha256']!=sha(public_root/'RETAINED_FUTURE_CONTROL_BINDINGS.json'):raise ValueError('frozen code/query/control binding changed')
 for m in modules():
  if p['helpers'][Path(m.__file__).name]!=sha(m.__file__):raise ValueError('frozen helper changed')
 for file,key in [('distribution_laws.py','law_code_sha256'),('precision_grid.py','precision_code_sha256'),('scoring.py','scoring_code_sha256')]:
  if sha(Path(__file__).with_name(file))!=p[key]:raise ValueError('law/precision/scoring helper changed')
 for s in p['source_ids']:
  if sha(source_root/s['name'])!=s['sha256']:raise ValueError('source changed')
 r=load(verifier_receipt)
 if r.get('protocol_sha256')!=sha(public_root/'FROZEN_PROTOCOL.json')or r.get('state')!='PASS_PREFIT_PROTOCOL_REVIEW':raise ValueError('independent prefit protocol review required')
 checks=load(public_root/'SOFTWARE_CHECKS.json')
 if checks.get('status')!='PASS'or checks.get('code_sha256')!=sha(__file__):raise ValueError('exactcode software checks required')
 return p

def run_historical(*,source_root,control_public,control_private,chart_public,chart_private,public_root,private_root,verifier_receipt,sole_worker_confirmed=False):
 if not sole_worker_confirmed:raise ValueError('rootsolefitworkercoordinationrequired')
 source_root,control_public,control_private,chart_public,chart_private,public_root,private_root=map(Path,(source_root,control_public,control_private,chart_public,chart_private,public_root,private_root));p=verify(public_root,private_root,source_root,verifier_receipt);start,cpu=time.monotonic(),time.process_time()
 write(public_root/'HISTORICAL_EXECUTION_REGISTRATION.json',dict(version=VERSION,actual_started_at_utc=now(),protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),independent_prefit_review_sha256=sha(verifier_receipt),sole_worker_confirmed=True,actual_fit_calls_before_start=0,environment=dict(python=platform.python_version(),numpy=np.__version__)))
 rows,games,counts,labels,chartcoverage=chart.load_chart_source(source_root,p)
 if sha(chart_private/'qualified-chart-labels.json.gz')!=p['chart_label_packet_sha256']:raise ValueError('frozen qualified chart packet changed')
 cached={(r['game_id'],r['player_id']):r['label']['points_times_50']for r in json.loads(gzip.decompress((chart_private/'qualified-chart-labels.json.gz').read_bytes()))['rows']}
 if set(cached)!={(r['game_id'],r['player_id'])for r in rows}or any(cached[r['game_id'],r['player_id']]!=r['values'][CHART]for r in rows):raise ValueError('rebuilt chart labels differ from retained qualified packet')
 inputs.attach_context(rows,games,source_root);lookup={(r['game_id'],r['player_id']):r for r in rows};dh=inputs.build_history(rows,TARGETS);hist={floor:base.feature_history(rows,floor)for floor in(2022,2026)};controls={}
 for spec,priv in zip(p['control_prediction_sources'],(control_private,chart_private)):
  path=priv/spec['artifact_id']
  if sha(path)!=spec['sha256']:raise ValueError('control predictions changed')
  with gzip.open(path,'rt',newline='')as f:
   for r in csv.DictReader(f):
    if r['season']!='2026'or int(r['week'])>7 or r.get('family')!=FAMILY:continue
    record={k:r[k]for k in('target','policy_id','game_id','player_id','population','position','history_regime','product_id','procedure_id','fallback')}
    for k in('prediction','actual'):record[k]=None if r[k]==''else float(r[k])
    key=old_recipe.controlkey(record)
    if key in controls:raise ValueError('duplicate original control')
    controls[key]=record
 datasets={};feature_coverage=[]
 for target in TARGETS:
  roles=set(src.POSITIONS)if target==CHART else src.allowed_roles(p,target);eligible=[r for r in rows if r['position']in roles and r['values'][target]is not None]
  for floor in(2022,2026):
   rs=[r for r in eligible if r['season']>=floor];matrix={g:[]for g in GROUPS};maxima={g:[]for g in GROUPS};coverage=collections.Counter()
   for r in rs:
    own,m=hist[floor].get(r['player_id'],r['position'],target,r['kickoff']);q=dict(r,target=target,cutoff=r['kickoff'],blocked_reason=None)
    full,a=inputs.augment(own,dh,q,floor,'D2');coverage['rows']+=1;coverage['raw_total_supported']+=int(a['values']['qualified_allowed_mean4']is not None);coverage['rate_supported']+=int(a['values']['shrunk_allowed_per_opportunity4']is not None)
    for g in GROUPS:matrix[g].append(full[:24]if g=='D1'else full);maxima[g].append(latest(m,a,g))
   for g in GROUPS:datasets[target,floor,g]=(rs,np.asarray(matrix[g]),maxima[g])
   feature_coverage.append(dict(target=target,feature_floor=floor,**coverage))
 write(public_root/'TRAINING_FEATURE_COVERAGE.json',feature_coverage)
 historical=collections.defaultdict(list)
 for q in load(private_root/'frozen-queries.json')['historical']:
  r=lookup[q['game_id'],q['player_id']];v=r['values'][q['target']];historical[int(q['week'])].append(dict(q,season=2026,week=int(q['week']),kickoff=r['kickoff'],cutoff=r['kickoff'],defense=r['defense'],team=r['team'],actual_grid=v if q['target']==CHART else None,actual=v/50 if q['target']==CHART and v is not None else v,blocked_reason=None))
 for name in('models','query-features','prediction-chunks'):(private_root/name).mkdir(exist_ok=True)
 private_bytes=sum(f.stat().st_size for f in private_root.rglob('*')if f.is_file());fits=retained=outputs=0;allrows=[];completed={};failures=[];meters=collections.defaultdict(old_recipe.Metrics);terminal='COMPLETE'
 def guard():
  if time.monotonic()-start>p['budget']['wall_seconds']or time.process_time()-cpu>p['budget']['cpu_seconds']:raise RuntimeError('TIME_BUDGET')
  if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>p['budget']['max_peak_memory_bytes']:raise RuntimeError('RSS_BUDGET')
 def save(path,value,raw=False):
  nonlocal private_bytes
  body=value if raw else canonical(value);blob=gzip.compress(body,mtime=0)
  if private_bytes+len(blob)>p['budget']['max_private_bytes']:raise RuntimeError('PRIVATE_BYTES_BEFORE_WRITE')
  with path.open('xb')as f:f.write(blob);f.flush();os.fsync(f.fileno())
  private_bytes+=len(blob)
  if path.read_bytes()!=blob:raise ValueError('private readback')
  return dict(artifact_id='DEFENSE-'+sha(path),bundle_name=path.relative_to(private_root).as_posix(),sha256=sha(path),bytes=len(blob))
 with threadpool_limits(limits=2):
  try:
   for week in range(1,8):
    origin=min(g['kickoff']for g in games.values()if g['season']==2026 and g['week']==week)
    for target in TARGETS:
     qr=[q for q in historical[week]if q['target']==target]
     for policy,(arm,fit_floor,floor)in POLICIES.items():
      for group in GROUPS:
       guard();slot=f'W{week:02}-{target}-{policy}-{group}';rs,x,mx=datasets[target,floor,group];idx=np.asarray([i for i,r in enumerate(rs)if r['season']>=fit_floor and r['available']<origin],dtype=int);y=np.asarray([rs[i]['values'][target]for i in idx]);positions=[rs[i]['position']for i in idx];globalprior=old_recipe.laws_prior(y,target);poscounts={pos:positions.count(pos)for pos in src.POSITIONS};priors={pos:old_recipe.laws_prior([rs[i]['values'][target]for i in idx if rs[i]['position']==pos],target)if poscounts[pos]else globalprior for pos in src.POSITIONS}
       oldslot=f'W{week:02}-{policy}-{FAMILY}'if target==CHART else f'W{week:02}-{target}-{policy}-{FAMILY}';oldpub=chart_public if target==CHART else control_public;oldfit=load(oldpub/(oldslot+'-FIT.json'));membership=hashlib.sha256(canonical([(rs[i]['game_id'],rs[i]['player_id'])for i in idx])).hexdigest()
       if oldfit['training_membership_sha256']!=membership or oldfit['training_n']!=len(idx)or oldfit['prior_parameters']!={pos:law.parameters()for pos,law in priors.items()}or oldfit['prior_position_sample_counts']!=poscounts or src.utc(oldfit['fit_cutoff_utc']).timestamp()!=origin or oldfit['feature_floor']!=floor:raise ValueError('control training/prior/cutoff mismatch')
       qx=[];qm=[];qa=[]
       for q in qr:
        own,m=hist[floor].get(q['player_id'],q['position'],target,q['cutoff']);f,a=inputs.augment(own,dh,q,floor,group);qx.append(f);qm.append(latest(m,a,group));qa.append(a)
       qx=np.asarray(qx);featurepacket=save(private_root/'query-features'/(slot+'.json.gz'),[dict(query=q,features=src.json_features(f),latest_consumed_feature_available=m,defense_audit=a)for q,f,m,a in zip(qr,qx,qm,qa)])
       model=None;modelpacket=None;state='NO_FIT_INSUFFICIENT_TRAINING';fitstart=fitend=None
       if len(idx)>=60:
        if target in src.empirical.COUNTS and np.all(y==0):state='NO_FIT_ALL_ZERO_COUNT'
        elif target=='anytime_td'and len(np.unique(y))<2:state='NO_FIT_SINGLE_CLASS_BINARY'
        else:
         if fits>=p['budget']['historical_fit_opportunities']:raise RuntimeError('FIT_BUDGET')
         fits+=1;fitstart=now()
         try:model=base.FittedLawModel(FAMILY,target).fit(x[idx],y,positions);fitend=now()
         except Exception as exc:model=None;fitend=now();state='FIT_FAILED_FALLBACK';failures.append(dict(slot=slot,type=type(exc).__name__,reason=str(exc)[:240]))
         if model is not None:guard();modelpacket=save(private_root/'models'/(slot+'.pickle.gz'),pickle.dumps(model,protocol=5),True);retained+=1;state='FITTED_RETAINED'
       audit=dict(slot=slot,target=target,week=week,information_group=group,feature_columns=list(src.FEATURES)+list(GROUPS[group]),policy_id=policy,history_regime=arm,feature_floor=floor,training_n=len(idx),training_membership_sha256=membership,fit_cutoff_utc=datetime.fromtimestamp(origin,timezone.utc).isoformat(),latest_training_label_available=max((rs[i]['available']for i in idx),default=None),latest_training_consumed_feature_available=max((mx[i]for i in idx if mx[i]is not None),default=None),prior_parameters={pos:law.parameters()for pos,law in priors.items()},prior_position_sample_counts=poscounts,control_training_and_priors_match=True,control_fit_artifact=(oldpub/(oldslot+'-FIT.json')).as_posix(),control_fit_sha256=sha(oldpub/(oldslot+'-FIT.json')),state=state,model=modelpacket,query_features=featurepacket,actual_fit_started_at=fitstart,actual_fit_completed_at=fitend);write(public_root/(slot+'-FIT.json'),audit)
       need=len(qr)*len(old_recipe.products(target))
       if outputs+need>p['budget']['max_forecast_rows']:raise RuntimeError('OUTPUT_BUDGET_BEFORE_INFERENCE')
       inferred=model.predict(qx,[q['position']for q in qr],priors)if model is not None else[(None,None)]*len(qr);records=[]
       for q,f,m,(law,detail)in zip(qr,qx,qm,inferred):
        fallback='none'
        if model is None or f[3]<=0:fallback='fixed_no_NFL_startup'if not len(idx)else'cold_start_role_prior'if f[3]<=0 else'no_model_role_prior';law=priors[q['position']];detail=dict(fallback_prior=law.parameters())
        if m is not None and m>=q['cutoff']:raise ValueError('consumed feature chronology violation')
        summary=chart.chart_summary(law,q['actual_grid'])if target==CHART else law.summary(q['actual'])
        for product in old_recipe.products(target):
         record=dict(q,run_id=VERSION,procedure_id=proc(group,policy),procedure_family_id=FAMILY,product_id=product,information_group=group,policy_id=policy,history_regime=arm,information_policy='STRICT-CURRENT'if floor==2026 else'COMMON-2022-MEMORY',feature_floor=floor,prediction=summary['mean'if product=='event_probability'else product],fallback=fallback,fit_slot=slot,fit_state=state,latest_feature_available=m,distribution_summary=summary,law_reference=detail,status='RECONSTRUCTED_RESEARCH_FORECAST',actual_generated_at=now());control=controls[old_recipe.controlkey(record)]
         if control['actual']!=record['actual']or control['position']!=record['position']:raise ValueError('samequery control label/position mismatch')
         record.update(control_prediction=control['prediction'],control_procedure_id=control['procedure_id'],control_fallback=control['fallback']);views=[('ALL','ALL','ALL'),(str(week),'ALL','ALL'),('ALL',q['position'],'ALL')]
         if fallback=='none':views.append(('ALL','ALL','LEARNED_ONLY'))
         if fallback=='none'and control['fallback']=='none':views.append(('ALL','ALL','PAIRED_LEARNED_OVERLAP'))
         for wk,pos,view in views:meters[group,policy,target,q['population'],product,wk,pos,view].add(record)
         records.append(record)
       packet=save(private_root/'prediction-chunks'/(slot+'.json.gz'),dict(schema=VERSION,rows=records));outputs+=len(records);completed[slot]=state;allrows.extend(records);write(public_root/(slot+'-FORECAST.json'),dict(slot=slot,packet=packet,rows=len(records),actual_persistence_completed_at=now(),future_rows=0))
  except Exception as exc:terminal='PARTIAL_STOPPED';failures.append(dict(type=type(exc).__name__,reason=str(exc)[:240]))
 scores=[];dates=[]
 for dims,meter in sorted(meters.items()):
  group,policy,target,pop,product,wk,pos,view=dims;rr=meter.rows;scored=[r for r in rr if r['prediction']is not None and r['actual']is not None];other={ident(r):dict(r,prediction=r['control_prediction'],procedure_id=r['control_procedure_id'],fallback=r['control_fallback'])for r in rr};comparison=subgroup.paired(rr,other,'brier'if target=='anytime_td'else'mae');result=meter.result(target,product)
  scores.append(dict(record_id='DEFENSE-'+hashlib.sha256(canonical(dims)).hexdigest()[:24],procedure_id=proc(group,policy),procedure_family_id=FAMILY,information_group=group,target=target,history_regime=POLICIES[policy][0],policy_id=policy,information_policy='STRICT-CURRENT'if POLICIES[policy][2]==2026 else'COMMON-2022-MEMORY',product_id=product,population=pop,evaluation_panel_id=VERSION,season=2026,week=int(wk)if wk.isdigit()else wk,position=pos,fallback_view=view,period='REG',record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',evidence='NEW_EXPERIMENT',source_vintage=p['source_vintage'],cohort_limit=p['defense_population'],comparison=comparison,scoring_version='native-point-and-law-exact-chart-median-grid-v1',**result));dates.append(dict(source_row_index=len(scores)-1,evaluation_seasons=[2026],evaluation_weeks=sorted({r['week']for r in scored}),actual_scored_weeks=sorted({r['week']for r in scored}),forecast_query_weeks=sorted({r['week']for r in rr}),registered_panel_weeks=list(range(1,8))))
 write(public_root/'SCORES.json',scores);src.empirical.write_csv(public_root/'SCORES.csv',scores);write(public_root/'SCORE_DATE_PROJECTION.json',dict(source_score_sha256=sha(public_root/'SCORES.json'),rows=dates));write(public_root/'HISTORICAL_FAILURES.json',failures);write(public_root/'HISTORICAL_GRID_STATUS.json',[dict(c,slot=f"W{c['week']:02}-{c['target']}-{c['policy_id']}-{c['information_group']}",state=completed.get(f"W{c['week']:02}-{c['target']}-{c['policy_id']}-{c['information_group']}",'NOT_RUN_AFTER_BOUNDED_STOP'))for c in p['historical_grid']]);flat=save(private_root/'ALL_HISTORICAL_PREDICTIONS.json.gz',dict(schema=VERSION,rows=allrows))
 receipt=dict(version=VERSION,state=terminal,actual_completed_at_utc=now(),protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),code_sha256=sha(__file__),historical_fit_opportunities=672,actual_fit_calls=fits,retained_models=retained,completed_cells=len(completed),remaining_historical_cells=672-len(completed),forecast_output_views=outputs,score_views=len(scores),private_prediction_packet=flat,private_output_bytes=private_bytes,source_counts=counts,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2),new_family_count=0,new_future_forecasts=0,week8_outcomes_read=0,future_state='96NEW_CELLS_PLUS48_RETAINED_CONTROLS_REQUIRE_SEPARATE_EXPLICIT_WORKER_EXECUTION_WITH_REMAINING_TOTAL_BUDGET',private_durability='LOCAL_READBACK_PENDING_ROOT_COMPANION_RESTORATION');write(public_root/'HISTORICAL_RUN_RECEIPT.json',receipt);return receipt

def run_future(*,source_root,public_root,private_root,verifier_receipt,sole_worker_confirmed=False):
 """96new information fits +48retained controls, same original fit membership.

Runs only after historical completion; consumes the remaining registered total
wall/CPU/fit budget. This does not grade or query any Week8statistical outcomes.
 """
 if not sole_worker_confirmed:raise ValueError('rootsolefitworkercoordinationrequired')
 source_root,public_root,private_root=map(Path,(source_root,public_root,private_root));p=verify(public_root,private_root,source_root,verifier_receipt);prior=load(public_root/'HISTORICAL_RUN_RECEIPT.json');start,cpu=time.monotonic(),time.process_time()
 if prior['state']!='COMPLETE'or prior['protocol_sha256']!=sha(public_root/'FROZEN_PROTOCOL.json'):raise ValueError('complete sameprotocol historicalwave required')
 write(public_root/'FUTURE_EXECUTION_REGISTRATION.json',dict(version=VERSION,actual_started_at_utc=now(),protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),prior_historical_receipt_sha256=sha(public_root/'HISTORICAL_RUN_RECEIPT.json'),prior_actual_fit_calls=prior['actual_fit_calls'],sole_worker_confirmed=True,week8_outcomes_read=0))
 rows,games,counts,chartlabels,coverage=chart.load_chart_source(source_root,p);inputs.attach_context(rows,games,source_root);dh=inputs.build_history(rows,TARGETS);hist={floor:base.feature_history(rows,floor)for floor in(2022,2026)};queries=load(private_root/'frozen-queries.json')['week8'];bindings=load(public_root/'RETAINED_FUTURE_CONTROL_BINDINGS.json');local=load(private_root/'CONTROL_BINDINGS_PRIVATE.json');asof=src.utc(p['fixed_future_query_asof_utc']).timestamp();outputs=[];audits=[];failures=[];calls=retained=0;private_bytes=sum(f.stat().st_size for f in private_root.rglob('*')if f.is_file());terminal='COMPLETE'
 for name in('future-models','future-features','future-chunks'):(private_root/name).mkdir(exist_ok=True)
 def guard():
  if prior['resource']['wall_seconds']+time.monotonic()-start>p['budget']['wall_seconds']or prior['resource']['cpu_seconds']+time.process_time()-cpu>p['budget']['cpu_seconds']:raise RuntimeError('TOTAL_HISTORICAL_FUTURE_TIME_BUDGET')
  if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>p['budget']['max_peak_memory_bytes']:raise RuntimeError('RSS_BUDGET')
 def save(path,value,raw=False):
  nonlocal private_bytes
  body=value if raw else canonical(value);blob=gzip.compress(body,mtime=0)
  if private_bytes+len(blob)>p['budget']['max_private_bytes']:raise RuntimeError('TOTAL_PRIVATE_BYTES_BEFORE_WRITE')
  with path.open('xb')as f:f.write(blob);f.flush();os.fsync(f.fileno())
  private_bytes+=len(blob)
  if path.read_bytes()!=blob:raise ValueError('future private readback')
  return dict(artifact_id='DEFENSE-FUTURE-'+sha(path),bundle_name=path.relative_to(private_root).as_posix(),sha256=sha(path),bytes=len(blob))
 with threadpool_limits(limits=2):
  try:
   for binding in bindings:
    guard();target=binding['target'];policy=binding['policy_id'];arm=binding['history_regime'];floor=binding['feature_floor'];key=binding['key'];oldpath=Path(local[key]['receipt_path'])
    if sha(oldpath)!=binding['receipt_sha256']:raise ValueError('future control receipt changed')
    old=load(oldpath);origin=src.utc(binding['fit_cutoff_utc']).timestamp();roles=set(src.POSITIONS)if target==CHART else src.allowed_roles(p,target);train=[r for r in rows if r['position']in roles and r['season']>=binding['fit_floor']and r['values'][target]is not None and r['available']<origin];y=np.asarray([r['values'][target]for r in train]);positions=[r['position']for r in train];membership=hashlib.sha256(canonical([(r['game_id'],r['player_id'])for r in train])).hexdigest();globalprior=old_recipe.laws_prior(y,target);poscounts={pos:positions.count(pos)for pos in src.POSITIONS};priors={pos:old_recipe.laws_prior([r['values'][target]for r in train if r['position']==pos],target)if poscounts[pos]else globalprior for pos in src.POSITIONS}
    if membership!=binding['training_membership_sha256']or len(train)!=old['training_n']or {pos:law.parameters()for pos,law in priors.items()}!=old['prior_parameters']or poscounts!=old['prior_position_sample_counts']:raise ValueError('exact original Week8training/priors mismatch')
    tx={g:[]for g in GROUPS};tmax={g:[]for g in GROUPS}
    for r in train:
     own,m=hist[floor].get(r['player_id'],r['position'],target,r['kickoff']);full,a=inputs.augment(own,dh,dict(r,target=target,cutoff=r['kickoff'],blocked_reason=None),floor,'D2')
     for g in GROUPS:tx[g].append(full[:24]if g=='D1'else full);tmax[g].append(latest(m,a,g))
    qr=[dict(q,cutoff=asof,actual=None)for q in queries if q['target']==target];fullown=[];ownmaxima=[];qfeatures={g:[]for g in GROUPS};qmax={g:[]for g in GROUPS};qa=[]
    for q in qr:
     reason=q.get('blocked_reason')or('UNQUALIFIED_POSITION'if q.get('position')not in src.POSITIONS else None)
     if reason:own=np.full(20,np.nan);m=None
     else:own,m=hist[floor].get(q['player_id'],q['position'],target,asof)
     full,a=inputs.augment(own,dh,q,floor,'D2');fullown.append(own);ownmaxima.append(m);qa.append(a)
     if m is not None and m>=asof:raise ValueError('future own feature chronology violation')
     for g in GROUPS:qfeatures[g].append(full[:24]if g=='D1'else full);qmax[g].append(latest(m,a,g))
    ownmatrix=np.asarray(fullown);featurepacket=save(private_root/'future-features'/(key.replace(':','--')+'.json.gz'),[dict(query=q,own_features=src.json_features(own),D1_features=src.json_features(a),D2_features=src.json_features(b),defense_audit=audit)for q,own,a,b,audit in zip(qr,ownmatrix,qfeatures['D1'],qfeatures['D2'],qa)])
    control=None
    if local[key]['model_path']:
     if sha(local[key]['model_path'])!=binding['model_sha256']:raise ValueError('retained model changed')
     control=pickle.loads(gzip.decompress(Path(local[key]['model_path']).read_bytes()))
    models={'retained_ordered_control':control};modelpackets={};states={'retained_ordered_control':old['state']}
    for group in GROUPS:
     guard();state='NO_FIT_INSUFFICIENT_TRAINING';model=None;modelpacket=None;fitstart=fitend=None
     if len(train)>=60 and not(target in src.empirical.COUNTS and np.all(y==0))and not(target=='anytime_td'and len(np.unique(y))<2):
      if calls>=p['budget']['future_fit_opportunities']or prior['actual_fit_calls']+calls>=p['budget']['max_fit_calls']:raise RuntimeError('TOTAL_FIT_BUDGET')
      calls+=1;fitstart=now()
      try:model=base.FittedLawModel(FAMILY,target).fit(np.asarray(tx[group]),y,positions);fitend=now()
      except Exception as exc:model=None;fitend=now();state='FIT_FAILED_FALLBACK';failures.append(dict(key=key,information_group=group,type=type(exc).__name__,reason=str(exc)[:240]))
      if model is not None:guard();modelpacket=save(private_root/'future-models'/(key.replace(':','--')+'-'+group+'.pickle.gz'),pickle.dumps(model,protocol=5),True);retained+=1;state='FITTED_RETAINED'
     models[group]=model;modelpackets[group]=modelpacket;states[group]=state;audit=dict(target=target,information_group=group,policy_id=policy,history_regime=arm,feature_floor=floor,feature_columns=list(src.FEATURES)+list(GROUPS[group]),training_n=len(train),training_membership_sha256=membership,training_label_fit_cutoff_utc=binding['fit_cutoff_utc'],latest_training_label_available=max((r['available']for r in train),default=None),latest_training_consumed_feature_available=max((m for m in tmax[group]if m is not None),default=None),prior_parameters={pos:law.parameters()for pos,law in priors.items()},prior_position_sample_counts=poscounts,control_training_and_priors_match=True,retained_control_model_artifact_id=binding['model_artifact_id'],state=state,model=modelpacket,query_features=featurepacket,actual_fit_started_at=fitstart,actual_fit_completed_at=fitend);write(public_root/('FUTURE-'+key.replace(':','--')+'-'+group+'-FIT.json'),audit);audits.append(audit)
    need=len(qr)*3*len(old_recipe.products(target))
    if prior['forecast_output_views']+len(outputs)+need>p['budget']['max_forecast_rows']:raise RuntimeError('TOTAL_OUTPUT_BUDGET_BEFORE_INFERENCE')
    slotrows=[]
    for group,model in models.items():
     matrix=ownmatrix if group=='retained_ordered_control'else np.asarray(qfeatures[group]);predicted=base.predict_admitted(model,matrix,qr,priors);generated=now()
     for j,(q,own,(law,detail))in enumerate(zip(qr,ownmatrix,predicted)):
      reason=q.get('blocked_reason')or('UNQUALIFIED_POSITION'if q.get('position')not in src.POSITIONS else None);fallback='none';d=None
      if not reason:
       if model is None or own[3]<=0:law=priors[q['position']];detail=dict(fallback_prior=law.parameters());fallback='fixed_no_NFL_startup'if not len(train)else'cold_start_role_prior'if own[3]<=0 else'no_model_role_prior'
       d=chart.chart_summary(law,None)if target==CHART else law.summary(None)
      m=ownmaxima[j]if group=='retained_ordered_control'else qmax[group][j]
      if m is not None and m>=asof:raise ValueError('future consumed feature chronology violation')
      for product in old_recipe.products(target):
       slotrows.append(dict(q,run_id=VERSION,variant=group,information_group=group,family=FAMILY,procedure_id=VERSION+':retained_ordered_control'+(':strict-current-inputs'if floor==2026 else':common-feature-memory')if group=='retained_ordered_control'else proc(group,policy),history_regime=arm,policy_id=policy,information_policy='STRICT-CURRENT'if floor==2026 else'COMMON-2022-MEMORY',product_id=product,prediction=None if reason else d['mean'if product=='event_probability'else product],actual=None,actual_status='PENDING_FUTURE',status='ABSTAIN'if reason else'STAGED_RESEARCH_SHADOW',abstention_reason=reason,fallback=None if reason else fallback,feature_cutoff_utc=p['fixed_future_query_asof_utc'],latest_feature_available=m,training_fit_cutoff_utc=binding['fit_cutoff_utc'],actual_generated_at=generated,issued_at_utc=None if reason else generated,actual_horizon_seconds=None if reason else src.utc(q['kickoff_utc']).timestamp()-src.utc(generated).timestamp(),distribution_summary=d,law_reference=None if reason else detail,fit_state=states[group],model_artifact_id=binding['model_artifact_id']if group=='retained_ordered_control'else None if modelpackets[group]is None else modelpackets[group]['artifact_id']))
    check=datetime.now(timezone.utc).timestamp()
    for r in slotrows:
     if not avail.open_query(r,check):r.update(prediction=None,status='ABSTAIN',abstention_reason='T90_CLOSED_BEFORE_PERSISTENCE',distribution_summary=None,issued_at_utc=None)
    packet=save(private_root/'future-chunks'/(key.replace(':','--')+'.json.gz'),dict(schema=VERSION,rows=slotrows));persisted=now()
    if any(r['prediction']is not None and not avail.open_query(r,src.utc(persisted).timestamp())for r in slotrows):raise RuntimeError('DEADLINE_CROSSED_DURING_PERSISTENCE_PACKET_INVALID')
    write(public_root/('FUTURE-'+key.replace(':','--')+'-FORECAST.json'),dict(key=key,packet=packet,actual_persistence_completed_at=persisted,output_views=len(slotrows),issued=sum(r['prediction']is not None for r in slotrows),abstained=sum(r['prediction']is None for r in slotrows),all_issued_before_T90=True));outputs.extend(slotrows)
  except Exception as exc:terminal='PARTIAL_STOPPED';failures.append(dict(type=type(exc).__name__,reason=str(exc)[:240]))
 packet=save(private_root/'WEEK8_PAIRED_SHADOWS.json.gz',dict(schema=VERSION,rows=outputs));persisted=now();write(public_root/'FUTURE_FAILURES.json',failures)
 receipt=dict(version=VERSION,state=terminal,actual_completed_at_utc=now(),actual_aggregate_persistence_completed_at=persisted,fixed_future_query_asof_utc=p['fixed_future_query_asof_utc'],protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),packet=packet,query_cells=len(queries),query_games=13,actual_fit_calls=calls,retained_new_models=retained,retained_control_models=48,completed_candidate_cells=len(audits),remaining_future_cells=96-len(audits),output_views=len(outputs),issued=sum(r['prediction']is not None for r in outputs),abstained=sum(r['prediction']is None for r in outputs),score_views=0,week8_outcomes_read=0,official_capture=False,website_published=False,private_output_bytes=private_bytes,total_wave_fit_calls=prior['actual_fit_calls']+calls,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2),private_durability='LOCAL_READBACK_PENDING_ROOT_COMPANION_RESTORATION');write(public_root/'WEEK8_CAPTURE_RECEIPT.json',receipt);return receipt
