"""Seal or ROOT-release actual-side projections from retained grades only."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.prop_side_projection import prepare,run
p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','run'))
for key in('output','private-output'):p.add_argument('--'+key,required=True,type=Path)
for key in('graded','source-receipt','cohort-tags','universe','threshold-census'):p.add_argument('--'+key,type=Path)
p.add_argument('--root-execution-released',action='store_true');a=vars(p.parse_args());action=a.pop('action')
if action=='prepare':
    a.pop('root_execution_released')
    if any(a[k]is None for k in('graded','source_receipt','cohort_tags','universe','threshold_census')):p.error('prepare requires all retained input bindings')
    r=prepare(**a)
else:
    for k in('graded','source_receipt','cohort_tags','universe','threshold_census'):a.pop(k)
    r=run(**a)
print(json.dumps(r,sort_keys=True))
