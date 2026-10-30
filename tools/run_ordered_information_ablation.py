#!/usr/bin/env python3
"""Register/test/run finite C02 historical feature-block ablation only."""
import argparse,io,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2.ordered_information_ablation import prepare,run,write,sha
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('prepare','check','run'))
    for a in('source-root','control-public','control-private','chart-public','chart-private','public-root','private-root'):p.add_argument('--'+a,type=Path)
    p.add_argument('--sole-worker-confirmed',action='store_true');a=vars(p.parse_args());command=a.pop('command')
    if command=='check':
        stream=io.StringIO();r=unittest.TextTestRunner(stream=stream).run(unittest.defaultTestLoader.loadTestsFromName('tests.test_ordered_information_ablation'));receipt=dict(status='PASS'if r.wasSuccessful()else'FAIL',tests_run=r.testsRun,errors=len(r.errors),failures=len(r.failures),code_sha256=sha(ROOT/'nfl_v2/ordered_information_ablation.py'),test_code_sha256=sha(ROOT/'tests/test_ordered_information_ablation.py'),new_nfl_fits=0,new_forecasts=0,nfl_outcomes=0);write(a['public_root']/'SOFTWARE_CHECKS.json',receipt);print(stream.getvalue());print(json.dumps(receipt));sys.exit(0 if r.wasSuccessful()else 1)
    elif command=='prepare':a.pop('sole_worker_confirmed');r=prepare(**a);print(json.dumps({k:r[k]for k in('version','registered_at_utc','code_sha256','historical_query_cells','mechanism','budget')},indent=2))
    else:print(json.dumps(run(**a),indent=2))
