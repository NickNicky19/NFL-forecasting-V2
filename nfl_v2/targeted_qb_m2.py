"""M2: fixed-context mean, learned OOT conversion dispersion, coherent counts.

Mean parents are existing retained procedures. Beta mixing models conditional
game conversion heterogeneity, not a posterior confidence certificate. FTN
parent derivatives retain FTN Data/nflverse CC-BY-SA-4.0 attribution.
"""
from __future__ import annotations
import math
import numpy as np
from scipy import optimize, special, stats
from . import player_context_matchup as ctx

VERSION='B-TARGETED-QB-CONTEXT-BETA-BINOMIAL-v1'
FEATURES=('intercept','predicted_context_entropy','lagged_known_destination_entropy',
          'lagged_known_distance_mean_div20','log_prior_attempt_support_div_log1000',
          'destination_unavailable','distance_unavailable')
K_MIN=.05
K_MAX=10000.
K_INITIAL=20.
TAIL_TOL=1e-10

def dispersion_features(q,history):
    d=history.describe(q);mix=np.asarray(d['mix'],float)
    entropy=-float(np.sum(mix[mix>0]*np.log(mix[mix>0])))/math.log(25)
    own=history.player_rows(q['player_id'],q['kickoff'])
    counts=np.zeros(3);distance_sum=0.;distance_n=0
    for r in own:
        dest=r.get('pass_destination_counts',{})
        counts+=np.asarray([dest.get(k,0) for k in ('left','middle','right')],float)
        val=r['field_context']['ydstogo'];n=int(val['n'])
        if val['mean'] is not None and n>0:
            distance_sum+=float(val['mean'])*n;distance_n+=n
    known=float(counts.sum())
    if known:
        w=counts[counts>0]/known;dest_entropy=-float(w@np.log(w))/math.log(3)
    else:dest_entropy=0.
    distance=None if not distance_n else distance_sum/distance_n
    # Finite registered scaling bounds, not outcome-fitted preprocessing.
    z=np.asarray([1.,entropy,dest_entropy,0. if distance is None else min(2.,max(0.,distance/20)),
                  min(2.,math.log1p(d['own_attempts'])/math.log(1000)),float(not known),float(distance is None)])
    if z.shape!=(7,) or not np.isfinite(z).all():raise ValueError('Dispersion feature contract')
    return z,dict(feature_order=list(FEATURES),known_destination_denominator=known,
      known_distance_denominator=distance_n,raw_distance_mean=distance,
      latest_own_source=max((r['available'] for r in own),default=None),
      latest_own_game=max((r['kickoff'] for r in own),default=None),
      interpretation='Earlier known pass destination, not alignment; earlier game-distance mean, not per-attempt distance cells.')

def prior_beta():
    b=np.zeros(7);b[0]=special.logit((K_INITIAL-K_MIN)/(K_MAX-K_MIN));return b

class DispersionModel:
    def __init__(self,beta=None,optimization=None):
        self.beta=prior_beta() if beta is None else np.asarray(beta,float)
        if self.beta.shape!=(7,)or not np.isfinite(self.beta).all():raise ValueError('Dispersion coefficients')
        self.optimization=optimization or {'success':False,'fallback':'REGISTERED_INITIAL_PRECISION'}

    def precision(self,z):
        z=np.asarray(z,float)
        if z.shape[-1]!=7 or not np.isfinite(z).all():raise ValueError('Named feature width/order')
        return K_MIN+(K_MAX-K_MIN)*special.expit(z@self.beta)

    @staticmethod
    def objective(beta,z,n,c,m):
        s=special.expit(z@beta);k=K_MIN+(K_MAX-K_MIN)*s;alpha=m*k;br=(1-m)*k
        logp=(special.gammaln(n+1)-special.gammaln(c+1)-special.gammaln(n-c+1)
              +special.betaln(c+alpha,n-c+br)-special.betaln(alpha,br))
        gradk=(m*(special.digamma(c+alpha)-special.digamma(alpha))
               +(1-m)*(special.digamma(n-c+br)-special.digamma(br))
               -special.digamma(n+k)+special.digamma(k))
        penalty=np.r_[1.,np.full(6,10.)];delta=beta-prior_beta()
        return float(-logp.sum()+.5*np.dot(penalty*delta,delta)),z.T@(-gradk*(K_MAX-K_MIN)*s*(1-s))+penalty*delta

    def fit(self,z,n,c,m):
        z,n,c,m=map(lambda a:np.asarray(a,float),(z,n,c,m))
        if len(n)<30 or n.sum()<80:
            self.optimization={'success':False,'fallback':'INSUFFICIENT_EARLIER_OOT_SUPPORT','rows':len(n)};return self
        if z.shape!=(len(n),7)or np.any(n<0)or np.any(c<0)or np.any(c>n)or np.any(m<=0)or np.any(m>=1):
            raise ValueError('Qualified conditional training contract')
        f=optimize.minimize(self.objective,prior_beta(),args=(z,n,c,m),jac=True,method='L-BFGS-B',
                            options={'maxiter':200,'ftol':1e-10,'gtol':1e-6})
        finite=bool(np.isfinite(f.x).all()and math.isfinite(f.fun))
        self.beta=f.x if f.success and finite else prior_beta()
        self.optimization={'success':bool(f.success),'finite':finite,'iterations':int(f.nit),'message':str(f.message),
          'objective':float(f.fun)if finite else None,'rows':len(n),'attempts':int(n.sum()),
          'fallback':None if f.success and finite else 'REGISTERED_INITIAL_PRECISION_AFTER_NONCONVERGENCE'}
        return self

    def payload(self):
        return dict(kind='oot_context_conditional_bb_precision',version=VERSION,feature_order=list(FEATURES),
                    beta=self.beta.tolist(),bounds=[K_MIN,K_MAX],optimization=self.optimization)

    @classmethod
    def restore(cls,p):
        if p['kind']!='oot_context_conditional_bb_precision'or p['feature_order']!=list(FEATURES)or p['bounds']!=[K_MIN,K_MAX]:
            raise ValueError('Dispersion model identity/feature order')
        return cls(p['beta'],p['optimization'])

class IntegratedBetaBinomial:
    """A~NB; Theta~Beta; C|A,Theta~Binomial. Exact sum to bounded A-tail.

    The adaptive numerical grid is not a support limit. Outside-grid PMFs use
    a fresh scalar tail sum; infinity has CDF1. No omitted mass is renormalized.
    """
    def __init__(self,attempt_mean,attempt_shape,conversion_mean,precision,tail_tol=TAIL_TOL):
        self.attempt_mean=float(attempt_mean);self.attempt_shape=float(attempt_shape)
        self.conversion_mean=float(conversion_mean);self.precision=float(precision);self.tail_tol=float(tail_tol)
        if not all(math.isfinite(v)for v in [self.attempt_mean,self.attempt_shape,self.conversion_mean,self.precision]):raise ValueError('Nonfinite law')
        if self.attempt_mean<0 or self.attempt_shape<=0 or not 0<=self.conversion_mean<=1 or self.precision<=0 or not 0<self.tail_tol<=1e-6:raise ValueError('Law support')
        self._pmf=None;self._cdf=None;self.grid_max=None;self.omitted_attempt_tail=None

    @property
    def mean(self):return self.attempt_mean*self.conversion_mean

    @property
    def variance(self):
        m=self.conversion_mean;M=self.attempt_mean;r=self.attempt_shape
        e2=m*m+m*(1-m)/(1+self.precision)
        return m*M+(M*M+M*M/r)*e2-(M*m)**2

    def _build(self):
        if self._pmf is not None:return
        if not self.attempt_mean or not self.conversion_mean:
            self._pmf=np.asarray([1.]);self._cdf=self._pmf.copy();self.grid_max=0;self.omitted_attempt_tail=0.;return
        r=self.attempt_shape;p=r/(r+self.attempt_mean)
        K=int(stats.nbinom.isf(self.tail_tol/4,r,p))
        if K>4096:raise RuntimeError('NUMERICAL_GRID_RESOURCE_LIMIT_NOT_SUPPORT_CLIPPING')
        a=np.arange(K+1);weights=stats.nbinom.pmf(a,r,p)
        if self.conversion_mean==1:pmf=weights
        else:
            n=a[:,None];c=a[None,:];ok=c<=n
            alpha=self.conversion_mean*self.precision;beta=(1-self.conversion_mean)*self.precision
            with np.errstate(invalid='ignore'):
                logp=(special.gammaln(n+1)-special.gammaln(c+1)-special.gammaln(n-c+1)
                     +special.betaln(c+alpha,n-c+beta)-special.betaln(alpha,beta))
            conditional=np.where(ok,np.exp(logp),0.)
            pmf=weights@conditional
        if not np.isfinite(pmf).all()or np.any(pmf<0):raise ValueError('Invalid integrated mass')
        tail=float(stats.nbinom.sf(K,r,p))
        if abs(float(pmf.sum())-(1-tail))>1e-7:raise ValueError('Integrated normalization')
        self._pmf=pmf;self._cdf=np.cumsum(pmf);self.grid_max=K;self.omitted_attempt_tail=tail

    def cdf(self,x):
        if x==math.inf:return 1.
        if x<0:return 0.
        if not math.isfinite(x):raise ValueError('CDF argument')
        if not self.attempt_mean or not self.conversion_mean:return 1.
        if self.conversion_mean==1:
            return float(stats.nbinom.cdf(math.floor(x),self.attempt_shape,self.attempt_shape/(self.attempt_shape+self.attempt_mean)))
        self._build();k=math.floor(x)
        if k<=self.grid_max:return min(1.,float(self._cdf[k]))
        # C>A exclusion bounds the uncomputed remainder by the A survival.
        # Refine scalar CDF using the full NB tail when a larger x is asked.
        r=self.attempt_shape;p=r/(r+self.attempt_mean)if self.attempt_mean else 1.
        high=max(k,int(stats.nbinom.isf(self.tail_tol/4,r,p)))
        a=np.arange(self.grid_max+1,high+1)
        if not len(a):return min(1.,float(self._cdf[-1]))
        alpha=self.conversion_mean*self.precision;beta=(1-self.conversion_mean)*self.precision
        extra=float(np.dot(stats.nbinom.pmf(a,r,p),stats.betabinom.cdf(k,a,alpha,beta)))
        return min(1.,float(self._cdf[-1])+extra)

    def logpmf(self,x):
        if not math.isfinite(x)or x<0 or x!=math.floor(x):return -math.inf
        self._build();x=int(x)
        if x<=self.grid_max:
            mass=float(self._pmf[x]);return math.log(mass)if mass else -math.inf
        if not self.attempt_mean or not self.conversion_mean:return -math.inf
        r=self.attempt_shape;p=r/(r+self.attempt_mean)
        if self.conversion_mean==1:return float(stats.nbinom.logpmf(x,r,p))
        amax=max(x+64,self.grid_max)
        goal=max(1e-300,self.tail_tol*float(stats.nbinom.sf(x-1,r,p))/4)
        while stats.nbinom.sf(amax,r,p)>goal:amax=2*amax+1
        a=np.arange(x,amax+1);alpha=self.conversion_mean*self.precision;beta=(1-self.conversion_mean)*self.precision
        return float(special.logsumexp(stats.nbinom.logpmf(a,r,p)+stats.betabinom.logpmf(x,a,alpha,beta)))

    def pmf(self,x):return math.exp(self.logpmf(x))

    def quantile(self,p):
        if not 0<p<1:raise ValueError('Open quantile')
        self._build()
        i=int(np.searchsorted(self._cdf,p))
        if i<=self.grid_max:return i
        lo=self.grid_max;hi=2*lo+1
        while self.cdf(hi)<p:hi=2*hi+1
        while hi-lo>1:
            mid=(hi+lo)//2
            if self.cdf(mid)>=p:hi=mid
            else:lo=mid
        return hi

    def parameters(self):
        return dict(kind='integrated_nb_beta_binomial',version=VERSION,attempt_mean=self.attempt_mean,
                    attempt_shape=self.attempt_shape,conversion_mean=self.conversion_mean,precision=self.precision,
                    tail_tol=self.tail_tol,conditioning='physical_participation_statistical_panel_not_venue_nonvoid',
                    support='integer_A>=0_and_0<=C<=A;unbounded_marginals')

    def joint_logpmf(self,a,c):
        if a<0 or c<0 or a!=int(a)or c!=int(c)or c>a:return -math.inf
        if not self.attempt_mean:return 0. if a==c==0 else -math.inf
        r=self.attempt_shape;p=r/(r+self.attempt_mean)
        if self.conversion_mean in (0.,1.):
            good=c==(a if self.conversion_mean else 0)
            return float(stats.nbinom.logpmf(a,r,p))if good else -math.inf
        alpha=self.conversion_mean*self.precision;beta=(1-self.conversion_mean)*self.precision
        return float(stats.nbinom.logpmf(a,r,p)+stats.betabinom.logpmf(c,a,alpha,beta))

def restore_law(p):
    if p['kind']=='integrated_nb_beta_binomial':
        return IntegratedBetaBinomial(**{k:p[k]for k in ('attempt_mean','attempt_shape','conversion_mean','precision','tail_tol')})
    if p['kind']=='gamma_poisson_count':return ctx.CountLaw(p['mean'],p['shape'])
    if p['kind']=='leaf_mixture':
        from .distribution_laws import Law
        return Law('mixture',support=p['support'],weights=p['weights'],prior=Law(**p['prior']),mixture=p['mixture'])
    raise ValueError('Trusted law identity')
