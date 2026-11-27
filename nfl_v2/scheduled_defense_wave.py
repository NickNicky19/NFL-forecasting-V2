"""Prepared selective-refit scheduled-window experiment; never self-authorizes.

Old observed-group code/artifacts are immutable. Execution requires independent
prefit review, a fresh root restoration PASS and a separate root worker release.
There is no acquisition, recurring capture, production write or Week8 grading.
"""
from __future__ import annotations
import collections, gzip, hashlib, json, math, os, pickle, resource, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from . import qualified_defense_wave as old_wave, scheduled_defense as scheduled
from . import scheduled_defense_audit as audit, qualified_defense_inputs as inputs
from . import hgb_control as src, distribution_wave_v2 as learner, chart_wave as chart
from . import ordered_information_ablation as recipe, shared_subgroups as subgroup
from . import distribution_laws, precision_grid, scoring
from . import expanded_retention_gate as retention

VERSION='v2-scheduled-team-game-defense-alternative-v3'
TARGETS=recipe.TARGETS;POLICIES=learner.POLICIES;GROUPS=inputs.GROUPS;FAMILY='ordered_leaf_cdf'
sha=src.sha;canonical=src.canonical;now=src.now;write=src.immutable_json
class ResourceBudget(RuntimeError):pass

def load(path):return json.loads(Path(path).read_bytes())
def proc(group,policy):return VERSION+':'+group+(':strict-current-inputs'if POLICIES[policy][2]==2026 else':common-feature-memory')
def modules():return(old_wave,scheduled,audit,inputs,src,src.empirical,learner,chart,recipe,subgroup,distribution_laws,precision_grid,scoring,retention)
def identity(q):return tuple(q[k]for k in('game_id','player_id','target','population'))

def array_digest(values):
    a=np.asarray(values,dtype='<f8');a=np.where(np.isfinite(a),a,np.nan).astype('<f8')
    return hashlib.sha256(canonical(list(a.shape))+a.tobytes(order='C')).hexdigest()

def member(root,metadata):
    name=metadata.get('bundle_name')or metadata.get('name')
    if not name or Path(name).is_absolute()or'..'in Path(name).parts:raise ValueError('safe retained bundle member required')
    root=Path(root).resolve();path=(root/name).resolve()
    if not path.is_relative_to(root)or sha(path)!=metadata['sha256']:raise ValueError('retained artifact hash/root mismatch')
    return path

def action(old_state,changed):
    if old_state.startswith('NO_FIT_'):
        return 'REUSE_DECLARED_NO_MODEL_PRIOR'
    if old_state!='FITTED_RETAINED':raise ValueError('old failed or unknown state needs separate continuation')
    return 'REFIT_AFFECTED_TRAINING'if changed else'REUSE_UNCHANGED_TRAINING_MODEL'

def gates(protocol,*,restoration_gate,worker_release,review,software,phase):
    """Root alone creates factual restoration/release receipts; no fallback grant."""
    r=retention.require_retention(restoration_gate,Path(__file__).resolve().parents[1]);w=load(worker_release);v=load(review);s=load(software)
    restored=src.utc(r['completed_at_utc'])
    if restored>datetime.now(timezone.utc):raise ValueError('restoration completion cannot be in the future')
    if not(w.get('worker_release')is True and w.get('protocol_sha256')==protocol['protocol_sha256']and w.get('restoration_gate_sha256')==sha(restoration_gate)
           and w.get('max_new_fits')==308 and phase in w.get('phases',[])):raise ValueError('root separate exact-protocol sole fit-worker release required')
    if not w.get('released_at_utc')or not restored<=src.utc(w['released_at_utc'])<=datetime.now(timezone.utc):raise ValueError('actual worker release clock after restoration required')
    if v.get('state')!='PASS_PREFIT_PROTOCOL_REVIEW'or v.get('protocol_sha256')!=protocol['protocol_sha256']:raise ValueError('independent sealed prefit review required')
    if s.get('status')!='PASS'or s.get('code_sha256')!=sha(__file__):raise ValueError('exact-code software tests required')
    return dict(restoration_gate_sha256=sha(restoration_gate),worker_release_sha256=sha(worker_release),prefit_review_sha256=sha(review))

def fallback_contribution(rows,target):
    scored=[r for r in rows if r['actual']is not None and r['prediction']is not None]
    fb=[r for r in scored if r['fallback']!='none'];learn=[r for r in scored if r['fallback']=='none'];n=len(scored)
    loss=lambda r:(r['prediction']-r['actual'])**2 if target=='anytime_td'else abs(r['prediction']-r['actual'])
    f=math.fsum(loss(r)for r in fb);l=math.fsum(loss(r)for r in learn)
    return dict(metric='brier'if target=='anytime_td'else'mae',full_n=n,fallback_n=len(fb),learned_n=len(learn),fallback_loss_sum=f,learned_loss_sum=l,fallback_contribution=f/n if n else None,learned_contribution=l/n if n else None)

def prepare(*,manifest,public_root,private_root):
    """Only metadata/hash retention and a new actual future cutoff; zero fits."""
    m=load(manifest);pub,priv=Path(public_root),Path(private_root)
    if pub.exists()or priv.exists():raise ValueError('fresh immutable outputs required')
    if priv.resolve().is_relative_to(Path(__file__).resolve().parents[1]):raise ValueError('private inputs outside publicGit required')
    original=Path(m['original_public']);oldpriv=Path(m['original_private']);ap=Path(m['audit_public']);p=load(original/'FROZEN_PROTOCOL.json')
    ar=load(ap/'AUDIT_RECEIPT.json');changes=load(ap/'ORIGINAL_FIT_TRAINING_FEATURE_CHANGES.json')
    if ar['state']!='COMPLETE_NO_FIT_SOURCE_FEATURE_AUDIT'or ar['protocol_sha256']!=sha(ap/'FROZEN_PROTOCOL.json'):raise ValueError('sealed source-feature audit required')
    for mod in audit.modules():
        if load(ap/'FROZEN_PROTOCOL.json')['helper_sha256'][Path(mod.__file__).name]!=sha(mod.__file__):raise ValueError('audited helper changed')
    for s in p['source_ids']:
        if sha(Path(m['source_root'])/s['name'])!=s['sha256']:raise ValueError('qualified source bytes changed')
    if sha(oldpriv/'frozen-queries.json')!=p['frozen_queries_sha256']:raise ValueError('same original queries required')
    q=load(oldpriv/'frozen-queries.json');asof=now()
    if any(x.get('actual')is not None or not old_wave.avail.open_query(x,src.utc(asof).timestamp())for x in q['week8']):raise ValueError('same future actual-null queries must remain openT90')
    plan=[];model_bytes=collections.Counter()
    for c in changes:
        path=original/c['artifact_id'];f=load(path);decision=action(f['state'],bool(c.get('any_raw_feature_changed')));future=c['future_reference']
        qp=member(oldpriv,f['query_features']);model=f.get('model')
        if model:member(oldpriv,model);model_bytes[decision]+=model['bytes']
        fp=None
        if not future:
            receipt=load(original/(f['slot']+'-FORECAST.json'));fp=receipt['packet'];member(oldpriv,fp)
        plan.append(dict(original_fit_artifact=c['artifact_id'],original_fit_sha256=sha(path),target=c['target'],policy_id=c['policy_id'],
            information_group=c['information_group'],phase='future'if future else'historical',action=decision,
            affected_training_rows=c.get('any_raw_feature_changed',0),training_n=f['training_n'],training_membership_sha256=f['training_membership_sha256'],
            original_model=model,original_query_features=f['query_features'],original_forecast_packet=fp))
    census=collections.Counter((r['phase'],r['action'])for r in plan)
    if len(plan)!=768 or census['historical','REFIT_AFFECTED_TRAINING']!=266 or census['future','REFIT_AFFECTED_TRAINING']!=42:raise ValueError('exact308 selective-refit census required')
    members=[]
    for name in('football_memberships','chart_memberships','football_future_memberships','chart_future_memberships'):
        members.append(dict(role=name,artifact_id='RETAINED-'+sha(m[name]),sha256=sha(m[name])))
    if sha(m['chart_labels'])!=p['chart_label_packet_sha256']:raise ValueError('qualified chart source packet changed')
    # Original own-player Leaf controls are already authenticated in the original
    # private binding map. New future refreshes preserve those fit origins.
    base_bindings=load(original/'RETAINED_FUTURE_CONTROL_BINDINGS.json');base_local=load(oldpriv/'CONTROL_BINDINGS_PRIVATE.json')
    for b in base_bindings:
        loc=base_local[b['key']]
        if sha(loc['receipt_path'])!=b['receipt_sha256']or(loc['model_path']and sha(loc['model_path'])!=b['model_sha256']):raise ValueError('original future base control binding changed')
    pub.mkdir(parents=True);priv.mkdir(parents=True)
    write(priv/'INPUT_BINDINGS_PRIVATE.json',m);write(priv/'frozen-queries.json',q)
    write(pub/'REUSE_PLAN.json',plan);write(pub/'RETAINED_BASE_FUTURE_BINDINGS.json',base_bindings)
    prior=load(original/'HISTORICAL_RUN_RECEIPT.json');future=load(original/'WEEK8_CAPTURE_RECEIPT.json')
    protocol=dict(version=VERSION,state='PREPARED_NO_FITS_RESTORATION_AND_WORKER_GATED',registered_at_utc=now(),code_sha256=sha(__file__),
        helpers={Path(x.__file__).name:sha(x.__file__)for x in modules()},source_ids=p['source_ids'],source_role_contract=p['source_role_contract'],
        original_protocol_sha256=sha(original/'FROZEN_PROTOCOL.json'),audit_protocol_sha256=sha(ap/'FROZEN_PROTOCOL.json'),audit_receipt_sha256=sha(ap/'AUDIT_RECEIPT.json'),
        original_historical_receipt_sha256=sha(original/'HISTORICAL_RUN_RECEIPT.json'),original_future_receipt_sha256=sha(original/'WEEK8_CAPTURE_RECEIPT.json'),
        reuse_plan_sha256=sha(pub/'REUSE_PLAN.json'),base_future_bindings_sha256=sha(pub/'RETAINED_BASE_FUTURE_BINDINGS.json'),
        private_input_binding_sha256=sha(priv/'INPUT_BINDINGS_PRIVATE.json'),frozen_query_sha256=sha(priv/'frozen-queries.json'),
        chart_label_packet_sha256=p['chart_label_packet_sha256'],cohort_memberships=members,
        preparation_query_metadata_at_utc=asof,original_future_query_asof_utc=p['fixed_future_query_asof_utc'],
        future_query_cutoff_policy='Freeze a new aware actual common query/feature cutoff at FUTURE phase execution start before any feature generation/inference; preparation metadata is never an inference or issuance clock.',
        mechanism='Separate four eligible scheduled REG team-game windows. Absent position groups consume UNKNOWN slots, not zeros; exact same own20features/labels/trainingmembers/learner/priors/fallback; unchanged league prior. D2 age refers to latest scheduled kickoff.',
        history='Historical fit/query clocks unchanged. Core3common2022featurememory; strict2026labels/own/opponent/league/priors/transforms. No pre2022 or currentWeek8labels. Future TRAINING labels/features/origins exactly original observed model receipts, with a new common query cutoff for every variant.',
        reuse='Recompute old/new raw training matrices, labels, memberships and priors. Unchanged fitted cells restore same hashed model with zero refits. Historical forecasts alias original bytes only when model/prior/source/query features and actuals match, or when a declared prior fallback ignores changed defense inputs. Every affected fitted training cell must attempt a new fit. Reuse is not a new NFL fit or original issuance.',
        equivalence_census=dict(logical_cells=768,historical_refits=266,future_refits=42,unchanged_fitted_models=344,unchanged_no_model_prior_cells=116),
        forest=learner.FOREST,law='unchanged95%equal-tree leafPMF+5%samearmrole/globalprior; mean/median outputs are views, not independent learners',
        historical_panel=dict(query_cells=17968,weeks=list(range(1,8)),games=107,source_vintage='current_vintage_reconstruction',population='retrospective qualified observed participant'),
        comparisons='Scheduled vs same-policy observed window primary; own-player Leaf secondary. Frozen strongest-compatible full-primary controls from source audit remain required review references; unresolved adapter joins remain explicit, never invented losses. Full/top10/top15/top20 reuse original membership with full/ownlearned/pairedlearned/fallback contributions.',
        strongest_reference_specs=load(ap/'FROZEN_PROTOCOL.json')['strongest_reference_specs'],
        future='New partial13game research version: scheduledD1/D2 plus same-new-cutoff observedD1/D2 (96retainedmodels0refit) and baseLeaf (48retainedmodels0refit). Preserve original13game2229queries/8blocked and frozen future cohorts. Record actual model origin, inference/issue/persistence/horizon. No backdate, official capture, currentinjury refresh or website deployment.',
        budget=dict(max_new_fit_calls=308,max_historical_new_fits=266,max_future_new_fits=42,logical_opportunities=768,wall_seconds=900,cpu_seconds=1200,
            max_peak_memory_bytes=2147483648,max_private_bytes=805306368,max_forecast_rows=600000,max_threads=2,max_source_rows=200000,hyperparameter_searches=0),
        measured_original=dict(historical_fits=556,historical_wall_seconds=prior['resource']['wall_seconds'],historical_peak_bytes=prior['resource']['peak_rss_bytes'],
            future_fits=96,future_wall_seconds=future['resource']['wall_seconds'],original_private_bytes=future['private_output_bytes'],model_bytes_by_action=dict(model_bytes)),
        admission='NO_FIT_UNTIL_ROOT_FRESH_FULL_RESTORE_PASS_PLUS_SEPARATE_WORKER_RELEASE_AND_INDEPENDENT_PREFIT_PASS',
        expanded_retention_gate=dict(helper_sha256=sha(retention.__file__),required_recovery_plan_sha256=retention.EXPECTED_PLAN_SHA256,required_private_file_map_sha256=retention.EXPECTED_PRIVATE_MAP_SHA256,required_aliases=29527,required_unique_contents=20217,required_missing_part_restorations=53),
        new_family_count=0,actual_new_fit_calls=0,new_forecasts=0,week8_outcomes_read=0,official_capture=False,deployed=False)
    write(pub/'FROZEN_PROTOCOL.json',protocol);return protocol

def amend_prepared(*,previous_public,previous_private,public_root,private_root):
    """Clock-only metadata amendment; no repeated source/model/data scans."""
    oldpub,oldpriv,pub,priv=map(Path,(previous_public,previous_private,public_root,private_root))
    if pub.exists()or priv.exists():raise ValueError('fresh amended preparation required')
    p=load(oldpub/'FROZEN_PROTOCOL.json')
    for mod in modules():
        if p['helpers'][Path(mod.__file__).name]!=sha(mod.__file__):raise ValueError('changed dependency needs a separately reviewed full preparation')
    for name,key in(('REUSE_PLAN.json','reuse_plan_sha256'),('RETAINED_BASE_FUTURE_BINDINGS.json','base_future_bindings_sha256')):
        if sha(oldpub/name)!=p[key]:raise ValueError('old prepared public binding changed')
    for name,key in(('INPUT_BINDINGS_PRIVATE.json','private_input_binding_sha256'),('frozen-queries.json','frozen_query_sha256')):
        if sha(oldpriv/name)!=p[key]:raise ValueError('old prepared private binding changed')
    pub.mkdir(parents=True);priv.mkdir(parents=True)
    for name in('REUSE_PLAN.json','RETAINED_BASE_FUTURE_BINDINGS.json'):
        with(pub/name).open('xb')as f:f.write((oldpub/name).read_bytes())
    for name in('INPUT_BINDINGS_PRIVATE.json','frozen-queries.json'):
        with(priv/name).open('xb')as f:f.write((oldpriv/name).read_bytes())
    p.update(version=VERSION,code_sha256=sha(__file__),state='PREPARED_UNRUN_ACTUAL_FUTURE_PHASE_CLOCK_REQUIRED',registered_at_utc=now(),
        supersedes_prepared_protocol_sha256=sha(oldpub/'FROZEN_PROTOCOL.json'),
        prior_proposed_query_cutoff_utc=p.pop('fixed_future_query_asof_utc',None),
        preparation_query_metadata_at_utc=now(),
        future_query_cutoff_policy='Freeze a new aware actual common query/feature cutoff at FUTURE phase execution start before any feature generation/inference; preparation metadata is never an inference or issuance clock.')
    write(pub/'FROZEN_PROTOCOL.json',p);return p

def verify(public_root,private_root,*,restoration_gate,worker_release,review,phase):
    pub,priv=Path(public_root),Path(private_root);p=load(pub/'FROZEN_PROTOCOL.json');p['protocol_sha256']=sha(pub/'FROZEN_PROTOCOL.json')
    if p['code_sha256']!=sha(__file__):raise ValueError('frozen wave code changed')
    for mod in modules():
        if p['helpers'][Path(mod.__file__).name]!=sha(mod.__file__):raise ValueError('frozen helper changed')
    if sha(priv/'INPUT_BINDINGS_PRIVATE.json')!=p['private_input_binding_sha256']or sha(priv/'frozen-queries.json')!=p['frozen_query_sha256']:raise ValueError('private bindings/queries changed')
    if sha(pub/'REUSE_PLAN.json')!=p['reuse_plan_sha256']:raise ValueError('reuse plan changed')
    if sha(pub/'RETAINED_BASE_FUTURE_BINDINGS.json')!=p['base_future_bindings_sha256']:raise ValueError('retained future base model bindings changed')
    proof=gates(p,restoration_gate=restoration_gate,worker_release=worker_release,review=review,software=pub/'SOFTWARE_CHECKS.json',phase=phase)
    m=load(priv/'INPUT_BINDINGS_PRIVATE.json')
    for s in p['source_ids']:
        if sha(Path(m['source_root'])/s['name'])!=s['sha256']:raise ValueError('source changed after admission')
    for binding in p['cohort_memberships']:
        if sha(m[binding['role']])!=binding['sha256']:raise ValueError('frozen cohort membership changed')
    if sha(m['chart_labels'])!=p['chart_label_packet_sha256']:raise ValueError('qualified chart label packet changed')
    return p,m,proof

def _data(p,m,guard):
    rows,games,counts,_,_=chart.load_chart_source(m['source_root'],dict(p,budget=dict(max_source_rows=p['budget']['max_source_rows'])))
    cached={(r['game_id'],r['player_id']):r['label']['points_times_50']for r in json.loads(gzip.decompress(Path(m['chart_labels']).read_bytes()))['rows']}
    if set(cached)!={(r['game_id'],r['player_id'])for r in rows}or any(cached[r['game_id'],r['player_id']]!=r['values'][chart.TARGET]for r in rows):raise ValueError('qualified original chart labels not reproduced')
    inputs.attach_context(rows,games,m['source_root']);oldhist=inputs.build_history(rows,TARGETS);newhist=scheduled.build_history(rows,games,TARGETS)
    own={f:learner.feature_history(rows,f)for f in(2022,2026)};datasets={}
    for t in TARGETS:
        roles=set(src.POSITIONS)if t==chart.TARGET else src.allowed_roles(p,t)
        for floor in(2022,2026):
            rs=[r for r in rows if r['season']>=floor and r['position']in roles and r['values'][t]is not None];a=[];b=[]
            for r in rs:
                x,_=own[floor].get(r['player_id'],r['position'],t,r['kickoff']);q=dict(r,target=t,cutoff=r['kickoff'],blocked_reason=None)
                oa,_=inputs.augment(x,oldhist,q,floor,'D2');nb,_=inputs.augment(x,newhist,q,floor,'D2');a.append(oa);b.append(nb)
            datasets[t,floor]=rs,np.asarray(a),np.asarray(b)
            guard()
    return rows,games,counts,own,oldhist,newhist,datasets

def run(*,phase,public_root,private_root,restoration_gate,worker_release,review):
    """Only caller-supplied proven admission can reach an NFL fit/inference."""
    if phase not in('historical','future'):raise ValueError('registered explicit phase required')
    p,m,proof=verify(public_root,private_root,restoration_gate=restoration_gate,worker_release=worker_release,review=review,phase=phase)
    pub,priv,oldpub,oldpriv=map(Path,(public_root,private_root,m['original_public'],m['original_private']))
    if(pub/(phase.upper()+'_RUN_RECEIPT.json')).exists():raise ValueError('completed/failed phase is immutable; explicit new continuation required')
    prior=load(pub/'HISTORICAL_RUN_RECEIPT.json')if phase=='future'else None
    if prior and prior['state']!='COMPLETE':raise ValueError('complete historical phase required before future')
    if phase=='future'and any(not old_wave.avail.open_query(q,datetime.now(timezone.utc).timestamp())for q in load(priv/'frozen-queries.json')['week8']):raise ValueError('frozen future deadlines closed; new explicit protocol/cohort amendment required')
    execution_asof=now()if phase=='future'else None
    if phase=='future':write(pub/'FUTURE_EXECUTION_CUTOFF.json',dict(version=VERSION,state='ACTUAL_FUTURE_QUERY_FEATURE_CUTOFF_FROZEN_BEFORE_INFERENCE',actual_cutoff_utc=execution_asof,protocol_sha256=p['protocol_sha256'],query_packet_sha256=p['frozen_query_sha256'],source_ids=p['source_ids'],candidate_and_observed_and_base_same_cutoff=True,preparation_clock_used_for_inference=False,week8_outcomes_read=0))
    start,cpu=time.monotonic(),time.process_time();calls=models_reused=model_aliases=forecast_aliases=0;rows_out=[];finished=[];failures=[];meters=collections.defaultdict(recipe.Metrics);terminal='COMPLETE'
    private_bytes=sum(f.stat().st_size for f in priv.rglob('*')if f.is_file())
    write(pub/(phase.upper()+'_EXECUTION_REGISTRATION.json'),dict(version=VERSION,actual_started_at_utc=now(),actual_query_feature_cutoff_utc=execution_asof,phase=phase,protocol_sha256=p['protocol_sha256'],new_fit_calls_before_start=0,**proof))
    def guard():
        wall=(prior['resource']['wall_seconds']if prior else 0)+time.monotonic()-start;cp=(prior['resource']['cpu_seconds']if prior else 0)+time.process_time()-cpu
        if wall>p['budget']['wall_seconds']or cp>p['budget']['cpu_seconds']:raise ResourceBudget('TOTAL_TIME_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>p['budget']['max_peak_memory_bytes']:raise ResourceBudget('MEMORY_BUDGET')
    def save(name,value,raw=False):
        nonlocal private_bytes
        guard();body=value if raw else canonical(value);guard();blob=gzip.compress(body,mtime=0);guard()
        if private_bytes+len(blob)>p['budget']['max_private_bytes']:raise ResourceBudget('PRIVATE_BYTES_BEFORE_WRITE')
        path=priv/name;path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb')as f:f.write(blob);f.flush();os.fsync(f.fileno())
        private_bytes+=len(blob)
        if path.read_bytes()!=blob:raise ValueError('new artifact readback failed')
        guard()
        return dict(artifact_id='SCHEDULED-'+sha(path),bundle_name=name,sha256=sha(path),bytes=len(blob))
    try:
        source_rows,games,counts,own,oh,nh,datasets=_data(p,m,guard);lookup={(r['game_id'],r['player_id']):r for r in source_rows}
        members={}
        for key in('football_memberships','chart_memberships'):
            for r in json.loads(gzip.decompress(Path(m[key]).read_bytes())):
                k=tuple(r['key'])
                if k in members:raise ValueError('duplicate frozen subgroup membership')
                members[k]=r
        qs=load(priv/'frozen-queries.json');plan=[r for r in load(pub/'REUSE_PLAN.json')if r['phase']==phase]
        basebindings={r['key']:r for r in load(pub/'RETAINED_BASE_FUTURE_BINDINGS.json')};baselocal=load(oldpriv/'CONTROL_BINDINGS_PRIVATE.json');future_base_done=set()
        with threadpool_limits(limits=2):
            for cell in plan:
                guard();path=oldpub/cell['original_fit_artifact']
                if sha(path)!=cell['original_fit_sha256']:raise ValueError('original fit receipt changed')
                oldfit=load(path);t=cell['target'];policy=cell['policy_id'];group=cell['information_group'];arm,fitfloor,floor=POLICIES[policy];width=20+len(GROUPS[group]);rs,ox,nx=datasets[t,floor]
                origin=src.utc(oldfit.get('fit_cutoff_utc')or oldfit['training_label_fit_cutoff_utc']).timestamp();idx=[i for i,r in enumerate(rs)if r['season']>=fitfloor and r['available']<origin]
                oldx,newx=ox[idx,:width],nx[idx,:width];y=np.asarray([rs[i]['values'][t]for i in idx]);positions=[rs[i]['position']for i in idx]
                membership=hashlib.sha256(canonical([(rs[i]['game_id'],rs[i]['player_id'])for i in idx])).hexdigest();count={pos:positions.count(pos)for pos in src.POSITIONS};globalprior=recipe.laws_prior(y,t);priors={pos:recipe.laws_prior([rs[i]['values'][t]for i in idx if rs[i]['position']==pos],t)if count[pos]else globalprior for pos in src.POSITIONS}
                if len(idx)!=oldfit['training_n']or membership!=oldfit['training_membership_sha256']or count!=oldfit['prior_position_sample_counts']or {pos:law.parameters()for pos,law in priors.items()}!=oldfit['prior_parameters']:raise ValueError('original training membership/labels/priors changed')
                oldhash,newhash=array_digest(oldx),array_digest(newx);changed=oldhash!=newhash
                if changed!=bool(cell['affected_training_rows']):raise ValueError('frozen raw-feature change census contradicts reconstructed matrices')
                model=None;modelref=cell['original_model'];state=cell['action'];started=ended=None
                if state=='REFIT_AFFECTED_TRAINING':
                    if calls>=p['budget']['max_'+phase+'_new_fits']or calls+(prior['actual_new_fit_calls']if prior else 0)>=308:raise RuntimeError('AFFECTED_ONLY_FIT_BUDGET')
                    calls+=1;started=now()
                    try:model=learner.FittedLawModel(FAMILY,t).fit(newx,y,positions);ended=now()
                    except(MemoryError,ResourceBudget):raise
                    except Exception as exc:
                        ended=now();state='FIT_FAILED_FALLBACK';modelref=None;failures.append(dict(cell=cell['original_fit_artifact'],type=type(exc).__name__,reason=str(exc)[:240]))
                    if model is not None:
                        guard();modelref=save(phase+'-models/'+Path(cell['original_fit_artifact']).stem+'.pickle.gz',pickle.dumps(model,protocol=5),True)
                elif state=='REUSE_UNCHANGED_TRAINING_MODEL':models_reused+=1
                else:model_aliases+=1
                original_packet=json.loads(gzip.decompress(member(oldpriv,cell['original_query_features']).read_bytes()))
                if phase=='historical':
                    qrows=[r['query']for r in original_packet];oldqx=np.asarray([[math.nan if v is None else v for v in r['features']]for r in original_packet]);oldrecords=json.loads(gzip.decompress(member(oldpriv,cell['original_forecast_packet']).read_bytes()))['rows'];oldindex={recipe.controlkey(r):r for r in oldrecords}
                else:qrows=[dict(q,cutoff=src.utc(execution_asof).timestamp(),actual=None)for q in qs['week8']if q['target']==t];oldindex={};oldqx=None
                qx=[];observed_qx=[];maxima=[];observed_maxima=[];own_maxima=[];audits=[]
                for q in qrows:
                    if phase=='historical':
                        r=lookup[q['game_id'],q['player_id']];value=r['values'][t];actual=value/50 if t==chart.TARGET and value is not None else value
                        if q['actual']!=actual or q['position']!=r['position']:raise ValueError('original query label/position differs from qualified source')
                    else:
                        if q.get('actual')is not None:raise ValueError('current Week8 outcome forbidden')
                    blocked=q.get('blocked_reason')or q.get('position')not in src.POSITIONS
                    f,clock=(np.full(20,np.nan),None)if blocked else own[floor].get(q['player_id'],q['position'],t,q['cutoff'])
                    a,aa=inputs.augment(f,oh,q,floor,group);b,ba=inputs.augment(f,nh,q,floor,group);observed_qx.append(a);qx.append(b);maxima.append(old_wave.latest(clock,ba,group));observed_maxima.append(old_wave.latest(clock,aa,group));own_maxima.append(clock);audits.append(ba)
                qx=np.asarray(qx);observed_qx=np.asarray(observed_qx)
                if oldqx is not None and array_digest(observed_qx)!=array_digest(oldqx):raise ValueError('original stored query features not reproduced')
                fullalias=phase=='historical'and state!='FIT_FAILED_FALLBACK'and(cell['action']=='REUSE_DECLARED_NO_MODEL_PRIOR'or(not changed and array_digest(qx)==array_digest(oldqx)))
                if model is None and state=='REUSE_UNCHANGED_TRAINING_MODEL'and not fullalias:model=pickle.loads(gzip.decompress(member(oldpriv,cell['original_model']).read_bytes()))
                if model is not None and model.estimator.get_params()!=dict(model.estimator.get_params(),**learner.FOREST):raise ValueError('fixed forest parameters changed')
                variants=[('scheduled_'+group,model,qx,modelref,maxima)]
                origins={'scheduled_'+group:dict(source_fit_receipt_sha256=cell['original_fit_sha256'],actual_model_fit_completed_at=ended or oldfit.get('actual_fit_completed_at'))}
                if phase=='future':
                    observed_model=pickle.loads(gzip.decompress(member(oldpriv,cell['original_model']).read_bytes()));variants.append(('observed_'+group,observed_model,observed_qx,cell['original_model'],observed_maxima))
                    origins['observed_'+group]=dict(source_fit_receipt_sha256=cell['original_fit_sha256'],actual_model_fit_completed_at=oldfit.get('actual_fit_completed_at'))
                    key=t+':'+policy
                    if key not in future_base_done:
                        binding=basebindings[key];loc=baselocal[key]
                        if sha(loc['receipt_path'])!=binding['receipt_sha256']or(loc['model_path']and sha(loc['model_path'])!=binding['model_sha256']):raise ValueError('retained base model changed')
                        if binding['training_membership_sha256']!=membership or binding['training_n']!=len(idx)or src.utc(binding['fit_cutoff_utc']).timestamp()!=origin:raise ValueError('base future origin/membership must match unchanged original training')
                        base_model=None if not loc['model_path']else pickle.loads(gzip.decompress(Path(loc['model_path']).read_bytes()));variants.append(('retained_base_leaf',base_model,qx[:,:20],dict(artifact_id=binding['model_artifact_id'],sha256=binding['model_sha256']),own_maxima));future_base_done.add(key)
                        origins['retained_base_leaf']=dict(source_fit_receipt_sha256=binding['receipt_sha256'],actual_model_fit_completed_at=load(loc['receipt_path']).get('actual_fit_completed_at'))
                if len(rows_out)+len(qrows)*len(recipe.products(t))*len(variants)+(prior['logical_output_views']if prior else 0)>p['budget']['max_forecast_rows']:raise RuntimeError('OUTPUT_BUDGET_BEFORE_INFERENCE')
                features=save(phase+'-features/'+Path(cell['original_fit_artifact']).stem+'.json.gz',[dict(query=q,features=src.json_features(f),latest_feature_available=clock,scheduled_window=a)for q,f,clock,a in zip(qrows,qx,maxima,audits)])
                records=[]
                for variant,vm,matrix,reference,clocks in variants:
                    guard();inferred=[(None,None)]*len(qrows)if fullalias and variant.startswith('scheduled_')else learner.predict_admitted(vm,matrix,qrows,priors);guard();generated=now()
                    variant_state=state if variant.startswith('scheduled_')else'REUSED_ORIGINAL_OBSERVED_MODEL'if variant.startswith('observed_')else'REUSED_ORIGINAL_BASE_MODEL'
                    variant_proc=proc(group,policy)if variant.startswith('scheduled_')else old_wave.proc(group,policy)if variant.startswith('observed_')else(chart.VERSION if t==chart.TARGET else learner.VERSION)+':ordered_leaf_cdf'+(':strict-current-inputs'if floor==2026 else':common-feature-memory')
                    for q,f,clock,(law,detail)in zip(qrows,matrix,clocks,inferred):
                        blocked=q.get('blocked_reason')or('UNQUALIFIED_POSITION'if q.get('position')not in src.POSITIONS else None)
                        fallback=None if blocked else'none'
                        if not blocked and(vm is None or f[3]<=0):
                            law=priors[q['position']];detail=dict(fallback_prior=law.parameters());fallback='fixed_no_NFL_startup'if not len(idx)else'cold_start_role_prior'if f[3]<=0 else'no_model_role_prior'
                        alias=phase=='historical'and(fullalias or(fallback!='none'and state!='FIT_FAILED_FALLBACK'))
                        summary=None if blocked or alias else chart.chart_summary(law,q.get('actual_grid'))if t==chart.TARGET else law.summary(q.get('actual'))
                        for product in recipe.products(t):
                            key=recipe.controlkey(dict(q,policy_id=policy,product_id=product))
                            if alias:
                                oldrow=oldindex[key]
                                if not fullalias and oldrow['fallback']=='none':raise ValueError('prior-only alias cannot replace learned original forecast')
                                row=dict(oldrow,run_id=VERSION,procedure_id=proc(group,policy),reuse='ORIGINAL_FORECAST_VALUE_ALIAS',original_procedure_id=oldrow['procedure_id'],original_forecast_artifact_id=cell['original_forecast_packet']['artifact_id'],derived_projection_at_utc=generated);forecast_aliases+=1
                            else:
                                row=dict(q,run_id=VERSION,procedure_id=variant_proc,procedure_family_id=FAMILY,information_group=group if variant!='retained_base_leaf'else'OWN_ONLY',variant=variant,history_regime=arm,policy_id=policy,information_policy='STRICT-CURRENT'if floor==2026 else'COMMON-2022-MEMORY',feature_floor=floor,product_id=product,prediction=None if blocked else summary['mean'if product=='event_probability'else product],fallback=fallback,distribution_summary=summary,law_reference=None if blocked else detail,actual_generated_at=generated,reuse='NEW_INFERENCE_FROM_'+variant_state,fit_state=variant_state)
                            if phase=='historical':
                                oldrow=oldindex[key];row.update(window_control_prediction=oldrow['prediction'],window_control_fallback=oldrow['fallback'],window_control_procedure_id=oldrow['procedure_id'],control_prediction=oldrow['control_prediction'],control_fallback=oldrow['control_fallback'],control_procedure_id=oldrow['control_procedure_id'])
                                views=[('ALL','ALL','ALL'),(str(q['week']),'ALL','ALL'),('ALL',q['position'],'ALL')]
                                if row['fallback']=='none':views.append(('ALL','ALL','LEARNED_ONLY'))
                                else:views.append(('ALL','ALL','FALLBACK_ONLY'))
                                if row['fallback']=='none'and oldrow['fallback']=='none':views.append(('ALL','ALL','PAIRED_LEARNED_OVERLAP'))
                                for cohort in members[identity(q)]['cohorts']:
                                    if cohort in('top10','top15','top20'):views.append(('ALL','ALL',cohort))
                                for week,pos,view in views:meters[group,policy,t,q['population'],product,week,pos,view].add(row)
                            else:
                                if clock is not None and clock>=q['cutoff']:raise ValueError('future feature availability violation')
                                if not old_wave.avail.open_query(q,src.utc(generated).timestamp()):blocked=blocked or'T90_CLOSED_BEFORE_ISSUANCE'
                                row.update(actual=None,actual_status='PENDING_FUTURE',status='ABSTAIN'if blocked else'STAGED_RESEARCH_SHADOW',prediction=None if blocked else row['prediction'],abstention_reason=blocked,distribution_summary=None if blocked else row['distribution_summary'],issued_at_utc=None if blocked else generated,feature_cutoff_utc=execution_asof,training_fit_cutoff_utc=datetime.fromtimestamp(origin,timezone.utc).isoformat(),model_artifact_id=None if reference is None else reference['artifact_id'],original_model_sha256=None if reference is None else reference['sha256'],actual_horizon_seconds=None if blocked else src.utc(q['kickoff_utc']).timestamp()-src.utc(generated).timestamp(),official_capture=False,**origins[variant])
                            records.append(row)
                if len(rows_out)+len(records)+(prior['logical_output_views']if prior else 0)>p['budget']['max_forecast_rows']:raise RuntimeError('OUTPUT_BUDGET_BEFORE_PERSISTENCE')
                packet=save(phase+'-chunks/'+Path(cell['original_fit_artifact']).stem+'.json.gz',dict(schema=VERSION,rows=records));persisted=now()
                if phase=='future'and any(r['prediction']is not None and not old_wave.avail.open_query(r,src.utc(persisted).timestamp())for r in records):raise RuntimeError('T90_CROSSED_DURING_PERSISTENCE')
                receipt=dict(cell=cell['original_fit_artifact'],state=state,action=cell['action'],training_membership_sha256=membership,training_label_sha256=array_digest(y),old_training_features_sha256=oldhash,new_training_features_sha256=newhash,training_features_changed=changed,old_model=cell['original_model'],model=modelref,feature_packet=features,forecast_packet=packet,full_historical_forecast_alias=fullalias,original_fit_cutoff_utc=datetime.fromtimestamp(origin,timezone.utc).isoformat(),latest_training_label_available=max((rs[i]['available']for i in idx),default=None),feature_floor=floor,latest_query_feature_available=max((x for x in maxima if x is not None),default=None),actual_fit_started_at=started,actual_fit_completed_at=ended,actual_persistence_completed_at=persisted,prior_parameters={pos:law.parameters()for pos,law in priors.items()},output_views=len(records))
                write(pub/(phase.upper()+'-'+Path(cell['original_fit_artifact']).stem+'-CELL.json'),receipt);finished.append(cell['original_fit_artifact']);rows_out.extend(records)
                guard()
    except Exception as exc:terminal='PARTIAL_STOPPED';failures.append(dict(cell=cell['original_fit_artifact']if'cell'in locals()else None,type=type(exc).__name__,reason=str(exc)[:240]))
    # Release source/feature caches before serializing the retained prediction
    # bundle; those caches are not scoring inputs and do not mutate old files.
    if'datasets'in locals():datasets.clear()
    if'own'in locals():own.clear()
    if'oh'in locals():oh.opponents.clear();oh.league.clear()
    if'nh'in locals():nh.lookup.clear();nh.observed.opponents.clear();nh.observed.league.clear()
    if'lookup'in locals():lookup.clear()
    if'source_rows'in locals():source_rows.clear()
    packet=None
    try:packet=save('ALL_'+phase.upper()+'_PREDICTIONS.json.gz',dict(schema=VERSION,rows=rows_out))
    except Exception as exc:terminal='PARTIAL_STOPPED';failures.append(dict(stage='aggregate_persistence',type=type(exc).__name__,reason=str(exc)[:240]))
    completed_at=now()
    if phase=='historical':
        scores=[];dates=[]
        try:
            for dims,meter in sorted(meters.items()):
                guard();group,policy,target,pop,product,week,pos,view=dims;rr=meter.rows;control={identity(r):dict(r,prediction=r['window_control_prediction'],fallback=r['window_control_fallback'],procedure_id=r['window_control_procedure_id'])for r in rr};comparison=subgroup.paired(rr,control,'brier'if target=='anytime_td'else'mae')
                scores.append(dict(record_id='SCHEDULED-'+hashlib.sha256(canonical([VERSION,dims])).hexdigest()[:24],procedure_id=proc(group,policy),procedure_family_id=FAMILY,information_group=group,target=target,history_regime=POLICIES[policy][0],policy_id=policy,product_id=product,population=pop,evaluation_panel_id=VERSION,season=2026,week=int(week)if week.isdigit()else week,position=pos,fallback_view=view,source_vintage='current_vintage_reconstruction',record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',evidence='NEW_EXPERIMENT',comparison=comparison,strongest_reference_status='FROZEN_REFERENCE_PENDING_SEPARATE_EXACT_ROW_REPLAY',fallback_decomposition=fallback_contribution(rr,target),**meter.result(target,product)))
                dates.append(dict(source_row_index=len(scores)-1,evaluation_seasons=[2026],evaluation_weeks=sorted({int(r['week'])for r in rr if r['actual']is not None}),forecast_query_weeks=sorted({int(r['week'])for r in rr})));guard()
        except(ResourceBudget,MemoryError)as exc:terminal='PARTIAL_STOPPED';failures.append(dict(stage='scoring',type=type(exc).__name__,reason=str(exc)[:240]))
        # Tiny failure/status persistence remains available after a resource
        # stop. Completed score rows retain identity; uncomputed views stay absent.
        try:
            guard();write(pub/'SCORES.json',scores);guard();write(pub/'SCORE_DATE_PROJECTION.json',dict(source_score_sha256=sha(pub/'SCORES.json'),rows=dates));guard()
        except(ResourceBudget,MemoryError)as exc:
            terminal='PARTIAL_STOPPED';failures.append(dict(stage='score_persistence',type=type(exc).__name__,reason=str(exc)[:240]))
            write(pub/'SCORING_PENDING.json',dict(state='BOUNDED_SCORER_STOPPED_RETAIN_PREDICTIONS_AND_REPLAY_ONLY_MISSING_VIEWS',computed_score_views=len(scores),canonical_score_persisted=(pub/'SCORES.json').exists(),current2026_week8_outcomes_read=0))
    receipt=dict(version=VERSION,state=terminal,phase=phase,actual_completed_at_utc=completed_at,actual_query_feature_cutoff_utc=execution_asof,protocol_sha256=p['protocol_sha256'],actual_new_fit_calls=calls,
        reused_unchanged_model_cells=models_reused,reused_no_model_prior_cells=model_aliases,aliased_historical_forecast_views=forecast_aliases,logical_output_views=len(rows_out),
        completed_cells=len(finished),remaining_cells=(672 if phase=='historical'else 96)-len(finished),completed_cell_ids=finished,packet=packet,failures=failures,
        issued_future_views=sum(r.get('prediction')is not None for r in rows_out)if phase=='future'else 0,abstained_future_views=sum(r.get('prediction')is None for r in rows_out)if phase=='future'else 0,
        private_output_bytes=private_bytes,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2),
        week8_outcomes_read=0,official_capture=False,website_published=False,private_durability='LOCAL_NEW_OUTPUTS_REQUIRE_FRESH_ROOT_COMPANION_RESTORATION')
    write(pub/(phase.upper()+'_RUN_RECEIPT.json'),receipt);return receipt
