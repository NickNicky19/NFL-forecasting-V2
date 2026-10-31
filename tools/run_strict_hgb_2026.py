#!/usr/bin/env python3
"""CLI for metadata readiness, retention-gated freeze, and reviewed execution."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import strict_hgb_2026_runner as r
p=argparse.ArgumentParser();p.add_argument('action',choices=('readiness','freeze','execute'))
for n in('source-root','public','private','prepared-public','prepared-private','retention-gate','repository','software-checks','prefit-review'):p.add_argument('--'+n,type=Path)
p.add_argument('--sole-fit-worker',action='store_true');a=p.parse_args();d=vars(a);action=d.pop('action')
required={'readiness':('source_root','prepared_public','prepared_private'),'freeze':('source_root','prepared_public','prepared_private','public','private','retention_gate','repository','software_checks'),'execute':('source_root','public','private','retention_gate','repository','prefit_review')}
missing=[n for n in required[action]if d[n]is None]
if missing:p.error('required: '+', '.join('--'+n.replace('_','-')for n in missing))
if action=='readiness':result=r.readiness(**{k:d[k]for k in('prepared_public','prepared_private','source_root','retention_gate','repository')})
elif action=='freeze':result=r.freeze(**{k:d[k]for k in required[action]})
else:result=r.execute(**{k:d[k]for k in required[action]},sole_fit_worker=a.sole_fit_worker)
print(json.dumps(result))
