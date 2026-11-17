"""One game-weighted, earlier-only intercept; no point-to-probability conversion."""
import collections,hashlib,json,math
from datetime import datetime
import numpy as np
from scipy.optimize import brentq
from scipy.special import expit

VERSION='B-EXACT-LINE-INTERCEPT-v1'
SIGMA=.5
LABEL_LAG_SECONDS=7*86400
MIN_ROWS=20
MIN_GAMES=5
MIN_CLASS=3

def epoch(value):
 d=datetime.fromisoformat(value.replace('Z','+00:00'))
 if d.tzinfo is None:raise ValueError('timezone-aware clock required')
 return d.timestamp()
def cdf_shift(x,alpha):
 if not 0<=x<=1:raise ValueError('invalid CDF probability')
 if x in (0.,1.):return float(x)
 return float(expit(math.log(x)-math.log1p(-x)-alpha))
def repair(probabilities,alpha):
 if probabilities is None:return None
 if min(probabilities.values())<0 or abs(sum(probabilities.values())-1)>1e-10:raise ValueError('invalid baseline probability law')
 lo=cdf_shift(probabilities['under'],alpha);hi=cdf_shift(probabilities['under']+probabilities['push'],alpha)
 if hi+1e-12<lo:raise ValueError('CDF order violation')
 return dict(over=1-hi,under=lo,push=max(0.,hi-lo))
def choose(probabilities):
 if probabilities is None or abs(probabilities['over']-probabilities['under'])<=1e-12:return None
 return 'over'if probabilities['over']>probabilities['under']else'under'
def eligible_training(rows,cutoff):
 return [r for r in rows if r['label_available']<cutoff and r['probabilities']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'and float(r['line'])%1==.5]
def fit(rows,cutoff):
 rr=eligible_training(rows,cutoff);games=collections.Counter(r['game_id']for r in rr);y=np.array([r['actual']>float(r['line'])for r in rr],float);p=np.array([r['probabilities']['over']for r in rr]);ids=sorted(r['offer_id']for r in rr);membership=hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest()
 result=dict(alpha=0.,state='IDENTITY_INSUFFICIENT_EARLIER_SUPPORT',fit_performed=False,n=len(rr),games=len(games),positive=int(y.sum()),negative=int(len(y)-y.sum()),membership_sha256=membership,cutoff_epoch=cutoff,latest_label_available=max((r['label_available']for r in rr),default=None))
 if len(rr)<MIN_ROWS or len(games)<MIN_GAMES or min(result['positive'],result['negative'])<MIN_CLASS:return result
 if any((a==0 and b==1)or(a==1 and b==0)for a,b in zip(p,y)):result['state']='IDENTITY_IRREPARABLE_INFINITE_TRAINING_LOGLOSS';return result
 weights=np.array([1/games[r['game_id']]for r in rr]);logits=np.zeros(len(rr));interior=(p>0)&(p<1);logits[interior]=np.log(p[interior])-np.log1p(-p[interior])
 def gradient(alpha):
  q=p.copy();q[interior]=expit(logits[interior]+alpha)
  return float(np.dot(weights,q-y)+alpha/(SIGMA**2))
 alpha=-1.5 if gradient(-1.5)>=0 else 1.5 if gradient(1.5)<=0 else float(brentq(gradient,-1.5,1.5,xtol=1e-12))
 result.update(alpha=alpha,state='FITTED_GAME_WEIGHTED_INTERCEPT_MAP',fit_performed=True,gradient=gradient(alpha),at_registered_bound=abs(alpha)>=1.5-1e-10)
 return result
def confidence(probabilities):return max(probabilities['over'],probabilities['under'])if probabilities is not None else None
def gate_threshold(earlier_predictions,cutoff):
 values=[confidence(r['probabilities'])for r in earlier_predictions if r['decision_epoch']<cutoff and r['probabilities']is not None]
 # This gate learns a confidence quantile, not correctness, from earlier OOF
 # predictions. No outcome is read here, and no 90% reliability is assumed.
 return max(.6,float(np.quantile(values,.5)))if len(values)>=20 else .6
