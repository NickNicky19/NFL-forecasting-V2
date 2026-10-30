#!/usr/bin/env python3
"""Stream new public score versions onto the immutable accepted index.

Older records/shards are reused verbatim. At most one new source aggregate and
one bounded shard are decoded at a time; CSV output is also streamed.
"""
import collections
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nfl_v2.result_index import evaluation,software_receipt,validate_index
from tools.build_test_index import category_slug
from tools.build_test_index_v2 import current_flat,MAX_SHARD,encoded

PREVIOUS='reports/continuation-20261030b/results-index/INDEX_MANIFEST.json'
OUTPUT='reports/continuation-20261030c/results-index'


def sha(data):return hashlib.sha256(data).hexdigest()


def new_records(root,item,inputs):
    artifact=item['artifact'];body=(root/artifact).read_bytes();digest=sha(body);obj=json.loads(body)
    if item['state']=='SOFTWARE_VERIFIED':
        record=software_receipt(artifact,obj);record['source_artifact_sha256']=digest
        yield record
        inputs.append(dict(source_artifact=artifact,sha256=digest,rows=1,kind='software_verification'))
        return
    if not isinstance(obj,list):raise ValueError('aggregate score array required')
    dates={};annotations={};supersessions={}
    if item.get('supersession_mapping'):
        raw=(root/item['supersession_mapping']).read_bytes();mapping=json.loads(raw)
        supersessions={r['source_row_index']:r for r in mapping['rows'] if r['source_artifact']==artifact}
        if any(r['source_sha256']!=digest for r in supersessions.values()):raise ValueError('supersession source binding mismatch')
        inputs.append(dict(source_artifact=item['supersession_mapping'],sha256=sha(raw),rows=len(supersessions),kind='prediction_recipe_supersession_not_scoring_fix'))
    for field in ('dates_projection','comparison_annotations'):
        if not item.get(field):continue
        raw=(root/item[field]).read_bytes();projection=json.loads(raw)
        if projection['source_score_sha256']!=digest:raise ValueError('annotation source binding mismatch')
        if field=='dates_projection':
            dates={r['source_row_index']:r for r in projection['rows']}
            if set(dates)!=set(range(len(obj))):raise ValueError('date projection census mismatch')
        else:
            if projection.get('identity')=='source_row_index':
                annotations={r['source_row_index']:r['comparison']for r in projection['rows']}
                if set(annotations)!=set(range(len(obj))):raise ValueError('comparison projection census mismatch')
            else:
                by_id={r['source_record_id']:r['comparison']for r in projection['rows']}
                if len(by_id)!=len(obj)or set(by_id)!={r.get('record_id')for r in obj}:raise ValueError('comparison projection census mismatch')
                annotations={i:by_id[r['record_id']]for i,r in enumerate(obj)}
        inputs.append(dict(source_artifact=item[field],sha256=sha(raw),rows=len(projection['rows']),kind='source_bound_annotation_not_extra_evaluation'))
    for i,original in enumerate(obj):
        row=dict(original)
        if row.get('infinite_NLL',0):row['NLL']='Infinity'
        if row.get('infinite_log_losses',0):row['log_loss']='Infinity'
        date={k:row.get(k)for k in ('evaluation_seasons','evaluation_weeks')}
        if i in dates:date={k:dates[i][k]for k in date}
        record=evaluation(row,artifact,year_record=date)
        record['source_artifact_sha256']=digest;record['source_aggregate_fields']=original
        record['source_registry_kind']=item.get('kind')
        record['source_version_note']=item.get('version_note')
        invalid_mask=item.get('invalidated_shared_mask')
        if invalid_mask and original.get('fallback_view')==invalid_mask:
            record['score_version_state']='INVALIDATED_REQUESTED_SHARED_MASK_REFERENCE_ALIAS'
        if annotations:record['reporting_comparison']=annotations[i]
        if i in supersessions:
            s=supersessions[i]
            if s['source_test_id']!=record['test_id']:raise ValueError('supersession identity mismatch')
            record.update(score_version_state=s['state'],replacement_test_id=s['replacement_test_id'],supersession_mapping=item['supersession_mapping'])
        explicit_empty=(date.get('evaluation_weeks')==[]and('evaluation_weeks'in original or dates))
        if explicit_empty:
            if record['n']!=0:raise ValueError('empty scored dates with positive support')
            record.update(weeks=[],seasons=date.get('evaluation_seasons',[]),dates_missing_reason='zero_supported_rows_no_scored_weeks')
        if original.get('precision_counts'):
            for metric,p in original['precision_counts'].items():
                if metric not in(record['precision_metrics']or{}):continue
                if p['denominator']!=record['n']:raise ValueError('precision denominator differs from scored sample')
                if p['denominator']:
                    record['precision_metrics'][metric].update(numerator=p['numerator'],denominator=p['denominator'],numerator_provenance='retained_prediction_row_exact_counts_in_source_aggregate')
        if original.get('precision_counts_exact_grid'):
            for metric,p in original['precision_counts_exact_grid'].items():
                record['precision_metrics'][metric].update(numerator=p['numerator'],denominator=p['denominator'],numerator_provenance='independently_replayed_exact_integer_chart_grid_counts')
        if dates:record['evaluation_date_provenance']=dict(artifact=item['dates_projection'],source_row_index=i)
        validate_index([record]);yield record
    inputs.append(dict(source_artifact=artifact,sha256=digest,rows=len(obj),kind=item.get('kind',item['state'])))


def write(root=ROOT,previous=PREVIOUS,output=OUTPUT):
    root=Path(root);out=root/output
    if out.exists()and not(out/'INDEX_MANIFEST.json').exists():
        raise ValueError('incomplete index output exists; preserve failure and choose new output version')
    prior_body=(root/previous).read_bytes();prior=json.loads(prior_body)
    out.mkdir(parents=True,exist_ok=True)
    inputs=list(prior['input_manifests']);seen=set();shards=list(prior['shards']);kinds=collections.Counter();previous_n=0
    for part in shards:
        body=(root/part['path']).read_bytes()
        if len(body)!=part['bytes']or sha(body)!=part['sha256']:raise ValueError('previous immutable shard changed')
        records=json.loads(body);validate_index(records)
        if len(records)!=part['records']:raise ValueError('previous shard row count changed')
        for record in records:
            if record['test_id']in seen:raise ValueError('duplicate prior result ID')
            seen.add(record['test_id']);kinds[record['kind']]+=1;previous_n+=1
    if previous_n!=prior['record_count']:raise ValueError('previous manifest count mismatch')
    # Validate inherited source bytes, including annotations. A changed source
    # needs a new artifact/version, never silent replacement in this index.
    for item in inputs:
        if sha((root/item['source_artifact']).read_bytes())!=item['sha256']:raise ValueError('frozen input changed')
    existing={r['source_artifact']for r in inputs};buf=[];size=3;new_n=0
    def flush():
        nonlocal buf,size
        if not buf:return
        body=b'['+b','.join(buf)+b']\n';name=f'new-records-{len(shards):04d}.json';path=out/name
        path.write_bytes(body);shards.append(dict(path=str(path.relative_to(root)),sha256=sha(body),bytes=len(body),records=len(buf)))
        buf=[];size=3
    registry=json.loads((root/'registries/RESULT_ARTIFACTS.json').read_text())
    for item in registry:
        if item['artifact']in existing or item['state']not in {'SCORED','SOFTWARE_VERIFIED'}:continue
        for record in new_records(root,item,inputs):
            if record['test_id']in seen:raise ValueError('duplicate new evaluation identity')
            seen.add(record['test_id']);kinds[record['kind']]+=1;new_n+=1;body=encoded(record)
            if len(body)+3>MAX_SHARD:raise ValueError('single record exceeds shard bound')
            if size+len(body)+1>MAX_SHARD:flush()
            buf.append(body);size+=len(body)+1
        existing.add(item['artifact'])
    flush()
    active={Path(s['path']).name for s in shards if Path(s['path']).parent==Path(output)}
    for path in out.glob('new-records-*.json'):
        if path.name not in active:path.unlink()
    # CSVs and category views stream from retained shards; no complete record
    # list or complete flattened CSV is held in memory.
    cats=out/'categories';cats.mkdir(exist_ok=True);files={};writers={};cat_counts=collections.Counter();csv_parts=[]
    handle=None;writer=None;part_n=0;row_n=0;fieldnames=None
    try:
        for part in shards:
            for record in json.loads((root/part['path']).read_bytes()):
                row=current_flat(record)
                source=record.get('source_aggregate_fields')or{}
                for key in ('prediction_version','score_version_state','replacement_test_id','replaces_test_id','supersession_mapping','source_registry_kind','source_version_note'):
                    row[key]=record.get(key,source.get(key))
                if fieldnames is None:fieldnames=list(row)
                if writer is None or part_n==10000:
                    if handle:
                        handle.close();csv_parts[-1].update(rows=part_n,bytes=path.stat().st_size,sha256=sha(path.read_bytes()))
                    path=out/f'TEST_RESULTS_INDEX-{len(csv_parts):04d}.csv';handle=path.open('w',newline='');writer=csv.DictWriter(handle,fieldnames=fieldnames);writer.writeheader();part_n=0
                    csv_parts.append(dict(path=str(path.relative_to(root))))
                writer.writerow(row);part_n+=1;row_n+=1
                if record['kind']=='software_verification':continue
                target=record['category'];cat_counts[target]+=1
                if target not in writers:
                    f=(cats/(category_slug(target)+'.csv')).open('w',newline='');files[target]=f;writers[target]=csv.DictWriter(f,fieldnames=fieldnames);writers[target].writeheader()
                writers[target].writerow(row)
        if handle:
            handle.close();handle=None;csv_parts[-1].update(rows=part_n,bytes=path.stat().st_size,sha256=sha(path.read_bytes()))
    finally:
        if handle:handle.close()
        for f in files.values():f.close()
    if row_n!=previous_n+new_n:raise ValueError('streamed row count mismatch')
    manifest=dict(schema_version='v2-sharded-results-index-v2',record_unit=prior['record_unit'],
        baseline_checkpoint=prior['baseline_checkpoint'],previous_sharded_checkpoint=dict(artifact=previous,sha256=sha(prior_body),records=previous_n,unchanged=True),
        definitions=prior['definitions'],precision_definition=prior['precision_definition'],forbidden_accuracy_conversion=prior['forbidden_accuracy_conversion'],
        comparison_reporting=prior.get('comparison_reporting'),input_manifests=inputs,record_count=row_n,by_kind=dict(kinds),shards=shards,max_shard_bytes=MAX_SHARD,csv_parts=csv_parts,
        streaming_build=dict(previous_records_reused=previous_n,new_records=new_n,prior_shards_unchanged=True,ordering='prior immutable shards followed by new registered versions; CSVfilterbytestID/panel'),
        reader_contract='New reported/reproduced/reconstructed/future and software evidence retain distinct identities; a score view is not a fit or unique NFL observation.')
    (out/'INDEX_MANIFEST.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    (out/'CSV_FILES.md').write_text('# Filterable result parts\n\nAll parts share columns; retain one header when combining. Comparator error changes are candidate minus control; missing pairs stay unknown.\n\n'+'\n'.join(f"- [{Path(r['path']).name}]({Path(r['path']).name}): {r['rows']:,} records"for r in csv_parts)+'\n')
    (out/'README.md').write_text('# Permanent accuracy and error index\n\n'+f"{row_n:,} records; {row_n-kinds['software_verification']:,} evaluation views and {kinds['software_verification']:,} software receipts. All {previous_n:,} prior records and shards remain unchanged. Views are not distinct methods or NFL observations.\n\n"+'[CSV parts](CSV_FILES.md) · [JSON manifest](INDEX_MANIFEST.json) · [Accepted previous checkpoint](../../continuation-20261030b/results-index/README.md)\n\n'+'Every result retains method, history, product, dates, sample, population, native error, defined precision numerator/denominator, fallback/coverage, paired comparator/delta, uncertainty and source evidence. Unknowns are explicit. Scoring corrections, changed predictions and retrospective cohort projections remain distinct. MAE and relative error reductions are not generic percentage accuracy. Point, mean-MSE, proper-distribution and actual-offer rankings are separate.\n\n| Category | Views |\n|---|---:|\n'+'\n'.join(f'| [{target}](categories/{category_slug(target)}.csv) | {n:,} |'for target,n in sorted(cat_counts.items()))+'\n')
    return dict(status='PASS',records=row_n,new_records=new_n,reused_records=previous_n,shards=len(shards))


if __name__=='__main__':print(json.dumps(write()))
