from pathlib import Path
import sys,json,gzip,csv,hashlib,datetime,urllib.request,collections
import argparse
ap=argparse.ArgumentParser(description='Restore permitted exact immutable native QB offer identities for a new comparison; do not publish raw rows.')
ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--source-cache',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--week5-source-dir',type=Path,required=True)
a=ap.parse_args();ROOT=a.repo_root.resolve();sys.path.insert(0,str(ROOT))
from nfl_v2.identity import unique_gsis_bridge
CACHE=a.source_cache.resolve();OUT=a.output.resolve();OUT.mkdir(parents=True,exist_ok=True);W5=a.week5_source_dir.resolve()
expected=json.loads((ROOT/'reports/player-context-matchup-01/B/independent/RETAINED_QB_OFFER_INVENTORY_V1.json').read_bytes())
with gzip.open(ROOT/'reports/player-context-matchup-01/B/source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz','rt') as f:queries={(q['game_id'],q['player_id']):q for q in json.load(f)}
all_sources=[];receipts=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def identity(r):return tuple(str(r[k])if k=='line'else r.get(k)for k in('game_id','player_id','target','line','line_from','source_head','source_server_clock'))
for week in range(5,9):
 with gzip.open(CACHE/'roster-week8-identity-2026.csv.gz','rt')as f:bridge=unique_gsis_bridge([(r['sleeper_id'],r['gsis_id'])for r in csv.DictReader(f)if r['season']=='2026'and int(r['week'])<=week and r['sleeper_id']and r['gsis_id']],source_id=f'WEEK_LE{week}_EXACT_ID_BRIDGE_ONLY_NO_ROSTER_FEATURE_SUBSTITUTION')
 games={r['espn']:r for r in csv.DictReader((CACHE/'games.csv').open())if(r['season'],r['game_type'],r['week'])==('2026','REG',str(week))}
 if week==5:
  meta=json.loads(gzip.decompress((W5/'FROZEN_W5_METADATA.json.gz').read_bytes()))['rows']
  boards={head:json.loads((W5/('W5_SOURCE_'+head+'.json')).read_bytes())for head in {r['source_head'] for r in meta}}
  entries=[]
  for m in meta:
   if m['target']not in('pass_cmp','pass_att'):continue
   p=boards[m['source_head']]['players'][m['source_player_index']];prop=p['props'][m['source_prop_index']]
   assert prop['key']==m['target'] and prop['line']==m['line']
   entries.append((dict(m),p,prop))
 else:
  if week in(6,7):
   base=ROOT/'reports/completion-20261031g/source-expansion';base=base/'w7-rolling-v1'if week==7 else base
   proto=json.loads((base/'FROZEN_ROLLING_SOURCE_ASSIGNMENTS.json').read_bytes());assign=proto['assignments'];known={r['head_sha']:r for r in json.loads((base/'METADATA_QUALIFICATION_RECEIPT.json').read_bytes())['source_sources']}
   norm=[dict(game_id=a['game_id'],source_ESPN_event_id=a['source_ESPN_event_id'],source_head=a['selected_source_commit'],source_server_clock=a['source_server_clock'],source_server_run_id=a['server_run_id'],kickoff=a['kickoff'],T90=a['T90'])for a in assign]
  else:
   proto=json.loads((ROOT/'reports/week8-grading-20261102l/FROZEN_SOURCE_ASSIGNMENTS_V1.json').read_bytes());known={}
   norm=[dict(game_id=a['game_id'],source_ESPN_event_id=a['espn_game_id'],source_head=a['selected_source']['head'],source_server_clock=a['selected_source']['server_retained_at'],source_server_run_id=a['selected_source']['run_id'],kickoff=a['kickoff_utc'],T90=a['T90'])for a in proto['assignments']if a['selected_source']]
  boards={}
  for head in sorted({a['source_head']for a in norm}):
   path=f'output/data/archive/2026_w{week:02d}.json';local=OUT/f'W{week}_SOURCE_{head}.json';url=f'https://raw.githubusercontent.com/NickNicky19/nicks-expert-nfl-picks/{head}/{path}'
   b=local.read_bytes()if local.exists()else urllib.request.urlopen(url,timeout=30).read()
   if head in known:
    k=known[head];assert(len(b),sha(b),blob(b))==(k['bytes'],k['source_sha256'],k['blob_sha1'])
   if not local.exists():local.write_bytes(b)
   boards[head]=json.loads(b);all_sources.append(dict(week=week,head=head,path=path,bytes=len(b),SHA256=sha(b),Git_blob_sha1=blob(b),old_source_hash_verified=head in known))
  entries=[]
  for a in norm:
   board=boards[a['source_head']];assert(board['season'],board['week'])==(2026,week)
   for pi,p in enumerate(board['players']):
    if str(p['game_id'])!=a['source_ESPN_event_id']:continue
    for qi,prop in enumerate(p['props']):
     if prop['key']not in('pass_cmp','pass_att')or prop.get('line_from')not in('dk','sleeper'):continue
     m=dict(game_id=a['game_id'],player_id=bridge.get(str(p['id'])),source_player_id=str(p['id']),source_game_id=a['source_ESPN_event_id'],target=prop['key'],line=prop['line'],line_from=prop['line_from'],source_head=a['source_head'],source_server_clock=a['source_server_clock'],source_server_run_id=a['source_server_run_id'],kickoff=a['kickoff'],source_T90_deadline=a['T90'],season=2026,week=week,position=p['pos'],team=p.get('team'),source_player_index=pi,source_prop_index=qi)
     entries.append((m,p,prop))
 rows=[]
 for m,p,prop in entries:
  assert p['pos']=='QB';q=queries[m['game_id'],m['player_id']];assert q['physical_participation']
  m.update(prediction=prop.get('adj'),raw_prediction=prop.get('proj'),original_side=prop.get('lean'),side=prop.get('lean'),actual=q['official_completions'if m['target']=='pass_cmp'else'official_attempts'],label_state='SUPPORTED',participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL',panel='ORIGINAL_PROVIDER_T90',strategy='original',method_key=None,model_output_source='RETAINED_WEBSITE_ADJUSTED_RAW',source_row_index=len(rows))
  assert m['actual'] is not None;rows.append(m)
 keys=[identity(r)for r in rows];assert len(keys)==len(set(keys))
 digest=sha(json.dumps(sorted(keys),separators=(',',':')).encode());e=next(x for x in expected['weeks']if x['week']==week)
 assert len(rows)==e['records'] and digest==e['offer_identity_sha256'],(week,len(rows),digest,e['offer_identity_sha256'])
 b=gzip.compress(json.dumps({'schema':'B_NATIVE_QB_OFFERS_KEY_RESTORATION_v1','rows':rows},sort_keys=True,separators=(',',':'),allow_nan=False).encode(),mtime=0);p=OUT/f'RESTORED_W{week}_QB_OFFERS.json.gz';assert not p.exists() or p.read_bytes()==b
 if not p.exists():p.write_bytes(b)
 receipts.append(dict(week=week,rows=len(rows),categories=dict(collections.Counter(r['target']for r in rows)),games=len({r['game_id']for r in rows}),offer_identity_sha256=digest,prior_inventory_identity_sha256=e['offer_identity_sha256'],exact_identity_parity=True,new_file_SHA256=sha(b),new_file_bytes=len(b),original_normalized_artifact_SHA256=e['source_sha256'],original_normalized_byte_restore=False,method='Exact original immutable archive lines/source clocks/identities plus qualified retained derived QB labels; new normalized representation explicitly versioned',source_adjusted_point_available=sum(r['prediction']is not None for r in rows),source_raw_point_available=sum(r['raw_prediction']is not None for r in rows)))
result=dict(id='B_NEXTGEN_NATIVE_QB_OFFER_KEY_RESTORATION_v1',checked_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='Owner-local new research uses same224sourcekeys/112playergames,112CMPoffers; not new observations, regrade, fit or sourceclock authentication',weeks=receipts,immutable_source_restorations=all_sources,unchanged_limit='Provider tags and retained-by clocks are not independently authenticated original bookmaker quote timestamps; native historical model forecast still retrospective kickoff reconstruction',no_new_NFL_scores=True,new_fits=0,new_model_inference=0,raw_rows_public=False)
(OUT/'RESTORATION_RECEIPT.json').write_text(json.dumps(result,indent=2)+'\n')
(ROOT/'reports/next-generation-information-research-01/B/peer-coordination/NATIVE_OFFER_RESTORATION_V1.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'weeks':receipts,'sources':len(all_sources),'raw_restored_bytes':sum(s['bytes']for s in all_sources)},indent=2))
