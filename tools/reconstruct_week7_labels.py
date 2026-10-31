#!/usr/bin/env python3
"""Reconstruct explicit later Week7 labels from supplied private, pinned bytes.

No network, fitting or scoring. The public report has aggregates only. The
private output retains all original opportunity keys and explicit null reasons.
This is same-provider later-snapshot reconstruction, not old issuance recovery.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path

VERSION = "v2-week7-later-explicit-labels-v1"
PRIMITIVES = {"pass_yd", "pass_td", "pass_cmp", "pass_att", "pass_int", "rush_yd", "rush_att", "rec", "rec_yd"}
COUNTS = {"pass_td", "pass_cmp", "pass_att", "pass_int", "rush_att", "rec"}
TARGETS = PRIMITIVES | {"rush_rec_yd", "anytime_td"}
MAX_COMPRESSED_BYTES = 64 * 1024 * 1024
MAX_DECODED_BYTES = 96 * 1024 * 1024
MAX_FORECAST_ROWS = 100000


def sha(body):
    return hashlib.sha256(body).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def load(path):
    size = path.stat().st_size
    if size > MAX_COMPRESSED_BYTES:
        raise ValueError("input exceeds registered byte bound")
    original = path.read_bytes()
    if original[:2] == b"\x1f\x8b":
        with gzip.GzipFile(fileobj=io.BytesIO(original)) as stream:
            body = stream.read(MAX_DECODED_BYTES + 1)
    else:
        body = original
    if len(body) > MAX_DECODED_BYTES:
        raise ValueError("decoded input exceeds registered byte bound")
    return json.loads(body, object_pairs_hook=unique_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON"))), sha(original)


def clock(value):
    if not isinstance(value, str) or not value:
        raise ValueError("explicit clock required")
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("timezone required")
    return t.astimezone(timezone.utc)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def count(value):
    return number(value) and value >= 0 and value == int(value)


def explicit_value(target, stats):
    """Only supported finite explicit fields; never infer zero from omission."""
    if target in PRIMITIVES:
        if target not in stats:
            return None, "omitted_primitive_not_zero"
        value = stats[target]
        if not number(value) or (target in COUNTS and not count(value)):
            return None, "invalid_primitive_support"
        return value, "explicit_primitive"
    if target == "rush_rec_yd":
        if not all(k in stats for k in ("rush_yd", "rec_yd")):
            return None, "incomplete_sum_components_not_zero"
        if not all(number(stats[k]) for k in ("rush_yd", "rec_yd")):
            return None, "invalid_sum_components"
        return stats["rush_yd"] + stats["rec_yd"], "explicit_signed_component_sum"
    if target == "anytime_td":
        present = [stats[k] for k in ("rush_td", "rec_td") if k in stats]
        if any(not count(v) for v in present):
            return None, "invalid_TD_component_support"
        if any(v > 0 for v in present):
            return 1, "positive_rushing_or_receiving_TD_proof"
        if len(present) == 2 and present == [0, 0]:
            return 0, "explicit_both_TD_zero"
        return None, "incomplete_event_components_not_zero"
    raise ValueError("unsupported target")


def reconstruct(forecasts, stats, schedule, *, observed_at, run_id, source_commit,
                forecast_sha, stats_sha, schedule_sha):
    clock(observed_at)
    if not run_id or len(source_commit) != 40 or any(c not in "0123456789abcdef" for c in source_commit):
        raise ValueError("new run ID and pinned source commit required")
    rows = forecasts["rows"]
    if not rows or len(rows) > MAX_FORECAST_ROWS:
        raise ValueError("forecast row bound/empty")
    if schedule.get("season") != 2026 or schedule.get("week") != 7:
        raise ValueError("wrong schedule panel")
    games = {}
    team_games = collections.Counter()
    for game in schedule["games"]:
        gid = str(game["id"])
        if gid in games:
            raise ValueError("ambiguous schedule identity")
        games[gid] = game
        team_games.update((game["home"], game["away"]))
    if any(n != 1 for n in team_games.values()):
        raise ValueError("multiple weekly games per team; identity not reconstructable")
    contexts = {}
    conflict = set()
    forecast_keys = collections.Counter()
    # No forecasts are changed; repeated model views share one outcome record.
    for row in rows:
        if (row.get("season") != 2026 or row.get("week") != 7
                or row.get("period") != "full_game" or row.get("target") not in TARGETS):
            raise ValueError("forecast outside exact Week7/category/full-game contract")
        key = (row["player_id"], row["game_id"], row["target"])
        forecast_keys[key] += 1
        context = {k: row.get(k) for k in ("player_id", "sleeper_id", "game_id", "target", "team", "opponent", "position", "kickoff_utc", "scoring_id")}
        if key in contexts and contexts[key] != context:
            conflict.add(key)
        contexts.setdefault(key, context)
    labels, reasons, target_counts, game_counts = [], collections.Counter(), {}, {}
    played_players, supported_players, supported_games = set(), set(), set()
    for key, context in sorted(contexts.items()):
        pid, prefixed_gid, target = key
        record = dict(player_id=pid, game_id=prefixed_gid, target=target, actual=None,
                      participation_state="unknown", source="later_production_normalized_sleeper_week7",
                      source_sha256=stats_sha, status_sha256=schedule_sha, source_timestamp=None,
                      observed_at=observed_at, finality="later ESPN completed flag; statistical revision time unknown",
                      reconstruction_run_id=run_id, source_commit=source_commit,
                      source_tier="current_vintage_later_label_reconstruction",
                      scoring_id=context["scoring_id"])
        reason = None
        if key in conflict:
            reason = "conflicting_original_forecast_context"
        elif not isinstance(pid, str) or not pid.startswith("sleeper:") or not pid[8:]:
            reason = "unverified_identity_namespace"
        elif context["sleeper_id"] != pid[8:]:
            reason = "forecast_sleeper_identity_conflict"
        elif not isinstance(prefixed_gid, str) or not prefixed_gid.startswith("espn:"):
            reason = "unverified_game_namespace"
        else:
            game = games.get(prefixed_gid[5:])
            source = stats.get(pid[8:])
            if game is None:
                reason = "game_not_in_week7_schedule"
            elif game.get("state") != "post" or game.get("completed") is not True:
                reason = "game_not_confirmed_completed"
            elif clock(context["kickoff_utc"]) != clock(game["kickoff"]):
                reason = "forecast_schedule_kickoff_mismatch"
            elif (context["team"], context["opponent"]) not in (
                    (game["home"], game["away"]), (game["away"], game["home"])):
                reason = "forecast_schedule_team_mismatch"
            elif source is None:
                reason = "player_not_in_normalized_snapshot"
            elif (source.get("team"), source.get("opp")) != (context["team"], context["opponent"]):
                reason = "source_forecast_team_opponent_mismatch"
            else:
                production = source.get("stats", {})
                if not any(count(production.get(k)) and production[k] > 0 for k in ("gp", "off_snp")):
                    reason = "participation_not_established"
                else:
                    record["participation_state"] = "played"
                    played_players.add((pid, prefixed_gid))
                    value, reason = explicit_value(target, production)
                    record["actual"] = value
                    if value is not None:
                        supported_players.add((pid, prefixed_gid))
                        supported_games.add(prefixed_gid)
        record["label_reason"] = reason
        reasons[reason] += 1
        target_counts.setdefault(target, collections.Counter())["supported" if record["actual"] is not None else "null"] += 1
        game_counts.setdefault(prefixed_gid, collections.Counter())["supported" if record["actual"] is not None else "null"] += 1
        labels.append(record)
    n_supported = sum(r["actual"] is not None for r in labels)
    scored_compatible_forecast_rows = sum(forecast_keys[(r["player_id"], r["game_id"], r["target"])]
                                         for r in labels if r["actual"] is not None)
    summary = dict(version=VERSION, run_id=run_id, evidence_label="NEW_EXPERIMENT_LABEL_RECONSTRUCTION_ONLY",
                   original_forecast_rows=len(rows), original_unique_opportunities=len(contexts),
                   original_unique_player_games=len({(p, g) for p, g, _ in contexts}),
                   original_unique_games=len({g for _, g, _ in contexts}),
                   supported_label_rows=n_supported, null_label_rows=len(labels)-n_supported,
                   supported_unique_player_games=len(supported_players), positive_participation_player_games=len(played_players),
                   supported_games=len(supported_games), forecast_rows_with_supported_later_label=scored_compatible_forecast_rows,
                   forecast_rows_unresolved=len(rows)-scored_compatible_forecast_rows,
                   reasons=dict(reasons), by_target={k: dict(v) for k, v in sorted(target_counts.items())},
                   by_game={k: dict(v) for k, v in sorted(game_counts.items())},
                   source_repository="NickNicky19/nicks-expert-nfl-picks", source_commit=source_commit,
                   source_paths={"statistics":"data/cache/stat-keys-fgm-v1/stats_2026_07.json", "schedule":"output/data/weeks/2026_w07.json"},
                   input_sha256={"forecast_gzip_bytes":forecast_sha, "normalized_statistics_bytes":stats_sha, "schedule_bytes":schedule_sha},
                   observed_at=observed_at, provider_revision_timestamp=None,
                   mapping={"primitive":"exact explicit field, finite; counts nonnegative integers; signed yards retained",
                            "rush_rec_yd":"sum only two finite explicit signed primitives",
                            "anytime_td":"positive valid rush_td or rec_td proves1; zero needs both explicit0",
                            "identity":"exact sleeper prefix/key and existing sleeper_id agree; team/opponent and kickoff match completed ESPN schedule",
                            "participation":"positive valid gp/off_snp only; missing snapshot never DNP"},
                   actual_fits=0, new_forecasts=0, accuracy_scores=0,
                   limitations=["Later same-provider website-normalized values, not independent NFL truth or original outcome capture recovery.",
                                "trim_stats drops zero/falsey fields; omissions remain null, never assumed zero.",
                                "Explicit-value-only grading selects positive production; it cannot establish full-population skill or the original history question.",
                                "All original query keys and unverified identities remain in private output with null reasons.",
                                "Current source bytes and ESPN final flag do not authenticate provider revision times or complete official labels.",
                                "No alias guessing, chart-PPR substitution, fitting, forecast issuance or scoring."])
    return labels, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("forecasts", "stats", "schedule", "output", "report"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--observed-at", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    if args.output.exists() or args.report.exists():
        raise ValueError("immutable run output already exists; use a new run identity")
    forecasts, fsha = load(args.forecasts)
    stats, ssha = load(args.stats)
    schedule, csha = load(args.schedule)
    labels, summary = reconstruct(forecasts, stats, schedule, observed_at=args.observed_at,
                                  run_id=args.run_id, source_commit=args.source_commit,
                                  forecast_sha=fsha, stats_sha=ssha, schedule_sha=csha)
    body = json.dumps(labels, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    summary["private_label_body_sha256"] = sha(body)
    summary["private_label_bytes"] = len(body)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(body)
    args.report.write_text(json.dumps(summary, sort_keys=True, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: summary[k] for k in ("run_id", "supported_label_rows", "null_label_rows", "supported_games", "accuracy_scores")}))


if __name__ == "__main__":
    main()
