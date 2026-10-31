#!/usr/bin/env python3
"""Fictional aggregate fixtures for the public paired-index CI guard."""
import contextlib
import copy
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    module_path = ROOT / "tools/check_analysis_index_coverage.py"
    spec = importlib.util.spec_from_file_location("independent_paired_guard", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checks = []
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        (root / "reports").mkdir()
        (root / "registries").mkdir()

        def write(name, value, raw=False):
            p = root / name
            p.write_text(value if raw else json.dumps(value))
            return dict(path=name, sha256=hashlib.sha256(p.read_bytes()).hexdigest())

        audit = write("reports/audit.json", {})
        ids = write("reports/ids.json", ["fixture"])
        part = write("reports/canonical.csv", "test_id\nfixture\n", True)
        part.update(bytes=(root / part["path"]).stat().st_size, rows=1)
        default = write("reports/default.json", dict(audit_manifest=audit["path"], audit_manifest_sha256=audit["sha256"], selected_ids=ids, csv_parts=[part], selected_evaluation_views=1))
        ranking = write("reports/ranking.json", [dict(test_id="fixture")])
        source = dict(procedure_id="fictional", product_id="mean", target="rec", population="primary", season=2026,
                      history_regime="ADJACENT_CORE_COMPARISON", contrast="H-RECENT_MINUS_H-CURRENT", fallback_view="FULL_SYSTEM",
                      metric="MAE", n=2, candidate_error=2., comparator_error=1., delta=1., relative_error_change=1.,
                      membership_sha256="0" * 64, week_clusters=1, week_interval=None,
                      week_interval_status="INSUFFICIENT_WEEK_CLUSTERS", fullsystem_n=2,
                      contribution_to_fullsystem_delta=1.)
        row = dict(analysis_id="PAIR-FICTIONAL", kind="DERIVED_PAIRED_LOSS_ANALYSIS", state="PAIRED_LOSS_SCORED",
                   procedure_id="fictional", product_id="mean", target="rec", population="primary", season=2026,
                   history_regime=source["history_regime"], policy_id=None, contrast=source["contrast"], view="FULL_SYSTEM",
                   cohort_id=None, position=None, metric="MAE", n=2, candidate_error=2., comparator_error=1.,
                   absolute_error_change=1., relative_error_change=1., membership_sha256="0" * 64,
                   week_clusters=1, week_interval=None, week_interval_status=source["week_interval_status"], game_cluster_se=None,
                   history_status=None, candidate_history_regime="H-RECENT", comparator_history_regime="H-CURRENT",
                   comparator_procedure_id="fictional", comparator_product_id="mean", query_rows=None, unresolved_rows=None,
                   fullsystem_n=2, contribution_to_fullsystem_delta=1., candidate_fallback_rows=None, comparator_fallback_rows=None,
                   source_artifact="reports/source.json", source_row_index=0, new_fits=0, new_forecasts=0, new_NFL_observations=0)

        def install(original, projected, csv_mutant=False):
            binding = write("reports/source.json", [original])
            projected.setdefault("source_artifact_sha256", binding["sha256"])
            entry = dict(artifact=binding["path"], sha256=binding["sha256"], rows=1, new_univariate_forecast_views=0)
            write("registries/ANALYSIS_ARTIFACTS.json", [entry])
            records = write("reports/records.json", [projected])
            p = root / "reports/records.csv"
            with p.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(projected))
                writer.writeheader()
                csv_row = {k: json.dumps(v, separators=(",", ":")) if isinstance(v, (dict, list)) else "" if v is None else str(v) for k, v in projected.items()}
                if csv_mutant:
                    csv_row["membership_sha256"] = "a" * 64
                writer.writerow(csv_row)
            csv_ref = dict(path="reports/records.csv", sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            manifest = write("reports/manifest.json", dict(inputs=[entry], records_json=records, records_csv=csv_ref, record_count=1, status_counts={"PAIRED_LOSS_SCORED": 1}))
            write("registries/CURRENT_RESULTS_INDEX.json", dict(manifest=audit["path"], default_score_version_manifest=default,
                  derived_comparison_manifest=manifest, procedure_rankings=ranking, top_five_rankings=ranking))

        def check(name, original, projected, reject, csv_mutant=False):
            install(original, projected, csv_mutant)
            module.ROOT = root
            error = None
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    module.main()
            except ValueError as exc:
                error = str(exc)
            assert (error is not None) == reject, (name, error)
            checks.append(dict(name=name, expected_rejection=reject, passed=True, reason=error))

        check("unchanged_fictional_projection", source, copy.deepcopy(row), False)
        loss_mutant = copy.deepcopy(row)
        loss_mutant.update(candidate_error=3., absolute_error_change=2., relative_error_change=2.)
        check("self_consistent_loss_mutation_with_rehashed_wrapper", source, loss_mutant, True)
        for field, value in (("membership_sha256", "a" * 64), ("source_artifact_sha256", "f" * 64), ("week_interval", [0., 1.])):
            mutant = copy.deepcopy(row)
            mutant[field] = value
            check("changed_" + field, source, mutant, True)
        check("changed_csv_with_rehashed_csv_binding", source, copy.deepcopy(row), True, True)
        zero = dict(source, comparator_error=0., delta=2., relative_error_change=None)
        zero_row = dict(row, comparator_error=0., absolute_error_change=2., relative_error_change=None)
        check("zero_control_null_relative", zero, copy.deepcopy(zero_row), False)
        check("zero_control_fabricated_relative", zero, dict(zero_row, relative_error_change=0.), True)
    report = dict(state="PASS_FICTIONAL_SOURCE_BINDING_GUARDS", checker_sha256=hashlib.sha256(module_path.read_bytes()).hexdigest(),
                  fixture_count=len(checks), checks=checks, new_fits=0, inference_calls=0, new_forecasts=0,
                  new_NFL_observations=0, current2026_week8_outcomes_read=0,
                  limitation="Synthetic public-aggregate shape only; no NFL model, raw prediction, source acquisition or statistical skill test.")
    (HERE / "PAIRED_COVERAGE_GUARDS_INDEPENDENT_REVIEW.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"state": report["state"], "fixture_count": len(checks)}))


if __name__ == "__main__":
    main()
