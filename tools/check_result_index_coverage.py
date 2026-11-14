#!/usr/bin/env python3
"""Require every registered result artifact to appear in the public test index."""
import hashlib,json,pathlib,sys,gzip,csv,io
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nfl_v2.result_index import validate_index
from tools.build_test_index_v3 import decode_shard
pointer=ROOT/'registries/CURRENT_RESULTS_INDEX.json'
p=ROOT/(json.loads(pointer.read_text())['manifest'] if pointer.exists() else 'reports/continuation-20261029/TEST_RESULTS_INDEX.json')
o=json.loads(p.read_text())
indexed=set();seen_ids=set();record_count=0
if o.get('schema_version')=='v2-sharded-results-index-v2':
 for shard in o['shards']:
  body=(ROOT/shard['path']).read_bytes()
  if len(body)!=shard['bytes'] or hashlib.sha256(body).hexdigest()!=shard['sha256']:raise SystemExit('Stale index shard: '+shard['path'])
  rows=decode_shard(ROOT,shard)
  if len(rows)!=shard['records']:raise SystemExit('Shard count mismatch')
  validate_index(rows)
  for r in rows:
   if r['test_id'] in seen_ids:raise SystemExit('Duplicate result across shards')
   seen_ids.add(r['test_id']);indexed.add(r['source_artifact']);record_count+=1
 if record_count!=o['record_count']:raise SystemExit('Index total count mismatch')
 csv_ids=set()
 for part in o.get('csv_parts',[]):
  body=(ROOT/part['path']).read_bytes()
  if len(body)!=part['bytes'] or hashlib.sha256(body).hexdigest()!=part['sha256']:raise SystemExit('Changed CSV delivery')
  if part.get('compression')=='gzip':body=gzip.decompress(body)
  elif part.get('compression')is not None:raise SystemExit('Unsupported CSV compression')
  n=0
  for row in csv.DictReader(io.StringIO(body.decode())):
   if row['test_id']in csv_ids:raise SystemExit('Duplicate CSV test ID')
   csv_ids.add(row['test_id']);n+=1
  if n!=part['rows']:raise SystemExit('CSV part row count mismatch')
 if csv_ids!=seen_ids:raise SystemExit('CSV and JSON test ID sets differ')
 base=o['baseline_checkpoint'];old_body=(ROOT/base['artifact']).read_bytes()
 if hashlib.sha256(old_body).hexdigest()!=base['sha256']:raise SystemExit('Prior checkpoint bytes changed')
 if not {r['test_id'] for r in json.loads(old_body)['records']} <= seen_ids:raise SystemExit('Prior test IDs lost')
 del old_body
 if o.get('previous_sharded_checkpoint'):
  previous=o['previous_sharded_checkpoint'];body=(ROOT/previous['artifact']).read_bytes()
  if hashlib.sha256(body).hexdigest()!=previous['sha256']:raise SystemExit('Previous manifest changed')
  current={s['path']:s for s in o['shards']}
  for s in json.loads(body)['shards']:
   if current.get(s['path'])!=s:raise SystemExit('Previous immutable shard replaced')
else:
 validate_index(o['records']);record_count=len(o['records'])
 indexed={r['source_artifact']for r in o['records']}
for source in o['input_manifests']:
 b=(ROOT/source['source_artifact']).read_bytes()
 if hashlib.sha256(b).hexdigest()!=source['sha256']:raise SystemExit('Stale result index: '+source['source_artifact'])
required=json.loads((ROOT/'registries/RESULT_ARTIFACTS.json').read_text())
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
print(json.dumps({'status':'PASS','indexed_records':record_count,'registered_artifacts':len(required),'scope':'streamed coverage/hashes; not additional NFL evidence'}))
