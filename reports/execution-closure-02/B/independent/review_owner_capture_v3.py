"""Read retained public bytes only; no requests, inference or selection replay."""
import argparse,collections,gzip,hashlib,json
from datetime import datetime,timedelta
from pathlib import Path
def sha(b):return hashlib.sha256(b).hexdigest()
def time(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def main():
 ap=argparse.ArgumentParser()
 for k in ('repo','snapshots','output'):ap.add_argument('--'+k,type=Path,required=True)
 a=ap.parse_args();m=json.loads((a.snapshots/'MAP.json').read_bytes());wpath=a.repo/'reports/execution-closure-02/B/CURRENT_OWNER_CAPTURE_AND_SERVED_V3.json';w=json.loads(wpath.read_bytes());objects={};pairs=[]
 for r in m['files']:
  b=(a.snapshots/r['local_name']).read_bytes();assert len(b)==r['bytes']and sha(b)==r['sha256'];objects[r['kind'],r['path']]=b
 for (kind,path),b in objects.items():
  if kind=='git':assert b==objects['served',path];pairs.append(dict(path=path,bytes=len(b),sha256=sha(b),git_served_equal=True))
 assert len(pairs)==5 and m['ref']==w['production_commit']=='fe369c7462e4e4f290727b2d03b696d28ef5454b'
 def get(path):return json.loads(objects['git',path])
 board=get('output/data/week.json');pointer=get('output/data/weekly-selected-rankings.json');ranking=get('output/data/'+pointer['path'])
 assert pointer['sha256']==sha(objects['git','output/data/'+pointer['path']]) and pointer['bytes']==len(objects['git','output/data/'+pointer['path']])
 op=get('output/data/weekly-adaptive-overlay.json');overlay=get('output/'+op['path'])
 assert sha(objects['git','output/'+op['path']])==op['sha256'] and overlay['state']=='DISABLED_USE_R0'and not overlay['rows']
 assert ranking['display_board_sha256']==pointer['display_board_sha256']==overlay['display_board_sha256']==sha(objects['git','output/data/week.json'])
 capture_binding=next(r for r in m['files']if r['kind']=='capture');wrapped=json.loads(gzip.decompress(objects['capture',capture_binding['path']]));c=wrapped['payload']
 assert sha(json.dumps(c,sort_keys=True,separators=(',',':')).encode())==wrapped['payload_sha256']==w['capture_payload_sha256']
 assert c['input_sha256']==sha(objects['git','output/data/week.json'])
 assert c['model']=='sleeper-matchup-classic-fg-identity-v1'
 assert len(c['rows'])==w['capture_forecast_rows']==2568
 assert all(r.get('raw_projection')is not None or r.get('adjusted_projection')is not None for r in c['rows'])
 assert len(board['games'])==15
 game_ids={g['id']for g in board['games']};assert {r['game_id']for r in c['rows']}<=game_ids
 assert len({r['game_id']for r in c['rows']})==15
 first=min(time(g['kickoff'])for g in board['games']);deadline=first-timedelta(minutes=90)
 picks=ranking['picks']['over']+ranking['picks']['under'];counts=collections.Counter(r['direction']for r in picks)
 assert counts=={'over':12,'under':12}and len({(r['game_id'],r['player_id'],r['key'],r['line'])for r in picks})==24
 assert len({r['game_id']for r in picks})==w['top_picks']['games']==12
 assert {r['forecast_source']for r in picks}=={'CURRENT_BASELINE'} and {r['product']for r in picks}=={'reference_point'}
 assert {r['model_version']for r in picks}=={c['model']}
 cap={(r['game_id'],r['player_id'],r['category']):r for r in c['rows']};assert len(cap)==2568
 for r in picks:
  s=cap[r['game_id'],r['player_id'],r['key']]
  assert r['line']==s['line'] and r['adj']==s['adjusted_projection']
  assert s['top_'+r['direction']]
  assert time(r['selected_at'])<=time(ranking['prepared_at'])<deadline
 original_top={(r['game_id'],r['player_id'],r['category'],d)for r in c['rows']for d in('over','under')if r['top_'+d]}
 assert original_top=={(r['game_id'],r['player_id'],r['key'],r['direction'])for r in picks}
 clocks=[time(c['forecast_generated_at']),time(c['captured_at']),time(w['git_persisted_at_utc']),time(ranking['prepared_at']),time(pointer['published_at'])]
 assert all(t<deadline for t in clocks)and clocks[0]<clocks[1]<clocks[2]
 assert sum(bool(r['source_timestamps_verified'])for r in c['rows'])==0
 old=a.repo/'reports/execution-closure-02/B/OWNER_CAPTURE_FAILURE_WITNESS_V1.json';interim=a.repo/'reports/execution-closure-02/B/CURRENT_OWNER_SERVED_READBACK_V2.json'
 assert json.loads(old.read_bytes())['run_id']==42108386576 and interim.exists()
 result=dict(state='PASS_INDEPENDENT_RETAINED_OWNER_CAPTURE_AND_SERVED_BYTES',
   source_witness_sha256=sha(wpath.read_bytes()),snapshot_map_sha256=sha((a.snapshots/'MAP.json').read_bytes()),
   production_commit=m['ref'],served_pairs=pairs,capture_file_sha256=capture_binding['sha256'],capture_payload_sha256=wrapped['payload_sha256'],
   forecast_rows=2568,forecast_games=15,point_outputs_present=2568,
   categories=dict(collections.Counter(r['category']for r in c['rows'])),
   top_picks=dict(over=12,under=12,total=24,games=12,source='CURRENT_BASELINE',product='reference_point',capture_membership_matches=True),
   first_kickoff_utc=first.isoformat(),first_t90_utc=deadline.isoformat(),clock_order_and_pre_t90=True,
   source_publication_verified_rows=0,overlay_state=overlay['state'],selected_research_rows=0,
   retained_prior_failure_sha256=sha(old.read_bytes()),retained_interim_readback_sha256=sha(interim.read_bytes()),
   owner_action_scope='Run42129928866/job127603655038 success is parent witness evidence; independent audit verified retained capture/output bytes, not an independently retained Actions API/log snapshot.',
   limits=['Served bytes equality only, no browser render claim','No authentication of football source or offer publication clocks','No B capture, new model admission or scientific/Top Picks qualification','2568 records include legacy fpts, not proven chart-PPR parity','Old failed42108386576 and interimV2 are preserved historical states'],
   network_calls=0,model_calls=0,new_scoring=0,production_writes=0)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(state=result['state'],sha256=sha(a.output.read_bytes()))))
if __name__=='__main__':main()
