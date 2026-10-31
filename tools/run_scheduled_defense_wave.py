"""Explicit preparation/execution; no scheduler and no implicit permission."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.scheduled_defense_wave import prepare,amend_prepared,run
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('action',choices=('prepare','amend','historical','future'))
for name in('public-root','private-root'):p.add_argument('--'+name,required=True,type=Path)
for name in('manifest','restoration-gate','worker-release','review','previous-public','previous-private'):p.add_argument('--'+name,type=Path)
a=vars(p.parse_args());action=a.pop('action')
if action=='prepare':
    for key in('restoration_gate','worker_release','review','previous_public','previous_private'):a.pop(key)
    if a['manifest']is None:p.error('prepare requires explicit private --manifest')
    result=prepare(**a)
elif action=='amend':
    for key in('manifest','restoration_gate','worker_release','review'):a.pop(key)
    if a['previous_public']is None or a['previous_private']is None:p.error('amend requires both explicit previous roots')
    result=amend_prepared(**a)
else:
    for key in('manifest','previous_public','previous_private'):a.pop(key)
    if any(a[key]is None for key in('restoration_gate','worker_release','review')):p.error('execution requires factual root restoration gate, separate worker release and independent review')
    result=run(phase=action,**a)
print(json.dumps(result,sort_keys=True))
