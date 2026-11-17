"""All annotation-mask metadata plus three independent raw learned-mask cases."""
import csv,gzip,hashlib,json,math,resource,sys,time
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'reports/continuation-20261030c';sys.path.insert(0,str(HERE))
from review_paths import companion_root,source_root
from check_season_scores_independent import sha,close
from check_defense_features_independent import canonical
from check_baseline_annotations_independent import CASES
def verify():
 start,cpu=time.monotonic(),time.process_time();p=json.loads((HERE/'learned-mask-baseline-v2/FROZEN_PROTOCOL.json').read_text());run=json.loads((HERE/'learned-mask-baseline-v2/RUN_RECEIPT.json').read_text());assert run['state']=='COMPLETE'and run['protocol_sha256']==sha(HERE/'learned-mask-baseline-v2/FROZEN_PROTOCOL.json');c=Counter();samples=[];sources=[]
 for year,directory,_ in CASES:
  pub=HERE/directory;scores=json.loads((pub/'SCORES.json').read_text());old=json.loads((pub/'BASELINE_COMPARISON_ANNOTATIONS.json').read_text());new=json.loads((pub/'BASELINE_COMPARISON_ANNOTATIONS_V2.json').read_text());assert new['source_score_sha256']==sha(pub/'SCORES.json')and new['parent_annotations_sha256']==sha(pub/'BASELINE_COMPARISON_ANNOTATIONS.json');assert len(new['rows'])==len(old['rows'])==len(scores);count=0
  for i,(r,a,b)in enumerate(zip(scores,old['rows'],new['rows'])):
   if r['fallback_view']!='LEARNED_ONLY':assert a==b;c['unchanged_original_annotation_objects']+=1;continue
   comp=b['comparison'];assert b['source_row_index']==i and comp['status']=='PAIRED_RETAINED_ROWS';metric='brier'if r['target']=='anytime_td'else'mae';assert comp['metric']==metric and comp['paired_n']==r['n'];close(comp['candidate_error'],r[metric]);assert comp['comparator_history_regime']=='H-RECENT'and comp['comparator_product_id']==('event_probability'if r['target']=='anytime_td'else'mean');assert len(comp['membership_sha256'])==64;assert comp['uncertainty']['n']==r['n'];close(comp['uncertainty']['comparator_error'],comp['comparator_error']);c['all_learned_candidate_loss_n_mask_and_control_metadata']+=1;count+=1
   for name,v in comp['comparator_subset_precision'].items():assert v['denominator']==r['n']and 0<=v['numerator']<=r['n'];close(v['rate'],v['numerator']/r['n']);c['baseline_exact_tolerance_numerator_denominators']+=1
   if directory=='season-2025-v1':
    label='empirical_bug_case'if r['procedure_id']=='empirical-player-history-control-v1'and r['target']=='anytime_td'and r['history_regime']=='H-CURRENT'else'win'if comp['candidate_error']<comp['comparator_error']else'loss'
    if r['population']=='primary'and label not in{x['label']for x in samples}and(label=='empirical_bug_case'or r['procedure_id'].startswith('hgb-direct')):samples.append(dict(label=label,index=i,row=r,comparison=comp))
  sources.append(dict(source=directory,new_annotation_sha256=sha(pub/'BASELINE_COMPARISON_ANNOTATIONS_V2.json'),learned_views=count))
 assert len(samples)==3 and sum(x['learned_views']for x in sources)==run['learned_views_completed']==2720
 datasets=[dict(a={},b={})for s in samples];path=companion_root()/'seasonal-rolling-2025-v1/predictions.csv.gz';assert sha(path)==p['sources'][0]['source_flat_sha256']
 with gzip.open(path,'rt',newline='')as f:
  for raw in csv.DictReader(f):
   if raw['actual']=='':continue
   for s,out in zip(samples,datasets):
    r=s['row'];comp=s['comparison']
    if(raw['target'],raw['population'])!=(r['target'],r['population']):continue
    value=(float(raw['prediction']),float(raw['actual']),int(raw['week']),raw['game_id']);qid=raw['query_id']
    if(raw['procedure_id'],raw['policy_id'],raw['product_id'])==(r['procedure_id'],r['policy_id'],r['product_id'])and raw['fallback']=='none':assert qid not in out['a'];out['a'][qid]=value
    if(raw['procedure_id'],raw['history_regime'],raw['product_id'])==('empirical-player-history-control-v1','H-RECENT',comp['comparator_product_id']):assert qid not in out['b'];out['b'][qid]=value
 examples=[]
 for s,data in zip(samples,datasets):
  comp=s['comparison'];n=len(data['a']);assert n==comp['paired_n'];assert hashlib.sha256(canonical(sorted(data['a']))).hexdigest()==comp['membership_sha256'];a=[];b=[];errors=[];weeks=defaultdict(list);games=defaultdict(list);precision=Counter()
  for qid,(p,y,w,game)in data['a'].items():
   pred,actual,w2,g2=data['b'][qid];assert(y,w,game)==(actual,w2,g2);loss=lambda v:(v-y)**2 if s['row']['target']=='anytime_td'else abs(v-y);x,z=loss(p),loss(pred);a.append(x);b.append(z);errors.append(pred-y);weeks[w].append(x-z);games[game].append(x-z);err=abs(pred-y);precision['exact_rate']+=err==0
   for t in(1,5,10):precision['abs_lt_'+str(t)]+=err<t;precision['abs_le_'+str(t)]+=err<=t
  close(comp['candidate_error'],math.fsum(a)/n);close(comp['comparator_error'],math.fsum(b)/n);close(comp['comparator_subset_mae'],math.fsum(map(abs,errors))/n);close(comp['comparator_subset_mse'],math.fsum(x*x for x in errors)/n);close(comp['comparator_subset_bias'],math.fsum(errors)/n)
  for name,v in precision.items():assert comp['comparator_subset_precision'][name]['numerator']==v
  delta=math.fsum(x-y for x,y in zip(a,b))/n;u=comp['uncertainty'];close(u['delta'],delta);close(u['relative_error_change'],delta/(math.fsum(b)/n)if math.fsum(b)else None);ws=sorted(weeks);rng=np.random.Generator(np.random.PCG64(1703));sums=[math.fsum(weeks[w])for w in ws];counts=[len(weeks[w])for w in ws];draws=[]
  for ix in rng.integers(0,len(ws),size=(500,len(ws))):draws.append(math.fsum(sums[int(i)]for i in ix)/sum(counts[int(i)]for i in ix))
  draws.sort();q=lambda p:(lambda x:draws[math.floor(x)]+(draws[math.ceil(x)]-draws[math.floor(x)])*(x-math.floor(x)))(499*p)
  for x,y in zip(u['week_interval'],(q(.025),q(.975))):close(x,y)
  se=math.sqrt(len(games)/(len(games)-1)*math.fsum((math.fsum(ds)-delta*len(ds))**2 for ds in games.values()))/n;close(u['game_cluster_sensitivity_se'],se);c['raw_join_qid_membership_loss_precision_500bootstrap_gameSE_cases']+=1;examples.append(dict(label=s['label'],source_row_index=s['index'],target=s['row']['target'],procedure_id=s['row']['procedure_id'],policy_id=s['row']['policy_id'],n=n,candidate_error=comp['candidate_error'],control_error=comp['comparator_error'],delta=delta,week_interval=u['week_interval']))
 oldrun=json.loads((HERE/'learned-mask-baseline-v1/RUN_RECEIPT.json').read_text());assert run['resource']['wall_seconds']+oldrun['resource']['wall_seconds']<=180;assert run['resource']['cpu_seconds']+oldrun['resource']['cpu_seconds']<=240
 return dict(state='PASS_ALL_LEARNED_ANNOTATION_METADATA_AND_THREE_INDEPENDENT_RAW_MASK_CASES',source_protocol_sha256=sha(HERE/'learned-mask-baseline-v2/FROZEN_PROTOCOL.json'),source_receipt_sha256=sha(HERE/'learned-mask-baseline-v2/RUN_RECEIPT.json'),sources=sources,checks=dict(c),representative_cases=examples,scope='All2720newlearnedannotationscandidate/controlmetadata+precisiondenominators; threesaved-rowmask/loss/500bootstrap/gameSEreplaysincludingempiricalbugcase. Originalfullsystemannotationsunchanged; notevery2720rawsubsetindependentlyreplayed.',producer_resource_cumulative=dict(raw_rows_decoded=oldrun['rows_read']+run['rows_read'],wall_seconds=oldrun['resource']['wall_seconds']+run['resource']['wall_seconds'],cpu_seconds=oldrun['resource']['cpu_seconds']+run['resource']['cpu_seconds'],note='Rowcapspersealedattempt; aggregateincludesfailedv1readagain. No newNFLsamples orfits.'),resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
if __name__=='__main__':
 r=verify();(HERE/'LEARNED_BASELINES_BOUNDED_INDEPENDENT_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
