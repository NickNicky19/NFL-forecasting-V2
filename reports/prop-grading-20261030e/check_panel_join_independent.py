#!/usr/bin/env python3
"""Verify frozen metadata and a panel-only joined packet; no production scorer."""
import argparse
import collections
import csv
from datetime import datetime, timedelta
from decimal import Decimal
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import resource
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PUBLIC = HERE / "evidence-inventory"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clock(value):
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    assert d.tzinfo is not None
    return d


def canon(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def raw_rows(text):
    """Find only top-level rows objects without parsing target numbers."""
    start = re.search(r'"rows"\s*:\s*\[', text).end()
    index = start
    while True:
        while text[index] in " \r\n\t,":index += 1
        if text[index] == "]":return
        assert text[index] == "{"
        beginning = index
        depth = 0
        quoted = escaped = False
        while index < len(text):
            ch = text[index]
            if quoted:
                if escaped:escaped = False
                elif ch == "\\":escaped = True
                elif ch == '"':quoted = False
            elif ch == '"':quoted = True
            elif ch == "{":depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    index += 1
                    yield text[beginning:index]
                    break
            index += 1
        else:raise ValueError("incomplete rows object")


def identity_scalar(raw, key):
    match = re.search(r'"'+re.escape(key)+r'"\s*:\s*("(?:[^"\\]|\\.)*")', raw)
    return None if match is None else json.loads(match.group(1))


def main():
    a = argparse.ArgumentParser(description=__doc__)
    for name in ("metadata-root", "join-root", "source-root", "reference", "original-forward"):
        a.add_argument("--"+name, required=True, type=Path)
    args = a.parse_args()
    started = time.monotonic()
    panel_protocol = json.loads((PUBLIC / "FROZEN_PANEL_PROTOCOL.json").read_text())
    panel_receipt = json.loads((PUBLIC / "FROZEN_PANEL_RECEIPT.json").read_text())
    join_public = PUBLIC / "panel-join-v1"
    protocol = json.loads((join_public / "FROZEN_JOIN_PROTOCOL.json").read_text())
    receipt = json.loads((join_public / "JOIN_COVERAGE_RECEIPT.json").read_text())
    assert sha(PUBLIC / "FROZEN_PANEL_PROTOCOL.json") == panel_receipt["protocol_sha256"]
    assert sha(join_public / "FROZEN_JOIN_PROTOCOL.json") == receipt["protocol_sha256"]
    bindings = {r["logical_member"]:r for r in panel_receipt["private_artifacts"]}
    metadata = {}
    for name, binding in bindings.items():
        p = args.metadata_root / name
        assert sha(p) == binding["sha256"] and p.stat().st_size == binding["bytes"]
        document = json.loads(gzip.decompress(p.read_bytes()))
        assert document["protocol_sha256"] == panel_receipt["protocol_sha256"]
        assert document["source_gzip_sha256"] == panel_protocol["source_gzip_sha256"]
        metadata[name] = document["rows"]
    original_metadata = metadata["ALL_ORIGINAL_METADATA.json.gz"]
    panel = metadata["FROZEN_SIDE_LINE_PANEL.json.gz"]
    assert len(original_metadata) == 2289 and len(panel) == 285
    assert [r["source_row_index"] for r in original_metadata] == list(range(2289))
    admitted = []
    eligibility = collections.Counter()
    supported_targets = set(panel_protocol["ten_supported_numeric_targets"])
    deadline_proof = clock(panel_protocol["server_proven_retained_by_utc"])
    safe_fields = set(original_metadata[0])
    assert not ({"actual", "outcome", "prediction", "adjusted_projection"} & safe_fields)
    for r in original_metadata:
        assert set(r) in (safe_fields, safe_fields | {"sleeper_observation"})
        assert r["price"] is None and r["probability"] is None and r["source_timestamps_verified"] is False
        reason = "SERVER_RETENTION_NOT_BEFORE_T90" if clock(r["kickoff"])-timedelta(minutes=90) <= deadline_proof else "UNSUPPORTED_TARGET_CONTRACT" if r["category"] not in supported_targets else "NO_ORIGINAL_SAVED_SIDE" if r["lean"] not in ("over", "under") else "NONFINITE_ORIGINAL_LINE" if type(r["line"]) not in (int, float) or not math.isfinite(r["line"]) else "ADMITTED"
        assert reason == r["metadata_panel_status"]
        eligibility[reason] += 1
        if reason == "ADMITTED":admitted.append(r)
    assert dict(eligibility) == panel_receipt["eligibility_reason_counts"]
    assert len({(r["game_id"], r["player_id"], r["category"]) for r in panel}) == len(panel)
    for selected, expected in zip(panel, admitted):
        assert {k:selected[k] for k in expected} == expected
    projection = [{k:(r["lean"] if k == "saved_side" else r[k]) for k in ("source_row_index", "season", "week", "game_id", "player_id", "category", "position", "kickoff", "saved_side", "line", "line_from", "top_over", "top_under")} for r in panel]
    assert hashlib.sha256(canon(projection)).hexdigest() == panel_receipt["eligible_key_projection_sha256"]
    side_counts = dict(collections.Counter(r["lean"] for r in panel))
    target_counts = dict(collections.Counter(r["category"] for r in panel))
    provenance_counts = dict(collections.Counter(r["line_from"] for r in panel))
    assert side_counts == panel_receipt["side_counts"] and target_counts == panel_receipt["target_counts"] and provenance_counts == panel_receipt["line_provenance_counts"]
    for name in ("over", "under"):
        assert sum(bool(r["top_"+name]) for r in panel) == panel_receipt["original_top_flag_counts_within_panel"][name]
    sources = {"original_forward": args.original_forward, "retained_reference": args.reference,
               "identity_bridge": args.source_root / "roster-week8-identity-2026.csv.gz", "schedule": args.source_root / "games.csv",
               "panel": args.metadata_root / "FROZEN_SIDE_LINE_PANEL.json.gz"}
    for name, path in sources.items():assert sha(path) == protocol["sources"][name]
    forward, reverse = collections.defaultdict(set), collections.defaultdict(set)
    with gzip.open(sources["identity_bridge"], "rt") as stream:
        for r in csv.DictReader(stream):
            if r["season"] == "2026" and int(r["week"]) <= 7 and r["sleeper_id"] and r["gsis_id"]:
                forward[r["sleeper_id"]].add(r["gsis_id"])
                reverse[r["gsis_id"]].add(r["sleeper_id"])
    bridge = {sid:next(iter(ids)) for sid, ids in forward.items() if len(ids) == 1 and re.fullmatch(r"00-\d{7}", next(iter(ids))) and len(reverse[next(iter(ids))]) == 1}
    games = {}
    with sources["schedule"].open() as stream:
        for r in csv.DictReader(stream):
            if (r["season"], r["game_type"], r["week"]) == ("2026", "REG", "7"):
                assert r["espn"] not in games
                games[r["espn"]] = {k:r[k] for k in ("game_id", "gameday", "gametime")}
    wanted = {}
    for row in panel:
        game = games[str(row["game_id"])]
        assert datetime.fromisoformat(game["gameday"]+"T"+game["gametime"]).replace(tzinfo=ZoneInfo("America/New_York")).timestamp() == clock(row["kickoff"]).timestamp()
        key = (game["game_id"], bridge[str(row["player_id"])], row["category"])
        assert key not in wanted
        wanted[key] = row
    references = collections.defaultdict(list)
    decoded_reference_rows = scanned_reference_rows = 0
    for i, raw in enumerate(raw_rows(gzip.decompress(args.reference.read_bytes()).decode())):
        scanned_reference_rows += 1
        key = tuple(identity_scalar(raw, k) for k in ("game_id", "player_id", "target"))
        if key not in wanted:continue
        r = json.loads(raw, parse_float=Decimal)
        assert (r["game_id"], r["player_id"], r["target"]) == key
        assert r["game_id"].startswith("2026_07_")
        if "season" in r:assert r["season"] == 2026
        if "week" in r:assert r["week"] == 7
        references[key].append((i, r))
        decoded_reference_rows += 1
    selected_source = {r["source_row_index"] for r in panel}
    original_rows = {i:json.loads(raw, parse_float=Decimal) for i, raw in enumerate(raw_rows(gzip.decompress(args.original_forward.read_bytes()).decode())) if i in selected_source}
    output_binding = receipt["private_output"]
    joined_path = args.join_root / output_binding["logical_member"]
    assert sha(joined_path) == output_binding["sha256"] and joined_path.stat().st_size == output_binding["bytes"]
    joined = json.loads(gzip.decompress(joined_path.read_bytes()), parse_float=Decimal)
    assert joined["protocol_sha256"] == receipt["protocol_sha256"]
    assert len(joined["rows"]) == 285
    statuses = collections.Counter()
    scalar_checks = 0
    for output, outer in zip(joined["rows"], panel):
        source = original_rows[outer["source_row_index"]]
        key = (games[str(outer["game_id"])]["game_id"], bridge[str(outer["player_id"])], outer["category"])
        rr = references[key]
        assert {r.get("position") for _, r in rr} == {outer["position"]}
        populations = {r["population"] for _, r in rr}
        assert len(populations) == 1
        actuals = {r["actual"] for _, r in rr if r["actual"] is not None}
        assert len(actuals) <= 1
        state = "SUPPORTED" if any(r["status"] == "SUPPORTED" and r["actual"] is not None for _, r in rr) else rr[0][1]["status"]
        y = next(iter(actuals)) if state == "SUPPORTED" else None
        if y is not None:
            assert not isinstance(y, bool) and Decimal(y).is_finite() and Decimal(y) == Decimal(y).to_integral_value()
            if outer["category"] in {"pass_td", "pass_cmp", "pass_att", "pass_int", "rush_att", "rec"}:assert y >= 0
        point = source["adjusted_projection"]
        assert {r["prediction"] for _, r in rr if r["product_id"] == "website_point"} == {point}
        expected = dict(source_row_index=outer["source_row_index"], game_id=key[0], player_id=key[1], target=key[2], position=outer["position"], population=next(iter(populations)),
                        actual=y, prediction=point, point_state="EXACT_ORIGINAL_AND_RETAINED_PARITY", label_state=state,
                        participation="VERIFIED_PLAYED_POSITIVE_PHYSICAL" if state == "SUPPORTED" else "UNKNOWN", side=outer["lean"], line=Decimal(str(outer["line"])),
                        line_from=outer["line_from"], top_over=outer["top_over"], top_under=outer["top_under"], kickoff=outer["kickoff"],
                        retained_source_row_indices=[i for i, _ in rr], retained_source_product_views=sorted({r["product_id"] for _, r in rr}), price=None, probability=None)
        for k, value in expected.items():assert output[k] == value, (outer["source_row_index"], k)
        scalar_checks += len(expected)
        statuses[state] += 1
    assert dict(statuses) == receipt["label_state_counts"] == {"SUPPORTED":279, "APPEARANCE_UNKNOWN":6}
    assert scanned_reference_rows == 4248 and decoded_reference_rows == 570
    report = dict(state="PASS_INDEPENDENT_METADATA_ELIGIBILITY_AND_PANEL_ONLY_JOIN", panel_protocol_sha256=panel_receipt["protocol_sha256"], join_protocol_sha256=receipt["protocol_sha256"],
                  input_metadata_rows=2289, admitted_rows=285, metadata_projection_sha256=panel_receipt["eligible_key_projection_sha256"],
                  eligibility_reason_counts=dict(eligibility), side_counts=side_counts, target_counts=target_counts, line_provenance_counts=provenance_counts,
                  joined_packet_sha256=output_binding["sha256"], joined_scalar_or_list_fields_independently_checked=scalar_checks,
                  label_states=dict(statuses), source_reference_records_scanned_lexically=scanned_reference_rows,
                  only_panel_matched_reference_views_numerically_decoded=decoded_reference_rows, unique_player_games=receipt["player_games"], games=13,
                  source_truth_limit="Labels reuse previously qualified source rows and their existing complete-zero/positive-physical contract. This checks source identity/value/participation joins, not a new independent NFL official-stat publication or historical quote availability.",
                  point_limit="Exact saved adjusted_projection parity is established; unrounded internal model precision is not recovered by this join.",
                  new_fits=0, inference_calls=0, new_forecasts=0, new_NFL_observations=0, current2026_week8_outcomes_read=0,
                  wall_seconds=time.monotonic()-started, peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    path = HERE / "FROZEN_PANEL_JOIN_INDEPENDENT_REVIEW.json"
    if path.exists():raise ValueError("Preserve original review; use an explicit new version")
    path.write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k:report[k] for k in ("state", "admitted_rows", "label_states", "joined_scalar_or_list_fields_independently_checked", "wall_seconds", "peak_rss_bytes")}))


if __name__ == "__main__":main()
