#!/usr/bin/env python3
"""Map existing cohort tags to frozen prop keys without decoding any labels."""
import argparse
import collections
import gzip
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nfl_v2.prop_evidence_metadata_v2 import object_spans_in_array, project_metadata


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def field(raw, key):
    match = re.search(r'"' + re.escape(key) + r'"\s*:\s*("(?:[^"\\]|\\.)*")', raw)
    return json.loads(match.group(1)) if match else None


def main(args):
    args.public_root.mkdir(parents=True, exist_ok=False)
    args.private_root.mkdir(parents=True, exist_ok=False)
    member_receipt = json.loads(args.membership_receipt.read_text())
    join_receipt = json.loads(args.join_receipt.read_text())
    if sha(args.memberships) != member_receipt["membership_sha256"]:
        raise ValueError("existing frozen membership hash changed")
    if sha(args.joined_panel) != join_receipt["private_output"]["sha256"]:
        raise ValueError("frozen joined panel hash changed")
    proof = datetime.fromisoformat("2026-10-23T17:49:53+00:00").timestamp()
    protocol = dict(
        version="v2-recorded-side-panel-existing-cohort-map-v1",
        registered_at_utc=datetime.now(timezone.utc).isoformat(),
        code_sha256=sha(__file__),
        parser_sha256=sha(ROOT / "nfl_v2/prop_evidence_metadata_v2.py"),
        membership_sha256=sha(args.memberships),
        membership_receipt_sha256=sha(args.membership_receipt),
        parent_membership_protocol_sha256=sha(args.membership_protocol),
        joined_panel_sha256=sha(args.joined_panel),
        join_receipt_sha256=sha(args.join_receipt),
        exact_key=["game_id", "player_id", "target", "population"],
        qualification="Only existing 2026W7 memberships; finite ranking_cutoff at or before server-retained-byte clock, with latest_available strictly earlier than ranking_cutoff. Preserve all source ranks and bands; never rerank the13-game subset.",
        evidence_tier="Retrospective pregame-defined prior-workload diagnostic. Actual existing membership freeze occurred October30, not before original October22 forecast. Not an authenticated original star list or betting selection policy.",
        selector="Existing last3 earlier-available compatible attempts/carries/targets/carries+targets, seven-day availability assumption, fixed role populations and current-vintage source. Unknowns remain unknown.",
        outer_rows=285, source_server_retention_clock="2026-10-23T17:49:53Z",
        no_label_policy="Lexically scan joined rows, decode only allowed metadata fields and exact target/population/source index strings. No actual, prediction, result or price scalar decoded.",
        missing="Keep every outer row with membership_unknown; absent cohort is distinct from a present unranked/workload_unknown source record.",
        new_rankings=0, new_fits=0, new_forecasts=0, new_target_label_reads=0,
        CURRENT_2026_Week8_outcomes_read=0)
    body = canonical(protocol)
    (args.public_root / "FROZEN_COHORT_MAP_PROTOCOL.json").write_bytes(body)
    protocol_hash = hashlib.sha256(body).hexdigest()
    # This saved artifact contains only precomputed membership metadata, not labels.
    members = json.loads(gzip.decompress(args.memberships.read_bytes()))
    source = {}
    w7_count = 0
    for row in members:
        key = tuple(row["key"])
        if not str(key[0]).startswith("2026_07_"):
            continue
        w7_count += 1
        if key in source:
            raise ValueError("conflicting existing membership keys")
        source[key] = row
    rows = []
    counters = collections.Counter()
    group_counts = collections.Counter()
    cutoffs = set()
    available = []
    joined_text = gzip.decompress(args.joined_panel.read_bytes()).decode()
    for raw in object_spans_in_array(joined_text, "rows"):
        metadata, _ = project_metadata(raw)
        target, population = field(raw, "target"), field(raw, "population")
        index_match = re.search(r'"source_row_index"\s*:\s*(\d+)', raw)
        if not index_match:
            raise ValueError("source row index absent")
        index = int(index_match.group(1))
        key = (metadata.get("game_id"), metadata.get("player_id"), target, population)
        member = source.get(key)
        state = "UNMATCHED_SOURCE_COHORT"
        groups, rank, cutoff, latest = [], None, None, None
        if member is not None:
            cutoff, latest = member.get("ranking_cutoff"), member.get("latest_available")
            qualified = isinstance(cutoff, (int, float)) and cutoff <= proof
            qualified = qualified and (latest is None or latest < cutoff)
            state = "MATCHED_PRIOR_CLOCK_RECONSTRUCTED" if qualified else "REJECTED_COHORT_CLOCK"
            if qualified:
                groups, rank = list(member["cohorts"]), member.get("rank")
                cutoffs.add(cutoff)
                if latest is not None:
                    available.append(latest)
        projected = [g for g in groups if g != "all"] if state == "MATCHED_PRIOR_CLOCK_RECONSTRUCTED" else ["membership_unknown"]
        row = dict(source_row_index=index, game_id=key[0], player_id=key[1], target=target,
                   population=population, position=metadata.get("position"),
                   membership_state=state, source_cohorts=groups,
                   cohort_groups=projected,
                   role_groups=["position_"+str(metadata.get("position")),
                                "population_"+str(population)],
                   original_rank=rank, ranking_cutoff=cutoff, latest_available=latest)
        rows.append(row)
        counters[state] += 1
        group_counts.update(projected)
    if len(rows) != 285 or len({r["source_row_index"] for r in rows}) != 285:
        raise ValueError("outer membership loss or duplication")
    output = args.private_root / "FROZEN_SIDE_COHORT_TAGS.json.gz"
    output.write_bytes(gzip.compress(canonical(dict(protocol_sha256=protocol_hash, rows=rows)), mtime=0))
    receipt = dict(
        state="COMPLETE_EXISTING_COHORT_METADATA_MAP", actual_completed_at=datetime.now(timezone.utc).isoformat(),
        protocol_sha256=protocol_hash, source_membership_sha256=sha(args.memberships),
        source_W7_memberships=w7_count, outer_rows=285, mapping_state_counts=dict(counters),
        subgroup_counts=dict(group_counts), all_outer_rows_preserved=True,
        ranking_cutoffs_utc=[datetime.fromtimestamp(x, timezone.utc).isoformat() for x in sorted(cutoffs)],
        latest_assumed_available_utc=datetime.fromtimestamp(max(available), timezone.utc).isoformat() if available else None,
        original_membership_freeze="2026-10-30T00:41:33.537406+00:00",
        actual_freeze_preceded_original_forecast=False,
        recorded_original_forecast_capture="2026-10-22T17:55:30Z",
        selector_cutoff_after_recorded_original_capture=True,
        use_tier="Retrospective prior-workload diagnostic before server-retention bound; not original archived pregame ranks.",
        role_group_counts=dict(collections.Counter(g for r in rows for g in r["role_groups"])),
        target_state_counts=[dict(target=t, membership_state=s, n=n)
                             for (t, s), n in sorted(collections.Counter((r["target"], r["membership_state"]) for r in rows).items())],
        private_output=dict(artifact_id="V2-PROP-W7-EXISTING-COHORT-TAGS-V1", logical_member=output.name,
                            bytes=output.stat().st_size, sha256=sha(output)),
        no_rerank_of_restricted_13game_panel=True, new_rankings=0,
        target_label_values_decoded=0, new_fits=0, new_forecasts=0,
        CURRENT_2026_Week8_outcomes_read=0)
    (args.public_root / "COHORT_MAP_COVERAGE.json").write_bytes(canonical(receipt))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("public-root", "private-root", "memberships", "membership-receipt", "membership-protocol", "joined-panel", "join-receipt"):
        parser.add_argument("--"+name, type=Path, required=True)
    main(parser.parse_args())
