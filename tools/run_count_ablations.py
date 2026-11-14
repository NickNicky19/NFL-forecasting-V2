#!/usr/bin/env python3
"""Prepare/check/run new count ablations; root permits sole fit worker only."""
import argparse,io,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2.count_ablations import prepare,run,sha,immutable_json,now

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','check','run'])
    p.add_argument('--source-root',type=Path);p.add_argument('--public-root',type=Path,required=True);p.add_argument('--private-root',type=Path)
    for arg in ('old-protocol','shared-queries','shared-protocol','shared-execution'):p.add_argument('--'+arg,type=Path)
    p.add_argument('--source-artifact-id');p.add_argument('--sole-worker-confirmed',action='store_true');a=vars(p.parse_args());command=a.pop('command')
    if command=='check':
        suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_count_ablations');stream=io.StringIO();r=unittest.TextTestRunner(stream=stream).run(suite)
        module=ROOT/'nfl_v2/count_ablations.py';receipt=dict(status='PASS'if r.wasSuccessful()else'FAIL',tests_run=r.testsRun,failures=len(r.failures),errors=len(r.errors),code_sha256=sha(module),test_code_sha256=sha(ROOT/'tests/test_count_ablations.py'),completed_at_utc=now(),nfl_outcomes=0,nfl_fits=0)
        immutable_json(a['public_root']/'SOFTWARE_CHECKS.json',receipt);print(stream.getvalue());print(json.dumps(receipt,indent=2));sys.exit(0 if r.wasSuccessful()else 1)
    elif command=='prepare':
        a.pop('sole_worker_confirmed');missing=[k for k,v in a.items()if v is None]
        if missing:p.error('prepare requires '+','.join('--'+k.replace('_','-')for k in missing))
        result=prepare(**a);print(json.dumps({k:result[k]for k in ('version','registered_at_utc','shared_week8_feature_origin_utc','historical_query_cells','future_query_cells','future_games','expected_output_rows','budget')},indent=2))
    else:
        if a['source_root']is None or a['private_root']is None:p.error('run requires source/private roots')
        print(json.dumps(run(**{k:a[k]for k in ('source_root','public_root','private_root','sole_worker_confirmed')}),indent=2))
