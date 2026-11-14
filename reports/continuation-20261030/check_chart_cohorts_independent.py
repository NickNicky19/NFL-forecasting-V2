"""Independent raw-history cohort/ranking and all saved scalar metrics replay."""
from collections import defaultdict,Counter
from decimal import Decimal,localcontext
from pathlib import Path
import csv,gzip,hashlib,json,math,sys
from check_new_wave_prefixes import load,sha
from check_label_extension import metrics

def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def identity(q):return(q['game_id'],q['player_id']or'sleeper:'+str(q['sleeper_id']),q['target'],q['population'])
def audit(public,private,chart_public,chart_private,source):
    p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());run=json.loads((public/'RUN_RECEIPT.json').read_text());base=json.loads((chart_public/'FROZEN_PROTOCOL.json').read_text())
    rows,history,games=load(source,base);queries=json.loads((chart_private/'frozen-queries.json').read_text());past=[q for q in queries['historical']if q['season']==2026]
    future=[dict(q,population='frozen_exante_chart_union',week=8)for q in queries['week8']]
    expected={};profile_checks=0;rank_checks=0
    from datetime import datetime
    origins={w:min(g['kickoff']for g in games.values()if g['year']==2026 and g['week']==w)-5400 for w in range(1,8)};origins[8]=datetime.fromisoformat(p['future_asof_utc'].replace('Z','+00:00')).timestamp()
    allqueries=past+future
    for week in range(1,9):
        qs=[q for q in allqueries if q['week']==week];profiles={}
        for q in qs:
            pid=identity(q)[1];slots=[]if q.get('blocked_reason')else[r for r in history.get(q['player_id'],[])if r['available']<origins[week]][-3:]
            values=[float(r['values']['nick-chart-ppr-v1']/50)for r in slots if r['values']['nick-chart-ppr-v1']is not None]
            profiles[pid]=dict(mean=math.fsum(values)/len(values)if values else None,supported_slots=len(values),history_slots=len(slots),latest_available=max((r['available']for r in slots),default=None))
        ranked=sorted((pid for pid,s in profiles.items()if s['mean']is not None),key=lambda pid:(-profiles[pid]['mean'],pid));ranks={pid:i+1 for i,pid in enumerate(ranked)}
        for q in qs:
            pid=identity(q)[1];profile=profiles[pid];rank=ranks.get(pid);mean=profile['mean'];cohorts=['all']
            if rank is None:cohorts.append('unranked')
            else:
                cohorts.extend('top'+str(n)for n in(10,15,20)if rank<=n)
                cohorts.append('rank1_10'if rank<=10 else'rank11_15'if rank<=15 else'rank16_20'if rank<=20 else'rank21plus')
            band='unknown'if mean is None else'zero'if mean==0 else'low'if mean<=5 else'middle'if mean<=15 else'high'
            cohorts.append('score_history_'+band);expected[identity(q)]=dict(profile,rank=rank,cohorts=cohorts,ranking_cutoff=origins[week])
    for name in('memberships.json.gz','future-memberships.json.gz'):
        path=private/name;assert sha(path)==run['membership_sha256'if name=='memberships.json.gz'else'future_membership_sha256']
        member=json.loads(gzip.decompress(path.read_bytes()))
        for m in member:
            exp=expected[tuple(m['key'])]
            for k in('mean','supported_slots','history_slots','latest_available','ranking_cutoff'):
                assert(m[k]is None and exp[k]is None)or(m[k]is not None and exp[k]is not None and math.isclose(m[k],exp[k],rel_tol=2e-13,abs_tol=2e-12)),(k,m[k],exp[k]);profile_checks+=1
            assert m['rank']==exp['rank']and m['cohorts']==exp['cohorts'];rank_checks+=2
    records=[]
    with gzip.open(chart_private/'all-chart-predictions.csv.gz','rt')as f:
        for r in csv.DictReader(f):
            if int(r['season'])!=2026 or int(r['week'])>7:continue
            for k in('actual','prediction'):r[k]=float(r[k])if r[k]!=''else None
            r['week']=int(r['week']);records.append(r)
    assert len(records)==run['retained_prediction_views']==52668
    eligible=defaultdict(lambda:defaultdict(set))
    for r in records:
        k=r['procedure_id'],r['product_id'],r['target'],r['population'];eligible[k].setdefault(r['history_regime'],set())
        if r['fallback']=='none'and r['prediction']is not None and r['actual']is not None:eligible[k][r['history_regime']].add(identity(r))
    overlap={k:set.intersection(*(arms.get(a,set())for a in('H-CURRENT','H-RECENT','H-MULTI')))for k,arms in eligible.items()}
    shared=set.intersection(*(values for arms in eligible.values()for values in arms.values()))
    groups=defaultdict(list)
    for r in records:
        key=r['procedure_id'],r['product_id'],r['target'],r['population'];views=['full_system']
        if r['fallback']=='none':views.append('own_learned_only')
        if identity(r)in overlap[key]:views.append('three_history_learned_overlap')
        if identity(r)in shared:views.append('all_competitor_learned_overlap')
        for cohort in expected[identity(r)]['cohorts']:
            for view in views:groups[(r['procedure_id'],r['product_id'],r['target'],r['population'],r['history_regime'],cohort,view)].append(r)
    scores=json.loads((public/'SCORES.json').read_text());checks=0;maxdelta=0
    assert len(groups)==len(scores)==1176
    for s in scores:
        rs=groups[tuple(s[k]for k in('procedure_id','product_id','target','population','history_regime','cohort_id','fallback_view'))];scored=[r for r in rs if r['actual']is not None and r['prediction']is not None];pairs=[(r['prediction'],r['actual'])for r in scored]
        assert len(rs)==s['forecast_rows']and len(pairs)==s['n'];checks+=2
        assert hashlib.sha256(canonical(sorted(identity(r)for r in rs))).hexdigest()==s['cohort_membership_sha256'];checks+=1
        assert hashlib.sha256(canonical(sorted(identity(r)for r in scored))).hexdigest()==s['scored_membership_sha256'];checks+=1
        assert len({r['game_id']for r in scored})==s['unique_games'];checks+=1
        if not pairs:continue
        exp=metrics(pairs,'nick-chart-ppr-v1')
        with localcontext()as exact:
            exact.prec=1200;errors=[abs(float(Decimal.from_float(a)-Decimal.from_float(b)))for a,b in pairs]
        for tol in(1,5,10):exp['abs_lt_'+str(tol)]=Decimal(sum(e<tol for e in errors))/len(errors);exp['abs_le_'+str(tol)]=Decimal(sum(e<=tol for e in errors))/len(errors)
        for name,v in exp.items():
            if name=='n':continue
            delta=abs(float(v)-s[name]);maxdelta=max(maxdelta,delta);assert math.isclose(float(v),s[name],rel_tol=4e-12,abs_tol=2e-8);checks+=1
    return dict(status='PASS_RAW_PREFIX_RANKS_COHORT_INTERSECTIONS_AND_ALL_SCALAR_SCORES',historical_queries=len(past),future_queries=len(future),profile_value_checks=profile_checks,rank_and_membership_checks=rank_checks,scored_views=len(scores),metric_and_cohort_hash_checks=checks,max_metric_difference=maxdelta,retained_historical_output_views=len(records),all_competitor_learned_overlap_rows=len(shared),future_blocked_unranked=sum(q.get('blocked_reason')is not None for q in future),future_first_game_excluded=all(q['game_id']!='2026_08_CAR_GB'for q in future),new_fits=0,new_forecasts=0,week8_actuals_read=0,run_receipt_sha256=sha(public/'RUN_RECEIPT.json'),limits='New retrospective chart-score-history diagnostic selector, not workload; commonoldermemory membershipdoesnotturnstrictmodelintoapurecurrentselectedsystem; futurefrozenatrealregistrationtimeandunscored')

if __name__=='__main__':
    with localcontext()as ctx:
        ctx.prec=50;result=audit(*(Path(x)for x in sys.argv[1:6]))
    (Path(__file__).parent/'CHART_COHORT_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
