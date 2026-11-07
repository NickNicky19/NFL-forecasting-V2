"""Future-only strict-current-information adapter for original HGB controls.

This does not refit a 2026 historical evaluation or acquire new sources.
"""
import collections,csv,gzip,hashlib,io,json,math,os,pickle,platform,resource,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from . import hgb_control as s,empirical_benchmark as emp,availability_wave as availability
VERSION='v2-original-hgb-strict-current-future-only-v1'
sha=s.sha;now=s.now;write=s.immutable_json;canonical=s.canonical

class ResourceBudget(RuntimeError):pass

def complete_grid(fits,completed,attempted=None):
    audits={r['slot']:r for r in fits};attempted=attempted or {}
    return [dict(slot=target+'-'+objective,target=target,objective=objective,state=audits[target+'-'+objective]['state'] if target+'-'+objective in audits else attempted.get(target+'-'+objective,'NOT_RUN_AFTER_BOUNDED_STOP'),forecast_state='PERSISTED' if target+'-'+objective in completed else 'NOT_PERSISTED') for target in s.TARGETS for objective in s.objectives(target)]

def admitted(q):return not q.get('blocked_reason') and q.get('position') in s.POSITIONS
def output_views(queries):return sum(len(s.objectives(q['target'])) for q in queries)

def prepare(public,private,source_root,old_protocol,query_source):
    public,private=Path(public),Path(private)
    if public.exists() or private.exists():raise ValueError('new immutable outputs required')
    old=json.loads(Path(old_protocol).read_text());queries=[q for q in json.loads(Path(query_source).read_text()) if q['target'] in s.TARGETS];asof=now();instant=s.utc(asof).timestamp()
    if len(queries)!=1795 or len({q['game_id'] for q in queries})!=13:raise ValueError('same frozen thirteen-game football membership required')
    if any(q.get('actual') is not None or q['week']!=8 for q in queries):raise ValueError('future-pending queries only')
    for item in old['source_ids']:
        if sha(Path(source_root)/item['name'])!=item['sha256']:raise ValueError('source changed')
    public.mkdir(parents=True);private.mkdir(parents=True);write(private/'frozen-queries.json',queries);p=dict(version=VERSION,state='FROZEN_BEFORE_CURRENT_SOURCE_FEATURES_AND_FITS',registered_at_utc=now(),fixed_asof_utc=asof,code_sha256=sha(__file__),helper_sha256={Path(m.__file__).name:sha(m.__file__) for m in (s,emp,availability)},source_ids=old['source_ids'],source_role_contract=old['source_role_contract'],frozen_queries_sha256=sha(private/'frozen-queries.json'),source_query_sha256=sha(query_source),query_cells=len(queries),query_games=13,query_closed_at_registration=sum(not availability.open_query(q,instant) for q in queries),expected_output_views=output_views(queries),targets=list(s.TARGETS),history_regime='H-CURRENT',policy_id='H-CURRENT-STRICT',information_policy='2026-onlyoutcomes inlabels/features/priors/transforms; fixedhistoricallyselected/exposedarchitecture disclosed; no olderNFLfit/featurememory/calibration/retrieval/embedding/pretraining',availability='samefrozenfootballsource; kickoff+7daysSTRICTLYearlierthanrealasof fortraininglabels/queryhistory; trainfeatures atownkickoff withsame7dayrule; doNOTmixqualifiedfreshW7A/B/Cpolicy',recipe=dict(HGB=s.PARAMS,objectives='absolute_error_point andsquared_error_mean fornumeric;binaryloglossclassifier forrushing-or-receivingTD; pointobjective doesnotauthenticatecountlaw',minimum_rows=40,binary_requires_two_classes=True,fallback='2026-onlyearlierownempirical thenposition thenliteralzero onlyifmodelunavailable; originalHGBmissing-history inference retained'),procedure_id='hgb-direct-history-controls-v1:{objective}:strict-current-inputs',grading=dict(state='PENDING_CURRENT2026_WEEK8_LABELS',primary='MAEnumeric/BrierTD; intendedmeanMSEseparate; nativeprecision; no countdistributionclaim',membership='samefrozenallqueries/roles+pendingabstentions; DNP/playedzero/playedmissing/unknown separately qualified later; nofuturemethodselector',selection='NONE; nooffer/price/ROIrule'),ownership=dict(state='RESEARCH_SHADOW_OWNER_ADMISSION_PENDING',coordination='retainedownerchannel6513284161',official_capture=False,website_published=False),budget=dict(max_fit_calls=21,wall_seconds=600,cpu_seconds=900,max_peak_memory_bytes=2147483648,max_private_bytes=268435456,max_threads=2,max_forecast_rows=output_views(queries),max_source_rows=200000,hyperparameter_searches=0),new_family_count=0,actual2026_historical_refits=0,CURRENT_2026_Week8_outcomes_read=0)
    grading_parent=Path(__file__).resolve().parents[1]/'reports/continuation-20261030b/FUTURE_GRADING_SUBGROUP_FREEZE.json'
    parent=json.loads(grading_parent.read_text())
    p['comparison_limit']='Future-only purity adapter; real current label cutoff can differ from prior common-memory HGB snapshots; do not attribute any old/new packet difference solely to history policy or claim forecast skill before outcomes'
    p['grading'].update(parent_protocol_sha256=sha(grading_parent),membership_artifacts=parent['membership_artifacts'],extension='Same frozen common future cohorts and point/Brier rules; this pending-only strict policy adapter adds no law or outcome; all new views graded, no method selection')
    write(public/'FROZEN_PROTOCOL.json',p);return p

def run(public,private,source_root,verifier):
    public,private=Path(public),Path(private);p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());v=json.loads(Path(verifier).read_text());start,cpu=time.monotonic(),time.process_time()
    if v.get('state')!='PASS_STRICT_HGB_FUTURE_PREFIT_REVIEW' or v.get('protocol_sha256')!=sha(public/'FROZEN_PROTOCOL.json') or p['code_sha256']!=sha(__file__):raise ValueError('prefit/frozen gate')
    if sha(private/'frozen-queries.json')!=p['frozen_queries_sha256']:raise ValueError('query bytes changed')
    for name,h in p['helper_sha256'].items():
        if sha(Path(__file__).with_name(name))!=h:raise ValueError('helper changed')
    for item in p['source_ids']:
        if sha(Path(source_root)/item['name'])!=item['sha256']:raise ValueError('source changed')
    write(public/'EXECUTION_REGISTRATION.json',dict(actual_started_at=now(),fixed_asof_utc=p['fixed_asof_utc'],protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),independent_prefit_sha256=sha(verifier),new_fit_calls=0,sole_fit_worker=True,environment=dict(python=platform.python_version(),numpy=np.__version__)))
    allrows,games,counts=s.load_source(source_root,p);rows=[r for r in allrows if r['season']==2026];history=s.FeatureHistory(rows);asof=s.utc(p['fixed_asof_utc']).timestamp();queries=json.loads((private/'frozen-queries.json').read_text());out=[];fits=[];failures=[];calls=0;attempted={}
    for name in ('models','features','chunks'):(private/name).mkdir(exist_ok=True)
    private_bytes=sum(f.stat().st_size for f in private.rglob('*') if f.is_file())
    def guard():
        if time.monotonic()-start>p['budget']['wall_seconds'] or time.process_time()-cpu>p['budget']['cpu_seconds']:raise ResourceBudget('TIME_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>p['budget']['max_peak_memory_bytes']:raise ResourceBudget('RSS_BUDGET')
    def save(path,obj,raw=False):
        nonlocal private_bytes
        blob=gzip.compress(obj if raw else canonical(obj),mtime=0)
        if private_bytes+len(blob)>p['budget']['max_private_bytes']:raise ResourceBudget('PRIVATE_BUDGET_BEFORE_WRITE')
        with path.open('xb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
        private_bytes+=len(blob);return dict(artifact_id='STRICT-HGB-FUTURE-'+sha(path),bundle_name=path.relative_to(private).as_posix(),sha256=sha(path),bytes=len(blob))
    terminal='COMPLETE';completed=[]
    with threadpool_limits(limits=2):
      try:
       for target in s.TARGETS:
        guard();roles=s.allowed_roles(p,target);train=[r for r in rows if r['position'] in roles and r['values'][target] is not None and r['available']<asof];tx=[];tm=[]
        for r in train:
            x,m=history.get(r['player_id'],r['position'],target,r['kickoff']);tx.append(x);tm.append(m)
            if m is not None and m>=r['kickoff']:raise ValueError('strict train leakage')
        tx=np.asarray(tx);y=np.asarray([r['values'][target] for r in train]);qr=[q for q in queries if q['target']==target];fx=[];fm=[]
        for q in qr:
            x,m=history.get(q['player_id'],q['position'],target,asof);fx.append(x);fm.append(m)
            if m is not None and m>=asof:raise ValueError('strict query leakage')
        fx=np.asarray(fx);featurepacket=save(private/'features'/(target+'.json.gz'),[dict(query=q,features=s.json_features(x),latest_feature_available=m) for q,x,m in zip(qr,fx,fm)])
        for objective in s.objectives(target):
         guard();slot=target+'-'+objective;model=None;packet=None;state='NO_FIT_INSUFFICIENT_TRAINING';began=ended=None
         if len(y)>=40 and (target!='anytime_td' or len(np.unique(y))==2):
            if calls>=p['budget']['max_fit_calls']:raise RuntimeError('FIT_BUDGET')
            calls+=1;began=now();attempted[slot]='FIT_STARTED'
            try:model=s.make_estimator(target,objective).fit(tx,y);ended=now();guard();packet=save(private/'models'/(slot+'.pickle.gz'),pickle.dumps(model,protocol=5),True);state='FITTED_RETAINED'
            except ResourceBudget:attempted[slot]='FIT_RESOURCE_STOP_UNRETAINED';raise
            except Exception as exc:model=None;ended=now();state='FIT_FAILED_FALLBACK';failures.append(dict(slot=slot,type=type(exc).__name__,reason=str(exc)[:200]))
         elif len(y)>=40 and target=='anytime_td':state='NO_FIT_SINGLE_CLASS_BINARY'
         audit=dict(slot=slot,target=target,objective=objective,state=state,training_n=len(train),training_seasons=sorted({r['season'] for r in train}),training_membership_sha256=hashlib.sha256(canonical([(r['game_id'],r['player_id']) for r in train])).hexdigest(),latest_training_label_available=max((r['available'] for r in train),default=None),latest_training_feature_available=max((m for m in tm if m is not None),default=None),fit_cutoff_utc=p['fixed_asof_utc'],feature_floor=2026,model=packet,query_features=featurepacket,actual_fit_started_at=began,actual_fit_completed_at=ended);write(public/(slot+'-FIT.json'),audit);fits.append(audit)
         predicted=availability.infer_hgb(model,fx,qr,target);guard();generated=now();records=[]
         if len(out)+len(qr)>p['budget']['max_forecast_rows']:raise RuntimeError('FORECAST_BUDGET')
         for q,value,m in zip(qr,predicted,fm):
            reason=q.get('blocked_reason') or ('UNQUALIFIED_POSITION' if not admitted(q) else None);fallback='none';used=None
            if not reason:
                if model is not None:value=s.project_point(target,value)
                else:
                    summary=availability.pool_summary(rows,target,'H-CURRENT',asof,q['player_id'],q['position']);value=summary['lower_median' if objective=='absolute_error_point' else 'mean'];fallback='own_empirical' if summary['own_n'] else 'position_empirical' if summary['n'] else 'constant_zero';used=summary['n']
            records.append(dict(q,run_id=VERSION,procedure_id='hgb-direct-history-controls-v1:'+objective+':strict-current-inputs',family='HGB_DIRECT_HISTORY_CONTROL',history_regime='H-CURRENT',policy_id='H-CURRENT-STRICT',information_policy='STRICT-CURRENT',product_id=objective,prediction=None if reason else value,actual=None,actual_status='PENDING_FUTURE',fallback=None if reason else fallback,fallback_source_n=used,status='ABSTAIN' if reason else 'STAGED_RESEARCH_SHADOW',abstention_reason=reason,feature_cutoff_utc=p['fixed_asof_utc'],latest_feature_available=m,fit_state=state,fit_slot=slot,model_artifact_id=None if packet is None else packet['artifact_id'],actual_generated_at=generated,issued_at_utc=None if reason else generated,actual_horizon_seconds=None if reason else s.utc(q['kickoff_utc']).timestamp()-s.utc(generated).timestamp()))
         checked=datetime.now(timezone.utc).timestamp()
         for r in records:
            if not availability.open_query(r,checked):r.update(prediction=None,status='ABSTAIN',abstention_reason='T90_CLOSED_BEFORE_PERSISTENCE',issued_at_utc=None)
         guard();predpacket=save(private/'chunks'/(slot+'.json.gz'),dict(schema=VERSION,rows=records));persisted=now()
         if any(r['prediction'] is not None and not availability.open_query(r,s.utc(persisted).timestamp()) for r in records):raise RuntimeError('DEADLINE_CROSSED_DURING_PERSISTENCE_INVALID')
         write(public/(slot+'-FORECAST.json'),dict(slot=slot,packet=predpacket,actual_persistence_completed_at=persisted,output_views=len(records),all_issued_before_T90=True));out.extend(records);completed.append(slot);guard()
      except Exception as exc:terminal='PARTIAL_STOPPED';failures.append(dict(type=type(exc).__name__,reason=str(exc)[:200]))
    try:guard()
    except ResourceBudget as exc:terminal='PARTIAL_STOPPED';failures.append(dict(type=type(exc).__name__,reason=str(exc)))
    write(public/'GRID_STATUS.json',complete_grid(fits,completed,attempted))
    try:packet=save(private/'STAGED_SHADOWS.json.gz',dict(schema=VERSION,rows=out))
    except ResourceBudget as exc:packet=None;terminal='PARTIAL_STOPPED';failures.append(dict(type=type(exc).__name__,reason=str(exc)))
    receipt=dict(version=VERSION,state=terminal,actual_completed_at=now(),fixed_asof_utc=p['fixed_asof_utc'],packet=packet,protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),actual_fit_calls=calls,retained_models=sum(f['state']=='FITTED_RETAINED' for f in fits),failed_fits=sum(f['state']=='FIT_FAILED_FALLBACK' for f in fits),completed_cells=len(fits),remaining_cells=21-len(fits),output_views=len(out),issued=sum(r['prediction'] is not None for r in out),abstained=sum(r['prediction'] is None for r in out),query_cells=len(queries),query_games=13,source_counts=counts,private_output_bytes=private_bytes,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2),score_views=0,new_family_count=0,owner_state='RESEARCH_SHADOW_OWNER_ADMISSION_PENDING',official_capture=False,website_published=False,actual2026_historical_refits=0,CURRENT_2026_Week8_outcomes_read=0,failures=failures);write(public/'RUN_RECEIPT.json',receipt);return receipt
