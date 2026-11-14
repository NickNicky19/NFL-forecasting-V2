#!/usr/bin/env python3
"""Check bound aggregate prop projections; never read NFL prediction/outcome rows."""
import collections
import csv
import itertools
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.check_analysis_index_coverage import read_bound

SIDES = ("over", "under", "Combined")
DIMS = ("strategy", "target", "cohort_id", "K", "rank_scope", "time_panel_id", "horizon_id")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def count(value):
    require(type(value) is int and value >= 0, "Invalid nonnegative count")
    return value


def equal_rate(value, numerator, denominator):
    if denominator == 0:
        require(value is None, "Empty denominator must have null rate")
    else:
        require(isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) and math.isclose(value, numerator/denominator,
                                                        rel_tol=0, abs_tol=1e-12),
                "Incorrect rate or denominator")


def validate(manifest, scores, supplement, unsupported):
    full_pool = manifest.get("scope") == "full-provider-pool-v1"
    require(len(scores) == manifest["audit_views"], "Audit score coverage changed")
    require(supplement["source_score_sha256"] == manifest["source_scores"]["sha256"],
            "Metadata binds another score version")
    rows = supplement["rows"]
    ids = {r["record_id"] for r in scores}
    require(len(ids) == len(scores), "Repeated source score ID")
    metadata = {r["record_id"]: r for r in rows}
    require(len(metadata) == len(rows) == len(scores) and set(metadata) == ids,
            "Metadata/source ID census mismatch")
    dimensions = tuple(manifest.get("required_group_dimensions", DIMS))
    require(set(dimensions) == set(DIMS), "Missing required scoreboard dimension")
    required_sides = tuple(manifest.get("required_actual_selected_sides", SIDES))
    require(set(required_sides) == set(SIDES), "Actual selected-side contract changed")
    groups = collections.defaultdict(dict)
    byid = {r["record_id"]: r for r in scores}
    aliases = 0
    for r in scores:
        side = r["side"]
        require(side in required_sides and (full_pool or r["actual_preselected_side"] == side),
                "Actual selected-side identity mismatch")
        key = tuple(r[k] for k in dimensions)
        require(side not in groups[key], "Duplicate selected side in group")
        groups[key][side] = r
        m = r["selection_metrics"]
        states, books, den = m["status_counts"], m["bookmaker_settlement_status_counts"], m["denominators"]
        for c in list(states.values()) + list(books.values()) + list(den.values()):
            count(c)
        selected = count(r["forecast_rows"])
        wins, losses, pushes = (count(states[k]) for k in ("WIN", "LOSS", "PUSH"))
        require(states.get("ABSTAIN", 0) == 0, "Abstentions entered selected-side partition")
        require(sum(states.values()) == sum(books.values()) == selected == den["outer_rows"],
                "Statistical/book/selected denominators differ")
        require(m["WIN"] == wins and m["LOSS"] == losses and m["PUSH"] == pushes,
                "Native outcome counts disagree with status counts")
        require(r["n"] == den["decided"] == wins+losses, "Decided denominator is not W+L")
        require(den["supported_threshold_outcomes"] == wins+losses+pushes
                and den["unresolved"] == selected-wins-losses-pushes,
                "Supported/unresolved denominator mismatch")
        equal_rate(m["hit_rate"], wins, wins+losses)
        equal_rate(r["selection_loss_rate"], losses, wins+losses)
        if any(n and state != "VERIFIED" for state, n in books.items()):
            require(r["settlement_status"] == "UNRESOLVED_CONTRACT"
                    and all(m["returns"][k] is None for k in ("ROI", "net", "drawdown")),
                    "Unverified bookmaker contract gained return metrics")
        meta = metadata[r["record_id"]]
        if full_pool:
            require(not r["season_alias_of_week_view"] and meta["alias_of_record_id"] is None,
                    "Full-pool view fabricated a season alias")
            require(meta["unique_players"] == r["unique_players"]
                    and meta["unique_player_games"] == r["unique_player_games"]
                    and meta["selected_week_count"] == int(selected > 0)
                    and meta["decided_week_count"] == int(wins+losses > 0)
                    and meta["registered_weeks"] == [7], "Full-pool metadata scope mismatch")
            require(r["season"] == 2026 and r["week"] == 7 and r["evaluation_weeks"] == [7]
                    and r["statistic_period"] == "full_game" and r["overtime"] is True,
                    "Full-pool statistical period changed")
            equal_rate(m["selection_coverage"], selected, count(m["eligible_rank_pool_n"]))
            require(count(m["abstentions_outside_selected_partition"]) <= count(m["selection_pool_count"]),
                    "Abstentions exceed source pool")
            require(all(r.get(k) is None for k in ("mae", "mse", "brier", "log_loss"))
                    and all(m["probability_scores"][k] is None for k in ("brier", "log_loss")),
                    "Point-only pool gained probability/numerical metrics")
        else:
            require(meta["source_record_id"] == r["record_id"]
                    and meta["query_membership_sha256"] == r["query_membership_sha256"]
                    and meta["season_alias_of_week_view"] == r["season_alias_of_week_view"],
                    "Metadata identity/membership binding mismatch")
        if r["season_alias_of_week_view"]:
            aliases += 1
            parent_id = meta["alias_of_record_id"]
            require(parent_id in byid and not byid[parent_id]["season_alias_of_week_view"],
                    "Season alias points outside weekly canonical source")
            parent = byid[parent_id]
            skip = {"record_id", "time_panel_id", "week", "season_alias_of_week_view"}
            require({k: v for k, v in r.items() if k not in skip}
                    == {k: v for k, v in parent.items() if k not in skip},
                    "Season alias changes weekly scientific metrics or membership")
            skip_meta = {"record_id", "source_record_id", "alias_of_record_id", "season_alias_of_week_view"}
            require({k: v for k, v in meta.items() if k not in skip_meta}
                    == {k: v for k, v in metadata[parent_id].items() if k not in skip_meta},
                    "Season alias metadata changes weekly scope")
        else:
            require(meta["alias_of_record_id"] is None, "Weekly row aliases another row")
    for sides in groups.values():
        require(set(sides) == set(required_sides), "Missing Over/Under/Combined group cell")
        over, under, combined = (sides[k] for k in SIDES)
        for field in ("forecast_rows", "n"):
            require(combined[field] == over[field]+under[field], "Combined count is not side sum")
        for field in ("WIN", "LOSS", "PUSH"):
            require(combined["selection_metrics"][field]
                    == over["selection_metrics"][field]+under["selection_metrics"][field],
                    "Combined W/L/push is not side sum")
        for field in ("status_counts", "bookmaker_settlement_status_counts", "denominators"):
            a, b, c = (r["selection_metrics"][field] for r in (over, under, combined))
            keys = set(a) | set(b) | set(c)
            require(all(c.get(k, 0) == a.get(k, 0)+b.get(k, 0) for k in keys),
                    "Combined selected/status denominator is not side sum")
    predicate = manifest["default_predicate"]
    require(predicate == {"season_alias_of_week_view": False}, "Default view may pool season aliases")
    default = [r for r in scores if all(r[k] == v for k, v in predicate.items())]
    require(len(default) == manifest["default_views"]
            and aliases == manifest["aliases_retained_not_pooled"]
            and len(default)+aliases == len(scores), "Weekly default/alias census mismatch")
    require(len(unsupported) == manifest["unsupported_cell_count"], "Unsupported cell census mismatch")
    targets = set(manifest["unsupported_targets"])
    strategies = {r["strategy"] for r in scores}
    times = {r["time_panel_id"] for r in scores}
    expected = set(itertools.product(strategies, targets, required_sides)) if full_pool else set(itertools.product(strategies, targets, required_sides, times))
    actual = {(r["strategy"], r["target"], r["side"]) for r in unsupported} if full_pool else {(r["strategy"], r["target"], r["side"], r["time_panel_id"]) for r in unsupported}
    require(len(actual) == len(unsupported) and actual == expected, "Unsupported target grid incomplete")
    require(not targets & {r["target"] for r in scores}, "Unsupported target fabricated scored row")
    for r in unsupported:
        require(r["state"] == "UNAVAILABLE" and bool(r["reason"]), "Unsupported state/reason missing")
        null_fields = ("wins", "losses", "hit_rate", "n", "selected") if full_pool else ("WIN", "LOSS", "PUSH", "hit_rate", "n", "selection_count", "selection_loss_rate")
        require(all(k in r and r[k] is None for k in null_fields),
                "Unsupported missing score changed to fake zero")
    return dict(score_views=len(scores), group_cells=len(groups), metadata_rows=len(rows),
                default_weekly_views=len(default), retained_aliases=aliases,
                unsupported_cells=len(unsupported), unsupported_targets=len(targets))


def validate_csv(binding, scores, metadata, source_sha, scope=None, comparisons=None):
    if scope == "full-provider-pool-v1":
        return validate_full_pool_csv(binding, scores, metadata, source_sha, comparisons)
    rows = list(csv.DictReader(read_bound(binding).decode().splitlines()))
    byid = {r["record_id"]: r for r in scores}
    meta = {r["record_id"]: r for r in metadata["rows"]}
    require(len(rows) == len(byid) and {r["record_id"] for r in rows} == set(byid), "CSV ID coverage mismatch")
    for row in rows:
        r, m = byid[row["record_id"]], meta[row["record_id"]]
        sm = r["selection_metrics"]
        expected = dict(strategy=r["strategy"], target=r["target"], actual_selected_side=r["side"],
                        cohort=r["cohort_id"], time_panel=r["time_panel_id"], K=r["K"], rank_scope=r["rank_scope"],
                        source_selected_rows=r["forecast_rows"], decided=r["n"], wins=sm["WIN"], losses=sm["LOSS"],
                        pushes=sm["PUSH"], unknown=sm["status_counts"]["UNKNOWN_PARTICIPATION"],
                        missing_actual=sm["status_counts"]["MISSING_ACTUAL"], DNP=sm["status_counts"]["DNP"],
                        pending=sm["status_counts"]["PENDING"], hit_rate=sm["hit_rate"],
                        selection_loss_rate=r["selection_loss_rate"], alias_of_record_id=m["alias_of_record_id"],
                        source_score_artifact="SCORES.json", source_score_sha256=source_sha)
        interval = sm["game_uncertainty"]["game_interval"]
        expected.update(
            unique_players=m["unique_players"], unique_player_games=m["unique_player_games"],
            unique_games=m["unique_games"], registered_weeks=json.dumps(m["registered_weeks"]),
            decided_week_count=m["decided_week_count"], original_conditional_pool=sm["selection_pool_count"],
            full_forecast_feed_count=sm["full_forecast_feed_count"],
            provider_labelled_threshold_count=sm["provider_labelled_finite_threshold_count"],
            site_generated_threshold_count=sm["site_generated_threshold_count"],
            original_fullfeed_coverage=sm["original_fullfeed_coverage"],
            original_provider_threshold_coverage=sm["original_provider_threshold_coverage"],
            conditional_selection_coverage=sm["conditional_selection_coverage"],
            eligible_rank_pool=sm.get("eligible_rank_pool_n"),
            game_bootstrap95_low=None if interval is None else interval[0],
            game_bootstrap95_high=None if interval is None else interval[1],
            game_uncertainty_status=sm["game_uncertainty"]["game_interval_status"],
            week_uncertainty_status=sm["game_uncertainty"]["week_interval_status"],
            probability=None, decimal_price=None, Brier=sm["probability_scores"]["brier"],
            log_loss=sm["probability_scores"]["log_loss"], EV=None,
            ROI=sm["returns"]["ROI"], drawdown=sm["returns"]["drawdown"],
            book_settlement=r["settlement_status"], null_reason=r["null_reason"])
        require(set(row) == set(expected) | {"record_id"}, "CSV columns not fully covered by source parity check")
        for key, value in expected.items():
            cell = row[key]
            if value is None:
                require(cell == "", "CSV null rendered as nonnull")
            elif isinstance(value, float):
                require(math.isclose(float(cell), value, rel_tol=0, abs_tol=1e-12), "CSV rate differs from source")
            else:
                require(cell == str(value), "CSV identity/count differs from source")
    return len(rows)


def validate_full_pool_csv(binding, scores, metadata, source_sha, comparisons):
    """F adds no fake precision/side/alias fields to immutable canonical scores."""
    rows = list(csv.DictReader(read_bound(binding).decode().splitlines()))
    byid = {r["record_id"]: r for r in scores}
    meta = {r["record_id"]: r for r in metadata["rows"]}
    require(len(rows) == len(byid) and {r["record_id"] for r in rows} == set(byid), "CSV ID coverage mismatch")
    require(comparisons is not None and comparisons["source_score_sha256"] == source_sha,
            "CSV paired supplement source binding missing")
    pairs = {}
    for item in comparisons["rows"]:
        i = item["source_row_index"]
        require(type(i) is int and 0 <= i < len(scores) and i not in pairs, "Invalid CSV paired source identity")
        pairs[i] = item["comparison"]
    require(len(pairs) == len(scores), "CSV paired supplement coverage mismatch")
    byrecord = {r["record_id"]: pairs[i] for i, r in enumerate(scores)}
    for row in rows:
        r, m = byid[row["record_id"]], meta[row["record_id"]]
        sm = r["selection_metrics"]
        expected = dict(record_id=r["record_id"], method=r["procedure_id"], strategy=r["strategy"],
            target=r["target"], season=r["season"], weeks="7", games=r["unique_games"],
            horizon=r["horizon_id"], evidence=r["selection_evidence"], cohort=r["cohort_id"],
            K=r["K"], rank_scope=r["rank_scope"], side=r["side"],
            eligible=sm["eligible_rank_pool_n"], original_source_pool=sm["selection_pool_count"],
            selected=r["forecast_rows"], wins=sm["WIN"], losses=sm["LOSS"], pushes=sm["PUSH"],
            voids=sm["status_counts"]["VOID"], pending=sm["status_counts"]["PENDING"],
            missing_actual=sm["status_counts"]["MISSING_ACTUAL"], unknown_participation=sm["status_counts"]["UNKNOWN_PARTICIPATION"],
            book_unresolved=r["forecast_rows"], decided=r["n"], hit_rate=sm["hit_rate"],
            error_rate=r["selection_loss_rate"], abstentions=sm["abstentions_outside_selected_partition"],
            selection_coverage=sm["selection_coverage"], unique_players=m["unique_players"],
            unique_player_games=m["unique_player_games"], unique_weeks=m["unique_weeks"],
            game_clusters=sm["game_uncertainty"]["game_clusters"],
            game_interval=json.dumps(sm["game_uncertainty"]["game_interval"]),
            game_interval_status=sm["game_uncertainty"]["game_interval_status"], week_interval=None,
            price=None, probability=None, Brier=None, EV=None, ROI=None, CLV=None,
            comparator="v2-retained-provider-labelled-full-pool-2026W7-v1:SAVED_ADJUSTED_POINT_DIRECTION_RETAINED_PRECISION")
        comparison = byrecord[r["record_id"]]
        if r["n"]:
            require(comparison["paired_n"] == r["n"]
                    and math.isclose(comparison["candidate_error"], r["selection_loss_rate"], rel_tol=0, abs_tol=1e-12),
                    "CSV paired candidate denominator mismatch")
            expected["paired_error_change"] = comparison["candidate_error"] - comparison["comparator_error"]
        else:
            require(comparison["status"] == "UNESTABLISHED", "Unsupported CSV comparison gained a loss")
            expected["paired_error_change"] = None
        require(set(row) == set(expected), "CSV columns not fully covered by source parity check")
        for key, value in expected.items():
            cell = row[key]
            if value is None:require(cell == "", "CSV null rendered as nonnull")
            elif isinstance(value, float):require(math.isclose(float(cell), value, rel_tol=0, abs_tol=1e-12), "CSV rate differs from source")
            else:require(cell == str(value), "CSV identity/count differs from source")
    return len(rows)


def main():
    pointer = json.loads((ROOT / "registries/CURRENT_RESULTS_INDEX.json").read_text())
    manifest = json.loads(read_bound(pointer["prop_scoreboard"]))
    if manifest.get('scope')=='completion-multi-source-v1':
        from tools.check_completion_prop_coverage import validate as validate_completion
        print(json.dumps(validate_completion(manifest),sort_keys=True))
        return
    scores = json.loads(read_bound(manifest["source_scores"]))
    metadata = json.loads(read_bound(manifest["metadata"]))
    unsupported = json.loads(read_bound(manifest["unsupported_cells"]))
    counts = validate(manifest, scores, metadata, unsupported)
    comparisons = json.loads(read_bound(manifest["comparisons"])) if manifest.get("scope") == "full-provider-pool-v1" else None
    counts["bound_csv_rows"] = validate_csv(manifest["records_csv"], scores, metadata, manifest["source_scores"]["sha256"], manifest.get("scope"), comparisons)
    print(json.dumps(dict(state="PASS_PROP_SCOREBOARD_COVERAGE", **counts,
                          new_grades=0, NFL_outcome_rows_read=0), sort_keys=True))


if __name__ == "__main__":
    main()
