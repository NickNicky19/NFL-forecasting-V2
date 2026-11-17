"""Prepare/append SKILL source views through the established result indices.

Default preparation is read-only. Only the registered B root executor may use
--execute after scoring and independent verification. This script neither
scores, fits, collects sources nor changes the shared C evaluator.
"""
from __future__ import annotations

import argparse
import contextlib
import gzip
import hashlib
import json
import sys
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import register_targeted_m2 as established
from nfl_v2.result_index import evaluation, validate_index

BASE = Path("reports/information-skill-01/B")
SOURCE = BASE / "evaluation-v2/SCORES.json"
PAIRS = BASE / "evaluation-v2/PAIRED_COMPARISONS_V1.json.gz"
RUN_RECEIPT = BASE / "evaluation-v2/RUN_RECEIPT_V1.json"
REPRESENTATION = BASE / "evaluation-v2/LOSSLESS_REPRESENTATION_RECEIPT_V1.json"
PROJECTION = BASE / "INDEX_PROJECTION_V1.json.gz"
RESULTS = BASE / "results-index-v1"
ARCHIVE = BASE / "registration-predecessor-v1"
RECEIPT = BASE / "REGISTRATION_RECEIPT_V1.json"
REGISTRY = Path("registries/RESULT_ARTIFACTS.json")
ANALYSIS_REGISTRY = Path("registries/ANALYSIS_ARTIFACTS.json")
POINTER = Path("registries/CURRENT_RESULTS_INDEX.json")
EXPORT = Path("reports/abc-championship/EXPORT_INDEX.json")
EXPECTED_PREDECESSOR_FLOORS = dict(result_records=617723, result_artifacts=234,
                                   paired_records=23423, analysis_artifacts=23)


@contextlib.contextmanager
def established_paths():
    """Reuse established pure projections/analysis writer with owned paths."""
    replacements = dict(BASE=BASE, SOURCE=SOURCE, PAIRS=PAIRS, PROJECTION=PROJECTION)
    prior = {key: getattr(established, key) for key in replacements}
    try:
        for key, value in replacements.items():
            setattr(established, key, value)
        yield
    finally:
        for key, value in prior.items():
            setattr(established, key, value)


def source_bound_records(root, item, inputs):
    if item["artifact"] != str(SOURCE):
        raise ValueError("Unrelated unindexed source: complete its existing owner task separately")
    if item.get("information_skill_index_projection") != str(PROJECTION):
        raise ValueError("SKILL projection binding missing")
    compatible = dict(item, targeted_m2_index_projection=str(PROJECTION))
    # The historical helper name is a compatibility key, not M2 identity/history.
    yield from established.projected_records(root, compatible, inputs)


def validate_representation():
    """Authenticate lossless retained bytes; never rerun their calculations."""
    receipt = established.read(ROOT/REPRESENTATION)
    if (receipt.get("state") != "LOSSLESS_REPACK_WITH_CAP_UNCHANGED;NO_RESCORING"
            or receipt.get("decoded_identity_verified_files") != 11
            or receipt.get("all_original_decoded_bytes_identical") is not True
            or receipt.get("unchanged_cap") != 8388608
            or any(receipt.get(name) != 0 for name in
                   ("changed_scientific_rows", "new_grading_runs", "new_fits"))):
        raise ValueError("Exact lossless representation contract required")
    capsule = ROOT/receipt["original_capsule"]
    manifest = established.read(ROOT/receipt["original_manifest"])
    if (established.sha(capsule) != receipt["original_capsule_sha256"]
            or manifest.get("cap") != 8388608
            or manifest.get("members") != receipt.get("members")):
        raise ValueError("Preserved failed-output archive/manifest mismatch")
    members = receipt["members"]
    if len(members) != 11 or len({row["original_path"] for row in members}) != 11:
        raise ValueError("Exactly eleven original output bindings required")
    with tarfile.open(capsule, "r:gz") as archive:
        files = {member.name: member for member in archive.getmembers() if member.isfile()}
        if set(files) != {row["original_path"] for row in members} | {"MANIFEST.json"}:
            raise ValueError("Original failure archive membership changed")
        if archive.extractfile(files["MANIFEST.json"]).read() != (ROOT/receipt["original_manifest"]).read_bytes():
            raise ValueError("Preserved original manifest differs from archive")
        for row in members:
            old = archive.extractfile(files[row["original_path"]]).read()
            new_path = ROOT/BASE/row["new_path"]
            if not new_path.resolve().is_relative_to((ROOT/BASE/"evaluation-v2").resolve()):
                raise ValueError("Representation destination outside owned version")
            new = new_path.read_bytes()
            if (len(old) != row["original_bytes"]
                    or hashlib.sha256(old).hexdigest() != row["original_sha256"]
                    or len(new) != row["new_bytes"]
                    or hashlib.sha256(new).hexdigest() != row["new_sha256"]):
                raise ValueError("Bound original/new output bytes changed")
            recovered = gzip.decompress(new) if row["original_path"].endswith("PAIRED_COMPARISONS_V1.json") else new
            if recovered != old or row.get("recovered_original_bytes_identical") is not True:
                raise ValueError("Representation changed original decoded output")
    if established.sha(ROOT/SOURCE) != receipt["canonical_SCORES_sha256"]:
        raise ValueError("Canonical score bytes changed during representation repair")
    measured = sum(path.stat().st_size for path in (ROOT/BASE/"evaluation-v2").rglob("*") if path.is_file())
    if measured >= 8388608:
        raise ValueError("Complete final representation exceeds unchanged8MiB cap")
    return dict(path=str(REPRESENTATION), sha256=established.sha(ROOT/REPRESENTATION),
                original_capsule=receipt["original_capsule"],
                original_capsule_sha256=receipt["original_capsule_sha256"],
                decoded_files_verified=11, unchanged_SCORES_sha256=receipt["canonical_SCORES_sha256"],
                measured_final_version_bytes=measured, unchanged_cap=8388608,
                changed_scientific_rows=0, new_grading_runs=0)


def prepare():
    required = [SOURCE, PAIRS, RUN_RECEIPT, REPRESENTATION]
    missing = [str(path) for path in required if not (ROOT/path).exists()]
    if missing:
        return None, dict(state="PREPARED_NO_CANONICAL_MUTATIONS", pending=missing)
    raw = established.read(ROOT/SOURCE)
    if (not isinstance(raw, list) or not raw
            or len({row["record_id"] for row in raw}) != len(raw)):
        raise ValueError("SKILL source must have unique nonempty evaluation IDs")
    if any(not row["record_id"].startswith("B-SKILL-") for row in raw):
        raise ValueError("Only fresh source-bound SKILL evaluation IDs may append")
    if any(row.get("canonical_source_view") is False
           or row.get("method") in ("RETAINED_B0", "RETAINED_B2") for row in raw):
        raise ValueError("Aggregate-only/reused B0/B2 controls cannot be registered again")
    projected = [established.canonical(row) for row in raw]
    for row in projected:
        record = evaluation(row, str(SOURCE), year_record={
            key: row[key] for key in ("evaluation_seasons", "evaluation_weeks")})
        validate_index([record])
    source_pairs = established.read(ROOT/PAIRS)
    references = established.read(ROOT/BASE/"evaluation-v2/PUBLIC_RETAINED_CONTROL_REFERENCES_V1.json")
    procedure_sets = {}
    for row in raw + references["records"]:
        procedure_sets.setdefault(row["method"], set()).add(row["procedure_id"])
    if any(len(values) != 1 for values in procedure_sets.values()):
        raise ValueError("Method alias has ambiguous procedure identity")
    procedures = {method: next(iter(values)) for method, values in procedure_sets.items()}
    for row in source_pairs:
        if row["candidate"] not in procedures or row["control"] not in procedures:
            raise ValueError("Pair procedure identity lacks a bound source record")
    # Source pairs carry method/policy names. Bind their exact procedure IDs
    # from the same immutable source views; do not mutate/recompute the pairs.
    pairs = established.normalize_pairs([dict(row,
        procedure_id=procedures[row["candidate"]],
        comparator_procedure_id=procedures[row["control"]],
        population=row.get("population", "EXACT_SOURCE_BOUND_QB_PASS_MIX_INFORMATION_PANEL"),
        history_limit=row.get("history_limit", "Current-vintage strict7day chronological SKILL pass-mix information reconstruction; exposed development, source-native masks/fallbacks retained. No original issuance, authenticated quote timing or private peer-fit parity."))
        for row in source_pairs])
    run = established.read(ROOT/RUN_RECEIPT)
    if run.get("state") != "EXECUTED_SKILL_LOCAL_NOT_C_ADMITTED;OUTPUT_PRESERVING_REPRESENTATION_REPAIR":
        raise ValueError("Final source scoring receipt not complete")
    if run.get("canonical_views") != len(raw) or run.get("paired_views") != len(pairs):
        raise ValueError("Source scoring receipt/view count mismatch")
    representation = validate_representation()
    return (raw, projected, pairs, run, representation), dict(
        state="PREPARED_VALIDATED_NO_CANONICAL_MUTATIONS",
        source_sha256=established.sha(ROOT/SOURCE),
        source_score_views=len(raw), derived_pairs=len(pairs),
        representation=representation,
        new_fits=0, new_scoring=0, new_NFL_observations=0)


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
        raise ValueError("SKILL already registered; never append twice")
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
            raise ValueError("Only public-safe owned SKILL verification receipts may bind")
        receipt = established.read(path)
        state = str(receipt.get("state", receipt.get("status", "")))
        if "PASS" not in state:
            raise ValueError("Independent verification not passed: " + str(value))
        verified.append(dict(path=str(path.relative_to(ROOT)), sha256=established.sha(path)))
    disclosures = []
    fit_path = BASE/"independent/FIT_REPRODUCTION_V1.json"
    disclose_paths = list(disclosed_failed_verification)
    if (ROOT/fit_path).exists() and fit_path not in disclose_paths:
        disclose_paths.append(fit_path)
    for value in disclose_paths:
        path = value if value.is_absolute() else ROOT/value
        if not path.resolve().is_relative_to((ROOT/BASE).resolve()):
            raise ValueError("Disclosed verification outside owned SKILL scope")
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
        kind="QB_PASS_MIX_INFORMATION_AND_CONDITIONAL_CONVERSION_FIXED_SELECTION_EVALUATION",
        information_skill_index_projection=str(PROJECTION),
        version_note="Separately frozen SKILL pass-context information and learned composition comparison; unchanged attempt law. Numerical W1-9 and native actual-line W5-9 are distinct. Quote timing/main-alt unknown; exposed reconstruction. Reused control views are not new fits/forecasts; no C admission or website activation."))
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
    pointer["information_skill_01"] = dict(report=report, source_artifact=str(SOURCE),
        projection=str(PROJECTION), new_source_score_views=len(raw), new_pairs=added_pairs,
        scope="Original SKILL version; source-native point/law/probability/selection products separate. New index views are not new NFL observations, fits, original selections, C admission or deployment.")
    established.save(ROOT/POINTER, pointer, fresh=False)
    if (ROOT/EXPORT).read_bytes() != export_bytes:
        raise ValueError("Registration must not modify publication discovery independently")
    receipt = dict(state="APPENDED_SOURCE_BOUND_SKILL_SCORES_AND_PAIRS",
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--verification", type=Path, action="append", default=[])
    parser.add_argument("--disclosed-failed-verification", type=Path, action="append", default=[])
    parser.add_argument("--report", default=str(BASE/"README.md"))
    args = parser.parse_args()
    with established_paths():
        prepared, status = prepare()
        if not args.execute:
            print(json.dumps(status))
            return
        if prepared is None:
            raise FileNotFoundError(status["pending"])
        execute(prepared, args.verification, args.report, args.disclosed_failed_verification)


if __name__ == "__main__":
    main()
