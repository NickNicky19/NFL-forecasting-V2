"""Independent source-window and feature audit; no fitting or inference."""
import argparse,bisect,collections,hashlib,json,math,resource,sys,time
from functools import lru_cache
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'reports/continuation-20261030c'))
from check_season_scores_independent import load_truth,sha
from check_defense_features_independent import Prefixes,attach,epoch,canonical,POSITIONS,CHART
from nfl_v2.qualified_defense import RAW_COLUMNS,RATE_COLUMNS
from nfl_v2 import scheduled_defense as actual

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--companion-root',type=Path,required=True);a=p.parse_args()
 start,cpu=time.monotonic(),time.process_time();oldpub=ROOT/'reports/continuation-20261030c/qualified-defense-information-v1';pub=HERE/'scheduled-defense-window-v1'
 protocol=json.loads((pub/'FROZEN_PROTOCOL.json').read_bytes());receipt=json.loads((pub/'AUDIT_RECEIPT.json').read_bytes());old=json.loads((oldpub/'FROZEN_PROTOCOL.json').read_bytes())
 assert sha(pub/'FROZEN_PROTOCOL.json')==receipt['protocol_sha256']
 for name,digest in protocol['helper_sha256'].items():assert sha(ROOT/'nfl_v2'/name)==digest
 rows,lookup,games=load_truth(a.source_root,old,2026);attach(rows,a.source_root);prefix=Prefixes(rows)
 schedule=collections.defaultdict(list);slot_by_id={}
 for gid,g in games.items():
  slot=dict(game_id=gid,season=g['year'],kickoff=g['kickoff'],available=g['kickoff']+604800)
  slot_by_id[gid]=slot
  for team in(g['home'],g['away']):schedule[team].append(slot)
 for gs in schedule.values():gs.sort(key=lambda x:(x['available'],x['kickoff'],x['game_id']))
 times={k:[g['available']for g in gs]for k,gs in schedule.items()}
 @lru_cache(None)
 def windows(defense,position,target,cutoff,floor):
  gs=prefix.observed.get((defense,position,target),[]);ot=prefix.otimes.get((defense,position,target),[])
  observed=[g for g in gs[:bisect.bisect_left(ot,cutoff)]if g['season']>=floor][-4:]
  scheduled=[g for g in schedule.get(defense,[])[:bisect.bisect_left(times.get(defense,[]),cutoff)]if g['season']>=floor][-4:]
  return observed,scheduled
 independent_observations={(d,pos,t,g['game_id']):g for(d,pos,t),gs in prefix.observed.items()for g in gs}
 # The independent reader retains Decimal workload primitives. The production
 # adapter's public contract consumes native floats; bridge representation only.
 adapter_rows=[dict(r,workload={k:float(v)if v is not None else None for k,v in r['workload'].items()})for r in rows]
 consumed=actual.build_history(adapter_rows,{gid:dict(g,season=g['year'])for gid,g in games.items()},old['targets'])
 math_checks=0
 def change(defense,pos,target,cutoff,floor):
  nonlocal math_checks
  observed,scheduled=windows(defense,pos,target,cutoff,floor);oi=[g['game_id']for g in observed];si=[g['game_id']for g in scheduled]
  local=[independent_observations[(defense,pos,target,g['game_id'])]for g in scheduled if(defense,pos,target,g['game_id'])in independent_observations]
  absent=len(scheduled)-len(local)
  if oi==si:return dict(window_changed=False,changed_columns=[],absent_slots=absent)
  ov,audit=prefix.defense(defense,pos,target,cutoff,floor);totals=[g['total']for g in local if g['total']is not None];rate=[g for g in local if g['n']is not None]
  n=math.fsum(g['n']for g in rate);y=math.fsum(g['y']for g in rate);r0=audit['league_rate'];shrunk=(20*r0+y)/(20+n)if r0 is not None else None
  nv=[math.fsum(totals)/len(totals)if totals else None,len(totals),sum(g['rows']for g in local),sum(g['known']for g in local),shrunk,shrunk-r0 if shrunk is not None else None,n,len(rate),(cutoff-scheduled[-1]['kickoff'])/86400 if scheduled else None]
  got,ga=consumed.at(defense,pos,target,cutoff,feature_floor=floor)
  assert ga['local_game_ids']==si and ga['absent_group_slots']==absent
  if r0 is None:assert ga['league_rate']is None
  else:assert ga['league_rate']is not None and math.isclose(ga['league_rate'],r0,rel_tol=1e-12,abs_tol=1e-10),('league discrepancy',defense,pos,target,floor,cutoff,ga['league_rate'],r0)
  for col,want in zip(RATE_COLUMNS,nv):
   if want is None:assert got[col]is None
   else:assert math.isclose(got[col],want,rel_tol=1e-12,abs_tol=1e-10)
   math_checks+=1
  assert all(g['available']<cutoff and g['season']>=floor for g in scheduled)
  return dict(window_changed=True,changed_columns=[c for c,x,y in zip(RATE_COLUMNS,ov,nv)if x!=y],absent_slots=absent)
 def agg(contexts,columns):
  z=collections.Counter()
  for x in contexts:
   z['contexts']+=1;z['window_changed']+=x['window_changed'];cols=set(x['changed_columns'])&set(columns);z['any_raw_feature_changed']+=bool(cols);z['absent_slot_contexts']+=x['absent_slots']>0
   for col in cols:z['changed_'+col]+=1
  return dict(z)
 contexts={};changed=[];source_projection=[]
 for target in old['targets']:
  roles=set(POSITIONS)if target==CHART else set(old['source_role_contract']['primary'][target])|set(old['source_role_contract']['extended'].get(target,[]))
  for floor in(2022,2026):
   rr=[]
   for r in rows:
    if r['season']<floor or r['position']not in roles or r['values'][target]is None:continue
    diff=change(r['defense'],r['position'],target,r['kickoff'],floor);rr.append(dict(r,**diff))
    if diff['changed_columns']:changed.append((target,floor,r['game_id'],r['player_id']))
   contexts[target,floor]=rr
   for season in sorted({r['season']for r in rr}):
    for group,cols in(('D1',RAW_COLUMNS),('D2',RATE_COLUMNS)):
     source_projection.append(dict(target=target,feature_floor=floor,season=season,information_group=group,**agg([r for r in rr if r['season']==season],cols)))
 assert source_projection==json.loads((pub/'SOURCE_TRAINING_FEATURE_CHANGES.json').read_bytes())
 fits=[]
 for binding in json.loads((pub/'ORIGINAL_FIT_BINDINGS.json').read_bytes()):
  path=oldpub/binding['artifact_id'];assert sha(path)==binding['sha256'];fit=json.loads(path.read_bytes());policy=old['policies'][fit['policy_id']];origin=epoch(fit.get('fit_cutoff_utc')or fit['training_label_fit_cutoff_utc']);rr=[r for r in contexts[fit['target'],fit['feature_floor']]if r['season']>=policy['fit_floor']and r['available']<origin]
  membership=hashlib.sha256(canonical([(r['game_id'],r['player_id'])for r in rr])).hexdigest();assert len(rr)==fit['training_n']and membership==fit['training_membership_sha256']
  fits.append(dict(artifact_id=binding['artifact_id'],target=fit['target'],policy_id=fit['policy_id'],history_regime=fit['history_regime'],feature_floor=fit['feature_floor'],information_group=fit['information_group'],training_membership_sha256=membership,future_reference=binding['artifact_id'].startswith('FUTURE-'),**agg(rr,RAW_COLUMNS if fit['information_group']=='D1'else RATE_COLUMNS)))
 assert fits==json.loads((pub/'ORIGINAL_FIT_TRAINING_FEATURE_CHANGES.json').read_bytes())
 queries=json.loads((a.companion_root/'qualified-defense-information-v1/frozen-queries.json').read_bytes());qp=[]
 for period,qs in(('2026_W1_W7',queries['historical']),('OLD_FUTURE_CONTEXT_ONLY',queries['week8'])):
  for floor in(2022,2026):
   for target in old['targets']:
    rr=[];blocked=0
    for q in qs:
     if q['target']!=target:continue
     if q.get('blocked_reason')or q['position']not in POSITIONS:blocked+=1;continue
     if period=='2026_W1_W7':r=lookup[q['game_id'],q['player_id']];defense,cutoff=r['defense'],r['kickoff']
     else:assert q.get('actual')is None;defense,cutoff=q['defense'],epoch(protocol['original_future_query_asof_utc'])
     rr.append(change(defense,q['position'],target,cutoff,floor))
    for group,cols in(('D1',RAW_COLUMNS),('D2',RATE_COLUMNS)):qp.append(dict(period=period,target=target,feature_floor=floor,information_group=group,blocked_contexts=blocked,**agg(rr,cols)))
 assert qp==json.loads((pub/'QUERY_FEATURE_CHANGES.json').read_bytes())
 changed.sort();assert len(changed)==385 and hashlib.sha256(canonical(changed)).hexdigest()==receipt['changed_context_membership_sha256']
 assert len(fits)==768 and sum(x.get('any_raw_feature_changed',0)>0 for x in fits)==308
 result=dict(state='PASS_INDEPENDENT_SCHEDULED_WINDOW_PREFIX_SOURCE_TRAINING_AND_QUERY_AUDIT',protocol_sha256=sha(pub/'FROZEN_PROTOCOL.json'),producer_audit_receipt_sha256=sha(pub/'AUDIT_RECEIPT.json'),unique_scheduled_games=len(games),independently_rebuilt_source_target_floor_contexts=sum(len(x)for x in contexts.values()),changed_source_contexts=len(changed),original_training_receipts_exact=768,training_receipts_with_changed_features=308,independently_recomputed_feature_fields=math_checks,source_projection_rows=len(source_projection),query_projection_rows=len(qp),historical_common_query_changes=sum(x.get('any_raw_feature_changed',0)for x in qp if x['period']=='2026_W1_W7'and x['feature_floor']==2022 and x['information_group']=='D2'),strict_or_oldfuture_query_changes=sum(x.get('any_raw_feature_changed',0)for x in qp if(x['period']!='2026_W1_W7'or x['feature_floor']==2026)and x['information_group']=='D2'),limitations='Feature audit only. Source truth/qualified partial chart contract reused from independently reviewed snapshot. Registered1194scheduled games omit canceledBUF-CIN; no full cancellation census. No claim of error improvement or capture. NFL fit admission remains blocked by durable storage capacity.',new_fits=0,inference_calls=0,new_forecasts=0,current2026_week8_outcomes_read=0,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
 (HERE/'SCHEDULED_WINDOW_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
