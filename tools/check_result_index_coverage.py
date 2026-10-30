#!/usr/bin/env python3
"""Require every registered result artifact to appear in the public test index."""
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nfl_v2.result_index import validate_index
pointer=ROOT/'registries/CURRENT_RESULTS_INDEX.json'
p=ROOT/(json.loads(pointer.read_text())['manifest'] if pointer.exists() else 'reports/continuation-20261029/TEST_RESULTS_INDEX.json')
o=json.loads(p.read_text())
if o.get('schema_version')=='v2-sharded-results-index-v2':
 records=[]
 for shard in o['shards']:
  body=(ROOT/shard['path']).read_bytes()
  if len(body)!=shard['bytes'] or hashlib.sha256(body).hexdigest()!=shard['sha256']:raise SystemExit('Stale index shard: '+shard['path'])
  rows=json.loads(body)
  if len(rows)!=shard['records']:raise SystemExit('Shard count mismatch')
  records.extend(rows)
 if len(records)!=o['record_count']:raise SystemExit('Index total count mismatch')
 base=o['baseline_checkpoint'];old_body=(ROOT/base['artifact']).read_bytes()
 if hashlib.sha256(old_body).hexdigest()!=base['sha256']:raise SystemExit('Prior checkpoint bytes changed')
 prior=json.loads(old_body)
 if not {r['test_id'] for r in prior['records']} <= {r['test_id'] for r in records}:raise SystemExit('Prior test IDs lost')
 o['records']=records
validate_index(o['records'])
for source in o['input_manifests']:
 b=(ROOT/source['source_artifact']).read_bytes()
 if hashlib.sha256(b).hexdigest()!=source['sha256']:raise SystemExit('Stale result index: '+source['source_artifact'])
required=json.loads((ROOT/'registries/RESULT_ARTIFACTS.json').read_text())
indexed={r['source_artifact'] for r in o['records']}
for r in required:
 if r['state']=='SCORED' and r['artifact'] not in indexed:raise SystemExit('Unindexed scored result: '+r['artifact'])
 if r['state']=='FORECASTED_UNSCORED' and not r.get('pending_reason'):raise SystemExit('Forecast receipt lacks pending reason')
registered={r['artifact'] for r in required}
failed_empty=set()
for r in required:
 if r['state']=='FAILED_EMPTY_NO_EVALUATIONS':
  body=json.loads((ROOT/r['artifact']).read_text());receipt=json.loads((ROOT/r['failure_receipt']).read_text())
  if body!=[] or receipt.get('score_views')!=0 or receipt.get('state') not in {'PARTIAL_STOPPED','FAILED'}:
   raise SystemExit('Failed empty score registration is not bound to a genuine zero-score failed receipt')
  failed_empty.add(r['artifact'])
for artifact in (ROOT/'reports').rglob('SCORES.json'):
 relative=str(artifact.relative_to(ROOT))
 if relative in failed_empty:continue
 if relative not in registered or relative not in indexed:
  raise SystemExit('New canonical SCORES.json must be registered and indexed: '+relative)
for directory in (ROOT/'reports').glob('continuation-*'):
 for artifact in directory.rglob('*SCORES.json'):
  relative=str(artifact.relative_to(ROOT))
  if relative in failed_empty:continue
  if relative not in registered or relative not in indexed:
   raise SystemExit('Every continuation score artifact must be registered and indexed: '+relative)
print(json.dumps({'status':'PASS','indexed_records':len(o['records']),'registered_artifacts':len(required),'scope':'coverage/hashes; not additional NFL evidence'}))
