"""Verify append-only exact-grid correction against independent projection.

Reads only retained historical aggregate artifacts. No fits or outcome fetches.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "reports/continuation-20261030"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(row):
    return json.dumps(row, sort_keys=True, separators=(",", ":"))


def verify():
    audit_path = BASE / "CHART_EXACT_GRID_PRECISION_AUDIT.json"
    corrected_path = BASE / "chart-grid-precision-correction-v1/SCORES.json"
    audit = json.loads(audit_path.read_text())
    corrected = json.loads(corrected_path.read_text())
    dimensions = ("record_id", "procedure_id", "history_regime", "policy_id", "target",
                  "population", "product_id", "week", "season", "position",
                  "fallback_view", "cohort_id")
    projections = {}
    originals = {}
    for artifact, digest in audit["source_hashes"].items():
        assert sha(ROOT / artifact) == digest
        originals[artifact] = json.loads((ROOT / artifact).read_text())
    for row in audit["projection"]:
        key = (row["source_score_artifact"], identity({d: row[d] for d in dimensions}))
        assert key not in projections
        projections[key] = row
    checks = 0
    for row in corrected:
        artifact = row["supersedes_score_artifact"]
        dims = row["supersedes_source_identity"]
        key = (artifact, identity(dims))
        expected = projections.pop(key)
        assert row["product_id"] == "lower_median"
        assert row["supersedes_source_sha256"] == audit["source_hashes"][artifact]
        assert row["precision_counts_exact_grid"] == expected["precision"]
        for metric, counts in expected["precision"].items():
            assert row[metric] == counts["exact_grid_rate"]
            assert row["original_float_precision"][metric] == counts["original_float_rate"]
            assert counts["denominator"] == expected["n"]
            checks += 3
        source = [s for s in originals[artifact]
                  if all(s.get(d) == value for d, value in dims.items())]
        assert len(source) == 1
        source = source[0]
        for field in ("mae", "mse", "rmse", "bias", "n", "scored_n", "CRPS", "NLL",
                      "infinite_NLL", "exact_rate", "p90_abs", "p95_abs", "max_abs"):
            assert row.get(field) == source.get(field), field
            checks += 1
    assert not projections
    return {
        "status": "PASS",
        "corrected_score_views": len(corrected),
        "changed_original_precision_views": audit["score_views_with_any_precision_difference"],
        "metric_and_preservation_checks": checks,
        "independent_projection_sha256": sha(audit_path),
        "corrected_scores_sha256": sha(corrected_path),
        "source_scores_unchanged": True,
        "primary_error_unchanged": True,
        "interpretation": "Exact-grid precision diagnostic correction only; no predictive improvement",
        "new_fits": 0, "new_forecasts": 0, "week8_outcomes_read": 0,
    }


if __name__ == "__main__":
    output = verify()
    destination = Path(__file__).with_name("PRIOR_CHART_PRECISION_CORRECTION_REVIEW.json")
    destination.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output))
