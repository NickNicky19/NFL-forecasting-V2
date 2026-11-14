"""Separate scalar MAP/chronological policy arithmetic; no producer fit/scorer imports."""
import argparse,collections,gzip,hashlib,json,math,statistics,sys
from datetime import datetime,timezone
from pathlib import Path

VERSION='ABC-PREDICTIVE-IMPROVEMENT-01-B-INTERCEPT-v1'
def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def close(a,b,tol=1e-10):return a==b or(a is not None and b is not None and abs(a-b)<max(tol,abs(b)*1e-10))
def sigmoid(x):
    if x>=0:return 1/(1+math.exp(-x))
    v=math.exp(x);return v/(1+v)
def shift(x,alpha):return x if x in(0.,1.)else sigmoid(math.log(x/(1-x))-alpha)
def repaired(p,alpha):
    if p is None:return None
    lo=shift(p['under'],alpha);hi=shift(p['under']+p['push'],alpha);return dict(under=lo,push=max(0.,hi-lo),over=1-hi)
def side(p):return None if p is None or abs(p['over']-p['under'])<=1e-12 else'over'if p['over']>p['under']else'under'
def conf(p):return max(p['over'],p['under'])if p is not None else None
def eligible(rows,t):return[r for r in rows if r['label_available']<t and r['probabilities']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'and r['line']%1==.5]
def map_solution(pool,t):
    rr=eligible(pool,t);game=collections.Counter(r['game_id']for r in rr);positive=sum(r['actual']>r['line']for r in rr)
    result=dict(alpha=0.,state='IDENTITY_INSUFFICIENT_EARLIER_SUPPORT',fit_performed=False,n=len(rr),games=len(game),positive=positive,negative=len(rr)-positive,membership_sha256=hashlib.sha256(json.dumps(sorted(r['offer_id']for r in rr),separators=(',',':')).encode()).hexdigest(),latest_label_available=max((r['label_available']for r in rr),default=None))
    if len(rr)<20 or len(game)<5 or min(positive,len(rr)-positive)<3:return result
    if any((r['probabilities']['over']==0 and r['actual']>r['line'])or(r['probabilities']['over']==1 and r['actual']<=r['line'])for r in rr):result['state']='IDENTITY_IRREPARABLE_INFINITE_TRAINING_LOGLOSS';return result
    def gradient(a):
        terms=[]
        for r in rr:
            p=r['probabilities']['over'];q=p if p in(0.,1.)else sigmoid(math.log(p/(1-p))+a);terms.append((q-int(r['actual']>r['line']))/game[r['game_id']])
        return math.fsum(terms)+4*a
    lo,hi=-1.5,1.5
    if gradient(lo)>=0:alpha=lo
    elif gradient(hi)<=0:alpha=hi
    else:
        for _ in range(90):
            mid=(lo+hi)/2
            if gradient(mid)>0:hi=mid
            else:lo=mid
        alpha=(lo+hi)/2
    result.update(alpha=alpha,state='FITTED_GAME_WEIGHTED_INTERCEPT_MAP',fit_performed=True,gradient=gradient(alpha));return result

def gate(history,t):
    values=[conf(r['probabilities'])for r in history if r['decision_epoch']<t and r['probabilities']is not None]
    return max(.6,statistics.median(values))if len(values)>=20 else .6

def state(r,s):
    if r['probabilities']is None:return'UNAVAILABLE_FORECAST'
    if s is None:return'ABSTAIN'
    if r['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL':return'UNKNOWN_PARTICIPATION'
    if r['actual']is None:return'MISSING_ACTUAL'
    return'PUSH'if r['actual']==r['line']else'WIN'if((r['actual']>r['line'])==(s=='over'))else'LOSS'
def proper(rr):
    valid=[r for r in rr if r['probabilities']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];bs=[];ls=[]
    for r in valid:
        event='over'if r['actual']>r['line']else'under'if r['actual']<r['line']else'push';p=r['probabilities'];bs.append(.5*math.fsum((p[k]-int(k==event))**2 for k in('over','under','push')));ls.append(-math.log(p[event])if p[event]>0 else math.inf)
    return dict(n=len(valid),brier=math.fsum(bs)/len(valid)if valid else None,log_loss=math.inf if any(math.isinf(x)for x in ls)else math.fsum(ls)/len(valid)if valid else None,infinite_log_losses=sum(math.isinf(x)for x in ls))

def run(repo,private,out):
    binding=read(out/'CURRENT_EXECUTION_BINDING.json');protocol=read(out/binding['protocol']);data=read(private/binding['inputs']);actual=read(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz');assert sha(private/binding['inputs'])==binding['input_sha256'];assert sha(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz')==read(out/'MODEL_MANIFEST.json')['private_models_rows_sha256'];assert sha(repo/'nfl_v2/exact_line_repair.py')==protocol['mechanism_sha256'];assert sha(repo/'tools/run_b_predictive_improvement_01.py')==protocol['code_sha256']
    models=actual['models'];reproduced={};maximum_alpha_difference=0.;fitted=0;future_checks=0
    sys.path.insert(0,str(repo));from nfl_v2 import exact_line_repair as actual_module
    for mid,m in models.items():
        pool=data[m['target']]['calibration'];expected=map_solution(pool,m['cutoff_epoch']);ids=sorted(r['offer_id']for r in eligible(pool,m['cutoff_epoch']));assert mid==digest([m['target'],ids])==m['model_id'];assert m['n']==expected['n']and m['games']==expected['games']and m['positive']==expected['positive']and m['negative']==expected['negative']and m['membership_sha256']==expected['membership_sha256']and m['latest_label_available']==expected['latest_label_available']and m['state']==expected['state']and m['fit_performed']==expected['fit_performed'];delta=abs(m['alpha']-expected['alpha']);maximum_alpha_difference=max(maximum_alpha_difference,delta);assert delta<1e-10
        assert datetime.fromisoformat(m['actual_computed_at_utc'])>=datetime.fromisoformat(protocol['at_utc']);fitted+=int(m['fit_performed']);reproduced[mid]=expected
        changed=[dict(r,actual=999,probabilities=dict(over=.99,under=.01,push=0.))if r['label_available']>=m['cutoff_epoch']else r for r in pool]
        assert [r['offer_id']for r in actual_module.eligible_training(changed,m['cutoff_epoch'])]==[r['offer_id']for r in actual_module.eligible_training(pool,m['cutoff_epoch'])]
        assert map_solution(changed,m['cutoff_epoch'])['alpha']==expected['alpha'];future_checks+=1
    assert len(models)==11 and fitted==6
    def used_model(target,t):
        mid=digest([target,sorted(r['offer_id']for r in eligible(data[target]['calibration'],t))]);assert mid in reproduced;return mid,reproduced[mid]
    groups=collections.defaultdict(list);usage=[];mutations=0
    for target in('pass_td','rec'):
        d=data[target];history={0:[],1:[]}
        if target=='pass_td':
            for r in sorted(d['gate_oof'],key=lambda x:(x['decision_epoch'],x['offer_id'])):
                mid,m=used_model(target,r['decision_epoch']);history[0].append(r);history[1].append(dict(r,probabilities=repaired(r['probabilities'],m['alpha'])))
            fixedid,fixed=used_model(target,d['calibration_freeze'])
        batches=collections.defaultdict(list)
        for r in d['evaluation']:batches[r['decision_epoch']].append(r)
        slots=collections.Counter()
        for t,batch in sorted(batches.items()):
            mid,m=(fixedid,fixed)if target=='pass_td'else used_model(target,t);frozen=d['calibration_freeze']if target=='pass_td'else t;thresholds={arm:gate(history[arm],frozen)for arm in(0,1)};arms={0:[dict(r,repair_state='UNCHANGED_BASELINE',repair_model_id=None)for r in batch],1:[dict(r,probabilities=repaired(r['probabilities'],m['alpha']),repair_state=m['state'],repair_model_id=mid)for r in batch]}
            for arm in(0,1):
                fake=dict(batch[0],decision_epoch=frozen+1,actual=999,probabilities=dict(over=1.,under=0.,push=0.));assert close(actual_module.gate_threshold(history[arm]+[fake],frozen),thresholds[arm]);mutations+=1
            qualified={arm:sorted([r for r in rr if r['probabilities']is not None and conf(r['probabilities'])>=thresholds[arm]],key=lambda r:(-conf(r['probabilities']),r['offer_id']))for arm,rr in arms.items()};K=min(math.ceil(.5*sum(r['probabilities']is not None for r in batch)),len(qualified[0]),len(qualified[1]));members={arm:{r['offer_id']for r in qualified[arm][:K]}for arm in(0,1)}
            usage.append(dict(target=target,decision_epoch=t,simulated_calibration_cutoff=frozen,model_id=mid,training_latest_available=m['latest_label_available'],gate_thresholds=thresholds,matched_K=K,batch_offers=len(batch),model_state=m['state']))
            for arm,rr in arms.items():
                for policy in ['ALL','B2_MATCHED_EARLIER_CONFIDENCE','CONF_0.60','CONF_0.70','CONF_0.80','CONF_0.90']+[f'ROLLING_K{k}_{s}'for k in(6,10,20)for s in('Combined','over','under')]:
                    picked=None
                    if policy.startswith('ROLLING_K'):
                        part,subside=policy.split('_')[1:];cap=int(part[1:]);candidates=sorted([r for r in rr if r['probabilities']is not None and conf(r['probabilities'])>=.6 and(subside=='Combined'or side(r['probabilities'])==subside)],key=lambda r:(-conf(r['probabilities']),r['offer_id']));key=arm,rr[0]['week'],policy;picked={r['offer_id']for r in candidates[:max(0,cap-slots[key])]};slots[key]+=len(picked)
                    for r in rr:
                        s=side(r['probabilities']);keep=s is not None
                        if policy=='B2_MATCHED_EARLIER_CONFIDENCE':keep=r['offer_id']in members[arm]
                        elif policy.startswith('CONF_'):keep=keep and conf(r['probabilities'])>=float(policy.split('_')[1])
                        elif picked is not None:keep=r['offer_id']in picked
                        chosen=s if keep else None;q=dict(r,chosen=chosen,state=state(r,chosen),selection_policy=policy,method_key=f'B::{VERSION}::{target}::B{arm}',gate_threshold=thresholds[arm]if policy=='B2_MATCHED_EARLIER_CONFIDENCE'else None);groups[target,arm,policy].append(q)
            if target=='rec':
                for arm in(0,1):history[arm]+=arms[arm]
        for cid in('ALWAYS_OVER','ALWAYS_UNDER','EARLIER_SOURCE_PRIOR'):
            for r in d['prior']if cid=='EARLIER_SOURCE_PRIOR'else d['evaluation']:
                pp=r['probabilities']if cid=='EARLIER_SOURCE_PRIOR'else dict(over=.5,under=.5,push=0.);s=side(pp)if cid=='EARLIER_SOURCE_PRIOR'else'over'if cid=='ALWAYS_OVER'else'under';q=dict(r,probabilities=pp,chosen=s);q['state']=state(q,s);groups[target,cid,cid].append(q)
    stored_usage=read(out/'FIT_USAGE_AND_CUTOFFS.json');assert len(usage)==len(stored_usage)
    for a,b in zip(usage,stored_usage):
        for k in('target','decision_epoch','simulated_calibration_cutoff','model_id','training_latest_available','matched_K','batch_offers','model_state'):assert a[k]==b[k]
        for arm in(0,1):assert close(a['gate_thresholds'][arm],b['gate_thresholds'][str(arm)])
    expected_rows={}
    for(target,arm,policy),rr in groups.items():
        if not isinstance(arm,int):continue
        for r in rr:expected_rows[target,arm,policy,r['offer_id']]=r
    assert len(expected_rows)==len(actual['rows'])==11700
    for r in actual['rows']:
        arm=int(r['method_key'][-1]);q=expected_rows[r['target'],arm,r['selection_policy'],r['offer_id']]
        assert r['selected_side']==q['chosen']and r['statistical_state']==q['state']and r['repair_model_id']==q['repair_model_id']and r['repair_state']==q['repair_state'];assert r['prediction']==q['prediction']and r['actual']==q['actual']and r['line']==q['line']and r['decision_epoch']==q['decision_epoch'];assert close(r['gate_threshold'],q['gate_threshold'])
        if q['probabilities']is None:assert r['probabilities']is None
        else:assert all(close(r['probabilities'][k],q['probabilities'][k])for k in('under','push','over'))and abs(sum(r['probabilities'].values())-1)<1e-12
    scores=read(out/'SCORES.json');sv=[s for s in scores if s['record_kind']=='prop_selection_evaluation'];pv=[s for s in scores if s['record_kind']=='prop_threshold_probability_evaluation'];assert len(sv)==396 and len(pv)==8
    def score_group(s):
        suffix=s['procedure_id'].split('::')[-1];arm=int(suffix[-1])if suffix in('B0','B1')else suffix;policy=s['strategy']if isinstance(arm,int)else arm
        return[r for r in groups[s['target'],arm,policy]if s['week']=='ALL'or r['week']==int(s['week'])]
    for s in sv:
        pool=score_group(s);rr=[r for r in pool if r['chosen']is not None and(s['side']=='Combined'or r['chosen']==s['side'])];c=collections.Counter(r['state']for r in rr);m=s['selection_metrics'];assert(s['forecast_rows'],s['n'],m['WIN'],m['LOSS'])==(len(rr),c['WIN']+c['LOSS'],c['WIN'],c['LOSS']);assert m['selection_pool_count']==len(pool)and m['hit_rate']==(c['WIN']/(c['WIN']+c['LOSS'])if c['WIN']+c['LOSS']else None)
        assert m['technical_unavailable']==sum(r['state']=='UNAVAILABLE_FORECAST'for r in pool)and m['admitted_rule_abstentions']==sum(r['state']=='ABSTAIN'for r in pool)
        for k,v in m['status_counts'].items():assert v==c[k]
        if s['procedure_id'].endswith(('::B0','::B1')):
            pm=proper(rr)
            for k in('n','brier','log_loss','infinite_log_losses'):
                value=m['probability_scores'][k];value=math.inf if value=='Infinity'else value;assert close(pm[k],value)
            assert m['repair_identity_fallback_rows']==sum(r['probabilities']is not None and r['repair_state'].startswith('IDENTITY')for r in pool)
        numerical=[r for r in rr if r['prediction']is not None and r['actual']is not None and r['state']in('WIN','LOSS','PUSH')]
        mae=math.fsum(abs(r['prediction']-r['actual'])for r in numerical)/len(numerical)if numerical else None;assert close(s['mae'],mae)
    for s in pv:
        arm=int(s['procedure_id'][-1]);pool=[r for r in groups[s['target'],arm,'ALL']if s['week']=='ALL'or r['week']==int(s['week'])];m=proper(pool);assert s['forecast_rows']==len(pool)
        for k in('n','brier','log_loss','infinite_log_losses'):
            value=s[k];value=math.inf if value=='Infinity'else value;assert close(m[k],value)
    # Explicit side buckets and per-batch matched-count and greedy-quota invariants.
    triads=collections.defaultdict(dict)
    for s in sv:triads[s['procedure_id'],s['strategy'],s['target'],str(s['week'])][s['side']]=s
    for v in triads.values():
        assert set(v)=={'over','under','Combined'}
        for k in('WIN','LOSS','PUSH'):assert v['over']['selection_metrics'][k]+v['under']['selection_metrics'][k]==v['Combined']['selection_metrics'][k]
        assert v['over']['n']+v['under']['n']==v['Combined']['n']and v['over']['forecast_rows']+v['under']['forecast_rows']==v['Combined']['forecast_rows']
    for u in usage:
        chosen=[]
        for arm in(0,1):chosen.append(sum(r['chosen']is not None for r in groups[u['target'],arm,'B2_MATCHED_EARLIER_CONFIDENCE']if r['decision_epoch']==u['decision_epoch']))
        assert chosen==[u['matched_K']]*2
    paired=read(out/'PAIRED_COMPARISONS.json')
    for p in paired:
        target=p['target'];policy=p['scope'];wk=p['week_view'];suffix=p['procedure_id'].split('::')[-1];arm=int(suffix[-1]);candidate=[r for r in groups[target,arm,policy if policy!='FULL_BOARD_COMMON_DECIDED'else'ALL']if wk=='ALL'or r['week']==int(wk)];control_key=(target,0,policy)if p['control_id']=='UNCHANGED_B0'else(target,p['control_id'],p['control_id']);controls={r['offer_id']:r for r in groups[control_key]};common=[(r,controls[r['offer_id']])for r in candidate if r['state']in('WIN','LOSS')and controls[r['offer_id']]['state']in('WIN','LOSS')];aw=sum(a['state']=='WIN'for a,b in common);bw=sum(b['state']=='WIN'for a,b in common);assert(len(common),aw,bw,aw-bw)==(p['common_decided'],p['candidate_wins'],p['control_wins'],p['win_difference'])
        game=collections.defaultdict(list)
        for a,b in common:game[a['game_id']].append(int(a['state']=='LOSS')-int(b['state']=='LOSS'))
        if common:
            delta=sum(map(sum,game.values()))/len(common);assert close(delta,p['uncertainty']['delta'])
            if len(game)>=8:
                se=math.sqrt(len(game)/(len(game)-1)*sum((sum(v)-len(v)*delta)**2 for v in game.values()))/len(common);assert close(se,p['uncertainty']['game_cluster_sensitivity_se'])
    summary=[]
    for target in('rec','pass_td'):
        for arm in(0,1):
            rr=groups[target,arm,'ALL'];pm=proper(rr);selected=[r for r in rr if r['chosen']is not None];c=collections.Counter(r['state']for r in selected);summary.append(dict(target=target,arm=arm,eligible=len(rr),selected=len(selected),wins=c['WIN'],losses=c['LOSS'],decided=c['WIN']+c['LOSS'],brier=pm['brier'],log_loss=pm['log_loss']))
    result=dict(state='PASS_INDEPENDENT_MAP_PREFIX_AND_POLICY_REPRODUCTION',at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=binding['protocol_sha256'],input_sha256=binding['input_sha256'],score_sha256=sha(out/'SCORES.json'),model_rows_sha256=sha(private/'CALIBRATOR_MODELS_AND_ROWS.json.gz'),models_checked=len(models),fitted_scalar_coefficients_independently_reproduced=fitted,maximum_alpha_absolute_difference=maximum_alpha_difference,coefficient_method='Independent90step convex-gradient bisection with game weights andN(0,.5^2); did not call producer mechanism.fit or scorer.',future_label_probability_prefix_mutation_checks=future_checks,future_confidence_gate_mutation_checks=mutations,base_fit_or_inference_calls=0,retained_policy_rows_verified=11700,side_views_verified=396,proper_views_verified=8,side_triads_verified=len(triads),paired_contrasts_verified=len(paired),actual_batch_fit_and_gate_usage_verified=len(usage),fixed_confidence_policies=[.6,.7,.8,.9],rolling_K_policies=[6,10,20],summary=summary,limits=['Source panels, confidencegates and studychoice are research-exposed; no freshholdout or originalB1issuance.','Crec single-line directevents do not authenticate a completeCDF; PT historical-to-originalcapture transfer remains explicit.','PTmean is unchanged B0ancillary output, including any inherited control MAE attribution; it is not a new repaired/control pointforecast.','Full-board properneutral/prior controls require the separatelybound reference supplement.','No privateparameter values or restricted player-level records published.'])
    (out/'INDEPENDENT_POSTRUN_CALIBRATION_AND_POLICIES_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('private',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.repo,a.private,a.out)
