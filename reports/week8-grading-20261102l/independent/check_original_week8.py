"""Independent saved Week8 source joins, finality, exact thresholds and side counts.

No producer grading/label code imported. Outputs contain aggregates only.
"""
import argparse,collections,csv,datetime,gzip,hashlib,json,math,re
from decimal import Decimal
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
FIELDS={'pass_yd':'passing_yards','pass_td':'passing_tds','pass_cmp':'completions','pass_att':'attempts','pass_int':'passing_interceptions','rush_yd':'rushing_yards','rush_att':'carries','rec':'receptions','rec_yd':'receiving_yards'}
PHYSICAL=('attempts','carries','targets','receptions','punt_returns','kickoff_returns')
SUBSTANTIVE=('player_id','game_id','key','line','direction','adj','forecast_source','model_version','product','selected_at')
RAW='SAVED_RAW_PROJECTION_DIRECTION_RETAINED_PRECISION';ADJ='SAVED_ADJUSTED_POINT_DIRECTION_RETAINED_PRECISION'
def read(p):return json.loads(Path(p).read_bytes())
def canon(z):return json.dumps(z,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def iso(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))
def numeric(x):
 try:v=Decimal(str(x))
 except Exception:return None
 return v if v.is_finite()else None
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--private-root',type=Path,required=True);ap.add_argument('--identity-roster',type=Path,required=True);a=ap.parse_args();priv=a.private_root;pub=HERE.parent;out=pub/'original-v1';assignment=read(pub/'FROZEN_SOURCE_ASSIGNMENTS_V1.json');schedule=assignment['assignments'];frozen={r['game_id']:r for r in schedule};receipt=read(out/'RUN_RECEIPT.json')
 assert assignment['at_utc']<min(r['started_at_utc']for r in read(priv/'ACQUISITION_LABELS_V1.json')['receipts'])
 assert receipt['scores_sha256']==sha(out/'SCORES.json')and receipt['private_grades_sha256']==sha(priv/'ORIGINAL_AND_TOP_GRADED_ROWS_V1.json.gz')and receipt['source_label_sha256']==sha(priv/'source-labels/fresh-player-stats-2026.csv')and receipt['finality_sha256']==sha(priv/'source-labels/espn-week8-scoreboard-v2.json')
 games={r['game_id']:r for r in csv.DictReader((priv/'source-labels/fresh-games.csv').open())if(r['season'],r['game_type'],r['week'])==('2026','REG','8')};assert set(games)==set(frozen)and len(games)==14;byespn={r['espn']:g for g,r in games.items()};events={e['id']:e for e in read(priv/'source-labels/espn-week8-scoreboard-v2.json')['events']};finality={}
 for gid,g in games.items():
  e=events[g['espn']];assert iso(e['date'])==iso(frozen[gid]['kickoff_utc']);s=e['status']['type'];finality[gid]='FINAL'if s.get('completed')is True and s.get('state')=='post'else'PENDING'if s.get('state')in('pre','in')else'UNVERIFIED'
  if finality[gid]=='FINAL':assert{c['homeAway']:numeric(c['score'])for c in e['competitions'][0]['competitors']}=={'home':numeric(g['home_score']),'away':numeric(g['away_score'])}
 assert collections.Counter(finality.values())=={'FINAL':13,'PENDING':1}
 stats={}
 for r in csv.DictReader((priv/'source-labels/fresh-player-stats-2026.csv').open()):
  if(r['season'],r['week'],r['season_type'])!=('2026','8','REG'):continue
  key=r['game_id'],r['player_id'];assert key not in stats and key[0]in games;g=games[key[0]];assert{r['team'],r['opponent_team']}=={g['home_team'],g['away_team']};stats[key]=r
 forward=collections.defaultdict(set);reverse=collections.defaultdict(set)
 with gzip.open(a.identity_roster,'rt')as f:
  for r in csv.DictReader(f):
   if r['season']=='2026'and int(r['week'])<=8 and r['sleeper_id']and r['gsis_id']:forward[r['sleeper_id']].add(r['gsis_id']);reverse[r['gsis_id']].add(r['sleeper_id'])
 bridge={sid:next(iter(v))for sid,v in forward.items()if len(v)==1 and re.fullmatch(r'00-\d{7}',next(iter(v)))and len(reverse[next(iter(v))])==1}
 def identity(sid):return sid if re.fullmatch(r'00-\d{7}',str(sid))else bridge.get(str(sid))
 def label(gid,pid,target):
  if finality.get(gid)=='PENDING':return None,'UNKNOWN','pending'
  if finality.get(gid)!='FINAL':return None,'UNKNOWN','final'
  r=stats.get((gid,pid))
  if not r or not any((numeric(r.get(k))or Decimal(0))>0 for k in PHYSICAL):return None,'UNKNOWN','final'
  if target in FIELDS:v=numeric(r.get(FIELDS[target]))
  elif target in('rush_rec_yd','anytime_td'):
   keys=('rushing_yards','receiving_yards')if target=='rush_rec_yd'else('rushing_tds','receiving_tds');values=[numeric(r.get(k))for k in keys];v=None if any(x is None for x in values)else sum(values)
   if v is not None and target=='anytime_td':v=Decimal(int(v>=1))
  else:v=None
  if v is not None:assert v==v.to_integral_value()and(target.endswith('_yd')or v>=0)
  return v,'VERIFIED_PLAYED_POSITIVE_PHYSICAL','final'
 # Authenticate retained source clocks and exact immutable source files.
 source=priv/'source-metadata';proofs={r['head']:r for r in assignment['proofs']};acq={r['name']:r for r in read(priv/'ACQUISITION_METADATA_V1.json')['receipts']};boards={};directories={}
 for head,p in proofs.items():
  log=priv/f"run-{p['run_id']}.log";assert sha(log)==p['log_sha256'];line=next(x for x in log.read_text().splitlines()if x.startswith(p['server_retained_at']+' '));f=read_json_line=line.split(' ',1)[1];f=json.loads(f);assert f['state']=='PUBLISHED_SOURCE_AND_ASSETS_BOUND'and f['published_head_sha']==head and f['manifest_sha256']==p['publication_manifest_sha256']
  bp=source/f'board-{head}.json';ar=acq[bp.name];assert sha(bp)==ar['sha256']and head in ar['url'];boards[head]=read(bp)
  dp=priv/('selected_directory.json'if head=='ea2ce5f57146112bb4b5ccebcf8544b181192f50'else f'selected-directory-{head}.json');directories[head]=read(dp)
 for s in schedule:
  eligible=[p for p in proofs.values()if iso(p['server_retained_at'])<=iso(s['T90'])];expected=max(eligible,key=lambda p:(iso(p['server_retained_at']),p['head']))if eligible else None;assert s['selected_source']==expected
 joined=readgz(priv/'ORIGINAL_JOINED_ROWS_V1.json.gz')['rows'];assert len(joined)==1591;canonkeys=set();source_fields_checked=0
 for r in joined:
  gid=r['game_id'];assert byespn[r['source_game_id']]==gid and identity(r['source_player_id'])==r['player_id'];key=gid,r['player_id']or r['source_player_id'],r['target'];assert key not in canonkeys;canonkeys.add(key)
  s=frozen[gid];assert r['source_head']==s['selected_source']['head']and r['source_server_clock']==s['selected_source']['server_retained_at']and iso(r['source_server_clock'])<=iso(r['kickoff'])-datetime.timedelta(minutes=90)
  b=boards[r['source_head']];matches=[(p,q)for p in b['players']if str(p['id'])==r['source_player_id']and str(p['game_id'])==r['source_game_id']for q in p['props']if q['key']==r['target']];assert len(matches)==1;player,q=matches[0]
  for x,y in ((r['line'],q['line']),(r['prediction'],q.get('adj')),(r['raw_prediction'],q.get('proj'))):assert numeric(x)==numeric(y)
  assert r['side']==q.get('lean')and r['line_from']==q.get('line_from')and r['position']==player.get('pos');assert r['panel']==('ORIGINAL_PROVIDER_T90'if q.get('line_from')in('dk','sleeper')else'ORIGINAL_SITE_GENERATED_THRESHOLD_T90');source_fields_checked+=6
 grades=readgz(priv/'ORIGINAL_AND_TOP_GRADED_ROWS_V1.json.gz')['rows'];assert len(grades)==8242;examples={};zero_decided=0
 for i,r in enumerate(grades):
  v,part,os=label(r['game_id'],r['player_id'],r['target']);assert numeric(r['actual'])==v and r['participation']==part and r['outcome_state']==os
  point=r['raw_prediction']if r['strategy']==RAW else r['prediction'];selected=r['side']if r['strategy']=='original'else'over'if r['strategy']=='alwaysOver'else'under'if r['strategy']=='alwaysUnder'else None if point is None else'over'if numeric(point)>numeric(r['line'])else'under'if numeric(point)<numeric(r['line'])else None
  assert selected==r['selected_side']
  state='ABSTAIN'if selected is None else'PENDING'if os=='pending'else'UNKNOWN_PARTICIPATION'if part=='UNKNOWN'else'MISSING_ACTUAL'if v is None else'PUSH'if v==numeric(r['line'])else'WIN'if(v>numeric(r['line']))==(selected=='over')else'LOSS'
  assert state==r['statistical_state']and r['settlement_state']==('NOT_SELECTED'if selected is None else'UNRESOLVED_CONTRACT')and r['net_return']is None
  if v==0 and state in('WIN','LOSS'):zero_decided+=1
  if r['panel']=='ORIGINAL_PROVIDER_T90'and r['strategy']=='original'and state not in examples:examples[state]={'grade_row_index':i,'source_row_index':r['source_row_index'],'state':state,'target':r['target'],'selected_side':selected,'line':r['line'],'prediction':r['prediction'],'actual':r['actual'],'game_id':r['game_id'],'player_id':r['player_id'],'label_source_field':FIELDS.get(r['target'],'rushing_yards+receiving_yards'),'source_head':r['source_head']}
 # Independently authenticate every retained list and substantive first-appearance clock.
 listc=read(out/'SAVED_LIST_VERSION_CENSUS.json');packetby={};first={}
 for item in listc['versions']:
  path=source/item['filename'];packet=read(path);assert sha(path)==item['packet_sha256']==path.stem[9:];seen=[]
  for head,dd in directories.items():
   entry=next((d for d in dd if d['name']==path.name[9:]),None)
   if entry:
    blob=path.read_bytes();assert hashlib.sha1(b'blob '+str(len(blob)).encode()+b'\0'+blob).hexdigest()==entry['sha']and len(blob)==entry['size'];seen.append(proofs[head])
  proof=min(seen,key=lambda p:(iso(p['server_retained_at']),p['head']));assert proof['head']==item['source_head']and proof['server_retained_at']==item['server_retained_by'];assert len(packet['picks']['over'])==item['selected_by_side']['over']and len(packet['picks']['under'])==item['selected_by_side']['under'];packetby[item['panel']]=packet
  for side,rows in packet['picks'].items():
   for row in rows:
    sig=hashlib.sha256(canon({k:row.get(k)for k in SUBSTANTIVE})).hexdigest();candidate=(iso(proof['server_retained_at']),proof['head']);first[sig]=min(first.get(sig,candidate),candidate)
 selected_keys=set();latest_signature_age=collections.Counter();poststart_lists=[]
 for item in listc['versions']:
  packet=packetby[item['panel']];actualrows=[r for r in grades if r['panel']==item['panel']];assert len(actualrows)==item['rows'];fullclock=iso(item['server_retained_by']);kickoffs=[];late=0
  for side,rows in packet['picks'].items():
   for source_row in rows:
    if source_row['key']not in FIELDS and source_row['key']!='rush_rec_yd':continue
    sig=hashlib.sha256(canon({k:source_row.get(k)for k in SUBSTANTIVE})).hexdigest();r=next(r for r in actualrows if r['original_record_signature']==sig);clock,head=first[sig];assert iso(r['source_server_clock'])==clock and r['source_head']==head and r['selected_side']==side and numeric(r['line'])==numeric(source_row['line'])and numeric(r['prediction'])==numeric(source_row.get('adj'))
    key=(item['panel'],r['game_id'],r['player_id']or r['source_player_id'],r['target'],numeric(r['line']));assert key not in selected_keys;selected_keys.add(key);kickoffs.append(iso(r['kickoff']));bad=clock>=iso(r['kickoff'])or(source_row.get('selected_at')and iso(source_row['selected_at'])>=iso(r['kickoff']));late+=bool(bad)
    if item['source_head']=='ea2ce5f57146112bb4b5ccebcf8544b181192f50':latest_signature_age['earlier_proved_record'if clock<fullclock else'first_proved_at_late_snapshot']+=1;assert clock<iso(r['kickoff'])
  assert late==item['no_proved_pregame_rows']
  if kickoffs and fullclock>=min(kickoffs):poststart_lists.append(item['panel'])
 primary=min(listc['versions'],key=lambda x:(iso(x['server_retained_by']),x['packet_sha256']));assert primary==listc['primary']and primary['selected_by_side']=={'over':11,'under':12}and primary['rows']==23 and primary['panel']not in poststart_lists
 assert latest_signature_age=={'earlier_proved_record':17,'first_proved_at_late_snapshot':7}
 # All published side-score and readable-wide records are checked from independently verified grades.
 scores=read(out/'SCORES.json');assert len(scores)==1152;groupmap={};state_names=('WIN','LOSS','PUSH','UNKNOWN_PARTICIPATION','MISSING_ACTUAL','PENDING','VOID','UNRESOLVED_CONTRACT');ci_checks=0
 for score in scores:
  pool=[r for r in grades if r['panel']==score['evaluation_panel_id']and r['strategy']==score['strategy']and r['target']==score['target']];tt=[r for r in pool if score['cohort_id']!='SAVED_BOARD_TOP_FLAGS'or r['top_over']or r['top_under']];rr=[r for r in tt if r['selected_side']and(score['side']=='Combined'or r['selected_side']==score['side'])];cnt=collections.Counter(r['statistical_state']for r in rr);n=cnt['WIN']+cnt['LOSS'];sm=score['selection_metrics'];assert score['forecast_rows']==len(rr)and score['n']==n and sm['WIN']==cnt['WIN']and sm['LOSS']==cnt['LOSS']and sm['PUSH']==cnt['PUSH']and sm['hit_rate']==(cnt['WIN']/n if n else None);assert sm['status_counts']=={s:cnt[s]for s in state_names};assert sm['selection_pool_count']==len(pool)and sm['abstentions_outside_selected_partition']==sum(r['selected_side']is None for r in pool)and sm['selection_coverage']==(len(rr)/len(pool)if pool else None)
  assert score['unique_games']==len({r['game_id']for r in rr})and score['whole_week_complete']is False and score['mae']is score['mse']is score['brier']is score['log_loss']is None
  assert score['query_membership_sha256']==hashlib.sha256(canon(sorted(r['source_row_index']for r in rr))).hexdigest();u=sm['game_uncertainty'];dec=[r for r in rr if r['statistical_state']in('WIN','LOSS')];gs=sorted({r['game_id']for r in dec});assert u['game_clusters']==len(gs)and u['week_interval']is None
  if len(gs)>=8:
   numer=np.array([sum(r['statistical_state']=='WIN'for r in dec if r['game_id']==g)for g in gs]);denom=np.array([sum(r['game_id']==g for r in dec)for g in gs]);draw=np.random.default_rng(1703).integers(0,len(gs),size=(500,len(gs)));values=numer[draw].sum(1)/denom[draw].sum(1);interval=np.quantile(values,[.025,.975],method='linear');assert np.allclose(interval,u['game_interval'],atol=1e-14,rtol=0)
  else:assert u['game_interval']is None
  ci_checks+=1;groupmap.setdefault((score['evaluation_panel_id'],score['strategy'],score['cohort_id'],score['target']),{})[score['side']]=score
 for sides in groupmap.values():
  o,u,c=(sides[k]for k in('over','under','Combined'));assert c['n']==o['n']+u['n']and c['forecast_rows']==o['forecast_rows']+u['forecast_rows'];assert all(c['selection_metrics']['status_counts'][s]==o['selection_metrics']['status_counts'][s]+u['selection_metrics']['status_counts'][s]for s in state_names)
 table=read(out/'SIDE_TABLE.json');assert len(table)==384
 for r in table:
  ss=groupmap[r['panel'],r['strategy'],r['cohort'],r['target']]
  for side,prefix in(('over','over'),('under','under'),('Combined','combined')):
   v=ss[side];sm=v['selection_metrics'];assert(r[prefix+'_selected'],r[prefix+'_wins'],r[prefix+'_losses'],r[prefix+'_decided'],r[prefix+'_hit_rate'])==(v['forecast_rows'],sm['WIN'],sm['LOSS'],v['n'],sm['hit_rate'])
 provider=[r for r in grades if r['panel']=='ORIGINAL_PROVIDER_T90'and r['strategy']=='original'and r['selected_side']];counts=collections.Counter(r['statistical_state']for r in provider);assert len(provider)==427 and counts=={'WIN':194,'LOSS':192,'PENDING':30,'UNKNOWN_PARTICIPATION':11}
 worked=priv/'independent-verification';worked.mkdir(exist_ok=True);examplepath=worked/'ORIGINAL_WORKED_EXAMPLES_V1.json'
 with examplepath.open('x')as f:json.dump({'source_graded_packet_sha256':sha(priv/'ORIGINAL_AND_TOP_GRADED_ROWS_V1.json.gz'),'examples':list(examples.values())},f,indent=2);f.write('\n')
 output={'state':'PASS_INDEPENDENT_INITIAL_WEEK8_ORIGINAL_LABELS_SOURCE_CLOCKS_LISTS_AND_SIDE_MATH','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_score_sha256':sha(out/'SCORES.json'),'source_grade_packet_sha256':sha(priv/'ORIGINAL_AND_TOP_GRADED_ROWS_V1.json.gz'),'source_joined_packet_sha256':sha(priv/'ORIGINAL_JOINED_ROWS_V1.json.gz'),'frozen_source_assignment_sha256':sha(pub/'FROZEN_SOURCE_ASSIGNMENTS_V1.json'),'identity_roster_sha256':sha(a.identity_roster),'NFLverse_stats_sha256':sha(priv/'source-labels/fresh-player-stats-2026.csv'),'NFLverse_games_sha256':sha(priv/'source-labels/fresh-games.csv'),'ESPN_finality_sha256':sha(priv/'source-labels/espn-week8-scoreboard-v2.json'),'game_finality':{'FINAL':13,'PENDING':1},'all13_ESPN_final_scores_match_schedule':True,'source_label_and_identity_checks':len(grades),'raw_board_rows_and_source_field_checks':[len(joined),source_fields_checked],'source_publication_clock_proofs':len(proofs),'original_provider_selected':427,'original_provider_over':{'WIN':104,'LOSS':122,'PENDING':12,'UNKNOWN':7,'selected':245},'original_provider_under':{'WIN':90,'LOSS':70,'PENDING':18,'UNKNOWN':4,'selected':182},'original_provider_combined':dict(counts),'side_score_views_verified':1152,'side_triads_verified':384,'wide_views_verified':384,'bootstrap_views_verified':ci_checks,'played_zero_grade_views_retained':zero_decided,'saved_list_versions':len(listc['versions']),'primary_saved_list_selected':23,'primary_saved_list_side_counts':{'over':11,'under':12},'primary_saved_list_counts':{'WIN':8,'LOSS':9,'PENDING':6},'late_snapshot_signature_clock_counts':dict(latest_signature_age),'post_start_whole_list_snapshots':poststart_lists,'list_qualification':'Post-start whole-list membership is not an authenticated fixed-weekly policy. Every retained individual decision is qualified by its own earliest substantive signature and target-game kickoff; all17earlier and7newlate-afternoon decisions in the latest snapshot pass those row-level gates. Keep versions separate, never union as independent weekly picks.','cohort_qualification':'SAVED_BOARD_TOP_FLAGS mixes registered per-game source versions; it is not one original fixed weekly top12 list. Its selected subset coverage is relative to the full category/source pool.','membership_hash_qualification':'Index-ordinal query hashes are source/panel scoped; cross-panel matching requires actual game/player/target/line identities.','book_settlement_and_prices':'All contracts unverified; statistical wins/losses are not settled profit. No actual push/void asserted when absent.','private_worked_examples_sha256':sha(examplepath),'private_example_states':sorted(examples),'private_example_retention':'LOCAL_VERIFICATION_CACHE_ONLY; no new offhost backup claim','whole_week_complete':False,'new_transfers_or_model_calls':0,'source_preserved':True,'checker_sha256':sha(__file__)}
 with(HERE/'INITIAL_ORIGINAL_WEEK8_INDEPENDENT_REVIEW_V1.json').open('x')as f:json.dump(output,f,indent=2);f.write('\n')
 print(json.dumps({k:output[k]for k in('state','side_score_views_verified','side_triads_verified','source_label_and_identity_checks','original_provider_combined','late_snapshot_signature_clock_counts')}))
def readgz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
if __name__=='__main__':main()
