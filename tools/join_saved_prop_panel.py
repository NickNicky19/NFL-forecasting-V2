#!/usr/bin/env python3
"""Join only a frozen saved-side panel to retained qualified Week 7 rows."""
import argparse
import collections
import csv
import gzip
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nfl_v2.identity import unique_gsis_bridge
from nfl_v2.prop_evidence_metadata_v2 import object_spans_in_array, project_metadata


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def string_field(raw, name):
    match = re.search(r'"' + re.escape(name) + r'"\s*:\s*("(?:[^"\\]|\\.)*")', raw)
    return json.loads(match.group(1)) if match else None


def now():
    return datetime.now(timezone.utc).isoformat()


def main(args):
    public = args.public_root
    private = args.private_root
    public.mkdir(exist_ok=False, parents=True)
    private.mkdir(exist_ok=False, parents=True)
    panel_receipt = json.loads(args.panel_receipt.read_text())
    parent_receipt = json.loads(args.reference_receipt.read_text())
    panel_binding = next(x for x in panel_receipt["private_artifacts"]
                         if x["artifact_id"] == "V2-PROP-W7-FROZEN-SIDE-LINE-PANEL-V1")
    expected = {
        "panel": (args.panel, panel_binding["sha256"]),
        "original_forward": (args.original_forward, panel_receipt["source_gzip_sha256"]),
        "retained_reference": (args.retained_reference, parent_receipt["private_rows_sha256"]),
        "identity_bridge": (args.source_root / "roster-week8-identity-2026.csv.gz",
                            parent_receipt["identity_bridge_sha256"]),
        "schedule": (args.source_root / "games.csv",
                     next(x["sha256"] for x in parent_receipt["source_labels"]
                          if x["name"] == "games.csv")),
    }
    for _, (path, digest) in expected.items():
        if sha(path) != digest:
            raise ValueError("retained source hash changed")
    protocol = dict(
        version="v2-frozen-original-W7-side-line-panel-label-join-v1",
        registered_at_utc=now(), code_sha256=sha(__file__),
        metadata_parser_sha256=sha(ROOT / "nfl_v2/prop_evidence_metadata_v2.py"),
        identity_helper_sha256=sha(ROOT / "nfl_v2/identity.py"),
        panel_receipt_sha256=sha(args.panel_receipt),
        reference_receipt_sha256=sha(args.reference_receipt),
        sources={k: v[1] for k, v in expected.items()},
        source_row_limit=2289, frozen_panel_rows=285,
        label_admission="Only metadata-matched canonical game/player/target rows from the retained qualified reference rows array; filter before JSON decoding prediction/actual scalars. No candidate array or Week 8 label decoded.",
        identity="Frozen season2026/week<=7 exact one-to-one Sleeper-GSIS bridge, cached REG2026W7 schedule ESPN mapping, exact kickoff and original position; ambiguous/missing remain unresolved.",
        label_contract="Previously independently checked complete-source explicit target credits, signed yards, positive physical appearance, null unknowns. No new absent-field zero or DNP inference.",
        duplicate_rule="Check all retained product/population views for identical canonical identity and nonmissing actual; conflicting actual/position/population unresolved. Collapse repeated views, never count them as NFL observations.",
        point_contract="Same original source row adjusted_projection; verify against retained website_point prediction. Missing/nonfinite/conflicting point remains null without changing frozen direction-panel membership.",
        outputs="All285 outer rows, qualification states and provenance; no crossing/hit/return computation.",
        budget=dict(wall_seconds=30, max_RSS_bytes=1073741824,
                    max_private_output_bytes=262144, max_threads=1),
        new_fits=0, new_forecasts=0, CURRENT_2026_Week8_outcomes_read=0)
    protocol_bytes = canonical(protocol)
    (public / "FROZEN_JOIN_PROTOCOL.json").write_bytes(protocol_bytes)
    protocol_hash = hashlib.sha256(protocol_bytes).hexdigest()
    panel = json.loads(gzip.decompress(args.panel.read_bytes()))["rows"]
    if len(panel) != 285:
        raise ValueError("frozen membership count changed")
    with gzip.open(expected["identity_bridge"][0], "rt") as handle:
        bridge = unique_gsis_bridge(
            [(r["sleeper_id"], r["gsis_id"]) for r in csv.DictReader(handle)
             if r["season"] == "2026" and int(r["week"]) <= 7
             and r["sleeper_id"] and r["gsis_id"]],
            source_id="FROZEN_WEEK_LE7_EXACT_ID_ONLY")
    games = {}
    with expected["schedule"][0].open() as handle:
        for r in csv.DictReader(handle):
            if (r["season"], r["game_type"], r["week"]) != ("2026", "REG", "7"):
                continue
            if r["espn"] in games:
                raise ValueError("ambiguous schedule ESPN identity")
            games[r["espn"]] = {k: r[k] for k in ("game_id", "gameday", "gametime")}
    wanted = {}
    kickoff_conflicts = set()
    for r in panel:
        game = games.get(str(r["game_id"]))
        gsis = bridge.get(str(r["player_id"]))
        if game:
            expected_kickoff = datetime.fromisoformat(game["gameday"]+"T"+game["gametime"]).replace(tzinfo=ZoneInfo("America/New_York")).timestamp()
            if expected_kickoff != datetime.fromisoformat(r["kickoff"].replace("Z","+00:00")).timestamp():
                kickoff_conflicts.add(r["source_row_index"])
        canonical_key = (game["game_id"], gsis, r["category"]) if game and gsis else None
        if canonical_key and r["source_row_index"] not in kickoff_conflicts:
            if canonical_key in wanted:
                raise ValueError("ambiguous frozen outer key")
            wanted[canonical_key] = r
    # Decompression and lexical object-span traversal do not decode target scalars.
    reference_text = gzip.decompress(args.retained_reference.read_bytes()).decode()
    retained = collections.defaultdict(list)
    seen_reference_records = matched_numeric_records = 0
    for index, raw in enumerate(object_spans_in_array(reference_text, "rows")):
        seen_reference_records += 1
        metadata, _ = project_metadata(raw)
        key = (metadata.get("game_id"), metadata.get("player_id"),
               string_field(raw, "target"))
        if key not in wanted:
            continue
        record = json.loads(raw)  # Only the frozen panel's qualified key is decoded.
        retained[key].append((index, record))
        matched_numeric_records += 1
    source_rows = {}
    selected_indices = {r["source_row_index"] for r in panel}
    forward_text = gzip.decompress(args.original_forward.read_bytes()).decode()
    for index, raw in enumerate(object_spans_in_array(forward_text, "rows")):
        if index in selected_indices:
            source_rows[index] = json.loads(raw)
    results = []
    statuses = collections.Counter()
    for outer in panel:
        game = games.get(str(outer["game_id"]))
        gsis = bridge.get(str(outer["player_id"]))
        key = (game["game_id"], gsis, outer["category"]) if game and gsis else None
        candidates = retained.get(key, [])
        raw_source = source_rows[outer["source_row_index"]]
        for name in ("game_id", "player_id", "category", "position", "line", "lean"):
            if raw_source.get(name) != outer.get(name):
                raise ValueError("original source row differs from frozen metadata")
        state = "IDENTITY_UNRESOLVED" if not gsis else "GAME_UNRESOLVED" if not game else "GAME_KICKOFF_CONFLICT" if outer["source_row_index"] in kickoff_conflicts else None
        if game:
            # The schedule times are Eastern local; source kickoff is independently
            # matched by the retained qualified record and parent source protocol.
            if not str(game["game_id"]).startswith("2026_07_"):
                raise ValueError("out-of-panel game")
        populations = {r.get("population") for _, r in candidates}
        positions = {r.get("position") for _, r in candidates}
        actuals = {r["actual"] for _, r in candidates if r.get("actual") is not None}
        supported = [r for _, r in candidates if r.get("status") == "SUPPORTED"
                     and r.get("actual") is not None]
        if state is None:
            state = ("RETAINED_LABEL_UNRESOLVED" if not candidates else
                     "CONFLICTING_RETAINED_VIEWS" if len(populations) > 1 or
                     positions != {outer["position"]} or len(actuals) > 1 else
                     "SUPPORTED" if supported else
                     candidates[0][1].get("status", "RETAINED_LABEL_UNRESOLVED"))
        actual = next(iter(actuals)) if state == "SUPPORTED" else None
        if actual is not None and (not isinstance(actual, (int, float)) or
                                   not math.isfinite(actual) or not float(actual).is_integer()):
            state, actual = "INVALID_NONINTEGER_RETAINED_STAT", None
        if actual is not None:
            actual = int(actual)
        original_point = raw_source.get("adjusted_projection")
        point = original_point if isinstance(original_point, (int, float)) and math.isfinite(original_point) else None
        website_points = {r["prediction"] for _, r in candidates
                          if r.get("product_id") == "website_point" and r.get("prediction") is not None}
        point_state = "EXACT_ORIGINAL_AND_RETAINED_PARITY" if point is not None and website_points == {point} else "POINT_MISSING_OR_CONFLICTING"
        if point_state != "EXACT_ORIGINAL_AND_RETAINED_PARITY":
            point = None
        participation = ("VERIFIED_PLAYED_POSITIVE_PHYSICAL" if state == "SUPPORTED" else
                         "VERIFIED_PLAYED_TARGET_MISSING" if state == "MISSING_ACTUAL" else "UNKNOWN")
        result = dict(source_row_index=outer["source_row_index"],
                      source_gzip_sha256=protocol["sources"]["original_forward"],
                      source_player_id=outer["player_id"], source_game_id=outer["game_id"],
                      game_id=game["game_id"] if game else None, player_id=gsis,
                      target=outer["category"], position=outer["position"],
                      population=next(iter(populations)) if len(populations) == 1 else None,
                      season=2026, week=7, kickoff=outer["kickoff"],
                      side=outer["lean"], line=outer["line"], line_from=outer.get("line_from"),
                      top_over=outer.get("top_over"), top_under=outer.get("top_under"),
                      actual=actual, prediction=point, point_state=point_state,
                      label_state=state, participation=participation,
                      retained_source_row_indices=[i for i, _ in candidates],
                      retained_source_product_views=sorted({r.get("product_id") for _, r in candidates}),
                      label_source_contract="QUALIFIED_EXPLICIT_OFFICIAL_CREDITS_WITH_POSITIVE_PHYSICAL_APPEARANCE_CURRENT_VINTAGE_W7",
                      recorded_capture="2026-10-22T17:55:30Z",
                      server_retained_by="2026-10-23T17:49:53Z",
                      price=None, probability=None)
        results.append(result)
        statuses[state] += 1
    body = gzip.compress(canonical(dict(protocol_sha256=protocol_hash, rows=results)), mtime=0)
    if len(body) > protocol["budget"]["max_private_output_bytes"]:
        raise ValueError("private output exceeds frozen cap")
    output = private / "FROZEN_PANEL_JOINED.json.gz"
    output.write_bytes(body)
    receipt = dict(state="COMPLETE_PANEL_ONLY_JOIN_NO_DIRECTION_GRADING", actual_completed_at=now(),
                   protocol_sha256=protocol_hash, source_bindings=protocol["sources"],
                   outer_rows=len(results), missing_outer_rows=285-len(results),
                   label_state_counts=dict(statuses),
                   point_parity_counts=dict(collections.Counter(r["point_state"] for r in results)),
                   participation_counts=dict(collections.Counter(r["participation"] for r in results)),
                   eligible_games=len({r["game_id"] for r in results if r["game_id"]}),
                   player_games=len({(r["game_id"], r["player_id"]) for r in results if r["player_id"]}),
                   source_row_objects_lexically_scanned=seen_reference_records,
                   metadata_matched_reference_views_decoded=matched_numeric_records,
                   repeated_views_are_not_new_NFL_observations=True,
                   private_output=dict(artifact_id="V2-PROP-W7-PANEL-JOIN-V1",
                                       logical_member=output.name, bytes=len(body), sha256=sha(output)),
                   actual_dtype="Exact integer official statistic or null; signed yardage retained",
                   source_recoverability="Original public Git blob and qualified-source hashes; raw records remain private; no new offhost restoration claimed",
                   new_fits=0, new_forecasts=0, direction_scores_computed=0,
                   CURRENT_2026_Week8_outcomes_read=0)
    (public / "JOIN_COVERAGE_RECEIPT.json").write_bytes(canonical(receipt))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("public-root", "private-root", "panel", "panel-receipt", "reference-receipt",
                 "original-forward", "retained-reference", "source-root"):
        p.add_argument("--"+name, required=True, type=Path)
    main(p.parse_args())
