#!/usr/bin/env python3
"""Check public frozen M2 aggregate arithmetic; never grade or export offer rows."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SOURCE = ROOT / "reports/targeted-accuracy-w1w9-01/B/evaluation"
COMMIT = "11db6280f8af4ae215f15ebbcc26c3a891db27f1"
DESTINATION = Path(__file__).with_name("NATIVE_AGGREGATE_VERIFICATION_V1.json")
checks = 0
problems: list[str] = []
bindings: list[dict] = []


def check(condition: bool, message: str) -> None:
    global checks
    checks += 1
    if not condition:
        problems.append(message)


def load(name: str):
    path = SOURCE / name
    raw = path.read_bytes()
    relative = str(path.relative_to(ROOT))
    committed = subprocess.check_output(["git", "show", f"{COMMIT}:{relative}"], cwd=ROOT)
    check(raw == committed, f"{relative} exactly committed frozen bytes")
    bindings.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "producer_commit": COMMIT,
                     "retrieval_url": f"https://raw.githubusercontent.com/NickNicky19/NFL-forecasting-V2/{COMMIT}/{relative}"})
    return json.loads(gzip.decompress(raw) if name.endswith(".gz") else raw)


def close(a, b) -> bool:
    return a is None and b is None or a is not None and b is not None and math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-12)


def count_value(value) -> int:
    # Published empty decided groups deliberately have null W/L/rate.
    return 0 if value is None else value


def key(row: dict) -> tuple:
    return tuple(row.get(k) for k in ("category", "method", "policy", "calibration_mode"))


main = load("MAIN_TABLES_V1.json.gz")
selective = load("SELECTIVE_TABLES_V1.json.gz")
paired = load("PAIRED_COMPARISONS_V1.json")
probability = load("PROBABILITY_TABLES_V1.json.gz")
all_rows = main + selective
for row in all_rows:
    label = row["record_id"]
    for side in ("OVER", "UNDER", "COMBINED"):
        count = row[side]
        check(count_value(count["wins"]) + count_value(count["losses"]) == count["decided"], f"{label} {side} W+L")
        expected = count["wins"] / count["decided"] if count["decided"] else None
        check(close(count["rate"], expected), f"{label} {side} rate")
    for field in ("wins", "losses", "decided", "selected"):
        check(count_value(row["COMBINED"][field]) == count_value(row["OVER"][field]) + count_value(row["UNDER"][field]), f"{label} weighted combined {field}")
    check(row["selected"] == row["COMBINED"]["selected"], f"{label} selected")
    check(row["decided"] == row["COMBINED"]["decided"], f"{label} decided")
    check(row["available"] + row["unavailable"] == row["eligible"], f"{label} available partition")
    check(row["selected"] <= row["available"] <= row["eligible"], f"{label} coverage bounds")
    check(close(row["coverage"], row["selected"] / row["eligible"] if row["eligible"] else None), f"{label} coverage")
    check(sum(row["selected_by_week"].values()) == row["selected"], f"{label} weekly selected sum")
    # `attribution` describes the declared board; selected fallback is separate.
    check(sum(row["attribution"].values()) == row["eligible"], f"{label} board attribution partition")
    check(row["fallback_selected"] <= row["attribution"].get("fallback", 0), f"{label} selected fallback bounded by board fallback")

# Check published totals against the original weekly aggregates, without raw-row grading.
weekly_checks = 0
for table in (main, selective):
    indexed = {(key(row), str(row["window"])): row for row in table}
    for row in table:
        if row["window"] != "ALL":
            continue
        weeks = [indexed.get((key(row), str(week))) for week in (5, 6, 7, 8, 9)]
        check(all(week is not None for week in weeks), f"{row['record_id']} all five weekly views")
        if any(week is None for week in weeks):
            continue
        for side in ("OVER", "UNDER", "COMBINED"):
            for field in ("wins", "losses", "decided", "selected"):
                check(sum(count_value(week[side][field]) for week in weeks) == count_value(row[side][field]), f"{row['record_id']} weekly {side} {field}")
                weekly_checks += 1
        for field in ("eligible", "available", "selected", "decided", "unavailable", "unknown", "fallback_selected"):
            check(sum(week[field] for week in weeks) == row[field], f"{row['record_id']} weekly {field}")
            weekly_checks += 1

native = [row for row in main if row["window"] == "ALL" and row["category"] == "pass_cmp"]
law = {row["method"]: row for row in native if row["policy"] in ("LAW", "P2_STATISTICAL_LAW")}
parent_results = []
for family in ("P2", "C1", "C2"):
    bin_name, bb_name = f"M2_{family}_BIN", f"M2_{family}_BB"
    bin_row, bb_row = law[bin_name], law[bb_name]
    selected_checked = 0
    for bin_selected in selective:
        if bin_selected["method"] != bin_name:
            continue
        counterpart = [r for r in selective if r["method"] == bb_name and r["policy"] == bin_selected["policy"] and r["window"] == bin_selected["window"]]
        check(len(counterpart) == 1, f"{family} unique selective counterpart")
        if len(counterpart) != 1:
            continue
        bb_selected = counterpart[0]
        for field in ("selected_membership_SHA256", "OVER", "UNDER", "COMBINED", "selected_by_week", "unknown", "unavailable"):
            check(bin_selected[field] == bb_selected[field], f"{family} frozen selected {bin_selected['policy']} {bin_selected['window']} {field}")
        selected_checked += 1
    proof = [r for r in paired if r["candidate"] == bb_name and r["control"] == bin_name and r["policy"] == "LAW" and r["metric"] == "SELECTION_LOSS_RATE"]
    check(len(proof) == 1, f"{family} own-parent law proof")
    if proof:
        check(proof[0]["side_disagreements"] == 0 and proof[0]["delta"] == 0, f"{family} no side changes")
        check(proof[0]["week_interval"] is None and proof[0]["week_interval_status"] == "INSUFFICIENT_WEEK_CLUSTERS", f"{family} few-week uncertainty retained")
    parent_results.append({
        "BB": bb_name, "BIN_parent": bin_name,
        "own_sides_equal": all(bb_row[s] == bin_row[s] for s in ("OVER", "UNDER", "COMBINED")),
        "selective_weekly_and_cumulative_views_checked": selected_checked,
        "law_win_difference": bb_row["COMBINED"]["wins"] - bin_row["COMBINED"]["wins"],
        "event_Brier_difference": bb_row["probability"]["strict_binary_Over_Brier"] - bin_row["probability"]["strict_binary_Over_Brier"],
        "event_log_loss_difference": bb_row["probability"]["log_loss"] - bin_row["probability"]["log_loss"],
        "paired_week_interval": None,
        "paired_week_interval_status": "INSUFFICIENT_WEEK_CLUSTERS",
    })

# Each independent probability summary must preserve its matching event population.
probability_checks = 0
for row in probability:
    match = [r for r in main if r["category"] == row["category"] and r["method"] == row["method"] and r["window"] == row["window"] and r["policy"] in ("LAW", "P2_STATISTICAL_LAW")]
    if row["policy"] != "RAW_EXACT_LINE_LAW":
        continue
    check(len(match) == 1, f"{row['record_id']} raw law summary match")
    if len(match) == 1:
        reference = match[0]
        for field in ("eligible", "available", "unavailable", "membership_SHA256", "evidence_tier"):
            check(row[field] == reference[field], f"{row['record_id']} matched {field}")
        check(close(row["brier"], reference["probability"]["half_three_state_Brier"]), f"{row['record_id']} Brier")
        check(close(row["log_loss"], reference["probability"]["log_loss"]), f"{row['record_id']} event logloss")
        probability_checks += 1

native_headlines = []
for method in ("M2_P2_BIN", "M2_P2_BB", "M2_C1_BIN", "M2_C1_BB", "M2_C2_BIN", "M2_C2_BB", "D_M2", "RETAINED_B0"):
    row = law[method]
    native_headlines.append({k: row[k] for k in ("method", "procedure_id", "policy", "actual_weeks", "OVER", "UNDER", "COMBINED", "eligible", "available", "selected", "unknown", "unavailable", "fallback_selected", "games", "evidence_tier")})

receipt = {
    "id": "B_CHECKPOINT_M2_NATIVE_PUBLIC_AGGREGATE_VERIFICATION_v1",
    "at_UTC": datetime.now(timezone.utc).isoformat(),
    "state": "PASS_PUBLIC_AGGREGATE_ARITHMETIC_NO_REGRADING" if not problems else "FAIL",
    "checks": checks, "problems": problems,
    "source_bindings": bindings,
    "main_rows_checked": len(main), "selective_rows_checked": len(selective),
    "weekly_sum_checks": weekly_checks,
    "raw_probability_summaries_checked": probability_checks,
    "within_method_results": parent_results,
    "native_exact_law_headlines": native_headlines,
    "new_early_M2_actual_line_grades": "NOT_EXECUTED_IN_RETRIEVED_A_RECEIPTS; no 226-case M2 cumulative record is asserted",
    "interpretation": "Separate arithmetic over frozen public aggregates, commitments and original weekly summaries. This does not rerun C grading or independently inspect private offer rows, source clocks, fitted parameters or original issuance. Counts of checks/views are not additional NFL observations.",
    "probability_contract": "Half multiclass Brier on Over/Under/push; native halfpoint push=0 so equals binary Over Brier. Log loss is exact statistical threshold event loss, not venue settlement or count PMF loss. No law score is inferred from a point-only product.",
    "resources": {"external_source_reads": 0, "fits": 0, "new_actual_offer_grades": 0, "protected_rows_exported": 0},
}
DESTINATION.write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps({**{k: receipt[k] for k in ("state", "checks", "main_rows_checked", "selective_rows_checked", "raw_probability_summaries_checked")}, "problem_count": len(problems), "first_problems": problems[:8]}))
raise SystemExit(bool(problems))
