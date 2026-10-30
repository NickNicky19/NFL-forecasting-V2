#!/usr/bin/env python3
"""Read public aggregate bytes; verify derived projections without NFL replay."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import resource
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bound(ref, key="path"):
    p = Path(ref[key])
    assert not p.is_absolute() and ".." not in p.parts
    p = ROOT / p
    assert sha(p) == ref["sha256"], str(p)
    return json.loads(p.read_text())


def near(a, b):
    if a is None or b is None:
        assert a is b, (a, b)
    else:
        assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-10), (a, b)


def main():
    started = time.monotonic()
    pointer_path = ROOT / "registries/CURRENT_RESULTS_INDEX.json"
    pointer = json.loads(pointer_path.read_text())
    assert pointer["manifest_role"] == "ALL_AUDIT_IMMUTABLE_BACKWARD_COMPATIBLE"
    assert pointer["default_view"] == "CURRENT_CANONICAL_SCORE_VERSIONS"
    current = bound(pointer["default_score_version_manifest"])
    audit = ROOT / pointer["manifest"]
    assert sha(audit) == current["audit_manifest_sha256"]
    assert current["audit_manifest"] == pointer["manifest"]
    assert current["selected_evaluation_views"] == 124630
    assert current["excluded_evaluation_views"] == 20567
    selected = set(bound(current["selected_ids"]))
    assert len(selected) == 124630
    rankings = bound(pointer["procedure_rankings"])
    top5 = bound(pointer["top_five_rankings"])
    assert len(rankings) == 237 and len(top5) == 170
    assert {r["test_id"] for r in rankings + top5} <= selected

    manifest = bound(pointer["derived_comparison_manifest"])
    registry_path = ROOT / "registries/ANALYSIS_ARTIFACTS.json"
    assert json.loads(registry_path.read_text()) == manifest["inputs"]
    assert len(manifest["inputs"]) == 5
    assert all(manifest[k] == 0 for k in ("new_fits", "new_forecasts", "new_NFL_observations"))
    projected = bound(manifest["records_json"])
    assert len(projected) == manifest["record_count"] == 18708
    counts = collections.Counter()
    ids = set()
    fields_checked = 0
    zero_controls = 0
    row_cursor = 0
    metrics = collections.Counter()
    sources_checked = []
    for source_ref in manifest["inputs"]:
        decoded = bound(source_ref, "artifact")
        source_rows = decoded if isinstance(decoded, list) else decoded["rows"]
        assert len(source_rows) == source_ref["rows"]
        assert source_ref["new_univariate_forecast_views"] == 0
        semantic_keys = set()
        for i, original in enumerate(source_rows):
            actual = projected[row_cursor]
            row_cursor += 1
            carry = "candidate_metrics" in original
            n = original["paired_n"] if carry else original["n"]
            assert type(n) is int and n >= 0
            a = original["candidate_metrics"]["mae"] if carry else original.get("candidate_error")
            b = original["comparator_metrics"]["mae"] if carry else original.get("comparator_error")
            delta = original["native_error_delta"] if carry else original.get("delta")
            relative = original.get("relative_error_delta") if carry else original.get("relative_error_change")
            if n:
                assert all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in (a, b))
                near(delta, a - b)
                near(relative, None if b == 0 else delta / b)
                zero_controls += int(b == 0)
            else:
                assert a is None and b is None and delta is None and relative is None
            procedure = original["candidate_procedure_id"] if carry else original["procedure_id"]
            product = original["candidate_product_id"] if carry else original["product_id"]
            target = original.get("target", "rush_att" if carry else None)
            metric = "MAE" if carry else original["metric"]
            assert metric in {"MAE", "MSE", "Brier"}
            metrics[metric] += 1
            contrast = original["comparison"] if carry else original["contrast"]
            identity = [procedure, product, target, original["population"], original["season"],
                        original["history_regime"], original.get("policy_id"), metric, contrast,
                        original["fallback_view"], original.get("cohort_id"), original.get("position"),
                        original.get("comparator_procedure_id"), original.get("comparator_history_regime")]
            semantic = json.dumps(identity, separators=(",", ":"))
            assert semantic not in semantic_keys
            semantic_keys.add(semantic)
            analysis_id = "PAIR-" + hashlib.sha256(json.dumps([source_ref["artifact"], identity], separators=(",", ":")).encode()).hexdigest()[:20]
            assert analysis_id not in ids
            ids.add(analysis_id)
            uncertainty = original.get("uncertainty", original)
            state = "PAIRED_LOSS_SCORED" if n else "NO_SUPPORTED_PAIRED_ROWS"
            counts[state] += 1
            expected = {
                "analysis_id": analysis_id, "kind": "DERIVED_PAIRED_LOSS_ANALYSIS", "state": state,
                "procedure_id": procedure, "product_id": product, "target": target,
                "population": original["population"], "season": original["season"],
                "history_regime": original["history_regime"], "policy_id": original.get("policy_id"),
                "contrast": contrast, "view": original["fallback_view"],
                "cohort_id": original.get("cohort_id"), "position": original.get("position"),
                "metric": metric, "n": n, "candidate_error": a, "comparator_error": b,
                "absolute_error_change": delta, "relative_error_change": relative,
                "membership_sha256": original["paired_membership_sha256"] if carry else original["membership_sha256"],
                "week_clusters": uncertainty.get("week_clusters"), "week_interval": uncertainty.get("week_interval"),
                "week_interval_status": uncertainty.get("week_interval_status"),
                "game_cluster_se": uncertainty.get("game_cluster_sensitivity_se"),
                "history_status": original.get("requested_history_status", original.get("history_limit")),
                "precision_status": "No new per-mask precision claim; retained univariate precision remains linked in audit index",
                "source_artifact": source_ref["artifact"], "source_artifact_sha256": source_ref["sha256"],
                "source_row_index": i, "new_fits": 0, "new_forecasts": 0, "new_NFL_observations": 0,
            }
            assert actual == expected, (source_ref["artifact"], i)
            assert len(actual["membership_sha256"]) == 64
            fields_checked += len(expected)
        sources_checked.append({"path": source_ref["artifact"], "sha256": source_ref["sha256"], "rows": len(source_rows)})
    assert row_cursor == len(projected)
    assert dict(counts) == manifest["status_counts"] == {"PAIRED_LOSS_SCORED": 17658, "NO_SUPPORTED_PAIRED_ROWS": 1050}
    csv_ref = manifest["records_csv"]
    csv_path = ROOT / csv_ref["path"]
    assert sha(csv_path) == csv_ref["sha256"]
    csv_fields = 0
    with csv_path.open(newline="") as stream:
        csv_rows = csv.DictReader(stream)
        for i, actual_csv in enumerate(csv_rows):
            expected_json = projected[i]
            assert list(actual_csv) == list(expected_json)
            for key, value in expected_json.items():
                cell = actual_csv[key]
                if value is None:
                    assert cell == ""
                elif isinstance(value, (dict, list)):
                    assert json.loads(cell) == value
                elif type(value) is int:
                    assert int(cell) == value
                elif type(value) is float:
                    assert float(cell) == value
                else:
                    assert cell == value
                csv_fields += 1
        assert i + 1 == len(projected)
    report = dict(
        state="PASS_EXACT_DERIVED_PROJECTION_AND_DEFAULT_POINTER_READBACK",
        pointer_sha256=sha(pointer_path), manifest_sha256=pointer["derived_comparison_manifest"]["sha256"],
        wrapper_json_sha256=manifest["records_json"]["sha256"], wrapper_csv_sha256=csv_ref["sha256"],
        builder_sha256=sha(ROOT / "tools/build_paired_analysis_index.py"),
        coverage_checker_sha256=sha(ROOT / "tools/check_analysis_index_coverage.py"),
        exact_source_rows=len(projected), exact_projected_fields=fields_checked, exact_csv_cells=csv_fields,
        status_counts=dict(counts), source_artifacts=sources_checked, metrics=dict(metrics),
        supported_zero_comparator_cases_retaining_null_relative=zero_controls,
        default_canonical_evaluation_views=124630, default_procedure_product_representatives=237,
        default_top_five_rows=170, immutable_all_audit_records=145219,
        semantic_scope="Derived comparisons retain native losses, exact source rows, common-mask hashes and uncertainty; not new univariate evaluations, methods, forecasts or NFL observations.",
        limitation="Public aggregate projection/source equality and front-door bindings only; underlying NFL rows and bootstrap calculations were already independently audited in separate reviews and were not rerun here.",
        new_fits=0, inference_calls=0, new_forecasts=0, new_NFL_observations=0,
        current2026_week8_outcomes_read=0, wall_seconds=time.monotonic()-started,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
    )
    (HERE / "PAIRED_WRAPPER_AND_DEFAULT_POINTER_INDEPENDENT_REVIEW.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k: report[k] for k in ("state", "exact_source_rows", "exact_projected_fields", "exact_csv_cells", "wall_seconds", "peak_rss_bytes")}))


if __name__ == "__main__":
    main()
