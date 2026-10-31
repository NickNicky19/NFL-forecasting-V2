"""Independently reconstruct category minima from frozen source aggregates."""
from collections import defaultdict,Counter
import csv,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/continuation-20261030b'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
    sources=[('reports/continuation-20261029/history-diagnostic-v1/HISTORY_COMPARISON_2026_W1_W7.csv','EMPIRICAL'),('reports/continuation-20261029/hgb-history-v1/SCORES.json','HGB'),('reports/continuation-20261030/distribution-wave-v2/SCORES.json',None),('reports/continuation-20261030/count-ablation-wave-v1/SCORES.json','HGB'),('reports/continuation-20261030/chart-wave-v1/SCORES.json',None),('reports/continuation-20261030/chart-wave-v1/EMPIRICAL_SCORES.json','EMPIRICAL'),('reports/continuation-20261030b/ordered-information-ablation-v1/SCORES.json','ORDERED_LEAF_CDF')]
    candidates=[];source_hashes={}
    for artifact,family in sources:
        path=ROOT/artifact;source_hashes[artifact]=sha(path);rows=list(csv.DictReader(path.open(newline='')))if path.suffix=='.csv'else json.loads(path.read_text())
        for r in rows:
            if r.get('population')!='primary'or str(r.get('season',2026))!='2026'or str(r.get('week'))!='ALL'or r.get('position','ALL')!='ALL'or r.get('fallback_view','ALL')!='ALL':continue
            n=int(r.get('n',r.get('scored_n',0)))
            if not n:continue
            fam=family or('ORDERED_LEAF_CDF'if'leaf'in r['procedure_family_id']else'GLM_LAW'if'glm'in r['procedure_family_id']else'EMPIRICAL')
            procedure=r.get('procedure_id','empirical-player-history-control-v1'if path.suffix=='.csv'else'hgb-direct-history-controls-v1:'+r.get('objective',''))
            candidates.append(dict(r,family=fam,procedure_id=procedure,product=r.get('product_id',r.get('product',r.get('objective'))),source_artifact=artifact,n=n))
    assert len(candidates)==436
    current=json.loads((OUT/'TOP5_BY_CATEGORY_PRODUCT.json').read_text());assert len(current)==114
    expected=[]
    for target in sorted({r['target']for r in candidates}):
        pool=[r for r in candidates if r['target']==target];assert len({r['n']for r in pool})==1
        for product,metric in [('display_point','brier'if target=='anytime_td'else'mae'),('intended_mean','mse'),('forecast_law','CRPS')]:
            if target=='anytime_td'and product=='intended_mean':continue
            subset=[r for r in pool if r.get(metric)not in(None,'')and(product!='intended_mean'or'mean'in r['product'])]
            reps=[]
            for fam in sorted({r['family']for r in subset}):
                options=[r for r in subset if r['family']==fam]
                best=min(options,key=lambda r:(float(r[metric]),r['procedure_id'],r['history_regime'],r['product']))
                reps.append(dict(best,ranking_product=product,ranking_metric=metric,ranking_loss=float(best[metric]),family_ties_within_1e12=sum(abs(float(r[metric])-float(best[metric]))<=1e-12 for r in options)))
            reps.sort(key=lambda r:(r['ranking_loss'],r['family']));last=None;rank=0
            for i,r in enumerate(reps):
                if last is None or abs(r['ranking_loss']-last)>1e-12:rank=i+1
                expected.append(dict(r,rank=rank));last=r['ranking_loss']
    key=lambda r:(r['target'],r['ranking_product'],r['family'])
    expected={key(r):r for r in expected};assert len(expected)==len(current)
    checks=0
    for r in current:
        e=expected.pop(key(r))
        for field in('procedure_id','product','history_regime','n','source_artifact','ranking_metric','ranking_loss','rank','family_ties_within_1e12'):
            assert r[field]==e[field],(field,r[field],e[field]);checks+=1
    assert not expected
    old=json.loads((ROOT/'reports/continuation-20261030/TOP5_BY_CATEGORY_PRODUCT.json').read_text());best=lambda rows:{target:min(r['ranking_loss']for r in rows if r['target']==target and r['ranking_product']=='display_point')for target in {r['target']for r in rows}}
    before,after=best(old),best(current);changes=[dict(target=t,previous_error=before[t],current_error=after[t],delta=after[t]-before[t])for t in sorted(before)]
    c02=[]
    for target in sorted(before):
        metric='brier'if target=='anytime_td'else'mae';rows=[r for r in candidates if r['target']==target and'ordered-information-ablation'in r['source_artifact']];minimum=min(float(r[metric])for r in rows)
        c02.append(dict(target=target,candidate_best_error=minimum,prior_best_error=before[target],delta=minimum-before[target]))
    outcomes=Counter('win'if r['delta']<-1e-12 else'loss'if r['delta']>1e-12 else'tie'for r in c02)
    assert outcomes==dict(win=3,loss=8,tie=1)
    return dict(status='PASS_INDEPENDENT_FROZEN_AGGREGATE_FAMILY_MINIMA',candidate_views=len(candidates),family_representatives=len(current),representative_identity_metric_rank_checks=checks,source_hashes=source_hashes,display_minimum_changes=changes,c02_best_against_prior_strongest=c02,c02_outcome_counts=dict(outcomes),table_sha256=sha(OUT/'TOP5_BY_CATEGORY_PRODUCT.json'),interpretation='Exposed minima by scientifically shared family/product/history, not a pregame selector. Native-unit categories and law/point/mean products remain separate.',new_fits=0,new_forecasts=0,week8_outcomes_read=0)
if __name__=='__main__':
    r=verify();OUT.joinpath('CATEGORY_PROJECTION_INDEPENDENT_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k not in('source_hashes','display_minimum_changes','c02_best_against_prior_strongest')}))
