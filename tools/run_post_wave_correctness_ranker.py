"""One fixed contextual ranking change on retained chronological forecasts."""
import collections
import hashlib
import json
import math
import resource
import sys
import time
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from threadpoolctl import threadpool_limits,threadpool_info
from nfl_v2 import correctness_ranker as mechanism,exact_line_repair as original,full_provider_prop_replay as core
from tools import abc_b_c_bound_replay as a,abc_b_glm_exact_line_replay as pm
from tools.diagnose_post_wave_confidence import metrics


def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def run(private,out,retained):
    start=time.monotonic();cpu=time.process_time();protocol=a.load(out/'FROZEN_PROTOCOL.json')
    assert a.sha(__file__)==protocol['runner_sha256']and a.sha(ROOT/'nfl_v2/correctness_ranker.py')==protocol['mechanism_sha256']
    assert a.sha(retained/'PREPARED_INPUT_ROWS_V2.json.gz')==protocol['input_sha256']
    private.mkdir(exist_ok=False);data=a.load(retained/'PREPARED_INPUT_ROWS_V2.json.gz');models={};rows=[];usages=[];fitcalls=0
    def model(pool,cutoff,target):
        nonlocal fitcalls
        train=original.eligible_training(pool,cutoff);key=digest([target,sorted(r['offer_id']for r in train)])
        if key not in models:
            before=time.monotonic();m=mechanism.fit(pool,cutoff);fitcalls+=int(m['fit_performed']);assert fitcalls<=16
            m.update(model_id=key,target=target,actual_computed_at_utc=datetime.now(timezone.utc).isoformat(),fit_wall_seconds=time.monotonic()-before);models[key]=m
        return models[key]
    with threadpool_limits(limits=2):
        pools=threadpool_info();assert all(p['num_threads']<=2 for p in pools)
        for target in ['rec','pass_td']:
            d=data[target];history=[] if target=='rec'else d['gate_oof'];batches=collections.defaultdict(list);slots=collections.defaultdict(int)
            for r in d['evaluation']:batches[r['decision_epoch']].append(r)
            fixed=model(d['calibration'],d['calibration_freeze'],target)if target=='pass_td'else None
            for cutoff,batch in sorted(batches.items()):
                frozen=d['calibration_freeze']if target=='pass_td'else cutoff;m=fixed or model(d['calibration'],cutoff,target)
                threshold=original.gate_threshold(history,frozen);candidates=[]
                for r in batch:
                    score=mechanism.rank_score(r,m)
                    if score is not None and original.confidence(r['probabilities'])>=threshold:candidates.append(dict(r,rank_score=score))
                qualified=[r for r in candidates if r['rank_score']>=.5]
                K=min(math.ceil(.5*sum(r['probabilities']is not None for r in batch)),len(candidates),len(qualified))
                ranks={0:sorted(candidates,key=lambda r:(-original.confidence(r['probabilities']),r['offer_id'])),1:sorted(qualified,key=lambda r:(-r['rank_score'],r['offer_id']))}
                for arm in [0,1]:
                    for policy in ['MATCHED50','FIXED_090']+[f'ROLLING_K{k}_{s}'for k in [6,10,20]for s in ['Combined','over','under']]:
                        if policy=='MATCHED50':ids={r['offer_id']for r in ranks[arm][:K]}
                        elif policy=='FIXED_090':ids={r['offer_id']for r in ranks[arm]if(original.confidence(r['probabilities'])if arm==0 else r['rank_score'])>=.9}
                        else:
                            k,side=policy.split('_')[1:];k=int(k[1:]);eligible=[r for r in ranks[arm]if side=='Combined'or original.choose(r['probabilities'])==side];slot=(arm,batch[0]['week'],policy);ids={r['offer_id']for r in eligible[:max(0,k-slots[slot])]};slots[slot]+=len(ids)
                        for r in batch:
                            side=original.choose(r['probabilities']);q=dict(r,prediction=None,raw_prediction=None,method_key=f'B::POST-WAVE-5W-CORRECTNESS-RANK-v1::{target}::G{arm}',selection_policy=policy,selected_side=side if r['offer_id']in ids else None,side=side if r['offer_id']in ids else None,original_side=None,rank_score=mechanism.rank_score(r,m)if arm else original.confidence(r['probabilities']),rank_model_id=m['model_id'],ranker_state=m['state']if arm else'UNCHANGED_CONFIDENCE_ORDER',ranker_identity_fallback=not m['fit_performed'],ranker_threshold=threshold)
                            q=core.grade([q],strategies=('original',))[0]
                            if q['probabilities']is None:q['statistical_state']='UNAVAILABLE_FORECAST'
                            rows.append(q)
                usages.append(dict(target=target,decision_epoch=cutoff,calibration_cutoff=frozen,model_id=m['model_id'],latest_label_available=m['latest_label_available'],base_confidence_threshold=threshold,matched_K=K,available_base_rows=sum(r['probabilities']is not None for r in batch),qualified_ranker_rows=len(qualified),model_state=m['state']))
                if target=='rec':history+=batch
        assert all(p['num_threads']<=2 for p in threadpool_info())
    # Required recoverable bytes precede public results; serialization is plain
    # JSON coefficients, not untrusted pickle. Refuse overwrite and excess size.
    a.gzsave(private/'MODELS_AND_SELECTION_ROWS.json.gz',dict(models=models,rows=rows),max_bytes=2097152)
    scores=[];pairs=[];ownpool=[]
    for target in ['rec','pass_td']:
        weeks=sorted({r['week']for r in rows if r['target']==target});views=[str(w)for w in weeks]+(['ALL']if len(weeks)>1 else[])
        for policy in sorted({r['selection_policy']for r in rows}):
            for week in views:
                byarm={arm:[r for r in rows if r['target']==target and r['method_key'].endswith('G'+str(arm))and r['selection_policy']==policy and(week=='ALL'or r['week']==int(week))]for arm in [0,1]}
                for arm,rr in byarm.items():
                    name=f'B::POST-WAVE-5W-CORRECTNESS-RANK-v1::{target}::G{arm}';ss=a.score(rr,name,target,week,dict(history_regime='H-MULTI_BASE_PLUS_EARLIER_OOF_CORRECTNESS',product_id='base_event_direction_with_selection_reliability_ranker',decision_rule=policy,point_functional='NONE;UNCHANGED_BASE_MEAN_SEPARATELY_RETAINED'),f'POST-WAVE-5W-v1:{target}:{policy}')
                    for s in ss:
                        sub=[r for r in rr if r['selected_side']and(s['side']=='Combined'or r['selected_side']==s['side'])];s.update(strategy=policy,default_rank_eligible=False,purpose='REGISTERED_RESEARCH_SELECTION_POLICY_NOT_PRIMARY_RELEASE',horizon_id='C_KICKOFF_RECONSTRUCTION'if target=='rec'else'B_ORIGINAL_EARLY_CAPTURE_PLUS_RETAINED_LATER_T90_THRESHOLDS',source_vintage=protocol['source_vintage'][target],selection_evidence='RETROSPECTIVE_RULE_REPLAY',probability_rank_score_contract='G1_RANK_SCORE_IS_BASELINE_CORRECTNESS_ESTIMATE_NOT_OVER_UNDER_EV',K=int(policy.split('_')[1][1:])if policy.startswith('ROLLING_K')else None,rank_scope='PER_CATEGORY_PER_WEEK_ROLLING_DECISION_BATCHES'if policy.startswith('ROLLING_K')else None)
                        s['selection_metrics']['probability_scores']=pm.metrics(sub);s['selection_metrics']['ranker_identity_fallback_rows']=sum(r['probabilities']is not None and r['ranker_identity_fallback']for r in rr);s['selection_metrics']['ranker_learned_rows']=sum(r['probabilities']is not None and not r['ranker_identity_fallback']for r in rr)
                    scores+=ss
                    # Strong simple controls on exactly the arm's selected mask.
                    for control in ['ALWAYS_OVER','ALWAYS_UNDER']:
                        cc=[]
                        for r in rr:
                            if not r['selected_side']:continue
                            q=dict(r,probabilities=dict(over=.5,under=.5,push=0.),selected_side='over'if control=='ALWAYS_OVER'else'under',side='over'if control=='ALWAYS_OVER'else'under',original_side=None);cc.append(core.grade([q],strategies=('original',))[0])
                        cs=a.score(cc,name+'::MATCHED_'+control,target,week,dict(history_regime='MATCHED_CONTROL',product_id='same_selected_opportunity_constant_side',decision_rule=control,parent_policy=policy,parent_source_eligible=len(rr),parent_selected=len(cc)),f'POST-WAVE-5W-v1:{target}:{policy}:G{arm}:{control}')
                        for s in cs:s.update(strategy=control,parent_policy=policy,default_rank_eligible=False,horizon_id=ss[0]['horizon_id'],source_vintage=protocol['source_vintage'][target],selection_evidence='RETROSPECTIVE_CONSTANT_CONTROL')
                        scores+=cs
                pairs.append(a.pair(byarm[1],byarm[0],target,f'B::POST-WAVE-5W-CORRECTNESS-RANK-v1::{target}::G1','G0_CONFIDENCE_MATCHED_COUNT',week,policy))
                pools_decided={arm:[r for r in rr if r['statistical_state']in ['WIN','LOSS']]for arm,rr in byarm.items()};ns={arm:len(rr)for arm,rr in pools_decided.items()};wins={arm:sum(r['statistical_state']=='WIN'for r in rr)for arm,rr in pools_decided.items()};rates={arm:wins[arm]/ns[arm]if ns[arm]else None for arm in [0,1]};delta=rates[1]-rates[0]if all(ns.values())else None;games=sorted({r['game_id']for r in byarm[0]});se=None
                if delta is not None and len(games)>1:
                    influence=[]
                    for game in games:
                        z={arm:sum(int(r['statistical_state']=='WIN')-rates[arm]for r in rr if r['game_id']==game)/ns[arm]for arm,rr in pools_decided.items()};influence.append(z[1]-z[0])
                    se=math.sqrt(len(games)/(len(games)-1)*sum(z*z for z in influence))
                ownpool.append(dict(target=target,week=week,policy=policy,raw_wins=wins[0],raw_n=ns[0],ranker_wins=wins[1],ranker_n=ns[1],hit_rate_change=delta,game_clusters=len(games),game_sensitivity_se=se,game95_sensitivity=[delta-1.96*se,delta+1.96*se]if se is not None else None,interpretation='Ownselectedpools maydiffer; sameavailableuniverse andbatchcountpolicy. Not purecommonrowlearner effect. Fewweekclusters/exposed/multiplicityunadjusted.'))
    # Learned-only common mask is an additional view, not startup deletion.
    for target in ['rec','pass_td']:
        for arm in [0,1]:
            rr=[r for r in rows if r['target']==target and r['method_key'].endswith('G'+str(arm))and r['selection_policy']=='MATCHED50'and not r['ranker_identity_fallback']]
            ss=a.score(rr,f'B::POST-WAVE-5W-CORRECTNESS-RANK-v1::{target}::G{arm}',target,'ALL',dict(history_regime='H-MULTI_BASE_PLUS_EARLIER_OOF_CORRECTNESS',product_id='base_event_direction_with_selection_reliability_ranker',decision_rule='MATCHED50',cohort_id='COMMON_LEARNED_RANKER_ROWS'),f'POST-WAVE-5W-v1:{target}:MATCHED50:COMMON_LEARNED')
            for s in ss:s.update(strategy='MATCHED50',cohort_id='COMMON_LEARNED_RANKER_ROWS',default_rank_eligible=False,horizon_id='C_KICKOFF_RECONSTRUCTION'if target=='rec'else'B_ORIGINAL_EARLY_CAPTURE_PLUS_RETAINED_LATER_T90_THRESHOLDS',source_vintage=protocol['source_vintage'][target])
            scores+=ss
    a.save(out/'SCORES.json',scores);a.save(out/'PAIRED_COMPARISONS.json',pairs);a.save(out/'OWN_POOL_CHANGE_SENSITIVITY.json',ownpool);a.save(out/'FIT_USAGE_AND_CUTOFFS.json',usages)
    a.save(out/'MODEL_MANIFEST.json',dict(models=[{k:v for k,v in m.items()if k not in ['coefficients','intercept','training_offer_ids']}for m in models.values()],private_rows_sha256=a.sha(private/'MODELS_AND_SELECTION_ROWS.json.gz'),private_rows_bytes=(private/'MODELS_AND_SELECTION_ROWS.json.gz').stat().st_size,offhost_restored=False))
    receipt=dict(state='COMPLETE_BOUNDED_CONTEXTUAL_SELECTION_TEST_NOT_C_ADMITTED',actual_completed_at_utc=datetime.now(timezone.utc).isoformat(),new_ranker_fits=fitcalls,new_football_fits=0,new_football_inference=0,new_issued_forecasts=0,new_NFL_observations=0,score_views=len(scores),paired_views=len(pairs),new_private_bytes=(private/'MODELS_AND_SELECTION_ROWS.json.gz').stat().st_size,wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,thread_pools_during_fit=[{k:p[k]for k in ['user_api','internal_api','num_threads']}for p in pools],source_rows_unchanged=True,base_probabilities_and_sides_unchanged=True,software_precision='deterministiclbfgs/C.25, boundedfeatures,seed1703, nosearch')
    assert receipt['wall_seconds']<=180 and receipt['cpu_seconds']<=120 and receipt['peak_RSS_bytes']<=536870912
    a.save(out/'RUN_RECEIPT.json',receipt);print(json.dumps(receipt))


if __name__=='__main__':run(*map(Path,sys.argv[1:4]))
