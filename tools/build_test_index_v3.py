#!/usr/bin/env python3
"""Stream new public score versions onto the immutable accepted index.

Older records/shards are reused verbatim. At most one new source aggregate and
one bounded shard are decoded at a time; CSV output is also streamed.
"""
import collections
import csv
import hashlib
import gzip
import io
import math
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nfl_v2.result_index import evaluation,software_receipt,validate_index,DEFINITIONS
from tools.build_test_index import category_slug
from tools.build_test_index_v2 import current_flat,MAX_SHARD,encoded

PREVIOUS='reports/continuation-20261030b/results-index/INDEX_MANIFEST.json'
OUTPUT='reports/continuation-20261030c/results-index'


def sha(data):return hashlib.sha256(data).hexdigest()


def decode_shard(root,part):
    body=(Path(root)/part['path']).read_bytes()
    if len(body)!=part['bytes'] or sha(body)!=part['sha256']:raise ValueError('immutable shard changed')
    if part.get('compression')=='gzip':
        body=gzip.decompress(body)
        if len(body)!=part['uncompressed_bytes'] or sha(body)!=part['uncompressed_sha256']:raise ValueError('uncompressed shard changed')
    elif part.get('compression') is not None:raise ValueError('unsupported shard compression')
    return json.loads(body)


def validate_probability_outer_coverage(record,coverage):
    if record.get('kind')!='prop_threshold_probability_evaluation':raise ValueError('outer probability coverage on other product')
    keys=('outer_offer_universe','matched_candidate_admitted_law_rows','candidate_full_qualified_mask_n','qualified_mask_n')
    if any(type(coverage.get(k))is not int or coverage[k]<0 for k in keys):raise ValueError('invalid probability coverage counts')
    outer,admitted,full,n=(coverage[k]for k in keys)
    if n!=record['n'] or not 0<=n<=full<=admitted<=outer:raise ValueError('probability mask exceeds full coverage')
    rate=coverage.get('mask_over_outer_offer_fraction')
    if (rate is not None if not outer else not isinstance(rate,(float,int))or not math.isfinite(rate)or abs(rate-n/outer)>1e-12):raise ValueError('probability outer fraction mismatch')
    return coverage


def apply_source_vintage_annotation(row, annotation):
    """Correct bound point/selection metadata without changing saved scores."""
    value = annotation.get('source_vintage')
    if value is None:
        return row
    if row.get('record_kind') not in {'prop_selection_evaluation', 'forecast_evaluation_view'}:
        raise ValueError('source-vintage correction requires point/selection record')
    if annotation.get('correction_kind') != 'SOURCE_VINTAGE_METADATA_ONLY':
        raise ValueError('source-vintage correction kind missing')
    if annotation.get('original_source_vintage') != row.get('source_vintage'):
        raise ValueError('source-vintage correction original mismatch')
    if not isinstance(value, str) or not value.strip():
        raise ValueError('source-vintage correction must supply nonempty label')
    return dict(row, source_vintage=value)


def validate_diagnostic_context_coverage(record, contexts):
    """Keep complete-source availability distinct from a paired score mask."""
    if record.get('kind') not in {'forecast_evaluation_view', 'prop_selection_evaluation'}:
        raise ValueError('diagnostic coverage requires point/selection record')
    if not isinstance(contexts, list) or not contexts:
        raise ValueError('diagnostic coverage contexts missing')
    expected = (record['forecast_or_offered_rows'] if record['kind'] == 'prop_selection_evaluation' else record['n'])
    for context in contexts:
        keys = ('source_offer_universe', 'source_available_points', 'mask_points',
                'context_outer_opportunities', 'scored_or_selected_n')
        if any(type(context.get(key)) is not int or context[key] < 0 for key in keys):
            raise ValueError('invalid diagnostic coverage counts')
        outer, available, mask, conditional, selected = (context[key] for key in keys)
        if not (selected == expected and selected <= mask <= available <= outer and mask <= conditional <= outer):
            raise ValueError('diagnostic coverage exceeds its declared scope')
        for field, denominator in (('fraction_of_source', outer), ('fraction_of_context', conditional)):
            value = context.get(field)
            if denominator:
                if type(value) not in (int, float) or not math.isfinite(value) or abs(value-selected/denominator) > 1e-12:
                    raise ValueError('diagnostic coverage fraction mismatch')
            elif value is not None:
                raise ValueError('empty diagnostic coverage denominator requires null')
        if not isinstance(context.get('context'), str) or not context['context']:
            raise ValueError('diagnostic context identity missing')
    return contexts


def csv_handle(path,compressed):
    return io.TextIOWrapper(gzip.GzipFile(filename=str(path),mode='wb',mtime=0),encoding='utf-8',newline='') if compressed else path.open('w',newline='')


def new_records(root,item,inputs):
    artifact=item['artifact'];body=(root/artifact).read_bytes();digest=sha(body);obj=json.loads(body)
    if item['state']=='SOFTWARE_VERIFIED':
        record=software_receipt(artifact,obj);record['source_artifact_sha256']=digest
        yield record
        inputs.append(dict(source_artifact=artifact,sha256=digest,rows=1,kind='software_verification'))
        return
    if not isinstance(obj,list):raise ValueError('aggregate score array required')
    dates={};annotations={};supersessions={}
    common_fields={}
    row_metadata={};reporting={}
    if item.get('reporting_annotations'):
        raw=(root/item['reporting_annotations']).read_bytes();projection=json.loads(raw)
        if projection['source_score_sha256']!=digest:raise ValueError('reporting annotation source mismatch')
        reporting={r['source_row_index']:r for r in projection['rows']}
        if len(reporting)!=len(projection['rows']):raise ValueError('duplicate reporting annotation row')
        inputs.append(dict(source_artifact=item['reporting_annotations'],sha256=sha(raw),rows=len(reporting),kind='source_bound_reporting_correction_no_prediction_change'))
    if item.get('selection_contract_projection'):
        raw=(root/item['selection_contract_projection']).read_bytes();projection=json.loads(raw)
        if projection['source_score_sha256']!=digest:raise ValueError('selection contract source binding mismatch')
        common_fields=projection['common_fields']
        if set(common_fields)-{'statistic_period','season_type','period_provenance'}:
            raise ValueError('unsupported common contract projection')
        inputs.append(dict(source_artifact=item['selection_contract_projection'],sha256=sha(raw),rows=len(obj),kind='source_bound_selection_contract_annotation'))
    if item.get('selection_metadata_projection'):
        raw=(root/item['selection_metadata_projection']).read_bytes();projection=json.loads(raw)
        if projection['source_score_sha256']!=digest:raise ValueError('selection metadata source mismatch')
        row_metadata={r['record_id']:r for r in projection['rows']}
        if len(row_metadata)!=len(obj)or set(row_metadata)!={r['record_id']for r in obj}:
            raise ValueError('selection metadata coverage mismatch')
        inputs.append(dict(source_artifact=item['selection_metadata_projection'],sha256=sha(raw),rows=len(obj),kind='source_bound_selection_view_metadata'))
    if item.get('supersession_mapping'):
        raw=(root/item['supersession_mapping']).read_bytes();mapping=json.loads(raw)
        supersessions={r['source_row_index']:r for r in mapping['rows'] if r['source_artifact']==artifact}
        if any(r['source_sha256']!=digest for r in supersessions.values()):raise ValueError('supersession source binding mismatch')
        mapping_kind=('precision_scoring_supersession_no_prediction_change'
                      if mapping.get('mapping_kind')=='SCORING_PRECISION_ONLY'
                      else 'prediction_recipe_supersession_not_scoring_fix')
        inputs.append(dict(source_artifact=item['supersession_mapping'],sha256=sha(raw),rows=len(supersessions),kind=mapping_kind))
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
    if item.get('sparse_comparison_annotations'):
        raw=(root/item['sparse_comparison_annotations']).read_bytes();projection=json.loads(raw)
        sparse=[r for r in projection if r['source_artifact']==artifact]
        for r in sparse:
            i=r['source_row_index']
            if r['source_artifact_sha256']!=digest or obj[i]['record_id']!=r['record_id']:
                raise ValueError('sparse comparison source identity mismatch')
            value=dict(r['comparison'])
            if value.pop('status')!='EXACT_FULL_MASK_PAIRED_ACTUAL_LINE_PROPER_SCORE':
                raise ValueError('unsupported sparse comparison mask')
            value['status']='PAIRED_RETAINED_ROWS';value['membership_sha256']=r['membership_sha256']
            if i in annotations:raise ValueError('comparison metadata collision')
            annotations[i]=value
        inputs.append(dict(source_artifact=item['sparse_comparison_annotations'],sha256=sha(raw),rows=len(sparse),kind='source_bound_sparse_paired_comparison'))
    for i,original in enumerate(obj):
        row=dict(original)
        if i in reporting:
            addition=reporting[i]
            if addition['record_id']!=original.get('record_id'):raise ValueError('reporting source record mismatch')
            row=apply_source_vintage_annotation(row,addition)
            if addition.get('precision_counts') is not None:row['precision_counts']=addition['precision_counts']
            if addition.get('law_origin_counts') is not None:
                counts=addition['law_origin_counts']
                if counts['actual_source_fallback_count']+counts['actual_source_learned_count']!=counts['actual_source_eligible_count']:
                    raise ValueError('law origin count partition mismatch')
                row.update(fallback_rows=counts['actual_source_fallback_count'],scored_fallback_rows=counts['actual_source_scored_fallback_count'])
                if row.get('record_kind')=='prop_selection_evaluation':
                    stats=dict(row['selection_metrics']);stats['fallback_issued']=counts['actual_source_fallback_count'];row['selection_metrics']=stats
            if addition.get('denominators') is not None:
                if row.get('record_kind')!='prop_selection_evaluation':raise ValueError('selection denominator metadata on other product')
                d=addition['denominators']
                if d['eligible_pool']!=d['admitted_forecast_opportunities']+d['unavailable_forecast_opportunities'] or d['admitted_forecast_opportunities']!=d['admitted_rule_abstentions']+d['selected_any_side_in_full_pool']:
                    raise ValueError('disjoint forecast/abstention coverage mismatch')
                stats=dict(row['selection_metrics']);stats.update({k:d[k]for k in ('admitted_forecast_opportunities','unavailable_forecast_opportunities','admitted_rule_abstentions')})
                stats['abstentions']=d['admitted_rule_abstentions'];stats['abstention_reporting_note']=d['original_abstention_field_semantics'];row['selection_metrics']=stats
            if addition.get('probability_scores') is not None:
                if row.get('record_kind')!='prop_selection_evaluation':raise ValueError('selected-pool probability metadata on other product')
                p=addition['probability_scores']
                supported=row['selection_metrics']['denominators'].get('supported_threshold_outcomes',row['n']+row['selection_metrics'].get('PUSH',0))
                if p['conditioning']!='MODELED_APPEARANCE' or p['score_contract']!='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1' or p['n']!=supported:
                    raise ValueError('selected probability conditioning/support mismatch')
                stats=dict(row['selection_metrics']);stats['probability_scores']=p;row['selection_metrics']=stats
                row.update(brier=p['brier'],log_loss=p['log_loss'],infinite_log_losses=p['infinite_log_losses'],probability_conditioning=p['conditioning'])
        if common_fields:
            if row.get('record_kind')!='prop_selection_evaluation':raise ValueError('selection contract on numeric record')
            row.update(common_fields)
        if row_metadata:
            supplement=dict(row_metadata[original['record_id']]);supplement.pop('record_id')
            for key in ('query_membership_sha256','unique_games','season_alias_of_week_view'):
                if key in supplement:
                    if supplement.pop(key)!=original.get(key):raise ValueError('selection supplement changed a source identity/count')
            if supplement.pop('source_record_id',original['record_id'])!=original['record_id']:
                raise ValueError('selection source record mismatch')
            if set(supplement)-{'alias_of_record_id','unique_players','unique_player_games','unique_weeks',
                    'decided_unique_games','decided_unique_player_games','decided_unique_players',
                    'decided_week_count','registered_week_count','registered_weeks','selected_week_count',
                    'overtime','season_type','statistic_period'}:
                raise ValueError('unsupported selection metadata field')
            row.update(supplement)
        if row.get('infinite_NLL',0):row['NLL']='Infinity'
        if row.get('infinite_log_losses',0):row['log_loss']='Infinity'
        date={k:row.get(k)for k in ('evaluation_seasons','evaluation_weeks')}
        if i in dates:date={k:dates[i][k]for k in date}
        record=evaluation(row,artifact,year_record=date)
        record['source_artifact_sha256']=digest;record['source_aggregate_fields']=original
        record['source_registry_kind']=item.get('kind')
        record['source_version_note']=item.get('version_note')
        if i in reporting:
            record['reporting_metadata_provenance']=dict(artifact=item['reporting_annotations'],source_row_index=i,predictions_unchanged=True)
            if reporting[i].get('law_origin_counts') is not None:record['law_origin_counts']=reporting[i]['law_origin_counts']
            if reporting[i].get('outer_offer_coverage') is not None:
                record['outer_offer_coverage']=validate_probability_outer_coverage(record,reporting[i]['outer_offer_coverage'])
                record['coverage_definition']='Source forecast_rows counts this qualified probability/outcome mask only; full source offers and matched-candidate availability are explicit in outer_offer_coverage.'
            if reporting[i].get('diagnostic_context_coverage') is not None:
                record['diagnostic_context_coverage']=validate_diagnostic_context_coverage(record,reporting[i]['diagnostic_context_coverage'])
                record['coverage_definition']='Canonical qualified score/forecast mask only. Complete-source availability and conditional overlap denominators are explicit in diagnostic_context_coverage; mask coverage is not complete-system coverage.'
        invalid_mask=item.get('invalidated_shared_mask')
        if invalid_mask and original.get('fallback_view')==invalid_mask:
            record['score_version_state']='INVALIDATED_REQUESTED_SHARED_MASK_REFERENCE_ALIAS'
        if i in annotations:record['reporting_comparison']=annotations[i]
        if i in supersessions:
            s=supersessions[i]
            if s['source_test_id']!=record['test_id']:raise ValueError('supersession identity mismatch')
            record.update(score_version_state=s['state'],replacement_test_id=s['replacement_test_id'],supersession_mapping=item['supersession_mapping'])
        explicit_empty=(date.get('evaluation_weeks')==[]and('evaluation_weeks'in original or dates))
        if explicit_empty:
            if record['n']!=0:raise ValueError('empty scored dates with positive support')
            record.update(weeks=[],seasons=date.get('evaluation_seasons',[]),dates_missing_reason='zero_supported_rows_no_scored_weeks')
        if row.get('precision_counts'):
            for metric,p in row['precision_counts'].items():
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


def write(root=ROOT,previous=PREVIOUS,output=OUTPUT,*,reuse_prior_csv=False,compressed_delivery=False):
    root=Path(root);out=root/output
    if out.exists()and not(out/'INDEX_MANIFEST.json').exists():
        raise ValueError('incomplete index output exists; preserve failure and choose new output version')
    prior_body=(root/previous).read_bytes();prior=json.loads(prior_body)
    out.mkdir(parents=True,exist_ok=True)
    inputs=list(prior['input_manifests']);seen=set();shards=list(prior['shards']);kinds=collections.Counter();previous_n=0
    for part in shards:
        records=decode_shard(root,part);validate_index(records)
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
        raw=b'['+b','.join(buf)+b']\n';name=f'new-records-{len(shards):04d}.json'+('.gz'if compressed_delivery else'');path=out/name
        body=gzip.compress(raw,mtime=0)if compressed_delivery else raw
        part=dict(path=str(path.relative_to(root)),sha256=sha(body),bytes=len(body),records=len(buf))
        if compressed_delivery:part.update(compression='gzip',uncompressed_bytes=len(raw),uncompressed_sha256=sha(raw))
        path.write_bytes(body);shards.append(part)
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
    if reuse_prior_csv:
        for part in prior['csv_parts']:
            path=root/part['path']
            if path.stat().st_size!=part['bytes'] or sha(path.read_bytes())!=part['sha256']:
                raise ValueError('previous CSV bytes changed')
        if sum(p['rows'] for p in prior['csv_parts'])!=previous_n:
            raise ValueError('previous CSV coverage mismatch')
        csv_parts=list(prior['csv_parts'])
    handle=None;writer=None;part_n=0;row_n=0;fieldnames=None
    try:
        delivery_shards=shards[len(prior['shards']):] if reuse_prior_csv else shards
        for part in delivery_shards:
            for record in decode_shard(root,part):
                row=current_flat(record)
                source=record.get('source_aggregate_fields')or{}
                for key in ('prediction_version','score_version_state','replacement_test_id','replaces_test_id','supersession_mapping','source_registry_kind','source_version_note'):
                    row[key]=record.get(key,source.get(key))
                if fieldnames is None:fieldnames=list(row)
                if writer is None or part_n==10000:
                    if handle:
                        handle.close();csv_parts[-1].update(rows=part_n,bytes=path.stat().st_size,sha256=sha(path.read_bytes()))
                    path=out/(f'TEST_RESULTS_INDEX-{len(csv_parts):04d}.csv'+('.gz'if compressed_delivery else''));handle=csv_handle(path,compressed_delivery);writer=csv.DictWriter(handle,fieldnames=fieldnames);writer.writeheader();part_n=0
                    csv_parts.append(dict(path=str(path.relative_to(root))))
                    if compressed_delivery:csv_parts[-1]['compression']='gzip'
                writer.writerow(row);part_n+=1;row_n+=1
                if record['kind']=='software_verification':continue
                target=record['category'];cat_counts[target]+=1
                if target not in writers:
                    f=csv_handle(cats/(category_slug(target)+'.csv'+('.gz'if compressed_delivery else'')),compressed_delivery);files[target]=f;writers[target]=csv.DictWriter(f,fieldnames=fieldnames);writers[target].writeheader()
                writers[target].writerow(row)
        if handle:
            handle.close();handle=None;csv_parts[-1].update(rows=part_n,bytes=path.stat().st_size,sha256=sha(path.read_bytes()))
    finally:
        if handle:handle.close()
        for f in files.values():f.close()
    if row_n!=(new_n if reuse_prior_csv else previous_n+new_n):raise ValueError('streamed row count mismatch')
    row_n=previous_n+new_n
    manifest=dict(schema_version='v2-sharded-results-index-v2',record_unit=prior['record_unit'],
        baseline_checkpoint=prior['baseline_checkpoint'],previous_sharded_checkpoint=dict(artifact=previous,sha256=sha(prior_body),records=previous_n,unchanged=True),
        definitions=dict(prior['definitions'],selection_loss_rate=DEFINITIONS['selection_loss_rate']),precision_definition=prior['precision_definition'],forbidden_accuracy_conversion=prior['forbidden_accuracy_conversion'],
        comparison_reporting=prior.get('comparison_reporting'),input_manifests=inputs,record_count=row_n,by_kind=dict(kinds),shards=shards,max_shard_bytes=MAX_SHARD,csv_parts=csv_parts,
        streaming_build=dict(previous_records_reused=previous_n,new_records=new_n,prior_shards_unchanged=True,ordering='prior immutable shards followed by new registered versions; CSVfilterbytestID/panel'),
        reader_contract='New reported/reproduced/reconstructed/future and software evidence retain distinct identities; a score view is not a fit or unique NFL observation.')
    if reuse_prior_csv:
        manifest['csv_header_policy']='Prior immutable CSV parts are reused; new product columns may extend the header. Combine by column name. JSON shards are authoritative.'
        manifest['category_csv_scope']='New appended evaluation views only; use prior category CSVs and source rankings for earlier records.'
        manifest['streaming_build']['previous_csv_parts_reused']=len(prior['csv_parts'])
    if compressed_delivery:
        manifest['compressed_delivery_contract']='New JSON/CSV parts use lossless gzip; validate stored bytes, decompress, then parse. JSON parts retain uncompressed size/SHA. Prior parts remain unchanged. max_shard_bytes bounds uncompressed JSON.'
    (out/'INDEX_MANIFEST.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    csv_note=('Prior CSV parts retain their original headers. Combine by column name, preserving missing product fields. Category CSVs here contain only appended views. ' if reuse_prior_csv else 'All parts share columns; retain one header when combining. ')
    (out/'CSV_FILES.md').write_text('# Filterable result parts\n\n'+csv_note+'Comparator error changes are candidate minus control; missing pairs stay unknown.\n\n'+'\n'.join(f"- [{Path(r['path']).name}]({Path(os.path.relpath(root/r['path'],out)).as_posix()}): {r['rows']:,} records"for r in csv_parts)+'\n')
    (out/'README.md').write_text('# Permanent accuracy and error index\n\n'+f"{row_n:,} records; {row_n-kinds['software_verification']:,} evaluation views and {kinds['software_verification']:,} software receipts. All {previous_n:,} prior records and shards remain unchanged. Views are not distinct methods or NFL observations.\n\n"+'[CSV parts](CSV_FILES.md) · [JSON manifest](INDEX_MANIFEST.json) · [Previous checkpoint](../../championship-20261030f/results-index-v5/README.md)\n\n'+'Every result retains method, history, product, dates, sample, population, native error, defined precision numerator/denominator, fallback/coverage, paired comparator/delta, uncertainty and source evidence. Unknowns are explicit. Scoring corrections, changed predictions and retrospective cohort projections remain distinct. MAE and relative error reductions are not generic percentage accuracy. Point, mean-MSE, proper-distribution and actual-offer rankings are separate.\n\n| Category | Views |\n|---|---:|\n'+'\n'.join(f'| [{target}](categories/{category_slug(target)}.csv{'.gz'if compressed_delivery else''}) | {n:,} |'for target,n in sorted(cat_counts.items()))+'\n')
    return dict(status='PASS',records=row_n,new_records=new_n,reused_records=previous_n,shards=len(shards))


if __name__=='__main__':print(json.dumps(write()))
