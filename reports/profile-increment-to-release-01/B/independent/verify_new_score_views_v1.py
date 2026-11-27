"""Independent point/line/probability/TopK arithmetic for every new score view."""
import gzip,hashlib,importlib.util,json,math
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;BASE=OUT.parent
def read(p):
    p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def key(r):return r['game_id'],r['player_id'],r['target']
def fallback(r):return r.get('fallback')not in(None,'none','NONE','learned','NOT_APPLICABLE')
def cdf(l,x):
    y=math.floor(x);return(1-l['mixture'])*math.fsum(w for s,w in zip(l['support'],l['weights'])if s<=y)+l['mixture']*(0. if y<0 else 1-l['prior']['q']**(y+1))
def probabilities(r,line):
    l=r['law'];u=cdf(l,math.ceil(line)-1);o=1-cdf(l,math.floor(line));p=cdf(l,line)-cdf(l,line-1)if float(line).is_integer()else 0.
    assert min(u,o,p)>=-1e-12 and abs(u+o+p-1)<1e-12
    return dict(over=o,under=u,push=p)
def pointside(p,l):return'over'if Decimal(str(p))>Decimal(str(l))else'under'if Decimal(str(p))<Decimal(str(l))else None
def num_subset(rr,window,offers,games):
    if isinstance(window,int):return[r for r in rr if r['week']==window]
    return[r for r in rr if window=='ALL'or window=='W1_4'and r['week']<=4 or window=='W5_PLUS'and r['week']>=5 or window=='W1_8'and r['week']<=8 or window=='PRIORITY_PROXY'and r['profile_priority']['member']or window=='BASIC_NONPRIORITY'and not r['profile_priority']['member']or window=='NO_OWN_HISTORY_SHARED_MODEL'and not r['own_prior_games']or window=='OWN_HISTORY_PRESENT'and r['own_prior_games']or window=='MATCHED_OFFERS_W5_W8'and key(r)in offers or window=='COVERED_GAMES_W5_W8'and r['game_id']in games]

spec=importlib.util.spec_from_file_location('offers',ROOT/'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
offers=[r for w,p in sorted(read('/tmp/b-context-offer-sources.json').items())for r in m.iter_offers(Path(p),int(w))if r['target']=='pass_cmp'];offerkeys={key(r)for r in offers};games={r['game_id']for r in offers}
forecasts=[r for p in sorted((BASE/'opportunity-wave-v1/predictions').glob('*.json.gz'))for r in read(p)['rows']];index={(r['method'],key(r)):r for r in forecasts}
by=defaultdict(list)
for r in forecasts:by[r['season'],r['method']].append(r)
grades={}
for arm in('R0','R1','R2','R3'):
    for policy in('P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','P90'):
        gg=[]
        for i,o in enumerate(offers):
            p=index[arm,key(o)];assert p['actual']==o['actual'];prob=probabilities(p,o['line'])
            side=pointside(p['mean'if policy=='P1_MEAN'else'lower_median'],o['line'])if policy.startswith('P1_')else'over'if prob['over']>prob['under']else'under'if prob['under']>prob['over']else None
            if policy=='P90'and(side is None or prob[side]<.9):side=None
            event='over'if Decimal(str(o['actual']))>Decimal(str(o['line']))else'under'if Decimal(str(o['actual']))<Decimal(str(o['line']))else'push'
            state='ABSTAIN'if side is None else'PUSH'if event=='push'else'WIN'if side==event else'LOSS'
            gg.append(dict(o,index=i,side=side,state=state,prob=prob,priority=p['profile_priority']['member'],band=p['pregame_role_band'],forecast=p))
        grades[arm,policy]=gg
def select(gg,window):
    if isinstance(window,int):return[r for r in gg if r['week']==window]
    return[r for r in gg if window=='ALL'or window=='PRIORITY_PROXY'and r['priority']or window=='BASIC_NONPRIORITY'and not r['priority']or isinstance(window,str)and window.startswith('ROLE:')and r['band']==window[5:]]
def proper(rr):
    br=[];ll=[]
    for r in rr:
        event='over'if r['actual']>r['line']else'under'if r['actual']<r['line']else'push';p=r['prob']
        br.append(.5*sum((p[s]-int(s==event))**2 for s in('over','under','push')));ll.append(-math.log(p[event])if p[event]else math.inf)
    return dict(n=len(rr),brier=sum(br)/len(br)if br else None,log_loss=sum(ll)/len(ll)if ll and all(math.isfinite(v)for v in ll)else None,infinite_log_losses=sum(not math.isfinite(v)for v in ll))
max_difference=0.;checks=0
def eq(a,b,tol=1e-10):
    global max_difference,checks
    checks+=1
    if a is None or b is None:assert a is b,(a,b);return
    d=abs(a-b);max_difference=max(max_difference,d);assert d<tol,(a,b,d)
score=read(BASE/'opportunity-scores-v1/SCORES.json');counts=defaultdict(int);memberships=0
for v in score:
    arm=v['procedure_id'].rsplit(':',1)[-1];typ=v['record_kind'];window=v['week'];counts[typ]+=1
    if typ=='forecast_evaluation_view':
        sub=num_subset(by[v['season'],arm],window,offerkeys,games)
        if v['fallback_view']=='LEARNED':sub=[r for r in sub if not fallback(r)]
        if v['fallback_view']=='FALLBACK':sub=[r for r in sub if fallback(r)]
        rs=[r for r in sub if r['actual']is not None and r.get(v['product_id'])is not None];error=np.asarray([r[v['product_id']]-r['actual']for r in rs])
        eq(len(rs),v['n']);eq(float(np.abs(error).mean())if len(rs)else None,v['mae']);eq(float(np.square(error).mean())if len(rs)else None,v['mse']);eq(float(error.mean())if len(rs)else None,v['bias'])
        for metric,op,cut in(('exact_rate','eq',0),('abs_lt_1','lt',1),('abs_le_1','le',1),('abs_lt_5','lt',5),('abs_le_5','le',5),('abs_lt_10','lt',10),('abs_le_10','le',10)):
            hit=int(sum(abs(e)==cut if op=='eq'else abs(e)<cut if op=='lt'else abs(e)<=cut for e in error));pc=v['precision_counts'][metric];eq(hit,pc['numerator']);eq(len(rs),pc['denominator'])
        continue
    policy=v['product_id']if typ=='prop_selection_evaluation'else'P2_STATISTICAL_LAW'
    if policy=='ROLLING_TOP_K_DIAGNOSTIC':
        pool=select(grades[arm,'P2_STATISTICAL_LAW'],window);chosen=[];remaining=v['K']
        for kickoff in sorted({r['kickoff']for r in pool}):
            batch=[r for r in pool if r['kickoff']==kickoff and r['side']is not None and(v['rank_scope']=='Combined'or r['side']==v['rank_scope'])]
            batch.sort(key=lambda r:(-r['prob'][r['side']],r['game_id'],r['player_id'],str(r['line'])));chosen+=batch[:remaining];remaining-=min(remaining,len(batch))
        sub=chosen
    else:
        pool=select(grades[arm,policy],window);sub=[r for r in pool if r['side']is not None]
    if typ=='prop_threshold_probability_evaluation':
        expected=proper(pool)
        for k in('n','brier','log_loss','infinite_log_losses'):eq(expected[k],v[k])
        continue
    rr=[r for r in sub if v['side']=='Combined'or r['side']==v['side']];wins=sum(r['state']=='WIN'for r in rr);loss=sum(r['state']=='LOSS'for r in rr);push=sum(r['state']=='PUSH'for r in rr);s=v['selection_metrics']
    eq(wins,s['WIN']);eq(loss,s['LOSS']);eq(push,s['PUSH']);eq(len(rr),v['forecast_rows']);eq(wins+loss,v['n']);eq(wins/(wins+loss)if wins+loss else None,s['hit_rate']);eq(len(pool),s['selection_pool_count'])
    assert digest(sorted(r['index']for r in rr))==v['query_membership_sha256'];memberships+=1
    eq(len({r['game_id']for r in rr}),v['unique_games'])
    expected=proper(rr)
    for k in('n','brier','log_loss','infinite_log_losses'):eq(expected[k],s['probability_scores'][k])
    eq(len(pool)-len(sub),s['abstentions_outside_selected_partition'])
receipt=dict(id='B-OPPORTUNITY-ALL-NEW-SCORE-VIEWS-INDEPENDENT-v1',status='PASS_IN_CHECKED_SCOPE',canonical_score_sha256=sha(BASE/'opportunity-scores-v1/SCORES.json'),record_counts=dict(counts),checked_values=checks,selected_membership_hashes=memberships,max_numeric_difference=max_difference,new_fits=0,new_forecasts=0,restricted_rows_exported=False,independence='Separate Decimal line/point/actual grading; explicit geometric-mixture CDF probabilities; independent numeric/precision/proper-score and chronological TopK membership arithmetic. Author scorer, summary, law, selector and metrics functions not called; qualified offer parser only reused.',limits=['Fouractual offeredweeks5-8; timingunverified/source-revised diagnostic, not pregame originalpicks or venue settlement.','TopK is frozen percategory rolling diagnostic, not original website crosscategory selector replay.','Arithmetic verification does not establish useful improvement, causal effect or C raw parity/admission.'])
dest=OUT/'NEW_SCORE_VIEWS_INDEPENDENT_REVIEW_V1.json';assert not dest.exists();dest.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n');print(json.dumps(receipt,indent=2))
