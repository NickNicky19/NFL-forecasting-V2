"""Independent arithmetic of public A owner-local exports; never reads private rows."""
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path


def verify(path):
    raw = path.read_bytes()
    body = gzip.decompress(raw)
    document = json.loads(body)
    rows = document.get("summaries", document.get("scores"))
    failures = []
    checks = collections.Counter()

    def equal(label, actual, expected):
        checks[label] += 1
        same = (actual is None and expected is None) or (
            actual is not None and expected is not None
            and (math.isclose(actual, expected, rel_tol=1e-11, abs_tol=1e-11)
                 if isinstance(expected, (float, int)) else actual == expected)
        )
        if not same:
            failures.append({"check": label, "actual": actual, "expected": expected})

    index = {}
    for row in rows:
        key = (row["candidate_id"], row["view"], row["source_panel"], str(row["week_view"]))
        equal("unique_summary_key", key not in index, True)
        index[key] = row
        for side in ("OVER", "UNDER", "COMBINED"):
            values = row[side]
            if values["wins"] is None or values["losses"] is None:
                equal("empty_pool_null_contract", (values["wins"], values["losses"], values["decided"]), (None, None, 0))
            else:
                equal("decided_equals_wins_plus_losses", values["decided"], values["wins"] + values["losses"])
            equal("own_rate", values["rate"], values["wins"] / values["decided"] if values["decided"] else None)
            equal("selected_covers_decided", values["selected"] >= values["decided"], True)
        for field in ("selected", "wins", "losses", "decided"):
            parts = [row[s][field] for s in ("OVER", "UNDER")]
            expected = None if all(v is None for v in parts) else sum(v or 0 for v in parts)
            equal("combined_side_partition", row["COMBINED"][field], expected)
        equal("selection_availability_partition", row["eligible"], row["COMBINED"]["selected"] + row["unavailable"] + row["abstentions"])
        equal("state_partition", row["eligible"], sum(row["states"].values()))
        equal("coverage", row["coverage"], row["COMBINED"]["selected"] / row["eligible"] if row["eligible"] else None)

    cumulative_groups = 0
    numerical_groups = 0
    for key, total in index.items():
        candidate, view, source, week = key
        if week != "ALL":
            continue
        parts = [r for k, r in index.items() if k[:3] == key[:3] and k[3] != "ALL"]
        if not parts:
            continue
        cumulative_groups += 1
        for side in ("OVER", "UNDER", "COMBINED"):
            for field in ("selected", "wins", "losses", "decided"):
                weekly_values = [p[side][field] for p in parts]
                expected = None if all(v is None for v in weekly_values) else sum(v or 0 for v in weekly_values)
                equal("weekly_count_reconciliation", total[side][field], expected)
        for field in ("eligible", "unavailable", "abstentions", "fallback_outputs"):
            equal("weekly_scope_reconciliation", total[field], sum(p[field] for p in parts))
        nkey = "numerical" if "numerical" in total else "numerical_same_offer_mask"
        numeric = total.get(nkey)
        if numeric and numeric.get("scored"):
            numerical_groups += 1
            count = sum(p[nkey]["scored"] for p in parts)
            equal("numerical_count_reconciliation", numeric["scored"], count)
            for metric in ("MAE", "MSE", "bias"):
                expected = math.fsum(p[nkey][metric] * p[nkey]["scored"] for p in parts if p[nkey]["scored"]) / count
                equal("weighted_numerical_reconciliation", numeric[metric], expected)

    pairs = document.get("paired", document.get("paired_controls", []))
    for pair in pairs:
        equal("paired_win_change", pair["win_change"], pair["left_wins"] - pair["right_wins"])
        equal("paired_wins_within_common_count", max(pair["left_wins"], pair["right_wins"]) <= pair["common_decided"], True)
        equal("paired_difference_bounded_by_disagreements", abs(pair["win_change"]) <= pair["side_disagreements"], True)

    return {
        "source_name": path.name,
        "stored_SHA256": hashlib.sha256(raw).hexdigest(),
        "decoded_SHA256": hashlib.sha256(body).hexdigest(),
        "summaries": len(rows),
        "cumulative_groups": cumulative_groups,
        "weighted_numerical_groups": numerical_groups,
        "paired_summaries": len(pairs),
        "checks": dict(checks),
        "failures": failures,
        "status": "PASS_PUBLIC_AGGREGATE_ARITHMETIC" if not failures else "FAIL",
        "limits": [
            "Independent standard-library calculation, not the owner or common summary function.",
            "Private relational rows, identities, original offers, timing and forecast joins were not inspected.",
            "Mask hashes are retained assertions; their memberships cannot be independently reproduced from aggregates.",
            "Intervals are retained descriptive owner outputs, not independently regenerated without permitted rows.",
            "Verification adds no fits, forecasts, scored NFL opportunities or tested weeks."
        ]
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("aggregates", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = [verify(path) for path in args.aggregates]
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps([{k: r[k] for k in ("source_name", "summaries", "paired_summaries", "status", "failures")} for r in result]))
    raise SystemExit(any(r["failures"] for r in result))
