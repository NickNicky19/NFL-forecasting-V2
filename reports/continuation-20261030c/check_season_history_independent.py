"""Independent saved-row paired histories and whole-week bootstrap replay."""
import argparse,csv,gzip,hashlib,json,math,resource,sys,time
from array import array
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'reports/continuation-20261030c';sys.path.insert(0,str(HERE))
from check_season_scores_independent import sha,close
CONTRASTS=(('H-RECENT_MINUS_H-CURRENT','H-RECENT-COMMON','H-CURRENT-COMMON'),('H-MULTI_MINUS_H-CURRENT','H-MULTI-COMMON','H-CURRENT-COMMON'),('STRICT_MINUS_COMMON_CURRENT','H-CURRENT-STRICT','H-CURRENT-COMMON'))
def normalized(x):
 for suffix in(':common-feature-memory',':strict-current-inputs',':strict-current-feature-memory'):x=x.replace(suffix,'')
 return x
def key(s):return tuple(s[k]for k in('procedure_id','procedure_family_id','target','population','product_id','contrast','fallback_view','metric'))
def verify(public,private,repair_public=None,repair_private=None):
 start,cpu=time.monotonic(),time.process_time();run=json.loads((public/'RUN_RECEIPT.json').read_text());year=run['evaluation_season'];assert sha(private/run['private_flat']['bundle_name'])==run['private_flat']['sha256'];overlay=defaultdict(list);superseded=set();c=Counter()
 if repair_public:
  rr=json.loads((repair_public/'RUN_RECEIPT.json').read_text());path=repair_private/rr['private_flat']['bundle_name'];assert sha(path)==rr['private_flat']['sha256'];assert rr['source_prediction_sha256']==run['private_flat']['sha256']
  with gzip.open(path,'rt',newline='')as f:
   for r in csv.DictReader(f):overlay[int(r['week'])].append(r);superseded.add((r['procedure_id'],r['target'],r['policy_id']))
 groups={}
 for path in sorted((private/'predictions').glob('W*.csv.gz')):
  cases=defaultdict(dict);week=int(path.name[1:3])
  with gzip.open(path,'rt',newline='')as f:
   for r in csv.DictReader(f):
    if (r['procedure_id'],r['target'],r['policy_id'])in superseded:continue
    if r['actual']=='':continue
    k=normalized(r['procedure_id']),r['family'],r['target'],r['population'],r['product_id'],r['query_id'];assert r['policy_id']not in cases[k];cases[k][r['policy_id']]=r
  for r in overlay[week]:
   if r['actual']!='':cases[normalized(r['procedure_id']),r['family'],r['target'],r['population'],r['product_id'],r['query_id']][r['policy_id']]=r
  for (procedure,family,target,population,product,query),policies in cases.items():
   for contrast,new,old in CONTRASTS:
    if new not in policies or old not in policies:continue
    a,b=policies[new],policies[old];assert(a['game_id'],a['actual'],a['query_id'],a['position'])==(b['game_id'],b['actual'],b['query_id'],b['position']);y=float(a['actual']);fn=lambda p:(p-y)**2 if target=='anytime_td'else abs(p-y);items=[('Brier'if target=='anytime_td'else'MAE',product,fn(float(a['prediction'])),fn(float(b['prediction'])))];c['exact_query_label_position_policy_pairs']+=1
    if a['distribution_summary']and b['distribution_summary']and product in('mean','event_probability'):
     ad,bd=json.loads(a['distribution_summary']),json.loads(b['distribution_summary']);items.extend((('CRPS','distribution',ad['crps'],bd['crps']),('PMF_NLL','distribution',math.inf if ad['infinite_nll']else ad['nll'],math.inf if bd['infinite_nll']else bd['nll'])))
    for view in('FULL_SYSTEM','PAIRED_LEARNED_ONLY'):
     if view=='PAIRED_LEARNED_ONLY'and(a['fallback']!='none'or b['fallback']!='none'):continue
     for metric,viewproduct,la,lb in items:
      k=procedure,family,target,population,viewproduct,contrast,view,metric
      if k not in groups:groups[k]=dict(a=array('d'),b=array('d'),weeks=array('i'),games=[])
      g=groups[k];g['a'].append(la);g['b'].append(lb);g['weeks'].append(week);g['games'].append(a['game_id'])
 scores=json.loads((public/'HISTORY_COMPARISONS.json').read_text());assert len(scores)==len(groups);examples=[]
 for s in scores:
  g=groups[key(s)];n=len(g['a']);assert s['n']==n;assert s['bootstrap_seed']==1703 and s['bootstrap_replicates']==500;assert s['week_clusters']==len(set(g['weeks']))and s['game_clusters']==len(set(g['games']));inf_a=sum(math.isinf(x)for x in g['a']);inf_b=sum(math.isinf(x)for x in g['b']);assert s['candidate_infinite_rows']==inf_a and s['comparator_infinite_rows']==inf_b
  if inf_a or inf_b:
   assert s['status']=='NONFINITE_LOSS_DIFFERENCE_UNDEFINED'and s['delta']is None and s['week_interval']is None;c['explicit_nonfinite_contrasts']+=1;continue
  a,b=math.fsum(g['a'])/n,math.fsum(g['b'])/n;delta=math.fsum(x-y for x,y in zip(g['a'],g['b']))/n;close(s['candidate_error'],a);close(s['comparator_error'],b);close(s['delta'],delta);close(s['relative_error_change'],delta/b if b else None)
  if not b:assert s['relative_error_missing_reason']=='zero_comparator_error_denominator';c['zero_denominator_guards']+=1
  weeks=defaultdict(list);games=defaultdict(list)
  for x,y,w,game in zip(g['a'],g['b'],g['weeks'],g['games']):weeks[w].append(x-y);games[game].append(x-y)
  for w,d in weeks.items():close(s['weekly_paired_sums_counts'][str(w)]['loss_difference_sum'],math.fsum(d));assert s['weekly_paired_sums_counts'][str(w)]['n']==len(d);c['independent_week_sums_and_counts']+=2
  if len(weeks)>=8:
   ordered=sorted(weeks);rng=np.random.Generator(np.random.PCG64(1703));draws=[]
   for indices in rng.integers(0,len(ordered),size=(500,len(ordered))):
    draws.append(math.fsum(math.fsum(weeks[ordered[int(i)]])for i in indices)/sum(len(weeks[ordered[int(i)]])for i in indices))
   draws.sort();quant=lambda p:(lambda x:draws[math.floor(x)]+(draws[math.ceil(x)]-draws[math.floor(x)])*(x-math.floor(x)))(499*p)
   for a,b in zip(s['week_interval'],(quant(.025),quant(.975))):close(a,b)
   assert s['week_interval_status']=='NOMINAL_WHOLE_WEEK_PAIRED_BOOTSTRAP';c['independent_500_draw_wholeweek_intervals']+=1
  else:assert s['week_interval']is None and s['week_interval_status']=='INSUFFICIENT_WEEK_CLUSTERS';c['insufficient_week_cluster_flags']+=1
  if len(games)>=8:
   residual=[math.fsum(d)-delta*len(d)for d in games.values()];se=math.sqrt(len(games)/(len(games)-1)*math.fsum(x*x for x in residual))/n;close(s['game_cluster_sensitivity_se'],se);close(s['game_normal95_sensitivity'][0],delta-1.96*se);close(s['game_normal95_sensitivity'][1],delta+1.96*se);c['independent_game_influence_SEs']+=1
  c['finite_history_contrasts']+=1
  if s['population']=='primary'and s['fallback_view']=='FULL_SYSTEM'and s['metric']=='MAE':
   kind='win'if delta<0 else'loss'if delta>0 else'tie'
   if kind not in {e['direction']for e in examples}:examples.append(dict(direction=kind,target=s['target'],procedure_id=s['procedure_id'],product_id=s['product_id'],contrast=s['contrast'],n=n,candidate_error=s['candidate_error'],comparator_error=s['comparator_error'],delta=s['delta'],week_interval=s['week_interval']))
 return dict(state='PASS_ALL_SAVED_ROW_HISTORY_CONTRASTS_AND_INDEPENDENT_BLOCK_UNCERTAINTY',season=year,score_views=len(scores),source_history_sha256=sha(public/'HISTORY_COMPARISONS.json'),source_prediction_sha256=run['private_flat']['sha256'],checks=dict(c),representative_observed_win_loss=examples,interpretation='Samegamepairedcurrent-vintagehistorycomparisonswithfallbacks; strictchangesfullinformationpolicy. Nominalwholeweekintervalsnotmultiplicityadjusted, notfreshconfirmation; seasonbalancedaveragescannotanswerfixed2026historyquestion.',resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--public',type=Path,required=True);a.add_argument('--private',type=Path,required=True);a.add_argument('--repair-public',type=Path);a.add_argument('--repair-private',type=Path);args=a.parse_args();r=verify(args.public,args.private,args.repair_public,args.repair_private);(HERE/('SEASON_'+str(r['season'])+'_HISTORY_INDEPENDENT_REVIEW.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
