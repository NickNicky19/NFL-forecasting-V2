"""Read-only gradient, chronology and frozen-policy audit; no fit/scorer imports."""
import argparse,collections,gzip,hashlib,json,math,statistics
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
def read(p):
    b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def close(a,b):return a==b or(a is not None and b is not None and abs(a-b)<1e-10)
def choose(p):return None if p is None or abs(p['over']-p['under'])<=1e-12 else'over'if p['over']>p['under']else'under'
def conf(p):return max(p['over'],p['under'])if p is not None else None
def feature(r):
    p=r['probabilities'];side=choose(p)
    if side is None:return None
    assert set(p)=={'over','under','push'}and abs(sum(p.values())-1)<1e-10 and min(p.values())>=0
    line=r['line'];assert line>=0 and line%1==.5 and r['position']in('QB','RB','WR','TE')
    return [2*conf(p)-1,int(side=='over'),line/(line+3),int(r['position']=='RB'),int(r['position']=='WR'),int(r['position']=='TE')]
def sigmoid(x):return 1/(1+math.exp(-x))if x>=0 else math.exp(x)/(1+math.exp(x))
def rank(r,m):
    x=feature(r)
    if x is None:return None
    return conf(r['probabilities'])if not m['fit_performed']else sigmoid(m['intercept']+math.fsum(a*b for a,b in zip(x,m['coefficients'])))
def eligible(rr,t):return[r for r in rr if r['label_available']<t and r['probabilities']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'and r['line']%1==.5]
def gate(rr,t):
    vv=[conf(r['probabilities'])for r in rr if r['decision_epoch']<t and r['probabilities']is not None]
    return max(.6,statistics.median(vv))if len(vv)>=20 else .6
def state(r):
    if r['probabilities']is None:return'UNAVAILABLE_FORECAST'
    if r['selected_side']is None:return'ABSTAIN'
    if r['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL':return'UNKNOWN_PARTICIPATION'
    if r['actual']is None:return'MISSING_ACTUAL'
    return'PUSH'if r['actual']==r['line']else'WIN'if((r['actual']>r['line'])==(r['selected_side']=='over'))else'LOSS'
def proper(rr):
    rr=[r for r in rr if r['probabilities']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];b=[];ll=[]
    for r in rr:
        e='over'if r['actual']>r['line']else'under'if r['actual']<r['line']else'push';p=r['probabilities'];b.append(.5*math.fsum((p[s]-int(e==s))**2 for s in('over','under','push')));ll.append(-math.log(p[e])if p[e]else math.inf)
    return dict(n=len(rr),brier=math.fsum(b)/len(b)if b else None,log_loss=math.fsum(ll)/len(ll)if ll else None,infinite_log_losses=sum(math.isinf(x)for x in ll))
def run(repo,retained,private,out):
    protocol=read(out/'FROZEN_PROTOCOL.json');receipt=read(out/'RUN_RECEIPT.json');manifest=read(out/'MODEL_MANIFEST.json');data=read(retained/'PREPARED_INPUT_ROWS_V2.json.gz');payload=read(private/'MODELS_AND_SELECTION_ROWS.json.gz');models=payload['models'];stored=payload['rows'];scores=read(out/'SCORES.json')
    assert sha(out/'FROZEN_PROTOCOL.json')=='8db55285efd2532155abf0a2a875052d0269909c50980a6aec651879f269da79';assert sha(repo/'nfl_v2/correctness_ranker.py')==protocol['mechanism_sha256']and sha(repo/'tools/run_post_wave_correctness_ranker.py')==protocol['runner_sha256'];assert sha(retained/'PREPARED_INPUT_ROWS_V2.json.gz')==protocol['input_sha256'];assert sha(private/'MODELS_AND_SELECTION_ROWS.json.gz')==manifest['private_rows_sha256']and(private/'MODELS_AND_SELECTION_ROWS.json.gz').stat().st_size==manifest['private_rows_bytes']==receipt['new_private_bytes']==348170
    gradients=[];prefixmutations=0
    for mid,m in models.items():
        rr=eligible(data[m['target']]['calibration'],m['cutoff_epoch']);ids=sorted(r['offer_id']for r in rr);assert mid==m['model_id']==digest([m['target'],ids])and ids==m['training_offer_ids'];assert all(feature(r)is not None for r in rr);games=collections.Counter(r['game_id']for r in rr);correct=sum((r['actual']>r['line'])==(choose(r['probabilities'])=='over')for r in rr)
        assert(m['n'],m['games'],m['correct'],m['incorrect'])==(len(rr),len(games),correct,len(rr)-correct);assert m['latest_label_available']==max((r['label_available']for r in rr),default=None);assert datetime.fromisoformat(m['actual_computed_at_utc'])>datetime.fromisoformat(protocol['registered_at_utc']);supported=len(rr)>=20 and len(games)>=5 and min(correct,len(rr)-correct)>=3;assert m['fit_performed']==supported
        changed=[dict(r,actual=999,probabilities=dict(over=.99,under=.01,push=0.))if r['label_available']>=m['cutoff_epoch']else r for r in data[m['target']]['calibration']];assert eligible(changed,m['cutoff_epoch'])==rr;prefixmutations+=1
        if not supported:continue
        b=np.asarray([m['intercept']]+m['coefficients']);grad=np.r_[0.,4*np.asarray(m['coefficients'])];hessian=np.diag([0.]+[4.]*6)
        for r in rr:
            x=np.asarray([1.]+feature(r));q=sigmoid(float(np.dot(x,b)));y=int((r['actual']>r['line'])==(choose(r['probabilities'])=='over'));w=1/games[r['game_id']];grad+=(q-y)*w*x;hessian+=q*(1-q)*w*np.outer(x,x)
        norm=float(max(abs(grad)));curvature=float(np.linalg.eigvalsh(hessian)[0]);assert norm<3e-7 and curvature>0 and not m['iteration_limit_reached'];gradients.append(dict(target=m['target'],training_rows=m['n'],training_games=m['games'],maximum_objective_gradient_abs=norm,minimum_objective_Hessian_eigenvalue=curvature,coefficient_verification='Storedcoefficients satisfy independentlywritten convex gameweightedloglossplusL2 firstorderconditions; no reoptimizationorfit.'))
    assert len(models)==7 and len(gradients)==receipt['new_ranker_fits']==5
    assert receipt['new_football_fits']==receipt['new_football_inference']==receipt['new_issued_forecasts']==receipt['new_NFL_observations']==0 and all(x['num_threads']<=2 for x in receipt['thread_pools_during_fit'])
    expected={};usages=[];futurechecks=0;policies=['MATCHED50','FIXED_090']+[f'ROLLING_K{k}_{s}'for k in(6,10,20)for s in('Combined','over','under')]
    def getmodel(t,cutoff):return models[digest([t,sorted(r['offer_id']for r in eligible(data[t]['calibration'],cutoff))])]
    for target in('rec','pass_td'):
        d=data[target];history=[]if target=='rec'else list(d['gate_oof']);batches=collections.defaultdict(list);slots=collections.Counter()
        for r in d['evaluation']:batches[r['decision_epoch']].append(r)
        for cutoff,batch in sorted(batches.items()):
            frozen=d['calibration_freeze']if target=='pass_td'else cutoff;m=getmodel(target,frozen);threshold=gate(history,frozen);candidate=[r for r in batch if rank(r,m)is not None and conf(r['probabilities'])>=threshold];qualified=[r for r in candidate if rank(r,m)>=.5];K=min(math.ceil(.5*sum(r['probabilities']is not None for r in batch)),len(candidate),len(qualified));ranks={0:sorted(candidate,key=lambda r:(-conf(r['probabilities']),r['offer_id'])),1:sorted(qualified,key=lambda r:(-rank(r,m),r['offer_id']))}
            assert gate(history+[dict(batch[0],decision_epoch=frozen+1,actual=999,probabilities=dict(over=1.,under=0.,push=0.))],frozen)==threshold
            for r in batch:assert feature(dict(r,actual=999))==feature(r)and rank(dict(r,actual=999),m)==rank(r,m);futurechecks+=1
            for arm in(0,1):
                for policy in policies:
                    if policy=='MATCHED50':ids={r['offer_id']for r in ranks[arm][:K]}
                    elif policy=='FIXED_090':ids={r['offer_id']for r in ranks[arm]if(conf(r['probabilities'])if arm==0 else rank(r,m))>=.9}
                    else:
                        kk,side=policy.split('_')[1:];kk=int(kk[1:]);ordered=[r for r in ranks[arm]if side=='Combined'or choose(r['probabilities'])==side];key=arm,batch[0]['week'],policy;ids={r['offer_id']for r in ordered[:max(0,kk-slots[key])]};slots[key]+=len(ids)
                    for r in batch:
                        q=dict(r,prediction=None,raw_prediction=None,selected_side=choose(r['probabilities'])if r['offer_id']in ids else None,rank_model_id=m['model_id'],rank_score=rank(r,m)if arm else conf(r['probabilities']),ranker_state=m['state']if arm else'UNCHANGED_CONFIDENCE_ORDER',ranker_identity_fallback=not m['fit_performed'],ranker_threshold=threshold);expected[target,arm,policy,r['offer_id']]=q
            usages.append(dict(target=target,decision_epoch=cutoff,calibration_cutoff=frozen,model_id=m['model_id'],latest_label_available=m['latest_label_available'],base_confidence_threshold=threshold,matched_K=K,available_base_rows=sum(r['probabilities']is not None for r in batch),qualified_ranker_rows=len(qualified),model_state=m['state']))
            if target=='rec':history+=batch
    assert usages==read(out/'FIT_USAGE_AND_CUTOFFS.json')and len(expected)==len(stored)==8580
    groups=collections.defaultdict(list)
    for r in stored:
        key=r['target'],int(r['method_key'][-1]),r['selection_policy'],r['offer_id'];q=expected[key]
        for k in('probabilities','line','actual','position','decision_epoch','kickoff','label_available','participation','fallback','prediction','raw_prediction','selected_side','rank_model_id','ranker_state','ranker_identity_fallback','ranker_threshold'):assert r[k]==q[k],k
        assert close(r['rank_score'],q['rank_score'])and r['statistical_state']==state(q);groups[key[:3]].append(q)
    def view(rr,w):return[r for r in rr if w=='ALL'or r['week']==int(w)]
    triads=collections.defaultdict(dict);summary=[]
    for s in scores:
        t=s['target'];name=s['procedure_id'];arm=int(name.split('::G')[1][0]);control='::MATCHED_'in name;policy=s['parent_policy']if control else s['strategy'];pool=view(groups[t,arm,policy],str(s['week']))
        if s['cohort_id']=='COMMON_LEARNED_RANKER_ROWS':pool=[r for r in pool if not r['ranker_identity_fallback']]
        if control:
            side='over'if s['strategy']=='ALWAYS_OVER'else'under';pool=[dict(r,selected_side=side,probabilities=dict(over=.5,under=.5,push=0.))for r in pool if r['selected_side']]
        selected=[r for r in pool if r['selected_side']and(s['side']=='Combined'or r['selected_side']==s['side'])];counts=collections.Counter(state(r)for r in selected);m=s['selection_metrics'];n=counts['WIN']+counts['LOSS'];assert(s['forecast_rows'],s['n'],m['WIN'],m['LOSS'],m['PUSH'])==(len(selected),n,counts['WIN'],counts['LOSS'],counts['PUSH']);assert m['hit_rate']==(counts['WIN']/n if n else None)
        for k,v in m['status_counts'].items():assert v==counts[k]
        assert m['selection_pool_count']==len(pool)and m['technical_unavailable']==sum(state(r)=='UNAVAILABLE_FORECAST'for r in pool)and m['admitted_rule_abstentions']==sum(state(r)=='ABSTAIN'for r in pool)
        assert m['fallback_status_unknown']==sum(r['fallback']=='NOT_RETAINED'for r in pool)and m['fallback_issued']==sum(r['fallback']not in('none',False,None,'NOT_RETAINED')for r in pool)
        assert s['mae']is None and s['bias']is None and s['default_rank_eligible']is False and s['source_vintage']==protocol['source_vintage'][t]
        if not control and s['cohort_id']!='COMMON_LEARNED_RANKER_ROWS':
            assert m['ranker_identity_fallback_rows']==sum(r['probabilities']is not None and r['ranker_identity_fallback']for r in pool)and m['ranker_learned_rows']==sum(r['probabilities']is not None and not r['ranker_identity_fallback']for r in pool)
            pp=proper(selected)
            for k in('n','brier','log_loss','infinite_log_losses'):assert close(pp[k],m['probability_scores'][k])
            if policy.startswith('ROLLING_K'):assert s['K']==int(policy.split('_')[1][1:])and s['rank_scope']=='PER_CATEGORY_PER_WEEK_ROLLING_DECISION_BATCHES'
        key=name,t,policy,str(s['week']),s['cohort_id'];assert s['side']not in triads[key];triads[key][s['side']]=s
        if s['side']=='Combined'and str(s['week'])in('ALL','8')and policy in('MATCHED50','ROLLING_K10_Combined','FIXED_090')and s['cohort_id']!='COMMON_LEARNED_RANKER_ROWS':summary.append(dict(target=t,procedure=name,policy=policy,selected=len(selected),eligible=len(pool),wins=counts['WIN'],losses=counts['LOSS'],decided=n,unknown=counts['UNKNOWN_PARTICIPATION']))
    assert len(scores)==804 and len(triads)==268
    for vv in triads.values():
        assert set(vv)=={'over','under','Combined'}
        for k in('WIN','LOSS','PUSH'):assert vv['Combined']['selection_metrics'][k]==sum(vv[side]['selection_metrics'][k]for side in('over','under'))
        for k in('n','forecast_rows'):assert vv['Combined'][k]==sum(vv[side][k]for side in('over','under'))
    for s in read(out/'OWN_POOL_CHANGE_SENSITIVITY.json'):
        t=s['target'];p=s['policy'];pools={a:[r for r in view(groups[t,a,p],str(s['week']))if state(r)in('WIN','LOSS')]for a in(0,1)};nn={a:len(rr)for a,rr in pools.items()};ww={a:sum(state(r)=='WIN'for r in rr)for a,rr in pools.items()};rates={a:ww[a]/nn[a]if nn[a]else None for a in(0,1)};delta=rates[1]-rates[0]if all(nn.values())else None;assert(nn[0],ww[0],nn[1],ww[1])==(s['raw_n'],s['raw_wins'],s['ranker_n'],s['ranker_wins'])and close(delta,s['hit_rate_change']);games=sorted({r['game_id']for r in view(groups[t,0,p],str(s['week']))});assert len(games)==s['game_clusters'];se=None
        if delta is not None:
            z=[math.fsum(int(state(r)=='WIN')-rates[1]for r in pools[1]if r['game_id']==g)/nn[1]-math.fsum(int(state(r)=='WIN')-rates[0]for r in pools[0]if r['game_id']==g)/nn[0]for g in games];se=math.sqrt(len(games)/(len(games)-1)*math.fsum(v*v for v in z))
        assert close(se,s['game_sensitivity_se'])
    for s in read(out/'PAIRED_COMPARISONS.json'):
        aa={r['offer_id']:r for r in view(groups[s['target'],1,s['scope']],str(s['week_view']))if state(r)in('WIN','LOSS')};bb={r['offer_id']:r for r in view(groups[s['target'],0,s['scope']],str(s['week_view']))if state(r)in('WIN','LOSS')};ids=aa.keys()&bb.keys();aw=sum(state(aa[k])=='WIN'for k in ids);bw=sum(state(bb[k])=='WIN'for k in ids);assert(len(ids),aw,bw,aw-bw)==(s['common_decided'],s['candidate_wins'],s['control_wins'],s['win_difference']);delta=(bw-aw)/len(ids)if ids else None;assert close(delta,s['uncertainty']['delta'])
    missing={t:sum(r['probabilities']is None for r in data[t]['evaluation'])for t in('rec','pass_td')};assert missing=={'rec':22,'pass_td':2}
    report=dict(state='PASS_INDEPENDENT_GRADIENT_CHRONOLOGY_AND_FROZEN_SELECTIONS_WITH_SOURCE_SCOPE_LIMITS',at_utc=datetime.now(timezone.utc).isoformat(),verification_code_sha256=sha(Path(__file__)),protocol_sha256=sha(out/'FROZEN_PROTOCOL.json'),scores_sha256=sha(out/'SCORES.json'),private_model_rows_sha256=manifest['private_rows_sha256'],source_input_sha256=protocol['input_sha256'],fitted_objectives_checked=gradients,all_cached_model_states_checked=7,earlier_label_prefix_mutations_checked=prefixmutations,target_outcome_feature_rank_invariance_checks=futurechecks,stored_policy_rows_checked=len(stored),side_views_checked=804,side_triads_checked=268,paired_common_selection_contrasts_checked=44,own_pool_cluster_sensitivity_contrasts_checked=44,thread_pool_receipt_bound_leq_two=True,coefficient_refits=0,football_fits_or_inference=0,new_NFL_observations=0,fullsystem_evaluation_weeks={'rec':[2,3],'pass_td':[8]},missing_base_probabilities=missing,five_week_floor_met=False,zero_selection90weeks_contribute=0,summary=summary,limits=['Source panels remain already exposed; chronological heldout baseline predictions and earlier-label membership do not create fresh prospective validation or authenticate original football publication clocks.','G1 rank is probability of the unchanged baseline side being correct, not a repaired Over/Under law or EV. All base probabilities and sides stay unchanged.','G0 andG1 own selected pools can differ despite equal batchcounts; common-row paired views and own-pool effects are separate.','Rec22 unavailable base rows retain fallback=None; raw fallback_status_unknown=0 does not establish known nonfallback on these unissued queries. Technical-unavailable and learned/identity partitions remain correct; source-bound qualification must expose this scope. PT2 missing rows retainNOT_RETAINED.','Actual consumed base-feature ages are unretained. Retained role/line/probabilities are used; no new NGS study, football fit, current-source capture or production deployment.','Exact policy is tested on only2rec/1PTweeks; zero-selection90%weeks contribute0; five-week floor and source/operational/admission requirements remain unmet. No promotion is supported.'])
    (out/'INDEPENDENT_CONTEXT_RANKER_AUDIT_V1.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='summary'},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('retained',type=Path);p.add_argument('private',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.repo,a.retained,a.private,a.out)
