#!/usr/bin/env python3
"""Recompute saved Week7 direction grades and aggregates without engine imports."""
import argparse
import collections
from decimal import Decimal
import gzip
import hashlib
import json
import math
from pathlib import Path
import resource
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PUBLIC = HERE / "first-scorecard-v1"
POINT = "SAVED_POINT_DIRECTION_RETAINED_PRECISION"


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical(obj):return json.dumps(obj, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
def close(a, b):
    if a is None or b is None:assert a is b
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b):close(x, y)
    else:assert math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12), (a, b)


def interval(rows, original=None):
    decided = [r for r in rows if r["state"] in ("WIN", "LOSS") and (original is None or original[r["index"]]["state"] in ("WIN", "LOSS"))]
    game_values = collections.defaultdict(list)
    for r in decided:
        value = int(r["state"] == "WIN") if original is None else int(r["state"] == "LOSS")-int(original[r["index"]]["state"] == "LOSS")
        game_values[r["game"]].append(value)
    games = sorted(game_values)
    estimate = sum(sum(game_values[g]) for g in games)/len(decided) if decided else None
    limits = None
    if len(games) >= 8:
        rng = np.random.Generator(np.random.PCG64(1703))
        rates = []
        for _ in range(500):
            sample = [games[i] for i in rng.integers(0, len(games), size=len(games))]
            rates.append(sum(sum(game_values[g]) for g in sample)/sum(len(game_values[g]) for g in sample))
        limits = np.percentile(rates, [2.5, 97.5], method="linear").tolist()
    return dict(n=len(decided), games=len(games), estimate=estimate, interval=limits)


def subgroup(rows, dimension, value):
    if dimension == "ALL":return rows
    if dimension == "category":return [r for r in rows if r["target"] == value]
    if dimension == "original_side":return [r for r in rows if r["original_side"] == value]
    if dimension == "line_source":return [r for r in rows if r["line_from"] == value]
    if dimension == "position":return [r for r in rows if r["position"] == value]
    if dimension == "saved_top_over":return [r for r in rows if r["top_over"]]
    if dimension == "saved_top_under":return [r for r in rows if r["top_under"]]
    if dimension == "any_saved_top":return [r for r in rows if r["top_over"] or r["top_under"]]
    if dimension == "not_saved_top":return [r for r in rows if not r["top_over"] and not r["top_under"]]
    raise ValueError("Unexpected aggregate dimension")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--joined", required=True, type=Path)
    p.add_argument("--grade-root", required=True, type=Path)
    p.add_argument("--private-output", required=True, type=Path)
    a = p.parse_args()
    started = time.monotonic()
    receipt = json.loads((PUBLIC / "RUN_RECEIPT.json").read_text())
    protocol = json.loads((PUBLIC / "FROZEN_PROTOCOL.json").read_text())
    assert digest(PUBLIC / "FROZEN_PROTOCOL.json") == receipt["protocol_sha256"]
    assert digest(PUBLIC / "SCORES.json") == receipt["score_sha256"]
    assert digest(PUBLIC / "SCORER_SOURCE_SNAPSHOT.py") == protocol["code_sha256"]
    assert digest(PUBLIC / "ROOT_SCORING_SOURCE_SNAPSHOT.py") == protocol["scoring_sha256"]
    assert digest(a.joined) == receipt["source_joined_sha256"] == protocol["joined_sha256"]
    packet = json.loads(gzip.decompress(a.joined.read_bytes()), parse_float=Decimal)
    assert packet["protocol_sha256"] == protocol["joined_protocol_sha256"]
    outer = packet["rows"]
    assert len(outer) == 285 and all((r["season"], r["week"]) == (2026, 7) for r in outer)
    assert len({r["source_row_index"] for r in outer}) == len(outer)
    expected = []
    by_strategy = collections.defaultdict(list)
    for source in outer:
        for rule in ("original", POINT, "alwaysOver", "alwaysUnder"):
            if rule == "original":side = source["side"]
            elif rule == "alwaysOver":side = "over"
            elif rule == "alwaysUnder":side = "under"
            elif source["prediction"] is None:side = None
            else:side = "over" if source["prediction"] > Decimal(str(source["line"])) else "under" if source["prediction"] < Decimal(str(source["line"])) else None
            y, line = source["actual"], Decimal(str(source["line"]))
            state = "ABSTAIN" if side is None else "UNKNOWN_PARTICIPATION" if source["participation"] == "UNKNOWN" else "MISSING_ACTUAL" if y is None else "PUSH" if y == line else "WIN" if (y > line if side == "over" else y < line) else "LOSS"
            r = dict(index=source["source_row_index"], strategy=rule, selected_side=side, original_side=source["side"], state=state,
                     game=source["game_id"], player=source["player_id"], target=source["target"], position=source["position"], line_from=source["line_from"], top_over=source["top_over"], top_under=source["top_under"])
            expected.append((source, r))
            by_strategy[rule].append(r)
    grade_path = a.grade_root / "GRADED_ROWS.json.gz"
    assert digest(grade_path) == receipt["private_grade_packet"]["sha256"]
    assert grade_path.stat().st_size == receipt["private_grade_packet"]["bytes"]
    graded = json.loads(gzip.decompress(grade_path.read_bytes()), parse_float=Decimal)["rows"]
    assert len(graded) == len(expected) == 1140
    for actual, (source, r) in zip(graded, expected):
        assert {k:actual[k] for k in source} == source
        assert actual["strategy"] == r["strategy"] and actual["selected_side"] == r["selected_side"]
        assert actual["original_side"] == r["original_side"] and actual["statistical_state"] == r["state"]
        assert actual["settlement_state"] == "UNRESOLVED_CONTRACT" and actual["net_return"] is None
        assert actual["price"] is None and actual["probability"] is None
    scores = json.loads((PUBLIC / "SCORES.json").read_text())
    assert len(scores) == 92
    original = {r["index"]:r for r in by_strategy["original"]}
    interval_count = 0
    for view in scores:
        dimension, value = view["group_id"].split(":", 1)
        rows = subgroup(by_strategy[view["strategy"]], dimension, value)
        n = collections.Counter(r["state"] for r in rows)
        metrics = view["selection_metrics"]
        assert metrics["status_counts"] == dict(n)
        w, l, push = n["WIN"], n["LOSS"], n["PUSH"]
        assert metrics["WIN"] == w and metrics["LOSS"] == l and metrics["PUSH"] == push
        assert view["n"] == w+l and view["forecast_rows"] == len(rows)
        close(metrics["hit_rate"], w/(w+l) if w+l else None)
        close(view["selection_loss_rate"], l/(w+l) if w+l else None)
        assert metrics["denominators"] == dict(outer_rows=len(rows), decided=w+l, supported_threshold_outcomes=w+l+push,
            abstained=n["ABSTAIN"], unresolved=len(rows)-w-l-push-n["ABSTAIN"])
        assert view["query_membership_sha256"] == hashlib.sha256(canonical(sorted(r["index"] for r in rows))).hexdigest()
        assert view["unique_games"] == len({r["game"] for r in rows})
        assert view["unique_player_games"] == len({(r["game"], r["player"]) for r in rows})
        assert metrics["bookmaker_settlement_status_counts"] == {"UNRESOLVED_CONTRACT":len(rows)}
        assert all(metrics["returns"][k] is None for k in ("net", "ROI", "drawdown"))
        assert all(metrics["probability_scores"][k] is None for k in ("brier", "log_loss"))
        for key, baseline in (("game_uncertainty", None), ("paired_vs_original", original)):
            result, stated = interval(rows, baseline), metrics[key]
            close(stated["estimate"], result["estimate"])
            close(stated["game_interval"], result["interval"])
            assert stated["game_clusters"] == result["games"]
            assert stated["paired_n"] == (result["n"] if baseline is not None else None)
            assert stated["week_interval"] is None and stated["week_interval_status"] == "INSUFFICIENT_WEEK_CLUSTERS"
            interval_count += int(result["interval"] is not None)
    side_table = []
    partitions_checked = 0
    for strategy, rows in sorted(by_strategy.items()):
        for target in ["ALL"]+sorted({r["target"] for r in rows}):
            base = rows if target == "ALL" else [r for r in rows if r["target"] == target]
            partitions = []
            for side in ("ALL", "over", "under", "ABSTAIN"):
                subset = base if side == "ALL" else [r for r in base if r["selected_side"] == (None if side == "ABSTAIN" else side)]
                count = collections.Counter(r["state"] for r in subset)
                w, l = count["WIN"], count["LOSS"]
                row = dict(strategy=strategy, target=target, actual_selected_side=side, outer_rows=len(subset), wins=w, losses=l, pushes=count["PUSH"], unknown_participation=count["UNKNOWN_PARTICIPATION"], abstained=count["ABSTAIN"], decided=w+l, hit_rate=w/(w+l) if w+l else None)
                side_table.append(row)
                partitions.append(row)
            for key in ("outer_rows", "wins", "losses", "pushes", "unknown_participation", "abstained", "decided"):
                assert partitions[0][key] == sum(r[key] for r in partitions[1:])
            partitions_checked += 1
    side_path = HERE / "ACTUAL_SIDE_INDEPENDENT_COUNTS.json"
    side_path.write_text(json.dumps(dict(source_grade_packet_sha256=digest(grade_path), rows=side_table), indent=2)+"\n")
    examples = []
    for state in ("WIN", "LOSS"):
        source, r = next((source, r) for source, r in expected if r["strategy"] == "original" and r["state"] == state)
        examples.append(dict(kind="ACTUAL_RETAINED_W7_CASE", source_row_index=r["index"], game_id=r["game"], player_id=r["player"], target=r["target"], side=r["selected_side"], line=str(source["line"]), actual=str(source["actual"]), statistical_state=state, bookmaker_state="UNRESOLVED_CONTRACT"))
    examples += [dict(kind="FICTIONAL_BOUNDARY_CASE", target="rec", actual="1", line="1", side="over", state="PUSH"),
                 dict(kind="FICTIONAL_BOUNDARY_CASE", participation="verified_DNP", contract="verified_refund_on_DNP", state="VOID")]
    a.private_output.mkdir(parents=True, exist_ok=True)
    example_path = a.private_output / "INDEPENDENT_CASES.json.gz"
    if example_path.exists():raise ValueError("Preserve original independent examples")
    example_path.write_bytes(gzip.compress(canonical(examples), mtime=0))
    main = [r for r in side_table if r["target"] == "ALL" and r["actual_selected_side"] == "ALL"]
    report = dict(state="PASS_INDEPENDENT_FIRST_DIRECTION_SCORECARD", protocol_sha256=receipt["protocol_sha256"], scores_sha256=receipt["score_sha256"],
        joined_input_sha256=digest(a.joined), grade_packet_sha256=digest(grade_path), original_rows=285, strategy_row_views_checked=1140,
        canonical_aggregate_views_checked=92, aggregate_components_checked="All state counts, decisive/outer/abstention/unresolved denominators, selected-side hit/loss rates, membership hashes, distinct games/player-games, unsupported probability/return nulls and both uncertainty products.", game_bootstrap_intervals_independently_recomputed=interval_count,
        side_partition_groups_checked=partitions_checked, actual_side_count_projection_sha256=digest(side_path), all_strategy_summary=main,
        private_case_artifact=dict(artifact_id="V2-INDEPENDENT-PROP-W7-WIN-LOSS-AND-FICTIONAL-REFUNDS-V1", sha256=digest(example_path), bytes=example_path.stat().st_size, actual_cases=2, fictional_boundary_cases=2),
        limitation="Original rows and current-vintage labels are exposed. No authenticated settlement, odds, probability, ROI, profitability or live-website improvement. There are zero actual push/void cases in this panel; their correctness is established by fictional boundary checks only. Mandatory category-by-actual-selected-side source projection still needs its separate readback.",
        new_fits=0, inference_calls=0, new_forecasts=0, new_NFL_observations=0, current2026_week8_outcomes_read=0,
        wall_seconds=time.monotonic()-started, peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    path = HERE / "FIRST_SCORECARD_INDEPENDENT_REVIEW.json"
    if path.exists():raise ValueError("Retain the original scorecard review")
    path.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("state", "strategy_row_views_checked", "canonical_aggregate_views_checked", "game_bootstrap_intervals_independently_recomputed", "all_strategy_summary", "wall_seconds", "peak_rss_bytes")}))


if __name__ == "__main__":main()
