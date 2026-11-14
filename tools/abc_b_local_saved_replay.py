"""Session B local continuation only; C owns the shared benchmark evaluator."""
import collections,csv,gzip,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import grade_saved_week8 as old,grade_week8_captured_library as lib
from nfl_v2 import scoring,full_provider_prop_replay as shared
from nfl_v2.shared_subgroups import packet_rows
BASE=ROOT/'reports/abc-championship'

def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 private=Path(sys.argv[1]);parent=Path(sys.argv[2]);out=BASE/'local-week8-final-v1';out.mkdir(parents=True,exist_ok=False)
 protocol=dict(version='B-ABC-SELECTION-FIRST-ADOPTION-20261103-v2.0',at_utc=old.now(),session='B',coordinator_repository='NickNicky19/NFL-forecasting-NGS-C',shared_protocol_state='NOT_LOCATED_NOT_PINNED_NO_PARITY_CLAIM',
 adopted_assignment='NFL A/B/C — COMMON ACTUAL-PROP ACCURACY CHAMPIONSHIP v2; direct user instruction November3. This is a normalized exact adoption record, not a byte-for-byte copy/hash of the chat message.',
 priorities=['Selection correctness at actual retained thresholds first; no MAE admission prerequisite','Separate point/probability/hit-rate/coverage/price scoreboards','C alone owns canonical protocol/scorer/admissions/consolidation; B writes only V2','Reuse supported original rows; no duplicate fits or schedulers; no external messaging','Preserve original/replay/reconstruction/prospective tracks and all losses/versions','All12 targets including exact inherited16componentchart and rushing-or-receiving TD; missing offers N/A','E1 2026W1-8; E2 2025W1-8; E3 2022-24W1-8; E4 full2022-25; E5 matchingW1-8pooled; E6 fullolder+currentW8; E7 equal-season same-set; E8 genuinefuture','Complete existing procedures primary, isolated ablations secondary; chronology/fit-memory distinction/startup retained','Common-board and separately frozen top6/10/20; sixleg supplementary; no hindsight routing/inversion','Side buckets selected pre-outcome; W/(W+L), weightedCombined; pushes/void/pending/missing/DNP/technical unavailability distinct','Strong matched simple/constant/earlier-only/qualifiedmarket/website controls; no probability/odds fabrication','Independent separate-path calculations, identities/clocks/labels/masks/duplicates/pooled arithmetic; representative not universal proof','Existing private A/B recovery and C GitHub-only rule protected; no restricted public rows/locators or new shared private archive','Existing provisional/scientific/production policies separate; no new universal wait or unilateral release'],
 local_execution=dict(scope='Finish previously pending Week8 saved rows and recompute new common offered mask with unchanged procedures; all previously exposed research.',source_quality_choice='Existing frozen661provider-labelled ordinary thresholds, no favorable source/version selection; original retained Nov1Monday source fixed, not newly authenticated final-latestT90.',resource=dict(new_fits=0,new_inference=0,max_private_bytes=8388608),label_version='NFLVERSE_CURRENT_REVISION_20261103_PLUS_ESPN_FINAL',primary_scope='LOCAL_ONLY_NOT_COMMON_ABC',new_policy=False))
 save(BASE/'ADOPTED_ASSIGNMENT_V2.json',protocol)
 save(out/'FROZEN_LOCAL_PROTOCOL.json',dict(adoption_sha256=digest(BASE/'ADOPTED_ASSIGNMENT_V2.json'),at_utc=old.now(),before_new_scores=True,code_sha256=digest(Path(__file__)),source_receipts=json.loads((private/'ACQUISITION.json').read_bytes()),new_fits=0,new_inference=0))
 labels=old.Labels(parent);games={r['game_id']:r for r in csv.DictReader((private/'source-labels/games.csv').open())if(r['season'],r['game_type'],r['week'])==('2026','REG','8')};events={e['id']:e for e in json.loads((private/'source-labels/espn.json').read_bytes())['events']}
 assert set(games)==set(labels.games)
 for gid,g in games.items():
  e=events[g['espn']];assert e['status']['type']['completed'] and e['status']['type']['state']=='post';scores={x['homeAway']:float(x['score'])for x in e['competitions'][0]['competitors']};assert scores=={'home':float(g['home_score']),'away':float(g['away_score'])}
 labels.games=games;labels.status={g:'FINAL'for g in games};labels.stats={}
 for r in csv.DictReader((private/'source-labels/stats.csv').open()):
  if(r['season'],r['week'],r['season_type'])!=('2026','8','REG'):continue
  g=games[r['game_id']];assert {r['team'],r['opponent_team']}=={g['home_team'],g['away_team']};k=r['game_id'],r['player_id'];assert k not in labels.stats;labels.stats[k]=r
 def refresh(r):
  assert r['target']in old.ORDINARY
  q=dict(r);q.update(labels.label(r['game_id'],r['player_id'],r['target']));return q
 original=[refresh(r)for r in packet_rows(parent/'ORIGINAL_JOINED_ROWS_V1.json.gz')if r['panel']=='ORIGINAL_PROVIDER_T90'];grades=shared.grade(original);scores=[]
 for strategy in shared.STRATEGIES:
  rr=[r for r in grades if r['strategy']==strategy];scores+=old.aggregate(rr,panel='B_LOCAL_W8_FIXED_ORIGINAL_SOURCE_FINAL_LABELS_V2',method='B:WEBSITE:'+strategy,track='A_ORIGINAL'if strategy=='original'else'B_REPLAY',strategy=strategy,pool=rr)
 metadata={r['method_key']:r for r in old.read(ROOT/'reports/week8-grading-20261102l/comparable-products-v3/SCORES.json')};by=collections.defaultdict(list)
 for r in packet_rows(parent/'CAPTURED_LIBRARY_P1_ROWS_V1.json.gz'):
  if r['method_key']in metadata:by[r['method_key']].append(r)
 masks={}
 for target in old.ORDINARY:
  sets=[{lib.key(r)for r in rr}for mid,rr in by.items()if metadata[mid]['target']==target];masks[target]=set.intersection(*sets)
 for mid,rr in by.items():
  m=metadata[mid];pool=[refresh(r)for r in rr if lib.key(r)in masks[m['target']]];gg=shared.grade(pool,strategies=(shared.ADJUSTED,));ss=old.aggregate(gg,panel='B_LOCAL_W8_ALL_REGISTERED_ISSUED_COMMON_OFFERS_V2',method='B:'+m['procedure_id']+':'+mid,track='B_REPLAY',strategy='P1',pool=gg)
  for s in ss:
   if s['target']!=m['target']:continue
   s.update(method_key=mid,base_procedure_id=m['procedure_id'],history_regime=m['history_regime'],product_id=m['product_id'],capture_version=m['capture_version'],availability_arm=m.get('availability_arm'),information_policy=m['information_policy']);scores.append(s)
  grades.extend(gg)
 for strategy in shared.STRATEGIES:
  rr=[r for r in grades if r.get('panel')=='ORIGINAL_PROVIDER_T90'and r['strategy']==strategy and lib.key(r)in masks.get(r['target'],set())]
  # grades also contains candidate copies of original offers; use original rows only.
  rr=[r for r in shared.grade(original,strategies=(strategy,))if lib.key(r)in masks.get(r['target'],set())]
  scores+=old.aggregate(rr,panel='B_LOCAL_W8_COMMON_OFFER_CONTROLS_V2',method='B:CONTROL:'+strategy,track='A_ORIGINAL'if strategy=='original'else'B_REPLAY',strategy=strategy,pool=rr)
 for s in scores:
  s['record_id']='ABC-B-LOCAL-'+hashlib.sha256((s['record_id']+s['procedure_id']).encode()).hexdigest()[:24];s.update(whole_week_complete=True,shared_benchmark_status='LOCAL_NOT_C_ADMITTED',grading_version='B-LOCAL-20261103-v2',outcome_version='NFLVERSE_20261103',source_vintage='ORIGINAL_PREGAME_OUTPUTS;CURRENT_REVISED_FINAL_LABELS;QUOTE_UPDATE_TIME_UNVERIFIED')
 save(out/'SCORES.json',scores);wide=old.wide(scores);save(out/'SIDE_TABLE.json',wide);old.write_csv(out/'SIDE_TABLE.csv',wide)
 old.savegz(private/'LOCAL_GRADED_ROWS.json.gz',dict(rows=grades));assert(private/'LOCAL_GRADED_ROWS.json.gz').stat().st_size<8388608
 save(out/'RUN_RECEIPT.json',dict(state='LOCAL_MATCHED_FINAL_WEEK8_NOT_ABC_PARITY',at_utc=old.now(),final_games=14,pending_games=0,outer_offers=len(original),common_offer_counts={k:len(v)for k,v in masks.items()},score_views=len(scores),private_sha256=digest(private/'LOCAL_GRADED_ROWS.json.gz'),private_retention='LOCAL_READBACK_OFFHOST_PENDING_EXISTING_APPROVED_ROUTE_ONLY',new_fits=0,new_inference=0,new_forecasts=0))
 print(json.dumps(dict(final_games=14,score_views=len(scores),original=[r for r in wide if r['panel']=='B_LOCAL_W8_FIXED_ORIGINAL_SOURCE_FINAL_LABELS_V2'and r['strategy']=='original'])))

if __name__=='__main__':main()
