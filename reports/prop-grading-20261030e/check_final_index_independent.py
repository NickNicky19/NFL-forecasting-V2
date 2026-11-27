#!/usr/bin/env python3
"""Read back new public index/metadata; reuse retained statuses, never regrade."""
import argparse
import collections
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import resource
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024), b""):h.update(block)
    return h.hexdigest()


def read(path):return json.loads(Path(path).read_text())
def gzip_rows(path):return json.loads(gzip.decompress(Path(path).read_bytes()))["rows"]
def canonical(v):return json.dumps(v, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
def close(a, b):
    if a is None or b is None:assert a is b, (a, b)
    else:assert math.isclose(float(a), float(b), rel_tol=1e-12, abs_tol=1e-12), (a, b)
def csv_value(v):
    return json.dumps(v, separators=(",", ":")) if isinstance(v, (list, dict)) else "" if v is None else str(v)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--projection-private-root", required=True, type=Path)
    a = p.parse_args()
    started = time.monotonic()
    manifest_path = HERE / "results-index/INDEX_MANIFEST.json"
    manifest = read(manifest_path)
    prior_path = ROOT / manifest["previous_sharded_checkpoint"]["artifact"]
    assert sha(prior_path) == manifest["previous_sharded_checkpoint"]["sha256"] == "5357620f2219bd3bfe9108bad72a9d3aa19e15a7c54426fbc5777be74150198d"
    prior = read(prior_path)
    assert len(prior["shards"]) == 90 and prior["record_count"] == 145219
    assert manifest["shards"][:90] == prior["shards"]
    assert manifest["record_count"] == 152751 and manifest["streaming_build"]["new_records"] == 7532
    assert sum(x["records"] for x in manifest["shards"]) == 152751
    # Git verifies immutable prior bytes without decoding their 145219 records again.
    changed = subprocess.check_output(["git", "diff", "--name-only", "c8cb933ab3a297e7deafd61d2886cf089f475342", "--", "reports/continuation-20261029", "reports/continuation-20261030", "reports/continuation-20261030b", "reports/continuation-20261030c", "reports/continuation-20261030d"], cwd=ROOT, text=True)
    assert not changed.strip()
    new_records = []
    for binding in manifest["shards"][90:]:
        path = ROOT / binding["path"]
        assert sha(path) == binding["sha256"] and path.stat().st_size == binding["bytes"]
        obj = read(path)
        rows = obj if isinstance(obj, list) else obj["records"]
        assert len(rows) == binding["records"]
        new_records.extend(rows)
    assert len(new_records) == 7532 and len({r["test_id"] for r in new_records}) == 7532
    sources = {}
    source_hashes = {}
    supplements = {}
    for name in ("first-scorecard-v1", "actual-side-projection-v2"):
        path = HERE / name / "SCORES.json"
        sources[str(path.relative_to(ROOT))] = {r["record_id"]:r for r in read(path)}
        source_hashes[str(path.relative_to(ROOT))] = sha(path)
        sup = read(HERE / name / "METADATA_SUPPLEMENT.json")
        assert sup["source_score_sha256"] == sha(path)
        supplements[name] = {r["record_id"]:r for r in sup["rows"]}
        contract = read(HERE / name / "INDEX_SELECTION_CONTRACT.json")
        assert contract["source_score_sha256"] == sha(path) and contract["common_fields"]["statistic_period"] == "full_game"
    new_bindings = [x for x in manifest["input_manifests"] if "prop-grading-20261030e" in x["source_artifact"]]
    assert len(new_bindings) == 7
    for binding in new_bindings:assert sha(ROOT / binding["source_artifact"]) == binding["sha256"]
    private_protocol = read(HERE / "actual-side-projection-v2/FROZEN_PROTOCOL.json")
    private_bindings = a.projection_private_root / "INPUT_BINDINGS_PRIVATE.json"
    assert sha(private_bindings) == private_protocol["private_binding_sha256"]
    loc = read(private_bindings)
    assert sha(loc["graded"]) == private_protocol["source_grade_sha256"]
    retained = gzip_rows(loc["graded"])
    tags = {r["source_row_index"]:r for r in gzip_rows(loc["cohort_tags"])}
    lists = gzip_rows(a.projection_private_root / "FROZEN_K_MEMBERSHIPS.json.gz")
    top = {(r["strategy"],r["target"],r["rank_scope"],r["K"]):set(r["source_row_indices"]) for r in lists}
    by = collections.defaultdict(list)
    for r in retained:by[r["strategy"]].append(r)
    original = {r["source_row_index"]:r for r in by["original"]}

    def choose(r, group):
        if group == "ALL":return True
        if group.startswith("position:"):return r["position"] == group.split(":",1)[1]
        if group in ("original_saved_top_over","saved_top_over"):return r["top_over"]
        if group in ("original_saved_top_under","saved_top_under"):return r["top_under"]
        if group in ("any_original_saved_top","any_saved_top"):return r["top_over"] or r["top_under"]
        if group in ("not_original_saved_top","not_saved_top"):return not(r["top_over"] or r["top_under"])
        if group == "cohort_unavailable":return not tags[r["source_row_index"]]["source_cohorts"]
        if group.startswith("reconstructed:"):return group.split(":",1)[1] in tags[r["source_row_index"]]["source_cohorts"]
        raise ValueError(group)

    def membership(view, pilot):
        rr = by[view["strategy"]]
        if pilot:
            dim, value = view["group_id"].split(":",1)
            if dim == "ALL":return rr
            if dim == "category":return [r for r in rr if r["target"] == value]
            if dim == "original_side":return [r for r in rr if r["original_side"] == value]
            if dim == "line_source":return [r for r in rr if r["line_from"] == value]
            if dim == "position":return [r for r in rr if r["position"] == value]
            return [r for r in rr if choose(r,dim)]
        rr = [r for r in rr if view["target"] == "ALL" or r["target"] == view["target"]]
        if view["K"] is not None:
            wanted = top[view["strategy"],view["target"],view["rank_scope"],view["K"]]
            rr = [r for r in rr if r["source_row_index"] in wanted]
        else:rr = [r for r in rr if choose(r,view["cohort_id"])]
        return [r for r in rr if view["side"] == "Combined" or r["selected_side"] == view["side"]]

    annotation = read(HERE / "first-scorecard-v1/PAIRED_COMPARISON_ANNOTATIONS.json")
    assert annotation["source_score_sha256"] == sha(HERE / "first-scorecard-v1/SCORES.json")
    paired = {r["source_row_index"]:r["comparison"] for r in annotation["rows"]}
    pilot_order = read(HERE / "first-scorecard-v1/SCORES.json")
    pilot_index = {r["record_id"]:i for i,r in enumerate(pilot_order)}
    result_by_id = {}
    paired_checks = metadata_checks = empty = aliases = 0
    for record in new_records:
        artifact = record["source_artifact"]
        source = sources[artifact][record["source_record_id"]]
        pilot = "first-scorecard" in artifact
        name = "first-scorecard-v1" if pilot else "actual-side-projection-v2"
        meta = supplements[name][source["record_id"]]
        rr = membership(source, pilot)
        decided = [r for r in rr if r["statistical_state"] in ("WIN","LOSS")]
        expected_metadata = dict(unique_players=len({r["player_id"] for r in rr}), unique_player_games=len({(r["game_id"],r["player_id"]) for r in rr}),
            decided_unique_games=len({r["game_id"] for r in decided}), decided_unique_players=len({r["player_id"] for r in decided}),
            decided_unique_player_games=len({(r["game_id"],r["player_id"]) for r in decided}), decided_week_count=int(bool(decided)),
            registered_week_count=1, registered_weeks=[7], selected_week_count=int(bool(rr)), overtime=True, season_type="REG", statistic_period="full_game")
        if "unique_games" in meta:expected_metadata["unique_games"] = len({r["game_id"] for r in rr})
        if "unique_weeks" in meta:expected_metadata["unique_weeks"] = int(bool(rr))
        for k,value in expected_metadata.items():
            field = "games" if k == "unique_games" else k
            assert meta[k] == value and record[field] == value, (source["record_id"],k)
            metadata_checks += 1
        if "query_membership_sha256" in meta:assert meta["query_membership_sha256"] == source["query_membership_sha256"]
        assert record["kind"] == "prop_selection_evaluation" and record["primary_metric"] == "selection_loss_rate"
        assert record["source_artifact_sha256"] == source_hashes[artifact]
        assert record["source_aggregate_fields"] == source
        assert record["period"] == "full_game" and record["weeks"] == [7] and record["seasons"] == [2026]
        assert record["side"] == source["side"] and record["strategy"] == source["strategy"]
        w, l = source["selection_metrics"]["WIN"], source["selection_metrics"]["LOSS"]
        assert record["n"] == w+l
        close(record["primary_error"], l/(w+l) if w+l else None)
        assert all(v is None for k,v in record["metrics"].items() if k != "selection_loss_rate")
        hit = record["precision_metrics"]["decided_pick_hit_rate"]
        assert hit["numerator"] == (w if w+l else None) and hit["denominator"] == w+l
        close(hit["rate"], w/(w+l) if w+l else None)
        stats = record["selection_metrics"]
        assert stats["book_settlement_status_counts"] == {"UNRESOLVED_CONTRACT":len(rr)}
        assert stats["selected_opportunities"] == len(rr)
        assert record["accuracy_status"] == "statistical_threshold_crossing_only"
        if not w+l:
            empty += 1
            assert record["primary_error"] is None
        if not pilot:
            for key in ("cohort_id","K","rank_scope","time_panel_id","season_alias_of_week_view"):
                assert record[key] == source[key]
            assert record["alias_of_record_id"] == meta["alias_of_record_id"]
            aliases += int(record["season_alias_of_week_view"])
        else:
            paired_rr = [r for r in decided if original[r["source_row_index"]]["statistical_state"] in ("WIN","LOSS")]
            c = paired[pilot_index[source["record_id"]]]
            assert record["reporting_comparison"] == c
            assert c["paired_n"] == len(paired_rr)
            assert c["membership_sha256"] == hashlib.sha256(canonical(sorted(r["source_row_index"] for r in paired_rr))).hexdigest()
            close(c["candidate_error"], sum(r["statistical_state"] == "LOSS" for r in paired_rr)/len(paired_rr))
            close(c["comparator_error"], sum(original[r["source_row_index"]]["statistical_state"] == "LOSS" for r in paired_rr)/len(paired_rr))
            close(c["candidate_error"]-c["comparator_error"], c["uncertainty"]["estimate"])
            paired_checks += 1
        result_by_id[record["test_id"]] = record
    assert aliases == 3720 and paired_checks == 92
    side_records = {r["source_record_id"]:r for r in new_records if "actual-side-projection" in r["source_artifact"]}
    for record in side_records.values():
        if record["season_alias_of_week_view"]:
            target = side_records[record["alias_of_record_id"]]
            assert not target["season_alias_of_week_view"]
            for k in ("n","metrics","precision_metrics","selection_metrics"):
                assert record[k] == target[k]
    csv_records_checked = 0
    for binding in manifest["csv_parts"]:
        path = ROOT / binding["path"]
        assert sha(path) == binding["sha256"] and path.stat().st_size == binding["bytes"]
        # Only appended rows need typed readback; earlier JSON shards are immutable.
        if not any(path.name.endswith(x) for x in ("0014.csv","0015.csv")):continue
        with path.open(newline="") as f:
            for row in csv.DictReader(f):
                record = result_by_id.get(row["test_id"])
                if record is None:continue
                for key in ("kind","category","n","primary_metric","primary_error","side","strategy","season_type","statistic_period","cohort_id","K","rank_scope","time_panel_id","season_alias_of_week_view","alias_of_record_id","unique_players","unique_player_games","unique_weeks","decided_unique_games","decided_unique_player_games","registered_week_count","selected_week_count"):
                    assert row[key] == csv_value(record.get(key)), (row["test_id"],key)
                hit = record["precision_metrics"]["decided_pick_hit_rate"]
                for key in ("numerator","denominator","rate"):assert row["decided_pick_"+key] == csv_value(hit[key])
                for state in ("WIN","LOSS","PUSH","VOID","PENDING","MISSING_ACTUAL","UNKNOWN_PARTICIPATION","UNRESOLVED_CONTRACT"):
                    expected = record["selection_metrics"]["book_settlement_status_counts"].get(state,0)
                    assert row["book_settlement_"+state] == str(expected)
                assert row["mae"] == row["brier"] == row["log_loss"] == row["selection_net_return"] == row["selection_ROI"] == ""
                c = record.get("reporting_comparison",{})
                if c.get("status") == "PAIRED_RETAINED_ROWS":
                    delta = c["candidate_error"]-c["comparator_error"]
                    close(row["absolute_error_change"], delta)
                    if c["comparator_error"] == 0:assert row["relative_error_change"] == ""
                    else:close(row["relative_error_change"], delta/c["comparator_error"])
                csv_records_checked += 1
    assert csv_records_checked == 7532
    view = read(HERE / "CURRENT_PROP_SCOREBOARD_VIEW.json")
    assert view["default_views"] == len([r for r in side_records.values() if not r["season_alias_of_week_view"]]) == 3720
    assert view["aliases_retained_not_pooled"] == 3720 and view["pilot_scores_retained_in_audit"] == 92
    pointer_path = ROOT / "registries/CURRENT_RESULTS_INDEX.json"
    pointer = read(pointer_path)
    assert pointer["manifest"] == str(manifest_path.relative_to(ROOT))
    for key in ("default_score_version_manifest","procedure_rankings","top_five_rankings","derived_comparison_manifest","prop_scoreboard"):
        assert sha(ROOT / pointer[key]["path"]) == pointer[key]["sha256"]
    default = read(ROOT / pointer["default_score_version_manifest"]["path"])
    assert default["audit_manifest"] == str(prior_path.relative_to(ROOT)) and default["audit_manifest_sha256"] == sha(prior_path)
    report = dict(state="PASS_NEW_PROP_INDEX_TYPED_FIELDS_ANNOTATIONS_AND_CURRENT_VIEW", manifest_sha256=sha(manifest_path), pointer_sha256=sha(pointer_path),
        index_records=152751, unchanged_prior_records=145219, unchanged_prior_shard_references=90, new_prop_records=7532,
        new_source_shards_checked=len(manifest["shards"])-90, typed_new_csv_records_checked=csv_records_checked,
        bound_new_source_artifacts_checked=len(new_bindings), metadata_values_checked=metadata_checks, paired_pilot_masks_and_losses_checked=paired_checks,
        season_aliases_checked=aliases, current_weekly_prop_views=3720, zero_decided_views_retaining_null_error=empty,
        original_numerical_and_derived_paired_bindings_unchanged=True,
        scope="Public index/CSV and retained-grade metadata/status readback only. No raw NFL joins, actual-minus-line comparisons, bootstrap or model inference repeated.",
        new_fits=0, new_forecasts=0, inference_calls=0, new_threshold_grades=0, new_NFL_observations=0, current2026_week8_outcomes_read=0,
        wall_seconds=time.monotonic()-started, peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    out = HERE / "FINAL_INDEX_INDEPENDENT_READBACK.json"
    if out.exists():raise ValueError("Retain the previous index review")
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("state","index_records","new_prop_records","metadata_values_checked","typed_new_csv_records_checked","wall_seconds","peak_rss_bytes")}))


if __name__ == "__main__":main()
