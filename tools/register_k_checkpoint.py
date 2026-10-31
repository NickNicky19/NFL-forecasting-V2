"""Root-only K metadata/source registration; never fits, forecasts or grades."""
import csv
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/right-and-wrong-diagnostic-20261031k'


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save_once(path,value):
    if not path.exists():path.write_text(json.dumps(value,indent=2)+'\n')


def prepare_sources():
    log=BASE/'UNIT_TEST_RESULTS_V1.log'
    if not log.exists():shutil.copyfile('/tmp/v2-k-units-v1.log',log)
    assert 'Ran 442 tests' in log.read_text() and log.read_text().rstrip().endswith('OK')
    files=['nfl_v2/right_wrong_diagnostic.py','nfl_v2/result_index.py','tools/build_test_index_v2.py',
           'tools/build_test_index_v3.py','tools/build_current_valid_view_v2.py','tools/build_full_championship_report.py',
           'tests/test_right_wrong_diagnostic.py','tests/test_diagnostic_ranking_exclusion.py']
    software=BASE/'SOFTWARE_VERIFICATION_V1.json'
    save_once(software,dict(status='PASS',state='SOFTWARE_VERIFIED_NO_NFL_ACCURACY_INFERRED',
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),tests_run=442,new_core_tests=11,
        new_index_and_ranking_scope_tests=3,unit_log_artifact=log.relative_to(ROOT).as_posix(),
        unit_log_sha256=digest(log),source_bindings=[dict(path=p,sha256=digest(ROOT/p))for p in files],
        new_NFL_fits=0,new_model_predict_calls=0,new_forecasts=0,NFL_accuracy=None,
        scope='Software checks of buckets/boundaries/bands/examples/components, ranking exclusion and mask availability. Overlapping old suite tests are not independent NFL observations.'))
    save_once(BASE/'SOFTWARE_VERIFICATION_MANIFEST_V1.json',dict(schema='v2-bound-software-verification-v1',
        receipt=dict(path=software.relative_to(ROOT).as_posix(),sha256=digest(software)),tests_run=442,
        previous_manifest='reports/defense-season-executor-20261031j-code/SOFTWARE_VERIFICATION_MANIFEST_V2.json',new_NFL_observations=0))
    sources=[]
    for stage in('stage-a-v1','stage-b-v1','rr-native-tie-completion-v1'):
        path=BASE/stage/'SCORES.json'
        item=dict(artifact=path.relative_to(ROOT).as_posix(),state='SCORED',
            kind='right_and_wrong_outcome_conditioned_diagnostic_not_championship_rank',
            version_note='Retained forecast/line/actual diagnostic subsets, not new learners/fits/NFL observations or live cohorts. Statistical crossing, not settled returns.')
        annotation=path.with_name('CURRENT_REPORTING_ANNOTATIONS_K_V1.json')
        if annotation.exists():item['reporting_annotations']=annotation.relative_to(ROOT).as_posix()
        sources.append(item)
    sources.append(dict(artifact=software.relative_to(ROOT).as_posix(),state='SOFTWARE_VERIFIED',
                        kind='right_wrong_core_and_index_eligibility_software_not_NFL_accuracy'))
    path=ROOT/'registries/RESULT_ARTIFACTS.json';rows=json.loads(path.read_text());known={x['artifact']for x in rows}
    added=[s for s in sources if s['artifact']not in known]
    if added:path.write_text(json.dumps(rows+added,indent=2)+'\n')
    bound=[]
    for s in sources:
        path=ROOT/s['artifact']
        n=len(json.loads(path.read_text())) if s['state']=='SCORED' else 1
        bound.append(dict(path=s['artifact'],sha256=digest(path),kind=s['kind'],rows=n))
    save_once(BASE/'NEW_CANONICAL_SCORE_MANIFEST_K_V1.json',dict(
        state='THREE_IMMUTABLE_DIAGNOSTIC_SCORE_SOURCES_PLUS_SOFTWARE',sources=bound,
        NFL_methods_added=0,new_NFL_fits=0,new_forecasts=0,new_NFL_observations=0))
    return len(added)


def append_receipts():
    ledger=ROOT/'registries/EXECUTIONS.jsonl'
    known={json.loads(x)['run_id']for x in ledger.read_text().splitlines()if x.strip()}
    path=ROOT/'registries/RUN_RESULT_ARTIFACT_MANIFEST.json';old=json.loads(path.read_text())
    artifacts={x['artifact_id']for x in old};events=[];new=[]
    for p in sorted(BASE.rglob('*.json')):
        if any(x.startswith('results-index')for x in p.parts):continue
        relative=p.relative_to(ROOT).as_posix();obj=json.loads(p.read_text())
        state=obj.get('state',obj.get('status','BOUND_K_METADATA_OR_SCORE_ARTIFACT'))if isinstance(obj,dict)else'IMMUTABLE_DIAGNOSTIC_SCORE_OR_METADATA_ARRAY'
        rid='V2-20261031K-'+hashlib.sha256(relative.encode()).hexdigest()[:16]
        if rid not in known:events.append(dict(run_id=rid,recorded_at_utc=datetime.now(timezone.utc).isoformat(),
            state=state,receipt=relative,receipt_sha256=digest(p),new_NFL_fits=0,new_model_inference=0,
            new_original_captures=0,new_NFL_observations=0,
            scope='K diagnostic/review/software metadata only; conditional views are not NFL fits or independent samples. Prior losses/captures retained.'))
        aid=rid+'-ARTIFACT'
        if aid not in artifacts:new.append(dict(artifact_id=aid,run_id=rid,file=relative,sha256=digest(p),bytes=p.stat().st_size,
            kind='K_safe_diagnostic_aggregate_code_or_execution_receipt',status=state,original=False,
            evidence_availability='PUBLIC_SAFE_AGGREGATES_AND_BINDINGS_PRIVATE_ROWS_REMAIN_PRIVATE',private_locator=None))
    with ledger.open('a')as f:
        for r in events:f.write(json.dumps(r)+'\n')
    if new:
        path.write_text(json.dumps(old+new,indent=2)+'\n')
        path=ROOT/'registries/RUN_RESULT_ARTIFACT_MANIFEST.csv'
        with path.open(newline='')as f:fields=csv.DictReader(f).fieldnames
        with path.open('a',newline='')as f:csv.DictWriter(f,fieldnames=fields,extrasaction='ignore').writerows(new)
    return len(events),len(new)


if __name__=='__main__':
    n=prepare_sources();events,artifacts=append_receipts()
    print(json.dumps(dict(added_canonical_sources=n,receipt_events=events,artifact_rows=artifacts,new_NFL_fits=0)))
