#!/usr/bin/env python3
"""Validate derived comparisons and default score-version bindings, without NFL rows."""
import collections
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_bound(binding, path_key="path"):
    path = Path(binding[path_key])
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Public bindings require repository-relative paths")
    body = (ROOT / path).read_bytes()
    if hashlib.sha256(body).hexdigest() != binding["sha256"]:
        raise ValueError("Changed bound artifact: " + str(path))
    return body


def main():
    pointer = json.loads((ROOT / "registries/CURRENT_RESULTS_INDEX.json").read_text())
    default = json.loads(read_bound(pointer["default_score_version_manifest"]))
    if pointer["manifest"] != default["audit_manifest"]:
        raise ValueError("Legacy audit index binding changed")
    audit_body = (ROOT / default["audit_manifest"]).read_bytes()
    if hashlib.sha256(audit_body).hexdigest() != default["audit_manifest_sha256"]:
        raise ValueError("Immutable all-audit index changed")
    selected = json.loads(read_bound(default["selected_ids"]))
    if len(selected) != len(set(selected)):
        raise ValueError("Duplicate canonical evaluation IDs")
    expected_ids = set(selected)
    actual_ids = set()
    csv_rows = 0
    for part in default["csv_parts"]:
        body = read_bound(part)
        rows = list(csv.DictReader(body.decode().splitlines()))
        if len(body) != part["bytes"] or len(rows) != part["rows"]:
            raise ValueError("Canonical CSV part size/count changed")
        for row in rows:
            if row["test_id"] in actual_ids:
                raise ValueError("Repeated canonical ID")
            actual_ids.add(row["test_id"])
            csv_rows += 1
    if actual_ids != expected_ids or csv_rows != default["selected_evaluation_views"]:
        raise ValueError("Canonical default coverage mismatch")

    manifest = json.loads(read_bound(pointer["derived_comparison_manifest"]))
    registry = json.loads((ROOT / "registries/ANALYSIS_ARTIFACTS.json").read_text())
    if registry != manifest["inputs"]:
        raise ValueError("Derived comparison registry is stale")
    sources = {}
    source_hashes = {}
    for source in registry:
        value = json.loads(read_bound(source, "artifact"))
        rows = value if isinstance(value, list) else value["rows"]
        if len(rows) != source["rows"] or source["new_univariate_forecast_views"] != 0:
            raise ValueError("Derived comparison input count/kind mismatch")
        sources[source["artifact"]] = rows
        source_hashes[source["artifact"]] = source["sha256"]
    rows = json.loads(read_bound(manifest["records_json"]))
    csv_records = list(csv.DictReader(read_bound(manifest["records_csv"]).decode().splitlines()))
    if len(csv_records) != len(rows):
        raise ValueError("Derived CSV/JSON row count mismatch")
    if len(rows) != manifest["record_count"] or len({r["analysis_id"] for r in rows}) != len(rows):
        raise ValueError("Derived comparison count/identity mismatch")
    counts = collections.Counter()
    source_indices = collections.defaultdict(set)
    for row in rows:
        counts[row["state"]] += 1
        n = row["n"]
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError("Paired support must be a nonnegative integer")
        losses = [row["candidate_error"], row["comparator_error"]]
        delta = row["absolute_error_change"]
        if n:
            if row["state"] != "PAIRED_LOSS_SCORED" or not all(
                isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in losses
            ) or not math.isclose(losses[0] - losses[1], delta, rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError("Paired loss arithmetic/state mismatch")
        elif row["state"] != "NO_SUPPORTED_PAIRED_ROWS" or any(v is not None for v in losses + [delta]):
            raise ValueError("Unsupported comparison lost its null loss")
        source, index = row["source_artifact"], row["source_row_index"]
        if index in source_indices[source] or not 0 <= index < len(sources[source]):
            raise ValueError("Derived source-row binding repeated or absent")
        source_indices[source].add(index)
        original = sources[source][index]
        carry = "candidate_metrics" in original
        uncertainty = original.get("uncertainty", original)
        proc = original.get("candidate_procedure_id", original.get("procedure_id"))
        product = original.get("candidate_product_id", original.get("product_id"))
        contrast = original.get("comparison", original.get("contrast"))
        histories = (original["history_regime"], original.get("comparator_history_regime")) if carry else contrast.split("_MINUS_")
        expected = {
            "source_artifact_sha256": source_hashes[source],
            "procedure_id": proc, "product_id": product,
            "target": original.get("target", "rush_att" if carry else None),
            "population": original["population"], "season": original["season"],
            "history_regime": original["history_regime"], "policy_id": original.get("policy_id"),
            "contrast": contrast, "view": original["fallback_view"],
            "cohort_id": original.get("cohort_id"), "position": original.get("position"),
            "metric": "MAE" if carry else original["metric"],
            "n": original.get("paired_n", original.get("n")),
            "candidate_error": original["candidate_metrics"].get("mae") if carry else original.get("candidate_error"),
            "comparator_error": original["comparator_metrics"].get("mae") if carry else original.get("comparator_error"),
            "absolute_error_change": original.get("native_error_delta") if carry else original.get("delta"),
            "relative_error_change": original.get("relative_error_delta", original.get("relative_error_change")),
            "membership_sha256": original.get("paired_membership_sha256", original.get("membership_sha256")),
            "week_clusters": uncertainty.get("week_clusters"),
            "week_interval": uncertainty.get("week_interval"),
            "week_interval_status": uncertainty.get("week_interval_status"),
            "game_cluster_se": uncertainty.get("game_cluster_sensitivity_se"),
            "history_status": original.get("requested_history_status", original.get("history_limit")),
            "candidate_history_regime": histories[0], "comparator_history_regime": histories[1],
            "comparator_procedure_id": original.get("comparator_procedure_id", proc),
            "comparator_product_id": original.get("comparator_product_id", product),
            "query_rows": original.get("query_rows"), "unresolved_rows": original.get("unresolved_rows"),
            "fullsystem_n": original.get("fullsystem_n"),
            "contribution_to_fullsystem_delta": original.get("contribution_to_fullsystem_delta"),
            "candidate_fallback_rows": original["candidate_metrics"].get("fallback_rows") if carry else None,
            "comparator_fallback_rows": original["comparator_metrics"].get("fallback_rows") if carry else None,
        }
        if any(row.get(k) != v for k, v in expected.items()):
            raise ValueError("Derived projection changed a bound source field")
        relative = row["relative_error_change"]
        if not n or losses[1] == 0:
            if relative is not None:
                raise ValueError("Unsupported/zero-control relative change must be null")
        elif not math.isclose(relative, delta / losses[1], rel_tol=1e-10, abs_tol=1e-10):
            raise ValueError("Paired relative loss change mismatch")
        if any(row[k] != 0 for k in ("new_fits", "new_forecasts", "new_NFL_observations")):
            raise ValueError("Derived analysis inflated independent evidence")
    for row, csv_row in zip(rows, csv_records):
        expected = {k: json.dumps(v, separators=(",", ":")) if isinstance(v, (dict, list))
                    else "" if v is None else str(v) for k, v in row.items()}
        if csv_row != expected:
            raise ValueError("Derived CSV disagrees with JSON")
    if dict(counts) != manifest["status_counts"] or any(
        len(source_indices[k]) != len(v) for k, v in sources.items()
    ):
        raise ValueError("Derived comparison status/source coverage mismatch")
    for binding in (pointer["procedure_rankings"], pointer["top_five_rankings"]):
        ranking = json.loads(read_bound(binding))
        if not {r["test_id"] for r in ranking} <= expected_ids:
            raise ValueError("Default ranking includes an excluded score version")
    print(json.dumps({"state": "PASS", "canonical_evaluation_views": csv_rows,
                      "derived_comparison_views": len(rows), "status_counts": dict(counts),
                      "new_NFL_observations": 0}))


if __name__ == "__main__":
    main()
