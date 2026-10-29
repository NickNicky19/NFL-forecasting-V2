#!/usr/bin/env python3
"""Require every registered result artifact to appear in the public test index."""
import hashlib,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nfl_v2.result_index import validate_index
p=ROOT/'reports/continuation-20261029/TEST_RESULTS_INDEX.json';o=json.loads(p.read_text());validate_index(o['records'])
for source in o['input_manifests']:
 b=(ROOT/source['source_artifact']).read_bytes()
 if hashlib.sha256(b).hexdigest()!=source['sha256']:raise SystemExit('Stale result index: '+source['source_artifact'])
required=json.loads((ROOT/'registries/RESULT_ARTIFACTS.json').read_text())
indexed={r['source_artifact'] for r in o['records']}
for r in required:
 if r['state']=='SCORED' and r['artifact'] not in indexed:raise SystemExit('Unindexed scored result: '+r['artifact'])
 if r['state']=='FORECASTED_UNSCORED' and not r.get('pending_reason'):raise SystemExit('Forecast receipt lacks pending reason')
registered={r['artifact'] for r in required}
for artifact in (ROOT/'reports').rglob('SCORES.json'):
 relative=str(artifact.relative_to(ROOT))
 if relative not in registered or relative not in indexed:
  raise SystemExit('New canonical SCORES.json must be registered and indexed: '+relative)
print(json.dumps({'status':'PASS','indexed_records':len(o['records']),'registered_artifacts':len(required),'scope':'coverage/hashes; not additional NFL evidence'}))
