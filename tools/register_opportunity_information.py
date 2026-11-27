"""Append frozen opportunity results through established source-bound indices.
No grading, fitting, source collection or history reset. Root executor only.
"""
import argparse,contextlib,gzip,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import register_targeted_m2 as established
from nfl_v2.result_index import evaluation,validate_index
BASE=Path('reports/information-skill-follow-through-01/B/opportunity-v1')
SOURCE=BASE/'evaluation-v1/SCORES.json'
PAIRS=BASE/'evaluation-v1/PAIRS.json.gz'
RUN_RECEIPT=BASE/'evaluation-v1/RUN_RECEIPT_V1.json'
PROJECTION=BASE/'INDEX_PROJECTION_V1.json.gz'
RESULTS=BASE/'results-index-v1';ARCHIVE=BASE/'registration-predecessor-v1';RECEIPT=BASE/'REGISTRATION_RECEIPT_V1.json'
REGISTRY=Path('registries/RESULT_ARTIFACTS.json');ANALYSIS_REGISTRY=Path('registries/ANALYSIS_ARTIFACTS.json');POINTER=Path('registries/CURRENT_RESULTS_INDEX.json');EXPORT=Path('reports/abc-championship/EXPORT_INDEX.json')
EXPECTED_PREDECESSOR_FLOORS=dict(result_records=619113,result_artifacts=235,paired_records=25475,analysis_artifacts=24)
@contextlib.contextmanager
def established_paths():
 prior={k:getattr(established,k)for k in('BASE','SOURCE','PAIRS','PROJECTION')}
 try:
  established.BASE=BASE;established.SOURCE=SOURCE;established.PAIRS=PAIRS;established.PROJECTION=PROJECTION
  yield
 finally:
  for k,v in prior.items():setattr(established,k,v)
def source_bound_records(root,item,inputs):
 if item['artifact']!=str(SOURCE):raise ValueError('Unrelated unindexed artifact')
 if item.get('opportunity_information_index_projection')!=str(PROJECTION):raise ValueError('Wrong projection')
 yield from established.projected_records(root,dict(item,targeted_m2_index_projection=str(PROJECTION)),inputs)
def prepare():
 raw=established.read(ROOT/SOURCE)
 if not raw or len({r['record_id']for r in raw})!=len(raw)or any(not r['record_id'].startswith('B-OPP-')for r in raw):raise ValueError('Fresh unique opportunity rows required')
 projected=[established.canonical(r)for r in raw]
 for r in projected:validate_index([evaluation(r,str(SOURCE),year_record={k:r[k]for k in('evaluation_seasons','evaluation_weeks')})])
 tables=established.read(ROOT/BASE/'evaluation-v1/MAIN_TABLES_V1.json.gz')
 procedure_sets={}
 for r in tables:procedure_sets.setdefault((r['target'],r['method']),set()).add(r['procedure_id'])
 if any(len(v)!=1 for v in procedure_sets.values()):raise ValueError('Ambiguous target-specific procedure identity')
 procedures={k:next(iter(v))for k,v in procedure_sets.items()}
 if any(r.get('method')not in('OPP_BASE','OPP_MEAN','OPP_JOINT','DIRECT_ATT')or r.get('target')not in('pass_att','pass_cmp')or r.get('canonical_source_view')is False for r in raw):raise ValueError('Only new own exact target views may append')
 pairs=established.normalize_pairs([dict(r,procedure_id=procedures[r['target'],r['candidate']],comparator_procedure_id=procedures[r['target'],r['control']],population='EXACT_SOURCE_BOUND_NATIVE_QB_OPPORTUNITY_PANEL',history_limit='HRECENT fit; inherited expanding feature memory; current-vintage strict7day; quote clocks/main-alt unknown; development exposed; not original issuance or peer private parity.')for r in established.read(ROOT/PAIRS)])
 run=established.read(ROOT/RUN_RECEIPT)
 if run['state']!='EXECUTED_OPPORTUNITY_LOCAL_NOT_C_ADMITTED'or run['canonical_views']!=len(raw)or run['paired_views']!=len(pairs):raise ValueError('Score receipt count/state mismatch')
 return(raw,projected,pairs,run,dict(kind='FIRST_WRITE_COMPRESSED_PAIRED_ARRAY;NO_REPRESENTATION_REPAIR',scientific_rows_changed=0)),dict(state='PREPARED',source_score_views=len(raw),paired_views=len(pairs))
def predecessor():
    pointer = established.read(ROOT/POINTER)
    manifest_path = pointer["manifest"]
    manifest = established.read(ROOT/manifest_path)
    registry = established.read(ROOT/REGISTRY)
    analysis_registry = established.read(ROOT/ANALYSIS_REGISTRY)
    analysis_manifest = json.loads(established.read_bound(pointer["derived_comparison_manifest"]))
    if analysis_manifest["inputs"] != analysis_registry:
        raise ValueError("Prior analysis registry/manifest mismatch")
    floors = EXPECTED_PREDECESSOR_FLOORS
    if (manifest["record_count"] < floors["result_records"]
            or len(registry) < floors["result_artifacts"]
            or analysis_manifest["record_count"] < floors["paired_records"]
            or len(analysis_registry) < floors["analysis_artifacts"]):
        raise ValueError("Predecessor lost established records/artifacts")
    if any(row["artifact"] == str(SOURCE) for row in registry):
        raise ValueError("OPPORTUNITY already registered; never append twice")
    indexed = {row["source_artifact"] for row in manifest["input_manifests"]}
    pending = [row["artifact"] for row in registry
               if row["state"] in ("SCORED", "SOFTWARE_VERIFIED") and row["artifact"] not in indexed]
    if pending:
        raise ValueError("Unrelated pending registered sources must not piggyback: " + str(pending))
    return pointer, manifest_path, manifest, registry, analysis_registry, analysis_manifest


def execute(prepared, verification, report, disclosed_failed_verification=()):
    raw, projected, pairs, source_run, representation = prepared
    if not verification:
        raise ValueError("Root execution requires passed independent verification receipt(s)")
    verified = []
    for value in verification:
        path = value if value.is_absolute() else ROOT/value
        if not path.resolve().is_relative_to((ROOT/BASE).resolve()):
            raise ValueError("Only public-safe owned OPPORTUNITY verification receipts may bind")
        receipt = established.read(path)
        state = str(receipt.get("state", receipt.get("status", "")))
        if "PASS" not in state:
            raise ValueError("Independent verification not passed: " + str(value))
        verified.append(dict(path=str(path.relative_to(ROOT)), sha256=established.sha(path)))
    disclosures = []
    fit_path = BASE/"independent/REPRESENTATIVE_FIT_REPRODUCTION_V1.json"
    disclose_paths = list(disclosed_failed_verification)
    if (ROOT/fit_path).exists() and 'PASS' not in str(established.read(ROOT/fit_path).get('state','')) and fit_path not in disclose_paths:
        disclose_paths.append(fit_path)
    for value in disclose_paths:
        path = value if value.is_absolute() else ROOT/value
        if not path.resolve().is_relative_to((ROOT/BASE).resolve()):
            raise ValueError("Disclosed verification outside owned OPPORTUNITY scope")
        body = established.read(path)
        state = str(body.get("state", body.get("status", "UNKNOWN")))
        disclosures.append(dict(path=str(path.relative_to(ROOT)), sha256=established.sha(path),
            original_state=state, all_passed=False,
            interpretation="Original failed/limited verification preserved; passing aggregate/law verification does not establish all fitted-model reproduction or promotion."))
    if not (ROOT/report).is_file():
        raise FileNotFoundError(report)
    prior_pointer, prior_path, prior, registry, analysis_registry, analysis_manifest = predecessor()
    for path in (PROJECTION, RESULTS, ARCHIVE, RECEIPT,
                 BASE/"INDEX_BOUND_PAIRED_ANALYSIS_V1.json.gz", BASE/"paired-analysis-index-v1"):
        if (ROOT/path).exists():
            raise FileExistsError("Immutable destination already exists; inspect recovery, do not rerun: " + str(path))
    # Archive exact predecessor bytes before the first canonical mutation.
    archive_bindings = []
    for source in (POINTER, REGISTRY, ANALYSIS_REGISTRY, EXPORT):
        body = (ROOT/source).read_bytes()
        destination = ROOT/ARCHIVE/(source.name.removesuffix(".json")+"_PREDECESSOR.json")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(body)
        archive_bindings.append(dict(source=str(source), archive=str(destination.relative_to(ROOT)),
                                     sha256=hashlib.sha256(body).hexdigest(), bytes=len(body)))
    export_bytes = (ROOT/EXPORT).read_bytes()
    established.save(ROOT/PROJECTION, dict(source_artifact=str(SOURCE),
        source_artifact_sha256=established.sha(ROOT/SOURCE), source_rows=len(raw),
        transformation="Established canonical field projection only; frozen source arrays unchanged; no scoring/fitting.", rows=projected))
    registry.append(dict(artifact=str(SOURCE), state="SCORED",
        kind="QB_TEAM_OPPORTUNITY_AND_FIXED_CONVERSION_EVALUATION",
        opportunity_information_index_projection=str(PROJECTION),
        version_note="Frozen usage-only team-volume/QB-attempt relationship; unchanged conversion; parent, mean isolation, joint law and direct control. Numerical W1-9 and native actual-line W5-9 are distinct. Quote timing/main-alt unknown; exposed reconstruction. Reused control views are not new fits/forecasts; no C admission or website activation."))
    established.save(ROOT/REGISTRY, registry, fresh=False)
    old_reader = established.index.new_records
    try:
        established.index.new_records = source_bound_records
        result = established.index.write(previous=prior_path, output=str(RESULTS),
                                         reuse_prior_csv=True, compressed_delivery=True)
    finally:
        established.index.new_records = old_reader
    current_path = str(RESULTS/"INDEX_MANIFEST.json")
    current = established.read(ROOT/current_path)
    if (current["shards"][:len(prior["shards"])] != prior["shards"]
            or current["csv_parts"][:len(prior["csv_parts"])] != prior["csv_parts"]
            or current["record_count"] != prior["record_count"]+len(raw)
            or result["new_records"] != len(raw)
            or established.read(ROOT/REGISTRY)[:-1] != registry[:-1]):
        raise ValueError("Existing result prefix changed or unexpected append count")
    pointer = dict(prior_pointer, previous_checkpoint=prior_path,
                   manifest=current_path, readable_checkpoint=report)
    added_pairs, old_pair_count = established.append_analysis(pointer, pairs)
    updated_analysis = json.loads(established.read_bound(pointer["derived_comparison_manifest"]))
    old_pair_rows = json.loads(established.read_bound(analysis_manifest["records_json"]))
    new_pair_rows = json.loads(established.read_bound(updated_analysis["records_json"]))
    if (new_pair_rows[:len(old_pair_rows)] != old_pair_rows
            or established.read(ROOT/ANALYSIS_REGISTRY)[:-1] != analysis_registry
            or old_pair_count != analysis_manifest["record_count"]):
        raise ValueError("Established paired analysis prefix changed")
    pointer["opportunity_information_v1"] = dict(report=report, source_artifact=str(SOURCE),
        projection=str(PROJECTION), new_source_score_views=len(raw), new_pairs=added_pairs,
        scope="Frozen opportunity version; source-native ATT/CMP point/law/probability/selection products separate. New index views are not new NFL observations, fits, original selections, C admission or deployment.")
    established.save(ROOT/POINTER, pointer, fresh=False)
    if (ROOT/EXPORT).read_bytes() != export_bytes:
        raise ValueError("Registration must not modify publication discovery independently")
    receipt = dict(state="APPENDED_SOURCE_BOUND_OPPORTUNITY_SCORES_AND_PAIRS",
        source_artifact=str(SOURCE), source_sha256=established.sha(ROOT/SOURCE),
        paired_source=str(PAIRS), paired_source_sha256=established.sha(ROOT/PAIRS),
        new_source_score_views=len(raw), new_pairs=added_pairs,
        prior_result_manifest=dict(path=prior_path, sha256=established.sha(ROOT/prior_path)),
        prior_analysis_manifest=prior_pointer["derived_comparison_manifest"],
        old_result_records_preserved=prior["record_count"], old_result_artifacts_preserved=len(registry)-1,
        old_pairs_preserved=old_pair_count, old_analysis_artifacts_preserved=len(analysis_registry),
        preservation_proofs=dict(prior_result_shards_exact_prefix=True,
            prior_result_CSV_parts_exact_prefix=True, prior_result_registry_exact_prefix=True,
            prior_paired_records_exact_prefix=True, prior_analysis_registry_exact_prefix=True),
        predecessor_archives=archive_bindings, current_result_manifest=current_path,
        current_analysis_manifest=pointer["derived_comparison_manifest"],
        export_index_unchanged=True, export_index_sha256=hashlib.sha256(export_bytes).hexdigest(),
        verification_receipts=verified, index=result,
        verification_scope="Records valid scores of frozen forecasts and canonical projection; no assertion that every fit was independently reproduced, admitted or promoted.",
        disclosed_failed_verifications=disclosures, independent_all_fits_reproduced=False,
        output_preserving_representation=representation,
        source_scoring_receipt=dict(path=str(RUN_RECEIPT),
            sha256=established.sha(ROOT/RUN_RECEIPT),
            new_fits_by_that_scoring=source_run.get("new_fits")),
        new_fits_by_registration=0, new_scoring_by_registration=0,
        new_forecasts_by_registration=0, new_NFL_observations_by_registration=0,
        C_admission=False, website_activation=False)
    established.save(ROOT/RECEIPT, receipt)
    print(json.dumps(receipt))


def main():
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--verification',type=Path,action='append',default=[]);p.add_argument('--report',default=str(BASE/'README.md'));a=p.parse_args()
 with established_paths():
  ready,status=prepare()
  if a.execute:execute(ready,a.verification,a.report)
  else:print(json.dumps(status))
if __name__=='__main__':main()
