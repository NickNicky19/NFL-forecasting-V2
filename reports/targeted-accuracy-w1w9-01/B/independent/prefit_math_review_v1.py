"""Independent M2 law checks, outside NFL evaluation and author inference code."""
from __future__ import annotations
import datetime, gzip, hashlib, json, math, pathlib, time
import numpy as np
from scipy import integrate, special, stats

ROOT=pathlib.Path(__file__).resolve().parents[4]
OUT=pathlib.Path(__file__).resolve().parent

def beta_integral_cdf(k,mean,shape,m,rho):
    """Separate integral of a binomial-thinned NB, not a count-sum recursion."""
    if k<0:return 0.,0.
    if mean==0 or m==0:return 1.,0.
    if m==1:return float(stats.nbinom.cdf(k,shape,shape/(shape+mean))),0.
    if rho==0:return float(stats.nbinom.cdf(k,shape,shape/(shape+mean*m))),0.
    precision=1/rho-1;alpha=m*precision;beta=(1-m)*precision
    if precision<700:
        x,w=special.roots_jacobi(128,beta-1,alpha-1)
        q=(1+x)/2;v=stats.nbinom.cdf(k,shape,shape/(shape+mean*q))
        result=float(np.dot(w/w.sum(),v))
        xx,ww=special.roots_jacobi(256,beta-1,alpha-1)
        second=float(np.dot(ww/ww.sum(),stats.nbinom.cdf(k,shape,shape/(shape+mean*(1+xx)/2))))
        return second,abs(second-result)
    # Standardized beta quadrature avoids overflowing Jacobi normalization
    # when concentration is large. This is a validation integral only.
    sd=math.sqrt(m*(1-m)/(precision+1));lo=-m/sd;hi=(1-m)/sd
    boundaries=sorted(set([lo,hi]+[z for z in [-12.,-6.,-3.,0.,3.,6.,12.]if lo<z<hi]))
    def f(z):
        q=m+sd*z
        if q<=0 or q>=1:return 0.
        logpdf=(alpha-1)*math.log(q)+(beta-1)*math.log1p(-q)-special.betaln(alpha,beta)+math.log(sd)
        return math.exp(logpdf)*float(stats.nbinom.cdf(k,shape,shape/(shape+mean*q)))
    result=error=0.
    for a,b in zip(boundaries,boundaries[1:]):
        val,err=integrate.quad(f,a,b,epsabs=2e-12,epsrel=2e-11,limit=100)
        result+=val;error+=err
    return result,error

def count_sum(mean,shape,m,rho,tol=1e-13):
    if mean==0:return np.asarray([1.]),0.,1
    stop=int(stats.nbinom.isf(tol,shape,shape/(shape+mean)))
    weights=stats.nbinom.pmf(np.arange(stop+1),shape,shape/(shape+mean))
    out=np.zeros(stop+1)
    for a,wa in enumerate(weights):
        if m==0:p=np.r_[1.,np.zeros(a)]
        elif m==1:p=np.r_[np.zeros(a),1.]
        elif rho==0:p=stats.binom.pmf(np.arange(a+1),a,m)
        else:
            concentration=1/rho-1
            p=stats.betabinom.pmf(np.arange(a+1),a,m*concentration,(1-m)*concentration)
        out[:a+1]+=wa*p
    return out,float(stats.nbinom.sf(stop,shape,shape/(shape+mean))),stop+1

def main():
    start=time.process_time();cases=[
      dict(id='KNOWN_ZERO_EXPOSURE',mean=0.,shape=20.,m=.6,rho=.05),
      dict(id='BINOMIAL_LIMIT',mean=35.,shape=20.,m=.67,rho=0.),
      dict(id='ORDINARY_OVERDISPERSED',mean=35.,shape=20.,m=.67,rho=.03),
      dict(id='HEAVY_EXPOSURE_TAIL',mean=10.,shape=.5,m=.4,rho=.5),
      dict(id='HIGH_COMPLETION_TAIL',mean=55.,shape=1.,m=.9,rho=.01),
      dict(id='ZERO_CONVERSION_LIMIT',mean=35.,shape=20.,m=0.,rho=.3),
      dict(id='CERTAIN_CONVERSION_LIMIT',mean=35.,shape=20.,m=1.,rho=.3),
      dict(id='HIGH_CONCENTRATION',mean=35.,shape=20.,m=.67,rho=1e-4)]
    checks=0;records=[]
    for c in cases:
        pmf,tail,n=count_sum(**{k:c[k]for k in ['mean','shape','m','rho']})
        assert np.isfinite(pmf).all()and np.min(pmf)>=0
        assert abs(pmf.sum()+tail-1)<3e-9
        cdf=pmf.cumsum();assert np.all(np.diff(cdf)>=-1e-14)
        maxdiff=maxerror=0.
        for k in [0,1,10,20,30,40,60,100]:
            integral,error=beta_integral_cdf(k,**{z:c[z]for z in ['mean','shape','m','rho']})
            value=float(cdf[min(k,len(cdf)-1)])
            maxdiff=max(maxdiff,abs(value-integral));maxerror=max(maxerror,error)
            assert abs(value-integral)<max(3e-8,8*error+tail)
            checks+=1
        support=np.arange(len(pmf));mu=float(np.dot(support,pmf));m2=float(np.dot(support**2,pmf))
        expected=c['mean']*c['m']
        theta2=c['m']**2+c['rho']*c['m']*(1-c['m'])
        variance=expected+(c['mean']**2+c['mean']**2/c['shape'])*theta2-expected**2
        assert abs(mu-expected)<2e-7 and abs(m2-mu*mu-variance)<3e-4
        checks+=5
        records.append(dict(c,total_mass=float(pmf.sum()),omitted_attempt_mass=tail,states=n,
          mean=mu,expected_mean=expected,variance=m2-mu*mu,expected_variance=variance,
          largest_CDF_difference=maxdiff,integral_error_bound=maxerror))
    result={'id':'B_M2_INDEPENDENT_PREFIT_MATH_FIXTURES_v1','state':'PASS','at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'independent_calculations':'Finite A-sum beta-binomial versus separate beta integral of binomial-thinned NB; no author law/scorer imported.',
      'checks':checks,'cases':records,'CPU_seconds':time.process_time()-start,'NFL_fits':0,'NFL_samples':0,
      'source_read_attempts':0,'author_law_verified':False,'limits':'This proves the declared mathematical family/check implementation, not any NFL fit, estimate, source timing or predictive improvement.',
      'code_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
    (OUT/'PREFIT_MATH_FIXTURES_V1.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'state':'PASS','checks':checks,'CPU_seconds':result['CPU_seconds'],'max_CDF_difference':max(r['largest_CDF_difference']for r in records)}))

if __name__=='__main__':main()
