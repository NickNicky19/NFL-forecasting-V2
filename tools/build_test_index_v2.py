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
from nfl_v2.comparison_reporting import comparison_fields
from tools.build_test_index import flat,category_slug

BASE='reports/continuation-20261029/TEST_RESULTS_INDEX.json'
OUTPUT='reports/continuation-20261030b/results-index'
PREVIOUS_SHARDED='reports/continuation-20261030/results-index/INDEX_MANIFEST.json'
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
    for key in ('run_id','procedure_family_id','cohort_id','information_policy','feature_memory_policy','training_population','source_vintage','scoring_version','correction_kind','precision_correction_artifact',
            'probability_conditioning','probability_score_contract','bookmaker_nonvoid_conditioning','proper_probability_n','reporting_metadata_provenance','law_origin_counts','outer_offer_coverage','diagnostic_context_coverage'):
        value=record.get(key,source.get(key))
        if value is None:value=source.get(key)
        row[key]=json.dumps(value,separators=(',',':')) if isinstance(value,(dict,list)) else value
    for key,value in comparison_fields(record).items():
        row[key]=json.dumps(value,separators=(',',':')) if isinstance(value,(dict,list)) else value
    outer=record.get('outer_offer_coverage')or{}
    for key in ('outer_offer_universe','matched_candidate_admitted_law_rows','candidate_full_qualified_mask_n','qualified_mask_n','mask_over_outer_offer_fraction'):
        row[key]=outer.get(key)
    diagnostic=(record.get('diagnostic_context_coverage')or[{}])[0]
    for key,source_key in (('diagnostic_source_offer_universe','source_offer_universe'),
                           ('diagnostic_fullsystem_available_points','source_available_points'),
                           ('diagnostic_fraction_of_full_source','fraction_of_source')):
        row[key]=diagnostic.get(source_key)
    stats=record.get('selection_metrics')or{}
    for key in ('admitted_forecast_opportunities','unavailable_forecast_opportunities','admitted_rule_abstentions'):
        row[key]=stats.get(key)
    for key in ('side','strategy','horizon','threshold_provenance','selection_evidence','probability_conditioning',
                'season_type','statistic_period','period_provenance','K','rank_scope','time_panel_id',
                'season_alias_of_week_view','alias_of_record_id','unique_players','unique_player_games','unique_weeks'):
        row[key]=record.get(key)
    for key in ('decided_unique_games','decided_unique_players','decided_unique_player_games','decided_week_count',
                'registered_week_count','registered_weeks','selected_week_count','overtime'):
        value=record.get(key);row[key]=json.dumps(value,separators=(',',':'))if isinstance(value,list)else value
    row['cohort_evidence']=record.get('cohort_evidence')
    row['selection_loss_rate']=(record.get('metrics')or{}).get('selection_loss_rate')
    for key in ('wins','losses','pushes','voids','pending','missing_actual','unknown_participation',
                'unresolved_contract','eligible_opportunities','selected_opportunities','abstentions',
                'source_pool_opportunities','selection_coverage','conditional_selection_coverage',
                'eligible_rank_pool_n','hit_rate','net_return','ROI'):
        row['selection_'+key]=stats.get(key)
    for key in ('coverage_scope','full_forecast_feed_count','provider_labelled_finite_threshold_count',
                'site_generated_threshold_count','authentic_offer_universe_count',
                'original_fullfeed_coverage','original_provider_threshold_coverage'):
        row['selection_'+key]=stats.get(key)
    hit=(record.get('precision_metrics')or{}).get('decided_pick_hit_rate',{})
    for key in ('numerator','denominator','rate'):
        row['decided_pick_'+key]=hit.get(key)
    book=stats.get('book_settlement_status_counts')
    book_complete=bool(book)and all(isinstance(v,int)and not isinstance(v,bool)and v>=0 for v in book.values())and sum(book.values())==record.get('forecast_or_offered_rows')
    for state in ('WIN','LOSS','PUSH','VOID','PENDING','MISSING_ACTUAL','UNKNOWN_PARTICIPATION','UNRESOLVED_CONTRACT'):
        row['book_settlement_'+state]=book.get(state,0 if book_complete else None)if book else None
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
            annotations={}
            if item.get('comparison_annotations'):
                annotation_body=(root/item['comparison_annotations']).read_bytes();projection=json.loads(annotation_body)
                if projection['source_score_sha256']!=artifact_sha:raise ValueError('comparison projection/source binding mismatch')
                annotations={r['source_record_id']:r['comparison'] for r in projection['rows']}
                if len(annotations)!=len(o) or set(annotations)!={r.get('record_id') for r in o}:raise ValueError('comparison projection view census mismatch')
                inputs.append(dict(source_artifact=item['comparison_annotations'],sha256=sha(annotation_body),rows=len(annotations),kind='source_bound_matched_comparison_annotation_not_extra_evaluation'))
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
                if date_rows and item.get('empty_dates_policy')=='explicit_empty_supported_scoring_dates' and not dates.get('evaluation_weeks'):
                    if r['n']!=0:raise ValueError('empty scored-date projection with supported outcomes')
                    r['weeks']=[];r['seasons']=dates.get('evaluation_seasons',[])
                    r['dates_missing_reason']='zero_supported_rows_no_scored_weeks'
                r['source_aggregate_fields']=original
                if annotations:r['reporting_comparison']=annotations[original['record_id']]
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
    shards=[];buf=[];size=2;previous=None
    # Reuse immutable prior shards instead of copying hundreds of MB whenever
    # a small new wave appends views. Prior record contents must match exactly.
    existing_ids=set()
    if (root/PREVIOUS_SHARDED).exists():
        prior_bytes=(root/PREVIOUS_SHARDED).read_bytes();prior=json.loads(prior_bytes)
        previous=dict(artifact=PREVIOUS_SHARDED,sha256=sha(prior_bytes),records=prior['record_count'],unchanged=True)
        current_records={r['test_id']:r for r in records}
        for part in prior['shards']:
            body=(root/part['path']).read_bytes()
            if sha(body)!=part['sha256']:raise ValueError('previous sharded checkpoint changed')
            for record in json.loads(body):
                if current_records.get(record['test_id'])!=record:
                    raise ValueError('previous indexed result changed or lost: '+record['test_id'])
                existing_ids.add(record['test_id'])
            shards.append(part)
    def flush():
        nonlocal buf,size
        if not buf:return
        body=b'['+b','.join(buf)+b']\n';name=f'new-records-{len(shards):04d}.json'
        (out/name).write_bytes(body)
        shards.append(dict(path=str((out/name).relative_to(root)),sha256=sha(body),bytes=len(body),records=len(buf)))
        buf=[];size=2
    for record in records:
        if record['test_id'] in existing_ids:continue
        body=encoded(record)
        if len(body)+3>MAX_SHARD:raise ValueError('single aggregate exceeds shard limit')
        if size+len(body)+1>MAX_SHARD:flush()
        buf.append(body);size+=len(body)+1
    flush()
    # Remove only superseded generated shards after the new source projection succeeds.
    current={Path(s['path']).name for s in shards}
    for p in out.glob('new-records-*.json'):
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
        previous_sharded_checkpoint=previous,
        comparison_reporting=dict(delta='candidate error minus comparator error; negative favors candidate',relative='delta / comparator error; null when comparator is zero or matching is unestablished',matching='explicit retained-row binding required; equal sample counts alone are insufficient',unreported='UNESTABLISHED with reason; no generic percentage accuracy from error',projection='CSV annotations do not alter source scores, predictions or earlier index bytes'),
        definitions=old['definitions'],precision_definition=old['precision_definition'],
        forbidden_accuracy_conversion=old['forbidden_accuracy_conversion'],input_manifests=inputs,
        record_count=len(records),by_kind=dict(collections.Counter(r['kind'] for r in records)),shards=shards,
        max_shard_bytes=MAX_SHARD,csv_parts=csv_parts)
    (out/'INDEX_MANIFEST.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')
    lines=['# Permanent test results: current index','',
        f"{len(records):,} records: {sum(r['kind']!='software_verification' for r in records):,} evaluation views and {sum(r['kind']=='software_verification' for r in records)} software receipts. Views are not distinct methods or independent NFL samples.",
        '', '[Filterable CSV parts](CSV_FILES.md) · [Sharded JSON manifest](INDEX_MANIFEST.json) · [Previous immutable checkpoint](../../continuation-20261030/results-index/README.md)',
        '', 'All earlier IDs and losses remain. New registrations retain procedure/history/product, exact panel/population and cohort, dates, denominators, native errors, defined tolerance accuracy, fallback/coverage, uncertainty and recoverable source links. Inspect source aggregate fields for exact cohort and source semantics. Unknowns remain null with reasons. Numeric errors do not become percentage accuracy. Software checks add no NFL observations.',
        '', 'Compare identical games, source vintages, information cutoffs, products and membership. Historical participant panels, original future captures, later partial-week captures and offered-price panels stay distinct. No hindsight-selected winner is credited as a live selector.',
        '', 'CSV comparison columns show the explicit comparator, paired denominator, candidate-minus-comparator error and relative change. Negative change favors the candidate. A relative change is not accuracy. Null comparisons remain UNESTABLISHED with a reason, including unmatched historical website references. Fallback rate uses the declared forecast-row denominator. Precision columns preserve their exact numerator/denominator and strict/inclusive definitions. Scoring corrections are labeled separately from prediction changes.',
        '', '| Category | Evaluation views |','|---|---:|',*summary,'',
        'Register each new immutable `SCORES.json` or software receipt in `registries/RESULT_ARTIFACTS.json`, run `python tools/build_test_index_v2.py`, and run `python tools/check_result_index_coverage.py`. Each JSON shard stays below12MiB; the old checkpoint is preserved.','']
    (out/'README.md').write_text('\n'.join(lines))
    return dict(status='PASS',records=len(records),shards=len(shards),previous_ids_retained=len(old['records']))


if __name__=='__main__':print(json.dumps(write()))
