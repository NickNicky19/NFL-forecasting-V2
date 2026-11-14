"""B QB derivation from already retained/public C projections; no network/fit."""
import argparse,base64,collections,csv,datetime,gzip,hashlib,io,json,lzma,math,resource,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5];sys.path.insert(0,str(ROOT))
from tools.qualify_player_context_sources import context_index,schedules
from tools.prepare_qb_depth_charting_v2 import eligible_attempt

C_REF='d3d1ef4dc60826334234cfa1a1b8e373b2ee024e'
EXPECTED={
 'C_source_0.b64':'ec6cf4186d2da567b28b06cdc791bbd04c8ea17ffc4cd5cd12640e51a4e1bad2',
 'C_source_1.b64':'350ecd653332dde323e67097459cdd7662ec729aba977a1ea3f92c57bf1e346a',
 'C_source_2.txt':'14d32c7b5ea24be56441d3fca6ab0d6683bea52b42f4a4e541fd1403a6bf29b2',
 'C_source_3.txt':'b085647871f6a52f50d7cbfdc4e39dad48465abc6e1e2cdb10aec26f684cf35c',
 'C_roster_projection.json':'bf725f7bd40b6327e03a0ae040ff107d51fe5defa7f2b1bbea2831bf66642050',
 'C_input.json':'0d80bd9437295246c34e302fd1c6eb417afae4d972762b3b9fd6a356e966475d'}
C_PATHS=['sources/profile-closure-next-02/pbp_facts_2026.csv.xz','sources/profile-closure-next-02/current_facts_2026.csv.gz',
 'sources/profile-closure-next-02/schedule.csv','sources/profile-closure-next-02/completed_game_proof.json',
 'sources/profile-closure-next-02/roster_current_season.json','prospective/runs/C-C04-20261110-W10-FIRST-01/draft/MODEL_INPUT_MANIFEST.json']
FIELDS=('ydstogo','yardline_100','game_seconds_remaining','score_differential')

def sha(b):return hashlib.sha256(b).hexdigest()
def number(x):
 try:v=float(x)
 except (TypeError,ValueError):return math.nan
 return v
def read_bytes(path):
 b=path.read_bytes();return base64.b64decode(b) if path.suffix=='.b64' else b
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cache-dir',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 a.out=a.out.resolve();registered=json.loads((a.out/'DERIVATION_REGISTRATION_V1.json').read_text());budget=registered['budget'];start=time.monotonic();cpu=time.process_time()
 blobs={};bindings=[]
 for (name,h),path in zip(EXPECTED.items(),C_PATHS):
  body=read_bytes(a.cache_dir/name)
  if sha(body)!=h:raise ValueError('Bound C source bytes changed')
  blobs[name]=body;bindings.append(dict(repository='NickNicky19/NFL-forecasting-NGS-C',commit=C_REF,path=path,sha256=h,bytes=len(body)))
 pbp=list(csv.DictReader(io.StringIO(lzma.decompress(blobs['C_source_0.b64']).decode())))
 stats=list(csv.DictReader(io.StringIO(gzip.decompress(blobs['C_source_1.b64']).decode())))
 finality=json.loads(blobs['C_source_3.txt']);roster=json.loads(blobs['C_roster_projection.json']);manifest=json.loads(blobs['C_input.json'])
 oldpath=ROOT/'reports/player-context-matchup-01/B/source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz';oldbody=oldpath.read_bytes()
 if sha(oldbody)!='f23bb72f05f398c7108700e10fa7bf63e233aca57bc67eb6820a38c9f212af90':raise ValueError('Old B binding changed')
 old=json.loads(gzip.decompress(oldbody));older=[r for r in old if r['season']<2026];old26=[r for r in old if r['season']==2026]
 # The proof's explicit match records cover recent native FINALs; older games
 # use its declared completed-ID rule and the unchanged accepted schedule
 # parser (America/New_York -> timezone-aware UTC), not an invented kickoff.
 games=schedules(a.cache_dir/'C_source_2.txt')
 games.update({r['game_id']:r for r in finality['game_match_records']});admitted=set(finality['completed_game_ids'])
 if set(finality['recent_native_final_game_ids'])!={'2026_09_CIN_ATL','2026_09_JAX_BAL'}:raise ValueError('Unexpected recent finality scope')
 required={'game_id','play_id','season','week','season_type','posteam','defteam','down','air_yards','pass_attempt','sack','two_point_attempt','play_deleted','complete_pass','passer_player_id','receiver_player_id','pass_location',*FIELDS}
 if not required<=set(pbp[0]):raise ValueError('QB PBP field/denominator source incomplete')
 seen=set();group=collections.defaultdict(list);safety_unknown=collections.Counter();eligible_throws=0
 for row in pbp:
  key=row['game_id'],row['play_id']
  if key in seen:raise ValueError('Duplicate PBP identity')
  seen.add(key)
  if number(row['pass_attempt'])==1:
   for f in ('sack','two_point_attempt','play_deleted','complete_pass'):
    safety_unknown[f]+=number(row[f]) not in (0,1)
  if row['season_type']=='REG' and eligible_attempt(row):
   if number(row['complete_pass']) not in (0,1):raise ValueError('Unknown completion annotation')
   group[row['game_id'],row['passer_player_id']].append(row);eligible_throws+=1
 if any(safety_unknown.values()):raise ValueError('Unknown consumed safety flags')
 derived={};all_qb=[];held=[];mismatches=[];qb_seen=set()
 for row in stats:
  if row['season_type']!='REG' or row['position']!='QB':continue
  key=row['game_id'],row['player_id']
  if key in qb_seen:raise ValueError('Duplicate official QB identity')
  qb_seen.add(key);all_qb.append(row)
  values=[number(row[k]) for k in ('attempts','completions')]
  if not all(math.isfinite(v) and v>=0 and int(v)==v for v in values):raise ValueError('Unknown/noninteger official target')
  att,comp=map(int,values);plays=group.get(key,[])
  if (att,comp)!=(len(plays),sum(number(p['complete_pass'])==1 for p in plays)):
   mismatches.append(dict(game_id=key[0],player_id=key[1]));continue
  if row['game_id'] not in admitted:
   held.append(dict(game_id=key[0],player_id=key[1],reason='RECENT_NATIVE_FINALITY_UNQUALIFIED'));continue
  game=games[row['game_id']];kickoff=float(game['kickoff'])
  a25=[0]*25;c25=[0]*25
  for p in plays:
   if p['posteam']!=row['team'] or p['defteam']!=row['opponent_team']:raise ValueError('QB historical team/opponent conflict')
   j=context_index(number(p['down']),number(p['air_yards']));a25[j]+=1;c25[j]+=number(p['complete_pass'])==1
  field={}
  for name in FIELDS:
   values=[number(p[name]) for p in plays];values=[v for v in values if math.isfinite(v)]
   field[name]=dict(mean=sum(values)/len(values) if values else None,n=len(values))
  physical=any(math.isfinite(number(row.get(f))) and number(row.get(f))>0 for f in ('attempts','carries','targets','receptions','sacks_suffered','passing_2pt_conversions','rushing_2pt_conversions'))
  r=dict(game_id=key[0],player_id=key[1],season=int(row['season']),week=int(row['week']),team=row['team'],opponent=row['opponent_team'],kickoff=kickoff,available=kickoff+7*86400,
   attempts=att,completions=comp,context_attempts=a25,context_completions=c25,field_context=field,
   pass_destination_counts=dict(collections.Counter(p['pass_location'] or 'UNKNOWN' for p in plays)),
   known_receiver_throws=sum(bool(p['receiver_player_id']) for p in plays),unknown_receiver_throws=sum(not p['receiver_player_id'] for p in plays),
   throwing_population='PBP credited passer; QB target eligibility separately reconciled to official rows' if plays else 'Official explicitly reported zero QB stat row',
   official_attempts=att,official_completions=comp,target_parity=True,position='QB',physical_participation=physical,
   label_status='SUPPORTED_PLAYED' if physical else 'UNKNOWN_PARTICIPATION',population='RETROSPECTIVE_OFFICIAL_QB_STAT_ROWS_NOT_EXANTE_ROSTER')
  derived[key]=r
 if mismatches:raise ValueError('Official QB ATT/CMP parity failure')
 core=('season','week','team','opponent','kickoff','available','attempts','completions','context_attempts','context_completions','pass_destination_counts','known_receiver_throws','unknown_receiver_throws','official_attempts','official_completions','target_parity','physical_participation','label_status')
 if {(r['game_id'],r['player_id']) for r in old26}!={k for k,r in derived.items() if r['week']<=8}:raise ValueError('Prior2026 QB population changed')
 max_field_difference=0.
 for r in old26:
  new=derived[r['game_id'],r['player_id']]
  if any(r[k]!=new[k] for k in core):raise ValueError('Substantive existing2026 input changed; review required')
  for name in FIELDS:
   x,y=r['field_context'][name],new['field_context'][name]
   if x['n']!=y['n'] or (x['mean'] is None)!=(y['mean'] is None):raise ValueError('Existing context support changed')
   if x['mean'] is not None:max_field_difference=max(max_field_difference,abs(x['mean']-y['mean']))
 if max_field_difference>1e-10:raise ValueError('Existing field means changed beyond arithmetic order')
 recent=[r for r in derived.values() if r['week']==9]
 if len(recent)!=4 or len(held)!=34:raise ValueError('Unexpected recent QB admission/hold population')
 result=older+old26+recent;result.sort(key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
 event={'game_id':'2026_10_WAS_NYG','native_event_id':'401873052','season':2026,'week':10,'kickoff':1794532500.,'kickoff_UTC':'2026-11-13T01:15:00+00:00'}
 basic=[]
 for row in roster:
  if row['position']!='QB' or row['team'] not in ('WAS','NYG'):continue
  if not isinstance(row['gsis_id'],str) or not row['gsis_id'].startswith('00-'):raise ValueError('Invalid current GSIS')
  basic.append(dict(**event,player_id=row['gsis_id'],name=row['full_name'],team=row['team'],opponent='NYG' if row['team']=='WAS' else 'WAS',position='QB',source_status=row['status'],
   source_contract=manifest['roster_contract'],source_snapshot_sha256=EXPECTED['C_roster_projection.json'],
   membership_scope='CURRENT_KNOWN_SEASON_ROSTER_CANDIDATE;CONDITIONAL_ON_APPEARANCE_NOT_FUTURE_GAMEDAY_GUARANTEE',
   individual_transaction_effective_UTC=None,expected_starter='UNKNOWN_NOT_INFERRED',health='UNKNOWN_NO_QUALIFIED_INJURY_FEED',
   candidate_forecast_under_C_rule=row['status']=='ACT',B_admission='PENDING_ROOT_SOURCE_REVIEW_AND_FRESH_NATIVE_STATUS'))
 if len(basic)!=8 or sum(r['candidate_forecast_under_C_rule'] for r in basic)!=5:raise ValueError('Unexpected current QB universe')
 def save(name,value):
  path=a.out/name
  if path.exists():raise FileExistsError(path)
  body=(json.dumps(value,separators=(',',':'),allow_nan=False)+'\n').encode();path.write_bytes(gzip.compress(body,mtime=0) if path.suffix=='.gz' else body)
  return dict(path=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()),bytes=path.stat().st_size)
 artifacts=[save('DERIVED_CURRENT_QB_GAME_INPUTS_V1.json.gz',result),save('CURRENT_KNOWN_QB_QUERY_CANDIDATES_V1.json',dict(event=event,basic=basic,current_forecast_candidates=[r for r in basic if r['candidate_forecast_under_C_rule']],current_admission='NOT_YET_ISSUED',future_target_outcomes_required=False))]
 resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,public_bytes=sum(p.stat().st_size for p in a.out.iterdir() if p.is_file()),new_network_requests=0,new_fits=0,new_model_inference=0,new_forecasts=0)
 if resources['wall_seconds']>budget['wall_seconds'] or resources['cpu_seconds']>budget['cpu_seconds'] or resources['peak_RSS_bytes']>budget['max_RSS_bytes'] or resources['public_bytes']>budget['public_retention_bytes']:raise ValueError('Registered derivation budget exceeded')
 receipt=dict(id='B-CURRENT-QB-CANDIDATE-INPUTS-v1',derived_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),C_ref=C_REF,source_bindings=bindings,
  old_B_input=dict(path=str(oldpath.relative_to(ROOT)),sha256=sha(oldbody),rows=len(old)),artifacts=artifacts,source_observed=manifest['source_observed'],
  actual_C_input_cutoff_UTC=manifest['actual_input_cutoff_UTC'],football_predictor_cutoff_UTC=manifest['football_predictor_cutoff_UTC'],
  records=dict(old_2022_2025_preserved_exactly=len(older),old_2026_W1_W8_preserved_exactly=len(old26),new_qualified_W9=len(recent),new_total=len(result),all_current_QB_statistics=len(all_qb),PBP_rows=len(pbp),PBP_game_play_duplicates=0,eligible_throws=eligible_throws,unknown_consumed_safety_flags=dict(safety_unknown),ATT_CMP_parity_rows=len(all_qb),max_field_mean_arithmetic_difference=max_field_difference),
  held_QB_rows=held,held_game_ids=finality['held_recent_game_ids'],recent_native_final_game_ids=finality['recent_native_final_game_ids'],
  recent_native_final_proofs=finality['retained_native_final_proofs'],
  definitions='Exact acceptedB25contextindex,strictcreditedattemptguard,officialzeroandphysical-positive-statproof;noFutureQBstatrowneededforquery;noCcatchability/receivingmodelreused',
  procedure_clock='Rowsretainmechanicalkickoff+7dayreconstruction;F2usesregistered48htransformatcurrentorigin. Observedversionsclocksherearenotbackdatedinitialavailability.',
  row_values='All2624olderand277existing2026rowsretainedexactlyafterindependentcurrentCvalidation;4qualifiedW9rowsappended. Existingpredictions/gradesnotchanged.',
  current_roster_scope='Current-knownsnapshotonly,5ACTcandidatesof8basicQBs;unknowntransaction/starter/healthunchanged. Rootmustadmitandrefreshnativeeventbeforeanynewcapture.',
  rights=manifest['rights'],attribution='nflverse/nflfastR ordinaryPBP/stat/rosterderivativesCCBY4;existingpublicCprojectionrouteonly;rawupstreamresponsesnotacquiredorrepublished',
  resources=resources,code_sha256=sha(Path(__file__).read_bytes()),helper_code=[dict(path='tools/qualify_player_context_sources.py',sha256=sha((ROOT/'tools/qualify_player_context_sources.py').read_bytes())),dict(path='tools/prepare_qb_depth_charting_v2.py',sha256=sha((ROOT/'tools/prepare_qb_depth_charting_v2.py').read_bytes()))],
  capture_state='NO_FIT_NO_FORECAST_NO_NEW_NATIVE_GET;CURRENT_INPUT_CANDIDATE_ONLY')
 save('CURRENT_INPUT_DERIVATION_RECEIPT_V1.json',receipt)
 print(json.dumps(dict(records=receipt['records'],resources=resources,artifacts=artifacts)))

if __name__=='__main__':main()
