"""Discrete signed/count laws for new reconstructed distribution controls.

Original V2 arithmetic; no source access or fitting on import. Count Poisson is
an explicit generative assumption, independent of any fitting-objective name.
"""
from __future__ import annotations
import math
import numpy as np
from scipy import special, stats


class Law:
    def __init__(self, kind, *, mean=None, center=0, q=0., p=.5, support=None, weights=None, prior=None, mixture=.05):
        self.kind=kind;self.mu=mean;self.center=int(center);self.q=float(q);self.p=float(p)
        self.support=None if support is None else np.asarray(support,dtype=float)
        self.weights=None if weights is None else np.asarray(weights,dtype=float)
        self.prior=prior;self.b=float(mixture)
        if kind=='mixture':
            if len(self.support)!=len(self.weights) or np.any(np.diff(self.support)<=0) or not np.isfinite(self.weights).all() or np.any(self.weights<0) or not math.isclose(float(self.weights.sum()),1.,abs_tol=1e-10):raise ValueError('invalid empirical law')
            self.weights=self.weights/self.weights.sum()
        if kind in ('geometric','signed') and not 0<=self.q<1:raise ValueError('invalid geometric parameter')
        if kind=='bernoulli' and not 0<=self.p<=1:raise ValueError('invalid Bernoulli')
        if kind=='poisson' and (mean is None or not math.isfinite(mean) or mean<0):raise ValueError('invalid Poisson mean')

    @property
    def mean(self):
        if self.kind=='zero':return 0.
        if self.kind=='bernoulli':return self.p
        if self.kind=='poisson':return float(self.mu)
        if self.kind=='geometric':return self.q/(1-self.q)
        if self.kind=='signed':return float(self.center)
        return (1-self.b)*float(self.weights@self.support)+self.b*self.prior.mean

    def cdf(self,x):
        x=math.floor(x)
        if self.kind=='zero':return float(x>=0)
        if self.kind=='bernoulli':return 0. if x<0 else 1-self.p if x<1 else 1.
        if self.kind=='poisson':return float(stats.poisson.cdf(x,self.mu))
        if self.kind=='geometric':return 0. if x<0 else 1-self.q**(x+1)
        if self.kind=='signed':
            d=x-self.center
            return self.q**(-d)/(1+self.q) if d<0 else 1-self.q**(d+1)/(1+self.q)
        return (1-self.b)*float(self.weights[self.support<=x].sum())+self.b*self.prior.cdf(x)

    def pmf(self,x):
        if not math.isfinite(x) or x!=math.floor(x):return 0.
        if self.kind=='zero':return float(x==0)
        if self.kind=='bernoulli':return self.p if x==1 else 1-self.p if x==0 else 0.
        if self.kind=='poisson':return float(stats.poisson.pmf(x,self.mu))
        if self.kind=='geometric':return (1-self.q)*self.q**int(x) if x>=0 else 0.
        if self.kind=='signed':return (1-self.q)/(1+self.q)*self.q**abs(int(x)-self.center)
        i=int(np.searchsorted(self.support,x));w=self.weights[i] if i<len(self.support) and self.support[i]==x else 0.
        return (1-self.b)*float(w)+self.b*self.prior.pmf(x)

    def logpmf(self,x):
        if not math.isfinite(x) or x!=math.floor(x):return -math.inf
        if self.kind=='zero':return 0. if x==0 else -math.inf
        if self.kind=='poisson':return float(stats.poisson.logpmf(x,self.mu))
        if self.kind=='bernoulli':
            v=self.p if x==1 else 1-self.p if x==0 else 0.
            return math.log(v) if v>0 else -math.inf
        if self.kind=='geometric':return math.log1p(-self.q)+x*math.log(self.q) if x>=0 and self.q>0 else 0. if x==0 else -math.inf
        if self.kind=='signed':return math.log1p(-self.q)-math.log1p(self.q)+abs(x-self.center)*math.log(self.q) if self.q>0 else 0. if x==self.center else -math.inf
        i=int(np.searchsorted(self.support,x));w=self.weights[i] if i<len(self.support) and self.support[i]==x else 0.
        a=math.log1p(-self.b)+math.log(w) if w>0 else -math.inf
        b=math.log(self.b)+self.prior.logpmf(x) if self.b>0 else -math.inf
        return float(np.logaddexp(a,b))

    def quantile(self,p):
        if not 0<p<1:raise ValueError('open quantile probability required')
        if self.kind=='poisson':return int(stats.poisson.ppf(p,self.mu))
        low,high=-1,1
        while self.cdf(low)>=p:low=low*2-1
        while self.cdf(high)<p:high=high*2+1
        while high-low>1:
            mid=(low+high)//2
            if self.cdf(mid)>=p:high=mid
            else:low=mid
        return high

    def abs_moment(self,x):
        if self.kind=='zero':return abs(x)
        if self.kind=='bernoulli':return (1-self.p)*abs(x)+self.p*abs(1-x)
        if self.kind=='geometric':return self.mean-x if x<0 else x-self.mean+2*self.q**(x+1)/(1-self.q)
        if self.kind=='signed':return abs(x-self.center)+2*self.q**(abs(x-self.center)+1)/(1-self.q*self.q)
        if self.kind=='poisson':
            if x<0:return self.mu-x
            return x-self.mu+2*(self.mu*stats.poisson.sf(x-1,self.mu)-x*stats.poisson.sf(x,self.mu))
        return (1-self.b)*float(self.weights@np.abs(self.support-x))+self.b*self.prior.abs_moment(x)

    def pair_abs(self):
        if self.kind=='zero':return 0.
        if self.kind=='bernoulli':return 2*self.p*(1-self.p)
        if self.kind=='geometric':return 2*self.q/(1-self.q*self.q)
        if self.kind=='signed':return 4*self.q*(1+self.q+self.q*self.q)/((1-self.q)*(1+self.q)**3)
        if self.kind=='poisson':return 2*self.mu*(special.ive(0,2*self.mu)+special.ive(1,2*self.mu))
        cumulative=np.cumsum(self.weights)-self.weights;moment=np.cumsum(self.weights*self.support)-self.weights*self.support
        emp=2*float(self.weights@(self.support*cumulative-moment))
        cross=float(self.weights@np.asarray([self.prior.abs_moment(y) for y in self.support]));a=1-self.b
        return a*a*emp+2*a*self.b*cross+self.b*self.b*self.prior.pair_abs()

    def crps(self,y):
        value=float(self.abs_moment(y)-self.pair_abs()/2)
        if value < -1e-8:raise ValueError('negative CRPS')
        return max(0.,value)

    def summary(self,actual=None):
        mean=self.mean;median=self.quantile(.5);lo=self.quantile(.05);hi=self.quantile(.95)
        logmass=None if actual is None else self.logpmf(actual)
        return dict(mean=mean,lower_median=median,q05=lo,q95=hi,interval90_width=hi-lo,zero_mass=self.pmf(0),crps=None if actual is None else self.crps(actual),nll=None if logmass is None or not math.isfinite(logmass) else -logmass,infinite_nll=bool(logmass==-math.inf) if logmass is not None else False,interval90_covered=None if actual is None else bool(lo<=actual<=hi))

    def parameters(self):
        if self.kind=='mixture':return dict(kind=self.kind,mixture=self.b,prior=self.prior.parameters())
        return dict(kind=self.kind,mean=self.mu,center=self.center,q=self.q,p=self.p)


def prior(y,target):
    values=np.asarray(y,dtype=float)
    if not len(values):return Law('bernoulli',p=.5) if target=='anytime_td' else Law('zero')
    if target=='anytime_td':return Law('bernoulli',p=float((values.sum()+1)/(len(values)+2)))
    if target in {'pass_td','pass_cmp','pass_att','pass_int','rush_att','rec'}:
        mu=max(.05,float(values.mean()));return Law('geometric',q=mu/(1+mu))
    center=int(np.sort(values)[(len(values)-1)//2]);scale=max(1.,float(np.abs(values-center).mean()))
    return Law('signed',center=center,q=scale/(1+scale))
