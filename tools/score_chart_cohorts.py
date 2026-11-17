#!/usr/bin/env python3
"""New saved-row chart cohort extension; no fitting or new forecasts."""
import argparse,io,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2.chart_cohorts import prepare,run,write,sha

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=('prepare','check','run'))
    for arg in('chart-public','chart-private','source-root','scorer-snapshot','public-output','private-output','scope'):p.add_argument('--'+arg,type=Path)
    a=vars(p.parse_args());command=a.pop('command')
    if command=='check':
        suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_chart_cohorts');stream=io.StringIO();r=unittest.TextTestRunner(stream=stream).run(suite)
        result=dict(status='PASS'if r.wasSuccessful()else'FAIL',tests_run=r.testsRun,failures=len(r.failures),errors=len(r.errors),code_sha256=sha(ROOT/'nfl_v2/chart_cohorts.py'),test_code_sha256=sha(ROOT/'tests/test_chart_cohorts.py'),new_fits=0,new_forecasts=0,nfl_outcomes=0)
        write(a['public_output']/'SOFTWARE_CHECKS.json',result);print(stream.getvalue());print(json.dumps(result));sys.exit(0 if r.wasSuccessful()else 1)
    elif command=='prepare':print(json.dumps(prepare(**a),indent=2))
    else:
        a.pop('scope');print(json.dumps(run(**a),indent=2))
