#!/usr/bin/env python3
"""Fictional clock, fixed-universe and rolling-batch selection boundaries."""
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from nfl_v2 import prop_selection as p

HERE = Path(__file__).resolve().parent


def main():
    code_path = ROOT / "nfl_v2/prop_selection.py"
    code_sha = hashlib.sha256(code_path.read_bytes()).hexdigest()
    checks = []

    def check(ident, call, expected=None, contains=None, reject=False):
        try:
            result = call()
            passed = not reject and (contains in result if contains is not None else result == expected)
            error = None
        except ValueError as exc:
            result, error, passed = None, str(exc), reject
        checks.append(dict(id=ident, passed=passed, observed=result, error=error))

    decision = "2026-10-30T21:10:00Z"
    identity = dict(event_id="FICTIONAL-GAME", player_id="FICTIONAL-PLAYER", target="rec", period="full_game", scoring_contract="official-rec-v1")
    forecast = dict(identity, evidence="CAPTURED_PREGAME", feature_cutoff="2026-10-30T21:00:00Z",
                    training_label_cutoff="2026-10-30T20:00:00Z", fallback_cutoff="2026-10-30T21:00:00Z",
                    calibration_cutoff="2026-10-29T21:00:00Z", issued_at="2026-10-30T21:05:00Z", persisted_at="2026-10-30T21:06:00Z")
    offer = dict(identity, source_update="2026-10-30T21:09:00Z", received_at="2026-10-30T21:09:30Z", status="OPEN", kickoff="2026-10-30T23:00:00Z", horizon_seconds=5400)
    check("T_VALID_AUTHENTIC", lambda: p.timing_violations(forecast, offer, decision), [])
    for ident, f, o, t, reason in (
        ("T_MISSING_KICKOFF", forecast, dict(offer, kickoff=None), decision, "MISSING_KICKOFF"),
        ("T_POST_KICKOFF", forecast, offer, "2026-10-30T23:01:00Z", "DECISION_NOT_PREGAME"),
        ("T_MISSED_T90", forecast, offer, "2026-10-30T21:30:01Z", "MISSED_HORIZON"),
        ("T_FEATURE_AFTER_ISSUE", dict(forecast, feature_cutoff="2026-10-30T21:07:00Z"), offer, decision, "INFORMATION_AFTER_ISSUANCE"),
        ("T_PERSIST_BEFORE_ISSUE", dict(forecast, persisted_at="2026-10-30T21:04:00Z"), offer, decision, "PERSISTENCE_BEFORE_ISSUANCE"),
        ("T_ISSUE_AFTER_DECISION", dict(forecast, issued_at="2026-10-30T21:11:00Z"), offer, decision, "LATE_issued_at"),
        ("T_FEATURE_AFTER_DECISION", dict(forecast, feature_cutoff="2026-10-30T21:11:00Z"), offer, decision, "FUTURE_feature_cutoff"),
        ("T_FUTURE_SOURCE_UPDATE", forecast, dict(offer, source_update="2026-10-30T21:10:01Z"), decision, "FUTURE_QUOTE_source_update"),
        ("T_FUTURE_RECEIPT", forecast, dict(offer, received_at="2026-10-30T21:10:01Z"), decision, "FUTURE_QUOTE_received_at"),
        ("T_UPDATE_AFTER_RECEIPT", forecast, dict(offer, source_update="2026-10-30T21:09:45Z"), decision, "QUOTE_UPDATE_AFTER_RECEIPT"),
        ("T_STALE_OVER_900", forecast, dict(offer, source_update="2026-10-30T20:54:59Z"), decision, "STALE_QUOTE"),
        ("T_CLOSED", forecast, dict(offer, status="CLOSED"), decision, "QUOTE_NOT_OPEN"),
        ("T_ID_COLLISION", forecast, dict(offer, player_id="OTHER"), decision, "IDENTITY_player_id"),
        ("T_REPLAY_MISSING_TIER", dict(forecast, evidence="RETROSPECTIVE_RULE_REPLAY"), offer, decision, "RECONSTRUCTION_TIER_REQUIRED"),
    ):
        check(ident, lambda f=f, o=o, t=t: p.timing_violations(f, o, t), contains=reason)
    fresh_boundary = dict(offer, source_update="2026-10-30T20:55:00Z")
    check("T_EXACT_900_ACCEPTED", lambda: p.timing_violations(forecast, fresh_boundary, decision), [])
    check("T_EXACT_T90_ACCEPTED", lambda: p.timing_violations(forecast, dict(offer, source_update="2026-10-30T21:29:00Z", received_at="2026-10-30T21:29:30Z"), "2026-10-30T21:30:00Z"), [])
    check("T_NAIVE_CLOCK_REJECTED", lambda: p.timing_violations(forecast, offer, "2026-10-30T21:10:00"), reject=True)
    check("T_NEGATIVE_HORIZON", lambda: p.timing_violations(forecast, dict(offer, horizon_seconds=-1), decision), reject=True)
    check("T_REPLAY_EXPLICIT_TIER", lambda: p.timing_violations(dict(forecast, evidence="RETROSPECTIVE_RULE_REPLAY", information_tier="CURRENT_VINTAGE_RECONSTRUCTION", issued_at=None, persisted_at=None), offer, decision), [])

    def row(ident, score, *, side="over", target="rec", available="2026-10-30T21:00:00Z", week=7):
        return dict(selection_unit_id=ident, season=2026, week=week, target=target, side=side,
                    rank_score=str(score), available_at=available, decision_time=available, kickoff="2026-10-31T20:00:00Z")

    def ids(value):
        return [r["selection_unit_id"] for r in value]

    rows = [row("b", ".8"), row("a", ".8"), row("c", ".4", side="under")]
    original = copy.deepcopy(rows)
    check("K_FIXED_TIE_ORDER_AND_NO_PADDING", lambda: ids(p.fixed_top_k(rows, 6, freeze_time=decision)), ["a", "b", "c"])
    check("K_INPUTS_UNCHANGED", lambda: rows == original, True)
    check("K_SIDE_POOL", lambda: ids(p.fixed_top_k(rows, 6, freeze_time=decision, side="under")), ["c"])
    check("K_DUPLICATE", lambda: p.fixed_top_k(rows + [rows[0]], 6, freeze_time=decision), reject=True)
    check("K_FUTURE_CANDIDATE", lambda: p.fixed_top_k(rows + [row("future", 100, available="2026-10-30T22:00:00Z")], 6, freeze_time=decision), reject=True)
    check("K_AFTER_INCLUDED_KICKOFF", lambda: p.fixed_top_k([dict(rows[0], kickoff="2026-10-30T21:09:00Z")], 6, freeze_time=decision), reject=True)
    check("K_MIXED_WEEKS", lambda: p.fixed_top_k(rows + [row("otherweek", 100, week=8)], 6, freeze_time=decision), reject=True)
    mixed = rows + [row("yards", ".9", target="rush_yd")]
    check("K_MIXED_RAW_UNITS", lambda: p.fixed_top_k(mixed, 6, freeze_time=decision, ranking_kind="point_gap"), reject=True)
    check("K_COMPATIBLE_PROBABILITY_RANK", lambda: ids(p.fixed_top_k(mixed, 6, freeze_time=decision, ranking_kind="probability")), ["yards", "a", "b", "c"])
    check("K_FULL_UNIVERSE_OLD_ANCHOR_REJECTED", lambda: p.fixed_top_k(rows, 6, freeze_time=decision, universe_first_kickoff="2026-10-29T23:00:00Z"), reject=True)
    check("K_EXPLICIT_PARTIAL_UNIVERSE", lambda: ids(p.fixed_top_k(rows, 6, freeze_time=decision, universe_first_kickoff="2026-10-31T20:00:00Z")), ["a", "b", "c"])
    check("K_UNREGISTERED_SIZE", lambda: p.fixed_top_k(rows, 5, freeze_time=decision), reject=True)
    check("K_BOOLEAN_SCORE", lambda: p.fixed_top_k([dict(rows[0], rank_score=True)], 6, freeze_time=decision), reject=True)
    first = [row(str(i), .5-.01*i) for i in range(4)]
    second = [row(str(i), .9-.01*i, available="2026-10-30T22:00:00Z") for i in range(4, 8)]
    batches = [dict(decision_time=decision, candidates=first), dict(decision_time="2026-10-30T22:05:00Z", candidates=second)]
    check("R_GREEDY_EARLIER_PICKS_RETAINED", lambda: ids(p.rolling_top_k(batches, 6)), ["0", "1", "2", "3", "4", "5"])
    check("R_DISTINCT_LATER_FIXED_UNIVERSE", lambda: ids(p.fixed_top_k(first + second, 6, freeze_time="2026-10-30T22:05:00Z")), ["4", "5", "6", "7", "0", "1"])
    check("R_REVERSED_BATCHES", lambda: p.rolling_top_k(list(reversed(batches)), 6), reject=True)
    check("R_DUPLICATE_CONTRACT", lambda: p.rolling_top_k([batches[0], dict(decision_time="2026-10-30T22:05:00Z", candidates=[first[0]])], 6), reject=True)
    check("R_FUTURE_BATCH_CANDIDATE", lambda: p.rolling_top_k([dict(decision_time=decision, candidates=second)], 6), reject=True)
    check("R_MIXED_WEEK", lambda: p.rolling_top_k([batches[0], dict(decision_time="2026-10-30T22:05:00Z", candidates=[row("nextweek", 1, week=8)])], 6), reject=True)
    check("R_MIXED_POINT_GAP_UNITS", lambda: p.rolling_top_k([batches[0], dict(decision_time="2026-10-30T22:05:00Z", candidates=[row("yard", 1, target="rush_yd")])], 6, ranking_kind="point_gap"), reject=True)
    assert hashlib.sha256(code_path.read_bytes()).hexdigest() == code_sha
    failures = [r for r in checks if not r["passed"]]
    report = dict(state="PASS_FICTIONAL_TIMING_FIXED_AND_ROLLING_SELECTION" if not failures else "FINDINGS_TIMING_SELECTION",
                  source_sha256=code_sha, checks=len(checks), passed=len(checks)-len(failures), failures=failures, cases=checks,
                  timing_scope="Exact input/issue/persist/quote clocks and optional registered horizon. Quote provenance and declared universe truth require bound source receipts; passing this helper cannot authenticate them.",
                  ranking_scope="Fixed and rolling functions consume caller-frozen ranking scores. Synthetic scores test ordering only and do not prove calibrated probabilities, EV or a policy's NFL skill.",
                  source_amendment="TIMING_FIXTURE_AMENDMENT_V1.json", new_fits=0, inference_calls=0,
                  new_forecasts=0, new_NFL_observations=0, current2026_week8_outcomes_read=0)
    path = HERE / "TIMING_SELECTION_INDEPENDENT_REVIEW.json"
    if path.exists():raise ValueError("Retain the previous receipt; use a new report version")
    path.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k: report[k] for k in ("state", "checks", "passed", "failures")}))


if __name__ == "__main__":
    main()
