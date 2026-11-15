"""Independent saved M2 state/inference review; no optimizer or NFL fit."""
from __future__ import annotations
import collections, datetime, gzip, hashlib, json, math, pathlib, sys, time
import numpy as np
from scipy import special, stats

ROOT=pathlib.Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from nfl_v2 import targeted_qb_m2 as m2, player_context_matchup as ctx
from nfl_v2.qb_depth_catchability import DepthCompletionModel
from tools import run_targeted_qb_m2 as driver
from check_author_prefit_v2 import independent_z, independent_objective
from prefit_math_review_v1 import beta_integral_cdf

OUT=pathlib.Path(__file__).resolve().parent;WAVE=OUT.parent/'wave-v1'
def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def enc(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def independent_exposure(q,rows):
    eligible=[r for r in rows if r['physical_participation']and r['target_parity']and r['available']<q['kickoff']]
    own=sorted([r for r in eligible if r['player_id']==q['player_id']],key=lambda r:(r['kickoff'],r['game_id']))[-8:]
    earlier=[r['official_attempts']for r in eligible if r['season']>=q['season']-1]
    y=np.asarray([r['official_attempts']for r in own],float);pool=np.asarray(earlier,float)
    mu=float((y.sum()+4*pool.mean())/(len(y)+4));variance=float(((y*y).sum()+4*np.mean(pool*pool))/(len(y)+4)-mu*mu)
    shape=min(200.,max(.5,mu*mu/max(.01,variance-mu)))if mu else 200.
    return mu,shape

def manual_forest(payload,x,prior):
    # Traverse safe primitive arrays independently; do not call author restorer.
    median=np.asarray(payload['design']['median']);x=np.asarray(x,float)
    design=np.r_[np.where(np.isfinite(x),x,median),~np.isfinite(x)].astype(np.float32)
    support=np.asarray(payload['support']);mass=np.zeros(len(support))
    for tree in payload['trees']:
        node=0;steps=0
        while tree['left'][node]!=-1:
            i=tree['feature'][node];node=tree['left'][node]if design[i]<=tree['threshold'][node]else tree['right'][node]
            steps+=1
            if steps>8:raise ValueError('Independent forest traversal bound')
        for row,col,value in zip(tree['leaf_histogram']['rows'],tree['leaf_histogram']['columns'],tree['leaf_histogram']['values']):
            if row==node:mass[col]+=value/len(payload['trees'])
    mass/=mass.sum();q=prior['q'];mean=.95*float(mass@support)+.05*q/(1-q)
    def cdf(k):return .95*float(mass[support<=math.floor(k)].sum())+.05*(0.if k<0 else 1-q**(math.floor(k)+1))
    med=next(k for k in range(1000)if cdf(k)>=.5)
    return mean,med,cdf,mass

def main():
    start=time.process_time();checks=0;problems=[]
    def check(ok,label):
        nonlocal checks
        checks+=1
        if not bool(ok):problems.append(label)
    protocol=read(WAVE/'FROZEN_PROTOCOL_V2.json')
    for p,digest in {**protocol['source_inputs'],**protocol['code'],**protocol['old_prediction_bindings']}.items():check(sha(ROOT/p)==digest,'Executing source binding '+p)
    rows,h,ch=driver.context();by={(r['game_id'],r['player_id']):r for r in rows};parents,_=driver.old_parents()
    zcache={};expcache={}
    def z(q):
        key=q['game_id'],q['player_id']
        if key not in zcache:zcache[key]=independent_z(q,rows)[0]
        return zcache[key]
    def exposure(q):
        key=q['game_id'],q['player_id']
        if key not in expcache:expcache[key]=independent_exposure(q,rows)
        return expcache[key]
    attempts=[json.loads(s)for s in (WAVE/'OPTIMIZER_ATTEMPTS.jsonl').read_text().splitlines()]
    check(len(attempts)==64 and len({r['slot']for r in attempts})==64,'Optimizer total and unique slots')
    check(sum(bool(r['NFL_fit'])for r in attempts)==63,'NFL fit count63')
    check(sum(not r['NFL_fit']for r in attempts)==1,'Synthetic fit count1')
    model_rows=[];max_objective_error=0.;max_gradient=0.;success=collections.Counter();states={}
    for path in sorted((WAVE/'fits').glob('*BB.json.gz')):
        saved=read(path);model=m2.DispersionModel.restore(saved['model']);data=saved['training_objective_inputs']
        season=int(path.name[:4]);week=int(path.name[6:8]);parent=path.name[9:11]
        expected={(q['game_id'],q['player_id'])for q in rows if q['physical_participation']and q['target_parity']and q['available']<saved['fit_cutoff']and q['season']>=season-1 and(q['game_id'],q['player_id'])in parents[parent]}
        actual={(r['game_id'],r['player_id'])for r in data}
        check(actual==expected and len(actual)==len(data),'Eligible OOF membership '+path.name)
        target_games={q['game_id']for q in rows if(q['season'],q['week'])==(season,week)}
        check(not target_games.intersection(r['game_id']for r in data),'No target-game training '+path.name)
        for r in data:
            q=by[r['game_id'],r['player_id']];old=parents[parent][r['game_id'],r['player_id']]
            check(r['attempts']==q['official_attempts']and r['completions']==q['official_completions'],'Source label/denominator')
            check(r['available']<saved['fit_cutoff']and old['fit_cutoff']<=q['kickoff']and old['feature_cutoff']==q['kickoff'],'OOF parameter and label chronology')
            check(r['parent_probability']==old['components']['integrated_completion_probability'],'Exact earlier mean binding')
            check(np.allclose(r['z'],z(q),rtol=0,atol=2e-14),'Independent OOF profile features')
        zz=np.asarray([r['z']for r in data]);n=np.asarray([r['attempts']for r in data]);c=np.asarray([r['completions']for r in data]);mu=np.asarray([r['parent_probability']for r in data])
        objective=independent_objective(model.beta,zz,n,c,mu);recorded=saved['model']['optimization']['objective']
        max_objective_error=max(max_objective_error,abs(objective-recorded));check(abs(objective-recorded)<1e-7,'Independent fitted objective '+path.name)
        _,gradient=m2.DispersionModel.objective(model.beta,zz,n,c,mu);max_gradient=max(max_gradient,float(np.max(np.abs(gradient))))
        check(np.isfinite(model.beta).all()and np.isfinite(gradient).all(),'Finite fitted parameters and gradient')
        check(saved['latest_training_label']==max(r['available']for r in data),'Latest admitted label')
        check(objective<=independent_objective(m2.prior_beta(),zz,n,c,mu)+1e-7,'Optimization improves registered objective')
        success[saved['model']['optimization']['success']]+=1
        states[season,week,parent]=model
        model_rows.append({'file':str(path.relative_to(ROOT)),'sha256':sha(path),'rows':len(data),'latest_label':saved['latest_training_label'],'cutoff':saved['fit_cutoff'],'iterations':saved['model']['optimization']['iterations'],'fallback':saved['model']['optimization'].get('fallback')})
    check(len(model_rows)==51,'51 precision models')
    prediction_bindings=[];allpred={};paircounts=collections.Counter();max_mean_change=0.;max_exposure_error=0.;max_precision_error=0.;all_k=[]
    for path in sorted((WAVE/'predictions').glob('*.json.gz')):
        packet=read(path);season,week=packet['season'],packet['week']
        query=[r for r in rows if(r['season'],r['week'])==(season,week)]
        check(packet['fit_cutoff']==min(q['kickoff']for q in query),'Forecast origin earliest game')
        groups=collections.defaultdict(dict)
        for r in packet['rows']:
            groups[r['game_id'],r['player_id']][r['method']]=r;allpred[r['method'],r['game_id'],r['player_id']]=r
            q=by[r['game_id'],r['player_id']]
            check(r['feature_cutoff']==q['kickoff'],'Query feature cutoff')
            if r['method'].startswith('M2_'):
                _,parent,suffix=r['method'].split('_');old=parents[parent][r['game_id'],r['player_id']];a=old['components']['attempt_law'];m=old['components']['integrated_completion_probability']
                check(r['original_parent_procedure']==old['procedure_id'],'Parent procedure identity')
                check(abs(sum(old['components']['predicted_context_mix'])-1)<1e-12,'Predicted context weights normalize')
                check(abs(np.dot(old['components']['predicted_context_mix'],old['components']['conditional_completion_probability'])-m)<1e-12,'Conversion context integration')
                check(r['conversion_components']['same_attempt_mean']==a['mean']and r['conversion_components']['same_attempt_shape']==a['shape'],'Fixed predicted exposure')
                check(r['mean']==a['mean']*m,'Same expected mean after dispersion')
                max_mean_change=max(max_mean_change,abs(r['mean']-old['mean']))
                check(abs(r['mean']-old['mean'])<1e-10,'Unchanged mean parent product')
                want_mu,want_r=exposure(q);max_exposure_error=max(max_exposure_error,abs(a['mean']-want_mu),abs(a['shape']-want_r))
                check(abs(a['mean']-want_mu)<1e-12 and abs(a['shape']-want_r)<1e-9,'Independent attempt-law reconstruction')
                if suffix=='BB':
                    actual_k=r['law']['precision'];want=float(states[season,week,parent].precision(z(q)));all_k.append(actual_k)
                    max_precision_error=max(max_precision_error,abs(actual_k-want));check(abs(actual_k-want)<1e-9,'Restored precision inference')
                    check(r['numerical_integration']['omitted_attempt_tail']<=1e-10 and not r['numerical_integration']['renormalized'],'Finite tail error / no renormalization')
                else:
                    check(r['law']['mean']==old['law']['mean']and r['law']['shape']==old['law']['shape'],'Exact unchanged binomial law')
                    check(r['lower_median']==old['lower_median'],'Exact unchanged binomial median')
                paircounts[suffix]+=1
        check(set(groups)=={(q['game_id'],q['player_id'])for q in query},'Every declared query retained')
        for key,group in groups.items():
            for parent in ['P2','C1','C2']:
                a,b=group['M2_'+parent+'_BIN'],group['M2_'+parent+'_BB']
                check(a['mean']==b['mean']and a['conversion_components']['same_attempt_mean']==b['conversion_components']['same_attempt_mean'],'Paired full-system mean/exposure equality')
            law=group['COMMON_EXPOSURE']['law'];a=parents['P2'][key]['components']['attempt_law']
            check(law['mean']==a['mean']and law['shape']==a['shape'],'Passing-attempt output unchanged')
        prediction_bindings.append({'path':str(path.relative_to(ROOT)),'sha256':sha(path),'query_count':len(query),'rows':len(packet['rows'])})
    # Independently restore representative complete inference paths without new fitting.
    cases=read(OUT/'PREFIT_DESIGN_REVIEW_V1.json')['representative_cases'];representative=[];max_CDF_error=0.;max_direct_mean_error=0.
    for case in cases:
        if 'game_id'not in case:continue
        q=by[case['game_id'],case['player_id']]
        for parent in ['P2','C1','C2']:
            row=allpred['M2_'+parent+'_BB',q['game_id'],q['player_id']];law=m2.restore_law(row['law']);law._build();largest=0.
            for k in [0,1,10,20,30,40,60]:
                independent,error=beta_integral_cdf(k,law.attempt_mean,law.attempt_shape,law.conversion_mean,1/(law.precision+1))
                diff=abs(independent-law.cdf(k));largest=max(largest,diff);check(diff<max(3e-8,error*8+1e-10),'Fitted-law independent CDF')
                check(law.cdf(k)+1e-10>=stats.nbinom.cdf(k,law.attempt_shape,law.attempt_shape/(law.attempt_shape+law.attempt_mean)),'Fitted stochastic ordering')
            max_CDF_error=max(max_CDF_error,largest)
            check(abs(law._pmf.sum()+law.omitted_attempt_tail-1)<1e-8,'Representative full mass')
            check(law.cdf(row['lower_median'])>=.5-1e-10 and law.cdf(row['lower_median']-1)<.5+1e-10,'Representative median')
            check(law.joint_logpmf(10,11)==-math.inf,'Impossible completion count zero')
            representative.append({'case':case['case'],'parent':parent,'largest_CDF_difference':largest,'precision':law.precision,'fallback':row['fallback']})
        path=WAVE/'fits'/f"2026-W{q['week']:02}-D_M2.json.gz";saved=read(path);levels=saved['identity_levels'];train=[r for r in rows if r['physical_participation']and r['target_parity']and r['available']<saved['fit_cutoff']and r['season']>=2025]
        for field in ['player_id','team','opponent']:check(levels[field]==sorted({r[field]for r in train}),'Direct fit-only identity levels')
        d=h.describe(q);mu,r=exposure(q);a,c=d['own_attempts'],d['own_completions']
        x=list(d['mix'])+list(d['opponent_residual'])+[math.log((c+1)/(a-c+1)),d['opponent_residual_main'],d['team_residual']]+list(z(q))+[mu,r]
        for field in ['player_id','team','opponent']:x.extend(float(q[field]==v)for v in levels[field])
        row=allpred['D_M2',q['game_id'],q['player_id']];check(np.allclose(x,row['features'],rtol=0,atol=1e-12),'Direct ordered feature adapter')
        mean,median,cdf,mass=manual_forest(saved['model'],x,saved['prior']);max_direct_mean_error=max(max_direct_mean_error,abs(mean-row['mean']))
        check(abs(mean-row['mean'])<1e-10 and median==row['lower_median'],'Independent direct safe-array traversal')
        for k in [0,10,20,30]:check(abs(cdf(k)-m2.restore_law(row['law']).cdf(k))<1e-11,'Independent direct distribution')
    # Independently restore the three new mean-parent models at frozen W9 case.
    q=next(by[r['game_id'],r['player_id']]for r in cases if r.get('case')=='ORDINARY_W9')
    mean_restores=[]
    for parent in ['P2','C1','C2']:
        saved=read(WAVE/'parents'/f'2026-W09-{parent}.json.gz')
        model=ctx.CompletionModel.restore(saved['model'])if parent=='P2'else DepthCompletionModel.restore(saved['model'])
        probabilities=model.probabilities(q,h)if parent=='P2'else model.probabilities(q,h,ch)
        old=parents[parent][q['game_id'],q['player_id']];diff=float(np.max(np.abs(probabilities-np.asarray(old['components']['conditional_completion_probability']))))
        check(diff<1e-12,'Missing mean-parent JSON restore '+parent)
        mean_restores.append({'parent':parent,'largest_probability_difference':diff,'optimizer_success':saved['model']['optimization']['success']})
    result={'id':'B_M2_INDEPENDENT_FITTED_STATE_VERIFICATION_v1','at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state':'PASS_WITH_STATED_SCOPE'if not problems else'FAIL','checks':checks,'problems':problems,
      'optimizer_attempts':len(attempts),'NFL_optimizer_calls':sum(r['NFL_fit']for r in attempts),'synthetic_calls':sum(not r['NFL_fit']for r in attempts),'precision_optimizer_success':dict(success),
      'precision_model_count':len(model_rows),'largest_independent_objective_difference':max_objective_error,'largest_fitted_gradient_abs':max_gradient,'fitted_precision_range':[min(all_k),max(all_k)],
      'largest_parent_mean_change':max_mean_change,'largest_independent_exposure_parameter_difference':max_exposure_error,'largest_restored_precision_difference':max_precision_error,
      'predicted_BIN_BB_row_counts':dict(paircounts),'prediction_bindings':prediction_bindings,'model_bindings':model_rows,'representative_inferences':representative,'missing_mean_parent_restores':mean_restores,
      'largest_representative_CDF_difference':max_CDF_error,'largest_independent_direct_mean_difference':max_direct_mean_error,'CPU_seconds':time.process_time()-start,
      'reviewer_NFL_fits':0,'reviewer_optimizer_calls':0,'source_read_attempts':0,
      'verification_limits':['Saved fitting objective and gradients independently evaluated; no fresh NFL fit reproduced or claimed.','Old source/vintage/shared-context contracts reused from accepted earlier checks; this does not authenticate original historical publication.','Direct distribution remains a separate marginal, not a joint C/A law. Its vector schema is code-controlled; low-level restorer cannot detect arbitrary same-width semantic permutation.','Private A offered rows and source clocks remain outside reviewed scope.','These checks establish correctness within scope, not predictive improvement or product admission.']}
    (OUT/'FITTED_STATE_VERIFICATION_V1.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'state':result['state'],'checks':checks,'problems':problems[:10],'CPU_seconds':result['CPU_seconds'],'max_CDF_difference':max_CDF_error,'max_mean_change':max_mean_change}))
    if problems:raise SystemExit(1)

if __name__=='__main__':main()
