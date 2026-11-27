"""Independent PMF/CDF, side and proper-score audit; no producer scorer imports."""
import argparse,bisect,collections,gzip,hashlib,itertools,json,math,pickle,sys
from contextlib import ExitStack
from datetime import datetime,timezone
from decimal import Decimal,ROUND_FLOOR
from pathlib import Path
from unittest.mock import patch


def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b,tol=1e-9):return a==b or(a is not None and b is not None and abs(a-b)<=max(tol,abs(b)*1e-10))
def stamp(x):return datetime.fromisoformat(x.replace('Z','+00:00')).timestamp()


class AnalyticLaw:
    def __init__(self,p):
        self.p=p;self.kind=p['kind']
        if self.kind=='mixture':
            self.support=p['support'];self.weights=p['weights'];self.blend=p['mixture'];self.prior=AnalyticLaw(p['prior'])
            assert self.blend==.05 and len(self.support)==len(self.weights)>0 and all(x==int(x)for x in self.support) and all(a<b for a,b in zip(self.support,self.support[1:]))
            assert min(self.weights)>=0 and abs(math.fsum(self.weights)-1)<1e-10
            self.prefix=[0.,*itertools.accumulate(self.weights)]
    def cdf(self,k):
        k=math.floor(k);p=self.p
        if self.kind=='mixture':return (1-self.blend)*self.prefix[bisect.bisect_right(self.support,k)]+self.blend*self.prior.cdf(k)
        if self.kind=='signed':
            q=p['q'];d=k-int(p['center']);return q**(-d)/(1+q)if d<0 else 1-q**(d+1)/(1+q)
        if self.kind=='geometric':return 0. if k<0 else 1-p['q']**(k+1)
        if self.kind=='zero':return float(k>=0)
        if self.kind=='poisson':
            mu=p['mean'];return 0. if k<0 else 1. if mu==0 else math.fsum(math.exp(-mu+i*math.log(mu)-math.lgamma(i+1))for i in range(k+1))
        raise AssertionError('UNSUPPORTED_PRIOR_KIND')
    def pmf(self,k):
        if k!=math.floor(k):return 0.
        p=self.p
        if self.kind=='mixture':
            i=bisect.bisect_left(self.support,k);w=self.weights[i]if i<len(self.support)and self.support[i]==k else 0.
            return (1-self.blend)*w+self.blend*self.prior.pmf(k)
        if self.kind=='signed':return(1-p['q'])/(1+p['q'])*p['q']**abs(k-p['center'])
        if self.kind=='geometric':return(1-p['q'])*p['q']**k if k>=0 else 0.
        if self.kind=='zero':return float(k==0)
        if self.kind=='poisson':return math.exp(-p['mean']+k*math.log(p['mean'])-math.lgamma(k+1))if k>=0 and p['mean']>0 else float(k==0)
        raise AssertionError('UNSUPPORTED_PRIOR_KIND')
    def mean(self):
        if self.kind=='mixture':return(1-self.blend)*math.fsum(w*y for w,y in zip(self.weights,self.support))+self.blend*self.prior.mean()
        if self.kind=='signed':return self.p['center']
        if self.kind=='geometric':return self.p['q']/(1-self.p['q'])
        return self.p.get('mean')or 0.
    def event(self,line):
        L=Decimal(str(line));k=int(L.to_integral_value(rounding=ROUND_FLOOR));at=self.cdf(k);u=self.cdf(k-1)if L==k else at
        v=dict(over=1-at,under=u,push=at-u if L==k else 0.)
        assert min(v.values())>=-1e-10 and max(v.values())<=1+1e-10 and abs(math.fsum(v.values())-1)<1e-10
        # Same registered floating-dust canonicalization; no statistical smoothing.
        v={key:min(1.,max(0.,x))for key,x in v.items()};z=math.fsum(v.values());return{k:x/z for k,x in v.items()}


def grade(y,line,side):
    y,L=Decimal(str(y)),Decimal(str(line));return'PUSH'if y==L else'WIN'if((y>L)==(side=='over'))else'LOSS'
def metrics(rows):
    valid=[r for r in rows if r['p']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];brier=[];logs=[]
    for r in valid:
        y,L=Decimal(str(r['actual'])),Decimal(str(r['line']));state='over'if y>L else'under'if y<L else'push';p=r['p']
        brier.append(.5*math.fsum((p[k]-int(state==k))**2 for k in('under','push','over')));logs.append(-math.log(p[state])if p[state]>0 else math.inf)
    return dict(n=len(valid),brier=math.fsum(brier)/len(valid)if valid else None,log_loss=math.inf if any(math.isinf(v)for v in logs)else math.fsum(logs)/len(valid)if valid else None,infinite_log_losses=sum(math.isinf(v)for v in logs))


def c_rows(croot):
    versions={}
    for d in read(croot/'reports/abc-championship/C_INPUT_BINDINGS.json')['datasets']:
        f=croot/d['path'];assert sha(f)==d['SHA256']
        for r in read(f)['rows']:versions[r['record_id']]=r
    first={};fields=('category','game_id','player_id','method_id','method_version','selector_id','policy_id','venue','product','line_tier','evidence_tier')
    for r in versions.values():
        key=tuple(r[k]for k in fields);order=(r['decision_UTC'],r['scoring_snapshot_id'])
        if key not in first or order<first[key][0]:first[key]=(order,r)
    return[r for _,r in first.values()if r['venue']=='pinnacle'and r['season']==2026 and r['week']in(2,3)]


def run(repo,evidence,croot,v1,out,private):
    p=read(v1/'FROZEN_PACKAGE.json');assert sha(v1/'SOURCE_SNAPSHOT_V1.py')==p['code_sha256'];run=read(out/'RUN_RECEIPT.json');m=read(out/'PRIVATE_DERIVATIVE_MANIFEST.json');assert sha(private)==m['sha256'];rows=read(private)['rows'];assert len(rows)==15488 and private.stat().st_size==9076411
    fits={};fit_by_slot={};feature_fields=collections.Counter();model_count=0
    for b in p['fits']:
        file=repo/b['fit_receipt'];assert sha(file)==b['fit_sha256'];f=read(file);fits[b['fit_receipt']]=f;fit_by_slot[b['source_folder'],f['slot']]=b['fit_receipt'];t=stamp(f['fit_cutoff_utc'])
        assert f['training_membership_sha256']==b['training_membership_sha256']
        for k in('latest_training_label_available','latest_training_feature_available','latest_training_consumed_feature_available'):
            if k in f:feature_fields[k]+=1
            if f.get(k)is not None:assert f[k]<t
        if b['model']:assert stamp(f['actual_fit_started_at'])<=stamp(f['actual_fit_completed_at'])<stamp(p['at_utc'])
        else:assert f['state']=='NO_FIT_INSUFFICIENT_TRAINING'and f['actual_fit_started_at']is None and f['actual_fit_completed_at']is None
        if b['model']:
            file=evidence/b['model']['member_id'];assert sha(file)==b['model']['sha256']and file.stat().st_size==b['model']['bytes'];model_count+=1
    source={};source_count=0
    for b in p['members']:
        file=evidence/b['member_id'];assert sha(file)==b['sha256']and file.stat().st_size==b['bytes'];folder=b['member_id'].split('/')[0]
        for r in read(file)['rows']:
            if r['population']!='primary'or r['product_id']!='mean':continue
            fit=fit_by_slot[folder,r['fit_slot']];source[fit,r['game_id'],r['player_id']]=r;source_count+=1
    assert source_count==p['source_primary_mean_rows']==26032 and len(fits)==128 and model_count==88
    cr=c_rows(croot);byoffer=collections.defaultdict(dict)
    for r in cr:byoffer[r['offer_id']][r['method_id']]=r
    assert len(byoffer)==968
    expected={};counts=collections.Counter();representatives={};maximum_moment_error=0.;ties=0
    for r in rows:
        q=byoffer[r['offer_id']]['P2_LAW'];assert all(r[k]==q[v]for k,v in [('game_id','game_id'),('player_id','player_id'),('target','category'),('actual','actual'),('line','line'),('week','week')]);params=r['law_parameters'];law=None if params is None else AnalyticLaw(params);pp=None;src=None
        if law:
            fit=r['fit_receipt'];f=fits[fit];src=source[fit,r['game_id'],r['player_id']];assert src['position']==r['position']and src['cutoff']==stamp(q['decision_UTC'])==stamp(q['kickoff_UTC']);assert src['latest_feature_available']is None or src['latest_feature_available']<src['cutoff'];assert stamp(f['fit_cutoff_utc'])<=src['cutoff'];assert src['distribution_summary']==r['saved_summary']
            s=r['saved_summary'];delta=abs(law.mean()-s['mean']);maximum_moment_error=max(maximum_moment_error,delta);assert close(law.mean(),s['mean'])and close(law.mean(),src['prediction']);assert close(law.pmf(0),s['zero_mass'])
            for field,prob in[('lower_median',.5),('q05',.05),('q95',.95)]:assert law.cdf(s[field])>=prob-1e-10 and law.cdf(s[field]-1)<=prob+1e-10
            pp=law.event(r['line']);assert all(close(pp[k],r['probabilities'][k],1e-11)for k in pp)
            k=math.floor(r['line']);assert close(law.cdf(k)-law.cdf(k-1),law.pmf(k),1e-11);lower=law.event(r['line']-1);higher=law.event(r['line']+1);assert lower['over']>=pp['over']-1e-10>=higher['over']-2e-10 and lower['under']<=pp['under']+1e-10<=higher['under']+2e-10
            side=None if abs(pp['over']-pp['under'])<=1e-12 else'over'if pp['over']>pp['under']else'under'
            if side is None:ties+=1
            elif Decimal(str(r['line']))%1==Decimal('.5'):assert side==('over'if s['lower_median']>r['line']else'under')
            counts[params['kind']]+=1
            if params['kind']=='mixture':
                family='D1'if':D1:'in r['method_key']else'D2'if':D2:'in r['method_key']else'C02'if'c02'in r['method_key']else'LEAF';tag=family,r['target']
                if r['target']in('pass_yd','rec')and tag not in representatives:representatives[tag]=(r,src)
        else:side=None;assert r['probabilities']is None and r['fit_receipt']is None
        state='UNAVAILABLE_FORECAST'if pp is None else'ABSTAIN'if side is None else'UNKNOWN_PARTICIPATION'if r['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL'else'MISSING_ACTUAL'if r['actual']is None else grade(r['actual'],r['line'],side)
        assert side==r['selected_side']and state==r['statistical_state']
        rr=dict(r,p=pp,state=state,chosen=side);expected[r['method_key'],r['target'],r['offer_id']]=rr
    groups=collections.defaultdict(list)
    for(key,target,oid),r in expected.items():groups[key,target].append(r)
    assert len(groups)==64 and sum(counts.values())==14672
    scores=read(out/'SCORES.json');sideviews=[s for s in scores if s['record_kind']=='prop_selection_evaluation'];properviews=[s for s in scores if s['record_kind']=='prop_threshold_probability_evaluation'];assert len(sideviews)==576 and len(properviews)==192
    for s in sideviews:
        pool=[r for r in groups[s['procedure_id'],s['target']]if s['week']=='ALL'or r['week']==int(s['week'])];sub=[r for r in pool if r['chosen']is not None and(s['side']=='Combined'or s['side']==r['chosen'])];c=collections.Counter(r['state']for r in sub);a=s['selection_metrics'];assert s['forecast_rows']==len(sub)and s['n']==c['WIN']+c['LOSS']and a['WIN']==c['WIN']and a['LOSS']==c['LOSS'];assert a['selection_pool_count']==len(pool)
        assert a['hit_rate']==(c['WIN']/(c['WIN']+c['LOSS'])if c['WIN']+c['LOSS']else None)
        assert a['technical_unavailable']==sum(r['p']is None for r in pool);assert a['admitted_rule_abstentions']==sum(r['p']is not None and r['chosen']is None for r in pool)
        assert a['fallback_status_unknown']==sum(r['p']is None or r['fallback']=='NOT_RETAINED'for r in pool)
        assert a['fallback_issued']==sum(r['p']is not None and r['fallback']not in('none',False,None,'NOT_RETAINED')for r in pool)
        met=metrics(sub)
        for k in('n','brier','log_loss','infinite_log_losses'):
            value=a['probability_scores'][k];value=math.inf if value=='Infinity'else value;assert close(met[k],value)
    for s in properviews:
        pool=[r for r in groups[s['procedure_id'],s['target']]if s['week']=='ALL'or r['week']==int(s['week'])];met=metrics(pool);assert s['forecast_rows']==len(pool)and s['admitted_forecast_rows']==sum(r['p']is not None for r in pool)
        for k in('n','brier','log_loss','infinite_log_losses'):
            value=s[k];value=math.inf if value=='Infinity'else value;assert close(met[k],value)
    masks=read(out/'OWNER_LOCAL_MASKS.json');assert len(masks)==192
    for msk in masks:
        pool=[r for r in groups[msk['procedure_id'],msk['target']]if msk['week']=='ALL'or r['week']==int(msk['week'])];ids=sorted(r['offer_id']for r in pool if r['p']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL');assert msk['safe_C_offer_ids']==ids and msk['n']==len(ids)and hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest()==msk['sha256']
    baselines=read(out/'PROBABILITY_BASELINES.json');assert len(baselines)==768
    for s in baselines:
        pool=[r for r in groups[s['procedure_id'],s['target']]if(s['week_view']=='ALL'or r['week']==int(s['week_view']))and r['p']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];controls=[];own=[]
        for r in pool:
            if s['control']=='NEUTRAL_HALFPOINT_50_50':
                if Decimal(str(r['line']))%1!=Decimal('.5'):continue
                pp=dict(under=.5,over=.5,push=0.)
            else:
                q=byoffer[r['offer_id']].get(s['control'])
                if q is None or q.get('p_over')is None:continue
                pp={k:q['p_'+k]for k in('under','over','push')}
            controls.append(dict(r,p=pp));own.append(r)
        a,b=metrics(own),metrics(controls);assert a['n']==b['n']==s['n']
        if a['n']:assert close(a['brier'],s['candidate_brier'])and close(b['brier'],s['control_brier'])and close(a['brier']-b['brier'],s['brier_delta'])
        if s['control']=='NEUTRAL_HALFPOINT_50_50'and a['n']:assert b['brier']==.25
    pairs=read(out/'PAIRED_CONTROLS.json');assert len(pairs)==768
    for p_ in pairs:
        pool=[r for r in groups[p_['procedure_id'],p_['target']]if p_['week_view']=='ALL'or r['week']==int(p_['week_view'])];paired=[(r,byoffer[r['offer_id']][p_['control_id']])for r in pool if r['state']in('WIN','LOSS')and byoffer[r['offer_id']][p_['control_id']]['status']in('WIN','LOSS')];aw=sum(r['state']=='WIN'for r,q in paired);bw=sum(q['status']=='WIN'for r,q in paired);assert(len(paired),aw,bw,aw-bw)==(p_['common_decided'],p_['candidate_wins'],p_['control_wins'],p_['win_difference'])
    # Representative histograms: own-run hash-qualified bytes only; no estimator calls.
    sys.path.insert(0,str(repo));import numpy as np
    from nfl_v2 import distribution_wave_v2 as module_new,distribution_wave as module_old
    from sklearn.ensemble import ExtraTreesRegressor
    def forbidden(*args,**kwargs):raise AssertionError('INDEPENDENT_ESTIMATOR_EXECUTION_FORBIDDEN')
    histogram_checks=[];bound={x['fit_receipt']:x for x in p['fits']}
    with ExitStack()as stack:
        for cls,names in[(module_new.FittedLawModel,('predict','fit')),(module_old.FittedLawModel,('predict','fit')),(ExtraTreesRegressor,('predict','apply','fit','decision_path')),(module_new.Design,('transform','fit')),(module_old.Design,('transform','fit'))]:
            for name in names:stack.enter_context(patch.object(cls,name,forbidden))
        for tag,(r,src)in sorted(representatives.items()):
            b=bound[r['fit_receipt']];modelpath=evidence/b['model']['member_id'];assert sha(modelpath)==b['model']['sha256'];model=pickle.loads(gzip.decompress(modelpath.read_bytes()));params=r['law_parameters'];assert model.support.tolist()==params['support']and len(model.hist)==len(src['law_reference']['leaf_ids'])==32
            treeweights=[]
            for matrix,leaf in zip(model.hist,src['law_reference']['leaf_ids']):
                row=matrix[int(leaf)];row=row.toarray()if hasattr(row,'toarray')else np.asarray(row);v=np.asarray(row,dtype=float).ravel().tolist();assert min(v)>=0 and abs(math.fsum(v)-1)<1e-10;treeweights.append(v)
            weight=[math.fsum(t[j]for t in treeweights)/32 for j in range(len(params['support']))];z=math.fsum(weight);weight=[v/z for v in weight];assert all(close(a,b_,1e-11)for a,b_ in zip(weight,params['weights']));assert params['prior']==fits[r['fit_receipt']]['prior_parameters'][r['position']]
            histogram_checks.append(dict(family=tag[0],target=tag[1],fit_receipt=r['fit_receipt'],model_sha256=b['model']['sha256'],trees=32,source_leaf_ids_verified=True,support_size=len(weight),prior_mix=.05));del model
    summary=[]
    for target in('pass_yd','rush_yd','rec','rec_yd'):
        rr=[s for s in sideviews if s['target']==target and s['week']=='ALL'and s['side']=='Combined'and s['n']];best=max(s['selection_metrics']['hit_rate']for s in rr);leaders=[s for s in rr if s['selection_metrics']['hit_rate']==best];bestprob=min((s for s in properviews if s['target']==target and s['week']=='ALL'and s['n']),key=lambda s:s['brier']);summary.append(dict(target=target,combined_wins=leaders[0]['selection_metrics']['WIN'],combined_decided=leaders[0]['n'],combined_rate=best,combined_leaders=[s['procedure_id']for s in leaders],lowest_brier=bestprob['brier'],lowest_brier_procedure=bestprob['procedure_id'],probability_n=bestprob['n'],beats_neutral_025=bestprob['brier']<.25))
    result=dict(state='PASS_INDEPENDENT_SAVED_PMF_CDF_AND_SCORING',private_source_sha256=sha(private),private_source_bytes=private.stat().st_size,source_fit_receipts_verified=128,original_completed_fits_with_execution_clocks=88,original_no_fit_startup_slots_with_null_clocks=40,source_chunk_hashes_verified=128,own_model_hashes_verified=88,training_availability_field_variants=dict(feature_fields),source_primary_mean_rows=source_count,retained_method_offer_rows=len(rows),available_laws=sum(counts.values()),law_kind_counts=dict(counts),source_missing_unavailable_rows=816,same_law_median_direction_explicit_ties=ties,source_moment_quantile_zero_mass_parity_rows=sum(counts.values()),maximum_mean_absolute_difference=maximum_moment_error,representative_histogram_reconstructions=histogram_checks,estimator_calls=0,selection_side_views_verified=576,proper_views_verified=192,matched_probability_baseline_views_verified=768,paired_direction_control_views_verified=768,mask_memberships_verified=192,summary=summary,retention='Original v1 post-write cap failure preserved; complete9076411byte file exceeds old8388608cap by687803bytes. v2 reuses same bytes with0newprivate derivatives; no offhost recovery or fit-gate waiver claimed.',limitations=['FullPMF arithmetic and all output aggregates independently recomputed; histogram origin independently sampled for8hash-qualified own-run models rather than every original tree lookup.','Fit/query availability maxima and actual source hashes checked; underlying historical training-source vintages are not authenticated by a hash.','Timing-unverified last-recorded quote panel, retrospective primary participant support and exposed two weeks; not original issuance or a release-qualified selector.','Unknown source rows are technical unavailable, not intentional confidence abstention or completed fallback.'])
    (out/'INDEPENDENT_RETAINED_LEAF_LAW_VERIFICATION_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('evidence',type=Path);p.add_argument('croot',type=Path);p.add_argument('v1',type=Path);p.add_argument('out',type=Path);p.add_argument('private',type=Path);a=p.parse_args();run(a.repo,a.evidence,a.croot,a.v1,a.out,a.private)
