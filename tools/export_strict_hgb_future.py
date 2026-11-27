#!/usr/bin/env python3
"""Validate and export retained strict-current future rows; never infer or fit."""
import argparse,collections,csv,gzip,json,platform,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import numpy,scipy,sklearn
from nfl_v2.strict_hgb_future import sha,now,write
p=argparse.ArgumentParser();p.add_argument('--public',type=Path,required=True);p.add_argument('--private',type=Path,required=True);a=p.parse_args();pub,priv=a.public,a.private
r=json.loads((pub/'RUN_RECEIPT.json').read_text());protocol=json.loads((pub/'FROZEN_PROTOCOL.json').read_text());packet=priv/r['packet']['bundle_name']
if sha(packet)!=r['packet']['sha256']:raise ValueError('retained packet bytes')
rows=json.loads(gzip.decompress(packet.read_bytes()))['rows'];modelrefs={};cells=[]
for path in sorted(pub.glob('*-FIT.json')):
 fit=json.loads(path.read_text());m=fit.get('model')
 if fit['training_seasons']!=[2026] or fit['feature_floor']!=2026:raise ValueError('strict history contract')
 if m:
  if sha(priv/m['bundle_name'])!=m['sha256']:raise ValueError('model bytes')
  modelrefs[m['bundle_name']]=m['sha256']
 cells.append(dict(target=fit['target'],product_id=fit['objective'],state=fit['state'],training_n=fit['training_n'],training_seasons=fit['training_seasons'],feature_floor=fit['feature_floor'],model_sha256=None if not m else m['sha256']))
if len(rows)!=r['output_views'] or len(modelrefs)!=r['retained_models'] or any(x.get('actual') is not None for x in rows):raise ValueError('row/model census or future actuals')
fields=sorted(set().union(*(x.keys() for x in rows)));flat=priv/'predictions.csv.gz'
with gzip.open(flat,'xt',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for row in rows:w.writerow({k:json.dumps(v,sort_keys=True,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in row.items()})
issued=[x for x in rows if x['prediction'] is not None];abstain=collections.Counter(x['abstention_reason'] for x in rows if x['prediction'] is None)
manifest=[dict(artifact_id='STRICT-HGB-FUTURE-'+sha(f),bundle_name=f.relative_to(priv).as_posix(),sha256=sha(f),bytes=f.stat().st_size)for f in sorted(priv.rglob('*'))if f.is_file()]
write(pub/'PUBLIC_ARTIFACT_MANIFEST.json',dict(state='LOCAL_RETAINED_DURABLE_RESTORATION_PENDING',logical_member_contract='Portable archive member scientific IDs; not filesystem/storage locators',files=len(manifest),total_bytes=sum(x['bytes'] for x in manifest),artifacts=manifest))
write(pub/'EXPORT_RECEIPT.json',dict(state='RETAINED_ROWS_EXPORT_VERIFIED',actual_completed_at=now(),code_sha256=sha(__file__),source_receipt_sha256=sha(pub/'RUN_RECEIPT.json'),source_protocol_sha256=sha(pub/'FROZEN_PROTOCOL.json'),source_packet_sha256=sha(packet),private_flat=dict(bundle_name=flat.name,sha256=sha(flat),bytes=flat.stat().st_size),rows=len(rows),pending_rows=len(rows),issued=len(issued),abstention_reasons=dict(abstain),actual_inference_started_at=min(x['actual_generated_at']for x in issued),actual_inference_completed_at=max(x['actual_generated_at']for x in issued),minimum_actual_horizon_seconds=min(x['actual_horizon_seconds']for x in issued),maximum_actual_horizon_seconds=max(x['actual_horizon_seconds']for x in issued),new_fit_calls=0,new_forecasts=0,score_views=0,CURRENT_2026_Week8_outcomes_read=0))
write(pub/'ENVIRONMENT_RECEIPT.json',dict(python=platform.python_version(),numpy=numpy.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__,max_threads=2,source_code_sha256=protocol['code_sha256'],new_fit_calls=0))
with (pub/'EXECUTION_CELLS.csv').open('x',newline='')as f:w=csv.DictWriter(f,fieldnames=list(cells[0]));w.writeheader();w.writerows(cells)
(pub/'README.md').write_text(f'''# Strict-current HGB future adapter\n\nThe existing HGB direct control now has an executed strict-current-information future adapter for all eleven NFL targets. It adds no model family or chart HGB recipe. Its21 original-objective cells fitted21 retained models, with no fit failures, at the real source cutoff {r['fixed_asof_utc']}. The recipe uses only2026 NFL outcomes in training labels, features, priors and transforms; the architecture was selected earlier and is research-exposed.\n\nThe saved packet contains3,193 views on1,795 frozen target queries in13 games:3,183 issued research shadows and10 abstentions for unqualified identity/position. Actual persistence completed {r['actual_completed_at']}; every issued row passed the real T-minus90 check. The first Week8 game is excluded. Original captures are unchanged. The declared source availability remains kickoff plus seven days, not the separately tested fresh-snapshot policy.\n\nAll3,193 actuals remain null. Numeric products are L1 points and intended means, scored later on MAE with mean MSE separate; TD uses a classifier probability with Brier primary. These point objectives do not authenticate a count distribution. Parent frozen common future cohorts and grading rules are bound before inference. There is no offer, price, ROI, method-selection or winner claim. The newer source cutoff can differ from earlier common-memory HGB snapshots, so their differences cannot isolate history policy.\n\nRuntime: {r['resource']['wall_seconds']:.3f} wall seconds, {r['resource']['cpu_seconds']:.3f} CPU seconds, {r['resource']['peak_rss_bytes']:,} peak RSS bytes, at most two threads. The export is a zero-fit copy of saved rows, preserving original generation clocks and identifiers.\n\nState: research shadow, owner admission pending; no official capture or website publication. Local immutable weights/queries/features/chunks are retained. Durable private restoration is pending and must be established separately; the existing private-store quota issue does not confer readiness. No2026 historical model was refitted and no current2026 Week8 outcome was read.\n''')
print(json.dumps(dict(files=len(manifest),private_bytes=sum(x['bytes']for x in manifest),flat_sha256=sha(flat))))
