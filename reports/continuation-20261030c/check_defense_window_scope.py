"""Metadata-only calendar-window discrepancy census; no corrected predictions."""
import bisect,json,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'reports/continuation-20261030c';sys.path.insert(0,str(HERE))
from review_paths import companion_root,source_root
from check_season_scores_independent import load_truth,sha
from check_defense_features_independent import attach,epoch,POSITIONS,CHART
def run():
 pub=HERE/'qualified-defense-information-v1';private=companion_root()/'qualified-defense-information-v1';p=json.loads((pub/'FROZEN_PROTOCOL.json').read_text());rows,lookup,games=load_truth(source_root(),p,2026);attach(rows,source_root());calendar=defaultdict(list);observed=defaultdict(list);seen=set()
 for game,g in games.items():
  for defense in(g['home'],g['away']):
   for pos in POSITIONS:calendar[defense,pos].append((g['kickoff']+604800,g['kickoff'],game,g['year']))
 for r in rows:
  key=r['game_id'],r['defense'],r['position']
  if key in seen:continue
  seen.add(key);observed[r['defense'],r['position']].append((r['available'],r['kickoff'],r['game_id'],r['season']))
 for groups in(calendar,observed):
  for gs in groups.values():gs.sort()
 cache={}
 def context(defense,pos,cutoff,floor):
  key=defense,pos,cutoff,floor
  if key not in cache:
   variants=[]
   for groups in(calendar,observed):variants.append([g[2]for g in groups[defense,pos]if g[0]<cutoff and g[3]>=floor][-4:])
   cache[key]=variants
  return cache[key]
 affected={};counts=Counter();examples=[]
 for floor in(2022,2026):
  for r in rows:
   a,b=context(r['defense'],r['position'],r['kickoff'],floor)
   if a!=b:affected[floor,r['game_id'],r['player_id']]=True;counts[str(r['season'])]+=1
 results=[];unique=defaultdict(set)
 for ff in sorted(pub.glob('*-FIT.json')):
  fit=json.loads(ff.read_text());target=fit['target'];policy=fit['policy_id'];floor=fit['feature_floor'];origin=epoch(fit.get('fit_cutoff_utc',fit.get('training_label_fit_cutoff_utc')));roles=set(POSITIONS)if target==CHART else set(p['source_role_contract']['primary'][target])|set(p['source_role_contract']['extended'].get(target,[]));rs=[r for r in rows if r['position']in roles and r['season']>=p['policies'][policy]['fit_floor']and r['available']<origin and r['values'][target]is not None and(floor,r['game_id'],r['player_id'])in affected]
  if rs:
   results.append(dict(fit_receipt=ff.name,target=target,policy_id=policy,information_group=fit['information_group'],affected_training_rows=len(rs),training_n=fit['training_n']))
   for r in rs:unique[target,policy].add((r['game_id'],r['player_id']))
 queries=json.loads((private/'frozen-queries.json').read_text())['historical'];qcounts=Counter()
 for q in queries:
  r=lookup[q['game_id'],q['player_id']]
  for floor in(2022,2026):
   a,b=context(r['defense'],r['position'],r['kickoff'],floor)
   if a!=b:
    qcounts[q['target'],floor]+=1
    if not examples:examples.append(dict(query_game_id=r['game_id'],position=r['position'],defense=r['defense'],feature_floor=floor,scheduled_last4=a,actual_observed_last4=b,description='Redactedgroup-windowexample; no playeridentity, label, forecast or proposedcorrectedscorepublished.'))
 return dict(state='CONFIRMED_OBSERVED_GROUP_WINDOW_SCOPE_ADDENDUM',protocol_sha256=sha(pub/'FROZEN_PROTOCOL.json'),source_finding_sha256=sha(HERE/'DEFENSE_ABSENT_POSITION_WINDOW_FINDING.json'),affected_source_contexts_by_season=dict(counts),affected_fit_receipts=len(results),affected_training_membership_rows_by_target_policy=[dict(target=k[0],policy_id=k[1],unique_player_games=len(v))for k,v in sorted(unique.items())],affected_fit_cell_counts=results,affected_historical_query_windows=[dict(target=k[0],feature_floor=k[1],n=v)for k,v in sorted(qcounts.items())],redacted_example=examples,interpretation='Onlywindowmembership discrepancy; somechangedwindowscanproduceidenticalnumericfeatures. Frozenv1methodlast4observedqualified-positiongroups. Calendarunknownpaddingrequiresnewregisteredmechanism; no correctedforecastsorfitsemitted.',new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
if __name__=='__main__':
 r=run();(HERE/'DEFENSE_WINDOW_SCOPE_ADDENDUM.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='affected_fit_cell_counts'}))
