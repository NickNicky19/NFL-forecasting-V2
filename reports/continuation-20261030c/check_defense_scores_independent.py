"""Independent D1/D2 saved-row/error/control and future-null capture check."""
import argparse,csv,gzip,hashlib,json,math,sys,time,resource
from collections import Counter,defaultdict
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/continuation-20261030c';sys.path.insert(0,str(OUT))
from check_season_scores_independent import Stats,load_truth,close,sha,groups_add
from check_shared_subgroups_independent import packet,canonical
PUB=OUT/'qualified-defense-information-v1'
def epoch(v):return datetime.fromisoformat(v.replace('Z','+00:00')).timestamp()
def ident(r):return tuple(r[k]for k in('game_id','player_id','target','population'))
def control_key(r):return(r['target'],r['policy_id'],r['game_id'],r['player_id'],r['population'],r['product_id'])
def score_key(r):return tuple(r[k]for k in('procedure_id','procedure_family_id','target','policy_id','history_regime','product_id','population'))+(str(r['week']),r['position'],r['fallback_view'])
def verify(private,source):
 start,cpu=time.monotonic(),time.process_time();p=json.loads((PUB/'FROZEN_PROTOCOL.json').read_text());run=json.loads((PUB/'HISTORICAL_RUN_RECEIPT.json').read_text());future=json.loads((PUB/'WEEK8_CAPTURE_RECEIPT.json').read_text());checks=Counter();assert sha(PUB/'FROZEN_PROTOCOL.json')==run['protocol_sha256']==future['protocol_sha256'];rows,labels,games=load_truth(source,p,2026)
 # load_truth's2026 source must be capped before Week8values; frozen source CSV
 # has no2026Week8rows and no source refresh is performed by this checker.
 assert all(r['week']<=7 for r in rows if r['season']==2026)
 controls={}
 for spec,directory in zip(p['control_prediction_sources'],('distribution-wave-v2','chart-wave-v1')):
  path=private.parent/directory/spec['artifact_id'];assert sha(path)==spec['sha256']
  with gzip.open(path,'rt',newline='')as f:
   for r in csv.DictReader(f):
    if r['season']!='2026'or int(r['week'])>7 or r['family']!='ordered_leaf_cdf':continue
    controls[control_key(r)]=(float(r['prediction']),None if r['actual']==''else float(r['actual']),r['fallback'],r['procedure_id'])
 groups=defaultdict(Stats);pairrows=defaultdict(list);count=0;path=private/run['private_prediction_packet']['bundle_name'];assert sha(path)==run['private_prediction_packet']['sha256'];highlights=[];examples={}
 for r in packet(path):
  assert r['season']==2026 and 1<=r['week']<=7;k=r['game_id'],r['player_id'];truth=labels[k];value=truth['values'][r['target']];value=value/50 if value is not None and r['target']=='nick-chart-ppr-v1'else value;close(r['actual'],value);assert r['position']==truth['position'];checks['independent_raw_label_position_checks']+=2
  c=controls[control_key(r)];assert r['control_prediction']==c[0]and r['actual']==c[1]and r['control_fallback']==c[2]and r['control_procedure_id']==c[3];checks['original_control_joins']+=1
  r['family']=r['procedure_family_id'];base=tuple(r[k]for k in('procedure_id','family','target','policy_id','history_regime','product_id','population'));suffix=[('ALL','ALL','ALL'),(str(r['week']),'ALL','ALL'),('ALL',r['position'],'ALL')]
  if r['fallback']=='none':suffix.append(('ALL','ALL','LEARNED_ONLY'))
  if r['fallback']==r['control_fallback']=='none':suffix.append(('ALL','ALL','PAIRED_LEARNED_OVERLAP'))
  for ending in suffix:groups[base+ending].add(r);pairrows[base+ending].append((ident(r),r['game_id'],r['week'],r['prediction'],r['actual'],r['control_prediction']))
  count+=1
 scores=json.loads((PUB/'SCORES.json').read_text());assert len(scores)==len(groups)==3216 and count==run['forecast_output_views']==268336
 for s in scores:
  key=score_key(s);expected=groups[key].result(s['target'])
  for field,value in expected.items():
   if field not in s:continue
   if field=='NLL'and value==math.inf:assert s[field]is None and s['infinite_NLL']>0
   elif isinstance(value,(dict,list)):assert s[field]==value
   else:close(s[field],value)
   checks['native_distribution_coverage_precision_checks']+=1
  chosen=[r for r in pairrows[key]if r[4]is not None];comparison=s['comparison']
  if chosen:
   measure=lambda x,y:(x-y)**2 if s['target']=='anytime_td'else abs(x-y);a=[measure(r[3],r[4])for r in chosen];b=[measure(r[5],r[4])for r in chosen];delta=math.fsum(x-y for x,y in zip(a,b))/len(a);close(comparison['candidate_error'],math.fsum(a)/len(a));close(comparison['comparator_error'],math.fsum(b)/len(b));close(comparison['absolute_error_delta'],delta);assert comparison['paired_n']==len(chosen);assert comparison['membership_sha256']==hashlib.sha256(canonical(sorted(r[0]for r in chosen))).hexdigest();checks['paired_loss_membership_checks']+=5
   if s['policy_id']=='H-MULTI-COMMON'and s['population']=='primary'and s['week']==s['position']==s['fallback_view']=='ALL'and s['product_id']in('lower_median','event_probability'):
    highlights.append(dict(target=s['target'],information_group=s['information_group'],product=s['product_id'],n=len(chosen),candidate=math.fsum(a)/len(a),control=math.fsum(b)/len(b),delta=delta))
    for row,la,lb in zip(chosen,a,b):
     kind='win'if la<lb else'loss'if la>lb else'tie'
     if kind not in examples:examples[kind]=dict(id=hashlib.sha256(canonical(row[0])).hexdigest()[:16],target=s['target'],information_group=s['information_group'],candidate_loss=la,control_loss=lb)
  else:assert comparison['status']=='UNESTABLISHED'
 fpath=private/future['packet']['bundle_name'];assert sha(fpath)==future['packet']['sha256'];qdoc=json.loads((private/'frozen-queries.json').read_text());qmap={q['query_id']:q for q in qdoc['week8']};assert len(qmap)==2229;future_groups=defaultdict(dict);future_count=issued=abstain=0;asof=epoch(p['fixed_future_query_asof_utc']);persisted=epoch(future['actual_aggregate_persistence_completed_at'])
 for r in packet(fpath):
  assert r['actual']is None and r['actual_status']=='PENDING_FUTURE'and r['week']==8 and r['season']==2026;assert r['feature_cutoff_utc']==p['fixed_future_query_asof_utc'];q=qmap[r['query_id']]
  for key in('game_id','player_id','target','position','team','defense'):assert r[key]==q[key]
  if r['prediction']is not None:
   assert asof<=epoch(r['issued_at_utc'])<=persisted<epoch(r['owner_input_cutoff_utc'])<epoch(r['kickoff_utc']);assert r['issued_at_utc']==r['actual_generated_at'];issued+=1
  else:assert r['status']=='ABSTAIN'and r['abstention_reason'];abstain+=1
  key=r['policy_id'],r['product_id'],r['query_id'];assert r['variant']not in future_groups[key];future_groups[key][r['variant']]=r;future_count+=1
 for rs in future_groups.values():
  assert set(rs)=={'retained_ordered_control','D1','D2'}
  for field in('fallback','abstention_reason','training_fit_cutoff_utc','actual'):assert len({r[field]for r in rs.values()})==1
  checks['three_way_same_query_route_pairs']+=1
 assert future_count==future['output_views']==48732 and issued==future['issued']==48564 and abstain==future['abstained']==168;assert len({q['game_id']for q in qmap.values()})==13
 return dict(status='PASS_ALL_D1_D2_NATIVE_PROPER_AGGREGATES_CONTROL_JOINS_AND_FUTURE_NULL_CLOCKS',historical_rows=count,score_views=len(scores),checks=dict(checks),H_MULTI_primary_median_and_event_examples=highlights,redacted_win_loss=examples,future_rows=future_count,issued=issued,abstained=abstain,future_persistence_utc=future['actual_aggregate_persistence_completed_at'],historical_packet_sha256=sha(path),future_packet_sha256=sha(fpath),score_sha256=sha(PUB/'SCORES.json'),verification_resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),scope='Allretainedhistoricalrowlabels/pointandproperaggregate/math/controljoins verified; source-derivedDfeatures/prefixes andmodelPMFsample require separate review. Everyfutureactualnull; actualissues/persistence checked before13T90deadlines.',new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private',type=Path,required=True);parser.add_argument('--source',type=Path,required=True);args=parser.parse_args();r=verify(args.private,args.source);OUT.joinpath('DEFENSE_SCORE_CAPTURE_INDEPENDENT_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='H_MULTI_primary_median_and_event_examples'}))
