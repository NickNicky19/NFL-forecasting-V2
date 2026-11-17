"""C02: remove the explicit lag block, retaining recency summaries and roles.

New fits on the same exposed historical rows. No future capture or acquisition.
Control rows, memberships, priors and original artifacts are reused, never refit.
"""
from __future__ import annotations
import collections,csv,gzip,hashlib,json,math,os,pickle,platform,resource,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from . import hgb_control as source
from . import distribution_wave_v2 as base
from . import chart_wave as chart
from .distribution_laws import prior
from .precision_grid import chart_median_precision
from .scoring import point_metrics

VERSION='v2-c02-explicit-lag-block-removal-leaf-cdf-v1'
FAMILY='ordered_leaf_cdf'
CHART='nick-chart-ppr-v1'
TARGETS=(*source.TARGETS,CHART)
POLICIES=base.POLICIES
KEEP=(0,1,2,3,16,17,18,19)
KEEP_NAMES=tuple(source.FEATURES[i]for i in KEEP)
canonical=source.canonical;sha=source.sha;now=source.now;write=source.immutable_json

def project(x):
    x=np.asarray(x,dtype=float)
    if x.shape[-1]!=20:raise ValueError('registered full20rawfeatures required')
    return x[...,KEEP]
def products(target):return('event_probability',)if target=='anytime_td'else('mean','lower_median')
def proc(policy):return VERSION+(':strict-current-inputs'if POLICIES[policy][2]==2026 else':common-feature-memory')
def ident(r):return(r['game_id'],r['player_id'],r['target'],r['population'])
def controlkey(r):return(r['target'],r['policy_id'],r['game_id'],r['player_id'],r['population'],r['product_id'])
def laws_prior(values,target):return chart.chart_prior(values)if target==CHART else prior(values,target)
def loadjson(path):return json.loads(Path(path).read_bytes())


def prepare(*,source_root,control_public,control_private,chart_public,chart_private,public_root,private_root):
    source_root,control_public,control_private,chart_public,chart_private,public_root,private_root=map(Path,(source_root,control_public,control_private,chart_public,chart_private,public_root,private_root))
    if public_root.exists()or private_root.exists():raise ValueError('freshimmutableoutputsrequired')
    if private_root.resolve().is_relative_to(Path(__file__).resolve().parents[1]):raise ValueError('private evidence outside publicGit required')
    old=loadjson(control_public/'FROZEN_PROTOCOL.json');cp=loadjson(chart_public/'FROZEN_PROTOCOL.json');cr=loadjson(chart_public/'RUN_RECEIPT.json')
    for s in old['source_ids']:
        if sha(source_root/s['name'])!=s['sha256']:raise ValueError('sourcehash mismatch')
    if old['source_ids']!=cp['source_ids']:raise ValueError('chart sourcebytes differ')
    public_root.mkdir(parents=True);private_root.mkdir(parents=True)
    queries=loadjson(control_private/'frozen-queries.json')['historical'];chart_queries=[q for q in loadjson(chart_private/'frozen-queries.json')['historical']if int(q['season'])==2026 and int(q['week'])<=7]
    if any(int(q.get('season',2026))!=2026 or int(q['week'])>7 for q in queries):raise ValueError('fixedW1-W7querypanelrequired')
    write(private_root/'frozen-queries.json',queries+chart_queries)
    controls=[]
    for pub,priv,name in[(control_public,control_private,'all-predictions.csv.gz'),(chart_public,chart_private,'all-chart-predictions.csv.gz')]:
        receipt=loadjson(pub/'POSTRUN_REPLAY_RECEIPT.json');expected=receipt.get('flat_prediction_sha256')
        if sha(priv/name)!=expected:raise ValueError('original retained control predictionhash mismatch')
        controls.append(dict(public_artifact=(pub/'POSTRUN_REPLAY_RECEIPT.json').as_posix(),receipt_sha256=sha(pub/'POSTRUN_REPLAY_RECEIPT.json'),artifact_id=name,sha256=expected))
    if sha(chart_private/'qualified-chart-labels.json.gz')!=cr['chart_label_packet']['sha256']:raise ValueError('qualifiedchartpacket hash mismatch')
    p=dict(version=VERSION,state='FROZEN_BEFORE_C02_FITS',registered_at_utc=now(),code_sha256=sha(__file__),helpers={Path(m.__file__).name:sha(m.__file__)for m in(source,source.empirical,base,chart)},law_code_sha256=sha(Path(__file__).with_name('distribution_laws.py')),precision_code_sha256=sha(Path(__file__).with_name('precision_grid.py')),scoring_code_sha256=sha(Path(__file__).with_name('scoring.py')),source_ids=old['source_ids'],source_role_contract=old['source_role_contract'],control_protocol_sha256=sha(control_public/'FROZEN_PROTOCOL.json'),chart_protocol_sha256=sha(chart_public/'FROZEN_PROTOCOL.json'),chart_label_packet_sha256=cr['chart_label_packet']['sha256'],control_prediction_sources=controls,frozen_queries_sha256=sha(private_root/'frozen-queries.json'),historical_query_cells=len(queries)+len(chart_queries),targets=list(TARGETS),policies={k:dict(history_regime=a,fit_floor=b,feature_floor=c)for k,(a,b,c)in POLICIES.items()},mechanism='Remove all4individual lag value/age/missing triplets and their imputationflags. Retain mean3/n3/mean8/n8+positiononehot. This doesNOTremoveallordering: sharedrecencymeans remain.',removed_raw_columns=[source.FEATURES[i]for i in range(4,16)],retained_raw_columns=list(KEEP_NAMES),control_raw_features=20,candidate_raw_features=8,control_design_features=40,candidate_design_features=16,unchanged='sourcebytes;queryIDs;roles;fitwindows;featurememory;weekfit/gamefeaturecutoffs;trainingrows;trainonlyimputer;32trees/depth8/minleaf30/seed1701;95%leaflaw+5%samearmroleprior;fallback;points/lawscoring',forest=base.FOREST,minimum_training_rows=60,training_floor_note='core3fitwindows withcommon2022memory;STRICTonly2026labels/features/priors/transforms,fixedhistoricallychosenarchitecture disclosed',availability='currentvintage source; kickoff+7days assumedavailable strictlybeforeweeklyfit and pergamefeaturecutoff; no historicalpublicationclaim',chart='samequalifiedpartial16componentlabels;35unknowncurrentlabelsretained;signed0.02grid; exactmedianprecisionintegercoordinate; meansneverrounded',source_vintage='current_vintage_reconstruction',previous_exposure='all2026W1-W7resultsalreadyexposed; mechanismtestnotuntouchedconfirmation',grid=[dict(week=w,target=t,policy_id=policy,history_regime=POLICIES[policy][0],state='REGISTERED')for w in range(1,8)for t in TARGETS for policy in POLICIES],budget=dict(max_fit_calls=336,wall_seconds=600,cpu_seconds=900,max_peak_memory_bytes=2147483648,max_private_bytes=536870912,max_source_rows=200000,max_forecast_rows=500000,max_threads=2,hyperparameter_searches=0),new_family_count=0,future_cells=0,week8_outcomes_read=0,official_capture=False,website_published=False)
    write(public_root/'FROZEN_PROTOCOL.json',p);return p


class Metrics:
    def __init__(self):self.rows=[]
    def add(self,row):self.rows.append(row)
    def result(self,target,product):
        scored=[r for r in self.rows if r['actual']is not None and r['prediction']is not None];p=[r['prediction']for r in scored];y=[r['actual']for r in scored];out=point_metrics(p,y,target)
        if out.get('log_loss')==math.inf:out['log_loss']='Infinity'
        ds=[r['distribution_summary']for r in scored];inf=sum(d['infinite_nll']for d in ds)
        out.update(forecast_rows=len(self.rows),fallback_rows=sum(r['fallback']!='none'for r in self.rows),scored_fallback_rows=sum(r['fallback']!='none'for r in scored),unique_games=len({r['game_id']for r in scored}),forecast_games=len({r['game_id']for r in self.rows}),CRPS=float(np.mean([d['crps']for d in ds]))if ds else None,NLL=None if inf or not ds else float(np.mean([d['nll']for d in ds])),infinite_NLL=inf,interval90_width=float(np.mean([d['interval90_width']for d in ds]))if ds else None,interval90_coverage=float(np.mean([d['interval90_covered']for d in ds]))if ds else None,mean_zero_mass=float(np.mean([d['zero_mass']for d in ds]))if ds else None)
        if target==CHART and product=='lower_median'and scored:
            exact=chart_median_precision(p,y,product_id=product);out.update({k:v['rate']for k,v in exact.items()});out['precision_counts_exact_grid']=exact
        return out


def run(*,source_root,control_public,control_private,chart_public,chart_private,public_root,private_root,sole_worker_confirmed=False):
    if not sole_worker_confirmed:raise ValueError('rootsolefitworkercoordinationrequired')
    source_root,control_public,control_private,chart_public,chart_private,public_root,private_root=map(Path,(source_root,control_public,control_private,chart_public,chart_private,public_root,private_root));p=loadjson(public_root/'FROZEN_PROTOCOL.json');start,cpu=time.monotonic(),time.process_time()
    if p['version']!=VERSION or p['code_sha256']!=sha(__file__):raise ValueError('frozenablationcodechanged')
    for m in(source,source.empirical,base,chart):
        if p['helpers'][Path(m.__file__).name]!=sha(m.__file__):raise ValueError('frozenhelperchanged')
    for filename,key in [('distribution_laws.py','law_code_sha256'),('precision_grid.py','precision_code_sha256'),('scoring.py','scoring_code_sha256')]:
        if sha(Path(__file__).with_name(filename))!=p[key]:raise ValueError('frozenlaw/precision/scoringhelperchanged')
    if sha(private_root/'frozen-queries.json')!=p['frozen_queries_sha256']:raise ValueError('frozenquerieschanged')
    for s in p['source_ids']:
        if sha(source_root/s['name'])!=s['sha256']:raise ValueError('sourcechanged')
    checks=loadjson(public_root/'SOFTWARE_CHECKS.json')
    if checks['status']!='PASS'or checks['code_sha256']!=sha(__file__):raise ValueError('exactcodesoftwarechecksrequired')
    write(public_root/'EXECUTION_REGISTRATION.json',dict(version=VERSION,actual_started_at_utc=now(),protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),sole_worker_confirmed=True,environment=dict(python=platform.python_version(),numpy=np.__version__),new_fits_before_registration=0))
    source_rows,games,source_counts=source.load_source(source_root,p);lookup={(r['game_id'],r['player_id']):r for r in source_rows};labelblob=(chart_private/'qualified-chart-labels.json.gz').read_bytes()
    if hashlib.sha256(labelblob).hexdigest()!=p['chart_label_packet_sha256']:raise ValueError('chartlabelschanged')
    for raw in json.loads(gzip.decompress(labelblob))['rows']:
        if int(raw['season'])not in range(2022,2027)or(int(raw['season'])==2026 and int(raw['week'])>7):continue
        lookup[raw['game_id'],raw['player_id']]['values'][CHART]=raw['label']['points_times_50']
    if any(CHART not in r['values']for r in source_rows):raise ValueError('chartlabelsnotboundtoallsourcegames')
    controls={}
    for spec,priv in zip(p['control_prediction_sources'],(control_private,chart_private)):
        file=priv/spec['artifact_id']
        if sha(file)!=spec['sha256']:raise ValueError('retainedcontrolchanged')
        with gzip.open(file,'rt',newline='')as h:
            for r in csv.DictReader(h):
                if r['season']!='2026'or int(r['week'])>7 or r.get('family')!=FAMILY:continue
                record={k:r[k]for k in('target','policy_id','game_id','player_id','population','position','history_regime','product_id','procedure_id','fallback')}
                for k in('prediction','actual'):record[k]=None if r[k]==''else float(r[k])
                k=controlkey(record)
                if k in controls:raise ValueError('duplicatecontrolrow')
                controls[k]=record
    histories={floor:base.feature_history(source_rows,floor)for floor in(2022,2026)};datasets={}
    for t in TARGETS:
        roles=set(source.POSITIONS)if t==CHART else source.allowed_roles(p,t);eligible=[r for r in source_rows if r['position']in roles and r['values'][t]is not None]
        for memory in(2022,2026):
            rs=[r for r in eligible if r['season']>=memory];x=[];maximum=[]
            for r in rs:
                f,m=histories[memory].get(r['player_id'],r['position'],t,r['kickoff']);x.append(f);maximum.append(m)
            datasets[t,memory]=(rs,project(np.asarray(x)),maximum)
    historical=collections.defaultdict(list)
    for q in loadjson(private_root/'frozen-queries.json'):
        r=lookup[q['game_id'],q['player_id']];t=q['target'];value=r['values'][t]
        historical[int(q['week'])].append(dict(q,season=2026,week=int(q['week']),kickoff=r['kickoff'],cutoff=r['kickoff'],actual_grid=value if t==CHART else None,actual=value/50 if t==CHART and value is not None else value,blocked_reason=None))
    for d in('models','query-features','prediction-chunks'):(private_root/d).mkdir(exist_ok=True)
    fits=retained=outputs=0;private_bytes=sum(f.stat().st_size for f in private_root.rglob('*')if f.is_file());allrows=[];failures=[];completed={};groups=collections.defaultdict(Metrics);terminal='COMPLETE'
    def guard():
        b=p['budget']
        if time.monotonic()-start>b['wall_seconds']or time.process_time()-cpu>b['cpu_seconds']:raise RuntimeError('TIME_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>b['max_peak_memory_bytes']:raise RuntimeError('RSS_BUDGET')
    def save(path,obj,raw=False):
        nonlocal private_bytes
        body=obj if raw else canonical(obj);blob=gzip.compress(body,mtime=0)
        if private_bytes+len(blob)>p['budget']['max_private_bytes']:raise RuntimeError('PRIVATE_BYTES_BEFORE_WRITE')
        with path.open('xb')as f:f.write(blob);f.flush();os.fsync(f.fileno())
        private_bytes+=len(blob)
        if path.read_bytes()!=blob:raise ValueError('privatereadbackfailed')
        return dict(name=path.relative_to(private_root).as_posix(),bytes=len(blob),sha256=sha(path),uncompressed_sha256=hashlib.sha256(body).hexdigest())
    with threadpool_limits(limits=2):
        try:
            for week in range(1,8):
                origin=min(g['kickoff']for g in games.values()if g['season']==2026 and g['week']==week)
                for target in TARGETS:
                    qrows=[q for q in historical[week]if q['target']==target]
                    for policy,(arm,floor,memory)in POLICIES.items():
                        guard();slot=f'W{week:02}-{target}-{policy}';rs,x,mx=datasets[target,memory];indices=np.asarray([i for i,r in enumerate(rs)if r['season']>=floor and r['available']<origin],dtype=int);y=np.asarray([rs[i]['values'][target]for i in indices]);positions=[rs[i]['position']for i in indices]
                        global_prior=laws_prior(y,target);counts={pos:positions.count(pos)for pos in source.POSITIONS};priors={pos:laws_prior([rs[i]['values'][target]for i in indices if rs[i]['position']==pos],target)if counts[pos]else global_prior for pos in source.POSITIONS}
                        oldslot=f'W{week:02}-{policy}-{FAMILY}'if target==CHART else f'W{week:02}-{target}-{policy}-{FAMILY}';oldpub=chart_public if target==CHART else control_public;oldfit=loadjson(oldpub/(oldslot+'-FIT.json'))
                        membership=hashlib.sha256(canonical([(rs[i]['game_id'],rs[i]['player_id'])for i in indices])).hexdigest();params={pos:law.parameters()for pos,law in priors.items()}
                        if oldfit['training_membership_sha256']!=membership or oldfit['prior_parameters']!=params or oldfit['prior_position_sample_counts']!=counts or aware(oldfit['fit_cutoff_utc'])!=origin or oldfit['feature_floor']!=memory:raise ValueError('controltraining/prior/cutoffbindingmismatch')
                        qfull=[];qm=[]
                        for q in qrows:
                            f,m=histories[memory].get(q['player_id'],q['position'],target,q['cutoff']);qfull.append(f);qm.append(m)
                        qx=project(np.asarray(qfull));feature_packet=save(private_root/'query-features'/(slot+'.json.gz'),[dict(query=q,features=source.json_features(f),latest_feature_available=m)for q,f,m in zip(qrows,qx,qm)])
                        audit=dict(slot=slot,target=target,week=week,policy_id=policy,history_regime=arm,feature_floor=memory,training_n=len(indices),training_seasons=sorted({rs[i]['season']for i in indices}),training_membership_sha256=membership,fit_cutoff_utc=datetime.fromtimestamp(origin,timezone.utc).isoformat(),latest_training_label_available=max((rs[i]['available']for i in indices),default=None),latest_training_feature_available=max((mx[i]for i in indices if mx[i]is not None),default=None),prior_parameters=params,prior_position_sample_counts=counts,control_fit_artifact=(oldpub/(oldslot+'-FIT.json')).as_posix(),control_fit_sha256=sha(oldpub/(oldslot+'-FIT.json')),control_training_and_priors_match=True,query_features=feature_packet,actual_fit_started_at=None,actual_fit_completed_at=None)
                        model=None;modelpacket=None;state='NO_FIT_INSUFFICIENT_TRAINING'
                        if len(indices)>=60:
                            if target in source.empirical.COUNTS and np.all(y==0):state='NO_FIT_ALL_ZERO_COUNT'
                            elif target=='anytime_td'and len(np.unique(y))<2:state='NO_FIT_SINGLE_CLASS_BINARY'
                            else:
                                if fits>=p['budget']['max_fit_calls']:raise RuntimeError('FIT_BUDGET')
                                fits+=1;audit['actual_fit_started_at']=now()
                                try:model=base.FittedLawModel(FAMILY,target).fit(x[indices],y,positions);audit['actual_fit_completed_at']=now()
                                except Exception as exc:model=None;state='FIT_FAILED_FALLBACK';audit['actual_fit_completed_at']=now();failures.append(dict(slot=slot,type=type(exc).__name__,reason=str(exc)[:240]))
                                if model is not None:guard();modelpacket=save(private_root/'models'/(slot+'.pickle.gz'),pickle.dumps(model,protocol=5),True);retained+=1;state='FITTED_RETAINED'
                        audit.update(state=state,model=modelpacket);write(public_root/(slot+'-FIT.json'),audit)
                        need=len(qrows)*len(products(target))
                        if outputs+need>p['budget']['max_forecast_rows']:raise RuntimeError('OUTPUT_BUDGET_BEFORE_INFERENCE')
                        inferred=model.predict(qx,[q['position']for q in qrows],priors)if model is not None else[(None,None)]*len(qrows);rows=[]
                        for q,f,m,(law,detail)in zip(qrows,qx,qm,inferred):
                            fallback='none'
                            if model is None or f[3]<=0:fallback='fixed_no_NFL_startup'if not len(indices)else'cold_start_role_prior'if f[3]<=0 else'no_model_role_prior';law=priors[q['position']];detail={'fallback_prior':law.parameters()}
                            if m is not None and m>=q['cutoff']:raise ValueError('queryfeatureleakage')
                            summary=chart.chart_summary(law,q['actual_grid'])if target==CHART else law.summary(q['actual'])
                            for product in products(target):
                                prediction=summary['mean'if product=='event_probability'else product];r=dict(q,run_id=VERSION,procedure_id=proc(policy),procedure_family_id=FAMILY,product_id=product,policy_id=policy,history_regime=arm,information_policy='STRICT-CURRENT'if memory==2026 else'COMMON-2022-MEMORY',feature_floor=memory,prediction=prediction,fallback=fallback,fit_slot=slot,fit_state=state,latest_feature_available=m,distribution_summary=summary,law_reference=detail,status='RECONSTRUCTED_RESEARCH_FORECAST',actual_generated_at=now());control=controls[controlkey(r)]
                                if control['actual']!=r['actual']or control['position']!=r['position']:raise ValueError('controlquery/labelmismatch')
                                r['control_prediction']=control['prediction'];r['control_procedure_id']=control['procedure_id'];r['control_fallback']=control['fallback']
                                views=[('ALL','ALL','ALL'),(str(week),'ALL','ALL'),('ALL',r['position'],'ALL')]
                                if fallback=='none':views.append(('ALL','ALL','LEARNED_ONLY'))
                                if fallback=='none'and control['fallback']=='none':views.append(('ALL','ALL','PAIRED_LEARNED_OVERLAP'))
                                for wk,pos,view in views:groups[(policy,target,r['population'],product,wk,pos,view)].add(r)
                                rows.append(r)
                        packet=save(private_root/'prediction-chunks'/(slot+'.json.gz'),dict(schema=VERSION,rows=rows));outputs+=len(rows);write(public_root/(slot+'-FORECAST.json'),dict(slot=slot,packet=packet,rows=len(rows),actual_persistence_completed_at=now(),new_future_forecasts=0));completed[slot]=state;allrows.extend(rows)
        except Exception as exc:terminal='PARTIAL_STOPPED';failures.append(dict(type=type(exc).__name__,reason=str(exc)[:240]))
    scores=[];comparisons=[];dates=[]
    for(policy,target,pop,product,wk,pos,view),metric in sorted(groups.items()):
        rows=metric.rows;scored=[r for r in rows if r['actual']is not None and r['prediction']is not None];pair=[r for r in scored if r['control_prediction']is not None];result=metric.result(target,product);record='C02-'+hashlib.sha256(canonical([policy,target,pop,product,wk,pos,view])).hexdigest()[:24]
        if len(pair)==len(scored)and pair:
            loss=lambda a,y:(a-y)**2 if target=='anytime_td'else abs(a-y)
            a=[loss(r['prediction'],r['actual'])for r in pair];b=[loss(r['control_prediction'],r['actual'])for r in pair];diff=[x-y for x,y in zip(a,b)];bg=collections.defaultdict(list)
            for r,d in zip(pair,diff):bg[r['game_id']].append(d)
            n=len(pair);g=len(bg);delta=math.fsum(diff)/n;se=math.sqrt(g/(g-1)*math.fsum((math.fsum(v)-len(v)*delta)**2 for v in bg.values())/n**2)if g>=8 else None
            comparison=dict(status='PAIRED_RETAINED_ROWS',comparator_procedure_id=pair[0]['control_procedure_id'],comparator_history_regime=pair[0]['history_regime'],comparator_product_id=product,metric='brier'if target=='anytime_td'else'mae',candidate_error=math.fsum(a)/n,comparator_error=math.fsum(b)/n,paired_n=n,membership_sha256=hashlib.sha256(canonical(sorted(ident(r)for r in pair))).hexdigest(),cutoff_policy='samepinnedweeklyfit/pergamefeaturecutoffsand7dayavailability;identicalpriors/trainingmembers',uncertainty=dict(week_clusters=len({r['week']for r in pair}),week_interval=None,game_cluster_sensitivity_se=se,reason='sevenexposedweekclusters;gameSEsensitivitynotselectionormultiplicityadjusted'))
        else:comparison=dict(status='UNESTABLISHED',reason='nosupportedpairedcontrolrowsonthisview')
        scores.append(dict(record_id=record,procedure_id=proc(policy),procedure_family_id=FAMILY,target=target,history_regime=POLICIES[policy][0],policy_id=policy,information_policy='STRICT-CURRENT'if POLICIES[policy][2]==2026 else'COMMON-2022-MEMORY',product_id=product,evaluation_panel_id=VERSION,population=pop,season=2026,week=int(wk)if wk.isdigit()else wk,position=pos,fallback_view=view,period='REG',record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',evidence='NEW_EXPERIMENT',source_vintage=p['source_vintage'],cohort_limit='sameexposed2026W1-W7retrospectivequerypopulation;sourceavailabilityassumed;chartpartialqualification;notexantehistoricalskill',comparison=comparison,scoring_version='native-point-with-exact-chart-median-grid-v1',**result))
        dates.append(dict(source_row_index=len(scores)-1,evaluation_seasons=[2026],evaluation_weeks=sorted({r['week']for r in scored}),actual_scored_weeks=sorted({r['week']for r in scored}),forecast_query_weeks=sorted({r['week']for r in rows}),registered_panel_weeks=list(range(1,8)),dimensions={k:scores[-1][k]for k in('procedure_id','target','history_regime','policy_id','product_id','population','week','position','fallback_view')}))
    write(public_root/'SCORES.json',scores);source.empirical.write_csv(public_root/'SCORES.csv',scores);write(public_root/'SCORE_DATE_PROJECTION.json',dict(source_score_artifact=(public_root/'SCORES.json').as_posix(),source_score_sha256=sha(public_root/'SCORES.json'),source_row_unit='zero-basedindexinimmutableSCORES.json',date_definition='actualsupportedweeks andforecastqueryweeks separately',rows=dates));write(public_root/'FAILURES.json',failures)
    grid=[dict(cell,slot=f"W{cell['week']:02}-{cell['target']}-{cell['policy_id']}",state=completed.get(f"W{cell['week']:02}-{cell['target']}-{cell['policy_id']}",'NOT_RUN_AFTER_BOUNDED_STOP'))for cell in p['grid']];write(public_root/'GRID_STATUS.json',grid)
    flat=save(private_root/'ALL_PREDICTIONS.json.gz',dict(schema=VERSION,rows=allrows))
    receipt=dict(version=VERSION,state=terminal,actual_completed_at_utc=now(),protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),code_sha256=sha(__file__),fit_opportunities=336,actual_fit_calls=fits,retained_models=retained,completed_cells=len(completed),remaining_cells=336-len(completed),forecast_output_views=outputs,score_views=len(scores),source_counts=source_counts,private_prediction_packet=flat,private_output_bytes=private_bytes,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2),new_family_count=0,new_future_forecasts=0,week8_outcomes_read=0,private_durability='LOCALREADBACK_PENDING_APPROVED_PRIVATECOMPANION')
    write(public_root/'RUN_RECEIPT.json',receipt);return receipt

def aware(value):return datetime.fromisoformat(value.replace('Z','+00:00')).timestamp()
