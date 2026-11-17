"""Full selector replay plus bounded full-system subgroup metrics; no fitting."""
import bisect,csv,gzip,hashlib,json,math,resource,sys,time
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'reports/continuation-20261030c';sys.path.insert(0,str(HERE))
from review_paths import companion_root,source_root
from check_season_scores_independent import load_truth,read_row,Stats,sha,close
from check_defense_features_independent import attach,canonical,CHART
SAMPLE_COHORTS={'all','top10','rank11_15','rank16_20','rank21plus','workload_high','score_history_high','unranked'}
def identity(r):return tuple(r[k]for k in('game_id','player_id','target','population'))
def modelkey(r):return tuple(r[k]for k in('procedure_id','history_regime','product_id','target','population'))
def verify(public):
 start,cpu=time.monotonic(),time.process_time();p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());year=p['evaluation_season'];sp=ROOT/p['source_protocol_artifact'];sourcep=json.loads(sp.read_text());source=source_root();rows,lookup,games=load_truth(source,sourcep,year);attach(rows,source);hist=defaultdict(list)
 for r in rows:hist[r['player_id']].append(r)
 for rs in hist.values():rs.sort(key=lambda r:(r['available'],r['game_id']))
 times={k:[r['available']for r in rs]for k,rs in hist.items()};mp=companion_root()/'shared-season-cohort-memberships-v1'/f'memberships-{year}.json.gz';assert sha(mp)==p['membership_sha256'];members={tuple(m['key']):m for m in json.loads(gzip.decompress(mp.read_bytes()))};groups=defaultdict(list);c=Counter()
 for key,m in members.items():
  game,player,target,pop=key;r=lookup[game,player];week=r['week'];cutoff=min(g['kickoff']for g in games.values()if g['year']==year and g['week']==week)-5400;assert m['ranking_cutoff']==cutoff;end=bisect.bisect_left(times.get(player,[]),cutoff);rs=hist.get(player,[])[max(0,end-3):end];values=[]
  for old in rs:
   if target==CHART:value=old['values'][target]/50 if old['values'][target]is not None else None
   elif target.startswith('pass_'):value=old['workload']['attempts']
   elif target in('rush_att','rush_yd'):value=old['workload']['carries']
   elif target in('rec','rec_yd'):value=old['workload']['targets']
   else:value=old['workload']['carries']+old['workload']['targets']if all(old['workload'][k]is not None for k in('carries','targets'))else None
   if value is not None:values.append(value)
  expected=math.fsum(values)/len(values)if values else None;close(m['mean'],expected);assert m['supported_slots']==len(values)and m['history_slots']==len(rs);assert m['latest_available']==max((r['available']for r in rs),default=None);groups[week,target,pop].append((key,expected));c['source_last3_missing_slot_and_clock_profiles']+=1
 for (week,target,pop),rs in groups.items():
  ordered=sorted((k for k,v in rs if v is not None),key=lambda k:(-members[k]['mean'],k[1]));ranks={k:i+1 for i,k in enumerate(ordered)}
  for k,value in rs:
   rank=ranks.get(k);assert rank==members[k]['rank'];cohorts=['all']
   if rank is None:cohorts.append('unranked')
   else:cohorts.extend('top'+str(n)for n in(10,15,20)if rank<=n);cohorts.append('rank1_10'if rank<=10 else'rank11_15'if rank<=15 else'rank16_20'if rank<=20 else'rank21plus')
   if value is None:band='unknown'
   elif value==0:band='zero'
   else:
    low,high=(5,15)if target==CHART else(20,35)if target.startswith('pass_')else(5,12)if target in('rush_att','rush_yd','rush_rec_yd','anytime_td')else(3,7);band='low'if value<=low else'middle'if value<=high else'high'
   cohorts.append(('score_history_'if target==CHART else'workload_')+band);assert cohorts==members[k]['cohorts'];c['independent_ranks_nested_top_disjoint_and_bands']+=1
 scores=json.loads((public/'SCORES.json').read_text());selected=[s for s in scores if s['fallback_view']=='full_system'and s['cohort_id']in SAMPLE_COHORTS];wanted={modelkey(s)+(s['cohort_id'],):s for s in selected};stats={k:Stats()for k in wanted};ids=defaultdict(list);scoredids=defaultdict(list);candidate_points=defaultdict(list);controls={};baseprivate=companion_root()/('seasonal-rolling-'+str(year)+'-v1');flat=baseprivate/'predictions.csv.gz';assert sha(flat)==p['source_bindings'][0]['sha256']
 with gzip.open(flat,'rt',newline='')as f:
  for text in csv.DictReader(f):
   proc=text['procedure_id'];iscandidate=proc.startswith('v2-c02-');iscontrol='ordered_leaf_cdf:'in proc
   if not(iscandidate or iscontrol):continue
   r=read_row(text);ident=identity(r)
   if iscontrol:controls[modelkey(r),ident]=r['prediction'];continue
   for cohort in members[ident]['cohorts']:
    k=modelkey(r)+(cohort,)
    if k not in wanted:continue
    stats[k].add(r);ids[k].append(ident)
    if r['actual']is not None:scoredids[k].append(ident);candidate_points[k].append((r['prediction'],r['actual'],r['game_id'],r['week'],ident))
 examples=[]
 for k,s in wanted.items():
  expected=stats[k].result(s['target'])
  # This scorer's fallback-source census excludes the ordinary 'none' route;
  # the seasonal base scorer includes it. Preserve that explicit definition.
  expected['fallback_source_counts'].pop('none',None)
  for field,value in expected.items():
   if field not in s:continue
   if field=='NLL'and value==math.inf:
    assert s[field]is None and s['NLL_state']=='INFINITE'and s['infinite_NLL']>0;c['explicit_infinite_NLL_state_checks']+=1;continue
   if isinstance(value,(list,dict)):assert s[field]==value
   else:close(s[field],value)
   c['bounded_fullsystem_native_proper_precision_fields']+=1
  assert s['cohort_membership_sha256']==hashlib.sha256(canonical(sorted(ids[k]))).hexdigest()and s['scored_membership_sha256']==hashlib.sha256(canonical(sorted(scoredids[k]))).hexdigest();c['independent_selected_cohort_membership_hashes']+=2
  compare=s['comparison'];product=s['product_id'];strict=s['procedure_id'].endswith(':strict-current-inputs');control=('v2-qualified-partial-chart-direct-wave-v1:'if s['target']==CHART else'v2-distribution-controls-reconstruction-v2:')+'ordered_leaf_cdf:'+('strict-current-inputs'if strict else'common-feature-memory');mk=(control,s['history_regime'],product,s['target'],s['population']);paired=[]
  for pred,actual,game,week,ident in candidate_points[k]:
   q=controls.get((mk,ident))
   if q is not None:paired.append((pred,actual,q,game,week,ident))
  if not paired:assert compare['status']=='UNESTABLISHED';continue
  loss=lambda a,y:(a-y)**2 if s['target']=='anytime_td'else abs(a-y);a=math.fsum(loss(x,y)for x,y,_,_,_,_ in paired)/len(paired);b=math.fsum(loss(z,y)for _,y,z,_,_,_ in paired)/len(paired);close(compare['candidate_error'],a);close(compare['comparator_error'],b);close(compare['absolute_error_delta'],a-b);close(compare['relative_error_delta'],(a-b)/b if b else None);assert compare['paired_n']==len(paired);assert compare['membership_sha256']==hashlib.sha256(canonical(sorted(x[-1]for x in paired))).hexdigest();c['independent_primary_paired_metrics_memberships']+=6
  if s['population']=='primary'and s['cohort_id']=='top10':
   direction='win'if a<b else'loss'if a>b else'tie'
   if direction not in{e['direction']for e in examples}:examples.append(dict(direction=direction,record_id=s['record_id'],target=s['target'],history=s['history_regime'],product=product,cohort='top10',n=len(paired),candidate_error=a,control_error=b,delta=a-b))
 return dict(state='PASS_FULL_SEASONAL_SELECTOR_REPLAY_AND_BOUNDED_FULL_SYSTEM_SUBGROUP_SCORES',season=year,source_score_sha256=sha(public/'SCORES.json'),source_protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),membership_sha256=sha(mp),all_frozen_memberships=len(members),published_score_views=len(scores),independently_replayed_fullsystem_score_views=len(selected),checks=dict(c),representative_win_loss=examples,scope='Allselectorprofiles/ranks/bands; selectedfullsystemnative/proper/precision/membership+same-policyorderedcontrolcomparisons. Learnedintersections/globalreference72941sidecarnotfullyreplayed; separateknownfixedempiricalproductaliasdefectrequiresversionedcorrection. Sourceparticipantuniverse/commonoldselector notpurecurrentselectedsystem.',resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
if __name__=='__main__':
 public=Path(sys.argv[1]);r=verify(public);(HERE/f"SEASON_{r['season']}_SUBGROUP_BOUNDED_INDEPENDENT_REVIEW.json").write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
