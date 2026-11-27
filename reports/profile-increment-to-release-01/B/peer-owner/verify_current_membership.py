"""Read-only arithmetic/membership witness, independent of the website ranker."""
import argparse
import collections
import hashlib
import json
import math
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    raw_base = "https://raw.githubusercontent.com/NickNicky19/nicks-expert-nfl-picks/" + args.ref + "/"
    served_base = "https://nicknicky19.github.io/nicks-expert-nfl-picks/"
    sources, checks, failures = [], collections.Counter(), []

    def check(name, condition):
        checks[name] += 1
        if not condition:
            failures.append(name)

    def fetch(path, served=False):
        url = served_base + path.removeprefix("output/") if served else raw_base + path
        with urllib.request.urlopen(url, timeout=45) as response:
            raw = response.read()
        member = ("served/" if served else "git/") + path
        target = args.cache / member
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        sources.append({"path": path, "served": served, "bytes": len(raw), "SHA256": digest(raw)})
        return raw

    pairs = []

    def paired(path):
        raw = fetch(path)
        live = fetch(path, True)
        check("served_bytes_equal_committed", raw == live)
        pairs.append({"path": path, "equal": raw == live, "SHA256": digest(raw), "bytes": len(raw)})
        return json.loads(raw), raw

    board, board_raw = paired("output/data/week.json")
    meta, _ = paired("output/data/meta.json")
    pointer, pointer_raw = paired("output/data/weekly-selected-rankings.json")
    rank, rank_raw = paired("output/data/" + pointer["path"])
    overlay_pointer, _ = paired("output/data/weekly-adaptive-overlay.json")
    overlay, overlay_raw = paired("output/" + overlay_pointer["path"])
    check("ranking_body_hash", digest(rank_raw) == pointer["sha256"])
    check("board_binding", digest(board_raw) == pointer["display_board_sha256"] == rank["display_board_sha256"])
    check("overlay_binding", digest(overlay_raw) == pointer["overlay_sha256"] == rank["overlay_sha256"])
    check("policy_binding", digest(canonical(rank["policy"])) == rank["policy_sha256"])
    key = lambda p: (p["game_id"], p["player_id"], p["key"], p["direction"])
    ordering = lambda p: (-abs(p["score"]), p["game_id"], p["player_id"], p["key"])
    utc = lambda value: datetime.fromisoformat(value.replace("Z", "+00:00"))
    all_picks = rank["picks"]["over"] + rank["picks"]["under"]
    check("unique_exact_opportunities", len({key(p) for p in all_picks}) == len(all_picks))
    proof_index = {tuple(p["key"]): p for p in rank["frozen_proofs"]}
    check("unique_frozen_proofs", len(proof_index) == len(rank["frozen_proofs"]))
    receipt_index = {}
    for sha in sorted({p["receipt_sha256"] for p in rank["frozen_proofs"]}):
        receipt = json.loads(fetch("output/data/weekly-selected-rankings/" + sha + ".receipt.json"))
        check("original_receipt_hash", digest(canonical(receipt)) == sha)
        original_raw = fetch("output/data/" + receipt["path"])
        check("original_body_hash", digest(original_raw) == receipt["sha256"])
        receipt_index[sha] = receipt, json.loads(original_raw)
    for side, picks in rank["picks"].items():
        check("side_capacity", len(picks) <= rank["policy"]["top_n"])
        check("stable_sorted_membership", picks == sorted(picks, key=ordering))
        check("one_player_per_side", len({p["player_id"] for p in picks}) == len(picks))
        for pick in picks:
            score = (pick["adj"] - pick["line"]) / rank["policy"]["categories"][pick["key"]]["scale"]
            check("exact_gap_score", math.isclose(pick["score"], score, rel_tol=1e-12, abs_tol=1e-12))
            check("selected_side", side == pick["direction"] == ("over" if score > 0 else "under"))
            check("minimum_gap_score", abs(score) >= rank["policy"]["minimum_score"])
            check("original_selection_before_kickoff", utc(pick["selected_at"]) < utc(pick["kickoff_utc"]))
            if key(pick) in proof_index:
                proof = proof_index[key(pick)]
                receipt, original = receipt_index[proof["receipt_sha256"]]
                check("frozen_original_exact_row", sum(p == pick for p in original["picks"][side]) == 1)
                check("frozen_receipt_clock", proof["persisted_at"] == receipt["published_at"] and utc(pick["selected_at"]) <= utc(proof["persisted_at"]) < utc(pick["kickoff_utc"]))

    # Independently rebuild only this packet's fresh slot candidates. Started
    # games retain their prior receipt; they must never be reranked after results.
    policy = rank["policy"]
    cutoff = utc(rank["prepared_at"])
    games = {g["id"]: g for g in board["games"]}
    started = {k for k, g in games.items() if g.get("state") != "pre" or utc(g["kickoff"]) <= cutoff}
    candidates = {"over": [], "under": []}
    for player in board["players"]:
        minimum = policy["minimum_projected_ppr"].get(player.get("pos"))
        if player["game_id"] in started or minimum is None or player.get("injury") in policy["unavailable"]:
            continue
        if not all(type(player.get(k)) in (int, float) and math.isfinite(player[k]) for k in ("games_this_season", "snap_share", "proj_ppr")):
            continue
        if player["games_this_season"] < policy["minimum_games"] or player["snap_share"] < policy["minimum_snap_share"] or player["proj_ppr"] < minimum:
            continue
        best = {}
        for prop in player.get("props", []):
            settings = policy["categories"].get(prop["key"])
            line, value = prop.get("line"), prop.get("adj")
            if settings is None or prop.get("line_from") not in ("dk", "sleeper") or not all(type(x) in (int, float) and math.isfinite(x) for x in (line, value)):
                continue
            if type(prop.get("over")) is not int or type(prop.get("n")) is not int or not 0 <= prop["over"] <= prop["n"]:
                continue
            if line < settings["minimum_line"] or not policy["projection_line_ratio"][0] <= value / line <= policy["projection_line_ratio"][1]:
                continue
            gap = value - line
            score = gap / settings["scale"]
            if abs(gap) <= settings["lean"] or abs(score) < policy["minimum_score"]:
                continue
            side = "over" if score > 0 else "under"
            item = {"game_id": player["game_id"], "player_id": player["id"], "key": prop["key"], "direction": side, "score": score}
            if side not in best or ordering(item) < ordering(best[side]):
                best[side] = item
        for side, pick in best.items():
            candidates[side].append(pick)
    check("current_packet_has_no_selected_model_rows", len(overlay["rows"]) == 0)
    fresh_counts = {}
    for side, picks in rank["picks"].items():
        frozen = [p for p in picks if key(p) in proof_index]
        fresh = [p for p in picks if key(p) not in proof_index]
        expected = sorted(candidates[side], key=ordering)[:max(0, policy["top_n"] - len(frozen))]
        check("fresh_slot_membership", [key(p) for p in fresh] == [key(p) for p in expected])
        fresh_counts[side] = len(fresh)

    result = {
        "kind": "B_INDEPENDENT_CURRENT_SAVED_MEMBERSHIP_WITNESS_NOT_SELECTOR_BACKTEST",
        "at_UTC": datetime.now(timezone.utc).isoformat(),
        "production_commit": args.ref,
        "season": rank["season"], "week": rank["week"],
        "policy": policy["version"], "policy_SHA256": rank["policy_sha256"],
        "body_SHA256": digest(rank_raw), "pointer_SHA256": digest(pointer_raw),
        "prepared_at": rank["prepared_at"], "persisted_at": pointer["published_at"],
        "selected": len(all_picks), "sides": dict(collections.Counter(p["direction"] for p in all_picks)),
        "sources": dict(collections.Counter(p["forecast_source"] for p in all_picks)),
        "frozen_prior_records": len(proof_index), "original_receipts": len(receipt_index), "fresh_records": fresh_counts,
        "overlay_state": overlay["state"], "research_overlay_rows": len(overlay["rows"]),
        "model": meta.get("execution_model", {}).get("model"), "served_pairs": pairs,
        "checks": dict(checks), "failures": failures,
        "status": "PASS_CHECKED_SAVED_MEMBERSHIP" if not failures else "FAIL",
        "limits": [
            "Separate standard-library calculation; production selector and grader were not called.",
            "Fresh-slot selection independently reconstructed; frozen records checked against exact original bodies and receipt clocks.",
            "Original frozen full-board eligibility/quote clocks not independently reconstructed.",
            "Served bytes checked, browser rendering and mobile interactions not checked.",
            "No historical five-week changed-selector replay, source authentication, new forecasts, picks, release or model admission implied."
        ],
        "source_bindings": sources
    }
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in ("selected", "sides", "frozen_prior_records", "fresh_records", "status", "failures")}))
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
