"""Separate public arithmetic only; arguments are the two immutable CSVs."""
import csv
import math
import sys

summaries = list(csv.DictReader(open(sys.argv[1], newline="")))
pairs = list(csv.DictReader(open(sys.argv[2], newline="")))
number = lambda value: float(value) if value else 0


def same(left, right):
    assert math.isclose(left, right, rel_tol=1e-11, abs_tol=1e-11), (left, right)


for row in summaries:
    for prefix in ("over", "under", "total"):
        same(number(row[prefix + "_n"]), number(row[prefix + "_w"]) + number(row[prefix + "_l"]))
    for field in ("w", "l", "n"):
        same(number(row["total_" + field]), number(row["over_" + field]) + number(row["under_" + field]))
    same(number(row["eligible"]), number(row["selected"]) + number(row["unavailable"]))
    same(number(row["selected"]), number(row["total_n"]) + number(row["unknown"]))
    if row["week"] != "ALL":
        continue
    parts = [r for r in summaries if r["week"] != "ALL" and all(r[k] == row[k] for k in ("view", "source", "method"))]
    for field in ("eligible", "selected", "unavailable", "over_w", "over_l", "over_n", "under_w", "under_l", "under_n", "total_w", "total_l", "total_n", "unknown"):
        same(number(row[field]), sum(number(r[field]) for r in parts))
    if number(row["total_n"]):
        for metric in ("MAE", "MSE", "bias"):
            same(number(row[metric]), math.fsum(number(r[metric]) * number(r["total_n"]) for r in parts) / number(row["total_n"]))
for row in pairs:
    same(number(row["win_change"]), number(row["left_wins"]) - number(row["right_wins"]))
    same(number(row["accuracy_change"]), number(row["win_change"]) / number(row["common_decided"]))
    assert abs(number(row["win_change"])) <= number(row["side_disagreements"])
print("PASS", len(summaries), "public summaries;", len(pairs), "public pairs; no private membership verification")
