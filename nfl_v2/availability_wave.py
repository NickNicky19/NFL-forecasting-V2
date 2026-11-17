"""Prospective availability A/B/C ablation using retained source bytes.

No acquisition, Week 8 labels, production write, or historical lag rewrite.
Existing model files are read-only; all new artifacts use exclusive writes.
"""
from __future__ import annotations
import collections,csv,gzip,hashlib,json,math,os,pickle,platform,resource,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits
from . import hgb_control as src, empirical_benchmark as emp, chart_wave as chart
from . import distribution_wave_v2 as dist
from .distribution_laws import Law,prior

VERSION='v2-availability-abc-shadow-v1'
CHART='nick-chart-ppr-v1'
TARGETS=src.TARGETS+(CHART,)
ARMS=src.ARMS
canonical=src.canonical;sha=src.sha;now=src.now;save_json=src.immutable_json

def fresh_rows(rows,captured,asof):
    """Only current W7 has proven snapshot availability; old origins unchanged."""
    if captured>=asof:raise ValueError('capture must precede query cutoff')
    out=[]
    for r in rows:
        if r['season']==2026 and r['week']>7:raise ValueError('Week8 source forbidden')
        if r['season']==2026 and r['week']==7:
            if r['kickoff']>=captured:raise ValueError('current label not pre-capture game')
            r=dict(r,available=min(r['available'],captured))
        out.append(r)
    return out

def open_query(q,persistence):
    return src.utc(q['owner_input_cutoff_utc']).timestamp()>persistence

def infer_hgb(model,x,queries,target):
    out=[None]*len(queries)
    good=[i for i,q in enumerate(queries) if not q.get('blocked_reason') and q.get('position') in src.POSITIONS]
    if model is not None and good:
        vals=model.predict_proba(x[good])[:,list(model.classes_).index(1.)] if target=='anytime_td' else model.predict(x[good])
        for i,v in zip(good,vals):out[i]=src.project_point(target,v)
    return out

def pool_summary(rows,target,arm,cutoff,player,position):
    values=[r for r in rows if r['season']>=src.fit_floor(arm) and r['available']<cutoff and r['position']==position and r['values'][target] is not None]
    own=[r for r in values if r['player_id']==player]
    selected=own or values
    y=sorted(r['values'][target] for r in selected)
    return dict(n=len(y),own_n=len(own),mean=sum(y)/len(y) if y else 0.,lower_median=y[(len(y)-1)//2] if y else 0.,fallback='none' if own else 'same_arm_position_empirical' if y else 'constant_zero',latest=max((r['available'] for r in selected),default=None))

def resolve_model(receipt,roots):
    item=receipt.get('model')
    if not item:return None
    member=item.get('bundle_name',item.get('name'))
    matches=[Path(root)/member for root in roots if (Path(root)/member).is_file() and sha(Path(root)/member)==item['sha256']]
    if not matches:raise ValueError('model bytes unavailable for bound receipt')
    return matches[0]

def prepare(public,private,source_root,old_public,private_roots,query_path,chart_query_path,receipts_path):
    public,private,source_root=Path(public),Path(private),Path(source_root)
    if (public/'FROZEN_PROTOCOL.json').exists() or private.exists():raise ValueError('new immutable run required')
    public.mkdir(parents=True,exist_ok=True);private.mkdir(parents=True)
    old_public=Path(old_public).resolve();hpub=old_public.parent.parent/'continuation-20261029'/'hgb-history-v1';cpub=old_public.parent/'chart-wave-v1'
    old=json.loads((old_public/'FROZEN_PROTOCOL.json').read_text());sources=old['source_ids']
    for s in sources:
        if sha(source_root/s['name'])!=s['sha256']:raise ValueError('source bytes changed')
    receipts=json.loads(Path(receipts_path).read_text());by={r['name']:r for r in receipts if r.get('status')=='RETRIEVED'}
    for s in sources:
        if by[s['name']]['sha256']!=s['sha256']:raise ValueError('capture source mismatch')
    asof=now();instant=src.utc(asof).timestamp();queries=json.loads(Path(query_path).read_text())['week8'];cq=json.loads(Path(chart_query_path).read_text())['week8']
    if len({q['game_id'] for q in queries})!=13:raise ValueError('expected prior13game panel')
    allq=[dict(q,query_id=hashlib.sha256(canonical(q)).hexdigest(),season=2026,week=8,population='frozen_original_feed' if q['target']!=CHART else 'frozen_feed_player_union',actual=None,actual_status='PENDING_FUTURE') for q in queries+cq]
    if len({(q['game_id'],q.get('player_id') or 'sleeper:'+str(q.get('sleeper_id')),q['target']) for q in allq})!=len(allq):raise ValueError('duplicate query')
    save_json(private/'frozen-queries.json',allq)
    bindings=[];private_bindings={}
    for t in TARGETS:
        for arm in ARMS:
            specs=[('ordered_leaf_cdf','law')]+([] if t==CHART else [('hgb_direct',o) for o in src.objectives(t)])
            for family,objective in specs:
                path=(cpub/f'W08-{arm}-COMMON-ordered_leaf_cdf-FIT.json') if t==CHART else (old_public/f'W08-{t}-{arm}-COMMON-ordered_leaf_cdf-FIT.json') if family=='ordered_leaf_cdf' else (hpub/f'W08-{t}-{arm}-{objective}-FIT.json')
                r=json.loads(path.read_text());model=resolve_model(r,private_roots);key=t+':'+arm+':'+family+':'+objective
                b=dict(key=key,target=t,history_regime=arm,family=family,objective=objective,receipt_artifact=path.relative_to(Path(__file__).resolve().parents[1]).as_posix(),receipt_sha256=sha(path),model_sha256=None if model is None else sha(model),model_artifact_id=None if model is None else 'MODEL-'+sha(model),original_fit_cutoff_utc=r['fit_cutoff_utc'],original_training_n=r['training_n'],original_training_membership_sha256=r['training_membership_sha256'])
                bindings.append(b);private_bindings[key]=dict(model_path=None if model is None else str(model),receipt_path=str(path))
    save_json(public/'FIXED_MODEL_BINDINGS.json',bindings);save_json(private/'FIXED_MODEL_BINDINGS_PRIVATE.json',private_bindings)
    protocol=dict(version=VERSION,state='FROZEN_BEFORE_FEATURE_REBUILD_INFERENCE_AND_REFIT',registered_at_utc=now(),fixed_feature_origin_utc=asof,code_sha256=sha(__file__),helper_code_sha256={p.name:sha(p) for p in (Path(src.__file__),Path(dist.__file__),Path(chart.__file__),Path(emp.__file__),Path(__file__).with_name('distribution_laws.py'),Path(__file__).with_name('chart_sources.py'))},source_ids=sources,source_role_contract=old['source_role_contract'],source_capture_receipts_sha256=sha(receipts_path),source_capture_upper_bounds=[dict(name=s['name'],sha256=s['sha256'],known_available_by_utc=by[s['name']]['retrieved_utc']) for s in sources],qualified_2026_source_available_by=by['stats_player_week_2026.csv']['retrieved_utc'],frozen_queries_sha256=sha(private/'frozen-queries.json'),fixed_model_manifest_sha256=sha(public/'FIXED_MODEL_BINDINGS.json'),query_cells=len(allq),football_query_cells=len(queries),chart_query_cells=len(cq),games=len({q['game_id'] for q in allq}),queries_closed_at_registration=sum(not open_query(q,instant) for q in allq),targets=list(TARGETS),history_regimes=list(ARMS),arms=dict(A='retained fixed models/priors/fallbackroute; conservative seven-day query features refreshed at common new actual asof',B='same exact model bytes, priors and fallbackroute as A; only qualified current W7 own-query history refreshed',C='same qualified fresh query features as B; separately fitted models admit qualified retained W7 labels; historical training-feature clocks stay ownkickoff with conservative seven-day availability'),fixed_AB='every perquery fallback decision/value/prior fixed across A/B; Leaf own-history coldstart route fixed from A; HGB no-model fallback fixed; empirical coldstart route/prior fixed from A',empirical_C='0 optimizer fits; same fresh own history as B, fresh same-arm fallback pool/routing; separately disclose arithmetic label-pool update',training_feature_contract='all C train features from OLD seven-day source at each own historical kickoff; no globally shortened lag; common2022+memory across fitwindows; current-season fitting not pure current-only',models=dict(leaf=dist.FOREST,hgb=src.PARAMS,leaf_law='95%empiricalequal-tree leafPMF+5%samearm roleprior; exact discrete law and fullsupport rules inherited',chart='exact16qualifiedcomponents,grid50;signeddirectlaw;positive/missingrareaggregatesremainmissing',chart_hgb='NOT_APPLICABLE_NO_RETAINED_CHART_HGB; not padding a new model mechanism'),grading=dict(state='NO_LABELS_PENDING',numeric_primary='MAE, every valid output functional retained',mean_secondary='MSE/RMSE',TD_primary='Brier',law='CRPS/PMFNLL/90%intervals with original exact law semantics; chart in0.02grid',precision='chart medians use exact integer-grid tolerances; means unrounded',population='all same frozen exante queryIDs, blocked/DNP/played-zero/played-missing preserved; no future selection; allrows+position+sharedadmitted intersections',selection='NONE; no offeredline/price/ROI claims; grade paired B-A and C-B only on identical final supported labels',future_truth='no Week8 stat/outcome values decoded; final qualified snapshots required later'),ownership=dict(state='RESEARCH_SHADOW_OWNER_ADMISSION_PENDING',authority='direct V2 research snapshot/shadow authorization; retained owner coordination delivered via comment6513284161',official_capture=False,website_published=False),old_source_availability=dict(position_qualified_W7_rows=303,old23h16_7day_excluded=303,prior00h27_7day_excluded=282,not_historical_publication_reconstruction=True),budget=dict(max_fit_calls=99,wall_seconds=900,cpu_seconds=1200,max_threads=2,max_peak_memory_bytes=2147483648,max_private_bytes=536870912,max_forecast_rows=100000,max_source_rows=200000,hyperparameter_searches=0),new_scientific_families=0)
    save_json(public/'FROZEN_PROTOCOL.json',protocol)
    return protocol

def run(source_root,public,private,refits=False):
    public,private=Path(public),Path(private);protocol=json.loads((public/'FROZEN_PROTOCOL.json').read_text());asof=src.utc(protocol['fixed_feature_origin_utc']).timestamp();captured=src.utc(protocol['qualified_2026_source_available_by']).timestamp()
    if sha(__file__)!=protocol['code_sha256'] or sha(private/'frozen-queries.json')!=protocol['frozen_queries_sha256'] or sha(public/'FIXED_MODEL_BINDINGS.json')!=protocol['fixed_model_manifest_sha256']:raise ValueError('frozen binding changed')
    for name,h in protocol['helper_code_sha256'].items():
        if sha(Path(__file__).with_name(name))!=h:raise ValueError('helper changed')
    for s in protocol['source_ids']:
        if sha(Path(source_root)/s['name'])!=s['sha256']:raise ValueError('source changed')
    if json.loads((public/'SOFTWARE_CHECKS.json').read_text())['code_sha256']!=sha(__file__):raise ValueError('fixture binding')
    stage='C' if refits else 'AB';start,cpu=time.monotonic(),time.process_time();outputs=[];changes=[];fits=[];failures=[];calls=0
    save_json(public/(stage+'-EXECUTION_REGISTRATION.json'),dict(actual_started_at=now(),fixed_asof_utc=protocol['fixed_feature_origin_utc'],protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),new_fit_calls_before_registration=0,stage=stage,environment=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__)))
    old,games,counts,chart_labels,chart_coverage=chart.load_chart_source(source_root,protocol);fresh=fresh_rows(old,captured,asof);histA=src.FeatureHistory(old);histB=src.FeatureHistory(fresh);queries=json.loads((private/'frozen-queries.json').read_text());bindings=json.loads((public/'FIXED_MODEL_BINDINGS.json').read_text());local=json.loads((private/'FIXED_MODEL_BINDINGS_PRIVATE.json').read_text());freshlookup={(r['game_id'],r['player_id']):r for r in fresh};pool_cache={}
    def summary(mode,t,arm,cutoff,player,position):
        key=(mode,t,arm,cutoff)
        if key not in pool_cache:
            groups=collections.defaultdict(list)
            for r in fresh if mode=='fresh' else old:
                if r['season']>=src.fit_floor(arm) and r['available']<cutoff and r['values'][t] is not None:
                    item=(r['available'],(r['game_id'],r['player_id']),r['values'][t]);groups[(r['position'],r['player_id'])].append(item);groups[(r['position'],None)].append(item)
            pool_cache[key]={k:emp.Series(v).at(cutoff) for k,v in groups.items()}
        groups=pool_cache[key];own=groups.get((position,player),(0,None,None,None));used=own if own[0] else groups.get((position,None),(0,None,None,None))
        return dict(n=used[0],own_n=own[0],mean=used[1] if used[0] else 0.,lower_median=used[2] if used[0] else 0.,fallback='none' if own[0] else 'same_arm_position_empirical' if used[0] else 'constant_zero',latest=used[3])
    def guard():
        if time.monotonic()-start>protocol['budget']['wall_seconds'] or time.process_time()-cpu>protocol['budget']['cpu_seconds']:raise RuntimeError('TIME_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>protocol['budget']['max_peak_memory_bytes']:raise RuntimeError('RSS_BUDGET')
        if sum(p.stat().st_size for p in private.rglob('*') if p.is_file())>protocol['budget']['max_private_bytes']-4194304:raise RuntimeError('PRIVATE_BUDGET')
        if len(outputs)>protocol['budget']['max_forecast_rows']:raise RuntimeError('FORECAST_BUDGET')
    def save_packet(path,obj,raw=False):
        body=gzip.compress(obj if raw else canonical(obj),mtime=0)
        if sum(p.stat().st_size for p in private.rglob('*') if p.is_file())+len(body)>protocol['budget']['max_private_bytes']:raise RuntimeError('PRIVATE_BUDGET_BEFORE_WRITE')
        with path.open('xb') as f:f.write(body);f.flush();os.fsync(f.fileno())
        if gzip.decompress(path.read_bytes())!=(obj if raw else canonical(obj)):raise ValueError('localreadback')
        return dict(artifact_id='AVAIL-'+sha(path),bundle_name=path.relative_to(private).as_posix(),sha256=sha(path),bytes=len(body))
    for d in ('models','features','chunks'):(private/d).mkdir(exist_ok=True)
    datasets={};qdata={}
    for t in TARGETS:
        guard();qr=[q for q in queries if q['target']==t];fa=[];fb=[];ma=[];mb=[]
        for q in qr:
            a,m=histA.get(q['player_id'],q['position'],t,asof);b,n=histB.get(q['player_id'],q['position'],t,asof);fa.append(a);fb.append(b);ma.append(m);mb.append(n)
            if m is not None and m>=asof or n is not None and n>=asof:raise AssertionError('query chronology')
            if not refits:changes.append(dict(query_id=q['query_id'],target=t,game_id=q['game_id'],player_id=q['player_id'],A_features=src.json_features(a),B_features=src.json_features(b),changed_columns=[c for c,x,y in zip(src.FEATURES,src.json_features(a),src.json_features(b)) if x!=y],A_max_available=m,B_max_available=n))
        qdata[t]=(qr,np.asarray(fa),np.asarray(fb),ma,mb)
        if refits:
            eligible=[r for r in old if r['position'] in (set(src.POSITIONS) if t==CHART else src.allowed_roles(protocol,t)) and r['values'][t] is not None];tx=[];tm=[]
            for r in eligible:
                x,m=histA.get(r['player_id'],r['position'],t,r['kickoff']);tx.append(x);tm.append(m)
                if m is not None and m>=r['kickoff']:raise AssertionError('training feature chronology')
            datasets[t]=(eligible,np.asarray(tx),np.asarray([r['values'][t] for r in eligible]),tm)
    if not refits:save_packet(private/'features'/'QUERY_FEATURE_CHANGES.json.gz',changes)
    terminal='COMPLETE'
    with threadpool_limits(limits=2):
      try:
        for t in TARGETS:
          qr,xa,xb,ma,mb=qdata[t];scale=50 if t==CHART else 1
          for arm in ARMS:
            guard()
            # Arithmetic control separates own-history update from frozen fallback.
            for q in qr:
                sa=summary('old',t,arm,asof,q['player_id'],q['position']);sb=summary('fresh',t,arm,asof,q['player_id'],q['position']);sb=sb if sa['own_n'] else sa
                for label,s in ([('C',summary('fresh',t,arm,asof,q['player_id'],q['position']))] if refits else [('A',sa),('B',sb)]):
                    for product in dist.products(t):
                        key='mean' if product=='event_probability' else product;reason=q.get('blocked_reason') or ('UNQUALIFIED_POSITION' if q.get('position') not in src.POSITIONS else None)
                        outputs.append(dict(q,availability_arm=label,run_id=VERSION,family='empirical_history_control',procedure_id=VERSION+':empirical',history_regime=arm,product_id=product,prediction=None if reason else s[key]/scale,fallback=None if reason else s['fallback'],fallback_n=None if reason else s['n'],status='ABSTAIN' if reason else 'STAGED_RESEARCH_SHADOW',abstention_reason=reason,feature_cutoff_utc=protocol['fixed_feature_origin_utc'],actual_generated_at=now(),actual=None,actual_status='PENDING_FUTURE',new_fit=False))
            for binding in [b for b in bindings if b['target']==t and b['history_regime']==arm]:
                guard();key=binding['key'];r=json.loads(Path(local[key]['receipt_path']).read_text())
                if sha(local[key]['receipt_path'])!=binding['receipt_sha256']:raise ValueError('fixed receipt changed')
                model=None;fitmeta=None;priors=None;training_n=r['training_n'];fixed_cutoff=src.utc(binding['original_fit_cutoff_utc']).timestamp()
                if refits:
                    train,tx,ty,tm=datasets[t];idx=np.asarray([i for i,v in enumerate(train) if v['season']>=src.fit_floor(arm) and freshlookup[(v['game_id'],v['player_id'])]['available']<asof],dtype=int);positions=[train[i]['position'] for i in idx];training_n=len(idx)
                    if any(train[i]['season']==2026 and train[i]['week']>7 for i in idx):raise AssertionError('future train label')
                    minimum=60 if binding['family']=='ordered_leaf_cdf' else 40;fitstate='NO_FIT_INSUFFICIENT_TRAINING';started=None;completed=None;artifact=None
                    if len(idx)>=minimum and (t!='anytime_td' or len(np.unique(ty[idx]))==2):
                        guard()
                        if calls>=protocol['budget']['max_fit_calls']:raise RuntimeError('FIT_BUDGET')
                        calls+=1;started=now()
                        try:
                            model=(chart.ChartModel('ordered_leaf_cdf',t) if t==CHART else dist.FittedLawModel('ordered_leaf_cdf',t)) if binding['family']=='ordered_leaf_cdf' else src.make_estimator(t,binding['objective']);model.fit(tx[idx],ty[idx],positions) if binding['family']=='ordered_leaf_cdf' else model.fit(tx[idx],ty[idx]);completed=now();fitstate='FITTED_RETAINED';artifact=save_packet(private/'models'/(hashlib.sha256(key.encode()).hexdigest()+'.pickle.gz'),pickle.dumps(model,protocol=5),raw=True)
                        except Exception as exc:model=None;completed=now();fitstate='FIT_FAILED_FALLBACK';failures.append(dict(key=key,type=type(exc).__name__,reason=str(exc)[:240]))
                    fitmeta=dict(key=key,state=fitstate,training_n=len(idx),training_membership_sha256=hashlib.sha256(canonical([(train[i]['game_id'],train[i]['player_id']) for i in idx])).hexdigest(),newly_admitted_W7_n=sum(train[i]['season']==2026 and train[i]['week']==7 and train[i]['available']>=fixed_cutoff for i in idx),latest_training_feature_available=max((tm[i] for i in idx if tm[i] is not None),default=None),fit_cutoff_utc=protocol['fixed_feature_origin_utc'],historical_feature_rule='UNCHANGED_CONSERVATIVE_7DAY',actual_fit_started_at=started,actual_fit_completed_at=completed,model=artifact)
                    fits.append(fitmeta);save_json(public/('C-FIT-'+hashlib.sha256(key.encode()).hexdigest()+'.json'),fitmeta)
                    prior_rows=[train[i] for i in idx];prior_cutoff=asof
                else:
                    path=local[key]['model_path']
                    if path:
                        if sha(path)!=binding['model_sha256']:raise ValueError('fixed model changed')
                        model=pickle.loads(gzip.decompress(Path(path).read_bytes()))
                    prior_rows=[v for v in old if v['season']>=src.fit_floor(arm) and v['available']<fixed_cutoff and v['values'][t] is not None and v['position'] in (set(src.POSITIONS) if t==CHART else src.allowed_roles(protocol,t))];prior_cutoff=fixed_cutoff
                if binding['family']=='ordered_leaf_cdf':
                    if refits:
                        overall=(chart.chart_prior if t==CHART else lambda y:prior(y,t))([v['values'][t] for v in prior_rows]);priors={p:(chart.chart_prior if t==CHART else lambda y:prior(y,t))([v['values'][t] for v in prior_rows if v['position']==p]) if any(v['position']==p for v in prior_rows) else overall for p in src.POSITIONS}
                    else:priors={p:Law(**params) for p,params in r['prior_parameters'].items()}
                for label,x,mx in ([('C',xb,mb)] if refits else [('A',xa,ma),('B',xb,mb)]):
                    predicted=dist.predict_admitted(model,x,qr,priors) if binding['family']=='ordered_leaf_cdf' else infer_hgb(model,x,qr,t)
                    for i,q in enumerate(qr):
                        reason=q.get('blocked_reason') or ('UNQUALIFIED_POSITION' if q.get('position') not in src.POSITIONS else None);fallback='none';d=None
                        if not reason and binding['family']=='ordered_leaf_cdf':
                            law,detail=predicted[i]
                            if model is None or (xb if refits else xa)[i,3]<=0:law=priors[q['position']];detail=dict(fallback_prior=law.parameters());fallback='fixed_role_prior' if not refits else 'refit_role_prior'
                            d=chart.chart_summary(law,None) if t==CHART else law.summary(None);products=dist.products(t)
                        else:products=('event_probability',) if t=='anytime_td' else ('mean',) if binding['objective']=='squared_error_mean' else ('absolute_error_point',)
                        for product in products:
                            value=None
                            if not reason:
                                if binding['family']=='ordered_leaf_cdf':value=d['mean' if product=='event_probability' else product]
                                elif model is not None:value=predicted[i]
                                else:
                                    s=summary('fresh' if refits else 'old',t,arm,prior_cutoff,q['player_id'],q['position']);value=s['lower_median' if product=='absolute_error_point' else 'mean']/scale;fallback=s['fallback']
                            outputs.append(dict(q,availability_arm=label,run_id=VERSION,family=binding['family'],procedure_id=VERSION+':'+binding['family']+':'+binding['objective'],history_regime=arm,product_id=product,prediction=value,fallback=None if reason else fallback,status='ABSTAIN' if reason else 'STAGED_RESEARCH_SHADOW',abstention_reason=reason,feature_cutoff_utc=protocol['fixed_feature_origin_utc'],latest_feature_available=mx[i],actual_generated_at=now(),actual=None,actual_status='PENDING_FUTURE',distribution_summary=None if reason else d,fixed_model_artifact_id=binding['model_artifact_id'] if not refits else None,new_fit=refits,fit_binding=key,fit_state=None if fitmeta is None else fitmeta['state']))
          guard()
      except Exception as exc:terminal='PARTIAL_STOPPED';failures.append(dict(type=type(exc).__name__,reason=str(exc)[:300]))
    # Final deadline status applies equally to all A/B/C counterparts; no backdate.
    persisted_check=datetime.now(timezone.utc).timestamp()
    for row in outputs:
        if not open_query(row,persisted_check):row.update(prediction=None,status='ABSTAIN',abstention_reason='T90_CLOSED_BEFORE_PERSISTENCE',distribution_summary=None)
    packet=save_packet(private/(stage+'-STAGED_SHADOWS.json.gz'),dict(schema=VERSION,rows=outputs));persisted=now()
    if any(row['prediction'] is not None and not open_query(row,src.utc(persisted).timestamp()) for row in outputs):raise RuntimeError('DEADLINE_CROSSED_DURING_PERSISTENCE_INVALID_PACKET')
    receipt=dict(version=VERSION,stage=stage,state=terminal,owner_state='RESEARCH_SHADOW_OWNER_ADMISSION_PENDING',actual_completed_at=now(),actual_persistence_completed_at=persisted,fixed_asof_utc=protocol['fixed_feature_origin_utc'],packet=packet,protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),output_views=len(outputs),issued=sum(v['prediction'] is not None for v in outputs),abstained=sum(v['prediction'] is None for v in outputs),query_cells=len(queries),games=len({q['game_id'] for q in queries}),actual_fit_calls=calls,retained_models=sum(v['state']=='FITTED_RETAINED' for v in fits),failed_fits=sum(v['state']=='FIT_FAILED_FALLBACK' for v in fits),actual_Week8_outcomes_read=0,score_views=0,official_capture=False,website_published=False,source_counts=counts,current_W7_position_rows=sum(r['season']==2026 and r['week']==7 for r in old),W7_rows_excluded_A=sum(r['season']==2026 and r['week']==7 and r['available']>=asof for r in old),W7_rows_excluded_B=sum(r['season']==2026 and r['week']==7 and r['available']>=asof for r in fresh),resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2),failures=failures)
    save_json(public/(stage+'-RUN_RECEIPT.json'),receipt);return receipt
