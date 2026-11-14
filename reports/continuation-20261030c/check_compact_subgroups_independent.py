"""Independent full compact masks/point scores/pairing and block uncertainty."""
import csv,gzip,hashlib,json,math,resource,sys,time
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'reports/continuation-20261030c';sys.path.insert(0,str(HERE))
from review_paths import companion_root,source_root
from check_season_scores_independent import Stats,sha,close,grid
from check_defense_features_independent import canonical,CHART
from check_shared_subgroups_independent import packet
def ident(r):return tuple(r[k]for k in('game_id','player_id','target','population'))
def key(r):return tuple(r[k]for k in('target','procedure_id','history_regime','product_id'))
def verify(public):
 start,cpu=time.monotonic(),time.process_time();p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());run=json.loads((public/'RUN_RECEIPT.json').read_text());assert run['protocol_sha256']==sha(public/'FROZEN_PROTOCOL.json');private=companion_root();c=Counter();members={}
 for item in p['bindings']:assert sha(private/item['private_member'])==item['sha256'];c['frozen_source_hashes']+=1
 for name in p['memberships']:
  for r in json.loads(gzip.decompress((private/name).read_bytes())):i=tuple(r['key']);assert i not in members;members[i]=r
 wanted={key(x):x['group']for x in p['choices']};needed={key(x)for x in p['reference_specs']};candidates=[];controls=defaultdict(dict);direct=defaultdict(dict)
 def admit(raw,kind):
  if int(raw.get('season',2026))!=p['evaluation_season']or not 1<=int(raw['week'])<=(7 if p['evaluation_season']==2026 else 18):return
  if p['mode']=='season'and p.get('role_overlay')and kind=='season_base'and'qb-rb-specialization'in raw['procedure_id']:return
  proc=raw.get('procedure_id')or('empirical-player-history-control-v1'if kind=='empirical'else'hgb-direct-history-controls-v1:'+raw['objective']);product=raw.get('product_id')or raw.get('product')or raw.get('objective');k=raw['target'],proc,raw['history_regime'],product
  if k not in wanted and k not in needed:return
  r={name:raw[name]for name in('game_id','player_id','target','population','position','history_regime','fallback')};number=lambda v:None if v in('',None)else float(v);r.update(week=int(raw['week']),procedure_id=proc,product_id=product,prediction=number(raw.get('prediction')),actual=number(raw.get('actual')),distribution_summary=None,actual_grid=None)
  if r['target']==CHART and r['actual']is not None:r['actual_grid']=grid(r['actual'])
  i=ident(r);assert i in members
  if k in needed:assert i not in controls[k];controls[k][i]=r
  if k in wanted:
   group=wanted[k];candidates.append((group,r))
   if p['mode']=='defense':old=dict(r,procedure_id=raw['control_procedure_id'],prediction=float(raw['control_prediction']),fallback=raw['control_fallback']);direct[group,r['target'],'same_leaf_control'][i]=old
 for source in p['prediction_sources']:
  path=private/source['private_member']
  if source['format']=='csv':
   with gzip.open(path,'rt',newline='')as f:
    for raw in csv.DictReader(f):admit(raw,source['kind'])
  else:
   for raw in packet(path):admit(raw,source['kind'])
 refs={}
 for s in p['reference_specs']:refs[s['group'],s['target'],s['reference']]=controls[key(s)]
 refs.update(direct);groups=defaultdict(list);seen=set()
 for group,r in candidates:
  i=ident(r);assert(group,i)not in seen;seen.add((group,i));others=[v[i]for(g,t,_),v in refs.items()if(g,t)==(group,r['target'])];assert others and all((x['actual'],x['position'])==(r['actual'],r['position'])for x in others);views=['full_system','own_learned_only'if r['fallback']=='none'else'fallback_only']
  if r['fallback']=='none'and r['actual']is not None and r['prediction']is not None and all(x['fallback']=='none'and x['prediction']is not None for x in others):views.append('selected_candidate_and_controls_common_learned_overlap')
  for cohort in members[i]['cohorts']:
   for view in views:groups[group,r['target'],r['population'],cohort,view].append(r)
 scores=json.loads((public/'SCORES.json').read_text());assert len(groups)==len(scores)==run['score_views'];byrecord={};examples=[]
 for s in scores:
  rs=groups[tuple(s[k]for k in('recipe_group','target','population','cohort_id','fallback_view'))];byrecord[s['record_id']]=rs;stat=Stats()
  for r in rs:stat.add(r)
  expected=stat.result(s['target']);expected['fallback_source_counts'].pop('none',None)
  for field,value in expected.items():
   if field not in s:continue
   if isinstance(value,(dict,list)):assert s[field]==value
   else:close(s[field],value)
   c['independent_all_compact_native_precision_coverage_fields']+=1
  good=[r for r in rs if r['actual']is not None and r['prediction']is not None];assert s['cohort_membership_sha256']==hashlib.sha256(canonical(sorted(ident(r)for r in rs))).hexdigest()and s['scored_membership_sha256']==hashlib.sha256(canonical(sorted(ident(r)for r in good))).hexdigest();c['full_mask_membership_hashes']+=2
 pairs=json.loads((public/'PAIRED_COMPARISONS.json').read_text());assert pairs['source_score_sha256']==sha(public/'SCORES.json')
 for comp in pairs['rows']:
  rs=byrecord[comp['source_record_id']];s=next(s for s in scores if s['record_id']==comp['source_record_id']);other=refs[s['recipe_group'],s['target'],comp['reference_view']];good=[(r,other[ident(r)])for r in rs if r['actual']is not None and r['prediction']is not None and other[ident(r)]['prediction']is not None]
  if not good:assert comp['status']=='UNESTABLISHED';continue
  n=len(good);fn=lambda r:(r['prediction']-r['actual'])**2 if s['target']=='anytime_td'else abs(r['prediction']-r['actual']);a=[fn(r)for r,_ in good];b=[fn(r)for _,r in good];ae=math.fsum(a)/n;be=math.fsum(b)/n;delta=math.fsum(x-y for x,y in zip(a,b))/n;close(comp['candidate_error'],ae);close(comp['comparator_error'],be);close(comp['absolute_error_delta'],ae-be);close(comp['relative_error_delta'],(ae-be)/be if be else None);assert comp['paired_n']==n and comp['membership_sha256']==hashlib.sha256(canonical(sorted(ident(r)for r,_ in good))).hexdigest();weeks=defaultdict(list);games=defaultdict(list)
  for (r,_),x,y in zip(good,a,b):weeks[r['week']].append(x-y);games[r['game_id']].append(x-y)
  u=comp['uncertainty'];close(u['delta'],delta);assert u['week_clusters']==len(weeks)and u['game_clusters']==len(games)
  for w,d in weeks.items():close(u['weekly_paired_sums_counts'][str(w)]['loss_difference_sum'],math.fsum(d));assert u['weekly_paired_sums_counts'][str(w)]['n']==len(d)
  if len(weeks)>=8:
   ws=sorted(weeks);sums=[math.fsum(weeks[w])for w in ws];counts=[len(weeks[w])for w in ws];rng=np.random.Generator(np.random.PCG64(1703));draws=[]
   for ix in rng.integers(0,len(ws),size=(500,len(ws))):draws.append(math.fsum(sums[int(i)]for i in ix)/sum(counts[int(i)]for i in ix))
   draws.sort();q=lambda p:(lambda x:draws[math.floor(x)]+(draws[math.ceil(x)]-draws[math.floor(x)])*(x-math.floor(x)))(499*p)
   for x,y in zip(u['week_interval'],(q(.025),q(.975))):close(x,y)
   c['independent_500_draw_wholeweek_intervals']+=1
  else:assert u['week_interval']is None and u['week_interval_status']=='INSUFFICIENT_WEEK_CLUSTERS';c['honest_insufficient_week_flags']+=1
  if len(games)>=8:se=math.sqrt(len(games)/(len(games)-1)*math.fsum((math.fsum(ds)-delta*len(ds))**2 for ds in games.values()))/n;close(u['game_cluster_sensitivity_se'],se);c['independent_game_influence_SEs']+=1
  c['all_compact_exact_paired_native_losses_memberships']+=1
  if s['population']=='primary'and s['cohort_id']=='top10':
   direction='win'if delta<0 else'loss'if delta>0 else'tie'
   if direction not in{x['direction']for x in examples}:examples.append(dict(direction=direction,record_id=s['record_id'],target=s['target'],cohort='top10',reference=comp['reference_view'],n=n,candidate_error=ae,comparator_error=be,delta=delta))
 return dict(state='PASS_FULL_COMPACT_SOURCE_MASK_POINT_PRECISION_PAIRING_AND_BLOCK_UNCERTAINTY_REPLAY',mode=p['mode'],season=p['evaluation_season'],protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),source_score_sha256=sha(public/'SCORES.json'),source_pair_sha256=sha(public/'PAIRED_COMPARISONS.json'),score_views=len(scores),pair_views=len(pairs['rows']),candidate_retained_views=len(candidates),checks=dict(c),representative_win_loss=examples,scope='Allcompactnativepoint/cohort/full-own-sharedlearnedmasksandpaireduncertainty. Correctedempiricalproductaliases; actualselectedcandidate+registeredcontrols overlap, NOToldall4candidatepoliciesmask. Pointonly; properlawsnotinvented. Exposedfullpanelreferencechoicesnotearlierselectionpolicy.',resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
if __name__=='__main__':
 r=verify(Path(sys.argv[1]));(HERE/(('DEFENSE'if r['mode']=='defense'else'SEASON_'+str(r['season']))+'_COMPACT_SUBGROUP_INDEPENDENT_REVIEW.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
