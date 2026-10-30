#!/usr/bin/env python3
"""Append registered aggregates to a bounded, sharded public result index.

The previous complete checkpoint stays immutable. No NFL rows or model fits are
read. Shards are a projection of evaluation views, never independent methods.
"""
import collections
import csv
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nfl_v2.result_index import evaluation,software_receipt,validate_index,DIAGNOSTIC_KIND,PRECISION
from tools.build_test_index import flat,category_slug

BASE='reports/continuation-20261029/TEST_RESULTS_INDEX.json'
OUTPUT='reports/continuation-20261030/results-index'
MAX_SHARD=12*1024*1024
CSV_OMIT_FIELDS={'source_aggregate_fields','diagnostic_provenance','game_count_provenance'}|{p+'_'+s for p in PRECISION for s in ('numerator_provenance','missing_reason')}
CORRECTION='reports/continuation-20261030/chart-grid-precision-correction-v1/SCORES.json'
CORRECTION_DIMS=('record_id','procedure_id','history_regime','policy_id','target','population','product_id','week','season','position','fallback_view','cohort_id')


def encoded(o):return json.dumps(o,separators=(',',':'),allow_nan=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest()


def current_flat(record):
    row=flat(record);source=record.get('source_aggregate_fields') or {}
    # Complete aggregate/provenance objects remain in JSON shards. CSVs retain
    # concise source pointers, explicit counts and metrics for practical filtering.
    for key in CSV_OMIT_FIELDS:row.pop(key,None)
    for key in ('run_id','procedure_family_id','cohort_id','information_policy','feature_memory_policy','training_population','source_vintage','scoring_version','correction_kind','precision_correction_artifact'):
        value=record.get(key,source.get(key))
        if value is None:value=source.get(key)
        row[key]=json.dumps(value,separators=(',',':')) if isinstance(value,(dict,list)) else value
    return row


def build(root=ROOT):
    baseline=(root/BASE).read_bytes();old=json.loads(baseline)
    records=list(old['records']);inputs=list(old['input_manifests'])
    existing={x['source_artifact'] for x in inputs}
    corrections={}
    if (root/CORRECTION).exists():
        for r in json.loads((root/CORRECTION).read_text()):
            corrections[(r['supersedes_score_artifact'],tuple(r['supersedes_source_identity'].get(k)for k in CORRECTION_DIMS))]=r
    for item in json.loads((root/'registries/RESULT_ARTIFACTS.json').read_text()):
        artifact=item['artifact']
        if artifact in existing or item['state'] not in {'SCORED','SOFTWARE_VERIFIED'}:continue
        body=(root/artifact).read_bytes();artifact_sha=sha(body);o=json.loads(body)
        if item['state']=='SOFTWARE_VERIFIED':
            r=software_receipt(artifact,o);r['source_artifact_sha256']=artifact_sha;records.append(r);n=1
        else:
            if not isinstance(o,list):raise ValueError('normalized aggregate result list required: '+artifact)
            date_rows={}
            if item.get('dates_projection'):
                date_body=(root/item['dates_projection']).read_bytes();projection=json.loads(date_body)
                if projection['source_score_sha256']!=artifact_sha:raise ValueError('date projection/source binding mismatch')
                date_rows={r['source_row_index']:r for r in projection['rows']}
                if set(date_rows)!=set(range(len(o))):raise ValueError('date projection view census mismatch')
                inputs.append(dict(source_artifact=item['dates_projection'],sha256=sha(date_body),rows=len(date_rows),kind='source_bound_date_annotation_not_extra_evaluation'))
            for i,original in enumerate(o):
                row=dict(original)
                if row.get('infinite_NLL',0):row['NLL']='Infinity'
                if row.get('infinite_log_losses',0):row['log_loss']='Infinity'
                dates={k:row.get(k) for k in ('evaluation_seasons','evaluation_weeks')}
                if i in date_rows:dates={k:date_rows[i][k] for k in dates}
                r=evaluation(row,artifact,year_record=dates);r['source_artifact_sha256']=artifact_sha
                r['source_aggregate_fields']=original
                if (artifact,tuple(original.get(k)for k in CORRECTION_DIMS)) in corrections:
                    r['accuracy_status']='superseded_float_chart_grid_precision'
                    r['accuracy_missing_reason']='Original floating tolerance rates retained; use the separately versioned exact0.02-grid correction, not a predictive improvement.'
                    r['precision_correction_artifact']=CORRECTION
                if original.get('precision_counts_exact_grid'):
                    for metric,p in original['precision_counts_exact_grid'].items():
                        r['precision_metrics'][metric].update(numerator=p['numerator'],denominator=p['denominator'],numerator_provenance='independently_replayed_exact_integer_chart_grid_counts')
                if date_rows:r['evaluation_date_provenance']=dict(artifact=item['dates_projection'],source_row_index=i)
                records.append(r)
            n=len(o)
        inputs.append(dict(source_artifact=artifact,sha256=artifact_sha,rows=n,kind=item.get('kind',item['state'])))
        existing.add(artifact)
    records=validate_index(sorted(records,key=lambda r:r['test_id']))
    if not {r['test_id'] for r in old['records']} <= {r['test_id'] for r in records}:
        raise ValueError('previous checkpoint IDs lost')
    for item in inputs:
        if sha((root/item['source_artifact']).read_bytes())!=item['sha256']:
            raise ValueError('source changed; preserve old version: '+item['source_artifact'])
    return old,records,inputs,sha(baseline)


def write(root=ROOT):
    old,records,inputs,base_hash=build(root);out=root/OUTPUT;out.mkdir(parents=True,exist_ok=True)
    shards=[];buf=[];size=2
    def flush():
        nonlocal buf,size
        if not buf:return
        body=b'['+b','.join(buf)+b']\n';name=f'records-{len(shards):04d}.json'
        (out/name).write_bytes(body)
        shards.append(dict(path=str((out/name).relative_to(root)),sha256=sha(body),bytes=len(body),records=len(buf)))
        buf=[];size=2
    for record in records:
        body=encoded(record)
        if len(body)+3>MAX_SHARD:raise ValueError('single aggregate exceeds shard limit')
        if size+len(body)+1>MAX_SHARD:flush()
        buf.append(body);size+=len(body)+1
    flush()
    # Remove only superseded generated shards after the new source projection succeeds.
    current={Path(s['path']).name for s in shards}
    for p in out.glob('records-*.json'):
        if p.name not in current:p.unlink()
    rows=[current_flat(r) for r in records]
    csv_parts=[]
    for first in range(0,len(rows),10000):
        name=f'TEST_RESULTS_INDEX-{len(csv_parts):04d}.csv';path=out/name
        with path.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows[first:first+10000])
        if path.stat().st_size>80*1024*1024:raise ValueError('CSV part exceeds bounded size')
        csv_parts.append(dict(path=str(path.relative_to(root)),sha256=sha(path.read_bytes()),rows=len(rows[first:first+10000]),bytes=path.stat().st_size))
    (out/'CSV_FILES.md').write_text('# Filterable CSV downloads\n\nEach part has the same columns; concatenate rows after retaining one header. Full source aggregates are in JSON shards.\n\n'+'\n'.join(f"- [{Path(p['path']).name}]({Path(p['path']).name}): {p['rows']:,} views" for p in csv_parts)+'\n')
    cats=out/'categories';cats.mkdir(exist_ok=True)
    summary=[]
    for target in sorted({r['category'] for r in records if r['kind']!='software_verification'}):
        selected=[r for r in records if r.get('category')==target];name=category_slug(target)+'.csv'
        with (cats/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(current_flat(r) for r in selected)
        summary.append(f'| [{target}](categories/{name}) | {len(selected):,} |')
    manifest=dict(schema_version='v2-sharded-results-index-v2',record_unit='evaluation/output view; not an independent learner, fit, game or player',
        baseline_checkpoint=dict(artifact=BASE,sha256=base_hash,records=len(old['records']),unchanged=True),
        definitions=old['definitions'],precision_definition=old['precision_definition'],
        forbidden_accuracy_conversion=old['forbidden_accuracy_conversion'],input_manifests=inputs,
        record_count=len(records),by_kind=dict(collections.Counter(r['kind'] for r in records)),shards=shards,
        max_shard_bytes=MAX_SHARD,csv_parts=csv_parts)
    (out/'INDEX_MANIFEST.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    lines=['# Permanent test results: current index','',
        f"{len(records):,} records: {sum(r['kind']!='software_verification' for r in records):,} evaluation views and {sum(r['kind']=='software_verification' for r in records)} software receipts. Views are not distinct methods or independent NFL samples.",
        '', '[Filterable CSV parts](CSV_FILES.md) · [Sharded JSON manifest](INDEX_MANIFEST.json) · [Previous immutable checkpoint](../../continuation-20261029/TEST_RESULTS_INDEX.md)',
        '', 'All earlier IDs and losses remain. New registrations retain procedure/history/product, exact panel/population and cohort, dates, denominators, native errors, defined tolerance accuracy, fallback/coverage, uncertainty and recoverable source links. Inspect source aggregate fields for exact cohort and source semantics. Unknowns remain null with reasons. Numeric errors do not become percentage accuracy. Software checks add no NFL observations.',
        '', 'Compare identical games, source vintages, information cutoffs, products and membership. Historical participant panels, original future captures, later partial-week captures and offered-price panels stay distinct. No hindsight-selected winner is credited as a live selector.',
        '', '| Category | Evaluation views |','|---|---:|',*summary,'',
        'Register each new immutable `SCORES.json` or software receipt in `registries/RESULT_ARTIFACTS.json`, run `python tools/build_test_index_v2.py`, and run `python tools/check_result_index_coverage.py`. Each JSON shard stays below12MiB; the old checkpoint is preserved.','']
    (out/'README.md').write_text('\n'.join(lines))
    return dict(status='PASS',records=len(records),shards=len(shards),previous_ids_retained=len(old['records']))


if __name__=='__main__':print(json.dumps(write()))
