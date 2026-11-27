"""Explicit preparation/execution; no scheduler and no implicit permission."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.scheduled_defense_wave import prepare,run
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('action',choices=('prepare','historical','future'))
for name in('public-root','private-root'):p.add_argument('--'+name,required=True,type=Path)
for name in('manifest','restoration-gate','worker-release','review'):p.add_argument('--'+name,type=Path)
a=vars(p.parse_args());action=a.pop('action')
if action=='prepare':
    for key in('restoration_gate','worker_release','review'):a.pop(key)
    if a['manifest']is None:p.error('prepare requires explicit private --manifest')
    result=prepare(**a)
else:
    a.pop('manifest')
    if any(a[key]is None for key in('restoration_gate','worker_release','review')):p.error('execution requires factual root restoration gate, separate worker release and independent review')
    result=run(phase=action,**a)
print(json.dumps(result,sort_keys=True))
