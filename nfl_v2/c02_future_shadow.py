"""New future-only C02 versus retained ordered Leaf-CDF shadow capture.

Training rows/priors match each retained control exactly. Query cutoff is a new
actual time with the conservative seven-day policy; no Week 8 label is decoded.
"""
from __future__ import annotations
import collections,gzip,json,os,pickle,platform,resource,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
from . import availability_wave as avail,ordered_information_ablation as recipe
from . import hgb_control as src,distribution_wave_v2 as base,chart_wave as chart
from .distribution_laws import Law

VERSION='v2-c02-future-ordered-control-shadow-v1'
canonical=src.canonical;sha=src.sha;now=src.now;write=src.immutable_json

def blocked_reason(q):
    return q.get('blocked_reason') or ('UNQUALIFIED_POSITION' if q.get('position') not in src.POSITIONS else None)

def training_binding(rows,target,arm,floor,origin,hist):
    rs=[r for r in rows if r['season']>=floor and r['position'] in (set(src.POSITIONS) if target==chart.TARGET else set(src.POSITIONS)) and r['values'][target] is not None]
    selected=[r for r in rs if r['season']>=src.fit_floor(arm) and r['available']<origin]
    x=[];maximum=[]
    for r in selected:
        f,m=hist.get(r['player_id'],r['position'],target,r['kickoff']);x.append(f);maximum.append(m)
        if m is not None and m>=r['kickoff']:raise ValueError('historical training feature leakage')
    return selected,np.asarray(x),maximum

def prepare(public,private,source_root,football_public,chart_public,private_roots,queries):
    public,private=Path(public),Path(private);football_public,chart_public=Path(football_public).resolve(),Path(chart_public).resolve()
    if public.exists() or private.exists():raise ValueError('fresh outputs required')
    old=json.loads((football_public/'FROZEN_PROTOCOL.json').read_text());cp=json.loads((chart_public/'FROZEN_PROTOCOL.json').read_text())
    if old['source_ids']!=cp['source_ids']:raise ValueError('source panels differ')
    for item in old['source_ids']:
        if sha(Path(source_root)/item['name'])!=item['sha256']:raise ValueError('source changed')
    public.mkdir(parents=True);private.mkdir(parents=True);asof=now();q=json.loads(Path(queries).read_text())
    if len(q)!=2229 or len({r['game_id'] for r in q})!=13:raise ValueError('wrong frozen future membership')
    if any(r.get('actual') is not None or r['week']!=8 for r in q):raise ValueError('not pending future queries')
    if any(not avail.open_query(r,src.utc(asof).timestamp()) for r in q):raise ValueError('deadline already closed')
    write(private/'frozen-queries.json',q);bindings=[];local={}
    for target in recipe.TARGETS:
        for policy,(arm,fit_floor,feature_floor) in recipe.POLICIES.items():
            path=chart_public/f'W08-{policy}-ordered_leaf_cdf-FIT.json' if target==chart.TARGET else football_public/f'W08-{target}-{policy}-ordered_leaf_cdf-FIT.json'
            receipt=json.loads(path.read_text());model=avail.resolve_model(receipt,private_roots);key=target+':'+policy
            bindings.append(dict(key=key,target=target,policy_id=policy,history_regime=arm,fit_floor=fit_floor,feature_floor=feature_floor,fit_cutoff_utc=receipt['fit_cutoff_utc'],training_n=receipt['training_n'],training_membership_sha256=receipt['training_membership_sha256'],receipt_artifact=path.relative_to(Path(__file__).resolve().parents[1]).as_posix(),receipt_sha256=sha(path),model_artifact_id=None if model is None else 'MODEL-'+sha(model),model_sha256=None if model is None else sha(model)))
            local[key]=dict(receipt_path=str(path),model_path=None if model is None else str(model))
    write(public/'RETAINED_CONTROL_BINDINGS.json',bindings);write(private/'CONTROL_BINDINGS_PRIVATE.json',local)
    expected=2*len(recipe.POLICIES)*sum(len(recipe.products(r['target'])) for r in q)
    p=dict(version=VERSION,state='FROZEN_BEFORE_NUMERIC_FEATURES_INFERENCE_AND_FITS',registered_at_utc=now(),fixed_query_asof_utc=asof,code_sha256=sha(__file__),helper_code_sha256={Path(m.__file__).name:sha(m.__file__) for m in (avail,recipe,src,base,chart,src.empirical)},law_code_sha256=sha(Path(__file__).with_name('distribution_laws.py')),source_ids=old['source_ids'],source_role_contract=old['source_role_contract'],frozen_queries_sha256=sha(private/'frozen-queries.json'),source_query_packet_sha256=sha(queries),retained_control_bindings_sha256=sha(public/'RETAINED_CONTROL_BINDINGS.json'),query_cells=len(q),query_games=len({r['game_id'] for r in q}),expected_output_views=expected,targets=list(recipe.TARGETS),policies={k:dict(history_regime=v[0],fit_floor=v[1],feature_floor=v[2]) for k,v in recipe.POLICIES.items()},candidate='sameC02explicitlagblockremovalmechanismasnewhistoricalwave; separatefutureidentity; raw20->8/design40->16; removeindividual4lagvalue/age/missingtriplets andflags, retainmean3/n3/mean8/n8 andpositiononehot',retained_raw_columns=list(recipe.KEEP_NAMES),removed_raw_columns=list(src.FEATURES[4:16]),training='match each ORIGINAL retainedWeek8Leaf training membership/labels/priors/floors/cutoff exactly; C02refitonlyfeatureprojection; no oldmodel refitted or oldforecast overwritten',query='bothvariants refresh own history at NEWcommonactualasof using seven-day availability only; no qualifiedfreshW7B/Cpolicy or newcontext',availability='historical rawsource cutoff+7day strictlyearlier; no historicalpublicationclaim; source currentvintage, allsource2026statistics filteredREGW<=7 before numericdecode',forest=base.FOREST,law='95%equal-tree empiricalleafPMF+5%samearmrole/globalfullsupportprior; exact inheritedPMF/CRPS/quantiles; signedchartscore*50 then point/CRPS/interval/50, PMFmassunchanged',fallback='samecontrolprior and samefullqueryn8coldstartroute forboth variants; 60mintraining; allzero-count/singleclassbinary nofit; unknownIDs/Noneposition abstainBEFOREmodel rolelookup',strict='H-CURRENT-STRICT labels/features/priors/transforms2026only; fixedarchitecturehistoricallychosen/exposed, not untouchedconfirmation',grading=dict(state='NO_WEEK8_LABELS_PENDING',primary='MAEnumericwithmean/medianfunctionalidentity; Brier rushing-or-receivinganytimeTD',secondary='meanMSE/RMSE; lawCRPS+PMFlogscore+zeroMass+90%coverage/width; exactchartmedianintegercoordinateprecision, no roundingmeans',cohort='samefrozen2229queryIDs; allissued/abstentions retained; no futureselection; matchedsupportedlabel pairs and separately learned-onlyintersection',labels='sourcepublication/finality/exactidentity/appearance/targetcontractadmission required; DNP/playedzero/playedmissing/unknown/canceled separate; positive/missingchartrareaggregates remainnull',selection='NONE; nooffers/prices/ROIorhindsightmethodselector'),ownership=dict(state='RESEARCH_SHADOW_OWNER_ADMISSION_PENDING',coordination='retainedownerchannelcomment6513284161',official_capture=False,website_published=False),budget=dict(max_fit_calls=48,wall_seconds=600,cpu_seconds=900,max_threads=2,max_peak_memory_bytes=2147483648,max_private_bytes=1073741824,max_source_rows=200000,max_forecast_rows=40000,hyperparameter_searches=0),new_family_count=0,Week8_outcomes_read=0)
    if expected>p['budget']['max_forecast_rows']:raise ValueError('preflight forecast budget')
    write(public/'FROZEN_PROTOCOL.json',p);return p

def run(source_root,public,private,verifier_receipt):
    public,private=Path(public),Path(private);p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());start,cpu=time.monotonic(),time.process_time()
    if sha(__file__)!=p['code_sha256'] or sha(private/'frozen-queries.json')!=p['frozen_queries_sha256'] or sha(public/'RETAINED_CONTROL_BINDINGS.json')!=p['retained_control_bindings_sha256']:raise ValueError('frozen input changed')
    for name,h in p['helper_code_sha256'].items():
        if sha(Path(__file__).with_name(name))!=h:raise ValueError('helper changed')
    if sha(Path(__file__).with_name('distribution_laws.py'))!=p['law_code_sha256']:raise ValueError('law changed')
    for s in p['source_ids']:
        if sha(Path(source_root)/s['name'])!=s['sha256']:raise ValueError('source changed')
    verification=json.loads(Path(verifier_receipt).read_text())
    if verification.get('protocol_sha256')!=sha(public/'FROZEN_PROTOCOL.json') or verification.get('state')!='PASS_PREFIT_PROTOCOL_REVIEW':raise ValueError('independent prefit review required')
    if json.loads((public/'SOFTWARE_CHECKS.json').read_text())['code_sha256']!=sha(__file__):raise ValueError('fixture binding')
    write(public/'EXECUTION_REGISTRATION.json',dict(version=VERSION,actual_started_at=now(),protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),independent_prefit_review_sha256=sha(verifier_receipt),new_fit_calls=0,sole_worker_confirmed=True,environment=dict(python=platform.python_version(),numpy=np.__version__)))
    rows,games,counts,chartlabels,chartcoverage=chart.load_chart_source(source_root,p);hist={floor:base.feature_history(rows,floor) for floor in (2022,2026)};queries=json.loads((private/'frozen-queries.json').read_text());bindings=json.loads((public/'RETAINED_CONTROL_BINDINGS.json').read_text());local=json.loads((private/'CONTROL_BINDINGS_PRIVATE.json').read_text());asof=src.utc(p['fixed_query_asof_utc']).timestamp();outputs=[];fits=[];failures=[];calls=0
    for name in ('models','features','chunks'):(private/name).mkdir(exist_ok=True)
    def guard():
        if time.monotonic()-start>p['budget']['wall_seconds'] or time.process_time()-cpu>p['budget']['cpu_seconds']:raise RuntimeError('TIME_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>p['budget']['max_peak_memory_bytes']:raise RuntimeError('RSS_BUDGET')
    def save(path,obj,raw=False):
        blob=gzip.compress(obj if raw else canonical(obj),mtime=0)
        if sum(f.stat().st_size for f in private.rglob('*') if f.is_file())+len(blob)>p['budget']['max_private_bytes']:raise RuntimeError('PRIVATE_BUDGET')
        with path.open('xb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
        if gzip.decompress(path.read_bytes())!=(obj if raw else canonical(obj)):raise ValueError('localreadback')
        return dict(artifact_id='C02-FUTURE-'+sha(path),bundle_name=path.relative_to(private).as_posix(),sha256=sha(path),bytes=len(blob))
    terminal='COMPLETE'
    with threadpool_limits(limits=2):
      try:
        for target in recipe.TARGETS:
          roles=set(src.POSITIONS) if target==chart.TARGET else src.allowed_roles(p,target);target_rows=[r for r in rows if r['position'] in roles]
          for binding in [b for b in bindings if b['target']==target]:
            guard();key=binding['key'];policy=binding['policy_id'];arm=binding['history_regime'];floor=binding['feature_floor'];original_origin=src.utc(binding['fit_cutoff_utc']).timestamp();oldpath=Path(local[key]['receipt_path'])
            if sha(oldpath)!=binding['receipt_sha256']:raise ValueError('control receipt changed')
            old=json.loads(oldpath.read_text());train,x,mx=training_binding(target_rows,target,arm,floor,original_origin,hist[floor]);y=np.asarray([r['values'][target] for r in train]);positions=[r['position'] for r in train];membership=__import__('hashlib').sha256(canonical([(r['game_id'],r['player_id']) for r in train])).hexdigest();globalprior=recipe.laws_prior(y,target);poscounts={pos:positions.count(pos) for pos in src.POSITIONS};priors={pos:recipe.laws_prior([r['values'][target] for r in train if r['position']==pos],target) if poscounts[pos] else globalprior for pos in src.POSITIONS}
            if membership!=binding['training_membership_sha256'] or len(train)!=old['training_n'] or {pos:law.parameters() for pos,law in priors.items()}!=old['prior_parameters'] or poscounts!=old['prior_position_sample_counts']:raise ValueError('exact control training/prior mismatch')
            qr=[q for q in queries if q['target']==target];features=[];maxima=[]
            for q in qr:
                f,m=hist[floor].get(q['player_id'],q['position'],target,asof);features.append(f);maxima.append(m)
                if m is not None and m>=asof:raise AssertionError('query feature leakage')
            full=np.asarray(features);projected=recipe.project(full);featurepacket=save(private/'features'/(key.replace(':','--')+'.json.gz'),[dict(query=q,full_features=src.json_features(f),candidate_features=src.json_features(g),latest_feature_available=m) for q,f,g,m in zip(qr,full,projected,maxima)])
            control=None
            if local[key]['model_path']:
                if sha(local[key]['model_path'])!=binding['model_sha256']:raise ValueError('control model changed')
                control=pickle.loads(gzip.decompress(Path(local[key]['model_path']).read_bytes()))
            candidate=None;state='NO_FIT_INSUFFICIENT_TRAINING';modelpacket=None;fit_start=None;fit_end=None
            if len(train)>=60 and not (target in src.empirical.COUNTS and np.all(y==0)) and not (target=='anytime_td' and len(np.unique(y))<2):
                if calls>=p['budget']['max_fit_calls']:raise RuntimeError('FIT_BUDGET')
                calls+=1;fit_start=now()
                try:candidate=base.FittedLawModel('ordered_leaf_cdf',target).fit(recipe.project(x),y,positions);fit_end=now();state='FITTED_RETAINED';guard();modelpacket=save(private/'models'/(key.replace(':','--')+'.pickle.gz'),pickle.dumps(candidate,protocol=5),True)
                except Exception as exc:candidate=None;fit_end=now();state='FIT_FAILED_FALLBACK';failures.append(dict(key=key,type=type(exc).__name__,reason=str(exc)[:200]))
            audit=dict(key=key,target=target,policy_id=policy,history_regime=arm,feature_floor=floor,training_n=len(train),training_membership_sha256=membership,control_training_and_priors_match=True,training_label_fit_cutoff_utc=binding['fit_cutoff_utc'],latest_training_label_available=max((r['available'] for r in train),default=None),latest_training_feature_available=max((m for m in mx if m is not None),default=None),prior_parameters={pos:law.parameters() for pos,law in priors.items()},prior_position_sample_counts=poscounts,state=state,actual_fit_started_at=fit_start,actual_fit_completed_at=fit_end,model=modelpacket,query_features=featurepacket,retained_control_model_artifact_id=binding['model_artifact_id'])
            write(public/(key.replace(':','--')+'-FIT.json'),audit);fits.append(audit);slotrows=[]
            if len(outputs)+len(qr)*2*len(recipe.products(target))>p['budget']['max_forecast_rows']:raise RuntimeError('FORECAST_BUDGET_BEFORE_INFERENCE')
            for variant,model,qx in [('retained_ordered_control',control,full),('c02_explicit_lag_block_removed',candidate,projected)]:
                predicted=base.predict_admitted(model,qx,qr,priors);generated=now()
                for q,f,m,(law,detail) in zip(qr,full,maxima,predicted):
                    reason=blocked_reason(q);fallback='none';d=None
                    if not reason:
                        if model is None or f[3]<=0:law=priors[q['position']];detail=dict(fallback_prior=law.parameters());fallback='fixed_no_NFL_startup' if not len(train) else 'cold_start_role_prior' if f[3]<=0 else 'no_model_role_prior'
                        d=chart.chart_summary(law,None) if target==chart.TARGET else law.summary(None)
                    for product in recipe.products(target):
                        value=None if reason else d['mean' if product=='event_probability' else product]
                        slotrows.append(dict(q,run_id=VERSION,variant=variant,family='ordered_leaf_cdf',procedure_id=VERSION+':'+variant+':'+('strict-current-inputs' if floor==2026 else 'common-feature-memory'),history_regime=arm,policy_id=policy,information_policy='STRICT-CURRENT' if floor==2026 else 'COMMON-2022-MEMORY',product_id=product,prediction=value,actual=None,actual_status='PENDING_FUTURE',status='ABSTAIN' if reason else 'STAGED_RESEARCH_SHADOW',abstention_reason=reason,fallback=None if reason else fallback,feature_cutoff_utc=p['fixed_query_asof_utc'],latest_feature_available=m,training_fit_cutoff_utc=binding['fit_cutoff_utc'],actual_generated_at=generated,issued_at_utc=None if reason else generated,actual_horizon_seconds=None if reason else src.utc(q['kickoff_utc']).timestamp()-src.utc(generated).timestamp(),distribution_summary=None if reason else d,law_reference=None if reason else detail,fit_state=old['state'] if variant=='retained_ordered_control' else state,model_artifact_id=binding['model_artifact_id'] if variant=='retained_ordered_control' else None if modelpacket is None else modelpacket['artifact_id']))
            # Slot persistence is immutable; later aggregate retains same actual clocks.
            checked=datetime.now(timezone.utc).timestamp()
            for r in slotrows:
                if not avail.open_query(r,checked):r.update(prediction=None,status='ABSTAIN',abstention_reason='T90_CLOSED_BEFORE_PERSISTENCE',distribution_summary=None,issued_at_utc=None)
            packet=save(private/'chunks'/(key.replace(':','--')+'.json.gz'),dict(schema=VERSION,rows=slotrows));persisted=now()
            if any(r['prediction'] is not None and not avail.open_query(r,src.utc(persisted).timestamp()) for r in slotrows):raise RuntimeError('DEADLINE_CROSSED_DURING_PERSISTENCE_INVALID')
            write(public/(key.replace(':','--')+'-FORECAST.json'),dict(key=key,packet=packet,actual_persistence_completed_at=persisted,output_views=len(slotrows),issued=sum(r['prediction'] is not None for r in slotrows),abstained=sum(r['prediction'] is None for r in slotrows),all_issued_before_T90=True));outputs.extend(slotrows)
      except Exception as exc:terminal='PARTIAL_STOPPED';failures.append(dict(type=type(exc).__name__,reason=str(exc)[:240]))
    packet=save(private/'STAGED_SHADOWS.json.gz',dict(schema=VERSION,rows=outputs));persisted=now()
    receipt=dict(version=VERSION,state=terminal,owner_state='RESEARCH_SHADOW_OWNER_ADMISSION_PENDING',actual_completed_at=now(),actual_aggregate_persistence_completed_at=persisted,fixed_query_asof_utc=p['fixed_query_asof_utc'],packet=packet,protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),query_cells=len(queries),query_games=len({r['game_id'] for r in queries}),actual_fit_calls=calls,retained_new_models=sum(f['state']=='FITTED_RETAINED' for f in fits),retained_control_models=len(bindings),completed_cells=len(fits),remaining_cells=len(bindings)-len(fits),output_views=len(outputs),issued=sum(r['prediction'] is not None for r in outputs),abstained=sum(r['prediction'] is None for r in outputs),score_views=0,actual_Week8_outcomes_read=0,official_capture=False,website_published=False,source_counts=counts,failures=failures,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2))
    write(public/'RUN_RECEIPT.json',receipt);return receipt
