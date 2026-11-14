#!/usr/bin/env python3
"""Check additive v2 columns against sources and retain every reviewed v1 value."""
import csv
import hashlib
import json
from pathlib import Path
import resource
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_bound(reference, key="path"):
    p = Path(reference[key])
    assert not p.is_absolute() and ".." not in p.parts
    p = ROOT / p
    assert digest(p) == reference["sha256"]
    return json.loads(p.read_text())


def main():
    started = time.monotonic()
    first_manifest_path = HERE / "paired-analysis-index/ANALYSIS_MANIFEST.json"
    assert digest(first_manifest_path) == "c7e68355232535d71ec69c8e24693d49fe03dec83ddd737afd93dab835299b48"
    first = json.loads(first_manifest_path.read_text())
    old = read_bound(first["records_json"])
    pointer_path = ROOT / "registries/CURRENT_RESULTS_INDEX.json"
    pointer = json.loads(pointer_path.read_text())
    manifest = read_bound(pointer["derived_comparison_manifest"])
    assert manifest["schema"] == "v2-derived-paired-analysis-index-v2"
    assert manifest["inputs"] == first["inputs"]
    assert json.loads((ROOT / "registries/ANALYSIS_ARTIFACTS.json").read_text()) == manifest["inputs"]
    for name in ("record_count", "status_counts", "new_fits", "new_forecasts", "new_NFL_observations", "univariate_audit_index"):
        assert manifest[name] == first[name]
    rows = read_bound(manifest["records_json"])
    assert len(rows) == len(old) == 18708
    source_fields = 0
    old_fields = 0
    cursor = 0
    for ref in manifest["inputs"]:
        source = read_bound(ref, "artifact")
        source = source if isinstance(source, list) else source["rows"]
        assert len(source) == ref["rows"]
        for original in source:
            baseline, current = old[cursor], rows[cursor]
            cursor += 1
            assert {k: current[k] for k in baseline} == baseline
            old_fields += len(baseline)
            carry = "candidate_metrics" in original
            if carry:
                candidate_history = original["history_regime"]
                comparator_history = original["comparator_history_regime"]
                assert original["query_rows"] == original["paired_n"] + original["unresolved_rows"]
            else:
                candidate_history, comparator_history = original["contrast"].split("_MINUS_")
            additions = {
                "candidate_history_regime": candidate_history,
                "comparator_history_regime": comparator_history,
                "comparator_procedure_id": original["comparator_procedure_id"] if carry else original["procedure_id"],
                "comparator_product_id": original["comparator_product_id"] if carry else original["product_id"],
                "query_rows": original.get("query_rows"), "unresolved_rows": original.get("unresolved_rows"),
                "fullsystem_n": original.get("fullsystem_n"),
                "contribution_to_fullsystem_delta": original.get("contribution_to_fullsystem_delta"),
                "candidate_fallback_rows": original["candidate_metrics"].get("fallback_rows") if carry else None,
                "comparator_fallback_rows": original["comparator_metrics"].get("fallback_rows") if carry else None,
            }
            assert set(current) - set(baseline) == set(additions)
            assert {k: current[k] for k in additions} == additions
            source_fields += len(additions)
    csv_path = ROOT / manifest["records_csv"]["path"]
    assert digest(csv_path) == manifest["records_csv"]["sha256"]
    csv_cells = 0
    with csv_path.open(newline="") as stream:
        for i, actual in enumerate(csv.DictReader(stream)):
            expected = {k: json.dumps(v, separators=(",", ":")) if isinstance(v, (list, dict)) else "" if v is None else str(v) for k, v in rows[i].items()}
            assert actual == expected
            csv_cells += len(expected)
        assert i + 1 == len(rows)
    # Canonical metrics and ranking files are unchanged from the full prior readback.
    old_review = json.loads((HERE / "PAIRED_WRAPPER_AND_DEFAULT_POINTER_INDEPENDENT_REVIEW.json").read_text())
    for reference, expected_sha in ((pointer["procedure_rankings"], "9f24f64ab8c004e42ed504da2cf8fb09287807b79bfe4d62f30db7b98f66d6a6"),
                                    (pointer["top_five_rankings"], "f7b540ccf688bb77672646b7a0af162f987a9669d836a4f44651e497205803d8"),
                                    (pointer["default_score_version_manifest"], "3d4f226156cfa492216b0aff0c187db9cdb6913e3b0f32a5b842034e58cbbd57")):
        assert reference["sha256"] == expected_sha
        read_bound(reference)
    assert old_review["exact_source_rows"] == len(rows)
    assert digest(ROOT / pointer["manifest"]) == "5357620f2219bd3bfe9108bad72a9d3aa19e15a7c54426fbc5777be74150198d"
    report = dict(
        state="PASS_ADDITIVE_V2_SOURCE_PROJECTION_AND_CURRENT_POINTER",
        pointer_sha256=digest(pointer_path), manifest_sha256=pointer["derived_comparison_manifest"]["sha256"],
        wrapper_json_sha256=manifest["records_json"]["sha256"], wrapper_csv_sha256=manifest["records_csv"]["sha256"],
        original_v1_manifest_sha256=digest(first_manifest_path), original_v1_review_sha256=digest(HERE / "PAIRED_WRAPPER_AND_DEFAULT_POINTER_INDEPENDENT_REVIEW.json"),
        source_rows=cursor, unchanged_v1_fields=old_fields, new_source_derived_fields=source_fields,
        csv_cells=csv_cells, status_counts=manifest["status_counts"],
        analysis_ids_metrics_membership_uncertainty_unchanged=True, source_artifacts_unchanged=5,
        canonical_score_manifest_and_rankings_unchanged=True,
        coverage_checker_sha256=digest(ROOT / "tools/check_analysis_index_coverage.py"),
        scope="Every prior field retained; candidate/comparator identities, history, query/fallback counts and full-system contribution independently match exact source rows. Missing optional source fields remain null. No NFL raw replay or bootstrap rerun.",
        new_fits=0, inference_calls=0, new_forecasts=0, new_NFL_observations=0,
        current2026_week8_outcomes_read=0, wall_seconds=time.monotonic()-started,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
    )
    (HERE / "PAIRED_WRAPPER_V2_AND_POINTER_INDEPENDENT_READBACK.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k: report[k] for k in ("state", "source_rows", "unchanged_v1_fields", "new_source_derived_fields", "csv_cells", "wall_seconds", "peak_rss_bytes")}))


if __name__ == "__main__":
    main()
