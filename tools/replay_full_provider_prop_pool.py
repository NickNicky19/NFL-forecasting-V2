"""Prepare or execute the bounded original-snapshot full-threshold replay."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.full_provider_prop_replay import prepare,run
p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','run'))
for name in('public','private'):p.add_argument('--'+name,required=True,type=Path)
for name in('metadata','forward','reference','source-root','memberships'):p.add_argument('--'+name,type=Path)
p.add_argument('--execution-released',action='store_true');a=vars(p.parse_args());action=a.pop('action')
if action=='prepare':
    a.pop('execution_released')
    if any(a[k]is None for k in('metadata','forward','reference','source_root','memberships')):p.error('all source paths required')
    result=prepare(**a)
else:
    for k in('metadata','forward','reference','source_root','memberships'):a.pop(k)
    result=run(**a)
print(json.dumps(result,sort_keys=True))
