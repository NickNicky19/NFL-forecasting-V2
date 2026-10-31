"""Qualified partial-chart empirical history and direct distribution extension.

No acquisition or production write. Grid50 is a bijective discrete coordinate;
log PMF mass is unchanged while points/CRPS/interval widths divide by50.
"""
from __future__ import annotations
import collections,csv,gzip,hashlib,json,math,pickle,platform,resource,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from . import chart_sources,empirical_benchmark as empirical,hgb_control as source
from .distribution_wave_v2 import FittedLawModel,DistributionMetrics,POLICIES,FAMILIES,predict_admitted,FOREST,GLM
from .distribution_laws import Law

VERSION='v2-qualified-partial-chart-direct-wave-v1';TARGET='nick-chart-ppr-v1';SCALE=50
canonical=source.canonical;sha=source.sha;now=source.now;immutable_json=source.immutable_json

def chart_prior(y):
    y=np.asarray(y,dtype=float)
    if not len(y):return Law('zero')
    center=int(np.sort(y)[(len(y)-1)//2]);scale=max(50.,float(np.abs(y-center).mean()));return Law('signed',center=center,q=scale/(1+scale))
class ChartModel(FittedLawModel):
    def fit(self,x,y,positions):
        super().fit(x,y,positions)
        if self.family=='regularized_glm_law':self.scale={p:max(50.,s) for p,s in self.scale.items()}
        return self

def chart_summary(law,actual):
    d=law.summary(actual)
    for key in ('mean','lower_median','q05','q95','interval90_width','crps'):
        if d[key] is not None:d[key]/=50
    d['grid_denominator']=50;d['nll_definition']='PMFmass at exact score*50; no density/Jacobian';return d

def chart_future(queries,instant):
    out={};closed=[]
    for q in queries:
        if source.utc(q['owner_input_cutoff_utc']).timestamp()<=instant:closed.append(q);continue
        identity=q['player_id'] or 'sleeper:'+str(q['sleeper_id']);key=(q['game_id'],identity)
        candidate={k:q.get(k) for k in ('game_id','player_id','sleeper_id','position','kickoff_utc','owner_input_cutoff_utc','blocked_reason')};candidate['target']=TARGET
        if key in out:
            if out[key]!=candidate:raise ValueError('conflicting chart future frozen context')
        else:out[key]=candidate
    return list(out.values()),closed

def prepare(source_root,previous_queries,old_protocol,public_root,private_root,policy_path,durability_path,shared_asof):
    public_root,private_root=Path(public_root),Path(private_root);public_root.mkdir(parents=True,exist_ok=True);private_root.mkdir(parents=True,exist_ok=True)
    policy=json.loads(Path(policy_path).read_text());durability=json.loads(Path(durability_path).read_text())
    if sha(policy_path)!=chart_sources.POLICY_SHA256 or durability['state']!='OWNER_ONLY_UNSHARED_FRESH_DOWNLOAD_HASH_VERIFIED':raise ValueError('unqualified chartpolicy/durability')
    old=json.loads(Path(old_protocol).read_text());hist=[]
    for item in old['source_ids']:
        if sha(Path(source_root)/item['name'])!=item['sha256']:raise ValueError('source bytes changed')
    for year in range(2022,2027):
        with (Path(source_root)/f'stats_player_week_{year}.csv').open() as f:
            for r in csv.DictReader(f):
                if r['season_type']!='REG' or r['season']!=str(year) or (year==2026 and int(r['week'])>7) or r['position'] not in source.POSITIONS:continue
                if not __import__('re').fullmatch(r'00-\d{7}',r['player_id']):continue
                hist.append(dict(season=year,week=int(r['week']),game_id=r['game_id'],player_id=r['player_id'],position=r['position'],target=TARGET,population='primary'))
    previous=json.loads(Path(previous_queries).read_text());future,closed=chart_future(previous['week8'],datetime.now(timezone.utc).timestamp())
    if len({(q['game_id'],q['player_id']) for q in hist})!=len(hist):raise ValueError('duplicate historicalchartquery')
    immutable_json(private_root/'frozen-queries.json',dict(historical=hist,week8=future,closed_t90_source_query_cells=len(closed)+len(previous.get('closed_t90',[]))))
    grid=[dict(week=w,family=f,policy_id=p,history_regime=POLICIES[p][0],target=TARGET,state='REGISTERED') for w in (8,1,2,3,4,5,6,7) for p in POLICIES for f in FAMILIES]
    protocol=dict(version=VERSION,state='FROZEN_BEFORE_CHART_LABEL_DECODE_AND_FITS',registered_at_utc=now(),code_sha256=sha(__file__),chart_adapter_sha256=sha(chart_sources.__file__),chart_policy_id=chart_sources.POLICY_ID,chart_policy_sha256=sha(policy_path),chart_policy_artifact='reports/continuation-20261030/CHART_PPR_PARTIAL_LABEL_POLICY_V2.json',durability_receipt_sha256=sha(durability_path),source_ids=old['source_ids'],source_loader_sha256=sha(source.__file__),empirical_helper_sha256=sha(empirical.__file__),distribution_helper_sha256=sha(Path(__file__).with_name('distribution_wave_v2.py')),law_helper_sha256=sha(Path(__file__).with_name('distribution_laws.py')),source_role_contract=old['source_role_contract'],frozen_queries_sha256=sha(private_root/'frozen-queries.json'),prior_query_packet_sha256=sha(previous_queries),expected_output_views=len(hist)*6+(sum(q['season']==2026 for q in hist)+len(future))*16,historical_query_cells=len(hist),current_2026_query_cells=sum(q['season']==2026 for q in hist),future_query_cells=len(future),future_games=len({q['game_id'] for q in future}),fixed_feature_origin_utc=shared_asof,point_grid_denominator=50,exact_weights_times_50=chart_sources.WEIGHTS_TIMES_50,label_contract='qualified16components;bothrareaggregatesexplicit0 onlyprovesrarezeros;positives/missingnull;allqueryrowsretained;source-providercompletenesstiernotrareeventcensus',appearance='samepositiveofficialphysicaleventproofasfrozenempirical/HGBsourcehelper; no inferencefromrowexistence',finality='beforechart_label: cachedschedulehome_score/away_score finite nonnegativeinteger; cachedresult equals home-away andtotal equals home+away; bound sixsourcehashes; onlyREG2022–25/2026W1–7 decoded',families=list(FAMILIES),policies={k:dict(history_regime=v[0],fit_floor=v[1],feature_floor=v[2]) for k,v in POLICIES.items()},feature_contract='ownchartgridtarget mean3/8,counts,last4values/age/missing,positiononehot;common2022memoryorstrict2026only; no componentforecasts or injury/markets',forest_parameters=FOREST,glm_parameters=GLM,glm='signed Ridge alpha10;training-only impute/standardization; roundedintegergridlocation; roletrainingresidualscale shrunk10towardglobal then max50gridunits; uncalibrateddiscreteLaplace law',prior='samearmpositionthen global signedintegerdiscreteLaplace,lower-median center,scale=max50gridunits,meanabsolute deviation;no labels =>pointmass0',forest_law='95%equal-tree empirical leafPMF+5%samearmpositionfullsupportprior; same32/depth8/minleaf30 parametersasqualifieddistributionwave',minimum_training_rows={'ordered_leaf_cdf':60,'regularized_glm_law':40},empirical='2022–26rollingpergame earliereligible chartlabels;3fitwindows;own/sameposition empiricalmean/lower-median thenpositionthenliteral0; STRICT aliasCURRENT exactly,notnewfit/family',historical_refit='onefitbeforeearliest2026weeklykickoff;trainlabel kickoff+7days strictlybeforeorigin;trainingfeaturesat ownkickoff; queryfeaturesrefreshat historicalkickoff',strict='only2026footballoutcomes labels/features/priors/transforms, historicallyselectedfixedarchitecture disclosed; completeinformationpolicycomparison',distribution_units='chartpointpredictions/quantiles/width/CRPS=gridvalue/50; PMFlogmass unchanged; genuine directtotallaw, no componentmedian sum or jointlawclaim',future='newchartqueriesdedupGSISorrawSleeperIDfromsamefrozenexantequeryunion; preserveblockedunknowncontexts; no newroles/players/targetoutcomes; sourceasof0:27 snapshot,actualnewissue and persistence beforeeachT90',previous_exposure='LegacychartandcurrentV2methodsseen;thisnewqualifiedpartiallabelprocedureisnotuntouchedconfirmation',grid=grid,budget=dict(max_fit_calls=64,wall_seconds=1200,cpu_seconds=1800,max_peak_memory_bytes=2147483648,max_private_bytes=536870912,max_source_rows=200000,max_forecast_rows=1500000,max_threads=2,hyperparameter_searches=0),new_family_count=0,official_capture=False,website_published=False)
    immutable_json(public_root/'FROZEN_PROTOCOL.json',protocol);return protocol

def load_chart_source(source_root,protocol):
    rows,games,counts=source.load_source(source_root,protocol);lookup={(r['game_id'],r['player_id']):r for r in rows};finality={}
    with (Path(source_root)/'games.csv').open() as f:
        for raw in csv.DictReader(f):
            if raw['game_type']!='REG' or raw['season'] not in {str(y) for y in range(2022,2027)} or (raw['season']=='2026' and int(raw['week'])>7):continue
            # Outcome fields below are label-finality checks only, never predictors.
            hs=empirical.numeric(raw['home_score']);aws=empirical.numeric(raw['away_score']);result=empirical.numeric(raw['result']);total=empirical.numeric(raw['total'])
            finality[raw['game_id']]=bool(empirical.valid_count(hs) and empirical.valid_count(aws) and result is not None and total is not None and result==hs-aws and total==hs+aws)
    labels=[];coverage=collections.Counter()
    for year in range(2022,2027):
        with (Path(source_root)/f'stats_player_week_{year}.csv').open() as f:
            for raw in csv.DictReader(f):
                if raw['season_type']!='REG' or raw['season']!=str(year) or (year==2026 and int(raw['week'])>7):continue
                key=(raw['game_id'],raw['player_id'])
                if key not in lookup:continue
                row=lookup[key];label=chart_sources.chart_label(raw,source_sha256=chart_sources.CSV_SHA256_BY_SEASON[year],appearance_verified=bool(row['played']),game_completed_verified=finality.get(raw['game_id'],False));row['values'][TARGET]=label['points_times_50'];row['chart_status']=label['status'];coverage[(year,label['status'])]+=1;labels.append(dict(game_id=row['game_id'],player_id=row['player_id'],season=year,week=row['week'],position=row['position'],label=label))
    if len(labels)!=len(rows):raise ValueError('chart sourcebindingmissing')
    return rows,games,counts,labels,coverage

def run(source_root,public_root,private_root):
    start,cpu=time.monotonic(),time.process_time();public_root,private_root=Path(public_root),Path(private_root);protocol=json.loads((public_root/'FROZEN_PROTOCOL.json').read_text())
    for file,key in [(Path(__file__),'code_sha256'),(Path(chart_sources.__file__),'chart_adapter_sha256'),(Path(source.__file__),'source_loader_sha256'),(Path(empirical.__file__),'empirical_helper_sha256'),(Path(__file__).with_name('distribution_wave_v2.py'),'distribution_helper_sha256'),(Path(__file__).with_name('distribution_laws.py'),'law_helper_sha256')]:
        if sha(file)!=protocol[key]:raise ValueError('frozen code changed:'+key)
    if protocol['version']!=VERSION or sha(private_root/'frozen-queries.json')!=protocol['frozen_queries_sha256']:raise ValueError('protocol/query binding')
    for item in protocol['source_ids']:
        if sha(Path(source_root)/item['name'])!=item['sha256']:raise ValueError('source changed')
    checks=json.loads((public_root/'SOFTWARE_CHECKS.json').read_text());assert checks['state']=='PASS' and checks['code_sha256']==sha(__file__)
    if protocol['expected_output_views']>protocol['budget']['max_forecast_rows']:raise RuntimeError('FORECAST_PREFLIGHT_BUDGET')
    fixed_origin=source.utc(protocol['fixed_feature_origin_utc']).timestamp();immutable_json(public_root/'EXECUTION_REGISTRATION.json',dict(version=VERSION,actual_started_at=now(),fixed_feature_origin_utc=protocol['fixed_feature_origin_utc'],protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),environment=dict(python=platform.python_version(),numpy=np.__version__),new_fits_before_registration=0,chart_points_source='qualifiedpartiallabelcontract;noWeek8outcomes'))
    rows,games,source_counts,labels,coverage=load_chart_source(source_root,protocol);lookup={(r['game_id'],r['player_id']):r for r in rows};queries=json.loads((private_root/'frozen-queries.json').read_text())
    private_bytes=sum(p.stat().st_size for p in private_root.rglob('*') if p.is_file());fit_calls=model_count=reserved=output_views=0;grid=[];failures=[];groups=collections.defaultdict(DistributionMetrics);future_records=[];terminal='COMPLETE'
    for dirname in ('models','query-features','prediction-chunks'):(private_root/dirname).mkdir(exist_ok=True)
    def guard():
        if time.monotonic()-start>protocol['budget']['wall_seconds']:raise RuntimeError('WALL_BUDGET')
        if time.process_time()-cpu>protocol['budget']['cpu_seconds']:raise RuntimeError('CPU_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>protocol['budget']['max_peak_memory_bytes']:raise RuntimeError('RSS_BUDGET')
        if private_bytes>protocol['budget']['max_private_bytes']-4194304:raise RuntimeError('PRIVATE_BYTE_BUDGET')
    def save(path,obj,raw=False):
        nonlocal private_bytes
        body=gzip.compress(obj if raw else canonical(obj),mtime=0)
        if private_bytes+len(body)>protocol['budget']['max_private_bytes']-4194304:raise RuntimeError('PRIVATE_BYTE_BUDGET_BEFORE_WRITE')
        with path.open('xb') as f:f.write(body);f.flush();__import__('os').fsync(f.fileno())
        private_bytes+=len(body);return dict(artifact_id='ART-CHART-'+sha(path),bundle_name=path.relative_to(private_root).as_posix(),sha256=sha(path),bytes=len(body))
    label_packet=save(private_root/'qualified-chart-labels.json.gz',dict(schema=VERSION,policy_sha256=protocol['chart_policy_sha256'],rows=labels))
    source_coverage=[dict(season=k[0],status=k[1],query_rows=n) for k,n in sorted(coverage.items())];empirical.write_csv(public_root/'LABEL_COVERAGE.csv',source_coverage)
    histories={floor:source.FeatureHistory([r for r in rows if r['season']>=floor]) for floor in (2022,2026)};datasets={}
    for floor in (2022,2026):
        eligible=[r for r in rows if r['season']>=floor and r['values'][TARGET] is not None];x=[];maximum=[]
        for r in eligible:
            f,m=histories[floor].get(r['player_id'],r['position'],TARGET,r['kickoff']);x.append(f);maximum.append(m)
        datasets[floor]=(eligible,np.asarray(x,dtype=float),np.asarray([r['values'][TARGET] for r in eligible]),maximum)
    historical=collections.defaultdict(list)
    for q in queries['historical']:
        row=lookup[(q['game_id'],q['player_id'])]
        if q['season']==2026:historical[q['week']].append(dict(q,cutoff=row['kickoff'],kickoff=row['kickoff'],actual_grid=row['values'][TARGET],actual=None if row['values'][TARGET] is None else row['values'][TARGET]/50,actual_status=row['chart_status'],blocked_reason=None))
    future=[dict(q,season=2026,week=8,population='original_pregame_feed_union',cutoff=fixed_origin,kickoff=source.utc(q['kickoff_utc']).timestamp(),actual_grid=None,actual=None,actual_status='PENDING_FUTURE') for q in queries['week8']]
    origins={w:min(g['kickoff'] for g in games.values() if g['season']==2026 and g['week']==w) for w in range(1,8)};origins[8]=fixed_origin
    with threadpool_limits(limits=2):
        try:
            for week in (8,1,2,3,4,5,6,7):
                origin=origins[week];qrows=future if week==8 else historical[week]
                for policy,(arm,fit_floor,feature_floor) in POLICIES.items():
                    guard();features=[];maxima=[]
                    for q in qrows:
                        f,m=histories[feature_floor].get(q['player_id'],q['position'],TARGET,q['cutoff']);features.append(f);maxima.append(m)
                    qx=np.asarray(features,dtype=float);train,tx,ty,tm=datasets[feature_floor];indices=np.asarray([i for i,r in enumerate(train) if r['season']>=fit_floor and r['available']<origin],dtype=int);positions=[train[i]['position'] for i in indices];prior_counts={p:positions.count(p) for p in source.POSITIONS};global_prior=chart_prior(ty[indices]);priors={p:chart_prior([ty[i] for i in indices if train[i]['position']==p]) if prior_counts[p] else global_prior for p in source.POSITIONS}
                    feature_packet=save(private_root/'query-features'/f'W{week:02}-{policy}.json.gz',[dict(query=q,features=source.json_features(f),latest_feature_available=m) for q,f,m in zip(qrows,features,maxima)])
                    for family in FAMILIES:
                        guard();slot=f'W{week:02}-{policy}-{family}';model=None;packet=None;state='NO_FIT_INSUFFICIENT_TRAINING'
                        audit=dict(slot=slot,week=week,target=TARGET,family=family,policy_id=policy,history_regime=arm,training_n=len(indices),training_seasons=sorted({train[i]['season'] for i in indices}),feature_floor=feature_floor,fit_cutoff_utc=datetime.fromtimestamp(origin,timezone.utc).isoformat(),latest_training_label_available=max((train[i]['available'] for i in indices),default=None),latest_training_feature_available=max((tm[i] for i in indices if tm[i] is not None),default=None),training_membership_sha256=hashlib.sha256(canonical([(train[i]['game_id'],train[i]['player_id']) for i in indices])).hexdigest(),prior_parameters={p:v.parameters() for p,v in priors.items()},prior_position_sample_counts=prior_counts,query_features=feature_packet,actual_fit_started_at=None,actual_fit_completed_at=None)
                        if len(indices)>=protocol['minimum_training_rows'][family]:
                            if fit_calls>=protocol['budget']['max_fit_calls']:raise RuntimeError('FIT_CALL_BUDGET')
                            fit_calls+=1;audit['actual_fit_started_at']=now()
                            try:
                                model=ChartModel(family,TARGET).fit(tx[indices],ty[indices],positions);audit['actual_fit_completed_at']=now();packet=save(private_root/'models'/(slot+'.pickle.gz'),pickle.dumps(model,protocol=5),raw=True);model_count+=1;state='FITTED_RETAINED'
                            except Exception as exc:state='FIT_FAILED_FALLBACK';model=None;audit['actual_fit_completed_at']=now();failures.append(dict(slot=slot,type=type(exc).__name__,reason=str(exc)[:240]))
                        audit.update(state=state,model=packet);immutable_json(public_root/(slot+'-FIT.json'),audit)
                        need=len(qrows)*2
                        if reserved+need>protocol['budget']['max_forecast_rows']:raise RuntimeError('FORECAST_BUDGET_BEFORE_INFERENCE')
                        reserved+=need;predicted=predict_admitted(model,qx,qrows,priors);generated=now();records=[]
                        for q,f,m,(law,detail) in zip(qrows,features,maxima,predicted):
                            reason=q.get('blocked_reason') or ('UNQUALIFIED_POSITION' if q.get('position') not in source.POSITIONS else None);fallback='none'
                            if week==8 and datetime.now(timezone.utc).timestamp()>=source.utc(q['owner_input_cutoff_utc']).timestamp():reason=reason or 'T90_CLOSED_BEFORE_ISSUANCE'
                            if not reason:
                                if model is None or f[3]<=0:
                                    fallback='fixed_no_NFL_startup' if not len(indices) else 'cold_start_role_prior' if f[3]<=0 else 'no_model_role_prior';law=priors[q['position']];detail={'fallback_prior':law.parameters()}
                                d=chart_summary(law,q['actual_grid'])
                            else:d=None
                            for product in ('mean','lower_median'):
                                prediction=None if reason else d[product];record=dict(q,run_id=VERSION,family=family,procedure_id=VERSION+':'+family+':'+('strict-current-inputs' if feature_floor==2026 else 'common-feature-memory'),history_regime=arm,policy_id=policy,information_policy='STRICT-CURRENT' if feature_floor==2026 else 'COMMON-2022-MEMORY',product_id=product,prediction=prediction,fallback=None if reason else fallback,fallback_source=None if reason or fallback=='none' else 'fixed_no_NFL_startup' if not len(indices) else 'same_arm_position_prior' if prior_counts[q['position']] else 'same_arm_global_prior',fallback_source_n=None if reason or fallback=='none' else prior_counts[q['position']] or len(indices),fit_slot=slot,fit_state=state,latest_feature_available=m,distribution_summary=d,law_reference=detail,status='ABSTAIN' if reason else 'FORECASTED',abstention_reason=reason,actual_generated_at=generated)
                                if week==8:record.update(issued_at_utc=generated,actual_horizon_seconds=q['kickoff']-source.utc(generated).timestamp(),owner_cutoff_status='BEFORE_OWNER_INPUT_CUTOFF' if not reason else 'NOT_ISSUED')
                                if m is not None and m>=q['cutoff']:raise AssertionError('query feature leakage')
                                if prediction is not None and week!=8:
                                    for wk,pos,view in [('ALL','ALL','ALL'),(str(week),'ALL','ALL'),('ALL',q['position'],'ALL')]+([('ALL','ALL','LEARNED_ONLY')] if fallback=='none' else []):groups[(family,policy,arm,product,wk,pos,view)].add(record)
                                records.append(record)
                        pred_packet=save(private_root/'prediction-chunks'/(slot+'.json.gz'),dict(schema=VERSION,rows=records));persisted=now()
                        before=all(source.utc(persisted)<source.utc(r['owner_input_cutoff_utc']) for r in records if r['prediction'] is not None) if week==8 else None
                        if week==8 and not before:raise RuntimeError('T90_PERSISTENCE_FAILED_INVALID_PACKET')
                        output_views+=len(records);receipt=dict(slot=slot,packet=pred_packet,actual_persistence_completed_at=persisted,output_views=len(records),issued=sum(r['prediction'] is not None for r in records),abstained=sum(r['prediction'] is None for r in records),all_before_T90_persistence=before);immutable_json(public_root/(slot+'-FORECAST.json'),receipt);grid.append(dict(slot=slot,state=state,forecast_receipt=receipt))
                        if week==8:future_records.extend(records)
                if week==8:
                    futurepacket=save(private_root/'WEEK8_CHART_SHADOWS.json.gz',dict(schema=VERSION,rows=future_records));immutable_json(public_root/'WEEK8_CAPTURE_RECEIPT.json',dict(version=VERSION,packet=futurepacket,state='CAPTURED_OPEN_T90_LOCAL_READBACK_OFFHOST_PENDING',actual_completed_at=now(),fixed_feature_origin_utc=protocol['fixed_feature_origin_utc'],output_views=len(future_records),issued=sum(r['prediction'] is not None for r in future_records),abstained=sum(r['prediction'] is None for r in future_records),query_cells=len(future),games=len({r['game_id'] for r in future_records}),actuals_read=0,new_fit_calls=fit_calls,official_capture=False,website_published=False))
        except Exception as exc:terminal='PARTIAL_STOPPED';failures.append(dict(type=type(exc).__name__,reason=str(exc)[:240]))
    scores=[]
    for (family,policy,arm,product,wk,pos,view),metrics in sorted(groups.items()):
        result=metrics.result();strict=POLICIES[policy][2]==2026;scores.append(dict(procedure_id=VERSION+':'+family+':'+('strict-current-inputs' if strict else 'common-feature-memory'),procedure_family_id=family,target=TARGET,history_regime=arm,policy_id=policy,information_policy='STRICT-CURRENT' if strict else 'COMMON-2022-MEMORY',product_id=product,evaluation_panel_id='qualified-partial-chart-observed-participant-2026-W1-W7-v1',population='primary',season=2026,period='REG',week=int(wk) if wk.isdigit() else wk,position=pos,fallback_view=view,record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',evidence='NEW_EXPERIMENT',n=result['scored_n'],forecast_rows=result['forecast_queries'],fallback_rows=result['fallback_n'],feature_memory_policy='2026-onlychartlabels/features/priors/transforms' if strict else 'common2022+chartmemory across3fittingarms',chart_source_policy=chart_sources.POLICY_ID,point_grid_denominator=50,**result))
    immutable_json(public_root/'SCORES.json',scores);empirical.write_csv(public_root/'SCORES.csv',scores);done={r['slot']:r['state'] for r in grid};full=[]
    for r in protocol['grid']:
        slot=f"W{r['week']:02}-{r['policy_id']}-{r['family']}";full.append(dict(r,slot=slot,state=done.get(slot,'NOT_RUN_AFTER_BOUNDED_STOP')))
    immutable_json(public_root/'GRID_STATUS.json',full);immutable_json(public_root/'FAILURES.json',failures)
    # Arithmetic historical controls use the same chart labels/population; STRICT
    # is a registered exact CURRENT alias, never an additional learner or fit.
    empirical_scores=[];empirical_rows=[];egroups=collections.defaultdict(empirical.Metrics);egames=collections.defaultdict(set);efgames=collections.defaultdict(set);series={}
    for year in range(2022,2027):
        for arm in ('H-CURRENT','H-RECENT','H-MULTI'):
            floor=year if arm=='H-CURRENT' else max(2022,year-1) if arm=='H-RECENT' else 2022;by=collections.defaultdict(list)
            for r in rows:
                if floor<=r['season']<=year and r['values'][TARGET] is not None:
                    item=(r['available'],(r['game_id'],r['player_id']),r['values'][TARGET]);by[(r['position'],r['player_id'])].append(item);by[(r['position'],None)].append(item)
            series[(year,arm)]={k:empirical.Series(v) for k,v in by.items()}
    for q in queries['historical']:
        guard();r=lookup[(q['game_id'],q['player_id'])];actual=r['values'][TARGET];year=q['season']
        for arm in ('H-CURRENT','H-RECENT','H-MULTI'):
            own=series[(year,arm)].get((q['position'],q['player_id']));summary=own.at(r['kickoff']) if own else (0,None,None,None);fallback='none'
            if not summary[0]:
                pool=series[(year,arm)].get((q['position'],None));summary=pool.at(r['kickoff']) if pool else (0,None,None,None);fallback='position_empirical' if summary[0] else 'constant_zero'
            for product,i in [('mean',1),('lower_median',2)]:
                pred=summary[i]/50 if summary[0] else 0.;record=dict(q,run_id=VERSION+':empirical',family='empirical_chart_history_control',procedure_id=VERSION+':empirical',history_regime=arm,information_policy='ARM_LIMITED_TARGET_HISTORY',product_id=product,prediction=pred,actual=None if actual is None else actual/50,actual_grid=actual,actual_status=r['chart_status'],fallback=fallback,latest_training_label_available=summary[3],cutoff=r['kickoff'],status='FORECASTED',alias_strict_current='H-CURRENT' if arm=='H-CURRENT' else None)
                if reserved+len(empirical_rows)+1>protocol['budget']['max_forecast_rows']:raise RuntimeError('EMPIRICAL_FORECAST_BUDGET')
                empirical_rows.append(record)
                for season,wk,pos in [(str(year),'ALL','ALL'),(str(year),str(q['week']),'ALL'),(str(year),'ALL',q['position']),('POOLED_2022_2026','ALL','ALL')]:
                    key=(arm,product,season,wk,pos);egroups[key].add(pred,record['actual'],fallback,TARGET);efgames[key].add(q['game_id'])
                    if record['actual'] is not None:egames[key].add(q['game_id'])
    epacket=save(private_root/'empirical-chart-predictions.json.gz',dict(schema=VERSION,rows=empirical_rows,strict_current_alias='H-CURRENT exact, noadditionalfit'))
    for (arm,product,season,wk,pos),metrics in sorted(egroups.items()):
        result=metrics.result();result.update(unique_games=len(egames[(arm,product,season,wk,pos)]),forecast_games=len(efgames[(arm,product,season,wk,pos)]));empirical_scores.append(dict(procedure_id=VERSION+':empirical',procedure_family_id='empirical_history_control',target=TARGET,history_regime=arm,product_id=product,evaluation_panel_id='qualified-partial-chart-observed-participant-2022-2026-v1',population='primary',season=int(season) if season.isdigit() else season,period='REG',week=int(wk) if wk.isdigit() else wk,position=pos,fallback_view='ALL',record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',evidence='NEW_EXPERIMENT',n=result['scored_n'],forecast_rows=result['forecast_queries'],fallback_rows=result['fallback_n'],strict_current_alias='H-CURRENT exact, notadditionallearner',point_grid_denominator=50,**result))
    immutable_json(public_root/'EMPIRICAL_SCORES.json',empirical_scores);empirical.write_csv(public_root/'EMPIRICAL_SCORES.csv',empirical_scores)
    receipt=dict(version=VERSION,state=terminal,actual_completed_at=now(),protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),code_sha256=sha(__file__),chart_source_policy=chart_sources.POLICY_ID,source_counts=source_counts,chart_label_packet=label_packet,fit_opportunities=64,actual_fit_calls=fit_calls,retained_models=model_count,failed_fits=sum(r['state']=='FIT_FAILED_FALLBACK' for r in grid),completed_cells=len(grid),remaining_cells=64-len(grid),forecast_output_views=output_views,reserved_output_views=reserved,distribution_score_views=len(scores),empirical_score_views=len(empirical_scores),empirical_output_views=len(empirical_rows),empirical_prediction_packet=epacket,empirical_optimization_fits=0,chart_historical_query_cells=len(queries['historical']),chart_current_query_cells=protocol['current_2026_query_cells'],week8_query_cells=len(future),week8_output_views=len(future_records),week8_actuals_read=0,private_output_bytes=private_bytes,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2),new_scientific_families=0,scientific_limit='qualifiedpartialchartlabelpanel;positive/missingrarecreditsremainnull;retrospectiveparticipantpopulation;notcoherentcomponentjointmodelorfullrareeventreplay',official_capture=False,website_published=False)
    immutable_json(public_root/'RUN_RECEIPT.json',receipt);return receipt
