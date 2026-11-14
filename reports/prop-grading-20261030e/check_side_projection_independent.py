#!/usr/bin/env python3
"""Replay retained-grade actual-side/K/cohort projections, without threshold grading."""
import argparse
import collections
from datetime import datetime
from decimal import Decimal
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import resource
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PUBLIC = HERE / "actual-side-projection-v2"


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(v):return json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
def read_gzip(p):return json.loads(gzip.decompress(Path(p).read_bytes()), parse_float=Decimal)
def near(a, b):
    if a is None or b is None:assert a is b
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b):near(x, y)
    else:assert math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12), (a, b)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-root", required=True, type=Path)
    parser.add_argument("--cohort-memberships", required=True, type=Path)
    a = parser.parse_args()
    start = time.monotonic()
    protocol = json.loads((PUBLIC / "FROZEN_PROTOCOL.json").read_text())
    receipt = json.loads((PUBLIC / "RUN_RECEIPT.json").read_text())
    assert sha(PUBLIC / "FROZEN_PROTOCOL.json") == receipt["protocol_sha256"]
    assert sha(PUBLIC / "SCORES.json") == receipt["score_sha256"]
    assert sha(PUBLIC / "PROJECTION_SOURCE_SNAPSHOT.py") == protocol["code_sha256"]
    binding_path = a.private_root / "INPUT_BINDINGS_PRIVATE.json"
    assert sha(binding_path) == protocol["private_binding_sha256"]
    bindings = json.loads(binding_path.read_text())
    for field, digest_field in (("graded", "source_grade_sha256"), ("cohort_tags", "cohort_tags_sha256"), ("universe", "universe_metadata_sha256"), ("threshold_census", "threshold_census_sha256")):
        assert sha(bindings[field]) == protocol[digest_field]
    records = read_gzip(bindings["graded"])["rows"]
    assert len(records) == 1140
    by = collections.defaultdict(list)
    for r in records:by[r["strategy"]].append(r)
    assert set(by) == set(protocol["strategies"])
    assert all(len(rows) == 285 for rows in by.values())
    tags = {r["source_row_index"]:r for r in read_gzip(bindings["cohort_tags"])["rows"]}
    assert len(tags) == 285
    map_protocol = json.loads((HERE / "evidence-inventory/side-cohort-mapping-v1/FROZEN_COHORT_MAP_PROTOCOL.json").read_text())
    assert sha(a.cohort_memberships) == map_protocol["membership_sha256"]
    members = {tuple(r["key"]):r for r in read_gzip(a.cohort_memberships) if r["key"][0].startswith("2026_07_")}
    assert len(members) == 1973
    matched = unavailable = 0
    proof_clock = datetime.fromisoformat(map_protocol["source_server_retention_clock"].replace("Z", "+00:00")).timestamp()
    for r in by["original"]:
        tag = tags[r["source_row_index"]]
        key = tuple(r[k] for k in ("game_id", "player_id", "target", "population"))
        assert tuple(tag[k] for k in ("game_id", "player_id", "target", "population")) == key
        source = members.get(key)
        if source is None:
            assert not tag["source_cohorts"] and tag["membership_state"] == "UNMATCHED_SOURCE_COHORT"
            unavailable += 1
        else:
            assert source["cohorts"] == tag["source_cohorts"] and source["rank"] == tag["original_rank"]
            near(source["ranking_cutoff"], tag["ranking_cutoff"])
            near(source["latest_available"], tag["latest_available"])
            assert tag["ranking_cutoff"] <= Decimal(str(proof_clock))
            if tag["latest_available"] is not None:assert tag["latest_available"] < tag["ranking_cutoff"]
            matched += 1
    assert (matched, unavailable) == (279, 6)
    universe = json.loads(Path(bindings["universe"]).read_text())
    census = json.loads(Path(bindings["threshold_census"]).read_text())
    # Producer stores a normalized copy in the bound universe metadata.
    if "eligible_universe_by_target" in universe:
        full = universe["eligible_universe_by_target"]
        provider = universe.get("provider_threshold_by_target")
        synthetic = universe.get("synthetic_threshold_by_target")
    else:
        full = {r["target"]:r["eligible_original_source_rows"] for r in universe["target_coverage"]}
        provider = None
        synthetic = None
    if provider is None:
        provider, synthetic = collections.Counter(), collections.Counter()
        for r in census["target_cross_states"]:
            assert r["line_from"] in ("ours", "dk", "sleeper")
            if r["finite_line"] and r["adjusted_point_present"]:
                (synthetic if r["line_from"] == "ours" else provider)[r["target"]] += r["n"]
    assert sum(full.values()) == 1419 and sum(provider.values()) == 462 and sum(synthetic.values()) == 957
    lists_path = a.private_root / "FROZEN_K_MEMBERSHIPS.json.gz"
    assert sha(lists_path) == protocol["frozen_memberships_sha256"]
    frozen = read_gzip(lists_path)["rows"]
    assert len(frozen) == 360
    ranks = {}
    for membership in frozen:
        rule, target, scope, k = (membership[x] for x in ("strategy", "target", "rank_scope", "K"))
        pool = [r for r in by[rule] if r["target"] == target and r["selected_side"] in ("over", "under") and (scope == "Combined" or r["selected_side"] == scope)]
        def rank(r):
            gap = abs(Decimal(str(r["prediction"]))-Decimal(str(r["line"])))
            return (-gap, r["game_id"], r["player_id"], r["target"], str(Decimal(str(r["line"]))), r["selected_side"], r["source_row_index"])
        chosen = sorted(pool, key=rank)[:k]
        assert membership["eligible_pool_n"] == len(pool)
        assert membership["source_row_indices"] == [r["source_row_index"] for r in chosen]
        assert len(chosen) == min(k, len(pool))
        ranks[rule, target, scope, k] = chosen
    for rule in by:
        for target in protocol["targets"]:
            for scope in ("Combined", "over", "under"):
                for k1, k2 in ((6, 10), (10, 20)):
                    assert [r["source_row_index"] for r in ranks[rule, target, scope, k1]] == [r["source_row_index"] for r in ranks[rule, target, scope, k2]][:k1]

    def cohort(r, name):
        if name == "ALL":return True
        if name.startswith("position:"):return r["position"] == name.split(":", 1)[1]
        if name == "original_saved_top_over":return r["top_over"]
        if name == "original_saved_top_under":return r["top_under"]
        if name == "any_original_saved_top":return r["top_over"] or r["top_under"]
        if name == "not_original_saved_top":return not (r["top_over"] or r["top_under"])
        source = tags.get(r["source_row_index"])
        if name == "cohort_unavailable":return source is None or not source["source_cohorts"]
        assert name.startswith("reconstructed:")
        return source is not None and name.split(":", 1)[1] in source["source_cohorts"]

    spec = importlib.util.spec_from_file_location("independent_original_bootstrap", HERE / "check_first_scorecard_independent.py")
    independent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(independent)
    scores = json.loads((PUBLIC / "SCORES.json").read_text())
    assert len(scores) == receipt["canonical_score_views"] == 7440
    assert len({r["record_id"] for r in scores}) == len(scores)
    uncertainty_cache = {}
    empty = aliases = 0
    group_rows = collections.defaultdict(dict)
    alias_rows = collections.defaultdict(dict)
    for view in scores:
        rule, target = view["strategy"], view["target"]
        source = [r for r in by[rule] if target == "ALL" or r["target"] == target]
        if view["K"] is None:
            population = [r for r in source if cohort(r, view["cohort_id"])]
            base = [r for r in population if r["selected_side"] in ("over", "under")]
        else:
            population = source
            base = ranks[rule, target, view["rank_scope"], view["K"]]
        selected = [r for r in base if view["side"] == "Combined" or r["selected_side"] == view["side"]]
        count = collections.Counter(r["statistical_state"] for r in selected)
        w, l, push, outer = count["WIN"], count["LOSS"], count["PUSH"], len(selected)
        sm = view["selection_metrics"]
        assert sm["WIN"] == w and sm["LOSS"] == l and sm["PUSH"] == push
        assert sm["status_counts"] == {s:count[s] for s in ("WIN", "LOSS", "PUSH", "UNKNOWN_PARTICIPATION", "MISSING_ACTUAL", "DNP", "PENDING", "ABSTAIN")}
        assert view["n"] == w+l and view["forecast_rows"] == outer
        near(sm["hit_rate"], w/(w+l) if w+l else None)
        near(view["selection_loss_rate"], l/(w+l) if w+l else None)
        assert sm["denominators"] == dict(outer_rows=outer, decided=w+l, supported_threshold_outcomes=w+l+push, unresolved=outer-w-l-push)
        assert view["query_membership_sha256"] == hashlib.sha256(canonical(sorted(r["source_row_index"] for r in selected))).hexdigest()
        assert view["unique_games"] == len({r["game_id"] for r in selected})
        assert sm["selection_pool_count"] == len(population)
        near(sm["conditional_selection_coverage"], outer/len(population) if population else None)
        near(sm["original_fullfeed_coverage"], 285/1419)
        near(sm["original_provider_threshold_coverage"], 285/462)
        assert sm["authentic_offer_universe_count"] is None
        if view["cohort_id"] in ("ALL", "NEW_RETRO_PICK_SUBSET"):
            assert sm["full_forecast_feed_count"] == (1419 if target == "ALL" else full[target])
            assert sm["provider_labelled_finite_threshold_count"] == (462 if target == "ALL" else provider.get(target, 0))
            assert sm["site_generated_threshold_count"] == (957 if target == "ALL" else synthetic.get(target, 0))
        else:assert sm["full_forecast_feed_count"] is None and sm["provider_labelled_finite_threshold_count"] is None
        assert sm["bookmaker_settlement_status_counts"] == {"UNRESOLVED_CONTRACT":outer}
        assert all(sm["returns"][k] is None for k in ("net", "ROI", "drawdown"))
        assert all(sm["probability_scores"][k] is None for k in ("brier", "log_loss"))
        key = (rule, tuple(sorted(r["source_row_index"] for r in selected)))
        if key not in uncertainty_cache:
            uncertainty_cache[key] = independent.interval([dict(index=r["source_row_index"], state=r["statistical_state"], game=r["game_id"]) for r in selected])
        expected = uncertainty_cache[key]
        near(sm["game_uncertainty"]["estimate"], expected["estimate"])
        near(sm["game_uncertainty"]["game_interval"], expected["interval"])
        assert sm["game_uncertainty"]["game_clusters"] == expected["games"]
        assert sm["game_uncertainty"]["week_interval"] is None
        if not w+l:
            assert view["selection_loss_rate"] is None and sm["hit_rate"] is None and view["state"] == "N_A"
            empty += 1
        group = (rule, target, view["cohort_id"], view["rank_scope"], view["K"])
        group_rows[group + (view["time_panel_id"],)][view["side"]] = view
        alias_rows[group + (view["side"],)][view["season_alias_of_week_view"]] = view
        aliases += int(view["season_alias_of_week_view"])
    for sides in group_rows.values():
        assert set(sides) == {"over", "under", "Combined"}
        for field in ("WIN", "LOSS", "PUSH"):
            assert sides["Combined"]["selection_metrics"][field] == sides["over"]["selection_metrics"][field]+sides["under"]["selection_metrics"][field]
        for field in ("forecast_rows", "n"):
            assert sides["Combined"][field] == sides["over"][field]+sides["under"][field]
        for state in sides["Combined"]["selection_metrics"]["status_counts"]:
            assert sides["Combined"]["selection_metrics"]["status_counts"][state] == sum(sides[x]["selection_metrics"]["status_counts"][state] for x in ("over", "under"))
    for pair in alias_rows.values():
        assert set(pair) == {False, True}
        for field in ("n", "forecast_rows", "unique_games", "query_membership_sha256", "selection_metrics", "selection_loss_rate", "state", "null_reason"):
            assert pair[False][field] == pair[True][field]
    unavailable = json.loads((PUBLIC / "UNAVAILABLE_CELLS.json").read_text())
    assert len(unavailable) == 48
    assert all(r["target"] in ("anytime_td", "nick-chart-ppr-v1") and all(r[k] is None for k in ("n", "WIN", "LOSS", "PUSH", "hit_rate", "selection_loss_rate", "selection_count")) for r in unavailable)
    assert all(view["target"] not in ("anytime_td", "nick-chart-ppr-v1") for view in scores)
    report = dict(state="PASS_ALL_ACTUAL_SIDE_CATEGORY_COHORT_AND_RETRO_K_PROJECTIONS", protocol_sha256=receipt["protocol_sha256"], scores_sha256=receipt["score_sha256"],
        retained_grade_packet_sha256=protocol["source_grade_sha256"], actual_side_score_views=7440, exact_combined_over_under_partitions=len(group_rows),
        same_week_season_alias_pairs_checked=len(alias_rows), season_alias_rows=aliases, empty_or_unresolved_views_with_null_loss=empty,
        frozen_per_category_topK_lists=360, K_values=[6,10,20], prior_cohort_tags_exact=279, missing_tags_preserved=6,
        independent_unique_bootstrap_membership_views=len(uncertainty_cache), separate_unsupported_contract_cells=len(unavailable),
        original_full_source_rows=1419, provider_labelled_threshold_rows=462, site_generated_rows=957, selected_original_rows=285,
        strict_timing_limit="K subsets are newly registered exposed retrospective subsets of a server-retained thirteen-game panel. They are not original issued K, an authentic whole-week star list, priced picks or future selector performance.",
        alias_policy="3720season rows are exact aliases of3720week views. They must remain typed and excluded from duplicate ranking/sample totals; no observation can be counted twice.",
        new_fits=0, inference_calls=0, new_forecasts=0, new_threshold_grades=0, new_NFL_observations=0, current2026_week8_outcomes_read=0,
        wall_seconds=time.monotonic()-start, peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    out = HERE / "ACTUAL_SIDE_K_COHORT_INDEPENDENT_REVIEW.json"
    if out.exists():raise ValueError("Preserve prior independent review")
    out.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("state", "actual_side_score_views", "exact_combined_over_under_partitions", "same_week_season_alias_pairs_checked", "frozen_per_category_topK_lists", "wall_seconds", "peak_rss_bytes")}))


if __name__ == "__main__":main()
