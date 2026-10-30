#!/usr/bin/env python3
"""Check published selected-total tables and CSV projections against frozen scores."""
import csv
import hashlib
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SIDE = HERE / "actual-side-projection-v2"


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def text_cell(r, push=True):
    s = r["selection_metrics"]
    rate = "N/A" if not r["n"] else f"{100*s['WIN']/r['n']:.2f}%"
    result = f"{s['WIN']}W/{s['LOSS']}L" + (f"/{s['PUSH']}P" if push else "")
    return f"{r['forecast_rows']} selected; {result}; {r['n']} decided; {rate}; {s['status_counts']['UNKNOWN_PARTICIPATION']} unknown"


def main():
    started = time.monotonic()
    scores = load(SIDE / "SCORES.json")
    source_sha = sha(SIDE / "SCORES.json")
    metadata = {r["record_id"]:r for r in load(SIDE / "METADATA_SUPPLEMENT.json")["rows"]}
    byid = {r["record_id"]:r for r in scores}
    lookup = {(r["strategy"],r["target"],r["side"],r["cohort_id"],r["K"],r["rank_scope"],r["season_alias_of_week_view"]):r for r in scores}
    refresh = load(SIDE / "READABLE_REPORT_REFRESH_RECEIPT.json")
    assert refresh["source_score_sha256"] == source_sha
    assert refresh["code_sha256"] == sha(SIDE / "REPORT_GENERATOR_V2.py")
    for ref in refresh["report_files"]:assert sha(SIDE / ref["path"]) == ref["sha256"]
    cells = 0
    unavailable_cells = 0
    strategy = None
    for line in (HERE / "ALL_METHODS_CATEGORY_SIDE_TABLES.md").read_text().splitlines():
        if line.startswith("## "):strategy = line[3:]
        if not line.startswith("| ") or strategy is None:continue
        fields = [x.strip() for x in line.split("|")[1:-1]]
        if fields[0] in ("Category", "---"):continue
        assert len(fields) == 4
        for side, cell in zip(("over","under","Combined"),fields[1:]):
            if fields[0] in ("anytime_td","nick-chart-ppr-v1"):
                assert cell.startswith("Unavailable:")
                unavailable_cells += 1
            else:
                expected = lookup[strategy,fields[0],side,"ALL",None,None,False]
                assert cell == text_cell(expected,False)
                cells += 1
    assert cells == 132 and unavailable_cells == 24
    for line in (SIDE / "README.md").read_text().splitlines():
        if not line.startswith("|") or line.startswith("|---"):continue
        f = [x.strip() for x in line.split("|")[1:-1]]
        if len(f) != 4 or f[0] in ("Category","Strategy"):continue
        if f[0] in ("anytime_td","nick-chart-ppr-v1"):continue
        if f[0] in ("original","SAVED_POINT_DIRECTION_RETAINED_PRECISION","alwaysOver","alwaysUnder"):
            rule,target = f[0],"ALL"
        else:rule,target = "original",f[0]
        for side, cell in zip(("over","under","Combined"),f[1:]):
            assert cell == text_cell(lookup[rule,target,side,"ALL",None,None,False])
            cells += 1
    for line in (SIDE / "TOPK_BY_CATEGORY.md").read_text().splitlines():
        if not line.startswith("|") or line.startswith("|---"):continue
        f = [x.strip() for x in line.split("|")[1:-1]]
        if f[0] == "Category":continue
        assert len(f) == 9
        target,k,scope = f[0],int(f[1]),f[2]
        for side, cell in zip(("over","under","Combined"),f[3:6]):
            assert cell == text_cell(lookup["original",target,side,"NEW_RETRO_PICK_SUBSET",k,scope,False])
            cells += 1
        r = lookup["original",target,"Combined","NEW_RETRO_PICK_SUBSET",k,scope,False]
        m = metadata[r["record_id"]]
        assert list(map(int,f[6:])) == [r["forecast_rows"],m["unique_players"],m["unique_player_games"]]
    for line in (SIDE / "COHORTS.md").read_text().splitlines():
        if not line.startswith("|") or line.startswith("|---"):continue
        f = [x.strip() for x in line.split("|")[1:-1]]
        if f[0] == "Cohort":continue
        assert len(f) == 6
        r = lookup["original","ALL",f[1],f[0],None,None,False]
        m = metadata[r["record_id"]]
        assert list(map(int,f[2:5])) == [r["forecast_rows"],m["unique_players"],m["unique_player_games"]]
        assert f[5] == text_cell(r)
        cells += 1
    all_csv = {}
    with (SIDE / "ALL_ACTUAL_SIDE_VIEWS.csv").open(newline="") as stream:
        for row in csv.DictReader(stream):
            rid = row["record_id"]
            assert rid not in all_csv
            all_csv[rid] = row
            r,m = byid[rid],metadata[rid]
            assert row["actual_selected_side"] == r["side"] and row["target"] == r["target"] and row["strategy"] == r["strategy"]
            for field,value in (("source_selected_rows",r["forecast_rows"]),("decided",r["n"]),("wins",r["selection_metrics"]["WIN"]),("losses",r["selection_metrics"]["LOSS"]),("pushes",r["selection_metrics"]["PUSH"]),("unknown",r["selection_metrics"]["status_counts"]["UNKNOWN_PARTICIPATION"]),("unique_players",m["unique_players"]),("unique_player_games",m["unique_player_games"]),("unique_games",m["unique_games"])):
                assert int(row[field]) == value
            assert row["alias_of_record_id"] == (m["alias_of_record_id"] or "")
            assert row["source_score_sha256"] == source_sha
            assert all(row[k] == "" for k in ("probability","decimal_price","Brier","log_loss","EV","ROI","drawdown"))
    assert set(all_csv) == set(byid)
    subset_counts = {}
    for name, predicate in (("COHORT_BY_CATEGORY_SIDE.csv",lambda r:r["K"] is None and r["cohort_id"] != "ALL"),("TOPK_BY_CATEGORY.csv",lambda r:r["K"] is not None)):
        expected = {r["record_id"] for r in scores if predicate(r)}
        actual = set()
        with (SIDE / name).open(newline="") as stream:
            for row in csv.DictReader(stream):
                assert row["record_id"] not in actual
                assert row == all_csv[row["record_id"]]
                actual.add(row["record_id"])
        assert actual == expected
        subset_counts[name] = len(actual)
    report = dict(state="PASS_READABLE_SELECTED_TOTALS_AND_SOURCE_BOUND_CSV_SUBSETS", source_scores_sha256=source_sha,
        refresh_receipt_sha256=sha(SIDE / "READABLE_REPORT_REFRESH_RECEIPT.json"), report_generator_sha256=refresh["code_sha256"],
        human_statistical_cells_checked=cells, human_unsupported_contract_cells_checked=unavailable_cells,
        full_csv_rows_checked=len(all_csv), identical_csv_subset_rows=subset_counts,
        readable_files={str(p.relative_to(ROOT)):sha(p) for p in (HERE/"ALL_METHODS_CATEGORY_SIDE_TABLES.md",SIDE/"README.md",SIDE/"TOPK_BY_CATEGORY.md",SIDE/"COHORTS.md")},
        all_statistical_cells_explicitly_show_selected_total=True, same_count_denominators_and_null_prices=True,
        scope="Formatting and source-aggregate parity only; no player/game target labels, new threshold decisions, fitting or inference read or executed.",
        new_fits=0, inference_calls=0, new_forecasts=0, new_threshold_grades=0, new_NFL_observations=0, current2026_week8_outcomes_read=0,
        wall_seconds=time.monotonic()-started)
    out = HERE / "READABLE_TABLES_INDEPENDENT_READBACK.json"
    if out.exists():raise ValueError("Preserve prior readable review")
    out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("state","human_statistical_cells_checked","human_unsupported_contract_cells_checked","full_csv_rows_checked","identical_csv_subset_rows","wall_seconds")}))


if __name__ == "__main__":main()
