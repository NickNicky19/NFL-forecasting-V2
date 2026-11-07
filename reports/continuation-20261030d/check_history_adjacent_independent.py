"""All adjacent-contrast algebra/weekly uncertainty plus bounded raw-row replay."""
import argparse,collections,csv,gzip,hashlib,json,math,resource,sys,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
FIELDS=('season','procedure_id','target','population','product_id','metric')
VIEWS=('FULL_SYSTEM','COMMON_CORE_LEARNED','ANY_ARM_FALLBACK','ALL_ARM_FALLBACK','MIXED_FALLBACK','WEEK1_STARTUP')
CORE=('H-CURRENT','H-RECENT','H-MULTI')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def close(a,b):
 if a is None or b is None:assert a is b,(a,b)
 else:assert math.isclose(a,b,rel_tol=2e-9,abs_tol=2e-9),(a,b)
def qlinear(values,p):
 s=sorted(values);v=(len(s)-1)*p;l=math.floor(v);h=math.ceil(v);return s[l]+(s[h]-s[l])*(v-l)
def main():
 p=argparse.ArgumentParser();p.add_argument('--companion-root',type=Path,required=True);a=p.parse_args();start,cpu=time.monotonic(),time.process_time()
 pub=HERE/'history-adjacent-v1';protocol=json.loads((pub/'FROZEN_PROTOCOL.json').read_bytes());receipt=json.loads((pub/'RUN_RECEIPT.json').read_bytes());rows=json.loads((pub/'SCORES.json').read_bytes());checks=collections.Counter()
 assert receipt['state']=='COMPLETE'and receipt['pending_cases']==0 and len(rows)==receipt['comparison_views']==17100
 for field,path in(('code_sha256','tools/history_adjacent_replay.py'),('paired_helper_sha256','nfl_v2/paired_uncertainty.py'),('packet_reader_sha256','nfl_v2/shared_subgroups.py')):assert sha(ROOT/path)==protocol[field]
 groups={};contrasts={};finite_ci=0
 for r in rows:
  k=tuple(r[x]for x in FIELDS);g=groups.setdefault(k+(r['contrast'],),{});assert r['fallback_view']not in g;g[r['fallback_view']]=r
  b=contrasts.setdefault(k+(r['fallback_view'],),{});assert r['contrast']not in b;b[r['contrast']]=r
  assert r['record_kind']=='DERIVED_PAIRED_HISTORY_COMPARISON'and r['history_regime']=='ADJACENT_CORE_COMPARISON'
  assert r['requested_history_status'].startswith('SOURCE_LIMITED')if r['season']==2022 else r['requested_history_status']=='REGISTERED_RELATIVE_HISTORY'
  n=r['n'];assert r['negative_favors_new'];weekly=sorted((int(w),x)for w,x in r.get('weekly_paired_sums_counts',{}).items());assert sum(x['n']for _,x in weekly)==n
  close(math.fsum(x['loss_difference_sum']for _,x in weekly),r['loss_difference_sum']);assert [w for w,_ in weekly]==r['evaluation_weeks']
  for arm in CORE:assert sum(r['fallback_source_counts'][arm].values())==n
  if n:
   close(r['candidate_error']-r['comparator_error'],r['delta']);close(r['loss_difference_sum']/n,r['delta']);close(r['relative_error_change'],r['delta']/r['comparator_error']if r['comparator_error']else None)
   if not r['comparator_error']:assert r['relative_error_missing_reason']=='zero_comparator_error_denominator'
  else:assert r.get('candidate_error')is None and r.get('comparator_error')is None and r['delta']is None
  close(r['contribution_to_fullsystem_delta'],r['loss_difference_sum']/r['fullsystem_n']if r['fullsystem_n']else None)
  if len(weekly)>=8:
   assert r['week_interval_status']=='NOMINAL_WHOLE_WEEK_PAIRED_BOOTSTRAP'
   sums=np.asarray([x['loss_difference_sum']for _,x in weekly]);ns=np.asarray([x['n']for _,x in weekly]);draw=np.random.Generator(np.random.PCG64(1703)).integers(0,len(weekly),size=(500,len(weekly)));samples=sums[draw].sum(axis=1)/ns[draw].sum(axis=1)
   close(r['week_interval'][0],qlinear(samples,.025));close(r['week_interval'][1],qlinear(samples,.975));finite_ci+=1
  else:assert r['week_interval']is None
  checks['all_source_contrast_algebra_rows']+=1
 for key,g in groups.items():
  assert set(g)==set(VIEWS)
  for whole,parts in(('FULL_SYSTEM',('COMMON_CORE_LEARNED','ANY_ARM_FALLBACK')),('ANY_ARM_FALLBACK',('ALL_ARM_FALLBACK','MIXED_FALLBACK'))):
   assert g[whole]['n']==sum(g[x]['n']for x in parts);close(g[whole]['loss_difference_sum'],math.fsum(g[x]['loss_difference_sum']for x in parts))
  assert g['WEEK1_STARTUP']['n']<=g['FULL_SYSTEM']['n']
  learned=g['COMMON_CORE_LEARNED'];allfallback=g['ALL_ARM_FALLBACK'];mixed=g['MIXED_FALLBACK']
  for arm in CORE:
   assert learned['fallback_source_counts'][arm].get('none',0)==learned['n'];assert not allfallback['fallback_source_counts'][arm].get('none',0)
  assert mixed['n']<=sum(mixed['fallback_source_counts'][h].get('none',0)for h in CORE)<=2*mixed['n']
  checks['disjoint_fallback_decomposition_groups']+=1
 for pair in contrasts.values():
  assert len(pair)==2;u,v=pair.values()
  for field in('n','membership_sha256','evaluation_weeks','fallback_source_counts','fullsystem_n'):assert u[field]==v[field]
  checks['identical_three_arm_memberships_across_adjacent_pairs']+=1
 bound=next(x for x in protocol['sources']if x['source_id']=='laws2026')['logical_members'][0];file=a.companion_root/bound['member'];assert sha(file)==bound['sha256'];raw={};read=0
 with gzip.open(file,'rt')as f:
  for r in csv.DictReader(f):
   read+=1
   if not 1<=int(r['week'])<=7:continue
   if r['target']!='rec'or r['population']!='primary'or r.get('product_id',r.get('product'))!='lower_median'or 'ordered_leaf_cdf'not in r['procedure_id']or 'strict'in r['procedure_id']:continue
   arm=r['history_regime'];assert arm in CORE;ident=tuple(r[x]for x in('game_id','player_id','target','population','position'));g=raw.setdefault(ident,{})
   assert arm not in g;g[arm]=r
 samples=[]
 for contrast,new,old in(('H-RECENT_MINUS_H-CURRENT','H-RECENT','H-CURRENT'),('H-MULTI_MINUS_H-RECENT','H-MULTI','H-RECENT')):
  for view in VIEWS:
   cases=[]
   for ident,arms in raw.items():
    assert set(arms)==set(CORE);assert len({x['actual']for x in arms.values()})==1
    fb=[arms[h]['fallback']for h in CORE];learned=all(x=='none'for x in fb);allfb=all(x!='none'for x in fb);week=int(arms[new]['week'])
    include=dict(FULL_SYSTEM=True,COMMON_CORE_LEARNED=learned,ANY_ARM_FALLBACK=not learned,ALL_ARM_FALLBACK=allfb,MIXED_FALLBACK=not learned and not allfb,WEEK1_STARTUP=week==1)[view]
    if not include or arms[new]['actual']in('',None):continue
    y=float(arms[new]['actual']);la=abs(float(arms[new]['prediction'])-y);lb=abs(float(arms[old]['prediction'])-y);cases.append((ident,la,lb,week,fb))
   source=next(r for r in rows if r['season']==2026 and r['procedure_id']=='v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf'and r['target']=='rec'and r['population']=='primary'and r['product_id']=='lower_median'and r['metric']=='MAE'and r['contrast']==contrast and r['fallback_view']==view)
   assert len(cases)==source['n'];assert hashlib.sha256(canonical(sorted(hashlib.sha256(canonical(x[0])).hexdigest()for x in cases))).hexdigest()==source['membership_sha256']
   if cases:
    n=len(cases);la=math.fsum(x[1]for x in cases)/n;lb=math.fsum(x[2]for x in cases)/n;close(la,source['candidate_error']);close(lb,source['comparator_error']);delta=la-lb
    games=collections.defaultdict(list)
    for ident,x,y,_,_ in cases:games[ident[0]].append(x-y-delta)
    if len(games)>=8:close(source['game_cluster_sensitivity_se'],math.sqrt(len(games)/(len(games)-1)*math.fsum(math.fsum(v)**2 for v in games.values()))/n)
    samples.append(dict(target='rec',contrast=contrast,fallback_view=view,n=n,candidate_error=la,comparator_error=lb,delta=delta))
   checks['raw_reception_sample_partitions_replayed']+=1
 result=dict(state='PASS_ALL_ADJACENT_DECOMPOSITIONS_AND_BOUNDED_RAW_WIN_LOSS_REPLAY',protocol_sha256=sha(pub/'FROZEN_PROTOCOL.json'),source_score_sha256=sha(pub/'SCORES.json'),comparison_views=len(rows),new_univariate_forecast_score_views=0,finite_whole_week_bootstrap_intervals_independently_recomputed=finite_ci,raw_forecast_rows_streamed=read,raw_same_three_arm_query_cells=len(raw),raw_sampled_comparison_views=samples,checks=dict(checks),limitations='All saved aggregate algebra, mask equality and weekly bootstrap recomputed; raw player-game replay is scoped to one2026rec law/point product and both adjacent win/loss contrasts. Other raw outcomes/scores previously reviewed separately. Same learner inputs except empirical estimator memory changes remain registered;2022RECENT2021 source gap persists. Seven2026weeks do not support weekCI. Exposed results are descriptive, not a selector or new independent NFL games.',new_fits=0,inference_calls=0,new_forecasts=0,current2026_week8_outcomes_read=0,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
 (HERE/'HISTORY_ADJACENT_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
