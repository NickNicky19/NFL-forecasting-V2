"""New finite HGB point ablations; no acquisition or mutation of original runs.

prepare() freezes contracts and supplied shared-origin query membership. run()
is an explicit sole-worker action, never called on import or by preparation.
Poisson is a fitting objective here, not an authenticated forecast distribution.
"""
from __future__ import annotations
import collections,gzip,json,math,os,pickle,platform,resource,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits
from . import hgb_control as source
from .hgb_control_guards import OutputViewBudget
from .scoring import point_metrics,valid_actual
from .shadow_grading import CONTRACTS,_safe_id,utc

VERSION='v2-hgb-count-ablation-wave-v1'
RA='v2-hgb-rush-att-qb-rb-specialization-v1'
POISSON='v2-hgb-poisson-count-point-reconstruction-v1'
COUNT_TARGETS=('pass_td','pass_cmp','pass_att','pass_int','rush_att','rec')
POLICIES={'H-CURRENT-COMMON':('H-CURRENT',2026,2022),'H-RECENT-COMMON':('H-RECENT',2025,2022),
          'H-MULTI-COMMON':('H-MULTI',2022,2022),'H-CURRENT-STRICT':('H-CURRENT',2026,2026)}
canonical=source.canonical;sha=source.sha;now=source.now;immutable_json=source.immutable_json


def families(target):
    if target not in COUNT_TARGETS:raise ValueError('unsupported count target')
    return (RA,POISSON)if target=='rush_att'else(POISSON,)


def training_roles(protocol,target,family):
    if family==RA:
        if target!='rush_att':raise ValueError('specialization only applies to rushing attempts')
        return {'QB','RB'}
    if family!=POISSON:raise ValueError('unknown new procedure')
    return source.allowed_roles(protocol,target)


def feature_history(rows,floor):
    if floor not in (2022,2026):raise ValueError('unregistered feature memory')
    return source.FeatureHistory([r for r in rows if r['season']>=floor])


def eligible_indices(rows,origin,fit_floor):
    return np.asarray([i for i,r in enumerate(rows)if fit_floor<=r['season']<=2026 and r['available']<origin],dtype=int)


def fit_state(y,family,minimum=40):
    if len(y)<minimum:return 'NO_FIT_INSUFFICIENT_TRAINING'
    if family==POISSON and not np.any(np.asarray(y)>0):return 'NO_FIT_ALL_ZERO_COUNT'
    return 'FIT_ELIGIBLE'


def make_estimator(family):
    if family not in (RA,POISSON):raise ValueError('unknown new procedure')
    return HistGradientBoostingRegressor(loss='absolute_error'if family==RA else'poisson',**source.PARAMS)


def output_count(queries):
    return sum(len(families(q['target']))*len(POLICIES)for q in queries if q['target']in COUNT_TARGETS)


def procedure_id(family,feature_floor):
    return family+(':strict-current-feature-memory'if feature_floor==2026 else':common-feature-memory')


def predict_admitted(model,x,queries):
    """Blocked/unknown identities never enter the estimator inference call."""
    result=[None]*len(queries);admitted=[i for i,q in enumerate(queries)if not q.get('blocked_reason')]
    if model is not None and admitted:
        values=model.predict(x[admitted])
        if len(values)!=len(admitted):raise ValueError('prediction census mismatch')
        for i,v in zip(admitted,values):result[i]=v
    return result


class Budget:
    def __init__(self,limits,existing_private_bytes=0):
        self.limits=limits;self.wall=time.monotonic();self.cpu=time.process_time()
        self.fits=0;self.private_bytes=existing_private_bytes;self.outputs=OutputViewBudget(limits['max_forecast_rows'])
    def check(self):
        b=self.limits
        if time.monotonic()-self.wall>b['wall_seconds']:raise RuntimeError('WALL_BUDGET')
        if time.process_time()-self.cpu>b['cpu_seconds']:raise RuntimeError('CPU_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>b['max_peak_memory_bytes']:raise RuntimeError('RSS_BUDGET')
        if self.private_bytes>b['max_private_bytes']:raise RuntimeError('PRIVATE_BYTE_BUDGET')
    def charge_fit(self):
        self.check()
        if self.fits>=self.limits['max_fit_calls']:raise RuntimeError('FIT_BUDGET')
        self.fits+=1
    def charge_private(self,n):
        self.check()
        if n<0 or self.private_bytes+n>self.limits['max_private_bytes']:raise RuntimeError('PRIVATE_BYTES_BEFORE_WRITE')
        self.private_bytes+=n


def prepare(*,source_root,old_protocol,shared_queries,shared_protocol,shared_execution,
            public_root,private_root,source_artifact_id):
    """Freeze a new identity from supplied shared-asof metadata, before any fit."""
    if not _safe_id(source_artifact_id):raise ValueError('approved public-safe source artifact ID required')
    public_root,private_root,source_root=map(Path,(public_root,private_root,source_root))
    if private_root.resolve().is_relative_to(Path(__file__).resolve().parents[1]):raise ValueError('private evidence must remain outside Git')
    public_root.mkdir(parents=True,exist_ok=True);private_root.mkdir(parents=True,exist_ok=True)
    base=json.loads(Path(old_protocol).read_bytes());shared=json.loads(Path(shared_protocol).read_bytes());execution=json.loads(Path(shared_execution).read_bytes())
    if execution.get('protocol_sha256')!=sha(shared_protocol):raise ValueError('shared execution/protocol binding mismatch')
    if shared.get('frozen_queries_sha256')!=sha(shared_queries):raise ValueError('shared frozen query bytes mismatch')
    for item in base['source_ids']:
        if sha(source_root/item['name'])!=item['sha256']:raise ValueError('original source hash mismatch')
    shared_sources={r['name']:r['sha256']for r in shared['source_ids']}
    if any(shared_sources.get(r['name'])!=r['sha256']for r in base['source_ids']):raise ValueError('different shared source bytes')
    asof=execution.get('actual_week8_feature_origin')or execution.get('actual_week8_feature_origin_utc')
    if utc(asof)>datetime.now(timezone.utc):raise ValueError('shared feature origin in future')
    queries=json.loads(Path(shared_queries).read_bytes())
    historical=[q for q in queries['historical']if q['target']in COUNT_TARGETS]
    future=[q for q in queries['week8']if q['target']in COUNT_TARGETS]
    if any(utc(q['owner_input_cutoff_utc'])<=utc(asof)for q in future):raise ValueError('shared cohort includes closed T90 game')
    packet=dict(historical=historical,week8=future)
    immutable_json(private_root/'frozen-queries.json',packet)
    grid=[dict(week=w,target=t,family=f,policy_id=p,history_regime=POLICIES[p][0],state='REGISTERED')
          for w in (8,1,2,3,4,5,6,7)for t in COUNT_TARGETS for p in POLICIES for f in families(t)]
    shared_origin=utc(asof).timestamp()
    games=source.schedules(source_root/'games.csv')
    # This discloses information changes versus old captures without new outcomes.
    old_root=Path(old_protocol).parent
    old_capture=json.loads((old_root/'WEEK8_CAPTURE_RECEIPT.json').read_bytes())
    old_asof=utc(old_capture['cutoff_utc']).timestamp()
    crossed=[g['game_id']for g in games.values()if old_asof<=g['kickoff']+7*86400<shared_origin]
    protocol=dict(version=VERSION,state='FROZEN_PRE_FIT_NEW_ABLATIONS',registered_at_utc=now(),code_sha256=sha(__file__),
        source_loader_sha256=sha(source.__file__),empirical_helper_sha256=sha(source.empirical.__file__),
        source_ids=base['source_ids'],source_artifact_id=source_artifact_id,source_role_contract=base['source_role_contract'],
        shared_protocol_sha256=sha(shared_protocol),shared_execution_sha256=sha(shared_execution),shared_queries_sha256=sha(shared_queries),
        frozen_queries_sha256=sha(private_root/'frozen-queries.json'),shared_week8_feature_origin_utc=asof,
        historical_query_cells=len(historical),future_query_cells=len(future),future_games=len({q['game_id']for q in future}),
        all_shared_query_cells=len(queries['week8']),all_shared_games=len({q['game_id']for q in queries['week8']}),
        old_hgb_feature_origin_utc=old_capture['cutoff_utc'],availability_boundaries_since_old_hgb=crossed,
        future_contract='Same shared asof football snapshot, actual later issue/persistence; partialweek still-openT90 cohorts, not exactT90 snapshot and never original14game capture',
        families={RA:dict(targets=['rush_att'],objective='absolute_error',product='absolute_loss_point',training_roles=['QB','RB'],mechanism='Change trainingroles only versus originalall4roleL1; originalfeaturesandparamsheldfixed'),
                  POISSON:dict(targets=list(COUNT_TARGETS),objective='poisson',product='poisson_intended_mean_point',mechanism='New corrected-count-point pathway; originalallrolespercategory; no oldCountAresultreproduction or CDF/PMF claim')},
        policies={k:dict(history_regime=a,fit_floor=b,feature_floor=c)for k,(a,b,c)in POLICIES.items()},
        feature_columns=list(source.FEATURES),params=source.PARAMS,minimum_training_rows=40,
        strict_contract='2026only outcomes in fit, ownfeatures and fallback; no historicalNFLpriors/encodings/calibration/retrieval. Architecture/settings inherited after earlierresearch exposure, current-vintage identities and retrospective observedparticipant cohort remain; no purityclaim about all provenance.',
        availability='Original current-vintage source; kickoff+7days assumedavailabilitystrictleftlimit; no actualpublicationclaim',
        chronology='Historical weeklyfit beforeearliestkickoff, featurequeryatgameleftlimit; futurefitandfeaturecutoff sharedasof from sourcewave; actualissueandpersistlater; no targetgameexposure',
        fallback='samearm sameposition ownplayer empirical; then sameposition empirical; then literal0; L1lower_median versus Poissonmean; unmatched identitiesABSTAIN; unfittedfallback updates atregisteredquerycutoff',
        scoring='All pointviewsMAE; intendedmeanMSE/RMSEseparate; signedbias/tails/strictinclusivecountprecision; no distribution scores, bettingprices or ROI',
        cohort='Fixed originalhistorical countsubset with primary/extended populations retained; observedstatrow/physicalevent diagnostic, not exante historicalproduct; same sharedfuture IDs selected onlybyclock',
        old_controls='All original forecasts/results untouched; no unchangedhistoricalrefits. OriginalbroadHGB/squaredloss/empirical controls remain separate source-bound records.',
        exposure='2026W1-W7 and earlierV2results alreadyexposed; newprocedureversion not pristine confirmation',
        grid=grid,budget=dict(max_fit_calls=224,max_source_rows=200000,max_forecast_rows=2000000,wall_seconds=1200,cpu_seconds=1800,max_peak_memory_bytes=1073741824,max_private_bytes=536870912,max_threads=2,hyperparameter_searches=0),
        expected_output_rows=output_count(historical+future),sole_worker='Root executes only after prior activefitwave completes; no overlapping fitworker',
        official_capture=False,website_published=False,new_fits_before_registration=0)
    immutable_json(public_root/'FROZEN_PROTOCOL.json',protocol)
    return protocol


class Metrics:
    def __init__(self):self.rows=[]
    def add(self,r):self.rows.append(r)
    def result(self,target):
        rows=self.rows;scored=[r for r in rows if r['prediction']is not None and r['actual']is not None]
        return dict(point_metrics([r['prediction']for r in scored],[r['actual']for r in scored],target),
            forecast_rows=len(rows),fallback_rows=sum(r['fallback']not in(None,'none')for r in rows),
            scored_fallback_rows=sum(r['fallback']not in(None,'none')for r in scored),unique_games=len({r['game_id']for r in scored}),
            coverage=dict(scored_rows=len(scored),offered_rows=len(rows),scored_games=len({r['game_id']for r in scored}),forecast_games=len({r['game_id']for r in rows}),
                abstention_rows=sum(r['prediction']is None for r in rows),played_missing_rows=sum(r['actual']is None for r in rows)))


def run(*,source_root,public_root,private_root,sole_worker_confirmed=False):
    if not sole_worker_confirmed:raise ValueError('root must verify previousfitworker finished before run')
    source_root,public_root,private_root=map(Path,(source_root,public_root,private_root))
    protocol_path=public_root/'FROZEN_PROTOCOL.json';p=json.loads(protocol_path.read_bytes())
    if p['version']!=VERSION or p['code_sha256']!=sha(__file__)or p['source_loader_sha256']!=sha(source.__file__)or p['empirical_helper_sha256']!=sha(source.empirical.__file__):raise ValueError('frozen code hash mismatch')
    checks=json.loads((public_root/'SOFTWARE_CHECKS.json').read_bytes())
    if checks.get('status')!='PASS'or checks.get('code_sha256')!=sha(__file__):raise ValueError('passing exact-code software receipt required')
    for d in p['source_ids']:
        if sha(source_root/d['name'])!=d['sha256']:raise ValueError('source byte mismatch')
    if sha(private_root/'frozen-queries.json')!=p['frozen_queries_sha256']:raise ValueError('query byte mismatch')
    qs=json.loads((private_root/'frozen-queries.json').read_bytes())
    if output_count(qs['historical']+qs['week8'])!=p['expected_output_rows']or p['expected_output_rows']>p['budget']['max_forecast_rows']:raise ValueError('output preflight mismatch/budget')
    shared_origin=utc(p['shared_week8_feature_origin_utc']).timestamp()
    if shared_origin>datetime.now(timezone.utc).timestamp():raise ValueError('future sharedasof')
    immutable_json(public_root/'EXECUTION_REGISTRATION.json',dict(version=VERSION,protocol_sha256=sha(protocol_path),actual_started_at=now(),shared_week8_feature_origin_utc=p['shared_week8_feature_origin_utc'],software_checks_sha256=sha(public_root/'SOFTWARE_CHECKS.json'),sole_worker_confirmed=True,environment=dict(python=platform.python_version(),sklearn=sklearn.__version__,numpy=np.__version__),new_fits_before_registration=0))
    guard=Budget(p['budget'],sum(f.stat().st_size for f in private_root.rglob('*')if f.is_file()))
    rows,games,source_counts=source.load_source(source_root,p);lookup={(r['game_id'],r['player_id']):r for r in rows}
    histories={floor:feature_history(rows,floor)for floor in (2022,2026)};datasets={};fallbacks={}
    for t in COUNT_TARGETS:
        for family in families(t):
            eligible=[r for r in rows if r['position']in training_roles(p,t,family)and r['values'][t]is not None]
            for policy,(arm,floor,memory)in POLICIES.items():
                selected=[r for r in eligible if r['season']>=memory];x=[];mx=[]
                for r in selected:
                    f,m=histories[memory].get(r['player_id'],r['position'],t,r['kickoff']);x.append(f);mx.append(m)
                datasets[(t,family,policy)]=(selected,np.asarray(x,dtype=float),mx)
                grouped=collections.defaultdict(list)
                for r in selected:
                    if r['season']>=floor:
                        item=(r['available'],(r['game_id'],r['player_id']),r['values'][t])
                        grouped[(r['position'],r['player_id'])].append(item);grouped[(r['position'],None)].append(item)
                fallbacks[(t,family,policy)]={k:source.empirical.Series(v)for k,v in grouped.items()}
    historical=collections.defaultdict(list)
    for q in qs['historical']:
        r=lookup[(q['game_id'],q['player_id'])]
        if r['position']!=q['position']:raise ValueError('historical identity mismatch')
        actual=r['values'][q['target']]
        if actual is not None and not valid_actual(q['target'],actual):raise ValueError('invalid count actual')
        historical[int(q['week'])].append(dict(q,query_id=__import__('hashlib').sha256(canonical([q[k]for k in ('game_id','player_id','target','population')])).hexdigest(),season=2026,week=int(q['week']),kickoff=r['kickoff'],cutoff=r['kickoff'],actual=actual,blocked_reason=None))
    future=[dict(q,season=2026,week=8,population='original_shared_open_T90_feed',kickoff=utc(q['kickoff_utc']).timestamp(),cutoff=shared_origin,actual=None)for q in qs['week8']]
    origins={w:min(g['kickoff']for g in games.values()if g['season']==2026 and g['week']==w)for w in range(1,8)};origins[8]=shared_origin
    for d in ('models','query-features','prediction-chunks'):(private_root/d).mkdir(exist_ok=True)
    def save(path,value,raw=False):
        body=value if raw else canonical(value);blob=gzip.compress(body,mtime=0);guard.charge_private(len(blob))
        with path.open('xb')as handle:handle.write(blob);handle.flush();os.fsync(handle.fileno())
        if path.read_bytes()!=blob:raise ValueError('artifact readback mismatch')
        return dict(name=path.relative_to(private_root).as_posix(),bytes=len(blob),sha256=sha(path),uncompressed_sha256=__import__('hashlib').sha256(body).hexdigest())
    failures=[];completed={};metrics=collections.defaultdict(Metrics);future_rows=[];fit_states=collections.Counter();retained=actual_outputs=0;terminal='COMPLETE'
    with threadpool_limits(limits=2):
        try:
            for w in (8,1,2,3,4,5,6,7):
                population=future if w==8 else historical[w];origin=origins[w]
                for target in COUNT_TARGETS:
                    qrows=[q for q in population if q['target']==target]
                    for family in families(target):
                        for policy,(arm,floor,memory)in POLICIES.items():
                            guard.check();guard.outputs.reserve(len(qrows))
                            slot=f'W{w:02}-{target}-{policy}-{family}'
                            qfeatures=[];qmax=[]
                            for q in qrows:
                                f,m=([math.nan]*len(source.FEATURES),None)if q['blocked_reason']else histories[memory].get(q['player_id'],q['position'],target,q['cutoff'])
                                qfeatures.append(f);qmax.append(m)
                            qx=np.asarray(qfeatures,dtype=float)
                            feature_packet=save(private_root/'query-features'/(slot+'.json.gz'),[dict(query=q,features=source.json_features(f),latest_feature_available=m)for q,f,m in zip(qrows,qfeatures,qmax)])
                            train,x,mx=datasets[(target,family,policy)];indices=eligible_indices(train,origin,floor)
                            if any(mx[i]is not None and mx[i]>=train[i]['kickoff']for i in indices):raise AssertionError('training feature leakage')
                            y=np.asarray([train[i]['values'][target]for i in indices]);state=fit_state(y,family,p['minimum_training_rows']);model=None;artifact=None
                            audit=dict(slot=slot,version=VERSION,family=family,target=target,policy_id=policy,history_regime=arm,feature_floor=memory,training_n=len(indices),training_seasons=sorted({train[i]['season']for i in indices}),training_roles=sorted(training_roles(p,target,family)),fit_cutoff_utc=datetime.fromtimestamp(origin,timezone.utc).isoformat(),latest_training_label_available=max((train[i]['available']for i in indices),default=None),latest_training_feature_available=max((mx[i]for i in indices if mx[i]is not None),default=None),training_membership_sha256=__import__('hashlib').sha256(canonical([(train[i]['game_id'],train[i]['player_id'])for i in indices])).hexdigest(),actual_fit_started_at=None,actual_fit_completed_at=None,query_features=feature_packet)
                            if state=='FIT_ELIGIBLE':
                                guard.charge_fit();audit['actual_fit_started_at']=now()
                                try:
                                    model=make_estimator(family);model.fit(x[indices],y);audit['actual_fit_completed_at']=now()
                                except Exception as exc:
                                    model=None;state='FIT_FAILED_FALLBACK';audit['actual_fit_completed_at']=now();failures.append(dict(slot=slot,exception=type(exc).__name__,reason=str(exc)[:240]))
                                if model is not None:
                                    guard.check();artifact=save(private_root/'models'/(slot+'.pickle.gz'),pickle.dumps(model,protocol=5),raw=True);state='FITTED_RETAINED';retained+=1
                            audit.update(state=state,model=artifact);immutable_json(public_root/(slot+'-FIT.json'),audit);fit_states[state]+=1
                            predicted=predict_admitted(model,qx,qrows)
                            generated=now();records=[]
                            for q,value,m in zip(qrows,predicted,qmax):
                                reason=q['blocked_reason'];fallback='none';n=latest=None
                                if w==8 and utc(generated)>=utc(q['owner_input_cutoff_utc']):reason=reason or'T90_CLOSED_BEFORE_ISSUANCE'
                                if reason:prediction=None;fallback=None
                                elif model is not None:prediction=source.project_point(target,value)
                                else:
                                    index=fallbacks[(target,family,policy)];own=index.get((q['position'],q['player_id']));s=own.at(q['cutoff'])if own else(0,None,None,None)
                                    fallback='own_empirical'
                                    if not s[0]:
                                        pooled=index.get((q['position'],None));s=pooled.at(q['cutoff'])if pooled else(0,None,None,None);fallback='position_empirical'if s[0]else'constant_zero'
                                    n,latest=s[0],s[3];prediction=float(s[2]if family==RA else s[1])if n else 0.
                                if m is not None and m>=q['cutoff']:raise AssertionError('query feature leakage')
                                if latest is not None and latest>=q['cutoff']:raise AssertionError('fallback leakage')
                                row=dict(q,run_id=VERSION,procedure_id=procedure_id(family,memory),procedure_family_id=family,history_regime=arm,policy_id=policy,feature_floor=memory,information_policy='2026_ONLY_FOOTBALL_FEATURES'if memory==2026 else'COMMON_2022_FEATURE_MEMORY',product_id=p['families'][family]['product'],objective=p['families'][family]['objective'],target_contract_id=CONTRACTS[target],prediction=prediction,fallback=fallback,fallback_n=n,latest_fallback_available=latest,latest_feature_available=m,fit_slot=slot,fit_state=state,status='ABSTAIN'if reason else'FORECASTED',abstention_reason=reason,actual_generated_at=generated,evidence_tier='genuine_new_partial_week_research_shadow'if w==8 else'current_vintage_observed_participant_reconstruction')
                                if w==8:row.update(issued_at_utc=generated,actual_horizon_seconds=q['kickoff']-utc(generated).timestamp(),owner_cutoff_status='BEFORE_OWNER_INPUT_CUTOFF'if not reason else'NOT_ISSUED',source_cutoff_utc=p['shared_week8_feature_origin_utc'])
                                else:
                                    views=[('ALL','ALL','ALL'),(str(w),'ALL','ALL'),('ALL',q['position'],'ALL')]
                                    if fallback=='none':views.append(('ALL','ALL','LEARNED_ONLY'))
                                    for weekview,pos,fb in views:metrics[(family,policy,target,q['population'],arm,weekview,pos,fb)].add(row)
                                records.append(row)
                            packet=save(private_root/'prediction-chunks'/(slot+'.json.gz'),dict(schema=VERSION,rows=records));persisted=now();actual_outputs+=len(records)
                            deadline_pass=all(utc(persisted)<utc(r['owner_input_cutoff_utc'])for r in records if r['prediction']is not None)if w==8 else None
                            if w==8 and not deadline_pass:raise RuntimeError('PERSISTENCE_T90_FAILED_PACKET_INVALID')
                            receipt=dict(slot=slot,packet=packet,actual_persistence_completed_at=persisted,rows=len(records),forecasted=sum(r['prediction']is not None for r in records),abstained=sum(r['prediction']is None for r in records),before_T90_persistence=deadline_pass)
                            immutable_json(public_root/(slot+'-FORECAST.json'),receipt);completed[slot]=state
                            if w==8:future_rows.extend(records)
                if w==8:
                    packet=save(private_root/'WEEK8_OPEN_T90_SHADOWS.json.gz',dict(schema=VERSION,rows=future_rows))
                    immutable_json(public_root/'WEEK8_CAPTURE_RECEIPT.json',dict(version=VERSION,state='NEW_PARTIAL_WEEK_RESEARCH_SHADOW_LOCAL_READBACK_PENDING_OFFHOST',packet=packet,protocol_sha256=sha(protocol_path),actual_completed_at=now(),feature_origin_utc=p['shared_week8_feature_origin_utc'],actual_issue_first_utc=min((r['issued_at_utc']for r in future_rows),default=None),actual_issue_last_utc=max((r['issued_at_utc']for r in future_rows),default=None),query_cells=len(future),games=len({q['game_id']for q in future}),output_views=len(future_rows),forecasted=sum(r['prediction']is not None for r in future_rows),abstained=sum(r['prediction']is None for r in future_rows),actuals_read=0,official_capture=False,website_published=False))
        except Exception as exc:
            terminal='PARTIAL_STOPPED';failures.append(dict(exception=type(exc).__name__,reason=str(exc)[:240]))
    scores=[]
    for(family,policy,target,population,arm,week,pos,fb),meter in sorted(metrics.items()):
        scores.append(dict(procedure_id=procedure_id(family,POLICIES[policy][2]),procedure_family_id='hgb-rush-att-role-specialization'if family==RA else'hgb-poisson-objective-count-point',policy_id=policy,history_regime=arm,target=target,product_id=p['families'][family]['product'],objective=p['families'][family]['objective'],evaluation_panel_id='source-matched-observed-participant-2026-W1-W7-count-ablation-v1',population=population,season=2026,week=int(week)if week.isdigit()else week,position=pos,fallback_view=fb,period='REG',record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',evidence='NEW_EXPERIMENT',target_contract_id=CONTRACTS[target],feature_memory_policy=p['strict_contract']if POLICIES[policy][2]==2026 else'Common2022-startfeaturememory; H-CURRENT=current-seasonfittingonly',source_vintage=p['availability'],cohort_limit=p['cohort'],**meter.result(target)))
    immutable_json(public_root/'SCORES.json',scores);source.empirical.write_csv(public_root/'SCORES.csv',scores)
    grid=[]
    for cell in p['grid']:
        slot=f"W{cell['week']:02}-{cell['target']}-{cell['policy_id']}-{cell['family']}"
        grid.append(dict(cell,slot=slot,state=completed.get(slot,'NOT_RUN_AFTER_BOUNDED_STOP')))
    immutable_json(public_root/'GRID_STATUS.json',grid);immutable_json(public_root/'FAILURES.json',failures)
    receipt=dict(version=VERSION,state=terminal,actual_completed_at=now(),protocol_sha256=sha(protocol_path),code_sha256=sha(__file__),source_counts=source_counts,fit_opportunities=len(grid),actual_fit_calls=guard.fits,retained_models=retained,fit_state_counts=dict(fit_states),completed_cells=len(completed),remaining_cells=len(grid)-len(completed),reserved_output_rows=guard.outputs.reserved,actual_output_rows=actual_outputs,score_views=len(scores),future_output_rows=len(future_rows),future_games=p['future_games'],shared_feature_origin_utc=p['shared_week8_feature_origin_utc'],week8_outcomes_read=0,private_output_bytes=guard.private_bytes,resource=dict(wall_seconds=time.monotonic()-guard.wall,cpu_seconds=time.process_time()-guard.cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2),official_capture=False,website_published=False,private_durability='LOCAL_READBACK_ONLY_UNTIL_APPROVED_COMPANION_RECEIPT')
    immutable_json(public_root/'RUN_RECEIPT.json',receipt);return receipt
