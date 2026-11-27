"""Seal or ROOT-release the first immutable recorded-selection scorecard."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.recorded_prop_grading import prepare,run
p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','run'))
for key in('output','private-output'):p.add_argument('--'+key,required=True,type=Path)
p.add_argument('--joined',type=Path);p.add_argument('--expected-sha256');p.add_argument('--initial-protocol',type=Path)
p.add_argument('--root-execution-released',action='store_true')
a=vars(p.parse_args());action=a.pop('action')
if action=='prepare':
    a.pop('root_execution_released')
    if any(a[k]is None for k in('joined','expected_sha256','initial_protocol')):p.error('prepare requires explicit joined/hash/initial-protocol')
    result=prepare(**a)
else:
    for k in('joined','expected_sha256','initial_protocol'):a.pop(k)
    result=run(**a)
print(json.dumps(result,sort_keys=True))
