"""Independent software checks for M2 before NFL optimization; no fit calls."""
from __future__ import annotations
import copy, datetime, gzip, hashlib, json, math, pathlib, sys, time
import numpy as np
from scipy import special, stats

ROOT=pathlib.Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from nfl_v2 import targeted_qb_m2 as author, player_context_matchup as ctx
from tools import run_targeted_qb_m2 as driver
from prefit_math_review_v1 import beta_integral_cdf

OUT=pathlib.Path(__file__).resolve().parent

def enc(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def independent_z(q,rows):
    prior=[r for r in rows if r['physical_participation']and r['target_parity']and r['available']<q['kickoff']]
    own=sorted([r for r in prior if r['player_id']==q['player_id']],key=lambda r:(r['kickoff'],r['game_id']))[-8:]
    total=np.asarray([r['context_attempts']for r in prior],float).sum(axis=0)if prior else np.zeros(25)
    owncounts=np.asarray([r['context_attempts']for r in own],float).sum(axis=0)if own else np.zeros(25)
    league=(total+1)/(total.sum()+25);mix=(owncounts+20*league)/(owncounts.sum()+20)
    entropy=-sum(x*math.log(x)for x in mix if x>0)/math.log(25)
    dest=np.asarray([sum(r.get('pass_destination_counts',{}).get(k,0)for r in own)for k in ['left','middle','right']],float)
    known=dest.sum();de=-sum((x/known)*math.log(x/known)for x in dest if x>0)/math.log(3)if known else 0.
    numerator=denominator=0.
    for r in own:
        v=r['field_context']['ydstogo']
        if v['mean']is not None and v['n']>0:numerator+=v['mean']*v['n'];denominator+=v['n']
    distance=numerator/denominator if denominator else None
    z=np.asarray([1.,entropy,de,0.if distance is None else min(2.,max(0.,distance/20)),
       min(2.,math.log1p(owncounts.sum())/math.log(1000)),float(known==0),float(distance is None)])
    return z,{'known_destination':float(known),'known_distance':int(denominator),'distance':distance}

def future_mutated(rows,cutoff):
    out=copy.deepcopy(rows)
    for r in out:
        if r['available']>=cutoff:
            n=int(r['official_attempts'])+113
            r['attempts']=r['official_attempts']=n;r['completions']=r['official_completions']=0
            r['context_attempts']=[n]+[0]*24;r['context_completions']=[0]*25
            r['pass_destination_counts']={'left':n,'middle':0,'right':0}
            r['field_context']['ydstogo']={'mean':99.,'n':n}
    return out

def independent_objective(beta,z,n,c,m):
    k=.05+9999.95/(1+np.exp(-(z@beta)))
    logp=stats.betabinom.logpmf(c,n,m*k,(1-m)*k)
    center=np.r_[special.logit((20-.05)/(10000-.05)),np.zeros(6)]
    return float(-logp.sum()+.5*np.sum(np.r_[1.,np.full(6,10.)]*(beta-center)**2))

def main():
    start=time.process_time();checks=0;results={};problems=[]
    def check(ok,label):
        nonlocal checks
        checks+=1
        if not bool(ok):problems.append(label)
    params=[(0.,20.,.6,20.),(35.,20.,.67,20.),(10.,.5,.4,1.),(55.,1.,.9,99.),
            (35.,20.,0.,20.),(35.,20.,1.,20.),(35.,20.,.67,9999.)]
    lawchecks=[]
    for M,r,m,k in params:
        law=author.IntegratedBetaBinomial(M,r,m,k);law._build()
        check(np.isfinite(law._pmf).all()and np.min(law._pmf)>=0,'Finite nonnegative PMF')
        check(abs(law._pmf.sum()+law.omitted_attempt_tail-1)<1e-8,'Total mass plus explicit attempt tail')
        check(np.diff(law._cdf).min(initial=0)>=-1e-14,'CDF monotonicity')
        diffs=[]
        for x in [-1,0,1,10,20,30,40,60,100]:
            expected,err=beta_integral_cdf(x,M,r,m,1/(k+1))
            actual=law.cdf(x);diffs.append(abs(actual-expected))
            check(abs(actual-expected)<max(3e-8,err*8+law.tail_tol),'Author CDF versus independent beta integral')
            fa=1.if not M and x>=0 else float(stats.nbinom.cdf(math.floor(x),r,r/(r+M)))if M else 0.
            check(actual+law.tail_tol>=fa,'Completion stochastic ordering below attempts')
        for a,c in [(0,0),(5,0),(5,3),(5,5),(5,6),(-1,0),(5,-1)]:
            val=law.joint_logpmf(a,c)
            if c>a or min(a,c)<0:check(val==-math.inf,'Joint impossible support zero')
            elif M==0:check(val==(0.if a==c==0 else -math.inf),'Zero attempt joint law')
            else:
                lp=stats.nbinom.logpmf(a,r,r/(r+M))
                if m==0:lp=lp if c==0 else -math.inf
                elif m==1:lp=lp if c==a else -math.inf
                else:lp+=stats.betabinom.logpmf(c,a,m*k,(1-m)*k)
                check(val==lp or abs(val-lp)<1e-10,'Joint factorization')
        for line in [-.5,0.,.5,10.,10.5,35.]:
            probs=ctx.exact_probabilities(law,line)
            check(abs(sum(probs.values())-1)<1e-12 and min(probs.values())>=-1e-12,'Exact side/push orientation')
            check(abs(probs['push']-(law.pmf(line)if line==int(line)and line>=0 else 0.))<2e-9,'Integer push mass')
        check(abs(law.mean-M*m)<1e-12,'Mean identity')
        theta2=m*m+m*(1-m)/(k+1)
        check(abs(law.variance-(M*m+(M*M+M*M/r)*theta2-(M*m)**2))<1e-9,'Variance identity')
        if M and m:
            beyond=law.grid_max+5
            check(math.isfinite(law.logpmf(beyond)),'Unbounded tail beyond numerical grid')
            check(law.cdf(math.inf)==1.,'CDF infinity')
        check(law.cdf(law.quantile(.5))>=.5-law.tail_tol,'Median CDF orientation')
        restored=author.restore_law(json.loads(json.dumps(law.parameters())))
        check(abs(restored.mean-law.mean)<1e-12 and abs(restored.cdf(20)-law.cdf(20))<1e-12,'Law JSON roundtrip')
        lawchecks.append({'attempt_mean':M,'attempt_shape':r,'conversion_mean':m,'precision':k,'largest_CDF_difference':max(diffs),
          'normalization_error':abs(float(law._pmf.sum())+law.omitted_attempt_tail-1),'attempt_grid':law.grid_max,'omitted_attempt_mass':law.omitted_attempt_tail})
    results['law_checks']=lawchecks
    # Seven-dimensional analytic gradient versus a separate likelihood and finite difference.
    rng=np.random.default_rng(2301);z=np.c_[np.ones(60),rng.uniform(0,1,(60,6))]
    n=rng.integers(0,55,60);m=rng.uniform(.15,.9,60);c=rng.binomial(n,m)
    beta=author.prior_beta()+np.asarray([.1,.03,-.07,.08,.01,-.03,.1])
    value,grad=author.DispersionModel.objective(beta,z,n,c,m)
    check(abs(value-independent_objective(beta,z,n,c,m))<1e-8,'Independent penalized BB likelihood')
    numerical=[]
    for j in range(7):
        hi=beta.copy();lo=beta.copy();hi[j]+=1e-5;lo[j]-=1e-5
        numerical.append((independent_objective(hi,z,n,c,m)-independent_objective(lo,z,n,c,m))/2e-5)
        check(abs(numerical[-1]-grad[j])<3e-5,'Gradient coefficient'+str(j))
    results['gradient']={'analytic':grad.tolist(),'finite_difference':numerical,'largest_difference':float(np.max(np.abs(np.asarray(numerical)-grad)))}
    model=author.DispersionModel(beta)
    restored=author.DispersionModel.restore(json.loads(json.dumps(model.payload())))
    batch=model.precision(z);single=np.asarray([restored.precision(x)for x in z])
    check(np.array_equal(batch,single),'Batch/single precision identity')
    order=rng.permutation(len(z));check(np.array_equal(model.precision(z[order])[np.argsort(order)],batch),'Shuffled row identity')
    payload=model.payload();payload['feature_order']=list(reversed(payload['feature_order']))
    try:author.DispersionModel.restore(payload);rejected=False
    except ValueError:rejected=True
    check(rejected,'Feature-order enforcement')
    # Fresh source reconstructions, not reused feature caches.
    source=driver.INPUTS;rows=ctx.load_inputs(source);history=ctx.ContextHistory(rows,8,20.)
    caseplan=json.loads((OUT/'PREFIT_DESIGN_REVIEW_V1.json').read_text())
    by={(r['game_id'],r['player_id']):r for r in rows};traces=[]
    for case in caseplan['representative_cases']:
        if 'game_id'not in case:continue
        q=by[case['game_id'],case['player_id']];want,trace=independent_z(q,rows);actual,observed=author.dispersion_features(q,history)
        check(np.allclose(want,actual,rtol=0,atol=2e-14),'Independent feature reconstruction '+case['case'])
        check(trace['known_destination']==observed['known_destination_denominator'],'Known destination denominator')
        check(trace['known_distance']==observed['known_distance_denominator'],'Known distance denominator')
        changed=future_mutated(rows,q['kickoff']);fresh=ctx.ContextHistory(changed,8,20.)
        # Remove target outcomes and context fields from legitimate query input.
        minimal={k:q[k]for k in ['game_id','player_id','season','week','team','opponent','kickoff']}
        after,_=author.dispersion_features(minimal,fresh)
        check(np.array_equal(actual,after),'Target/future outcomes cannot alter earlier feature '+case['case'])
        check(observed['latest_own_source']is None or observed['latest_own_source']<q['kickoff'],'Strict source admission')
        traces.append({'case':case['case'],'game_id':q['game_id'],'player_id':q['player_id'],'features':actual.tolist(),'trace':observed})
    # Earlier OOF design must survive adding/changing future labels and future saved means.
    qs=[q for q in rows if(q['season'],q['week'])==(2026,5)];cutoff=min(q['kickoff']for q in qs)
    parents,_=driver.old_parents();mutated=future_mutated(rows,cutoff);changed_history=ctx.ContextHistory(mutated,8,20.)
    changed_parents=copy.deepcopy(parents)
    for method,values in changed_parents.items():
        for key,v in values.items():
            source_row=by.get(key)
            if source_row is not None and source_row['available']>=cutoff:
                v['actual']=999;v['components']['integrated_completion_probability']=.999
    chronology=[]
    for parent in ['P2','C1','C2']:
        before=driver.dispersion_training(parent,parents,rows,history,cutoff,2026)
        after=driver.dispersion_training(parent,changed_parents,mutated,changed_history,cutoff,2026)
        check(enc(before)==enc(after),'OOF eligible design futuremutation '+parent)
        check(all(r['available']<cutoff and r['parent_fit_cutoff']<=r['kickoff']for r in before),'OOF fitted and label chronology '+parent)
        chronology.append({'parent':parent,'rows':len(before),'design_sha256':hashlib.sha256(enc(before)).hexdigest(),
          'latest_admitted_label':max(r['available']for r in before),'origin_cutoff':cutoff,'identical_after_future_mutation':True})
    results['representative_feature_traces']=traces;results['OOF_chronology']=chronology
    result={'id':'B_M2_INDEPENDENT_AUTHOR_PREFIT_SOFTWARE_v1','at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'state':'PASS'if not problems else'FAIL','checks':checks,'problems':problems,'results':results,
      'code_sha256':{f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest()for f in ['nfl_v2/targeted_qb_m2.py','tools/run_targeted_qb_m2.py']},
      'CPU_seconds':time.process_time()-start,'actual_optimizer_calls':0,'NFL_fits':0,'source_read_attempts':0,
      'limits':['No private A offers or authentic historical clocks inspected.','No NFL model fit or predictive improvement verified.','Direct-model vector feature order is code-controlled; low-level forest restorer checks width, not arbitrary same-width semantic permutations.','Author normalization guard tolerance is1e-7; these independent checked fixtures bound observed error separately.']}
    (OUT/'AUTHOR_PREFIT_SOFTWARE_CHECKS_V1.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'state':result['state'],'checks':checks,'problems':problems,'CPU_seconds':result['CPU_seconds']}))
    if problems:raise SystemExit(1)

if __name__=='__main__':main()
