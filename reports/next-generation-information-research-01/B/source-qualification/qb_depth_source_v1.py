"""Read-only nflverse QB depth snapshots. No forecasting, grading or collection.

Source: nflverse depth_charts release, CC-BY-4.0 repository license.
The source-authored `dt` is record load time, not a guaranteed starter label.
The caller must retain the current-vintage/source-loaded reconstruction tier.
"""
from __future__ import annotations

import bisect
import datetime as dt
import hashlib
import math
from pathlib import Path


def utc_seconds(value):
    if value is None:
        return None
    try:
        value = str(value)
        stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return None
        return stamp.timestamp()
    except (TypeError, ValueError, OverflowError):
        return None


class QBDepthSource:
    """Only exact team/GSIS joins and strict earlier source-loaded snapshots."""

    def __init__(self, sources):
        import fastparquet

        self.bindings = []
        self.records = []
        snapshots = {}
        self.invalid_clock_rows = 0
        for path, expected_sha256 in sources:
            path = Path(path)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != expected_sha256:
                raise ValueError("Depth source hash mismatch")
            self.bindings.append({"sha256": digest, "bytes": path.stat().st_size})
            frame = fastparquet.ParquetFile(path).to_pandas(columns=[
                "dt", "team", "gsis_id", "espn_id", "pos_grp", "pos_abb", "pos_slot", "pos_rank"
            ])
            # Preserve complete team update clocks even when no QB is reported.
            # Otherwise a later empty update could incorrectly reuse an old QB rank.
            for row in frame[["team", "dt"]].drop_duplicates().to_dict("records"):
                stamp = utc_seconds(row["dt"])
                if stamp is not None:
                    snapshots.setdefault(str(row["team"]), {}).setdefault(stamp, [])
            frame = frame[(frame.pos_abb == "QB") & (frame.pos_grp == "3WR 1TE")]
            for row in frame.to_dict("records"):
                stamp = utc_seconds(row["dt"])
                if stamp is None:
                    self.invalid_clock_rows += 1
                    continue
                snapshots.setdefault(str(row["team"]), {}).setdefault(stamp, []).append(row)
                rank = row["pos_rank"]
                if (isinstance(row["gsis_id"], str) and row["gsis_id"].strip()
                        and rank is not None and math.isfinite(float(rank))
                        and float(rank).is_integer() and int(rank) > 0):
                    self.records.append({"team": str(row["team"]), "player_id": str(row["gsis_id"]),
                                         "dt": stamp, "rank": int(rank)})
        self.snapshots = snapshots
        self.clocks = {team: sorted(values) for team, values in snapshots.items()}
        self.team_snapshots = [{"team": team, "dt": stamp}
                               for team in sorted(self.clocks) for stamp in self.clocks[team]]
        self.records.sort(key=lambda r: (r["dt"], r["team"], r["player_id"], r["rank"]))

    def asof(self, *, team, player_id, cutoff):
        if cutoff is None or not math.isfinite(float(cutoff)):
            return {"available": False, "reason": "UNKNOWN_QUERY_CUTOFF"}
        clocks = self.clocks.get(str(team), [])
        slot = bisect.bisect_left(clocks, float(cutoff)) - 1
        if slot < 0:
            return {"available": False, "reason": "NO_EARLIER_TEAM_SNAPSHOT"}
        clock = clocks[slot]
        rows = [r for r in self.snapshots[str(team)][clock] if r["gsis_id"] == player_id]
        common = {"source_loaded_utc": dt.datetime.fromtimestamp(clock, dt.timezone.utc).isoformat(),
                  "source_loaded_seconds": clock, "age_hours": (float(cutoff) - clock) / 3600}
        if len(rows) != 1:
            return {**common, "available": False,
                    "reason": "PLAYER_NOT_IN_LATEST_TEAM_SNAPSHOT" if not rows else "AMBIGUOUS_PLAYER_SLOT"}
        row = rows[0]
        rank = row["pos_rank"]
        if rank is None or not math.isfinite(float(rank)) or int(rank) != float(rank) or int(rank) < 1:
            return {**common, "available": False, "reason": "INVALID_RANK"}
        return {**common, "available": True, "reason": None, "rank": int(rank),
                "pos_slot": int(row["pos_slot"]), "source_espn_id": str(row["espn_id"])}

    def block(self, query, prior_query=None):
        current = self.asof(team=query["team"], player_id=query["player_id"], cutoff=query["kickoff"])
        current["prior_rank"] = None
        current["rank_change"] = None
        if (prior_query is not None and prior_query["team"] == query["team"]
                and float(prior_query["kickoff"]) < float(query["kickoff"])):
            prior = self.asof(team=prior_query["team"], player_id=query["player_id"], cutoff=prior_query["kickoff"])
            if current["available"] and prior["available"]:
                current["prior_rank"] = prior["rank"]
                current["rank_change"] = current["rank"] - prior["rank"]
        return current
