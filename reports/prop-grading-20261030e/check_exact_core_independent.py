#!/usr/bin/env python3
"""Independent fictional boundaries for the existing exact scoring extension."""
import copy
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nfl_v2 import scoring as s
from nfl_v2 import prop_selection as selection

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-name", default="EXACT_CORE_INDEPENDENT_REVIEW_V2.json")
    args = parser.parse_args()
    if Path(args.output_name).name != args.output_name:
        raise ValueError("Use a filename in this independent report directory")
    code = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "nfl_v2/scoring.py", ROOT / "nfl_v2/prop_selection.py")}
    results = []

    def check(ident, call, expected=None, reject=False):
        try:
            observed = call()
            passed = not reject and observed == expected
            error = None
        except (ValueError, TypeError) as exc:
            observed = None
            error = type(exc).__name__ + ": " + str(exc)
            passed = reject and isinstance(exc, ValueError)
        results.append(dict(id=ident, passed=passed, expected="ValueError" if reject else expected, observed=observed, error=error))

    def contract(target="rec"):
        return dict(verified=True, statistic=target, period="full_game", overtime=True,
                    scoring_contract="nick-chart-ppr-v1" if target == "nick-chart-ppr-v1" else "official-stat-v1",
                    event_scope="rushing_or_receiving_only" if target == "anytime_td" else "ordinary_statistic",
                    payout_kind="cash_refund", tie_rule="cash_refund", dnp_rule="cash_refund", void_rule="cash_refund",
                    contract_id="FICTIONAL", version="1", book="FICTIONAL", jurisdiction="TEST",
                    rule_source_id="FICTIONAL-RULES", stat_correction_policy="verified_final_revision",
                    injury_protection_rule="action_on_appearance")

    def grade(actual="1", line="0.5", side="over", target="rec", participation="PLAYED", outcome_state="final", odds="2", book=None, outcome=None):
        c = contract(target) if book is None else book
        o = copy.deepcopy(c) if outcome is None else outcome
        value = s.grade_settlement(actual, line, side, target=target, participation=participation,
                                   outcome_state=outcome_state, contract=c, outcome_contract=o, decimal_odds=odds)
        return value["state"], value["net"]

    for name, inputs, expected in (
        ("WIN", {}, ("WIN", Decimal(1))),
        ("LOSS_PLAYED_ZERO", {"actual": "0"}, ("LOSS", Decimal(-1))),
        ("PUSH", {"line": "1"}, ("PUSH", Decimal(0))),
        ("VOID_DNP", {"actual": None, "participation": "DNP"}, ("VOID", Decimal(0))),
        ("PENDING", {"actual": None, "outcome_state": "pending", "participation": "UNKNOWN"}, ("PENDING", None)),
        ("MISSING_ACTUAL", {"actual": None}, ("MISSING_ACTUAL", None)),
        ("UNKNOWN_PARTICIPATION", {"actual": "0", "participation": "UNKNOWN"}, ("UNKNOWN_PARTICIPATION", None)),
        ("UNRESOLVED_CONTRACT", {"book": {}}, ("UNRESOLVED_CONTRACT", None)),
        ("UNPRICED_WIN", {"odds": None}, ("WIN", None)),
        ("UNPRICED_LOSS", {"actual": "0", "odds": None}, ("LOSS", None)),
        ("UNPRICED_PUSH", {"line": "1", "odds": None}, ("PUSH", Decimal(0))),
        ("CANCELED_REFUND", {"actual": None, "outcome_state": "canceled", "participation": "UNKNOWN", "odds": None}, ("VOID", Decimal(0))),
        ("SIGNED_YARDS", {"actual": "-3", "line": "-2.5", "side": "under", "target": "rush_yd"}, ("WIN", Decimal(1))),
        ("OWN_PRICE_WIN", {"odds": "2.5"}, ("WIN", Decimal("1.5"))),
        ("EARLY_EXIT_ACTION", {"actual": "0", "participation": "PLAYED"}, ("LOSS", Decimal(-1))),
        ("UNKNOWN_TARGET", {"target": "invented_target"}, ("UNRESOLVED_CONTRACT", None)),
    ):
        check(name, lambda inputs=inputs: grade(**inputs), expected)
    for name, inputs in (
        ("NEGATIVE_COUNT", {"actual": "-1"}),
        ("FRACTIONAL_COUNT", {"actual": "0.5"}),
        ("BOOLEAN_ACTUAL", {"actual": True}),
        ("FRACTIONAL_OFFICIAL_YARDS", {"actual": "1.2", "target": "rush_yd"}),
        ("OFF_GRID_CHART", {"actual": "1.019", "target": "nick-chart-ppr-v1"}),
        ("BAD_PRICE", {"odds": "1"}),
    ):
        check(name, lambda inputs=inputs: grade(**inputs), reject=True)
    mismatch = contract()
    mismatch["overtime"] = False
    check("OUTCOME_CONTRACT_MISMATCH", lambda: grade(outcome=mismatch), ("UNRESOLVED_CONTRACT", None))
    missing_rule = contract()
    missing_rule["injury_protection_rule"] = None
    check("MISSING_VERSIONED_RULE", lambda: grade(book=missing_rule), ("UNRESOLVED_CONTRACT", None))
    for rushing, receiving in ((-5, 3), (-5, 4), (-5, 6)):
        components = dict.fromkeys(s.CHART_WEIGHTS, "0")
        components.update(rushing_yards=str(rushing), receiving_yards=str(receiving))
        exact = Decimal(rushing + receiving) * Decimal(".1")
        check("EXACT_CHART_" + str(receiving), lambda components=components: s.chart_points_exact(components), exact)
        check("EXACT_CHART_PUSH_" + str(receiving), lambda exact=exact: grade(actual=exact, line=str(exact), target="nick-chart-ppr-v1"), ("PUSH", Decimal(0)))
    for name, point, line, expected in (("P1_EQUAL", "10.00", "10", None), ("P1_UNROUNDED_OVER", "10.001", "10", "over"), ("P1_UNROUNDED_UNDER", "9.999", "10", "under"), ("P1_NO_POINT", None, "10", None)):
        check(name, lambda point=point, line=line: selection.choose_side("P1", point=point, line=line), expected)
    p = dict(over=".33", under=".27", push=".40", conditioning="conditional_nonvoid")
    check("P2_RETAIN_PUSH", lambda: selection.choose_side("P2", probabilities=p), "over")
    check("P2_ALL_PUSH_ABSTAIN", lambda: selection.choose_side("P2", probabilities=dict(over="0", under="0", push="1", conditioning="conditional_nonvoid")), None)
    check("P2_POINT_ONLY_ABSTAIN", lambda: selection.choose_side("P2", point="10", line="9.5"), None)
    check("P2_WRONG_CONDITIONING", lambda: selection.choose_side("P2", probabilities=dict(p, conditioning="conditional_decisive")), reject=True)
    check("P3_LOWER_WIN_PROB_BETTER_PRICE", lambda: selection.choose_side("P3", probabilities=dict(over=".55", under=".45", push="0", conditioning="conditional_nonvoid"), prices=dict(over="1.5", under="2.5")), "under")
    check("P3_ZERO_EV_ABSTAIN", lambda: selection.choose_side("P3", probabilities=dict(over=".5", under=".5", push="0", conditioning="conditional_nonvoid"), prices=dict(over="2", under="2")), None)
    check("P3_MISSING_PRICE_ABSTAIN", lambda: selection.choose_side("P3", probabilities=p), None)
    check("P3_REGISTERED_LEXICAL_TIE", lambda: selection.choose_side("P3", probabilities=dict(over=".5", under=".5", push="0", conditioning="conditional_nonvoid"), prices=dict(over="2.5", under="2.5")), "over")
    check("EV_UNCONDITIONAL", lambda: s.expected_value(".3", ".2", "2", conditioning="unconditional_placed"), dict(EV_placed=Decimal(".1"), EV_nonvoid=None))
    check("EV_NONVOID_PUSH_RETAINED", lambda: s.expected_value(".3", ".2", "2", conditioning="conditional_nonvoid"), dict(EV_nonvoid=Decimal(".1"), EV_placed=None))
    check("EV_NONVOID_BRIDGE", lambda: s.expected_value(".4", ".3", "2.5", conditioning="conditional_nonvoid", p_nonvoid=".9"), dict(EV_nonvoid=Decimal(".30"), EV_placed=Decimal(".270")))
    check("EV_MISSING_CONDITIONING", lambda: s.expected_value(".3", ".2", "2", conditioning="unknown"), reject=True)
    check("EV_INVALID_MASS", lambda: s.expected_value(".6", ".6", "2", conditioning="unconditional_placed"), reject=True)
    check("EV_DOUBLE_CONDITIONING", lambda: s.expected_value(".3", ".2", "2", conditioning="unconditional_placed", p_nonvoid=".9"), reject=True)
    for name, extra in (("INVALID_SIDE_PENDING", dict(side="neither", actual=None, outcome_state="pending")), ("INVALID_LINE_VOID", dict(line=None, actual=None, participation="DNP"))):
        check(name, lambda extra=extra: grade(**extra), ("UNRESOLVED_CONTRACT", None))
    assert code == {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "nfl_v2/scoring.py", ROOT / "nfl_v2/prop_selection.py")}, "producer source changed during checks"
    failures = [r for r in results if not r["passed"]]
    report = dict(state="PASS_EXACT_CORE_FICTIONAL_BOUNDARIES" if not failures else "FINDINGS_EXACT_CORE_FICTIONAL_BOUNDARIES",
                  code_sha256=code, fixture_checks=len(results), passed_checks=len(results)-len(failures), findings=failures,
                  cases=results, original_boundary_plan_sha256="c41d7d9e2af56a3a1a47d85edc44f371c763cddb6722fb741342cd2626d17af3",
                  conditioning_amendment="CONDITIONING_FIXTURE_AMENDMENT_V1.json",
                  scope="Exact arithmetic/eight states/P1-P3/EV only. Source joins, authentic quote clocks, fixed-week and rolling scheduling are separately reviewed; these are not 54 completed full-panel fixture cases.",
                  amendment="Initial two malformed-offer fixtures requested ValueError. The eight-state API now correctly rejects those as UNRESOLVED_CONTRACT instead of returning PENDING/VOID; this revised acceptance preserves the initial finding and its original receipt.",
                  new_fits=0, inference_calls=0, new_forecasts=0, new_NFL_observations=0, current2026_week8_outcomes_read=0)
    output = HERE / args.output_name
    if output.exists():
        raise ValueError("Preserve the initial fixture receipt; a rerun needs a new output version")
    output.write_text(json.dumps(report, indent=2, default=str)+"\n")
    print(json.dumps({k: report[k] for k in ("state", "fixture_checks", "passed_checks", "findings")}, default=str))


if __name__ == "__main__":
    main()
