"""Whole-week paired-loss uncertainty for frozen chronological evaluations."""
from __future__ import annotations

import math
import numpy as np


def paired_losses(candidate, comparator, weeks, games, *, replicates=500, seed=1703):
    if not (len(candidate)==len(comparator)==len(weeks)==len(games)):
        raise ValueError('paired arrays must have identical membership')
    n=len(candidate)
    out=dict(n=n,delta=None,relative_error_change=None,week_interval=None,
             week_clusters=len(set(weeks)),game_clusters=len(set(games)),
             bootstrap_replicates=replicates,bootstrap_seed=seed,
             bootstrap_rule='resetPCG64percontrast;resamplewholeweeks;sumlossdifferences/sumsampledrows',
             selection_limit='descriptive exposed-sample interval; not selection/multiplicity adjusted',
             game_cluster_sensitivity_se=None,game_normal95_sensitivity=None)
    if not n:
        return dict(out,status='NO_SUPPORTED_PAIRED_ROWS')
    a=np.asarray(candidate,dtype=float);b=np.asarray(comparator,dtype=float)
    if np.any(np.isnan(a)) or np.any(np.isnan(b)) or np.any(a<0) or np.any(b<0):
        raise ValueError('nonnegative loss arrays with explicit infinities required')
    out.update(candidate_infinite_rows=int(np.isinf(a).sum()),comparator_infinite_rows=int(np.isinf(b).sum()))
    if not np.isfinite(a).all() or not np.isfinite(b).all():
        return dict(out,status='NONFINITE_LOSS_DIFFERENCE_UNDEFINED',
                    candidate_error='Infinity' if not np.isfinite(a).all() else float(a.mean()),
                    comparator_error='Infinity' if not np.isfinite(b).all() else float(b.mean()))
    d=a-b;delta=float(d.mean());control=float(b.mean())
    out.update(candidate_error=float(a.mean()),comparator_error=control,delta=delta,
               relative_error_change=delta/control if control else None,
               relative_error_missing_reason=None if control else 'zero_comparator_error_denominator')
    week_ids=sorted(set(weeks));week_index={key:i for i,key in enumerate(week_ids)}
    codes=np.fromiter((week_index[w]for w in weeks),dtype=int,count=n)
    sums=np.bincount(codes,weights=d,minlength=len(week_ids));counts=np.bincount(codes,minlength=len(week_ids))
    out['weekly_paired_sums_counts']={str(key):dict(loss_difference_sum=float(s),n=int(c))for key,s,c in zip(week_ids,sums,counts)}
    if len(week_ids)>=8:
        sampled=np.random.default_rng(seed).integers(0,len(week_ids),size=(replicates,len(week_ids)))
        ratios=sums[sampled].sum(axis=1)/counts[sampled].sum(axis=1)
        out['week_interval']=[float(v)for v in np.quantile(ratios,[.025,.975],method='linear')]
        out['week_interval_status']='NOMINAL_WHOLE_WEEK_PAIRED_BOOTSTRAP'
    else:out['week_interval_status']='INSUFFICIENT_WEEK_CLUSTERS'
    game_ids=sorted(set(games))
    if len(game_ids)>=8:
        game_index={key:i for i,key in enumerate(game_ids)}
        codes=np.fromiter((game_index[g]for g in games),dtype=int,count=n)
        residuals=np.bincount(codes,weights=d,minlength=len(game_ids))-delta*np.bincount(codes,minlength=len(game_ids))
        se=math.sqrt(len(game_ids)/(len(game_ids)-1)*math.fsum(v*v for v in residuals))/n
        out['game_cluster_sensitivity_se']=se
        out['game_normal95_sensitivity']=[delta-1.96*se,delta+1.96*se]
    return dict(out,status='FINITE_PAIRED_LOSS_COMPARISON')
