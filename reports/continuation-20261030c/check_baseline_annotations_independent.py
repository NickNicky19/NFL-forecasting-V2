"""Check source-bound baseline comparisons and two raw-row uncertainty cases."""
import csv,gzip,hashlib,json,math,resource,sys,time
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'reports/continuation-20261030c';sys.path.insert(0,str(HERE))
from review_paths import companion_root,source_root
from check_season_scores_independent import sha,close
from check_defense_features_independent import canonical
CASES=((2025,'season-2025-v1','seasonal-rolling-2025-v1'),(2024,'season-2024-v2','seasonal-rolling-2024-v2'),(2023,'season-2023-complete-replay-v1','seasonal-rolling-2023-complete-replay-v1'),(2022,'season-2022-v2','seasonal-rolling-2022-v2'),(2025,'season-2025-continuity-repair-v1','seasonal-rolling-2025-v1'))
def verify():
 start,cpu=time.monotonic(),time.process_time();c=Counter();proofs=[];sample=[]
 for year,directory,priv in CASES:
  public=HERE/directory;private=companion_root()/priv;parent=HERE/'season-2025-v1'if'continuity-repair'in directory else public;source=json.loads((public/'SCORES.json').read_text());baselines=json.loads((parent/'SCORES.json').read_text());run=json.loads((parent/'RUN_RECEIPT.json').read_text());labelpath=private/run['labels']['bundle_name'];ann=json.loads((public/'BASELINE_COMPARISON_ANNOTATIONS.json').read_text());assert ann['source_score_sha256']==sha(public/'SCORES.json')and ann['baseline_source_score_sha256']==sha(parent/'SCORES.json')and ann['label_packet_sha256']==sha(labelpath);labels=json.loads(gzip.decompress(labelpath.read_bytes()));assert len(ann['rows'])==len(source);bm={}
  for r in baselines:
   if r['procedure_id']=='empirical-player-history-control-v1'and r['fallback_view']=='ALL':bm[r['target'],r['population'],str(r['week']),r['position'],r['history_regime'],r['product_id']]=r
  groups=defaultdict(list)
  for r in labels:
   if r['actual']is not None:groups[r['target'],r['population'],r['week'],r['position']].append([r[k]for k in('game_id','player_id','target','population')])
  membercache={};counts=Counter()
  for i,item in enumerate(ann['rows']):
   assert item['source_row_index']==i;r=source[i];comparison=item['comparison'];counts[comparison['status']]+=1
   if comparison['status']!='PAIRED_RETAINED_ROWS':assert r['fallback_view']!='ALL'or not r['n'];c['explicit_unpaired_subset_or_empty_views']+=1;continue
   product='event_probability'if r['target']=='anytime_td'else'mean';arm='H-CURRENT'if r['procedure_id']=='empirical-player-history-control-v1'and r['history_regime']=='H-RECENT'and r['product_id']==product else'H-RECENT';control=bm[r['target'],r['population'],str(r['week']),r['position'],arm,product];metric='brier'if r['target']=='anytime_td'else'mae';assert comparison['comparator_history_regime']==arm and comparison['comparator_product_id']==product and comparison['metric']==metric;close(comparison['candidate_error'],r[metric]);close(comparison['comparator_error'],control[metric]);assert comparison['paired_n']==r['n']==control['n'];mk=r['target'],r['population'],tuple(r['evaluation_weeks']),r['position']
   if mk not in membercache:
    ids=[]
    for (t,pop,w,pos),values in groups.items():
     if(t,pop)==mk[:2]and w in mk[2]and(mk[3]=='ALL'or pos==mk[3]):ids.extend(values)
    membercache[mk]=len(ids),hashlib.sha256(canonical(sorted(ids))).hexdigest()
   n,member=membercache[mk];assert n==r['n']and comparison['membership_sha256']==member;c['independent_annotation_metrics_counts_and_identity_hashes']+=1;u=comparison['uncertainty']
   if r['position']!='ALL'and len(r['evaluation_weeks'])>=8:assert u['week_interval']is None and u['week_interval_status']=='NOT_COMPUTED_POSITION_WEEK_LOSSES_UNRETAINED';c['honest_position_week_uncertainty_gaps']+=1
   if directory=='season-2025-v1'and r['population']=='primary'and r['week']=='ALL'and r['position']=='ALL'and not r['procedure_id'].startswith('empirical'):
    direction='win'if r[metric]<control[metric]else'loss'if r[metric]>control[metric]else'tie'
    if direction in('win','loss')and direction not in{x['direction']for x in sample}:sample.append(dict(direction=direction,source_row_index=i,row=r,comparison=comparison))
  proofs.append(dict(source=directory,source_score_sha256=sha(public/'SCORES.json'),annotation_sha256=sha(public/'BASELINE_COMPARISON_ANNOTATIONS.json'),views=len(source),statuses=dict(counts)))
 assert len(sample)==2;path=companion_root()/'seasonal-rolling-2025-v1/predictions.csv.gz';values=[dict(a={},b={})for _ in sample]
 with gzip.open(path,'rt',newline='')as f:
  for raw in csv.DictReader(f):
   if raw['actual']=='':continue
   for s,out in zip(sample,values):
    r=s['row'];cmp=s['comparison']
    if(raw['target'],raw['population'])!=(r['target'],r['population']):continue
    target=None
    if(raw['procedure_id'],raw['policy_id'],raw['product_id'])==(r['procedure_id'],r['policy_id'],r['product_id']):target='a'
    if(raw['procedure_id'],raw['history_regime'],raw['product_id'])==('empirical-player-history-control-v1',cmp['comparator_history_regime'],cmp['comparator_product_id']):target='b'
    if target:
     key=tuple(raw[k]for k in('game_id','player_id','target','population'));assert key not in out[target];out[target][key]=float(raw['prediction']),float(raw['actual']),int(raw['week'])
 examples=[]
 for s,raw in zip(sample,values):
  assert raw['a'].keys()==raw['b'].keys();weeks=defaultdict(list);a=[];b=[]
  for key,(pred,y,w)in raw['a'].items():
   pred2,y2,w2=raw['b'][key];assert(y,w)==(y2,w2);fn=lambda x:(x-y)**2 if s['row']['target']=='anytime_td'else abs(x-y);a.append(fn(pred));b.append(fn(pred2));weeks[w].append(fn(pred)-fn(pred2))
  n=len(a);close(s['comparison']['candidate_error'],math.fsum(a)/n);close(s['comparison']['comparator_error'],math.fsum(b)/n);rng=np.random.Generator(np.random.PCG64(1703));ws=sorted(weeks);sums=[math.fsum(weeks[w])for w in ws];ns=[len(weeks[w])for w in ws];draws=[]
  for ix in rng.integers(0,len(ws),size=(500,len(ws))):draws.append(math.fsum(sums[int(j)]for j in ix)/sum(ns[int(j)]for j in ix))
  draws.sort();q=lambda p:(lambda x:draws[math.floor(x)]+(draws[math.ceil(x)]-draws[math.floor(x)])*(x-math.floor(x)))(499*p)
  for x,y in zip(s['comparison']['uncertainty']['week_interval'],(q(.025),q(.975))):close(x,y)
  c['independent_raw_case_point_and_500_draw_interval_replays']+=1;examples.append(dict(direction=s['direction'],target=s['row']['target'],procedure_id=s['row']['procedure_id'],policy_id=s['row']['policy_id'],product_id=s['row']['product_id'],n=n,candidate_error=math.fsum(a)/n,baseline_error=math.fsum(b)/n,delta=(math.fsum(a)-math.fsum(b))/n,week_interval=[q(.025),q(.975)]))
 return dict(state='PASS_ALL_SOURCE_BOUND_BASELINE_ANNOTATIONS_AND_TWO_RAW_PAIRED_UNCERTAINTY_REPLAYS',sources=proofs,checks=dict(c),representative_win_loss=examples,scope='Allfiveannotationfilesmetrics/identitymasks/coverage; tworepresentative2025rawrowbootstrapcomparisons. FixedempiricalHRECENTmean/eventbaseline, selfswitchCURRENT; notstrongestlearnedcontrol, no newNFLobservations. Unretainedposition×weeklossesandprocedure-specificlearnedsubsetsremainexplicitunknown.',resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
if __name__=='__main__':
 r=verify();(HERE/'BASELINE_ANNOTATIONS_INDEPENDENT_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
