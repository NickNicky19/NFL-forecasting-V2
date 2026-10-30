#!/usr/bin/env python3
"""Fictional checks of retained math; no NFL rows, source fetches or fitting."""
from decimal import Decimal
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-name", default="EXISTING_MATH_INDEPENDENT_REVIEW_REPLAY.json")
    args = parser.parse_args()
    if Path(args.output_name).name != args.output_name:raise ValueError("A local report filename is required")
    output = HERE / args.output_name
    if output.exists():raise ValueError("Preserve the previous independent receipt")
    path = HERE / "legacy-code/scoring_c8cb933a.py"
    code_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    assert code_sha == "af8a417d03c7b7d2aac64313933b19d176fc7756513dbfb14a5cabcd5624fc5a"
    spec = importlib.util.spec_from_file_location("independent_legacy_scoring", path)
    scoring = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scoring)
    checks = []

    def check(name, condition):
        assert condition, name
        checks.append(name)

    law = {0: Decimal(".2"), 1: Decimal(".5"), 2: Decimal(".3")}
    over = []
    under = []
    for line in (Decimal("-.5"), Decimal(".5"), Decimal("1"), Decimal("1.5"), Decimal("2.5")):
        expected = {"over": sum((p for y, p in law.items() if y > line), Decimal(0)),
                    "under": sum((p for y, p in law.items() if y < line), Decimal(0)),
                    "push": sum((p for y, p in law.items() if y == line), Decimal(0))}
        observed = scoring.event_probabilities(list(law), [float(p) for p in law.values()], float(line))
        for side, p in expected.items():
            check("probability_" + side + "_at_" + str(line), math.isclose(observed[side], float(p), abs_tol=1e-15))
        check("normalized_at_" + str(line), math.isclose(sum(observed.values()), 1., abs_tol=1e-15))
        over.append(observed["over"])
        under.append(observed["under"])
    check("over_monotone", all(a >= b for a, b in zip(over, over[1:])))
    check("under_monotone", all(a <= b for a, b in zip(under, under[1:])))
    for actual in (0, 1):
        a = scoring.point_metrics([.7], [actual], "anytime_td")
        b = scoring.point_metrics([.3], [1-actual], "anytime_td")
        check("mirrored_brier_" + str(actual), math.isclose(a["brier"], b["brier"], abs_tol=1e-15))
        check("mirrored_logloss_" + str(actual), math.isclose(a["log_loss"], b["log_loss"], abs_tol=1e-15))
    check("unconditional_refund_EV", math.isclose(scoring.expected_net(.3, .2, 2), .1, abs_tol=1e-15))
    conditional = scoring.expected_net(.6, .4, 2)
    check("conditional_EV", math.isclose(conditional, .2, abs_tol=1e-15))
    check("decisive_mass_bridge", math.isclose(.5 * conditional, scoring.expected_net(.3, .2, 2), abs_tol=1e-15))
    check("push_and_void_residual_EV", math.isclose(scoring.expected_net(.4, .3, 2.5), .3, abs_tol=1e-15))
    for name, inputs, expected in (
        ("played_zero_loss", (0, .5, "over", 2), ("loss", -1.)),
        ("played_zero_under_win", (0, .5, "under", 2), ("win", 1.)),
        ("integer_push_over", (1, 1, "over", 2), ("push", 0.)),
        ("integer_push_under", (1, 1, "under", 2), ("push", 0.)),
        ("signed_yard_under_win", (-3, -2.5, "under", 2), ("win", 1.)),
        ("missing_label_unresolved", (None, .5, "over", 2), ("unresolved", None)),
        ("void_refund", (None, .5, "over", 2, "void"), ("void", 0.)),
        ("canceled_refund", (None, .5, "over", 2, "canceled"), ("void", 0.)),
    ):
        check(name, scoring.settle(*inputs) == expected)
    defects = []
    for rushing, receiving in ((-5, 3), (-5, 4), (-5, 6)):
        components = dict.fromkeys(scoring.CHART_WEIGHTS, 0)
        components.update(rushing_yards=rushing, receiving_yards=receiving)
        exact = Decimal(rushing + receiving) * Decimal(".1")
        floating = scoring.chart_points(components)
        result = scoring.settle(floating, float(exact), "over", 2)
        assert floating != float(exact) and result[0] == "win"
        defects.append(dict(component_rushing_yards=rushing, component_receiving_yards=receiving,
                            exact_chart_score=str(exact), floating_chart_score=repr(floating),
                            line=str(exact), exact_expected="PUSH", observed_legacy=list(result),
                            classification="EXACT_COMPONENT_PUSH_MISGRADED_BY_FLOAT_PATH"))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == code_sha, "source changed during checks"
    report = dict(state="BASELINE_MATH_CHECKS_PASS_WITH_EXPLICIT_PRECISION_FAILURES",
                  source_sha256=code_sha, git_head=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  independent_compatible_math_checks=len(checks), checks=checks,
                  known_precision_failure_cases=len(defects), precision_failures=defects,
                  scope="Generic discrete mass, probability complements/monotonicity, mirrored proper scores and refund arithmetic. These isolated functions do not authenticate offers, prices, participation, target contracts or selections.",
                  old_unit_test_functions_separately_executed=6,
                  future_check="New exact-component or certified-grid path must yield PUSH in these three cases while preserving old reported bytes. No blanket rounding of means or provider values.",
                  new_fits=0, inference_calls=0, new_forecasts=0, new_NFL_observations=0,
                  current2026_week8_outcomes_read=0)
    output.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({"state": report["state"], "compatible_checks": len(checks), "known_precision_failures": len(defects)}))


if __name__ == "__main__":
    main()
