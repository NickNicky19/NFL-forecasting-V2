"""Earlier-only category choice from retained weekly scores; never fits a model."""
from __future__ import annotations
import argparse,collections,csv,gzip,hashlib,json,math,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import packet_rows,canonical,sha,now,write
from nfl_v2.week8_shadow import schedules
from tools.numerical_championship import normalize,csvwrite,proc_id,product_id
from tools.build_current_valid_view_v2 import recipe
VERSION='v2-chronological-category-score-memory-selector-v1'
POLICIES=('FROZEN_2025_BEST','EARLIER_AVAILABLE_2026_SCORE_MEMORY','POOLED_2025_AND_AVAILABLE_2026_MEMORY')

def key(r):return(r.get('target',r.get('category')),proc_id(r['procedure_id']),product_id(r['product_id']))
def stable(k):return'|'.join(k)
def loss(r,target):return float(r['brier'if target=='anytime_td'else'mae'])
def eligible(r):
 return r.get('population')=='primary'and r.get('position')in(None,'','ALL')and r.get('fallback_view')in(None,'','ALL')and r.get('history_regime')=='H-MULTI'and not r.get('cohort_id')and'strict'not in r['procedure_id'].lower()and bool(recipe(r))
def prepare(a):
 if a.output.exists():raise ValueError('fresh output required')
 a.output.mkdir(parents=True);cur=collections.defaultdict(dict);old=collections.defaultdict(dict);bindings=[]
 manifest=a.root/'reports/continuation-20261030d/current-ranking-v2/current-valid-results/CURRENT_MANIFEST.json';m=json.loads(manifest.read_bytes())
 for part in m['csv_parts']:
  p=a.root/part['path']
  if sha(p)!=part['sha256']:raise ValueError('canonical source changed')
  bindings.append(dict(path=part['path'],sha256=part['sha256']))
  with p.open()as f:
   for r in csv.DictReader(f):
    if not eligible(r)or r['season']!='2026'or r['week']not in{str(w)for w in range(1,8)}:continue
    if r['evidence']!='NEW_EXPERIMENT'and r['source_artifact']!='reports/continuation-20261030/chart-grid-precision-correction-v1/SCORES.json':continue
    k=key(r);w=int(r['week'])
    if w in cur[k]:raise ValueError('duplicate current canonical recipe/week')
    cur[k][w]=dict(r)
 for name in('season-2025-v1','season-2025-continuity-repair-v1'):
  p=a.root/'reports/continuation-20261030c'/name/'SCORES.json';bindings.append(dict(path=p.relative_to(a.root).as_posix(),sha256=sha(p)))
  for r in json.loads(p.read_bytes()):
   if not eligible(r)or not isinstance(r.get('week'),int)or not 1<=r['week']<=18:continue
   if name=='season-2025-v1'and'qb-rb-specialization'in r['procedure_id']:continue
   k=key(r);w=r['week']
   if w in old[k]:raise ValueError('duplicate prior canonical recipe/week')
   old[k][w]=r
 roster=sorted(k for k in cur.keys()&old.keys()if set(cur[k])==set(range(1,8))and set(old[k])==set(range(1,19)))
 gaps=[dict(recipe=list(k),state='INCOMPLETE_PRIOR_OR_CURRENT_WEEKLY_CELLS',current_weeks=sorted(cur[k]),prior2025_weeks=sorted(old.get(k,{})))for k in sorted(cur)if k not in roster]
 origins={};available={};gamecounts={};games=schedules(a.schedule)
 for y,maxw in((2025,18),(2026,7)):
  for w in range(1,maxw+1):
   gs=[g for g in games.values()if g['season']==y and g['week']==w];origins[f'{y}-{w}']=min(g['kickoff']for g in gs);available[f'{y}-{w}']=max(g['kickoff']for g in gs)+7*86400;gamecounts[f'{y}-{w}']=len(gs)
 raw=json.loads((a.numeric/'FROZEN_PROTOCOL.json').read_bytes());sources=[r for r in raw['sources']if r['season']in(2025,2026)]
 priors={};current={}
 for k in roster:priors[stable(k)]={str(w):old[k][w]for w in old[k]};current[stable(k)]={str(w):cur[k][w]for w in cur[k]}
 p=dict(version=VERSION,registered_at=now(),state='FROZEN_BEFORE_MASK_REPLAY_OR_SELECTOR_METRICS',code_sha256=sha(__file__),roster=[list(k)for k in roster],excluded=gaps,policies=list(POLICIES),criterion='MAE numeric; Brier rushing-or-receiving anytimeTD; all candidates H-MULTI with exact complete2025+2026W1-7 weekly output continuity',tie='Losses within1e-12 choose stable target|normalizedprocedure|normalizedproduct lexicographically; no posthoc support/gain gate',availability='Whole evaluation week usable only when LAST game kickoff+7days strictly earlier than next weekly earliest-kickoff fit origin. No later sameweek outcomes. Reconstruction source-vintage limitation retained.',startup='EARLIER_AVAILABLE_2026_SCORE_MEMORY uses fixed base Leaf-CDF H-MULTI lower_median/event_probability until an entire current scoring week qualifies. This historically fitted common fallback and historical candidate roster mean this is NOT pure-current-football-information.',weighting='sum(weekly n * native loss)/sum(n); current-score-memory concerns choosing among MULTI models, not training only2026',exposure='All seasons previously exposed research; earlier-only numerical policy reconstruction, not untouched holdout or original issued routing',origins=origins,week_score_available=available,gamecounts=gamecounts,schedule_sha256=sha(a.schedule),source_aggregates=bindings,raw_sources=sources,weekly2025=priors,weekly2026=current,mask_contract='Before policy metrics, exact primary query and supported-actual sets for EVERY candidate/week must match the base Leaf-CDF reference. Null actual remains null; query identity includes game/player/target/population/position. Source code/query support not inferred from equal counts.',budget=dict(max_wall_seconds=180,max_CPU_seconds=240,max_RSS_bytes=1073741824,max_rows=4000000,max_threads=2),new_NFL_fits=0,new_forecasts=0,Week8_outcomes_read=0)
 write(a.output/'FROZEN_PROTOCOL.json',p);print(json.dumps(dict(state=p['state'],candidate_output_recipes=len(roster),targets=len({k[0]for k in roster}),excluded=len(gaps),sha256=sha(a.output/'FROZEN_PROTOCOL.json'))))
def run(a):
 p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes());start,cpu=time.monotonic(),time.process_time()
 if p['code_sha256']!=sha(__file__):raise ValueError('sealed code changed')
 roster={tuple(k)for k in p['roster']};masks=collections.defaultdict(lambda:[set(),set()]);rows=0
 for source in p['raw_sources']:
  year=source['season']
  for binding in source['members']:
   file=a.private_root/binding['member']
   if sha(file)!=binding['sha256']:raise ValueError('raw source changed')
   it=packet_rows(file)if binding['kind']=='packet'else csv.DictReader(gzip.open(file,'rt'))
   for raw in it:
    rows+=1
    if rows%10000==0:
     if rows>4000000 or time.monotonic()-start>180 or time.process_time()-cpu>240 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('bounded selector mask admission limit')
    norm=normalize(raw,binding['source_id'],year)
    if norm is None:continue
    full,w=norm;t,proc,h,product=full;k=(t,proc,product)
    if h!='H-MULTI'or k not in roster:continue
    if year==2025 and binding['source_id']=='season'and'qb-rb-specialization'in proc:continue
    q=tuple(raw[x]for x in('game_id','player_id','target','population','position'));mask=masks[year,k,w]
    if q in mask[0]:raise ValueError('duplicate exact source selection/query')
    mask[0].add(q)
    if raw.get('actual')not in(None,''):mask[1].add(q)
 baseproc='v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf';bytarget=collections.defaultdict(list)
 for k in sorted(roster):bytarget[k[0]].append(k)
 maskreceipts=[]
 for target,ks in bytarget.items():
  base=next(k for k in ks if k[1]==baseproc and k[2]==('event_probability'if target=='anytime_td'else'lower_median'))
  for year,maxw in((2025,18),(2026,7)):
   for w in range(1,maxw+1):
    reference=masks[year,base,w]
    for k in ks:
     actual=masks[year,k,w]
     if actual!=reference:raise ValueError('candidate query or actual-support mask differs')
     source=p['weekly2025'if year==2025 else'weekly2026'][stable(k)][str(w)]
     if len(actual[1])!=int(source['n']):raise ValueError('aggregate denominator differs from exact support')
     maskreceipts.append(dict(season=year,week=w,target=target,procedure_id=k[1],product_id=k[2],query_n=len(actual[0]),supported_n=len(actual[1]),query_sha256=hashlib.sha256(canonical(sorted(actual[0]))).hexdigest(),support_sha256=hashlib.sha256(canonical(sorted(actual[1]))).hexdigest(),reference=list(base),state='EXACT_QUERY_AND_SUPPORT_MEMBERSHIP_EQUAL'))
 write(a.output/'EXACT_MASK_ADMISSION.json',maskreceipts)
 decisions=[];scores=[]
 def choose(ks,which,weeks):
  values={k:math.fsum(int(p[which][stable(k)][str(w)]['n'])*loss(p[which][stable(k)][str(w)],k[0])for w in weeks)/sum(int(p[which][stable(k)][str(w)]['n'])for w in weeks)for k in ks};best=min(values.values());return min((k for k in ks if abs(values[k]-best)<=1e-12),key=stable)
 for target,ks in sorted(bytarget.items()):
  prior=choose(ks,'weekly2025',range(1,19));base=next(k for k in ks if k[1]==baseproc and k[2]==('event_probability'if target=='anytime_td'else'lower_median'))
  for policy in POLICIES:
   picked=[]
   for w in range(1,8):
    origin=p['origins'][f'2026-{w}'];eligibleweeks=[u for u in range(1,w)if p['week_score_available'][f'2026-{u}']<origin]
    if policy=='FROZEN_2025_BEST':chosen=prior
    elif policy=='EARLIER_AVAILABLE_2026_SCORE_MEMORY':chosen=choose(ks,'weekly2026',eligibleweeks)if eligibleweeks else base
    else:
     vals={k:(math.fsum(int(p['weekly2025'][stable(k)][str(u)]['n'])*loss(p['weekly2025'][stable(k)][str(u)],target)for u in range(1,19))+math.fsum(int(p['weekly2026'][stable(k)][str(u)]['n'])*loss(p['weekly2026'][stable(k)][str(u)],target)for u in eligibleweeks))/(sum(int(p['weekly2025'][stable(k)][str(u)]['n'])for u in range(1,19))+sum(int(p['weekly2026'][stable(k)][str(u)]['n'])for u in eligibleweeks))for k in ks};best=min(vals.values());chosen=min((k for k in ks if abs(vals[k]-best)<=1e-12),key=stable)
    r=p['weekly2026'][stable(chosen)][str(w)];picked.append(r);decisions.append(dict(target=target,policy_id=policy,evaluation_week=w,fit_origin_unix=origin,current_score_weeks_available=eligibleweeks,chosen_procedure_id=chosen[1],chosen_product_id=chosen[2],history_regime='H-MULTI',n=int(r['n']),native_loss=loss(r,target),startup_fallback=policy=='EARLIER_AVAILABLE_2026_SCORE_MEMORY'and not eligibleweeks,source_score_artifact=r['source_artifact'],not_originally_issued=True))
   n=sum(int(r['n'])for r in picked);metric='brier'if target=='anytime_td'else'mae';err=math.fsum(int(r['n'])*loss(r,target)for r in picked)/n;prec=collections.defaultdict(lambda:[0,0])
   for r in picked:
    d=r.get('precision_counts')or{}
    if isinstance(d,str):d=json.loads(d)
    for name,v in d.items():
     if isinstance(v,list):num,den=v
     else:num,den=v['numerator'],v['denominator']
     prec[name][0]+=int(num);prec[name][1]+=int(den)
   forecast=sum(len(masks[2026,tuple((target,proc_id(r['procedure_id']),product_id(r['product_id']))),int(r['week'])][0])for r in picked)
   fb=sum(int(r.get('fallback_rows')or 0)for r in picked);score=dict(record_id='SELECTOR-'+hashlib.sha256(canonical([target,policy])).hexdigest()[:24],record_kind='retrospective_chronological_category_selector_aggregate_replay',procedure_id=VERSION+':'+policy,history_regime='H-MULTI',product_id='event_probability_policy'if target=='anytime_td'else'point_choice_policy',target=target,population='primary',position='ALL',fallback_view='ALL',season=2026,week='ALL',evaluation_seasons=[2026],evaluation_weeks=list(range(1,8)),evaluation_panel_id=VERSION,period='REG',n=n,forecast_rows=forecast,fallback_rows=fb,unique_games=107,unique_weeks=7,precision_counts={name:dict(numerator=x[0],denominator=x[1],rate=x[0]/x[1]if x[1]else None)for name,x in prec.items()},week_interval=None,week_interval_status='INSUFFICIENT_WEEK_CLUSTERS',game_interval_status='NO_PER_GAME_AGGREGATE_LOSS_AVAILABLE',source_vintage='exposed current-vintage seven-day assumed availability, per-game kickoff query features; not original issue or T90',evidence='NEW_EXPERIMENT_SAVED_AGGREGATE_REPLAY',**{metric:err})
   scores.append(score)
 write(a.output/'DECISIONS.json',decisions);csvwrite(a.output/'DECISIONS.csv',decisions);write(a.output/'SCORES.json',scores);csvwrite(a.output/'POLICY_COMPARISON.csv',scores);receipt=dict(state='COMPLETE_BOUNDED_CHRONOLOGICAL_CATEGORY_SELECTOR',at=now(),protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),score_sha256=sha(a.output/'SCORES.json'),mask_sha256=sha(a.output/'EXACT_MASK_ADMISSION.json'),raw_rows_scanned=rows,mask_checks=len(maskreceipts),decisions=len(decisions),evaluation_views=len(scores),new_NFL_fits=0,new_forecasts=0,Week8_outcomes_read=0,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024));write(a.output/'RUN_RECEIPT.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);p.add_argument('--numeric',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--schedule',type=Path,required=True);a=p.parse_args();prepare(a)if a.action=='prepare'else run(a)
