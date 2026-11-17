"""All carry-pair aggregate QA and one-season retained-row replay, no fits."""
import argparse,collections,csv,gzip,hashlib,json,math,resource,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
POLICIES=('H-CURRENT-COMMON','H-RECENT-COMMON','H-MULTI-COMMON','H-CURRENT-STRICT')
ROLE='v2-hgb-rush-att-qb-rb-specialization-v1';VERSION='v2-retained-carry-training-role-older-robustness-pairs-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def close(a,b):
 if a is None or b is None:assert a is b,(a,b)
 else:assert math.isclose(a,b,rel_tol=2e-9,abs_tol=2e-9),(a,b)
def q(v,p):
 s=sorted(v);i=(len(s)-1)*p;lo=int(i);return s[lo]+(s[min(lo+1,len(s)-1)]-s[lo])*(i-lo)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--companion-root',type=Path,required=True);a=parser.parse_args();start,cpu=time.monotonic(),time.process_time();pub=HERE/'carry-older-robustness-v1';protocol=json.loads((pub/'FROZEN_PROTOCOL.json').read_bytes());receipt=json.loads((pub/'RUN_RECEIPT.json').read_bytes());bindings=json.loads((pub/'PAIR_ANALYSIS_BINDINGS.json').read_bytes());checks=collections.Counter();rows=[];main_results=[]
 def guard():
  assert time.monotonic()-start<=90 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=536870912,'independent scope budget'
 assert sha(ROOT/'nfl_v2/carry_older_pairs.py')==protocol['code_sha256']==receipt['code_sha256'];assert sha(ROOT/'nfl_v2/paired_uncertainty.py')==protocol['uncertainty_helper_sha256'];assert sha(pub/'FROZEN_PROTOCOL.json')==receipt['protocol_sha256'];assert receipt['state']=='COMPLETE'and receipt['remaining_seasons']==[]and receipt['failures']==[]
 for binding in bindings['files']:assert sha(pub/binding['artifact_id'])==binding['sha256']and(pub/binding['artifact_id']).stat().st_size==binding['bytes']
 for year in(2025,2024,2023,2022):rows+=json.loads((pub/f'PAIR_ANALYSIS_{year}.json').read_bytes())['rows']
 assert len(rows)==1608==receipt['pair_views'];seen=set();groups=collections.defaultdict(dict);cis=0
 for r in rows:
  guard();dims=r['population'],r['cohort_id'],r['position'],r['fallback_view'];identity='CARRY-OLDER-'+hashlib.sha256(canon([VERSION,r['season'],r['policy_id'],dims,r['comparison']])).hexdigest()[:24];assert identity==r['pair_id']and identity not in seen;seen.add(identity);groups[r['season'],r['policy_id'],dims][r['comparison']]=r
  u=r['uncertainty'];n=r['paired_n'];assert u['n']==n and r['query_rows']==n+r['unresolved_rows']and r['game_count']==u['game_clusters']and r['week_count']==u['week_clusters'];cm,bm=r['candidate_metrics'],r['comparator_metrics'];assert cm['n']==bm['n']==cm['query_rows']==bm['query_rows']==n
  for m in(cm,bm):
   if n:
    assert m['scored_fallback_rows']+m['learned_rows']==n;close(m['fallback_loss_sum']+m['learned_loss_sum'],m['mae']*n);close(m['fallback_full_error_contribution'],m['fallback_loss_sum']/n);close(m['rmse'],math.sqrt(m['mse']))
   else:assert m['mae']is None and m['mse']is None
  close(cm['mae'],u.get('candidate_error'));close(bm['mae'],u.get('comparator_error'));close(r['native_error_delta'],u['delta']);close(r['relative_error_delta'],u['relative_error_change'])
  weekly=sorted((int(k),v)for k,v in u.get('weekly_paired_sums_counts',{}).items());assert sum(v['n']for _,v in weekly)==n
  if n:
   close(cm['mae']-bm['mae'],u['delta']);close(math.fsum(v['loss_difference_sum']for _,v in weekly)/n,u['delta']);close(r['relative_error_delta'],u['delta']/bm['mae']if bm['mae']else None)
  if len(weekly)>=8:
   sums=np.asarray([v['loss_difference_sum']for _,v in weekly]);ns=np.asarray([v['n']for _,v in weekly]);draw=np.random.Generator(np.random.PCG64(1703)).integers(0,len(weekly),size=(500,len(weekly)));samples=sums[draw].sum(axis=1)/ns[draw].sum(axis=1);close(q(samples,.025),u['week_interval'][0]);close(q(samples,.975),u['week_interval'][1]);cis+=1
  else:assert u['week_interval']is None
  if r['population']=='primary'and r['cohort_id']=='all'and r['position']=='ALL'and r['policy_id']=='H-MULTI-COMMON'and r['fallback_view']=='full_system':main_results.append(dict(season=r['season'],comparison=r['comparison'],n=n,candidate_mae=cm['mae'],control_mae=bm['mae'],delta=u['delta'],week_interval=u['week_interval']))
  checks['all_aggregate_id_delta_fallback_uncertainty_rows']+=1
 for refs in groups.values():
  assert len(refs)==2;left,right=refs.values()
  for k in('query_rows','paired_n','query_membership_sha256','paired_membership_sha256','candidate_metrics'):assert left[k]==right[k]
  checks['shared_three_model_masks_and_candidate_metrics_across_controls']+=1
 # Independent strongest-choice readback uses each season's full-source points.
 for frozen in protocol['seasons']:
  year=frozen['season'];folder={2025:'season-2025-v1',2024:'season-2024-v2',2023:'season-2023-complete-replay-v1',2022:'season-2022-v2'}[year];scores=json.loads((ROOT/f'reports/continuation-20261030c/{folder}/SCORES.json').read_bytes())
  if year==2025:scores=[r for r in scores if not r['procedure_id'].startswith(ROLE)]+json.loads((ROOT/'reports/continuation-20261030c/season-2025-continuity-repair-v1/SCORES.json').read_bytes())
  pool=[r for r in scores if r['target']=='rush_att'and r['week']=='ALL'and r['position']=='ALL'and r['fallback_view']=='ALL'and r['population']=='primary'and not r['procedure_id'].startswith(ROLE)and r.get('mae')is not None];n=max(r['n']for r in pool);best=min((r for r in pool if r['n']==n),key=lambda r:(r['mae'],r['procedure_id'],r['history_regime'],r['product_id']));strong=frozen['strongest_reference'];assert all(best[k]==strong[k]for k in('procedure_id','history_regime','product_id'));close(best['mae'],strong['observed_full_primary_mae']);assert n==strong['observed_full_primary_n'];checks['frozen_global_strongest_reference_choices']+=1
 del scores,pool
 frozen=next(r for r in protocol['seasons']if r['season']==2025);files={'flat':a.companion_root/'seasonal-rolling-2025-v1/predictions.csv.gz','role_overlay':a.companion_root/'seasonal-rolling-2025-continuity-repair-v1/CORRECTED_PREDICTIONS.csv.gz','memberships':a.companion_root/'shared-season-cohort-memberships-v1/memberships-2025.json.gz'}
 for kind,path in files.items():assert sha(path)==frozen['files'][kind]['sha256']
 members={tuple(r['key']):r for r in json.loads(gzip.decompress(files['memberships'].read_bytes()))if r['key'][2]=='rush_att'};index=collections.defaultdict(dict);raw_count=0
 def pspec(policy,candidate):
  strict=policy.endswith('STRICT');arm='H-CURRENT'if policy.startswith('H-CURRENT')else'H-RECENT'if policy.startswith('H-RECENT')else'H-MULTI'
  return((ROLE+(':'+('strict-current-feature-memory'if strict else'common-feature-memory')),arm,'absolute_loss_point')if candidate else('hgb-direct-history-controls-v1:absolute_error_point:'+('strict-current-inputs'if strict else'common-feature-memory'),arm,'absolute_error_point'))
 leader=tuple(frozen['strongest_reference'][k]for k in('procedure_id','history_regime','product_id'));want={pspec(p,c)for p in POLICIES for c in(True,False)}|{leader}
 for kind in('flat','role_overlay'):
  with gzip.open(files[kind],'rt',newline='')as f:
   reader=csv.reader(f);header=next(reader);ix={k:header.index(k)for k in('game_id','player_id','target','population','position','procedure_id','history_regime','product_id','prediction','actual','week','fallback','season')}
   for raw in reader:
    raw_count+=1
    if raw_count%16384==0:guard()
    if raw[ix['target']]!='rush_att'or raw[ix['season']]!='2025':continue
    proc=raw[ix['procedure_id']]
    if kind=='flat'and proc.startswith(ROLE):continue
    spec=(proc,raw[ix['history_regime']],raw[ix['product_id']])
    if spec not in want:continue
    key=tuple(raw[ix[k]]for k in('game_id','player_id','target','population'));assert key not in index[spec];pred,actual=raw[ix['prediction']],raw[ix['actual']];index[spec][key]=(float(pred)if pred else None,float(actual)if actual else None,int(raw[ix['week']]),raw[ix['position']],raw[ix['fallback']])
 raw_checks=0
 for r in rows:
  if r['season']!=2025:continue
  ca=index[pspec(r['policy_id'],True)];orig=index[pspec(r['policy_id'],False)];lead=index[leader];assert set(ca)==set(orig)==set(lead)==set(members);cb=orig if r['comparison']=='same_policy_original_broad_HGB_L1'else lead;keys=[];pairs=[]
  for key,x in ca.items():
   y,z=orig[key],lead[key];assert x[1:4]==y[1:4]==z[1:4]
   if key[3]!=r['population']or r['cohort_id']not in members[key]['cohorts']or r['position']!='ALL'and x[3]!=r['position']:continue
   learned=x[4]=='none';common=all(v[4]=='none'and v[0]is not None and v[1]is not None for v in(x,y,z));anyfb=any(v[4]!='none'for v in(x,y,z));include={'full_system':True,'own_learned_only':learned,'candidate_fallback_only':not learned,'all_three_common_learned':common,'any_model_fallback':anyfb}[r['fallback_view']]
   if not include:continue
   keys.append(key);b=cb[key]
   if x[0]is not None and b[0]is not None and x[1]is not None:pairs.append((key,x,b))
  assert len(keys)==r['query_rows']and len(pairs)==r['paired_n'];assert hashlib.sha256(canon(sorted(keys))).hexdigest()==r['query_membership_sha256'];assert hashlib.sha256(canon(sorted(v[0]for v in pairs))).hexdigest()==r['paired_membership_sha256']
  if pairs:
   delta=0
   for which,keyname in((1,'candidate_metrics'),(2,'comparator_metrics')):
    errors=[v[which][0]-v[which][1]for v in pairs];ab=sorted(abs(x)for x in errors);n=len(ab);m=r[keyname];close(m['mae'],math.fsum(ab)/n);close(m['mse'],math.fsum(x*x for x in errors)/n);close(m['bias'],math.fsum(errors)/n);close(m['p90_abs'],q(ab,.9));close(m['p95_abs'],q(ab,.95));close(m['max_abs'],ab[-1]);raw_checks+=6
   la=[abs(v[1][0]-v[1][1])for v in pairs];lb=[abs(v[2][0]-v[2][1])for v in pairs];delta=math.fsum(x-y for x,y in zip(la,lb))/len(pairs);games=collections.defaultdict(list)
   for (key,_,_),x,y in zip(pairs,la,lb):games[key[0]].append(x-y-delta)
   if len(games)>=8:close(r['uncertainty']['game_cluster_sensitivity_se'],math.sqrt(len(games)/(len(games)-1)*math.fsum(math.fsum(v)**2 for v in games.values()))/len(pairs))
  checks['raw_2025_pair_masks_native_metrics_and_gameSE']+=1
 result=dict(state='PASS_ALL_CARRY_AGGREGATES_AND_FULL_2025_CARRY_SUBSET_REPLAY',protocol_sha256=sha(pub/'FROZEN_PROTOCOL.json'),bindings_sha256=sha(pub/'PAIR_ANALYSIS_BINDINGS.json'),pair_views=1608,new_univariate_forecast_score_views=0,whole_week_bootstrap_intervals_independently_recomputed=cis,raw_2025_source_rows_streamed=raw_count,raw_2025_native_metric_fields=raw_checks,main_multi_history_results=main_results,checks=dict(checks),limitations='All paired aggregate algebra, identities, shared masks and weekly CI checked. Raw replay covers2025carryonly, with entirecorrectedRAoverlay; other3years nativeerrors were independentlyreviewed earlier, not broadlyreplayedhere. All strongest same-season choices are exposedfull-primary benchmarks heldfixed acrosssubgroups, not earlierselectors. Extended andstrict policies retainseparate scopes;2022RECENT2021gap remains. No new2026comparison orWeek8outcomes.',new_fits=0,inference_calls=0,new_forecasts=0,current2026_week8_outcomes_read=0,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
 (HERE/'CARRY_OLDER_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
