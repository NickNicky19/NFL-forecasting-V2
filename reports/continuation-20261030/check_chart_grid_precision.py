"""Audit genuine chart lower-median tolerance precision on its exact .02 grid.

Original floats, forecasts, MAE and score files are not modified. Means are
excluded. This reports a scoring diagnostic correction, never predictive gain.
"""
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import csv,gzip,hashlib,json,sys

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def decode(p):return json.loads(gzip.decompress(p.read_bytes()))
def ident(r):return(r['game_id'],r['player_id'],r['target'],r['population'])
def grid(x):
    value=Decimal(str(x))*50
    assert value.is_finite()and value==value.to_integral_value(),str(x)
    return int(value)
def output(score,rows,artifact):
    rs=[r for r in rows if r['prediction']is not None and r['actual']is not None];n=len(rs);assert n==score['n']
    errors=[abs(grid(r['prediction'])-grid(r['actual']))for r in rs];updates={};changed=[]
    for tol in(1,5,10):
        for inclusive in(False,True):
            metric='abs_'+('le_'if inclusive else'lt_')+str(tol);hits=sum(e<=tol*50 if inclusive else e<tol*50 for e in errors)
            rate=hits/n if n else None;old=score.get(metric)
            updates[metric]=dict(numerator=hits,denominator=n,exact_grid_rate=rate,original_float_rate=old)
            if rate is not None and abs(rate-old)>1e-12:changed.append(metric)
    dims={k:score.get(k)for k in('record_id','procedure_id','history_regime','policy_id','target','population','product_id','week','season','position','fallback_view','cohort_id')}
    return dict(**dims,source_score_artifact=artifact,exact_grid_denominator=50,n=n,precision=updates,changed_metrics=changed)
def audit(public,private,cohort_public,cohort_private):
    direct=defaultdict(list);empirical=defaultdict(list);projection=[];unique={};rowdisagreements=defaultdict(int)
    run=json.loads((public/'RUN_RECEIPT.json').read_text())
    allrows=[]
    for receiptfile in sorted(public.glob('W0[1-7]-*-FORECAST.json')):
        desc=json.loads(receiptfile.read_text())['packet'];file=private/desc['bundle_name'];assert sha(file)==desc['sha256'];allrows.extend(decode(file)['rows'])
    d=run['empirical_prediction_packet'];file=private/d['bundle_name'];assert sha(file)==d['sha256'];emp=decode(file)['rows']
    for r in allrows:
        if r['product_id']!='lower_median':continue
        endings=[('ALL','ALL','ALL'),(str(r['week']),'ALL','ALL'),('ALL',r['position'],'ALL')]
        if r['fallback']=='none':endings.append(('ALL','ALL','LEARNED_ONLY'))
        for suffix in endings:direct[(r['family'],r['policy_id'])+suffix].append(r)
    for r in emp:
        if r['product_id']!='lower_median':continue
        for season,week,pos in[(str(r['season']),'ALL','ALL'),(str(r['season']),str(r['week']),'ALL'),(str(r['season']),'ALL',r['position']),('POOLED_2022_2026','ALL','ALL')]:empirical[(r['history_regime'],season,week,pos)].append(r)
    for s in json.loads((public/'SCORES.json').read_text()):
        if s['product_id']=='lower_median':projection.append(output(s,direct[(s['procedure_family_id'],s['policy_id'],str(s['week']),s['position'],s['fallback_view'])],'reports/continuation-20261030/chart-wave-v1/SCORES.json'))
    for s in json.loads((public/'EMPIRICAL_SCORES.json').read_text()):
        if s['product_id']=='lower_median':projection.append(output(s,empirical[(s['history_regime'],str(s['season']),str(s['week']),s['position'])],'reports/continuation-20261030/chart-wave-v1/EMPIRICAL_SCORES.json'))
    membership={tuple(r['key']):r for r in decode(cohort_private/'memberships.json.gz')};records=[r for r in allrows+emp if r['season']==2026]
    eligible=defaultdict(lambda:defaultdict(set))
    for r in records:
        k=r['procedure_id'],r['product_id'];eligible[k].setdefault(r['history_regime'],set())
        if r['fallback']=='none'and r['actual']is not None:eligible[k][r['history_regime']].add(ident(r))
    overlaps={k:set.intersection(*(v.get(a,set())for a in('H-CURRENT','H-RECENT','H-MULTI')))for k,v in eligible.items()};shared=set.intersection(*(v for arms in eligible.values()for v in arms.values()));groups=defaultdict(list)
    for r in records:
        if r['product_id']!='lower_median':continue
        views=['full_system']
        if r['fallback']=='none':views.append('own_learned_only')
        if ident(r)in overlaps[r['procedure_id'],r['product_id']]:views.append('three_history_learned_overlap')
        if ident(r)in shared:views.append('all_competitor_learned_overlap')
        for cohort in membership[ident(r)]['cohorts']:
            for view in views:groups[(r['procedure_id'],r['history_regime'],cohort,view)].append(r)
    for s in json.loads((cohort_public/'SCORES.json').read_text()):
        if s['product_id']=='lower_median':projection.append(output(s,groups[(s['procedure_id'],s['history_regime'],s['cohort_id'],s['fallback_view'])],'reports/continuation-20261030/chart-cohort-scorecards-v1/SCORES.json'))
    for r in allrows+emp:
        if r['product_id']!='lower_median'or r['actual']is None or r['prediction']is None:continue
        key=(r['procedure_id'],r['history_regime'],ident(r))
        if key in unique:continue
        unique[key]=True;e=abs(grid(r['prediction'])-grid(r['actual']));floating=abs(r['prediction']-r['actual'])
        for tol in(1,5,10):
            for inclusive in(False,True):
                exact=e<=tol*50 if inclusive else e<tol*50;old=floating<=tol if inclusive else floating<tol
                if exact!=old:rowdisagreements['abs_'+('le_'if inclusive else'lt_')+str(tol)]+=1
    return dict(status='CONFIRMED_EXACT_GRID_PRECISION_DIAGNOSTIC_DEFECT'if any(s['changed_metrics']for s in projection)else'NO_GRID_PRECISION_DIFFERENCE',product='lower_median ONLY; all mean products excluded',source_scores_unchanged=True,original_forecasts_unchanged=True,primary_MAE_RMSE_bias_unchanged=True,grid_denominator=50,lower_median_score_views=len(projection),score_views_with_any_precision_difference=sum(bool(s['changed_metrics'])for s in projection),unique_scored_median_prediction_rows=len(unique),row_threshold_disagreements=dict(rowdisagreements),source_hashes={str(p):sha(p)for p in[public/'SCORES.json',public/'EMPIRICAL_SCORES.json',cohort_public/'SCORES.json']},new_fits=0,new_forecasts=0,week8_outcomes_read=0,interpretation='Float subtraction can cross exact1/5/10point boundaries for .02-grid medians and labels. Exact integer coordinate tolerances repair precisiondiagnostics only; no forecast, accuracygain or MAEimprovement claim.',projection=projection)

if __name__=='__main__':
    result=audit(*(Path(x)for x in sys.argv[1:5]));out=Path(__file__).parent/'CHART_EXACT_GRID_PRECISION_AUDIT.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='projection'},indent=2))
