"""Reconstruct retained laws with independent PMF sums; inference only, no fits."""
import gzip,hashlib,json,math,pickle,sys
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.special import gammaln

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def unzip(p):return json.loads(gzip.decompress(p.read_bytes()))
def law_mean(law):
    k=law['kind']
    if k=='zero':return 0.
    if k=='bernoulli':return law['p']
    if k=='poisson':return law['mean']
    if k=='signed':return law['center']
    if k=='geometric':return law['q']/(1-law['q'])
    return .95*float(law['support']@law['weights'])+.05*law_mean(law['prior'])
def logpmf(law,x):
    k=law['kind']
    if x!=math.floor(x):return -math.inf
    if k=='zero':return 0. if x==0 else -math.inf
    if k=='bernoulli':
        p=law['p']if x==1 else 1-law['p']if x==0 else 0.;return math.log(p)if p else -math.inf
    if k=='poisson':
        m=law['mean'];return x*math.log(m)-m-math.lgamma(x+1)if m>0 and x>=0 else 0. if m==x==0 else -math.inf
    if k=='geometric':
        q=law['q'];return math.log1p(-q)+x*math.log(q)if q>0 and x>=0 else 0. if x==0 else -math.inf
    if k=='signed':
        q=law['q'];return math.log1p(-q)-math.log1p(q)+abs(x-law['center'])*math.log(q)if q>0 else 0. if x==law['center']else-math.inf
    i=np.searchsorted(law['support'],x);w=law['weights'][i]if i<len(law['weights'])and law['support'][i]==x else 0.
    return float(np.logaddexp(math.log(.95*w)if w else-math.inf,math.log(.05)+logpmf(law['prior'],x)))
def bounds(law):
    k=law['kind']
    if k=='zero':return 0,0
    if k=='bernoulli':return 0,1
    if k=='poisson':return 0,math.ceil(law['mean']+16*math.sqrt(law['mean']+1)+100)
    if k in('signed','geometric'):
        q=law['q'];radius=math.ceil(math.log(1e-17)/math.log(q))if q>0 else 0
        return (law['center']-radius,law['center']+radius)if k=='signed'else(0,radius)
    low,high=bounds(law['prior']);return min(low,int(min(law['support']))),max(high,int(max(law['support'])))
def masses(law,x):
    k=law['kind']
    if k=='zero':return (x==0).astype(float)
    if k=='bernoulli':return np.where(x==0,1-law['p'],np.where(x==1,law['p'],0.))
    if k=='poisson':
        m=law['mean']
        if m==0:return(x==0).astype(float)
        return np.exp(x*math.log(m)-m-gammaln(x+1))
    if k=='geometric':return np.where(x>=0,(1-law['q'])*law['q']**np.maximum(x,0),0.)
    if k=='signed':return (1-law['q'])/(1+law['q'])*law['q']**np.abs(x-law['center'])
    out=.05*masses(law['prior'],x);lookup={int(v):w for v,w in zip(law['support'],law['weights'])}
    return out+.95*np.asarray([lookup.get(int(v),0.)for v in x])
def summaries(law,y):
    lo,hi=bounds(law);x=np.arange(lo,hi+1,dtype=float);p=masses(law,x)
    assert np.isclose(p.sum(),1.,rtol=0,atol=5e-12)
    c=np.cumsum(p)
    result={'mean':law_mean(law),'zero_mass':math.exp(logpmf(law,0))if logpmf(law,0)>-math.inf else 0.}
    for name,q in [('q05',.05),('lower_median',.5),('q95',.95)]:result[name]=int(x[np.searchsorted(c,q)])
    result['interval90_width']=result['q95']-result['q05']
    if y is not None:
        prefix=c-p;first=np.cumsum(x*p)-x*p
        half_pair=float(p@(x*prefix-first))
        result['crps']=float(p@np.abs(x-y))-half_pair
        lp=logpmf(law,y);result['infinite_nll']=lp==-math.inf;result['nll']=None if lp==-math.inf else-lp
        result['interval90_covered']=result['q05']<=y<=result['q95']
    return result

def audit(public,private):
    protocol=json.loads((public/'FROZEN_PROTOCOL.json').read_text());run=json.loads((public/'RUN_RECEIPT.json').read_text())
    chart='chart-wave'in public.name
    law_code_sha=protocol.get('law_code_sha256',protocol.get('law_helper_sha256'))
    assert sha(ROOT/'nfl_v2/distribution_laws.py')==law_code_sha
    counts=Counter();maxdelta=0.;near_boundary=0
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=2):
        for fitfile in sorted(public.glob('*-FIT.json')):
            fit=json.loads(fitfile.read_text());slot=fit['slot'];fr=json.loads((public/(slot+'-FORECAST.json')).read_text())
            def path(d):
                base=private.with_name('distribution-wave-v1')if d.get('reused_from')else private
                p=base/d['bundle_name'];assert sha(p)==d['sha256'];return p
            descriptor=fr['packet']
            if fr.get('reused_from'):descriptor=dict(descriptor,reused_from=True)
            rs=unzip(path(descriptor))['rows'];entries=unzip(path(fit['query_features']))
            by_query={}
            for r in rs:by_query[(r['game_id'],r['player_id'],r['target'],r['population'])]=r
            model=None
            if fit['model']:
                model=pickle.loads(gzip.decompress(path(fit['model']).read_bytes()));counts['retained_models_hash_verified']+=1
            usable=[i for i,e in enumerate(entries)if not e['query']['blocked_reason']and e['query']['position']in('QB','RB','WR','TE')]
            if not usable:continue
            learned=[i for i in usable if entries[i]['features'][3]>0]
            chosen=list(dict.fromkeys(([learned[0]]if learned else[])+[usable[-1]]))
            for i in chosen:
                e=entries[i];q=e['query'];r=by_query[(q['game_id'],q['player_id'],q['target'],q['population'])];position=q['position'];prior=fit['prior_parameters'][position]
                if model is None or e['features'][3]<=0:law=prior;counts['prior_laws_checked']+=1
                else:
                    x=np.asarray([[math.nan if v is None else v for v in e['features']]],dtype=float)
                    raw=np.column_stack((np.where(np.isfinite(x),x,model.design.median),~np.isfinite(x))).astype(float)
                    design=(raw-model.design.mean)/model.design.scale if fit['family']=='regularized_glm_law'else raw
                    if fit['family']=='ordered_leaf_cdf':
                        leaves=model.estimator.apply(design)[0];weights=np.zeros(len(model.support))
                        for j,h in enumerate(model.hist):weights+=h[leaves[j]].toarray().ravel()/len(model.hist)
                        assert list(leaves)==r['law_reference']['leaf_ids'];weights/=weights.sum()
                        law=dict(kind='mixture',support=model.support,weights=weights,prior=prior)
                    elif q['target']=='anytime_td':law=dict(kind='bernoulli',p=float(model.estimator.predict_proba(design)[0,list(model.estimator.classes_).index(1.)]))
                    else:
                        v=float(model.estimator.predict(design)[0])
                        if q['target']in('pass_td','pass_cmp','pass_att','pass_int','rush_att','rec'):law=dict(kind='poisson',mean=v)
                        else:law=dict(kind='signed',center=int(np.rint(v)),q=model.scale[position]/(1+model.scale[position]))
                    counts['fitted_laws_reconstructed']+=1
                expected=summaries(law,r.get('actual_grid')if chart else r['actual']);saved=dict(r['distribution_summary'])
                if chart:
                    assert saved['grid_denominator']==50
                    for field in('mean','lower_median','q05','q95','interval90_width','crps'):
                        if saved[field]is not None:saved[field]*=50
                    for field in('lower_median','q05','q95'):
                        assert math.isclose(saved[field],round(saved[field]),rel_tol=0,abs_tol=1e-8)
                        saved[field]=int(round(saved[field]))
                for field,v in expected.items():
                    if isinstance(v,(bool,type(None))):assert v==saved[field],(slot,field)
                    elif field in('q05','q95','lower_median'):
                        # A floatingCDF exactlyat the quantile can differ byone ULP.
                        if v!=saved[field]:
                            z=np.arange(*((lambda a,b:(a,b+1))(*bounds(law))),dtype=float);cdf=float(masses(law,z[z<=saved[field]]).sum());prob={'q05':.05,'q95':.95,'lower_median':.5}[field]
                            assert abs(cdf-prob)<3e-12 and abs(v-saved[field])<=1,(slot,field,v,saved[field],cdf);near_boundary+=1
                    else:
                        delta=abs(v-saved[field]);maxdelta=max(maxdelta,delta)
                        assert math.isclose(v,saved[field],rel_tol=2e-10,abs_tol=2e-7),(slot,field,v,saved[field])
                    counts['independent_law_summary_checks']+=1
                counts['sampled_laws']+=1
    # Hand endpoint/underflow cases; no invented clipping.
    assert logpmf(dict(kind='poisson',mean=.01),400)<-3000
    assert math.isfinite(logpmf(dict(kind='poisson',mean=.01),400))
    assert summaries(dict(kind='zero'),2)['infinite_nll']
    return dict(status='PASS_RETAINED_MODEL_SAMPLE_INFERENCE_AND_INDEPENDENT_PMF_SUMS',counts=dict(counts),max_float_difference=maxdelta,near_exact_quantile_boundary_cases=near_boundary,new_fits=0,new_forecasts=0,week8_actuals_read=0,
        law_code_sha256=law_code_sha,protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),run_receipt_sha256=sha(public/'RUN_RECEIPT.json'),chart_units='grid*50 rebuilt independently; point/width/CRPS divide50, discretePMF logmass unchanged'if chart else None,scope='Allretainedmodelhashes, sampledexistingmodelinference; numericlawmean/quantiles/zeromass/CRPS via separatefinitePMFsums with omittedtailmass<1e-16, directlogmass; not a refit or complete training-row replay')

if __name__=='__main__':
    result=audit(Path(sys.argv[1]),Path(sys.argv[2]));name='CHART'if'chart-wave'in sys.argv[1]else'DISTRIBUTION';out=Path(__file__).parent/(name+'_LAW_INDEPENDENT_REVIEW.json')
    out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
