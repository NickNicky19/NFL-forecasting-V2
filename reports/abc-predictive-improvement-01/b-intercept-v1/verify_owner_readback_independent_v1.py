"""Bounded public payload readback; no writes to production or retained raw picks."""
import argparse,collections,hashlib,json,urllib.request
from datetime import datetime,timezone
from pathlib import Path
def fetch(url):
    request=urllib.request.Request(url,headers={'User-Agent':'NFL-V2-independent-read-only-audit','Accept':'application/vnd.github+json' if 'api.github.com' in url else 'application/json'})
    with urllib.request.urlopen(request,timeout=40)as r:return r.read()
def digest(b):return hashlib.sha256(b).hexdigest()
def run(out):
    source=json.loads((out/'CURRENT_OWNER_STATUS.json').read_text());counts=json.loads((out/'CURRENT_OWNER_SELECTION_COUNTS.json').read_text());ref=source['production_ref'];checks=[];packet=None
    for p in source['checks']:
        github='https://raw.githubusercontent.com/NickNicky19/nicks-expert-nfl-picks/'+ref+'/'+p['payload_path'];served='https://nicknicky19.github.io/nicks-expert-nfl-picks/'+p['payload_path'].removeprefix('output/')
        gb=fetch(github);sb=fetch(served);assert gb==sb and digest(gb)==p['payload_sha256']and len(gb)==p['payload_bytes'];d=json.loads(gb)
        if p['product']=='adaptive_overlay':assert d['state']=='DISABLED_USE_R0'and d['rows']==[]and d['frozen_rows']==[]
        else:packet=d
        checks.append(dict(product=p['product'],immutable_GitHub_url=github,served_url=served,sha256=digest(gb),bytes=len(gb),GitHub_served_bytes_equal=True,readback_at_utc=datetime.now(timezone.utc).isoformat()))
    assert packet is not None and set(packet['picks'])=={'over','under'};sidecounts={k:len(v)for k,v in packet['picks'].items()};picks=sum(packet['picks'].values(),[]);assert sidecounts=={'over':12,'under':12}==counts['selection_counts'];assert len({r['game_id']for r in picks})==counts['unique_games']==11
    assert {r['forecast_source']for r in picks}=={'CURRENT_BASELINE'}and {r['model_version']for r in picks}==set(counts['model_versions']);assert packet['prepared_at']==counts['prepared_at']and packet['policy']==counts['policy'];assert packet['frozen_proofs']==[]and packet['season']==2026 and packet['week']==9
    action_url='https://api.github.com/repos/NickNicky19/nicks-expert-nfl-picks/actions/runs/41909390038';action=json.loads(fetch(action_url));assert action['id']==41909390038 and action['name']=='Hourly update'and action['event']=='schedule'and action['status']=='completed'and action['conclusion']=='success'and action['created_at']=='2026-11-04T20:44:02Z'and action['updated_at']=='2026-11-04T20:45:36Z'
    result=dict(state='PASS_INDEPENDENT_CURRENT_OWNER_PUBLIC_PAYLOAD_READBACK',at_utc=datetime.now(timezone.utc).isoformat(),production_ref=ref,source_status_receipt_sha256=digest((out/'CURRENT_OWNER_STATUS.json').read_bytes()),source_count_receipt_sha256=digest((out/'CURRENT_OWNER_SELECTION_COUNTS.json').read_bytes()),verification_code_sha256=digest(Path(__file__).read_bytes()),checks=checks,season=2026,week=9,actual_persisted_prepared_at=packet['prepared_at'],side_counts=sidecounts,total_selections=len(picks),unique_games=11,forecast_sources=['CURRENT_BASELINE'],model_versions=counts['model_versions'],overlay_state='DISABLED_USE_R0',adaptive_overlay_rows=0,owner_action=dict(id=action['id'],name=action['name'],event=action['event'],status=action['status'],conclusion=action['conclusion'],created_at=action['created_at'],updated_at=action['updated_at'],head_sha=action['head_sha']),new_B_repair_captured_or_admitted=False,production_writes=0,new_scheduler=0,limits=['Bounded readback authenticates equal immutable GitHub and presently served payload bytes, counts and actual owner workflow result; it does not inspect browser rendering or claim a future packet remains unchanged.','Classic reference selections are not an admitted adaptive-overlay model or the new B probability repair.','Twelve Overs plus twelve Unders are twenty-four selections; no top-twelve combined claim.','No raw player-level packet retained or published by this verification.'])
    (out/'INDEPENDENT_CURRENT_OWNER_READBACK_V1.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);a=p.parse_args();run(a.out)
