"""Independent arithmetic on existing final grades; no grader/model invocation."""
import argparse,collections,gzip,hashlib,json,math,sys
from pathlib import Path
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
def equal(a,b):
 if a is None or b is None:assert a is b
 else:assert math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12),(a,b)
def identity(r):return tuple(r[k]if k!='line'else str(r[k])for k in ('game_id','player_id','target','line','source_head','source_server_clock','decision_time','line_from'))
def main():
 ap=argparse.ArgumentParser()
 for k in ('repo','grades','output'):ap.add_argument('--'+k,type=Path,required=True)
 a=ap.parse_args();sys.path.insert(0,str(a.repo));base=a.repo/'reports/audit-remediation-20261105-v1/B';out=base/'availability-final-matched-v3'
 p=read(out/'FROZEN_PROTOCOL.json');sp=a.repo/p['score_source'];assert sha(sp)==p['score_source_sha256']and sha(a.grades)==p['retained_grade_source_sha256']
 scores=read(sp);old=[s for s in scores if s.get('history_regime')=='H-MULTI'and s.get('product_id')=='lower_median'and s.get('base_procedure_id')in p['unchanged_procedures']]
 assert len(old)==180;meta={s['method_key']:s for s in old if s['side']=='Combined'};assert len(meta)==60
 saved=read(out/'OWN_POLICY_RECORDS.json');assert len(saved)==60
 pools=collections.defaultdict(dict)
 for r in gz(a.grades)['rows']:
  if r.get('method_key')not in meta:continue
  mid=r['method_key'];k=identity(r);assert k not in pools[mid];pools[mid][k]=r
 checks=[];ownrows=0;unknowns=collections.Counter();side_reconciled=0
 for record in saved:
  mid=record['method_key'];rr=list(pools[mid].values());ownrows+=len(rr)
  assert record['eligible_in_common_panel']==len(rr)==meta[mid]['selection_metrics']['selection_pool_count']
  for side,q in record['side_records'].items():
   sub=[r for r in rr if r['selected_side']is not None and(side=='Combined'or r['selected_side']==side)]
   c=collections.Counter(r['statistical_state']for r in sub);wins=c['WIN'];losses=c['LOSS']
   assert q['selected']==len(sub)and q['wins']==wins and q['losses']==losses and q['decided']==wins+losses
   equal(q['hit_rate'],wins/(wins+losses)if wins+losses else None)
   assert all(q['status_counts'].get(k,0)==v for k,v in c.items())
   oldrow=next(s for s in old if s['method_key']==mid and s['side']==side)
   assert oldrow['n']==wins+losses and oldrow['selection_metrics']['WIN']==wins and oldrow['selection_metrics']['LOSS']==losses
   side_reconciled+=1
  for field in ('wins','losses','selected','decided'):assert record['side_records']['Combined'][field]==sum(record['side_records'][s][field]for s in ('over','under'))
  nr=[r for r in rr if r['actual']is not None and r['prediction']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL']
  assert len(nr)==record['numeric_n'];equal(record['mae'],math.fsum(abs(r['prediction']-r['actual'])for r in nr)/len(nr)if nr else None);equal(record['bias'],math.fsum(r['prediction']-r['actual']for r in nr)/len(nr)if nr else None)
  assert dict(collections.Counter(r.get('fallback')for r in rr))==record['fallback_counts'];unknowns.update(r.get('fallback')for r in rr)
  assert len({r['game_id']for r in rr})==record['games']
 pairs=read(out/'INDEX_BOUND_PAIRED_ANALYSIS.json');assert len(pairs)==240;empty=0;strong_controls=[]
 for q in pairs:
  cmid=next(mid for mid,s in meta.items()if s['procedure_id']==q['procedure_id']);bmid=next(mid for mid,s in meta.items()if s['procedure_id']==q['comparator_procedure_id']);ca,co=pools[cmid],pools[bmid]
  assert set(ca)==set(co)
  keys=sorted(k for k in ca if ca[k]['statistical_state']in('WIN','LOSS')and co[k]['statistical_state']in('WIN','LOSS'))
  for k in keys:assert ca[k]['actual']==co[k]['actual']and ca[k]['line']==co[k]['line']
  if q['fallback_view']=='PAIR_KNOWN_NONFALLBACK':keys=[k for k in keys if ca[k].get('fallback')==co[k].get('fallback')=='none']
  elif q['fallback_view']=='PAIR_ANY_KNOWN_FALLBACK':keys=[k for k in keys if all(r.get('fallback')not in(None,'UNKNOWN_NOT_RETAINED')for r in(ca[k],co[k]))and any(r.get('fallback')!='none'for r in(ca[k],co[k]))]
  assert len(keys)==q['n'];assert hashlib.sha256(json.dumps(keys,separators=(',',':')).encode()).hexdigest()==q['membership_sha256']
  metric=q['metric'];loss=lambda r:float(r['statistical_state']=='LOSS')if metric=='STATISTICAL_SELECTED_SIDE_LOSS_RATE'else abs(r['prediction']-r['actual'])
  av=[loss(ca[k])for k in keys];bv=[loss(co[k])for k in keys];n=len(keys)
  expected=(math.fsum(av)/n,math.fsum(bv)/n,math.fsum(x-y for x,y in zip(av,bv))/n)if n else(None,None,None)
  for v,e in zip(('candidate_error','comparator_error','delta'),expected):equal(q[v],e)
  equal(q['relative_error_change'],expected[2]/expected[1]if n and expected[1]else None)
  cw=sum(ca[k]['statistical_state']=='WIN'for k in keys);bw=sum(co[k]['statistical_state']=='WIN'for k in keys)
  over=sum(ca[k]['actual']>ca[k]['line']for k in keys);under=sum(ca[k]['actual']<ca[k]['line']for k in keys)
  assert (q['candidate_wins'],q['comparator_wins'],q['alwaysOver_wins'],q['alwaysUnder_wins'])==(cw,bw,over,under)
  u=q['uncertainty'];games={k[0]for k in keys};assert u['week_clusters']==(1 if n else 0)and u['game_clusters']==len(games)
  if n:
   assert u['week_interval']is None and u['week_interval_status']=='INSUFFICIENT_WEEK_CLUSTERS'
   delta=expected[2];grouped=collections.defaultdict(list)
   for k,x,y in zip(keys,av,bv):grouped[k[0]].append(x-y)
   se=math.sqrt(len(games)/(len(games)-1)*math.fsum((math.fsum(ds)-delta*len(ds))**2 for ds in grouped.values()))/n if len(games)>=8 else None
   equal(u['game_cluster_sensitivity_se'],se)
   if se is not None:
    for v,e in zip(u['game_normal95_sensitivity'],[delta-1.96*se,delta+1.96*se]):equal(v,e)
  else:empty+=1;assert u['status']=='NO_SUPPORTED_PAIRED_ROWS'
  if metric=='STATISTICAL_SELECTED_SIDE_LOSS_RATE'and q['fallback_view']=='FULL_SYSTEM_ON_EXISTING_COMMON_MASK':
   strong_controls.append(dict(target=q['target'],procedure_id=q['procedure_id'],contrast=q['contrast'],wins=cw,n=n,comparator_wins=bw,
      alwaysOver_wins=over,alwaysUnder_wins=under,win_change_versus_strongest_constant=cw-max(over,under)))
 # Representative saved win and loss: primitive inequalities, no grader used.
 examples=[]
 for state in ('WIN','LOSS'):
  r=min((r for pool in pools.values()for r in pool.values()if r['statistical_state']==state),key=lambda r:(r['game_id'],r['player_id'],r['target'],r['method_key']))
  win=r['actual']>r['line']if r['selected_side']=='over'else r['actual']<r['line'];assert win==(state=='WIN')
  examples.append(dict(state=state,target=r['target'],selected_side=r['selected_side'],boundary_check='PASS'))
 from nfl_v2.recommendation_holds import recommendation_hold,HGB_CARRY_HOLD
 from nfl_v2.result_index import is_championship_eligible
 reg=read(a.repo/'registries/PROCEDURE_ADMISSION_HOLDS.json');h=reg['holds'][0];hashes=h['known_fixed_model_dependencies'];assert len(hashes)==3
 for digest in hashes:
  assert recommendation_hold(dict(target='rush_att',procedure_id='dependent_snapshot',model_sha256=digest))==HGB_CARRY_HOLD
  assert recommendation_hold(dict(target='pass_yd',procedure_id='dependent_snapshot',model_sha256=digest))is None
  assert recommendation_hold(dict(target='rush_att',procedure_id='independent_repair',comparator_model_sha256=digest))is None
 assert recommendation_hold(dict(target='rush_att',procedure_id='independent_repair',model_sha256='0'*64))is None
 overlay=read(base/'hold-overlay-v2/RUN_RECEIPT.json');spec=overlay['held_record_annotations'];path=a.repo/spec['path'];blob=path.read_bytes();body=gzip.decompress(blob)
 assert sha(path)==spec['sha256']and len(blob)==spec['bytes']and hashlib.sha256(body).hexdigest()==spec['uncompressed_sha256']
 held=json.loads(body);assert len(held)==spec['records']==2675
 assert len({r['test_id']for r in held})==2675 and all(r['category']=='rush_att'and recommendation_hold(r)==HGB_CARRY_HOLD for r in held)
 assert sum(r['prior_generic_filter_passed']for r in held)==2631 and sum(not r['prior_generic_filter_passed']for r in held)==44
 assert all(r['retained_for_score_audit']and not r['recommendation_eligible']for r in held)
 qhold=read(base/'hold-overlay-v1/FIVE_WEEK_HOLD_ANNOTATIONS.json');assert len(qhold['annotations'])==142
 qs=gz(a.repo/qhold['source']);assert sha(a.repo/qhold['source'])==qhold['source_sha256'];expected={r['qualification_id']for r in qs if recommendation_hold(r)};assert expected=={r['qualification_id']for r in qhold['annotations']}
 rank=read(base/'hold-overlay-v1/LEGACY_RANKING_HOLD_STATUS.json');assert len(rank['held_raw_ranking_rows'])==1 and len(rank['held_top5_rows'])==0
 result=dict(state='PASS_INDEPENDENT_EXISTING_FINAL_AVAILABILITY_V3_AND_SCOPED_HOLDS',
   source_bindings={str(f.relative_to(a.repo)):sha(f)for f in [sp,out/'FROZEN_PROTOCOL.json',out/'OWN_POLICY_RECORDS.json',out/'INDEX_BOUND_PAIRED_ANALYSIS.json',a.repo/'nfl_v2/recommendation_holds.py',a.repo/'registries/PROCEDURE_ADMISSION_HOLDS.json']},
   retained_grade_sha256=sha(a.grades),method_category_arm_cells=60,side_records_checked=side_reconciled,paired_views_checked=len(pairs),empty_pairs_with_nulls=empty,
   own_pool_row_views=ownrows,known_fallback_values=dict(unknowns),representative_boundaries=examples,
   same_row_strongest_constant_results=strong_controls,
   hold_overlay=dict(held_views=2675,previous_generic_passes=2631,already_diagnostic_excluded=44,qualification_views=142,held_old_top5=0,
     three_fixed_model_hash_scopes_checked=True,full_603711_index_rescan_not_repeated=True,
     independent_limit='All2675retained overlay membership annotations and142qualification IDs validated; originalworker full-universe scan receipt retained, not independently rerun1.36GB.'),
   failure_receipts_preserved=[str(x.relative_to(a.repo))for x in base.rglob('FAILED*json')],
   scope='One exposed W8 only;13captured games of14, later provider-labelled thresholds with unverified timing, existing all-method common offer mask rather than661fullboard. Point/selection/probability/price products separate; no global champion, policy change, new test-week qualification or promotion.',
   model_calls=0,grading_calls=0,NFL_fits=0,new_private_row_bytes=0)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(state=result['state'],side_views=side_reconciled,paired_views=len(pairs),sha256=sha(a.output))))
if __name__=='__main__':main()
