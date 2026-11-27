"""Verify the source-fallback amendment before calibration execution; no fit."""
import argparse,gzip,hashlib,json
from datetime import datetime,timezone
from pathlib import Path


def read(p):return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def differences(a,b,path=''):
    if type(a)!=type(b):return[(path,a,b)]
    if isinstance(a,dict):return[v for k in set(a)|set(b)for v in differences(a.get(k),b.get(k),path+'/'+str(k))]
    if isinstance(a,list):
        assert len(a)==len(b);return[v for i,(x,y)in enumerate(zip(a,b))for v in differences(x,y,path+'/'+str(i))]
    return[]if a==b else[(path,a,b)]


def run(repo,evidence,private,out):
    binding=read(out/'CURRENT_EXECUTION_BINDING.json');p=read(out/binding['protocol']);old=read(out/'FROZEN_PROTOCOL.json');assert sha(out/binding['protocol'])==binding['protocol_sha256'];assert sha(private/binding['inputs'])==binding['input_sha256']==p['input_rows_sha256'];assert sha(repo/'tools/run_b_predictive_improvement_01.py')==p['code_sha256'];assert sha(repo/'nfl_v2/exact_line_repair.py')==old['mechanism_sha256']==p['mechanism_sha256'];assert sha(out/'SOURCE_RUNNER_PREFIT_V1.py')==old['code_sha256']
    before=read(private/'PREPARED_INPUT_ROWS.json.gz');after=read(private/binding['inputs']);delta=differences(before,after);assert len(delta)==26 and all(path.startswith('/pass_td/evaluation/')and path.endswith('/fallback')and a=='NOT_RETAINED'and b=='none'for path,a,b in delta)
    assert old['mechanism']==p['mechanism']and old['budget']==p['budget']and old['panels']==p['panels']and old['closest_prior']==p['closest_prior']
    raw=read(evidence/'week8-grading-20261102l/WEEK8_ORIGINAL_LAW_THRESHOLD_ROWS_V2.json.gz')['rows'];reference={(r['game_id'],r['player_id'],float(r['line'])):r for r in raw if r['target']=='pass_td'and r['procedure_id']=='v2-c02-future-ordered-control-shadow-v1:c02_explicit_lag_block_removed:common-feature-memory'and r['history_regime']=='H-MULTI'}
    for r in after['pass_td']['evaluation']:
        if r['probabilities']is not None:
            q=reference[r['game_id'],r['player_id'],r['line']];assert q['fallback']==r['fallback']=='none'
        else:assert r['fallback']=='NOT_RETAINED'
    assert not(out/'RUN_RECEIPT.json').exists(),'This receipt must precede actual execution'
    receipt=dict(state='PREFIT_METADATA_AMENDMENT_PASS_NO_NUMERICAL_CHANGE',at_utc=datetime.now(timezone.utc).isoformat(),protocol_v1_sha256=sha(out/'FROZEN_PROTOCOL.json'),current_protocol_sha256=sha(out/binding['protocol']),current_runner_sha256=p['code_sha256'],current_module_sha256=p['mechanism_sha256'],original_input_sha256=sha(private/'PREPARED_INPUT_ROWS.json.gz'),current_input_sha256=sha(private/binding['inputs']),changed_metadata_fields=26,changed_field='pass_td.evaluation[*].fallback:NOT_RETAINED->none',unchanged='All probabilities, lines, outcomes, points, times, model-selection/gate/MAP settings and calibration sources.',source_captured_law_fallback_verified=26,source_unavailable_fallback_unknown=2,no_calibration_fit_called=True,source_snapshot_and_cache_preserved=True,original_prefit_scope_preserved=True,limits=['Earlier-source-prior control has separate reference metadata; this amendment verifies the26original captured football forecasts only.','Current source/query-transfer and historical-vintage limitations from the original independent preflight remain unchanged.'])
    (out/'INDEPENDENT_PREFIT_METADATA_QUALIFICATION_V2.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('repo',type=Path);p.add_argument('evidence',type=Path);p.add_argument('private',type=Path);p.add_argument('out',type=Path);a=p.parse_args();run(a.repo,a.evidence,a.private,a.out)
