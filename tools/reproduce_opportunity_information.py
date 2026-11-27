"""Exactly two root-reserved W1 GLM reproductions; no offer scoring or retries.

Independent NB/binomial likelihood and gradient arithmetic. Full independent
vectors are durably saved before any comparison. Original failed receipts may
not be overwritten. The root alone reserves calls in the global wave ledger.
"""
from __future__ import annotations
import argparse, copy, gzip, hashlib, json, math, pathlib, resource, sys, time
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from scipy import optimize, special, stats
from threadpoolctl import threadpool_limits
from nfl_v2 import opportunity_information as original

BASE=ROOT/'reports/information-skill-follow-through-01/B/opportunity-v1'
INITIAL_ETA=math.log(19.5/180.)
OPTIONS=dict(maxiter=300,ftol=1e-10,gtol=1e-6)
TOL=dict(coefficient_absolute=1e-5,probability_absolute=1e-7,
         objective_absolute=1e-6,objective_relative=1e-10)


def read(path):
    raw=path.read_bytes()
    return json.loads(gzip.decompress(raw)if path.suffix=='.gz'else raw)


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()


def independent_team(theta,x,offset,y):
    """NB(r,p=r/(r+mu)); separate stable likelihood and score reduction."""
    beta=np.asarray(theta[:3]);eta=float(theta[3]);s=special.expit(eta)
    shape=.5+199.5*s;logmu=offset+np.sum(x*beta[None,:],axis=1);mu=np.exp(logmu)
    probability=shape/(shape+mu)
    ridge=np.asarray([1.,10.,10.])
    loss=-float(np.sum(stats.nbinom.logpmf(y,shape,probability)))
    loss+=.5*float(np.sum(ridge*beta*beta))+.5*(eta-INITIAL_ETA)**2
    residual=shape*(mu-y)/(shape+mu)
    beta_score=np.sum(residual[:,None]*x,axis=0)+ridge*beta
    dloglik_dr=(special.digamma(y+shape)-special.digamma(shape)+math.log(shape)+1.
                -np.log(shape+mu)-(shape+y)/(shape+mu))
    eta_score=-float(np.sum(dloglik_dr))*199.5*s*(1-s)+eta-INITIAL_ETA
    return loss,np.r_[beta_score,eta_score]


def independent_share(beta,x,offset,n,y):
    linear=offset+np.sum(x*np.asarray(beta)[None,:],axis=1)
    ridge=np.asarray([1.,10.,10.,10.])
    loss=-float(np.sum(y*special.log_expit(linear)+(n-y)*special.log_expit(-linear)))
    loss+=.5*float(np.sum(ridge*beta*beta))
    score=np.sum((n*special.expit(linear)-y)[:,None]*x,axis=0)+ridge*beta
    return loss,score


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-root-reserved',action='store_true')
    args=parser.parse_args()
    if not args.execute_root_reserved:
        print('Prepared code only. Execution requires explicit root reservation and --execute-root-reserved.')
        return
    start=time.monotonic();cpu=time.process_time()
    dest=BASE/'independent/REPRESENTATIVE_FIT_REPRODUCTION_V1.json'
    if dest.exists():raise FileExistsError('Prior receipt exists; no retry or overwrite.')
    reservations=[json.loads(line)for line in(BASE/'wave-v1/FIT_ATTEMPTS.jsonl').read_text().splitlines()]
    slots={r['slot']for r in reservations}
    required={'INDEPENDENT_W01_TEAM','INDEPENDENT_W01_SHARE'}
    if not required<=slots or len(reservations)>36:raise RuntimeError('Missing root-reserved independent calls or wavecap exceeded.')
    training_path=BASE/'wave-v1/training-designs/2026-W01.json.gz'
    trace_path=BASE/'wave-v1/QUERY_TRACE_V1.json.gz'
    source_paths={kind:BASE/f'wave-v1/fits/2026-W01-{kind}.json.gz'for kind in('team','share')}
    arrays=read(training_path);trace=read(trace_path)['rows']
    receipt=dict(id='B_OPPORTUNITY_REPRESENTATIVE_FIT_REPRODUCTION_v1',UTC=now(),
        status='ROOT_RESERVED_BEFORE_INDEPENDENT_OPTIMIZERS',all_passed=False,
        frozen_tolerances=TOL,settings=OPTIONS,threads=1,CPU_cap_seconds=60,RSS_cap_bytes=1073741824,
        reserved_optimizer_calls=2,actual_optimizer_calls=0,attempts=[],
        source_bindings={str(p.relative_to(ROOT)):dict(bytes=p.stat().st_size,SHA256=sha(p))for p in[training_path,trace_path,*source_paths.values()]},
        code_SHA256={str(p.relative_to(ROOT)):sha(p)for p in[pathlib.Path(__file__).resolve(),ROOT/'nfl_v2/opportunity_information.py']},
        scope='Exactly two2026W1 team/share GLM reproductions. No forest, oldC1, forecasts, offers, grader, tuning or source collection.',
        full_vector_retention='Independent coefficient vector and typed state saved BEFORE source comparisons; failures preserved.')
    def usage():return dict(CPU_seconds=time.process_time()-cpu,wall_seconds=time.monotonic()-start,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    def save():
        receipt['resources']=usage();dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    def check():
        u=usage()
        if u['CPU_seconds']>60 or u['peak_RSS_bytes']>1073741824:raise RuntimeError('Independent CPU/RSS cap reached; no automatic extension.')
    save()
    try:
        with threadpool_limits(limits=1):
            for kind in('team','share'):
                check();source=read(source_paths[kind]);state=source['state']
                x=np.asarray(arrays[kind+'_X'],float);offset=np.asarray(arrays[kind+'_offset'],float)
                y=np.asarray(arrays[kind+'_y'],float)
                if not np.isfinite(x).all()or not np.isfinite(offset).all()or not np.isfinite(y).all():raise ValueError('Nonfinite retained training design.')
                if kind=='team':
                    native=np.r_[state['beta'],state['eta']];initial=np.r_[np.zeros(3),INITIAL_ETA]
                    objective=lambda beta:independent_team(beta,x,offset,y)
                    parent=lambda beta:original.team_objective(beta,x,offset,y)
                else:
                    n=np.asarray(arrays['share_n'],float)
                    if np.any(y<0)or np.any(y>n):raise ValueError('Invalid conditional exposure support.')
                    native=np.asarray(state['beta'],float);initial=np.zeros(4)
                    objective=lambda beta:independent_share(beta,x,offset,n,y)
                    parent=lambda beta:original.share_objective(beta,x,offset,n,y)
                membership=hashlib.sha256(json.dumps(arrays[kind+'_ids']).encode()).hexdigest()
                if source['member_sha256']!=membership:raise ValueError('Training membership differs from root fit.')
                probes=[]
                for name,beta in [('initial',initial),('retained_native',native),('fixed_probe',native+np.linspace(-1e-4,1e-4,len(native)))]:
                    f,g=objective(beta);ff,gg=parent(beta)
                    finite=[]
                    for j in range(len(beta)):
                        plus=beta.copy();minus=beta.copy();plus[j]+=1e-5;minus[j]-=1e-5
                        finite.append((objective(plus)[0]-objective(minus)[0])/2e-5)
                    probes.append(dict(beta=name,objective_absolute_difference=abs(f-ff),gradient_max_difference=float(np.max(np.abs(g-gg))),finite_difference_gradient_max_error=float(np.max(np.abs(g-finite)))))
                # This is a pure arithmetic guard before the charged fit, not a
                # mechanism/settings selection or post-result tolerance change.
                if any(p['objective_absolute_difference']>1e-6 or p['gradient_max_difference']>1e-6 or p['finite_difference_gradient_max_error']>1e-3 for p in probes):raise RuntimeError('Independent objective/gradient precheck failed; no fit attempted.')
                attempt=dict(kind=kind,slot='INDEPENDENT_W01_'+kind.upper(),charged_by_root=True,
                    state='ENTERING_OPTIMIZER',entered_UTC=now(),before_resources=usage(),
                    training_rows=len(y),membership_SHA256=membership,objective_gradient_prechecks=probes,
                    initial_vector=initial.tolist(),retained_native_vector=native.tolist())
                receipt['attempts'].append(attempt);receipt['actual_optimizer_calls']+=1;save()
                fit=optimize.minimize(objective,initial,jac=True,method='L-BFGS-B',options=OPTIONS)
                # Retain the whole independent fit before comparison, including
                # a nonconverged/failed state; never discard an inconvenient fit.
                independent_state=copy.deepcopy(state)
                independent_state['beta']=fit.x[:3].tolist()if kind=='team'else fit.x.tolist()
                if kind=='team':
                    independent_state['eta']=float(fit.x[3]);independent_state['shape']=float(.5+199.5*special.expit(fit.x[3]))
                independent_state['optimization']=dict(success=bool(fit.success),message=str(fit.message),iterations=int(fit.nit),independent=True,retry=False)
                attempt.update(state='FULL_VECTOR_DURABLE_BEFORE_COMPARISON',returned_UTC=now(),
                    independent_vector=fit.x.tolist(),independent_state=independent_state,
                    independent_objective=float(fit.fun),independent_success=bool(fit.success),
                    iterations=int(fit.nit),termination=str(fit.message),after_fit_resources=usage())
                save();check()
                coefficient_difference=float(np.max(np.abs(fit.x-native)))
                objective_records=[]
                for label,beta in[('native',native),('independent',fit.x)]:
                    f,g=objective(beta);ff,gg=parent(beta)
                    objective_records.append(dict(at=label,independent_objective=float(f),author_objective=float(ff),objective_difference=abs(f-ff),gradient_max_difference=float(np.max(np.abs(g-gg))),gradient_infinity_norm=float(np.max(np.abs(g)))))
                objective_difference=abs(objective(fit.x)[0]-objective(native)[0]);prediction_diff=0.;mean_diff=0.;scalar_batch_diff=0.;checked=0
                for item in trace:
                    if item['query']['week']!=1:continue
                    design=item['design']
                    if kind=='team':
                        if not design['team_eligible']:continue
                        xx=np.asarray(design['team_x']);off=design['team_offset']
                        a_mu=float(np.exp(off+xx@native[:3]));b_mu=float(np.exp(off+np.sum(xx*fit.x[:3])))
                        a_shape=.5+199.5*special.expit(native[3]);b_shape=.5+199.5*special.expit(fit.x[3])
                        grid=np.asarray([0,10,30,60,100,200]);aa=stats.nbinom.cdf(grid,a_shape,a_shape/(a_shape+a_mu));bb=stats.nbinom.cdf(grid,b_shape,b_shape/(b_shape+b_mu))
                        prediction_diff=max(prediction_diff,float(np.max(np.abs(aa-bb))));mean_diff=max(mean_diff,abs(a_mu-b_mu))
                        scalar_batch_diff=max(scalar_batch_diff,max(abs(float(aa[j])-float(stats.nbinom.cdf(int(k),a_shape,a_shape/(a_shape+a_mu))))for j,k in enumerate(grid)))
                    else:
                        if not design['eligible']:continue
                        values=np.asarray([0.,design['T_reference']/2,design['T_reference'],2*design['T_reference']])
                        xx=np.tile(np.asarray(design['share_x']),(4,1));xx[:,2]=np.log(np.where(values>0,values,design['T_reference'])/design['T_reference'])
                        aa=special.expit(design['share_offset']+xx@native);bb=special.expit(design['share_offset']+np.sum(xx*fit.x[None,:],axis=1))
                        prediction_diff=max(prediction_diff,float(np.max(np.abs(aa-bb))));mean_diff=max(mean_diff,float(np.max(np.abs(values*aa-values*bb))))
                        scalar_batch_diff=max(scalar_batch_diff,max(abs(float(aa[j])-float(special.expit(design['share_offset']+sum(xx[j,k]*native[k]for k in range(4)))))for j in range(4)))
                    checked+=1
                tolerance_pass=bool(fit.success and coefficient_difference<=TOL['coefficient_absolute']and prediction_diff<=TOL['probability_absolute']and objective_difference<=TOL['objective_absolute']+TOL['objective_relative']*abs(objective(native)[0]))
                attempt['comparison']=dict(training_member_match=True,coefficient_max_absolute_difference=coefficient_difference,
                    probability_or_count_CDF_max_absolute_difference=prediction_diff,mean_max_absolute_difference=mean_diff,
                    scalar_batch_max_difference=scalar_batch_diff,query_cases=checked,objective_difference=objective_difference,
                    objectives_at_both_persisted_vectors=objective_records,tolerance_pass=tolerance_pass)
                attempt['state']='COMPARED_PASS'if tolerance_pass else'COMPARED_STRICT_TOLERANCE_FAILED';save()
            receipt['all_passed']=len(receipt['attempts'])==2 and all(a['comparison']['tolerance_pass']for a in receipt['attempts'])
            receipt['status']='PASS_REPRESENTATIVE_TEAM_SHARE_FITS'if receipt['all_passed']else'FAILED_STRICT_REPRESENTATIVE_FIT_TOLERANCES'
            receipt['completed_UTC']=now();receipt['new_forecasts']=0;receipt['new_scores']=0;receipt['network_reads']=0;save()
            print(json.dumps(dict(status=receipt['status'],actual_optimizer_calls=receipt['actual_optimizer_calls'],comparisons=[a['comparison']for a in receipt['attempts']],resources=usage()),indent=2))
    except Exception as exc:
        receipt['status']='FAILED_PRESERVED_NO_AUTOMATIC_RETRY';receipt['error']=str(exc);receipt['failed_UTC']=now();save();raise


if __name__=='__main__':main()
