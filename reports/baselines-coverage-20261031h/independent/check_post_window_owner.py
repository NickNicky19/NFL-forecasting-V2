"""Read-only source bytes and clock metadata; no consumer/model/grade rerun."""
import argparse,collections,hashlib,json,sys
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];H=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from nfl_v2 import prop_evidence_metadata_v2 as lexical
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dt(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--private-root',type=Path,required=True);a=ap.parse_args();folder=H/'owner-status-20261031-late-v2';private=a.private_root/'baselines-coverage-20261031h-owner-status-late-v2'
    manifest=read(folder/'PUBLIC_ARTIFACT_MANIFEST.json')
    for b in manifest['artifacts']:
        p=folder/b['path'];assert p.stat().st_size==b['bytes']and sha(p)==b['sha256']
    p=read(folder/'FROZEN_PROTOCOL.json');acq=read(folder/'FRESH_SERVED_ACQUISITION.json');obs=read(folder/'OBSERVED_CAPTURE_AND_SERVED_STATUS.json');actions=read(folder/'PUBLIC_ACTIONS_AND_POLICY.json');ours=read(H/'independent/SERVED_CONSUMER_INDEPENDENT_REVIEW.json')
    assert sha(H/'owner-served/FRESH_SERVED_ACQUISITION.json')==p['prior_acquisition_sha256']
    assert sha(H/'owner-served/CONSUMER_EXECUTION_RESULT.json')==p['prior_consumer_execution_sha256']
    prior={r['kind']:r for r in read(H/'owner-served/FRESH_SERVED_ACQUISITION.json')['receipts']}
    for b in acq['receipts']:
        source=private/b['kind'];assert sha(source)==b['sha256']==prior[b['kind']]['sha256'];assert source.stat().st_size==b['bytes'];assert dt(p['registered_at_utc'])<=dt(b['request_started_utc'])<=dt(b['receipt_completed_utc']);assert b['equals_0338_snapshot']and b['status']==200
    assert sha(private/'payload.json')==ours['payload_sha256']and sha(private/'consumer.js')==ours['consumer_sha256']and sha(private/'app.js')==ours['app_sha256']
    # Parse strings/clocks only. Numeric prediction/statistic scalars are skipped lexically.
    allowed=set(obs['metadata_projection']['allowlist']);assert not({'forecast_value','actual','value','probability'}&allowed);old=lexical.ALLOWED;lexical.ALLOWED=allowed
    try:meta,skipped=lexical.project_metadata((private/'payload.json').read_text())
    finally:lexical.ALLOWED=old
    assert sha(Path(lexical.__file__))==obs['metadata_projection']['parser_sha256'];assert skipped==obs['metadata_projection']['skipped_scalar_values_not_decoded']
    now=dt(obs['checked_at_utc']);groups=collections.Counter();categories=collections.Counter();futuregames=set();issued=collections.Counter();persisted=collections.Counter();newmae=0
    for r in meta['rows']:
        kickoff=dt(r['kickoff_utc']);expiry=dt(r['valid_until_utc']);category=r['category'];categories[category]+=1;issued[r['issued_at']]+=1;persisted[r['persistence_completed_at']]+=1;newmae+=r['product']=='stat_point_mae_v2'
        assert dt(r['issued_at'])<=dt(r['persistence_completed_at'])<=dt(r['source_cutoff_utc'])<kickoff
        state='expired'if(now<kickoff and now>=expiry)or(now>=kickoff and expiry<kickoff)else'future'if now<kickoff else'frozen';groups[state]+=1
        if state=='future':futuregames.add(r['game_id'])
    assert len(meta['rows'])==obs['rows']==1945;assert groups==dict(future=1789,frozen=156);assert len(futuregames)==obs['existing_future_games']==13;assert issued==obs['issued_at_counts']and persisted==obs['persistence_completed_at_counts'];assert newmae==obs['new_MAE_profile_rows']==0
    assert sum(n for s,n in issued.items()if s.startswith('2026-10-31'))==obs['observed_Oct31_issued_rows']==0;assert sum(n for s,n in persisted.items()if s.startswith('2026-10-31'))==obs['observed_Oct31_persisted_rows']==0
    for r in obs['category_status']:assert categories[r['category']]==r['existing_served_rows']
    assert now>dt(actions['configured_parent_window']['UTC_end_exclusive']);assert now.utcoffset().total_seconds()==0;assert obs['clock_chicago'].startswith('2026-10-31T09:59:49')
    independent=read(H/'independent/POST_WINDOW_ACTIONS_INDEPENDENT_READBACK.json');assert len(independent['repositories'])==2
    for r in independent['repositories']:assert r['total_count']==0 and r['workflow_runs']==[]
    for repo in ('production','research'):assert actions[repo+'_new_run_total']==0 and actions[repo+'_new_runs']==[]
    report=dict(state='PASS_POST_WINDOW_BYTES_METADATA_CLOCKS_AND_INDEPENDENT_ACTIONS_READBACK',post_window_observed_at=obs['checked_at_utc'],independent_actions_readback_at=independent['observed_at_utc'],all_five_response_bytes_identical=True,prior_independent_consumer_receipt_sha256=sha(H/'independent/SERVED_CONSUMER_INDEPENDENT_REVIEW.json'),metadata_rows=1945,clock_classification=dict(groups),future_games=13,Oct31_issue_rows=0,Oct31_persistence_rows=0,new_MAE_profile_rows=0,configured_morning_window='ELAPSED',cause_of_absent_public_invocation='UNKNOWN',source_manifest_sha256=sha(folder/'PUBLIC_ARTIFACT_MANIFEST.json'),new_VM_runs=0,new_fits=0,new_inference=0,new_grades=0,NFL_outcomes_used=0,forecast_value_scalars_decoded=0,limits=['PublicservedbytesandActionsreadbackonly; unsharedownerlocal/privateworkunknown.','Noattestationofcurrentmodel/inputrestorationornewowneradmission.','Oct30failedrunreasonisnotadiagnosisofanunobservedOct31invocation.'])
    with (H/'independent/POST_WINDOW_OWNER_INDEPENDENT_REVIEW.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps(report))
if __name__=='__main__':main()
