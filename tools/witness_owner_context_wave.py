"""Read-only current owner capture and served-byte witness; no publication."""
import argparse,collections,gzip,json,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from tools.witness_owner_audit_packet import sha,clock

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ref',required=True);ap.add_argument('--capture',required=True);ap.add_argument('--cache',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    a.cache.mkdir(parents=True,exist_ok=False);sources=[];pairs=[]
    raw='https://raw.githubusercontent.com/NickNicky19/nicks-expert-nfl-picks/'+a.ref+'/'
    served='https://nicknicky19.github.io/nicks-expert-nfl-picks/'
    def fetch(path,site=False):
        with urllib.request.urlopen((served+path.removeprefix('output/'))if site else raw+path,timeout=45)as response:b=response.read()
        name=('served-'if site else'git-')+str(len(sources))+'.bin';(a.cache/name).write_bytes(b);sources.append(dict(path=path,kind='served'if site else'git',sha256=sha(b),bytes=len(b),cache_member=name));return b
    def pair(path):
        b=fetch(path);v=fetch(path,True);pairs.append(dict(path=path,git_sha256=sha(b),served_sha256=sha(v),equal=b==v,bytes=len(b)));return json.loads(b)
    board=pair('output/data/week.json');meta=pair('output/data/meta.json');rp=pair('output/data/weekly-selected-rankings.json');rank=pair('output/data/'+rp['path']);op=pair('output/data/weekly-adaptive-overlay.json');overlay=pair('output/'+op['path'])
    stored=fetch(a.capture);wrapped=json.loads(gzip.decompress(stored));capture=wrapped['payload'];assert sha(json.dumps(capture,sort_keys=True,separators=(',',':')).encode())==wrapped['payload_sha256']
    assert capture['input_sha256']==pairs[0]['git_sha256'];assert rank['display_board_sha256']==pairs[0]['git_sha256']
    policy_bytes=fetch('config/weekly-derived-selected-policy-v8.json');policy=json.loads(policy_bytes)
    picks=rank['picks']['over']+rank['picks']['under'];assert len({(r['game_id'],r['player_id'],r['key'],r['line'],r['direction'])for r in picks})==len(picks)
    indexed={(r['game_id'],r['player_id'],r['category']):r for r in capture['rows']};assert len(indexed)==len(capture['rows']);matches=0;unresolved=0
    for pick in picks:
        row=indexed.get((pick['game_id'],pick['player_id'],pick['key']))
        if row and row.get('line')==pick['line']and row.get('adjusted_projection')==pick['adj']:matches+=1
        else:unresolved+=1
    captured=clock(capture['captured_at']);future=[g for g in board['games']if clock(g['kickoff'])>captured];started=[g for g in board['games']if clock(g['kickoff'])<=captured]
    futureids={str(g['game_id'])for g in future} if all('game_id'in g for g in future)else None
    result=dict(kind='READ_ONLY_OWNER_CAPTURE_SERVED_WITNESS_NOT_B_CAPTURE',at_utc=datetime.now(timezone.utc).isoformat(),production_commit=a.ref,
        capture_path=a.capture,capture_sha256=sha(stored),capture_payload_sha256=wrapped['payload_sha256'],clocks={k:capture.get(k)for k in('forecast_generated_at','captured_at')},
        pointer_published_at=rp['published_at'],selection_prepared_at=rank['prepared_at'],season=meta['season'],week=meta['week'],capture_schema=capture.get('schema_version'),model=capture.get('model'),
        forecast_rows=len(capture['rows']),games=len({r['game_id']for r in capture['rows']}),future_schedule_games_at_capture=len(future),already_started_games_at_capture=len(started),
        top_picks=dict(total=len(picks),sides=dict(collections.Counter(r['direction']for r in picks)),exact_current_capture_value_matches=matches,unresolved_matches=unresolved,
            frozen_proof_count=len(rank.get('frozen_proofs',[])),products=sorted({r.get('product')for r in picks}),sources=sorted({r.get('forecast_source')for r in picks})),
        overlay_state=overlay['state'],research_overlay_rows=len(overlay.get('rows',[])),fallback_counts=overlay.get('fallback_counts'),served_pairs=pairs,all_pairs_equal=all(r['equal']for r in pairs),
        policy=dict(path='config/weekly-derived-selected-policy-v8.json',sha256=sha(policy_bytes),registration_id=policy.get('registration_id'),bound_producer_source_sha=policy.get('publication_authority',{}).get('source_sha')),
        current_execution=meta.get('execution_model'),B_new_capture=0,B_dispatches=0,B_mutations=0,
        limits=['Bytes/persistence/current data consumer path checked; browser rendering not rerun.',
                'Late refresh cannot authenticate a new pregame issue for already-started games; prior frozen proofs are separate.',
                'Source publication/quote execution clocks remain unverified. No B candidate or Count A admission inferred.',
                'No new scheduler or workflow dispatch, no production changes.'])
    if a.out.exists():raise FileExistsError(a.out.name)
    a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');(a.cache/'MAP.json').write_text(json.dumps(dict(ref=a.ref,files=sources),indent=2)+'\n');print(json.dumps({k:result[k]for k in('production_commit','clocks','forecast_rows','games','overlay_state','research_overlay_rows','all_pairs_equal','top_picks')}))
if __name__=='__main__':main()
