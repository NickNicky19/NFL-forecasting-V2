"""Root-only Week8 registration/index metadata; no NFL grading or fitting."""
import argparse,collections,csv,hashlib,json,shutil,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
BASE=ROOT/'reports/week8-grading-20261102l'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    if Path(p).exists():
        assert json.loads(Path(p).read_bytes())==v,'Immutable registration metadata differs'
        return
    with Path(p).open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')


def prepare():
    out=BASE/'software';out.mkdir(exist_ok=True);log=out/'UNIT_TEST_RESULTS_V1.log'
    if not log.exists():shutil.copyfile('/tmp/v2-week8-l-tests.log',log)
    assert'Ran 445 tests'in log.read_text()and log.read_text().rstrip().endswith('OK')
    code=['nfl_v2/full_provider_prop_replay.py','tests/test_week8_pending_extension.py']+[p.as_posix()for p in Path('tools').glob('*week8*.py')if p.name in {'grade_saved_week8.py','grade_week8_captured_library.py','extend_week8_saved_versions.py','grade_week8_saved_laws.py','project_week8_common_comparisons.py','summarize_week8_checkpoint.py','compare_week8_frozen_ablations.py','compare_week8_leaders_on_fixed_mask.py','qualify_week8_chart_source.py','acquire_week8_grading_sources.py'}]
    software=out/'SOFTWARE_VERIFICATION_V1.json';save(software,dict(status='PASS',state='SOFTWARE_VERIFIED_NO_NFL_ACCURACY_INFERRED',tests_run=445,new_pending_fixtures=3,unit_log=log.relative_to(ROOT).as_posix(),unit_log_sha256=sha(log),source_bindings=[dict(path=p,sha256=sha(ROOT/p))for p in code],new_NFL_fits=0,new_model_predict_calls=0,new_forecasts=0,NFL_accuracy=None))
    cov={r['method_key']:r for r in json.loads((BASE/'checkpoint-summary-v1/OUTER_FORECAST_COVERAGE_V2.json').read_bytes())};sources=[]
    for p in sorted(BASE.rglob('*SCORES.json')):
        rows=json.loads(p.read_bytes());assert isinstance(rows,list)and rows
        item=dict(artifact=p.relative_to(ROOT).as_posix(),state='SCORED',kind='week8_saved_pregame_outputs_and_retrospective_threshold_rules_partial_final_games',version_note='W8separate fromfixedW1–7/older seasons. No newfits/inference/forecasts. Exactoriginal selections versus replay, capture versions/histories/products and source clocks stay separate; probability is modeledappearance, not verifiedbooknonvoid. Full-system availability is not common-mask coverage.')
        annotations=[]
        if rows[0].get('record_kind')=='prop_selection_evaluation'and p.parent.name in('captured-library-v2','comparable-products-v3'):
            for i,r in enumerate(rows):
                m=cov[r['method_key']];outer=m['outer_provider_offer_rows'];available=m['issued_T90_forecasts_on_offers'];mask=r['selection_metrics']['selection_pool_count'];selected=r['forecast_rows'];assert selected<=mask<=available<=outer
                annotations.append(dict(source_row_index=i,record_id=r['record_id'],diagnostic_context_coverage=[dict(context='CURRENT_PARTIAL_WEEK_RETAINED_OFFER_POOL_AND_DECLARED_NATIVE_MASK',source_offer_universe=outer,source_available_points=available,mask_points=mask,context_outer_opportunities=outer,scored_or_selected_n=selected,fraction_of_source=selected/outer if outer else None,fraction_of_context=selected/outer if outer else None)]))
        elif rows[0].get('record_kind')=='prop_threshold_probability_evaluation':
            full={r['method_key']:r['n']for r in rows if r['reference']=='FOOTBALL_ORIGINAL_LAW'and r['evaluation_panel_id'].endswith(':ALL_LINES')};outer={r['target']:r['eligible']for r in json.loads((BASE/'checkpoint-summary-v1/TABLE_A_ORIGINAL_CATEGORY.json').read_bytes())}
            for i,r in enumerate(rows):
                o=outer[r['target']];a=r['forecast_rows'];f=full[r['method_key']];n=r['n'];assert n<=f<=a<=o
                annotations.append(dict(source_row_index=i,record_id=r['record_id'],outer_offer_coverage=dict(outer_offer_universe=o,matched_candidate_admitted_law_rows=a,candidate_full_qualified_mask_n=f,qualified_mask_n=n,mask_over_outer_offer_fraction=n/o if o else None)))
        if annotations:
            a=p.with_name(p.stem+'_INDEX_REPORTING_ANNOTATIONS_V1.json');save(a,dict(source_score_sha256=sha(p),predictions_and_scores_unchanged=True,rows=annotations));item['reporting_annotations']=a.relative_to(ROOT).as_posix()
        sources.append(item)
    sources.append(dict(artifact=software.relative_to(ROOT).as_posix(),state='SOFTWARE_VERIFIED',kind='Week8_pending_extension_software_checks_not_NFL_accuracy'))
    reg=ROOT/'registries/RESULT_ARTIFACTS.json';prior=json.loads(reg.read_bytes());known={r['artifact']for r in prior};added=[r for r in sources if r['artifact']not in known];reg.write_text(json.dumps(prior+added,indent=2)+'\n')
    save(BASE/'NEW_CANONICAL_SCORE_MANIFEST_L_V1.json',dict(state='NEW_WEEK8_PARTIAL_GRADING_SOURCES',sources=[dict(path=r['artifact'],sha256=sha(ROOT/r['artifact']),rows=len(json.loads((ROOT/r['artifact']).read_bytes()))if r['state']=='SCORED'else 1,kind=r['kind'])for r in sources],new_NFL_fits=0,new_model_inference=0,new_original_forecasts=0,private_retention='Existingoriginalcapturecontracts preserved; newbounded private grading derivatives localreadbackonly/offhostpending.'))
    print(json.dumps(dict(registered_sources=len(added),score_sources=len(sources)-1)))


def receipts():
    ledger=ROOT/'registries/EXECUTIONS.jsonl';known={json.loads(line)['run_id']for line in ledger.read_text().splitlines()if line.strip()};manifest=ROOT/'registries/RUN_RESULT_ARTIFACT_MANIFEST.json';old=json.loads(manifest.read_bytes());ids={r['artifact_id']for r in old};events=[];artifacts=[]
    for p in sorted(BASE.rglob('*.json')):
        if any(x.startswith('results-index')for x in p.parts):continue
        rel=p.relative_to(ROOT).as_posix();obj=json.loads(p.read_bytes());state=obj.get('state',obj.get('status','BOUND_WEEK8_SCORE_OR_METADATA'))if isinstance(obj,dict)else'BOUND_AGGREGATE_ARRAY';rid='V2-20261102L-'+hashlib.sha256(rel.encode()).hexdigest()[:16]
        if rid not in known:events.append(dict(run_id=rid,recorded_at_utc=datetime.now(timezone.utc).isoformat(),state=state,receipt=rel,receipt_sha256=sha(p),new_NFL_fits=0,new_model_inference=0,new_original_captures=0,NFL_sample_counts='SharedWeek8 source/outcome census inNEW_SAMPLE_COUNTS_V2.json; artifactviewsare dependent, never additionalindependent observations.',scope='Preserved originalWeek8issuance, actual labels and partial grading; original/replay/numeric/law/source/verification tracks separate. Production unchanged.'))
        aid=rid+'-ARTIFACT'
        if aid not in ids:artifacts.append(dict(artifact_id=aid,run_id=rid,file=rel,sha256=sha(p),bytes=p.stat().st_size,kind='L_public_safe_Week8_aggregate_code_binding_receipt_or_status',status=state,original=False,evidence_availability='PUBLIC_SAFE_AGGREGATES_PRIVATE_DETAILED_ROWS_LOCAL_READBACK_OFFHOST_PENDING',private_locator=None))
    with ledger.open('a')as f:
        for r in events:f.write(json.dumps(r)+'\n')
    if artifacts:
        manifest.write_text(json.dumps(old+artifacts,indent=2)+'\n');p=ROOT/'registries/RUN_RESULT_ARTIFACT_MANIFEST.csv'
        with p.open(newline='')as f:fields=csv.DictReader(f).fieldnames
        with p.open('a',newline='')as f:csv.DictWriter(f,fieldnames=fields,extrasaction='ignore').writerows(artifacts)
    print(json.dumps(dict(new_events=len(events),new_safe_artifacts=len(artifacts))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','receipts'));a=p.parse_args();prepare()if a.action=='prepare'else receipts()
