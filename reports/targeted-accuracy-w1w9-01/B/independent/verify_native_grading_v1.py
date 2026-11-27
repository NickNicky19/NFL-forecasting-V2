"""Separate Decimal grading, selection and calibration arithmetic for M2."""
from __future__ import annotations
import argparse, collections, datetime, gzip, hashlib, json, math, pathlib, sys, time
from decimal import Decimal
import numpy as np
from scipy import stats

ROOT=pathlib.Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from nfl_v2 import targeted_qb_m2 as models
from prefit_math_review_v1 import beta_integral_cdf

OUT=pathlib.Path(__file__).resolve().parent;EVAL=OUT.parent/'evaluation';WAVE=OUT.parent/'wave-v1'
NEW=['M2_P2_BIN','M2_P2_BB','M2_C1_BIN','M2_C1_BB','M2_C2_BIN','M2_C2_BB','D_M2','UNCHANGED_ATT','RETAINED_B0']
def read(p):
    p=pathlib.Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def key(r):return r['game_id'],r['player_id'],r['category']
def epoch(x):
    if isinstance(x,(float,int)):return float(x)
    return datetime.datetime.fromisoformat(x.replace('Z','+00:00')).timestamp()
def grade(actual,line,side):
    if side not in ['OVER','UNDER']:return 'ABSTAIN'
    a,b=Decimal(str(actual)),Decimal(str(line))
    if a==b:return 'PUSH'
    return 'WIN'if(a>b)==(side=='OVER')else'LOSS'
def simple_cdf(p,k):
    if k<0:return 0.
    if p['kind']=='gamma_poisson_count':return 1. if not p['mean']else float(stats.nbinom.cdf(k,p['shape'],p['shape']/(p['shape']+p['mean'])))
    if p['kind']=='leaf_mixture':
        weights=np.asarray(p['weights'],float);weights/=weights.sum();emp=float(weights[np.asarray(p['support'])<=k].sum())
        pr=p['prior'];v=1-pr['q']**(k+1)if pr['kind']=='geometric'else 1.
        return (1-p['mixture'])*emp+p['mixture']*v
    if p['kind']=='integrated_nb_beta_binomial':
        return beta_integral_cdf(k,p['attempt_mean'],p['attempt_shape'],p['conversion_mean'],1/(p['precision']+1))[0]
    raise ValueError('Unregistered law')

def choose(rows,kind,value,pool='Combined'):
    chosen=[];seen=0
    for t in sorted({r['kickoff']for r in rows}):
        batch=[r for r in rows if r['kickoff']==t];seen+=len(batch)
        good=[r for r in batch if r['side']in ['OVER','UNDER']and(pool=='Combined'or r['side']==pool)]
        good=sorted(good,key=lambda r:(-r['confidence'],r['game_id'],r['player_id'],r['category']))
        slots=max(0,int(value*seen)-len(chosen))if kind=='FRACTION'else max(0,value-len(chosen))
        chosen.extend(good[:slots])
    return {key(r)for r in chosen}

def main():
    start=time.process_time();ap=argparse.ArgumentParser();ap.add_argument('--sources',type=pathlib.Path,required=True);a=ap.parse_args()
    checks=0;problems=[]
    def check(ok,label):
        nonlocal checks
        checks+=1
        if not bool(ok):problems.append(label)
    sources={int(w):pathlib.Path(p)for w,p in read(a.sources).items()};offers=[]
    for week in range(5,10):
        for r in read(sources[week])['rows']:
            if r.get('target')not in('pass_cmp','pass_att'):continue
            if week==8 and not(r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original'and not r.get('method_key')):continue
            check(r['actual']is not None and r['label_state']=='SUPPORTED','Qualified explicit outcome')
            offers.append(r)
    check(len(offers)==284 and len({(r['game_id'],r['player_id'],r['target'])for r in offers})==284,'No repeated primary opportunities')
    packets=[read(p)for p in sorted((WAVE/'predictions').glob('2026-W*.json.gz'))];preds=[r for p in packets for r in p['rows']]
    origins={p['week']:p['fit_cutoff']for p in packets};predmap={(r['method'],r['game_id'],r['player_id'],r['target']):r for r in preds}
    for path in sorted((ROOT/'reports/information-first-20261112-01/B/completion-wave-v1/predictions').glob('2026-W*.json.gz')):
        for r in read(path)['rows']:
            if r['method']=='B0':predmap['RETAINED_B0',r['game_id'],r['player_id'],r['target']]=r
    main=read(EVAL/'MAIN_TABLES_V1.json.gz');selected=read(EVAL/'SELECTIVE_TABLES_V1.json.gz');lookup={(r['method'],r['policy'],str(r['window'])):r for r in main+selected}
    raw={};max_CDF_difference=0.;manual_grades=0;fullrecords=[];selection_memberships=0;calibration_checks=0
    def compare(rows,method,policy,window):
        old=lookup[method,policy,str(window)];take=[r for r in rows if r['side']in['OVER','UNDER']]
        for side in ['OVER','UNDER','COMBINED']:
            group=take if side=='COMBINED'else[r for r in take if r['side']==side];w=sum(r['status']=='WIN'for r in group);l=sum(r['status']=='LOSS'for r in group)
            check((old[side]['wins']or 0)==w and(old[side]['losses']or 0)==l and old[side]['decided']==w+l and old[side]['selected']==len(group),'Own-side independent counts '+method+policy+str(window)+side)
        check(old['selected']==len(take),'Selected denominator')
        check(old['selected_membership_SHA256']==digest(sorted(key(r)for r in take)),'Selected canonical identities')
        check(old['unknown']==0,'No unsupported zeros or hidden unknowns introduced')
        pts=[r for r in rows if r.get('point')is not None]
        if pts:
            mae=sum(abs(r['point']-r['actual'])for r in pts)/len(pts)
            check(abs(mae-old['numerical']['MAE'])<1e-10,'Numerical error on exact offer mask')
    for method in NEW:
        target='pass_att'if method=='UNCHANGED_ATT'else'pass_cmp';policy_names=['LAW']if method=='RETAINED_B0'else['MEAN','MEDIAN','LAW']
        board=[o for o in offers if o['target']==target]
        for policy in policy_names:
            group=[]
            for o in board:
                pr=predmap['COMMON_EXPOSURE'if method=='UNCHANGED_ATT'else method,o['game_id'],o['player_id'],target]
                p=pr['law'];k=math.floor(o['line']);under=simple_cdf(p,k);probs={'over':1-under,'under':under,'push':0.}
                # Ranking uses the exact executable raw probabilities after
                # independently checking them. This preserves floating ties.
                executable=models.restore_law(p);actual_under=executable.cdf(k);max_CDF_difference=max(max_CDF_difference,abs(actual_under-under))
                check(abs(actual_under-under)<3e-8,'Independent event probability')
                actualprobs={'over':1-actual_under,'under':actual_under,'push':0.}
                point=pr['mean']if policy=='MEAN'else pr['lower_median']if policy=='MEDIAN'else None
                if point is not None:
                    v,l=Decimal(str(point)),Decimal(str(o['line']));side='OVER'if v>l else'UNDER'if v<l else'ABSTAIN'
                else:side='OVER'if probs['over']>probs['under']else'UNDER'if probs['under']>probs['over']else'ABSTAIN'
                row={'game_id':o['game_id'],'player_id':o['player_id'],'category':target,'week':o['week'],'kickoff':epoch(o['kickoff']),
                     'side':side,'status':grade(o['actual'],o['line'],side),'actual':o['actual'],'line':o['line'],'point':point,'probs':actualprobs,
                     'confidence':actualprobs[side.lower()]if side in ['OVER','UNDER']else None}
                group.append(row);manual_grades+=1
            codepolicy='P2_STATISTICAL_LAW'if method=='RETAINED_B0'else policy
            for window in ['ALL']+list(range(5,10)):
                rr=group if window=='ALL'else[r for r in group if r['week']==window];compare(rr,method,codepolicy,window)
            if policy=='LAW':
                raw[method]=group;old=lookup[method,codepolicy,'ALL'];brier=sum((r['probs']['over']-int(r['actual']>r['line']))**2 for r in group)/len(group)
                ll=-sum(math.log(r['probs']['over'if r['actual']>r['line']else'under'])for r in group)/len(group)
                check(abs(brier-old['probability']['half_three_state_Brier'])<1e-10,'Proper Brier arithmetic')
                check(abs(ll-old['probability']['log_loss'])<1e-10,'Proper log loss arithmetic')
                fullrecords.append({'method':method,'OVER':old['OVER'],'UNDER':old['UNDER'],'COMBINED':old['COMBINED'],'Brier':brier,'log_loss':ll})
    for method,rows in raw.items():
        cal=[]
        for r in rows:
            b=min(9,int(r['confidence']*10));earlier=[s for s in rows if s['kickoff']+7*86400<origins[r['week']]and s['status']in['WIN','LOSS']and min(9,int(s['confidence']*10))==b]
            t=dict(r);t['cal_confidence']=(sum(s['status']=='WIN'for s in earlier)+20*r['confidence'])/(len(earlier)+20);cal.append(t)
        policies={}
        for frac,name in [(1.,'COVERAGE_100'),(.5,'COVERAGE_50'),(.25,'COVERAGE_25'),(.1,'COVERAGE_10')]:
            policies[name]=set().union(*(choose([r for r in rows if r['week']==w],'FRACTION',frac)for w in range(5,10)))
        for K in [6,10,20]:
            for pool in ['Combined','OVER','UNDER']:
                policies[f'TOP_{K}_{pool}']=set().union(*(choose([r for r in rows if r['week']==w],'TOP',K,pool)for w in range(5,10)))
        for threshold in [.75,.8,.9]:
            policies[f'THRESHOLD_{int(threshold*100)}_RAW']={key(r)for r in rows if r['confidence']>=threshold}
            policies[f'THRESHOLD_{int(threshold*100)}_CALIBRATED_RELIABILITY']={key(r)for r in cal if r['cal_confidence']>=threshold}
        for name,chosen in policies.items():
            gg=[dict(r)if key(r)in chosen else dict(r,side='ABSTAIN',status='ABSTAIN')for r in rows]
            for window in ['ALL']+list(range(5,10)):
                rr=gg if window=='ALL'else[r for r in gg if r['week']==window];compare(rr,method,name,window);selection_memberships+=1
            calibration_checks+=int(name.endswith('CALIBRATED_RELIABILITY'))
    differences=[]
    for parent in ['P2','C1','C2']:
        aa={key(r):r for r in raw['M2_'+parent+'_BIN']};bb={key(r):r for r in raw['M2_'+parent+'_BB']}
        different=sum(aa[k]['side']!=bb[k]['side']for k in aa)
        differences.append({'parent':parent,'law_side_disagreements':different,'BIN_wins':sum(r['status']=='WIN'for r in aa.values()),'BB_wins':sum(r['status']=='WIN'for r in bb.values())})
    result={'id':'B_M2_INDEPENDENT_NATIVE_GRADING_AND_SELECTORS_v1','at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state':'PASS_WITH_STATED_SCOPE'if not problems else'FAIL','checks':checks,'problems':problems,
      'manual_Decimal_grades':manual_grades,'selected_membership_views':selection_memberships,'calibrated_threshold_policy_checks':calibration_checks,
      'largest_independent_CDF_difference':max_CDF_difference,'full_law_records':fullrecords,'BIN_BB_actual_side_differences':differences,
      'source_bindings':[{'week':w,'sha256':sha(p)}for w,p in sorted(sources.items())],'source_score_sha256':sha(EVAL/'SCORES.json'),
      'CPU_seconds':time.process_time()-start,'reviewer_optimizer_calls':0,'reviewer_NFL_fits':0,'new_source_reads':0,'private_rows_published':0,
      'limits':['NativeW5–9 only; no private A earlier offer rows inspected.','Source clocks and original issuance remain unverified at declared TierB.','Point/grade/aggregate logic is independent; raw count laws were additionally checked by separate beta integral. Exact executable event probabilities are used after parity checks to preserve floating-point rank ties.','New M2 selector model/policy history cannot inherit oldFTN results; original ordinal bridge is separate verification.','No new prospective picks, scientific superiority or production admission established by these checks.']}
    (OUT/'NATIVE_GRADING_AND_SELECTION_VERIFICATION_V1.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'state':result['state'],'checks':checks,'problems':problems[:8],'manual_grades':manual_grades,'membership_views':selection_memberships,'CPU_seconds':result['CPU_seconds']}))
    if problems:raise SystemExit(1)

if __name__=='__main__':main()
