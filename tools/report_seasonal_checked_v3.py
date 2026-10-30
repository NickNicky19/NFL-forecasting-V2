#!/usr/bin/env python3
"""Validate self-created model hashes before running the frozen report tool."""
import argparse,json,runpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import seasonal_rolling as s
p=argparse.ArgumentParser();p.add_argument('--public',type=Path,required=True);p.add_argument('--private',type=Path,required=True);p.add_argument('--repair-public',type=Path);p.add_argument('--repair-private',type=Path);a=p.parse_args();protocol=json.loads((a.public/'FROZEN_PROTOCOL.json').read_text());run=json.loads((a.public/'RUN_RECEIPT.json').read_text());bound={};references=0
for file in sorted(a.public.glob('*-FIT.json')):
 r=json.loads(file.read_text());m=r.get('model')
 if not m:continue
 path=a.private/m['bundle_name'];references+=1
 if m['bundle_name'] in bound:
  if bound[m['bundle_name']]!=m['sha256']:raise ValueError('conflicting model bindings')
 else:
  if s.sha(path)!=m['sha256']:raise ValueError('self-created fitted model hash mismatch')
  bound[m['bundle_name']]=m['sha256']
actual={f.relative_to(a.private).as_posix() for f in (a.private/'models').glob('*.pickle.gz')}
if actual!=set(bound) or len(bound)!=run['retained_models']:raise ValueError('unbound or missing model; do not unpickle')
report=a.public.parent/'SEASONAL_REPORT_AMENDMENT_V3.json';amendment=json.loads(report.read_text());tool=Path(__file__).with_name('report_seasonal_rolling_v3.py')
if s.sha(tool)!=amendment['report_code_sha256'] or s.sha(Path(__file__).resolve().parents[1]/'nfl_v2/paired_uncertainty.py')!=amendment['shared_uncertainty_code_sha256']:raise ValueError('frozen report/helper bytes changed')
s.write(a.public/'SELF_CREATED_MODEL_HASH_REVIEW.json',dict(state='PASS_BEFORE_REPORT_PICKLE_READ',actual_completed_at=s.now(),wrapper_code_sha256=s.sha(__file__),source_protocol_sha256=s.sha(a.public/'FROZEN_PROTOCOL.json'),unique_self_created_models=len(bound),fit_receipt_model_references=references,all_private_model_files_bound=True,new_fit_calls=0))
runpy.run_path(str(tool),run_name='__main__')
