"""Independent C02 label, score, control, prefix and retained-law audit.

Reads only W1-W7 historical outcomes; no fits or new forecast issuance.
"""
import argparse
from collections import defaultdict, Counter
from decimal import Decimal
from functools import lru_cache
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import pickle
import sys

import numpy as np
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'reports/continuation-20261030'))
from check_new_wave_prefixes import load,clock,canonical
from check_retained_distribution_math import summaries
PUBLIC=ROOT/'reports/continuation-20261030b/ordered-information-ablation-v1'
KEEP=(0,1,2,3,16,17,18,19)
POSITIONS=('QB','RB','WR','TE')

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(p):return json.loads(gzip.decompress(p.read_bytes()))
def ident(r):return tuple(r[k]for k in('game_id','player_id','target','population'))
def ckey(r):return(r['target'],r['policy_id'],r['game_id'],r['player_id'],r['population'],r['product_id'])
def close(a,b):
    if b==math.inf:assert a in('Infinity',math.inf);return
    assert(a is None and b is None)or(a is not None and b is not None and math.isclose(float(a),float(b),rel_tol=4e-11,abs_tol=4e-10)),(a,b)
def grid(x):
    y=Decimal(str(x))*50;assert y==y.to_integral_value();return int(y)

def metrics(rs,target,product):
    selected=[r for r in rs if r['prediction']is not None and r['actual']is not None];n=len(selected)
    out=dict(n=n,forecast_rows=len(rs),fallback_rows=sum(r['fallback']!='none'for r in rs),scored_fallback_rows=sum(r['fallback']!='none'for r in selected),unique_games=len({r['game_id']for r in selected}),forecast_games=len({r['game_id']for r in rs}))
    if not n:return dict(out,mae=None,mse=None,rmse=None,bias=None)
    errors=[r['prediction']-r['actual']for r in selected];absolute=sorted(map(abs,errors));mse=math.fsum(v*v for v in errors)/n
    def q(p):
        x=(n-1)*p;i,j=math.floor(x),math.ceil(x);return absolute[i]+(absolute[j]-absolute[i])*(x-i)
    out.update(mae=math.fsum(absolute)/n,mse=mse,rmse=math.sqrt(mse),bias=math.fsum(errors)/n,p90_abs=q(.9),p95_abs=q(.95),max_abs=absolute[-1],exact_rate=sum(v==0 for v in errors)/n)
    exact=[abs(grid(r['prediction'])-grid(r['actual']))for r in selected]if target=='nick-chart-ppr-v1'and product=='lower_median'else None
    for tolerance in(1,5,10):
        values,threshold=(exact,50*tolerance)if exact is not None else(absolute,tolerance)
        for inclusive in(False,True):
            k=f"abs_{'le'if inclusive else'lt'}_{tolerance}";hits=sum(v<=threshold if inclusive else v<threshold for v in values);out[k]=hits/n
    if target=='anytime_td':
        losses=[-math.log(r['prediction']if r['actual']else 1-r['prediction'])if(r['prediction']if r['actual']else 1-r['prediction'])>0 else math.inf for r in selected]
        out.update(brier=mse,prevalence=math.fsum(r['actual']for r in selected)/n,log_loss=math.fsum(losses)/n)
    ds=[r['distribution_summary']for r in selected];inf=sum(d['infinite_nll']for d in ds)
    out.update(CRPS=math.fsum(d['crps']for d in ds)/n,NLL=None if inf else math.fsum(d['nll']for d in ds)/n,infinite_NLL=inf,interval90_width=math.fsum(d['interval90_width']for d in ds)/n,interval90_coverage=sum(d['interval90_covered']for d in ds)/n,mean_zero_mass=math.fsum(d['zero_mass']for d in ds)/n)
    return out

def verify(private,source):
    p=json.loads((PUBLIC/'FROZEN_PROTOCOL.json').read_text());run=json.loads((PUBLIC/'RUN_RECEIPT.json').read_text());counts=Counter()
    assert sha(ROOT/'nfl_v2/ordered_information_ablation.py')==p['code_sha256']==run['code_sha256']
    for name,digest in p['helpers'].items():assert sha(ROOT/'nfl_v2'/name)==digest
    for field,name in [('law_code_sha256','distribution_laws.py'),('precision_code_sha256','precision_grid.py'),('scoring_code_sha256','scoring.py')]:assert sha(ROOT/'nfl_v2'/name)==p[field]
    assert sha(PUBLIC/'FROZEN_PROTOCOL.json')==run['protocol_sha256']
    assert sha(private/'frozen-queries.json')==p['frozen_queries_sha256']
    packet=private/run['private_prediction_packet']['name'];assert sha(packet)==run['private_prediction_packet']['sha256']
    records=decode(packet)['rows'];assert len(records)==run['forecast_output_views']==134168
    rows,history,games=load(source,p);truth={(r['game_id'],r['player_id']):r for r in rows}
    controls={}
    for spec,directory in zip(p['control_prediction_sources'],('distribution-wave-v2','chart-wave-v1')):
        path=private.parent/directory/spec['artifact_id'];assert sha(path)==spec['sha256']
        with gzip.open(path,'rt')as handle:
            for r in csv.DictReader(handle):
                if r['season']!='2026'or int(r['week'])>7 or r['family']!='ordered_leaf_cdf':continue
                controls[ckey(r)]={k:None if r[k]==''else float(r[k])for k in('prediction','actual')}
                controls[ckey(r)].update(fallback=r['fallback'],procedure_id=r['procedure_id'])
    groups=defaultdict(list)
    for r in records:
        assert r['season']==2026 and r['week']in range(1,8)
        target=r['target'];expected=truth[r['game_id'],r['player_id']]['values'][target]
        if target=='nick-chart-ppr-v1'and expected is not None:expected/=50
        close(r['actual'],expected);counts['independent_raw_labels']+=1
        old=controls[ckey(r)]
        assert r['control_prediction']==old['prediction']and r['control_fallback']==old['fallback']and r['control_procedure_id']==old['procedure_id']
        close(r['actual'],old['actual']);counts['original_control_row_joins']+=1
        endings=[('ALL','ALL','ALL'),(str(r['week']),'ALL','ALL'),('ALL',r['position'],'ALL')]
        if r['fallback']=='none':endings.append(('ALL','ALL','LEARNED_ONLY'))
        if r['fallback']==r['control_fallback']=='none':endings.append(('ALL','ALL','PAIRED_LEARNED_OVERLAP'))
        for suffix in endings:groups[(r['policy_id'],target,r['population'],r['product_id'])+suffix].append(r)
    scores=json.loads((PUBLIC/'SCORES.json').read_text());highlights=[];examples={};maxdelta=0.
    for score in scores:
        k=(score['policy_id'],score['target'],score['population'],score['product_id'],str(score['week']),score['position'],score['fallback_view']);rs=groups[k];expected=metrics(rs,score['target'],score['product_id'])
        for field,value in expected.items():
            close(score[field],value);counts['native_probability_law_aggregate_checks']+=1
            if isinstance(value,(int,float))and math.isfinite(value):maxdelta=max(maxdelta,abs(score[field]-value))
        selected=[r for r in rs if r['actual']is not None and r['prediction']is not None and r['control_prediction']is not None]
        comparison=score['comparison']
        if selected:
            measure=lambda prediction,y:(prediction-y)**2 if score['target']=='anytime_td'else abs(prediction-y)
            a=[measure(r['prediction'],r['actual'])for r in selected];b=[measure(r['control_prediction'],r['actual'])for r in selected];delta=[x-y for x,y in zip(a,b)]
            close(comparison['candidate_error'],math.fsum(a)/len(a));close(comparison['comparator_error'],math.fsum(b)/len(b));assert comparison['paired_n']==len(selected)
            assert comparison['membership_sha256']==hashlib.sha256(canonical(sorted(ident(r)for r in selected))).hexdigest()
            assert comparison['status']=='PAIRED_RETAINED_ROWS';counts['paired_control_aggregate_checks']+=5
            if score['policy_id']=='H-MULTI-COMMON'and score['population']=='primary'and score['week']==score['position']==score['fallback_view']=='ALL':
                highlights.append(dict(target=score['target'],product=score['product_id'],n=len(selected),candidate_error=math.fsum(a)/len(a),ordered_control_error=math.fsum(b)/len(b),candidate_minus_control=math.fsum(delta)/len(delta)))
                for r,d,la,lb in zip(selected,delta,a,b):
                    label='win'if d<0 else'loss'if d>0 else'tie'
                    if label not in examples:examples[label]=dict(public_safe_id=hashlib.sha256(canonical(ident(r))).hexdigest()[:16],target=r['target'],product=r['product_id'],candidate_loss=la,ordered_control_loss=lb)
        if score.get('precision_counts_exact_grid'):
            assert score['target']=='nick-chart-ppr-v1'and score['product_id']=='lower_median'
            for field,entry in score['precision_counts_exact_grid'].items():assert entry['denominator']==expected['n'];close(entry['rate'],expected[field]);assert entry['numerator']==round(expected[field]*expected['n']);counts['exact_grid_precision_counts']+=1
    @lru_cache(None)
    def feature(player,position,target,cutoff,floor):
        rs=[r for r in history.get(player,[])if r['season']>=floor and r['available']<cutoff][-8:];full=[]
        for w in(3,8):
            ys=[float(r['values'][target])for r in rs[-w:]if r['values'][target]is not None];full.extend((sum(ys)/len(ys)if ys else None,float(len(ys))))
        full.extend([None]*12);full.extend(float(position==v)for v in POSITIONS)
        return [full[i]for i in KEEP],rs[-1]['available']if rs else None
    with threadpool_limits(limits=2):
        for fitfile in sorted(PUBLIC.glob('*-FIT.json')):
            fit=json.loads(fitfile.read_text());target=fit['target'];floor=fit['feature_floor'];cutoff=clock(fit['fit_cutoff_utc']);policy=p['policies'][fit['policy_id']]
            roles=set(POSITIONS)if target=='nick-chart-ppr-v1'else set(p['source_role_contract']['primary'][target]+p['source_role_contract']['extended'].get(target,[]))
            train=[r for r in rows if r['position']in roles and r['values'][target]is not None and r['season']>=max(floor,policy['fit_floor'])and r['available']<cutoff]
            assert len(train)==fit['training_n'];assert hashlib.sha256(canonical([(r['game_id'],r['player_id'])for r in train])).hexdigest()==fit['training_membership_sha256']
            assert sorted({r['season']for r in train})==fit['training_seasons'];assert max((r['available']for r in train),default=None)==fit['latest_training_label_available']
            oldfitpath=Path(fit['control_fit_artifact']);assert sha(oldfitpath)==fit['control_fit_sha256'];oldfit=json.loads(oldfitpath.read_text())
            for field in('training_n','training_membership_sha256','fit_cutoff_utc','feature_floor','prior_parameters','prior_position_sample_counts'):assert oldfit[field]==fit[field]
            counts['training_control_membership_and_prior_checks']+=10
            maxima=[feature(r['player_id'],r['position'],target,r['kickoff'],floor)[1]for r in train]
            assert all(m is None or m<r['kickoff']for r,m in zip(train,maxima));assert max((v for v in maxima if v is not None),default=None)==fit['latest_training_feature_available']
            counts['all_training_feature_clock_checks']+=1
            desc=fit['query_features'];fp=private/desc['name'];assert sha(fp)==desc['sha256'];entries=decode(fp)
            for e in entries:
                q=e['query'];expected,maximum=feature(q['player_id'],q['position'],target,q['cutoff'],floor)
                for x,y in zip(expected,e['features']):close(x,y);counts['independent_projected_query_features']+=1
                assert maximum==e['latest_feature_available']and(maximum is None or maximum<q['cutoff'])
            if fit['model']:
                desc=fit['model'];path=private/desc['name'];assert sha(path)==desc['sha256'];model=pickle.loads(gzip.decompress(path.read_bytes()));counts['retained_models_hash_verified']+=1
                assert len(model.design.median)==8
            else:model=None
            fr=json.loads((PUBLIC/(fit['slot']+'-FORECAST.json')).read_text());path=private/fr['packet']['name'];assert sha(path)==fr['packet']['sha256'];saved=decode(path)['rows'];byid={ident(r):r for r in saved}
            learned=[e for e in entries if e['features'][3]>0];chosen=([learned[0]]if learned else[])+([entries[-1]]if entries else[])
            for e in chosen:
                q=e['query'];r=byid[ident(q)];law=fit['prior_parameters'][q['position']]
                if model is not None and e['features'][3]>0:
                    x=np.asarray([[math.nan if v is None else v for v in e['features']]])
                    design=np.column_stack((np.where(np.isfinite(x),x,model.design.median),~np.isfinite(x))).astype(float)
                    leaf=model.estimator.apply(design)[0];weights=sum((h[leaf[j]].toarray().ravel()/len(model.hist)for j,h in enumerate(model.hist)),start=np.zeros(len(model.support)));weights/=weights.sum()
                    law=dict(kind='mixture',support=model.support,weights=weights,prior=law)
                expected=summaries(law,r['actual_grid']if target=='nick-chart-ppr-v1'else r['actual']);scale=50 if target=='nick-chart-ppr-v1'else 1
                for field,value in expected.items():
                    if field in('mean','lower_median','q05','q95','interval90_width','crps')and value is not None:value/=scale
                    close(r['distribution_summary'][field],value);counts['independent_retained_law_summary_checks']+=1
                counts['representative_retained_laws']+=1
    return dict(status='PASS_RAW_LABELS_PAIRED_SCORES_ALL_PREFIXES_AND_RETAINED_LAW_SAMPLES',counts=dict(counts),score_views=len(scores),forecast_rows=len(records),max_float_difference=maxdelta,primary_H_MULTI_common_results=highlights,redacted_win_loss=examples,
                protocol_sha256=sha(PUBLIC/'FROZEN_PROTOCOL.json'),score_sha256=sha(PUBLIC/'SCORES.json'),prediction_packet_sha256=sha(packet),
                evidence='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC; exposed2026W1-W7; historical availability reconstructed',
                interpretation='Only explicit lag value/age/missing triplets and their imputation indicators removed; mean3/8 and their recency information remain. No new family or universal ordering claim.',new_fits=0,new_forecasts=0,week8_outcomes_read=0)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private-root',type=Path,required=True);parser.add_argument('--source-root',type=Path,required=True);args=parser.parse_args();report=verify(args.private_root,args.source_root)
    Path(__file__).with_name('C02_INDEPENDENT_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k!='primary_H_MULTI_common_results'}))
