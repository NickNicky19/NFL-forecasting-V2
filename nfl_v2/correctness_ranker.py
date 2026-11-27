"""Earlier-only selection reliability ranking; never an Over/Under law."""
import collections
import math
import numpy as np
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from nfl_v2.exact_line_repair import choose,confidence,eligible_training

VERSION='B-CORRECTNESS-RANK-L2-v1'
FEATURES=('confidence_margin','selected_over','line_saturation','role_RB','role_WR','role_TE')


def features(row):
    p=row['probabilities']
    if p is None:return None
    if set(p)!={'over','under','push'} or not all(math.isfinite(x) and x>=0 for x in p.values()) or abs(sum(p.values())-1)>1e-10:
        raise ValueError('finite complete baseline event probabilities required')
    side=choose(p)
    if side is None:return None
    line=float(row['line'])
    if not math.isfinite(line) or line<0 or line%1!=.5:
        raise ValueError('this registered ranker accepts nonnegative half-count lines only')
    if row['position']not in ['QB','RB','WR','TE']:
        raise ValueError('unregistered role')
    return [2*confidence(p)-1,int(side=='over'),line/(line+3),
            int(row['position']=='RB'),int(row['position']=='WR'),int(row['position']=='TE')]


def fit(rows,cutoff):
    rr=[r for r in eligible_training(rows,cutoff)if features(r)is not None]
    y=np.array([int((r['actual']>r['line'])==(choose(r['probabilities'])=='over'))for r in rr])
    games=collections.Counter(r['game_id']for r in rr)
    answer=dict(state='IDENTITY_CONFIDENCE_INSUFFICIENT_EARLIER_SUPPORT',fit_performed=False,
                n=len(rr),games=len(games),correct=int(y.sum()),incorrect=int(len(y)-y.sum()),
                latest_label_available=max((r['label_available']for r in rr),default=None),
                training_offer_ids=sorted(r['offer_id']for r in rr),
                feature_names=list(FEATURES),cutoff_epoch=cutoff)
    if len(rr)<20 or len(games)<5 or min(answer['correct'],answer['incorrect'])<3:return answer
    x=np.array([features(r)for r in rr]);weights=np.array([1/games[r['game_id']]for r in rr])
    model=LogisticRegression(C=.25,solver='lbfgs',fit_intercept=True,max_iter=200,tol=1e-8,random_state=1703).fit(x,y,sample_weight=weights)
    answer.update(state='FITTED_CONTEXTUAL_CORRECTNESS_RANKER',fit_performed=True,
                  coefficients=model.coef_[0].tolist(),intercept=float(model.intercept_[0]),
                  n_iter=int(model.n_iter_[0]),iteration_limit_reached=bool(model.n_iter_[0]>=200))
    return answer


def rank_score(row,model):
    x=features(row)
    if x is None:return None
    if not model['fit_performed']:return confidence(row['probabilities'])
    return float(expit(model['intercept']+sum(a*b for a,b in zip(x,model['coefficients']))))
