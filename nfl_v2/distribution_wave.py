"""Finite new source-matched Leaf-CDF and GLM-law reconstruction wave.

No acquisition or mutation of earlier runs. Statistics are loaded only by run().
"""
from __future__ import annotations
import collections,csv,gzip,hashlib,json,math,pickle,platform,resource,time,warnings
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import sklearn
from scipy import sparse
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.linear_model import PoissonRegressor,Ridge,LogisticRegression
from threadpoolctl import threadpool_limits
from . import hgb_control as source
from . import empirical_benchmark as empirical
from .distribution_laws import Law,prior

VERSION='v2-distribution-controls-reconstruction-v1'
FAMILIES=('ordered_leaf_cdf','regularized_glm_law')
POLICIES={'H-CURRENT-COMMON':('H-CURRENT',2026,2022),'H-RECENT-COMMON':('H-RECENT',2025,2022),'H-MULTI-COMMON':('H-MULTI',2022,2022),'H-CURRENT-STRICT':('H-CURRENT',2026,2026)}
FOREST=dict(n_estimators=32,criterion='squared_error',max_depth=8,min_samples_leaf=30,max_features=1.,bootstrap=False,random_state=1701,n_jobs=2)
GLM=dict(count_alpha=10.,signed_alpha=10.,binary_C=.1,max_iter=100,tol=1e-6)
TARGETS=source.TARGETS
canonical=source.canonical;sha=source.sha;now=source.now;immutable_json=source.immutable_json

def products(target):return ('event_probability',) if target=='anytime_td' else ('mean','lower_median')
def output_count(queries):return sum(len(products(q['target'])) for q in queries)*len(POLICIES)*len(FAMILIES)

def feature_history(rows,floor):return source.FeatureHistory([r for r in rows if r['season']>=floor])

class Design:
    def fit(self,x):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',RuntimeWarning);self.median=np.nanmedian(x,axis=0)
        self.median=np.where(np.isfinite(self.median),self.median,0.)
        raw=self.impute(x);self.mean=raw.mean(axis=0);self.scale=raw.std(axis=0);self.scale=np.where(self.scale>1e-12,self.scale,1.)
        return self
    def impute(self,x):return np.column_stack((np.where(np.isfinite(x),x,self.median),~np.isfinite(x))).astype(float)
    def transform(self,x,standardize=False):
        raw=self.impute(x);return (raw-self.mean)/self.scale if standardize else raw

class FittedLawModel:
    def __init__(self,family,target):self.family=family;self.target=target
    def fit(self,x,y,positions):
        self.design=Design().fit(x)
        if self.family=='ordered_leaf_cdf':
            self.estimator=ExtraTreesRegressor(**FOREST).fit(self.design.transform(x),y)
            ids=self.estimator.apply(self.design.transform(x));self.support,codes=np.unique(y,return_inverse=True);self.hist=[]
            for j,tree in enumerate(self.estimator.estimators_):
                h=sparse.coo_matrix((np.ones(len(y)),(ids[:,j],codes)),shape=(tree.tree_.node_count,len(self.support))).tocsr();tot=np.asarray(h.sum(axis=1)).ravel();inv=np.divide(1.,tot,out=np.zeros_like(tot),where=tot>0);self.hist.append(sparse.diags(inv)@h)
        elif self.target=='anytime_td':self.estimator=LogisticRegression(C=GLM['binary_C'],solver='lbfgs',max_iter=GLM['max_iter'],tol=GLM['tol'],random_state=1701).fit(self.design.transform(x,True),y)
        elif self.target in empirical.COUNTS:self.estimator=PoissonRegressor(alpha=GLM['count_alpha'],max_iter=GLM['max_iter'],tol=GLM['tol']).fit(self.design.transform(x,True),y)
        else:
            self.estimator=Ridge(alpha=GLM['signed_alpha']).fit(self.design.transform(x,True),y)
            residual=np.abs(y-np.rint(self.estimator.predict(self.design.transform(x,True))))
            global_scale=max(1.,float(residual.mean()));self.scale={}
            for p in source.POSITIONS:
                vals=residual[np.asarray(positions)==p];self.scale[p]=max(1.,float((10*global_scale+vals.sum())/(10+len(vals))))
        return self
    def predict(self,x,positions,priors):
        design=self.design.transform(x,self.family=='regularized_glm_law')
        if self.family=='ordered_leaf_cdf':
            leaf=self.estimator.apply(design);weights=np.zeros((len(x),len(self.support)))
            for j,h in enumerate(self.hist):weights+=h[leaf[:,j]].toarray()/len(self.hist)
            return [(Law('mixture',support=self.support,weights=w,prior=priors[p],mixture=.05),{'leaf_ids':l.tolist()}) for w,l,p in zip(weights,leaf,positions)]
        values=self.estimator.predict_proba(design)[:,list(self.estimator.classes_).index(1.)] if self.target=='anytime_td' else self.estimator.predict(design)
        out=[]
        for v,p in zip(values,positions):
            if not math.isfinite(float(v)):raise ValueError('nonfinite forecast')
            law=Law('bernoulli',p=float(v)) if self.target=='anytime_td' else Law('poisson',mean=float(v)) if self.target in empirical.COUNTS else Law('signed',center=int(np.rint(v)),q=self.scale[p]/(1+self.scale[p]))
            out.append((law,{'parametric':law.parameters()}))
        return out

class DistributionMetrics:
    def __init__(self):self.points=empirical.Metrics();self.crps=[];self.nll=[];self.widths=[];self.coverage=[];self.inf=0;self.zero=[];self.games=set();self.forecast_games=set();self.fallbacks=collections.Counter()
    def add(self,r):
        self.points.add(r['prediction'],r['actual'],r['fallback'],r['target']);self.forecast_games.add(r['game_id']);self.fallbacks[r['fallback']]+=1
        if r['actual'] is None:return
        self.games.add(r['game_id']);d=r['distribution_summary'];self.crps.append(d['crps']);self.zero.append(d['zero_mass']);self.widths.append(d['interval90_width']);self.coverage.append(d['interval90_covered']);self.inf+=d['infinite_nll']
        if not d['infinite_nll']:self.nll.append(d['nll'])
    def result(self):
        out=self.points.result();out.update(unique_games=len(self.games),forecast_games=len(self.forecast_games),CRPS=float(np.mean(self.crps)) if self.crps else None,NLL=None if self.inf or not self.nll else float(np.mean(self.nll)),infinite_NLL=self.inf,interval90_width=float(np.mean(self.widths)) if self.widths else None,interval90_coverage=float(np.mean(self.coverage)) if self.coverage else None,mean_zero_mass=float(np.mean(self.zero)) if self.zero else None,fallback_source_counts=dict(self.fallbacks));return out

def prepare(source_root,previous_queries,old_protocol,public_root,private_root,provenance):
    public_root,private_root=Path(public_root),Path(private_root);public_root.mkdir(parents=True,exist_ok=True);private_root.mkdir(parents=True,exist_ok=True)
    queries=json.loads(Path(previous_queries).read_text());instant=datetime.now(timezone.utc).timestamp()
    admitted=[q for q in queries['week8'] if source.utc(q['owner_input_cutoff_utc']).timestamp()>instant]
    excluded=[q for q in queries['week8'] if source.utc(q['owner_input_cutoff_utc']).timestamp()<=instant]
    immutable_json(private_root/'frozen-queries.json',dict(historical=queries['historical'],week8=admitted,closed_t90=excluded))
    roles=json.loads(Path(old_protocol).read_text())['source_role_contract']
    grid=[dict(week=w,target=t,family=f,policy_id=p,history_regime=POLICIES[p][0],state='REGISTERED') for w in (8,1,2,3,4,5,6,7) for t in TARGETS for p in POLICIES for f in FAMILIES]
    protocol=dict(version=VERSION,state='FROZEN_BEFORE_NEW_NUMERIC_FEATURES_AND_FITS',registered_at_utc=now(),code_sha256=sha(__file__),law_code_sha256=sha(Path(__file__).with_name('distribution_laws.py')),source_loader_sha256=sha(source.__file__),empirical_helper_sha256=sha(empirical.__file__),source_role_contract=roles,source_ids=json.loads(Path(old_protocol).read_text())['source_ids'],frozen_queries_sha256=sha(private_root/'frozen-queries.json'),prior_query_packet_sha256=sha(previous_queries),historical_membership_sha256=hashlib.sha256(canonical(queries['historical'])).hexdigest(),historical_query_cells=len(queries['historical']),week8_open_t90_query_cells=len(admitted),week8_closed_t90_query_cells=len(excluded),week8_open_games=len({q['game_id'] for q in admitted}),targets=list(TARGETS),chart='BLOCKED_EXACT_COMPONENT_RARE_EVENT_SOURCE_CONTRACT',families=list(FAMILIES),policies={k:dict(history_regime=a,fit_floor=b,feature_floor=c) for k,(a,b,c) in POLICIES.items()},feature_columns=list(source.FEATURES),features='same own target mean3/n3/mean8/n8 and last4 values/age/missing plus positiononehot; missing slots retained; gamequery refresh; no other source groups',weekly_refit='labels available strictly before earliest week kickoff; training feature lookup at own historical kickoff; Week8actualoriginonly; kickoff+7day availability assumption',forest=FOREST,glm=GLM,minimum_training_rows={'ordered_leaf_cdf':60,'regularized_glm_law':40},priors='same eligible fit-arm labels: role then global; geometric mean=max(.05,meanY),q=mu/(1+mu); signed center=lower median,scale=max(1,meanabsY-center),q=scale/(1+scale); binaryp=(sumY+1)/(n+2)',forest_law='equal tree leaf empirical PMFs, normalized within1e-10, 95%empirical+5%samearmroleprior; signed/count integer support preserved',glm_law='Poisson PMF with fitted log-link mean is explicit uncalibrated model assumption; signed rounded Ridge location plus discreteLaplace scale from training-only absolute residuals shrunk10pseudoobservations toward global residualscale,minimum1; Bernoulli logistic law',strict_contract='STRICT uses only2026NFL outcomes in labels, features, priors and transform fitting; no calibration/retrieval/playerencoding/pretrained models. Fixed architecture/parameters inherited from exposed research and not newly validated; current source identity/querymembership is retained, not pure current-vintage provenance.',cold_start='no model, no prior position, zero own featurehistory, allzero count or singleclass binary => samearmrole/global prior; no eligibleNFLlabels => pointmass0fornumeric and fixedBernoulli.5; include all fallback and learned-only overlap',tail_contract='exact infinite-support geometric/discreteLaplace formulas and scipy PoissonCDF/PPF; NLL uses direct logPMF/logaddexp, never continuous density, no clipping or tail truncation; true impossible pointmass events retain infiniteNLL; interval inclusive5/95quantiles',scoring='numeric MAEallmean/median views; meanMSE separate; legitimate laws CRPS+PMFNLL+90%coverage,width,zero mass; TD Brierprimary/logloss; signedyards retained',cohort='same15574current-vintage retrospective observedparticipant querycells; extendedrolesdisjoint; not full exante historicalpopulation; Week8samefrozenIDs only stillOPEN T90',new_source_access=False,information_comparison='Common memory arms isolate fitwindow; STRICT changes completeinformationpolicy versus commoncurrent; no universalhistorywinner',previous_exposure='Legacy and earlierV2empirical/HGB results already exposed; new reconstruction/version not original issuance',source_provenance=provenance,grid=grid,budget=dict(max_fit_calls=704,max_source_rows=200000,max_forecast_rows=2000000,wall_seconds=1200,cpu_seconds=1800,max_peak_memory_bytes=2147483648,max_private_bytes=536870912,max_threads=2,hyperparameter_searches=0),official_capture=False,website_published=False)
    immutable_json(public_root/'FROZEN_PROTOCOL.json',protocol);return protocol

def run(source_root,public_root,private_root):
    start,cpu=time.monotonic(),time.process_time();public_root,private_root=Path(public_root),Path(private_root)
    protocol_path=public_root/'FROZEN_PROTOCOL.json';protocol=json.loads(protocol_path.read_text())
    if protocol['version']!=VERSION or protocol['code_sha256']!=sha(__file__) or protocol['law_code_sha256']!=sha(Path(__file__).with_name('distribution_laws.py')) or protocol['source_loader_sha256']!=sha(source.__file__) or protocol['empirical_helper_sha256']!=sha(empirical.__file__):raise ValueError('frozen code changed')
    checks=json.loads((public_root/'SOFTWARE_CHECKS.json').read_text())
    if checks['state']!='PASS' or checks['wave_code_sha256']!=sha(__file__) or checks['law_code_sha256']!=sha(Path(__file__).with_name('distribution_laws.py')):raise ValueError('software checks not bound')
    for s in protocol['source_ids']:
        if sha(Path(source_root)/s['name'])!=s['sha256']:raise ValueError('source bytes changed')
    if sha(private_root/'frozen-queries.json')!=protocol['frozen_queries_sha256']:raise ValueError('query bytes changed')
    queries=json.loads((private_root/'frozen-queries.json').read_text());future_origin=datetime.now(timezone.utc).timestamp()
    if output_count(queries['historical']+queries['week8'])>protocol['budget']['max_forecast_rows']:raise RuntimeError('output preflight budget')
    immutable_json(public_root/'EXECUTION_REGISTRATION.json',dict(version=VERSION,actual_started_at=now(),actual_week8_feature_origin=datetime.fromtimestamp(future_origin,timezone.utc).isoformat(),protocol_sha256=sha(protocol_path),software_checks_sha256=sha(public_root/'SOFTWARE_CHECKS.json'),environment=dict(python=platform.python_version(),sklearn=sklearn.__version__,numpy=np.__version__),new_fits_before_registration=0))
    source_rows,games,source_counts=source.load_source(source_root,protocol);rowmap={(r['game_id'],r['player_id']):r for r in source_rows}
    histories={floor:feature_history(source_rows,floor) for floor in (2022,2026)};datasets={}
    for target in TARGETS:
        eligible=[r for r in source_rows if r['position'] in source.allowed_roles(protocol,target) and r['values'][target] is not None]
        for floor,history in histories.items():
            selected=[r for r in eligible if r['season']>=floor];x=[];maxima=[]
            for r in selected:
                f,m=history.get(r['player_id'],r['position'],target,r['kickoff']);x.append(f);maxima.append(m)
            datasets[(target,floor)]=(selected,np.asarray(x,dtype=float),np.asarray([r['values'][target] for r in selected]),maxima)
    historical=collections.defaultdict(list)
    for q in queries['historical']:
        r=rowmap[(q['game_id'],q['player_id'])]
        if r['position']!=q['position']:raise ValueError('historical binding')
        historical[int(q['week'])].append(dict(q,season=2026,week=int(q['week']),kickoff=r['kickoff'],cutoff=r['kickoff'],actual=r['values'][q['target']],blocked_reason=None))
    future=[dict(q,season=2026,week=8,population='original_pregame_feed',kickoff=source.utc(q['kickoff_utc']).timestamp(),cutoff=future_origin,actual=None) for q in queries['week8']]
    origins={w:min(g['kickoff'] for g in games.values() if g['season']==2026 and g['week']==w) for w in range(1,8)};origins[8]=future_origin
    for dirname in ('models','query-features','prediction-chunks'):(private_root/dirname).mkdir(exist_ok=True)
    private_bytes=sum(p.stat().st_size for p in private_root.rglob('*') if p.is_file());fit_calls=model_count=output_rows=0;failures=[];grid=[];fits=[];groups=collections.defaultdict(DistributionMetrics);future_records=[];states=collections.Counter();terminal='COMPLETE'
    def check():
        if time.monotonic()-start>protocol['budget']['wall_seconds']:raise RuntimeError('WALL_BUDGET')
        if time.process_time()-cpu>protocol['budget']['cpu_seconds']:raise RuntimeError('CPU_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>protocol['budget']['max_peak_memory_bytes']:raise RuntimeError('RSS_BUDGET')
        if private_bytes>protocol['budget']['max_private_bytes']-4194304:raise RuntimeError('PRIVATE_BYTES')
    def save(path,value,raw=False):
        nonlocal private_bytes
        body=value if raw else canonical(value);body=gzip.compress(body,mtime=0)
        if private_bytes+len(body)>protocol['budget']['max_private_bytes']-4194304:raise RuntimeError('PRIVATE_BYTES_BEFORE_WRITE')
        with path.open('xb') as f:f.write(body);f.flush();__import__('os').fsync(f.fileno())
        private_bytes+=len(body);return dict(artifact_id='ART-DIST-'+sha(path),bundle_name=path.relative_to(private_root).as_posix(),sha256=sha(path),bytes=len(body))
    with threadpool_limits(limits=2):
        try:
            for week in (8,1,2,3,4,5,6,7):
                origin=origins[week];population=future if week==8 else historical[week]
                for target in TARGETS:
                    for policy,(arm,fit_floor,feature_floor) in POLICIES.items():
                        check();qrows=[q for q in population if q['target']==target];features=[];maximum=[]
                        for q in qrows:
                            f,m=histories[feature_floor].get(q['player_id'],q['position'],target,q['cutoff']);features.append(f);maximum.append(m)
                        qx=np.asarray(features,dtype=float);rows,x,y,mx=datasets[(target,feature_floor)];indices=np.asarray([i for i,r in enumerate(rows) if r['season']>=fit_floor and r['available']<origin],dtype=int)
                        if any(mx[i] is not None and mx[i]>=rows[i]['kickoff'] for i in indices):raise AssertionError('training feature leakage')
                        trainy=y[indices];positions=[rows[i]['position'] for i in indices];priors={p:prior([rows[i]['values'][target] for i in indices if rows[i]['position']==p],target) for p in source.POSITIONS}
                        global_prior=prior(trainy,target)
                        prior_counts={p:sum(v==p for v in positions) for p in source.POSITIONS}
                        for p in source.POSITIONS:
                            if not any(x==p for x in positions):priors[p]=global_prior
                        feature_packet=save(private_root/'query-features'/f'W{week:02}-{target}-{policy}.json.gz',[dict(query=q,features=source.json_features(f),latest_feature_available=m) for q,f,m in zip(qrows,features,maximum)])
                        for family in FAMILIES:
                            check();slot=f'W{week:02}-{target}-{policy}-{family}';state='NO_FIT_INSUFFICIENT_TRAINING';model=None;packet=None
                            audit=dict(slot=slot,target=target,family=family,policy_id=policy,history_regime=arm,information_policy='STRICT-CURRENT' if feature_floor==2026 else 'COMMON-2022-MEMORY',training_n=len(indices),training_seasons=sorted({rows[i]['season'] for i in indices}),feature_floor=feature_floor,fit_cutoff_utc=datetime.fromtimestamp(origin,timezone.utc).isoformat(),latest_training_label_available=max((rows[i]['available'] for i in indices),default=None),latest_training_feature_available=max((mx[i] for i in indices if mx[i] is not None),default=None),training_membership_sha256=hashlib.sha256(canonical([(rows[i]['game_id'],rows[i]['player_id']) for i in indices])).hexdigest(),prior_parameters={p:v.parameters() for p,v in priors.items()},prior_position_sample_counts=prior_counts,global_prior_sample_count=len(indices),actual_fit_started_at=None,actual_fit_completed_at=None,query_features=feature_packet)
                            enough=len(indices)>=protocol['minimum_training_rows'][family]
                            if enough and target in empirical.COUNTS and np.all(trainy==0):state='NO_FIT_ALL_ZERO_COUNT'
                            elif enough and target=='anytime_td' and len(np.unique(trainy))<2:state='NO_FIT_SINGLE_CLASS_BINARY'
                            elif enough:
                                if fit_calls>=protocol['budget']['max_fit_calls']:raise RuntimeError('FIT_BUDGET')
                                fit_calls+=1;audit['actual_fit_started_at']=now()
                                try:
                                    model=FittedLawModel(family,target).fit(x[indices],trainy,positions);audit['actual_fit_completed_at']=now();packet=save(private_root/'models'/(slot+'.pickle.gz'),pickle.dumps(model,protocol=5),raw=True);model_count+=1;state='FITTED_RETAINED'
                                except Exception as exc:
                                    model=None;state='FIT_FAILED_FALLBACK';audit['actual_fit_completed_at']=now();failures.append(dict(slot=slot,type=type(exc).__name__,reason=str(exc)[:240]))
                            audit.update(state=state,model=packet);fits.append(audit);states[state]+=1;immutable_json(public_root/(slot+'-FIT.json'),audit)
                            need=len(qrows)*len(products(target))
                            if output_rows+need>protocol['budget']['max_forecast_rows']:raise RuntimeError('OUTPUT_BUDGET_BEFORE_INFERENCE')
                            output_rows+=need
                            predictions=model.predict(qx,[q['position'] for q in qrows],priors) if model is not None and len(qrows) else [(None,None)]*len(qrows)
                            generated=now();records=[]
                            for q,f,m,(law,detail) in zip(qrows,features,maximum,predictions):
                                reason=q['blocked_reason'];fallback='none'
                                if week==8 and datetime.now(timezone.utc).timestamp()>=source.utc(q['owner_input_cutoff_utc']).timestamp():reason=reason or 'T90_CLOSED_BEFORE_ISSUANCE'
                                if not reason:
                                    if model is None or f[3]<=0:
                                        fallback='fixed_no_NFL_startup' if not len(indices) else 'cold_start_role_prior' if f[3]<=0 else 'no_model_role_prior';law=priors[q['position']];detail={'fallback_prior':law.parameters()}
                                    summary=law.summary(q['actual'])
                                else:summary=None
                                for product in products(target):
                                    prediction=None if reason else summary['mean' if product=='event_probability' else product]
                                    record=dict(q,run_id=VERSION,family=family,procedure_id=VERSION+':'+family+':'+('strict-current-inputs' if feature_floor==2026 else 'common-feature-memory'),history_regime=arm,policy_id=policy,information_policy=audit['information_policy'],product_id=product,prediction=prediction,fallback=None if reason else fallback,fit_slot=slot,fit_state=state,latest_feature_available=m,distribution_summary=summary,law_reference=detail,fallback_source=None if reason or fallback=='none' else 'fixed_no_NFL_startup' if not len(indices) else 'same_arm_position_prior' if prior_counts[q['position']] else 'same_arm_global_prior',fallback_source_n=None if reason or fallback=='none' else prior_counts[q['position']] or len(indices),status='ABSTAIN' if reason else 'FORECASTED',abstention_reason=reason,actual_status='PENDING_FUTURE' if week==8 else 'PLAYED_MISSING' if q['actual'] is None else 'SUPPORTED_OFFICIAL_PHYSICAL_STAT',actual_generated_at=generated)
                                    if week==8:record.update(issued_at_utc=generated,actual_horizon_seconds=q['kickoff']-source.utc(generated).timestamp(),owner_cutoff_status='BEFORE_OWNER_INPUT_CUTOFF' if not reason else 'NOT_ISSUED')
                                    if m is not None and m>=q['cutoff']:raise AssertionError('query feature leakage')
                                    if prediction is not None and week!=8:
                                        for wk,pos,view in [('ALL','ALL','ALL'),(str(week),'ALL','ALL'),('ALL',q['position'],'ALL')]+([('ALL','ALL','LEARNED_ONLY')] if fallback=='none' else []):groups[(family,policy,target,q['population'],arm,product,wk,pos,view)].add(record)
                                    records.append(record)
                            prediction_packet=save(private_root/'prediction-chunks'/(slot+'.json.gz'),dict(schema=VERSION,rows=records));persisted=now()
                            deadline_pass=all(source.utc(persisted)<source.utc(r['owner_input_cutoff_utc']) for r in records if r['prediction'] is not None) if week==8 else None
                            if week==8 and not deadline_pass:raise RuntimeError('PERSISTENCE_DEADLINE_FAILED_PACKET_INVALID')
                            receipt=dict(slot=slot,packet=prediction_packet,actual_persistence_completed_at=persisted,output_views=len(records),issued=sum(r['prediction'] is not None for r in records),abstained=sum(r['prediction'] is None for r in records),all_before_T90_persistence=deadline_pass)
                            immutable_json(public_root/(slot+'-FORECAST.json'),receipt);grid.append(dict(slot=slot,state=state,forecast_receipt=receipt))
                            if week==8:future_records.extend(records)
                if week==8:
                    packet=save(private_root/'WEEK8_OPEN_T90_SHADOWS.json.gz',dict(schema=VERSION,rows=future_records))
                    immutable_json(public_root/'WEEK8_CAPTURE_RECEIPT.json',dict(version=VERSION,state='CAPTURED_OPEN_T90_GAMES_LOCAL_READBACK_OFFHOST_PENDING',packet=packet,actual_completed_at=now(),feature_origin_utc=datetime.fromtimestamp(future_origin,timezone.utc).isoformat(),output_views=len(future_records),issued=sum(r['prediction'] is not None for r in future_records),abstained=sum(r['prediction'] is None for r in future_records),query_cells=len(future),excluded_closed_T90_queries=protocol['week8_closed_t90_query_cells'],games=len({r['game_id'] for r in future_records}),actuals_read=0,new_fit_calls=fit_calls,official_capture=False,website_published=False))
        except Exception as exc:
            terminal='PARTIAL_STOPPED';failures.append(dict(type=type(exc).__name__,reason=str(exc)[:240]))
    scores=[]
    for (family,policy,target,population,arm,product,week,position,view),metrics in sorted(groups.items()):
        result=metrics.result();strict=POLICIES[policy][2]==2026
        scores.append(dict(procedure_id=VERSION+':'+family+':'+('strict-current-inputs' if strict else 'common-feature-memory'),procedure_family_id=family,target=target,history_regime=arm,information_policy='STRICT-CURRENT' if strict else 'COMMON-2022-MEMORY',policy_id=policy,product_id=product,evaluation_panel_id='distribution-controls-source-matched-observed-participant-2026-W1-W7-v1',population=population,season=2026,period='REG',week=int(week) if week.isdigit() else week,position=position,fallback_view=view,record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',evidence='NEW_EXPERIMENT',n=result['scored_n'],forecast_rows=result['forecast_queries'],fallback_rows=result['fallback_n'],feature_memory_policy='2026-only outcomes/features/priors/transforms; completeinformationpolicy comparison' if strict else 'common2022+ memory across3fittingarms; not purecurrentinformation',**result))
    immutable_json(public_root/'SCORES.json',scores)
    empirical.write_csv(public_root/'SCORES.csv',scores)
    completed={r['slot']:r['state'] for r in grid};full=[]
    for r in protocol['grid']:
        slot=f"W{r['week']:02}-{r['target']}-{r['policy_id']}-{r['family']}";full.append(dict(r,slot=slot,state=completed.get(slot,'NOT_RUN_AFTER_BOUNDED_STOP')))
    immutable_json(public_root/'GRID_STATUS.json',full);immutable_json(public_root/'FAILURES.json',failures)
    receipt=dict(version=VERSION,state=terminal,actual_completed_at=now(),protocol_sha256=sha(protocol_path),code_sha256=sha(__file__),law_code_sha256=sha(Path(__file__).with_name('distribution_laws.py')),source_counts=source_counts,fit_opportunities=len(full),actual_fit_calls=fit_calls,retained_models=model_count,failed_fits=sum(r['state']=='FIT_FAILED_FALLBACK' for r in fits),fit_state_counts=dict(states),completed_cells=len(grid),remaining_cells=len(full)-len(grid),forecast_output_views=output_rows,score_views=len(scores),week8_output_views=len(future_records),week8_actuals_read=0,historical_query_cells=protocol['historical_query_cells'],private_output_bytes=private_bytes,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2),chart='BLOCKED',new_family_count=2,official_capture=False,website_published=False,private_durability='LOCAL_IMMUTABLE_ARTIFACTS_OFFHOST_RESTORATION_SEPARATE')
    immutable_json(public_root/'RUN_RECEIPT.json',receipt);return receipt
