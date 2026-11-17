"""Compare retained grades only. No grader, inference, selector or NFL fit."""
import argparse,collections,gzip,hashlib,json,math,sys
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def key(r):return tuple(str(r[k])if k=='line'else r[k]for k in('game_id','player_id','target','line','source_head','source_server_clock','decision_time','line_from'))
def digestkeys(keys):return hashlib.sha256(json.dumps(sorted(keys),separators=(',',':')).encode()).hexdigest()
def record(mid,meta,pool,keys):
 rows=[pool[k]for k in sorted(keys)if k in pool];out={}
 for side in('over','under','Combined'):
  sub=[r for r in rows if r['selected_side']in('over','under')and(side=='Combined'or r['selected_side']==side)]
  c=collections.Counter(r['statistical_state']for r in sub);n=c['WIN']+c['LOSS']
  out[side]=dict(selected=len(sub),wins=c['WIN'],losses=c['LOSS'],decided=n,hit_rate=c['WIN']/n if n else None,status_counts=dict(c))
 for f in('selected','wins','losses','decided'):assert out['Combined'][f]==out['over'][f]+out['under'][f]
 return dict(method_key=mid,procedure_id=meta.get('procedure_id'),base_procedure_id=meta.get('base_procedure_id'),
  history=meta.get('history_regime'),product=meta.get('product_id'),availability_arm=meta.get('availability_arm'),
  strategy=meta.get('strategy'),capture_version=meta.get('capture_version'),side_records=out,
  compared_keys=len(keys),available_rows=len(rows),games=len({r['game_id']for r in rows}),
  actual_player_games=len({(r['game_id'],r['player_id'])for r in rows}))
def main():
 ap=argparse.ArgumentParser()
 for k in('repo','grades','output'):ap.add_argument('--'+k,type=Path,required=True)
 a=ap.parse_args();sys.path.insert(0,str(a.repo));from nfl_v2.recommendation_holds import recommendation_hold
 dest=a.repo/'reports/audit-remediation-20261105-v1/B/independent';p=read(dest/'FROZEN_STRONG_MATCHED_CONTROL_V1.json')
 sp=a.repo/'reports/abc-championship/local-week8-final-v1/SCORES.json';assert sha(sp)==p['source_scores_sha256']and sha(a.grades)==p['retained_rows_sha256']
 scores=read(sp);combined=[s for s in scores if s.get('side')=='Combined'and s.get('cohort_id')=='ALL'and s.get('K')is None]
 meta={s['method_key']:s for s in combined if s.get('method_key')}
 abc={mid for mid,s in meta.items()if s.get('history_regime')=='H-MULTI'and s.get('product_id')=='lower_median'and s.get('base_procedure_id')in('v2-availability-abc-shadow-v1:empirical','v2-availability-abc-shadow-v1:ordered_leaf_cdf:law')}
 assert len(abc)==60
 pools=collections.defaultdict(dict);controls=collections.defaultdict(dict)
 for r in json.loads(gzip.decompress(a.grades.read_bytes()))['rows']:
  if r.get('method_key')in meta:
   mid=r['method_key'];k=key(r);assert k not in pools[mid];pools[mid][k]=r
  elif r.get('method_key')is None and r.get('panel')=='ORIGINAL_PROVIDER_T90':
   tag=(r['target'],r['strategy']);k=key(r);assert k not in controls[tag];controls[tag][k]=r
 results=[];coreall=set();eligibleall=set();matching_counts=collections.Counter()
 for target in p['target_scope']:
  mids=sorted(mid for mid in abc if meta[mid]['target']==target);assert len(mids)==6
  eligible=set(pools[mids[0]]);core={k for k,r in pools[mids[0]].items()if r['statistical_state']in('WIN','LOSS')}
  for mid in mids:
   assert set(pools[mid])==eligible
   assert {k for k,r in pools[mid].items()if r['statistical_state']in('WIN','LOSS')}==core
  coreall|=core;eligibleall|=eligible;opportunities={k:pools[mids[0]][k]for k in core}
  def qualify(mid):
   pool=pools[mid]
   present=core&set(pool)
   for k in present:assert pool[k]['actual']==opportunities[k]['actual']and pool[k]['line']==opportunities[k]['line']
   return present==core and all(pool[k]['statistical_state']in('WIN','LOSS')for k in core)
  def wins(mid):return sum(pools[mid][k]['statistical_state']=='WIN'for k in core)
  all_other=[mid for mid,s in meta.items()if s['target']==target and mid not in abc]
  held=[mid for mid in all_other if recommendation_hold(meta[mid])or any(recommendation_hold(r)for r in pools[mid].values())]
  valid=[mid for mid in all_other if mid not in held];complete=[mid for mid in valid if qualify(mid)];partial=[mid for mid in valid if mid not in complete]
  matching_counts.update(other_candidate_cells=len(all_other),held_cells=len(held),complete_cells=len(complete),partial_cells=len(partial))
  bestabc=max(wins(mid)for mid in mids);aleads=sorted(mid for mid in mids if wins(mid)==bestabc)
  best=max(wins(mid)for mid in complete)if complete else None;bleads=sorted(mid for mid in complete if wins(mid)==best)
  canonical=aleads[0];arec=record(canonical,meta[canonical],pools[canonical],core)
  aco=[record(mid,meta[mid],pools[mid],core)for mid in aleads]
  brecs=[record(mid,meta[mid],pools[mid],core)for mid in bleads]
  # Own-pool maxima retain partial coverage honestly; no completion gate applied.
  rates={mid:meta[mid]['selection_metrics']['WIN']/meta[mid]['n']for mid in valid if meta[mid]['n']}
  rawmax=max(rates.values())if rates else None;rawleaders=[dict(method_key=mid,procedure_id=meta[mid]['procedure_id'],history=meta[mid]['history_regime'],product=meta[mid]['product_id'],wins=meta[mid]['selection_metrics']['WIN'],decided=meta[mid]['n'],hit_rate=rates[mid],complete_on_current_core=mid in complete)for mid in sorted(rates)if rates[mid]==rawmax]
  refs=[]
  for (t,strategy),pool in controls.items():
   if t!=target:continue
   overlap=core&set(pool)
   for k in overlap:assert pool[k]['actual']==opportunities[k]['actual']and pool[k]['line']==opportunities[k]['line']
   rec=record('CONTROL:'+strategy,dict(procedure_id='B:CONTROL:'+strategy,strategy=strategy,product_id='recorded_side'if strategy=='original'else'saved_precision_point_direction_or_constant'),pool,core)
   rec['complete_on_core']=overlap==core and all(pool[k]['statistical_state']in('WIN','LOSS')for k in core);refs.append(rec)
  refs.sort(key=lambda r:r['method_key']);complete_refs=[r for r in refs if r['complete_on_core']]
  maxcontrol=max([best]if best is not None else[]+[r['side_records']['Combined']['wins']for r in complete_refs])if not complete_refs else max([best]if best is not None else[-1]+[r['side_records']['Combined']['wins']for r in complete_refs])
  # Explicit expression avoids mixing own-pool counts into common-core maxima.
  maxcontrol=max(([best]if best is not None else[])+[r['side_records']['Combined']['wins']for r in complete_refs])
  strong=[dict(kind='OTHER_B',**r)for r in brecs if r['side_records']['Combined']['wins']==maxcontrol]+[dict(kind='SAVED_OR_CONSTANT_CONTROL',**r)for r in complete_refs if r['side_records']['Combined']['wins']==maxcontrol]
  paired=[]
  for bmid in bleads:
   ds=[float(pools[canonical][k]['statistical_state']=='WIN')-float(pools[bmid][k]['statistical_state']=='WIN')for k in sorted(core)];delta=math.fsum(ds)/len(core)
   gs=collections.defaultdict(list)
   for k,d in zip(sorted(core),ds):gs[k[0]].append(d)
   G=len(gs);se=math.sqrt(G/(G-1)*math.fsum((math.fsum(v)-delta*len(v))**2 for v in gs.values()))/len(core)if G>=8 else None
   paired.append(dict(ABC_method_key=canonical,other_method_key=bmid,hit_rate_change=delta,win_change=bestabc-best,
       game_clusters=G,week_clusters=1,game_cluster_sensitivity_se=se,normal95_game_sensitivity=[delta-1.96*se,delta+1.96*se]if se is not None else None,
       limitation='One exposedweek, descriptive game sensitivity; not multiplicity adjusted'))
  results.append(dict(category=target,status='COMPLETE_SAME_DECIDED_CORE_DIAGNOSTIC',eligible_on_existing_common_mask=len(eligible),decided_core=len(core),
     unresolved_or_unselected_common_mask=len(eligible)-len(core),core_membership_sha256=digestkeys(core),eligible_membership_sha256=digestkeys(eligible),
     games=len({k[0]for k in core}),player_games=len({(k[0],k[1])for k in core}),
     ABC_combined_display_leader=arec,ABC_combined_co_leaders=aco,other_B_best_complete=brecs,
     saved_and_constant_controls=refs,strongest_matched_controls=strong,ABC_win_change_vs_strongest_matched_control=bestabc-maxcontrol,
     paired_ABC_vs_best_other_B=paired,other_candidate_cells=len(all_other),other_held_cells=len(held),other_complete_cells=len(complete),
     other_partial_cells=len(partial),raw_own_pool_maxima=rawleaders,
     horizon_limit='Originalearlycaptureproducts and laterprovider-labelledlines are a timing-unverified retrospective diagnostic. Matching clocks/labels is not proof of simultaneous original issuance or website-relative win.'))
 for target in('anytime_td','nick-chart-ppr-v1'):results.append(dict(category=target,status='NO_QUALIFIED_COMPATIBLE_OFFER',reason='No compatible retained actual offer in this panel; no synthetic line or probability substituted.'))
 assert len(coreall)==555 and len(eligibleall)==581
 result=dict(state='PASS_DESCRIPTIVE_STRONG_MATCHED_CONTROL_REVIEW',protocol_sha256=sha(dest/'FROZEN_STRONG_MATCHED_CONTROL_V1.json'),
   source_scores_sha256=sha(sp),retained_rows_sha256=sha(a.grades),ABC_cells=60,coverage=dict(unique_decided_offers=len(coreall),unique_eligible_common_mask_offers=len(eligibleall),
   unique_decided_player_games=len({(k[0],k[1])for k in coreall}),unique_eligible_player_games=len({(k[0],k[1])for k in eligibleall}),
   games=len({k[0]for k in coreall}),captured_games=13,schedule_games=14,forecast_output_row_views_across_six_ABC_candidates=6*len(eligibleall)),
   cell_counts=dict(matching_counts),category_results=results,
   scope='One exposedW8 only. Other B own-pool maxima preserved separately; exactmask complete maxima use identical full8fieldidentity/actual/selectedcase set. Samepanel controls do not establish website improvement, live routing,5weekactual-line qualification or pricing value.',
   new_forecasts=0,grading_calls=0,model_calls=0,NFL_fits=0,new_private_row_bytes=0)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(state=result['state'],coverage=result['coverage'],sha256=sha(a.output))))
if __name__=='__main__':main()
