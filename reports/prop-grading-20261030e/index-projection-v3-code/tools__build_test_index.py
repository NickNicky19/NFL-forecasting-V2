#!/usr/bin/env python3
"""Build an aggregate-only, linked accuracy/error index from frozen results."""
import argparse
import collections
import csv
import hashlib
import json
import os
import re
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nfl_v2.result_index import (DEFINITIONS,METRICS,PRECISION,VERSION,DIAGNOSTIC_KIND,
    canonical,diagnostic_row,hgb_row,evaluation,software_receipt,validate_index)

DEFAULTS=('reports/inventory/ALL_METHOD_SCORES.json','reports/replay/REPLAY_SCORES.json',
          'reports/week7-label-extension-v1/SCORES.json')
DEFAULT_SOFTWARE=('reports/verification/PRIMARY_COMPARISON.json',
                  'reports/verification/HISTORY_ENGINE_CHECKS.json',
                  'reports/continuation-20261029/RESULT_INDEX_SOFTWARE_TESTS.json',
                  'reports/continuation-20261029/RESULT_INDEX_DIAGNOSTIC_SOFTWARE_TESTS.json',
                  'reports/continuation-20261029/CONTINUATION_SOFTWARE_TESTS.json',
                  'reports/continuation-20261029/CORE_PUBLICATION_SOFTWARE_TESTS.json',
                  'reports/verification/FUTURE_GRADER_REVIEW_INITIAL.json',
                  'reports/verification/FUTURE_GRADER_REVIEW.json',
                  'reports/verification/HGB_SHADOW_GRADER_SOFTWARE_TESTS.json',
                  'reports/verification/HGB_FUTURE_GRADER_REVIEW_INITIAL.json',
                  'reports/verification/HGB_FUTURE_GRADER_REVIEW.json',
                  'reports/continuation-20261029/FINAL_PUBLICATION_SOFTWARE_TESTS.json')
DIAGNOSTIC_ROOT='reports/continuation-20261029/history-diagnostic-v1'
DIAGNOSTIC_CSV=DIAGNOSTIC_ROOT+'/SEASON_RESULTS_2022_2026.csv'
GAME_COUNTS='reports/verification/DIAGNOSTIC_VIEW_GAME_COUNTS.json'
DIAGNOSTIC_DIMS=('target','population','history_regime','product','season','week','position','fallback_view')
HGB_ROOT='reports/continuation-20261029/hgb-history-v1'
HGB_SCORES=HGB_ROOT+'/SCORES.json'
HGB_GAME_COUNTS='reports/verification/HGB_VIEW_GAME_COUNTS.json'
HGB_DIMS=('target','population','history_regime','objective','week','position')


def build(root,additional=(),software=()):
    manifests=json.loads((root/'reports/inventory/REPORTED_SOURCE_MANIFEST.json').read_text())
    links={r['source_id']:r['source_link'] for r in manifests}
    years={r['record_id']:r for r in json.loads((root/'reports/inventory/METHOD_YEAR_INVENTORY.json').read_text())}
    records=[];inputs=[]
    registry=root/'registries/RESULT_ARTIFACTS.json'
    registered=([r['artifact'] for r in json.loads(registry.read_text()) if r['state']=='SCORED'] if registry.exists() else [])
    generic=[p for p in (*DEFAULTS,*registered,*additional) if p not in {DIAGNOSTIC_CSV,HGB_SCORES}]
    for artifact in dict.fromkeys(generic):
        body=(root/artifact).read_bytes();rows=json.loads(body)
        if not isinstance(rows,list):raise ValueError('forecast source must be a list of aggregate evaluation rows')
        sha=hashlib.sha256(body).hexdigest()
        inputs.append(dict(source_artifact=artifact,sha256=sha,kind='forecast_evaluation_view',rows=len(rows)))
        for row in rows:
            record=evaluation(row,artifact,year_record=years.get(row.get('record_id')),
                source_link=links.get(row.get('source_id')))
            record['source_artifact_sha256']=sha;records.append(record)
    # This is a separately identified current-vintage participant diagnostic,
    # never pooled with inherited or issued-forecast panels as one ranking.
    if (root/DIAGNOSTIC_CSV).exists():
        source_body=(root/DIAGNOSTIC_CSV).read_bytes()
        source_sha=hashlib.sha256(source_body).hexdigest()
        run_artifact=DIAGNOSTIC_ROOT+'/RUN_RECEIPT.json'
        run_body=(root/run_artifact).read_bytes();receipt=json.loads(run_body)
        counts_body=(root/GAME_COUNTS).read_bytes();counts=json.loads(counts_body)
        if counts['prediction_sha256']!=receipt['private_prediction_sha256']:
            raise ValueError('diagnostic game census/prediction binding mismatch')
        if receipt['public_outputs']['SEASON_RESULTS_2022_2026.csv']!=source_sha:
            raise ValueError('diagnostic frozen aggregate hash mismatch')
        game_rows={}
        for row in counts['rows']:
            key=tuple(str(row[k]) for k in DIAGNOSTIC_DIMS)
            if key in game_rows:raise ValueError('duplicate diagnostic game census identity')
            game_rows[key]=row
        with (root/DIAGNOSTIC_CSV).open(newline='') as f:
            diagnostic_views=list(csv.DictReader(f))
        seen=set()
        for row in diagnostic_views:
            key=tuple(row[k] for k in DIAGNOSTIC_DIMS)
            if key in seen:raise ValueError('duplicate frozen diagnostic view')
            seen.add(key)
            if key not in game_rows:raise ValueError('missing per-view diagnostic game census')
            game_row=game_rows[key]
            normalized,dates=diagnostic_row(row,receipt['season_week_coverage'])
            normalized['unique_games']=game_row['scored_games']
            normalized['coverage']={'scored_games':game_row['scored_games'],
                'forecast_games':game_row['forecast_games'],
                'game_count_definition':'distinct game IDs in the exact retained scored/forecast view'}
            record=evaluation(normalized,DIAGNOSTIC_CSV,year_record=dates)
            record['source_artifact_sha256']=source_sha
            record['game_count_scope']='independent retained-prediction-row census; exact same view dimensions'
            record['game_count_provenance']={'source_artifact':GAME_COUNTS,
                'source_artifact_sha256':hashlib.sha256(counts_body).hexdigest(),
                'prediction_sha256':counts['prediction_sha256'],
                'forecast_games':game_row['forecast_games'],'scored_games':game_row['scored_games']}
            record['diagnostic_provenance']={'run_receipt':run_artifact,
                'run_receipt_sha256':hashlib.sha256(run_body).hexdigest(),
                'protocol_sha256':receipt['protocol_sha256'],'code_sha256':receipt['code_sha256'],
                'prediction_sha256':receipt['private_prediction_sha256'],
                'query_membership_sha256':receipt['query_membership_sha256'],
                'source_qualification_artifact':DIAGNOSTIC_ROOT+'/SOURCE_QUALIFICATION.json'}
            # Retain every original aggregate field, including prevalence,
            # missing/fallback counts and infinite-score flags beyond the shared metric list.
            record['source_aggregate_fields']=row
            records.append(record)
        if seen!=set(game_rows):raise ValueError('unmatched diagnostic game census views')
        inputs.append(dict(source_artifact=DIAGNOSTIC_CSV,sha256=source_sha,kind=DIAGNOSTIC_KIND,
            rows=len(diagnostic_views),game_census_artifact=GAME_COUNTS,
            game_census_sha256=hashlib.sha256(counts_body).hexdigest(),
            prediction_sha256=receipt['private_prediction_sha256']))
    if (root/HGB_SCORES).exists():
        body=(root/HGB_SCORES).read_bytes();views=json.loads(body)
        run_body=(root/(HGB_ROOT+'/RUN_RECEIPT.json')).read_bytes();receipt=json.loads(run_body)
        counts_body=(root/HGB_GAME_COUNTS).read_bytes();counts=json.loads(counts_body)
        if counts['run_receipt_sha256']!=hashlib.sha256(run_body).hexdigest() or counts['protocol_sha256']!=receipt['protocol_sha256']:
            raise ValueError('HGB census/protocol/run binding mismatch')
        census={tuple(str(row[k]) for k in HGB_DIMS):row for row in counts['rows']}
        if len(census)!=len(counts['rows']):raise ValueError('duplicate HGB game census view')
        seen=set();sha=hashlib.sha256(body).hexdigest()
        for row in views:
            key=tuple(str(row[k]) for k in HGB_DIMS)
            if key in seen or key not in census:raise ValueError('duplicate or missing HGB game census view')
            seen.add(key);games=census[key];normalized,dates=hgb_row(row)
            normalized['unique_games']=games['scored_games']
            normalized['coverage'].update({k:games[k] for k in ('scored_games','forecast_games')})
            record=evaluation(normalized,HGB_SCORES,year_record=dates)
            record['source_artifact_sha256']=sha
            record['game_count_scope']='independent retained HGB prediction-row census; exact same view dimensions'
            record['game_count_provenance']={'source_artifact':HGB_GAME_COUNTS,
                'source_artifact_sha256':hashlib.sha256(counts_body).hexdigest(),
                'forecast_games':games['forecast_games'],'scored_games':games['scored_games']}
            record['diagnostic_provenance']={'run_receipt':HGB_ROOT+'/RUN_RECEIPT.json',
                'run_receipt_sha256':hashlib.sha256(run_body).hexdigest(),
                'protocol_sha256':receipt['protocol_sha256'],'code_sha256':receipt['code_sha256'],
                'independent_review':'reports/verification/HGB_HISTORY_INDEPENDENT_QA.json'}
            record['source_aggregate_fields']=row;records.append(record)
        if seen!=set(census):raise ValueError('unmatched HGB census view')
        inputs.append(dict(source_artifact=HGB_SCORES,sha256=sha,kind=DIAGNOSTIC_KIND,
            rows=len(views),game_census_artifact=HGB_GAME_COUNTS,
            game_census_sha256=hashlib.sha256(counts_body).hexdigest()))
    software_inputs=list(dict.fromkeys([p for p in DEFAULT_SOFTWARE if (root/p).exists()]+list(software)))
    for artifact in software_inputs:
        body=(root/artifact).read_bytes();receipt=json.loads(body)
        record=software_receipt(artifact,receipt);record['source_artifact_sha256']=hashlib.sha256(body).hexdigest()
        records.append(record);inputs.append(dict(source_artifact=artifact,sha256=record['source_artifact_sha256'],kind='software_verification',rows=1))
    records=validate_index(sorted(records,key=lambda r:r['test_id']))
    return dict(schema_version=VERSION,record_unit='evaluation output view; not an independent method, fit or NFL observation',
        definitions=DEFINITIONS,precision_definition='exact/tolerance fractions only when explicitly supplied; numerator reconstructed from rate*n is labeled; probability residual precision is not binary accuracy',
        forbidden_accuracy_conversion='Native errors, software pass counts, and interval coverage are never converted to percent prediction accuracy.',
        input_manifests=inputs,records=records)


def flat(record):
    keys=['test_id','kind','procedure_id','history_regime','category','product_id','evaluation_panel_id','population','position','fallback_view',
          'seasons','weeks','period','n','n_source_field','games','games_source_field','forecast_or_offered_rows',
          'coverage_fraction','fallback_rows','scored_fallback_rows','evidence','native_units','primary_metric',
          'primary_error','accuracy_status','accuracy_missing_reason','source_artifact','source_artifact_sha256',
          'source_record_id','source_pointer','upstream_source_id','upstream_source_link','software_checks','software_status']
    r={k:record.get(k) for k in keys}
    for k in ['seasons','weeks']:
        if r[k] is not None:r[k]=canonical(r[k])
    for k in ['game_count_provenance','diagnostic_provenance','source_aggregate_fields']:
        r[k]=canonical(record[k]) if record.get(k) is not None else None
    for name in METRICS:
        r[name]=(record.get('metrics') or {}).get(name)
        r[name+'_status']=(record.get('metric_status') or {}).get(name)
    r['source_infinite_nll_rows']=record.get('source_infinite_nll_rows')
    for name in PRECISION:
        p=(record.get('precision_metrics') or {}).get(name,{})
        for field in ['rate','numerator','denominator','numerator_provenance','missing_reason']:
            r[name+'_'+field]=p.get(field)
        if not p:r[name+'_missing_reason']=record.get('accuracy_missing_reason','precision rate not supplied')
    return r


def readable(bundle,output):
    records=bundle['records'];evaluations=[r for r in records if r['kind']!='software_verification']
    inherited=[r for r in evaluations if r['kind']=='forecast_evaluation_view']
    diagnostic=[r for r in evaluations if r['kind']==DIAGNOSTIC_KIND]
    software=[r for r in records if r['kind']=='software_verification']
    def link(artifact):return os.path.relpath(ROOT/artifact,output)
    lines=['# Test results: error and explicitly measured accuracy','',
        f'{len(evaluations):,} evaluation output views and {len(software)} separate software-verification receipts. These are not distinct-method, fit, or independent-NFL-sample counts.',
        '',f'{len(inherited):,} inherited/replay views and {len(diagnostic):,} separate current-vintage participant-diagnostic views retain different population/evidence identities. No cross-panel winner is inferred.',
        '', '[Browse category CSVs](categories/README.md) · [Full filterable CSV](TEST_RESULTS_INDEX.csv) · [Complete compact JSON and definitions](TEST_RESULTS_INDEX.json) · [Reporting contract](../../docs/RESULT_REPORTING_CONTRACT.md)',
        '', 'Every evaluation has a stable test ID, exact source link/hash, method, category, product, evidence level, denominator and available errors. Filter the CSV by category, panel, product, population and evidence before comparing. Unknown dates, histories, coverage or scores remain explicit unknowns.',
        '', 'MAE/RMSE are native-unit errors; lower is better. Bias is signed prediction minus outcome. Brier/log loss score probabilities. None becomes an accuracy percentage. Exact-match and tolerance accuracy are supplied fractions with their denominators; reconstructed hit counts are labeled. Probability residual tolerances are not classification or pick accuracy. Software passes have no NFL accuracy.',
        '', '| Source | Evaluation views | Evidence |','|---|---:|---|']
    for m in bundle['input_manifests']:
        source_rows=[r for r in evaluations if r['source_artifact']==m['source_artifact']]
        if source_rows:lines.append(f"| [{m['source_artifact']}]({link(m['source_artifact'])}) | {len(source_rows):,} | {', '.join(sorted({r['evidence'] for r in source_rows}))} |")
    lines+=['','| Category | Views | With MAE | With Brier | With numeric precision accuracy |','|---|---:|---:|---:|---:|']
    for category in sorted({r['category'] for r in evaluations}):
        rs=[r for r in evaluations if r['category']==category]
        lines.append(f"| [{category}](categories/{category_slug(category)}.csv) | {len(rs)} | {sum(r['metrics']['mae'] is not None for r in rs)} | {sum(r['metrics']['brier'] is not None for r in rs)} | {sum(r['accuracy_status']=='precision_rates_reported' for r in rs)} |")
    lines+=['','The short reference below shows reproduced primary-role results from the original one-game replay. The CSV/JSON retain all views, losing results and the separate later-label panel. These examples are not a pooled ranking.','',
        '| Stable test ID | Method / category | n | Primary error | Exact matches | Source |','|---|---|---:|---:|---|---|']
    examples=[r for r in evaluations if r['source_artifact']==DEFAULTS[1] and r['population']=='primary_roles']
    for r in sorted(examples,key=lambda r:(r['category'],r['procedure_id'])):
        p=(r['precision_metrics'] or {}).get('exact_rate',{})
        accuracy=(f"{p['numerator']}/{p['denominator']}" if p.get('numerator') is not None else 'not reported') if r['category']!='anytime_td' else 'not a binary decision'
        error='null' if r['primary_error'] is None else f"{r['primary_metric']} {r['primary_error']:.6g}"
        lines.append(f"| `{r['test_id']}` | {r['procedure_id']} / {r['category']} | {r['n']} | {error} | {accuracy} | [frozen result]({link(r['source_artifact'])}) |")
    lines+=['','Original one-game and later Week 7 labels are incomplete and select explicit production. Later anytime-TD labels are all positive. Those probability scores do not establish representative calibration or skill. Training-history conclusions require identical populations and isolated fit-window procedures; unknown legacy history is labeled rather than inferred.','',
        'The history diagnostic includes all10,154 frozen season/week/position/fallback views, exact per-view distinct scored/forecast games, source aggregate fields, infinite-score flags and bound protocol/code/prediction provenance. It is a retrospective observed-stat-row/participation cohort, not the full ex-ante website population or authenticated pregame capture. Its seven-week uncertainty and exposure limits remain in the linked report.',
        '', 'The 930 HGB fixed-objective views are separately identified, linked to retained models, protocol/code, and independent per-view game counts. Current-season fitting uses common older feature memory. Losses and startup fallback are retained; these point products are not numeric probability distributions.',
        '', 'Future normalized JSON aggregate evaluations enter through `--additional`; empirical and HGB diagnostics have explicit adapters and independent game censuses. Software receipts use `--software-receipt`. Preserve immutable old artifacts and register corrected/new runs separately.','']
    return '\n'.join(lines)


def category_slug(category):
    slug=re.sub(r'[^A-Za-z0-9_-]+','_',str(category))
    if not slug:raise ValueError('empty category filename')
    return slug


def write_categories(bundle,output):
    directory=output/'categories';directory.mkdir(parents=True,exist_ok=True)
    evaluations=[r for r in bundle['records'] if r['kind']!='software_verification']
    lines=['# Category result views','',
        '[All result views and definitions](../TEST_RESULTS_INDEX.md) · [Reporting contract](../../../docs/RESULT_REPORTING_CONTRACT.md)','',
        'Each CSV preserves stable test IDs, method/history, product, panel, population, season/week, position/fallback, error and explicitly measured precision, counts and provenance. Filter on compatible panel/product/population/evidence before comparison. Values are not pooled rankings, and software checks are excluded.','',
        '| Category | All views | Inherited/replay | Participant diagnostic | CSV |','| --- | ---: | ---: | ---: | --- |']
    filenames=set()
    for category in sorted({r['category'] for r in evaluations}):
        slug=category_slug(category)
        if slug in filenames:raise ValueError('category filename collision')
        filenames.add(slug)
        selected=[r for r in evaluations if r['category']==category]
        rows=[flat(r) for r in selected]
        with (directory/(slug+'.csv')).open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        n_diag=sum(r['kind']==DIAGNOSTIC_KIND for r in selected)
        lines.append(f'| {category} | {len(selected):,} | {len(selected)-n_diag:,} | {n_diag:,} | [{slug}.csv]({slug}.csv) |')
    (directory/'README.md').write_text('\n'.join(lines)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--additional',action='append',default=[])
    p.add_argument('--software-receipt',action='append',default=[])
    p.add_argument('--output',type=Path,default=ROOT/'reports/continuation-20261029')
    a=p.parse_args()
    if (ROOT/'registries/CURRENT_RESULTS_INDEX.json').exists() and a.output.resolve()==(ROOT/'reports/continuation-20261029').resolve():
        p.error('The October29 index is now immutable. Use tools/build_test_index_v2.py for the current sharded index, or a fresh explicit staging --output.')
    bundle=build(ROOT,a.additional,a.software_receipt)
    a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'TEST_RESULTS_INDEX.json').write_text(json.dumps(bundle,separators=(',',':'),allow_nan=False)+'\n')
    rows=[flat(r) for r in bundle['records']]
    with (a.output/'TEST_RESULTS_INDEX.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (a.output/'TEST_RESULTS_INDEX.md').write_text(readable(bundle,a.output))
    write_categories(bundle,a.output)
    print(json.dumps(dict(indexed_records=len(rows),by_kind=dict(collections.Counter(r['kind'] for r in bundle['records'])))))


if __name__=='__main__':main()
