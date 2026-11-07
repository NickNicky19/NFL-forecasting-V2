"""Season-relative replay of the registered v2 category score-memory policies.

Uses retained predictions/weekly aggregates. No fitting or model inference.
"""
from __future__ import annotations
import argparse,collections,csv,gzip,hashlib,json,math,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import canonical,sha,now,write,packet_rows
from nfl_v2.week8_shadow import schedules
from tools.chronological_category_selector import key,stable,loss,eligible
from tools.numerical_championship import normalize,csvwrite,proc_id,product_id
VERSION='v2-chronological-category-score-memory-selector-v2-season-relative-extension'
POLICIES=('FROZEN_PRIOR_SEASON_BEST','EARLIER_AVAILABLE_CURRENT_SCORE_MEMORY','POOLED_PRIOR_AND_AVAILABLE_CURRENT_MEMORY')
SOURCE={2022:'season-2022-v2',2023:'season-2023-complete-replay-v1',2024:'season-2024-v2',2025:'season-2025-v1'}
BASEPROC='v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf'

def choose(ks,weekly,weeks):
    values={k:math.fsum(int(weekly[stable(k)][str(w)]['n'])*loss(weekly[stable(k)][str(w)],k[0])for w in weeks)/sum(int(weekly[stable(k)][str(w)]['n'])for w in weeks)for k in ks}
    best=min(values.values());return min((k for k in ks if abs(values[k]-best)<=1e-12),key=stable)

def pick(ks,policy,old,current,weeks,base):
    if policy==POLICIES[0]:return choose(ks,old,range(1,19))
    if policy==POLICIES[1]:return choose(ks,current,weeks)if weeks else base
    vals={k:(math.fsum(int(old[stable(k)][str(u)]['n'])*loss(old[stable(k)][str(u)],k[0])for u in range(1,19))+math.fsum(int(current[stable(k)][str(u)]['n'])*loss(current[stable(k)][str(u)],k[0])for u in weeks))/(sum(int(old[stable(k)][str(u)]['n'])for u in range(1,19))+sum(int(current[stable(k)][str(u)]['n'])for u in weeks))for k in ks}
    best=min(vals.values());return min((k for k in ks if abs(vals[k]-best)<=1e-12),key=stable)

def load_weekly(root,year):
    names=[SOURCE[year]]+(['season-2025-continuity-repair-v1']if year==2025 else[]);out=collections.defaultdict(dict);bindings=[]
    for name in names:
        path=root/'reports/continuation-20261030c'/name/'SCORES.json';bindings.append(dict(path=path.relative_to(root).as_posix(),sha256=sha(path)))
        for original in json.loads(path.read_bytes()):
            r=dict(original,source_artifact=path.relative_to(root).as_posix())
            if not eligible(r)or not isinstance(r.get('week'),int)or not 1<=r['week']<=18:continue
            if year==2025 and name=='season-2025-v1'and'qb-rb-specialization'in r['procedure_id']:continue
            k=key(r);w=r['week']
            if w in out[k]:raise ValueError('duplicate exact canonical recipe/week')
            out[k][w]=r
    return out,bindings

def prepare(a):
    if a.output.exists():raise ValueError('fresh immutable output required')
    a.output.mkdir(parents=True)
    old,ob=load_weekly(a.root,a.year-1);current,cb=load_weekly(a.root,a.year)
    roster=sorted(k for k in current.keys()&old.keys()if set(current[k])==set(range(1,19))and set(old[k])==set(range(1,19)))
    if len({k[0]for k in roster})!=12:raise ValueError('balanced twelve-target roster required')
    games=schedules(a.schedule);origins={};available={};gamecounts={}
    for year in(a.year-1,a.year):
        for w in range(1,19):
            gg=[g for g in games.values()if g['season']==year and g['week']==w]
            origins[f'{year}-{w}']=min(g['kickoff']for g in gg);available[f'{year}-{w}']=max(g['kickoff']for g in gg)+7*86400;gamecounts[f'{year}-{w}']=len(gg)
    numeric=json.loads((a.numeric/'FROZEN_PROTOCOL.json').read_bytes());sources=[r for r in numeric['sources']if r['season']in(a.year-1,a.year)]
    protocol=dict(version=VERSION,registered_at_utc=now(),evaluation_season=a.year,prior_season=a.year-1,evaluation_weeks=list(range(1,19)),roster=[list(k)for k in roster],policies=list(POLICIES),weekly_prior={stable(k):{str(w):v for w,v in old[k].items()}for k in roster},weekly_current={stable(k):{str(w):v for w,v in current[k].items()}for k in roster},origins=origins,week_score_available=available,gamecounts=gamecounts,source_aggregates=ob+cb,raw_sources=sources,schedule_sha256=sha(a.schedule),code_sha256=sha(__file__),parent_code_sha256=sha(Path(__file__).with_name('chronological_category_selector.py')),lineage='Same v2 algorithm with season-relative prior/current names; not a new learner. 2026 aliases FROZEN_2025_BEST / EARLIER_AVAILABLE_2026_SCORE_MEMORY / POOLED_2025_AND_AVAILABLE_2026_MEMORY retain original identities/scores.',fit_history='All forecasts H-MULTI, expanding from2022 with common older feature memory; current score-memory is method-selection evidence, not strict-current football information.',availability='Whole score week eligible only if LAST scheduled game kickoff+7days is strictly before earliest current-week fitting origin. No next-week or partial-current-week scores.',startup='Base Leaf-CDF H-MULTI median/event_probability, as registered v2; no hidden historical fallback purity claim.',tie='Within1e-12 choose stable target|normalizedprocedure|normalizedproduct lexicographically.',exposure='All years exposed; chronological reconstruction using current/revised football source versions under assumed7-day availability. No original issuance or fresh holdout.',mask_rule='Every recipe/week must equal base query identities, supported-label identities AND values; compare exact sets before policy metrics.',budget=dict(wall_seconds=300,cpu_seconds=360,max_RSS_bytes=1073741824,max_rows=8000000,threads=2),new_fits=0,new_inference=0,new_forward_captures=0)
    write(a.output/'FROZEN_PROTOCOL.json',protocol);(a.output/'EXECUTOR.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(state='FROZEN',year=a.year,output_recipes=len(roster),targets=12,protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'))))

def run(a):
    p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes());start,cpu=time.monotonic(),time.process_time();year=p['evaluation_season'];roster={tuple(k)for k in p['roster']};masks=collections.defaultdict(lambda:[set(),set(),set()]);scanned=0
    if p['code_sha256']!=sha(__file__)or p['parent_code_sha256']!=sha(Path(__file__).with_name('chronological_category_selector.py')):raise ValueError('sealed code changed')
    for b in p['source_aggregates']:
        if sha(a.root/b['path'])!=b['sha256']:raise ValueError('source aggregate changed')
    if sha(a.schedule)!=p['schedule_sha256']:raise ValueError('schedule changed')
    for source in p['raw_sources']:
        sy=source['season']
        for binding in source['members']:
            file=a.private_root/binding['member']
            if sha(file)!=binding['sha256']:raise ValueError('retained raw source changed')
            it=packet_rows(file)if binding['kind']=='packet'else csv.DictReader(gzip.open(file,'rt'))
            for raw in it:
                scanned+=1
                if scanned%10000==0 and(scanned>8000000 or time.monotonic()-start>300 or time.process_time()-cpu>360 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824):raise RuntimeError('finite mask-admission budget exceeded')
                norm=normalize(raw,binding['source_id'],sy)
                if norm is None:continue
                full,w=norm;target,proc,hist,product=full;k=(target,proc,product)
                if hist!='H-MULTI'or k not in roster:continue
                if sy==2025 and binding['source_id']=='season'and'qb-rb-specialization'in proc:continue
                q=tuple(raw[x]for x in('game_id','player_id','target','population','position'));mask=masks[sy,k,w]
                if q in mask[0]:raise ValueError('duplicate source query')
                mask[0].add(q)
                if raw.get('actual')not in(None,''):mask[1].add(q);mask[2].add((q,float(raw['actual'])))
    bytarget=collections.defaultdict(list);admissions=[]
    for k in sorted(roster):bytarget[k[0]].append(k)
    for target,ks in bytarget.items():
        base=next(k for k in ks if ':ordered_leaf_cdf'in k[1]and k[2]==('event_probability'if target=='anytime_td'else'lower_median'))
        for sy in(year-1,year):
            for w in range(1,19):
                reference=masks[sy,base,w]
                for k in ks:
                    actual=masks[sy,k,w]
                    if actual!=reference:raise ValueError('query/support/label-value mismatch')
                    row=p['weekly_current'if sy==year else'weekly_prior'][stable(k)][str(w)]
                    if len(actual[1])!=int(row['n']):raise ValueError('aggregate support mismatch')
                    admissions.append(dict(season=sy,week=w,target=target,procedure_id=k[1],product_id=k[2],query_n=len(actual[0]),supported_n=len(actual[1]),query_sha256=hashlib.sha256(canonical(sorted(actual[0]))).hexdigest(),support_sha256=hashlib.sha256(canonical(sorted(actual[1]))).hexdigest(),label_values_sha256=hashlib.sha256(canonical(sorted(actual[2]))).hexdigest(),state='EXACT_QUERY_SUPPORT_AND_LABEL_VALUES_EQUAL'))
    write(a.output/'EXACT_MASK_ADMISSION.json',admissions);decisions=[];scores=[];weekly_losses={}
    for target,ks in sorted(bytarget.items()):
        base=next(k for k in ks if ':ordered_leaf_cdf'in k[1]and k[2]==('event_probability'if target=='anytime_td'else'lower_median'))
        for policy in POLICIES:
            picked=[]
            for w in range(1,19):
                origin=p['origins'][f'{year}-{w}'];weeks=[u for u in range(1,w)if p['week_score_available'][f'{year}-{u}']<origin];chosen=pick(ks,policy,p['weekly_prior'],p['weekly_current'],weeks,base);r=p['weekly_current'][stable(chosen)][str(w)];picked.append(r)
                decisions.append(dict(season=year,week=w,target=target,policy=policy,fit_origin_unix=origin,eligible_current_score_weeks=weeks,chosen_procedure_id=chosen[1],chosen_product_id=chosen[2],n=r['n'],loss=loss(r,target),startup=policy==POLICIES[1]and not weeks,source_score_artifact=r['source_artifact']))
            n=sum(int(r['n'])for r in picked);metric='brier'if target=='anytime_td'else'mae';error=math.fsum(int(r['n'])*loss(r,target)for r in picked)/n;precision=collections.defaultdict(lambda:[0,0]);forecast=0
            for r in picked:
                for name,v in(r.get('precision_counts')or{}).items():
                    num,den=(v if isinstance(v,list)else(v['numerator'],v['denominator']));precision[name][0]+=int(num);precision[name][1]+=int(den)
                forecast+=len(masks[year,(target,proc_id(r['procedure_id']),product_id(r['product_id'])),int(r['week'])][0])
            score=dict(record_id='RELSELECT-'+hashlib.sha256(canonical([year,target,policy])).hexdigest()[:24],record_kind='retrospective_chronological_category_selector_aggregate_replay',procedure_id=VERSION+':'+policy,history_regime='H-MULTI',product_id='event_probability_policy'if target=='anytime_td'else'point_choice_policy',target=target,population='primary',position='ALL',fallback_view='ALL',season=year,week='ALL',evaluation_seasons=[year],evaluation_weeks=list(range(1,19)),evaluation_panel_id=VERSION+':'+str(year),period='REG',n=n,forecast_rows=forecast,fallback_rows=sum(int(r.get('fallback_rows')or 0)for r in picked),unique_games=sum(p['gamecounts'][f'{year}-{w}']for w in range(1,19)),unique_weeks=18,precision_counts={name:dict(numerator=num,denominator=den,rate=num/den if den else None)for name,(num,den)in precision.items()},source_vintage=p['exposure'],feature_memory_policy=p['fit_history'],evidence='NEW_EXPERIMENT_SAVED_AGGREGATE_REPLAY',**{metric:error});scores.append(score);weekly_losses[target,policy]=picked
    write(a.output/'DECISIONS.json',decisions);csvwrite(a.output/'DECISIONS.csv',decisions);write(a.output/'SCORES.json',scores);csvwrite(a.output/'POLICY_COMPARISON.csv',scores)
    from nfl_v2.paired_uncertainty import paired_losses
    paired=[]
    for target in bytarget:
        baseline=weekly_losses[target,POLICIES[0]]
        for policy in POLICIES[1:]:
            picked=weekly_losses[target,policy]
            # Weekly sums are sufficient for the registered whole-week bootstrap.
            differences=[(w+1,int(r['n'])*(loss(r,target)-loss(baseline[w],target)),int(r['n']))for w,r in enumerate(picked)]
            import numpy as np
            rng=np.random.default_rng(1703);samples=[]
            for _ in range(500):
                chosen=rng.integers(0,18,18);samples.append(math.fsum(differences[j][1]for j in chosen)/sum(differences[j][2]for j in chosen))
            delta=math.fsum(d[1]for d in differences)/sum(d[2]for d in differences)
            paired.append(dict(season=year,target=target,policy=policy,comparator=POLICIES[0],n=sum(d[2]for d in differences),delta=delta,week_interval=[float(v)for v in np.quantile(samples,[.025,.975])],week_clusters=18,game_interval=None,game_interval_status='NOT_AVAILABLE_FROM_AGGREGATE_LOSS',selection_limit='Exposed descriptive interval; not selection/multiplicity-adjusted',weekly_sums_counts=differences))
    write(a.output/'PAIRED_COMPARISONS.json',paired);csvwrite(a.output/'PAIRED_COMPARISONS.csv',paired)
    receipt=dict(state='COMPLETE_BALANCED_18_WEEK_SELECTOR_EVALUATION',season=year,completed_at_utc=now(),score_sha256=sha(a.output/'SCORES.json'),protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),mask_sha256=sha(a.output/'EXACT_MASK_ADMISSION.json'),mask_checks=len(admissions),choices=len(decisions),score_views=len(scores),new_fits=0,new_inference=0,new_forward_forecasts=0,new_independent_NFL_observations=0,raw_rows_scanned=scanned,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024));write(a.output/'RUN_RECEIPT.json',receipt);print(json.dumps(receipt))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);parser.add_argument('--year',type=int,choices=[2023,2024,2025],required=True);parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--numeric',type=Path,default=Path('reports/championship-20261030f/numerical-v2'));parser.add_argument('--private-root',type=Path,default=Path('/tmp/unspecified-source'));parser.add_argument('--schedule',type=Path,required=True);args=parser.parse_args();prepare(args)if args.action=='prepare'else run(args)
