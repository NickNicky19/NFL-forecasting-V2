"""Independent source-counter semantics and raw-verified population crosswalk.
No fitting, no recollection and no protected row export.
"""
import argparse,collections,csv,gzip,hashlib,json,time
from pathlib import Path

def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b)if str(p).endswith('.gz')else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def num(v):
 try:return float(v)
 except(ValueError,TypeError):return None

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
 for w in range(5,9):ap.add_argument('--week'+str(w),type=Path,required=True)
 a=ap.parse_args();started=time.monotonic();b=a.repo/'reports/player-context-matchup-01/B';inventory=read(b/'source-fields-v3/SOURCE_FIELD_WEEK_COVERAGE.json');author={(r['season'],r['week']):r for r in inventory['rows']if r['source']=='PBP'};counts=collections.defaultdict(collections.Counter)
 for year in range(2022,2027):
  with gzip.open(a.source_root/f'play_by_play_{year}.csv.gz','rt')as f:
   rd=csv.reader(f);ix={v:i for i,v in enumerate(next(rd))}
   for row in rd:
    if row[ix['season_type']]!='REG'or row[ix['play_type']]!='no_play':continue
    counter=counts[year,int(float(row[ix['week']]))];counter['marked_no_play']+=1
    admitted=num(row[ix['pass_attempt']])==1 and num(row[ix['sack']])==0 and num(row[ix['two_point_attempt']])==0 and num(row[ix['play_deleted']])!=1
    counter['credited_no_play_admitted']+=admitted;counter['marked_no_play_not_admitted']+=not admitted
 rows=[]
 for key,r in sorted(author.items()):
  c=counts[key];assert r['rows_excluded_no_play']==c['marked_no_play'];rows.append(dict(season=key[0],week=key[1],original_inventory_rows_excluded_no_play=r['rows_excluded_no_play'],**c))
 value=dict(state='CONFIRMED_SOURCE_COUNTER_LABEL_IS_BROADER_THAN_EXCLUSION',producer_commit='2fa855fc4dd7e9e495126dea93ba90a33fee4be3',source_inventory_sha256=sha(b/'source-fields-v3/SOURCE_FIELD_WEEK_COVERAGE.json'),
  original_field='rows_excluded_no_play',current_interpretation='All REG source rows marked play_type=no_play, including stat-credited attempts retained by the declared official-attempt mask. This field is not the count of removed records.',
  rows=rows,total_marked_no_play=sum(r['marked_no_play']for r in rows),total_credited_no_play_admitted=sum(r['credited_no_play_admitted']for r in rows),
  model_or_grade_changes=0,minimum_remedy='Source-bound metadata label qualification only; do not change the existing credited-attempt mask or frozen model rows.')
 p=a.out/'SOURCE_NO_PLAY_COUNTER_QUALIFICATION_V1.json';assert not p.exists();p.write_text(json.dumps(value,indent=2)+'\n')
 # Existing raw reconstruction proved all rows of this public source table; use
 # exact identities to distinguish offered membership from broad participant rows.
 public=read(b/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz');queries={ (r['game_id'],r['player_id']):r for r in public if r['season']==2026 and r['week']<=8};assert len(queries)==277
 offergroups=collections.defaultdict(list);bindings=[]
 for w in range(5,9):
  path=getattr(a,'week'+str(w));rr=read(path)['rows'];bindings.append(dict(source_id='RETAINED_B_QB_W'+str(w),sha256=sha(path)))
  for r in rr:
   if r.get('target')not in('pass_cmp','pass_att'):continue
   if w==8 and not(r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original'and not r.get('method_key')):continue
   assert r['season']==2026 and r['week']==w;key=r['game_id'],r['player_id'];q=queries[key]
   assert q['physical_participation']and q['target_parity'];assert r['actual']==q['official_completions'if r['target']=='pass_cmp'else'official_attempts'];offergroups[r['target']].append(r)
 result=[]
 for target,rr in sorted(offergroups.items()):
  ids={(r['game_id'],r['player_id'])for r in rr};assert len(rr)==112 and len(ids)==112
  result.append(dict(target=target,numerical_query_rows=277,offered_player_games=len(ids),nonoffered_numerical_queries=277-len(ids),games=len({r['game_id']for r in rr}),actual_weeks=sorted({r['week']for r in rr}),
   exact_labels=112,unknown_participation=0,technical_prediction_unavailability=0,query_identity_membership_sha256=hashlib.sha256(json.dumps(sorted(ids),separators=(',',':')).encode()).hexdigest(),
   offered_forecast_fallback_counts={}))
  for predpath in sorted((b/'qb-wave-v1/predictions').glob('2026-*.json.gz')):
   for r in read(predpath)['rows']:
    if r['target']==target and(r['game_id'],r['player_id'])in ids:
     stats=result[-1]['offered_forecast_fallback_counts'].setdefault(r['method'],collections.Counter());stats[r['fallback']]+=1
 receipt=dict(state='PASS_MATCHED_277_VERSUS_112_RAW_VERIFIED_IDENTITY_AND_LABEL_CROSSWALK',raw_reconstruction_receipt_sha256=sha(a.out/'RAW_TO_FEATURE_ACCEPTANCE_RECEIPT_V1.json'),derived_input_sha256=sha(b/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz'),owner_local_source_bindings=bindings,panels=result,
  source_permission='Owner-local protected boards inspected; only safe counts/hashes exported, no thresholds/players/decisionvalues.',source_timing='Current/revised feature reconstruction and timing-unverified actual-line panels; not original recommendations or authenticated quote execution.',missing='W1-4offers,oneW5gameandannualofferstillmissing/unqualified;277participantmembershipisnot277offeredgames.',new_fits=0,new_source_collections=0,new_NFL_outcomes=0,wall_seconds=time.monotonic()-started)
 p=a.out/'RAW_VERIFIED_POPULATION_CROSSWALK_V1.json';assert not p.exists();p.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(counter_admitted=value['total_credited_no_play_admitted'],counter_rows=len(rows),population=[{k:v for k,v in r.items()if k!='offered_forecast_fallback_counts'}for r in result],wall=time.monotonic()-started)))
if __name__=='__main__':main()
