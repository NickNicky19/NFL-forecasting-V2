"""As-of source-reported QB depth ranks, without starter/health inference.

The caller supplies canonical identities and source-loaded timestamp observations.
Depth ranks describe their provider snapshot, not guaranteed future participation.
"""
from __future__ import annotations

import bisect
import math
from collections import defaultdict


VALUE_NAMES = (
    'current_depth_rank',
    'rank_change_since_eligible_own_game',
    'current_snapshot_age_hours',
)
SUPPORT_FEATURES = (
    'current_snapshot_available',
    'current_player_in_snapshot',
    'current_rank_available',
    'previous_role_available',
    'current_depth_rank_missing',
    'rank_change_since_eligible_own_game_missing',
    'current_snapshot_age_hours',
    'current_snapshot_age_hours_missing',
)


def _clock(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _identity(row, key):
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Missing canonical ' + key)
    return value


def _rank(value):
    if value is None:
        return None
    result = _clock(value)
    if result is None or result <= 0 or result != int(result):
        raise ValueError('Depth rank must be a finite positive integer or null')
    return int(result)


class DepthRoleHistory:
    """Select a strict earlier TEAM snapshot before looking up its player."""

    def __init__(self, records, *, team_snapshots=()):
        self.snapshots = defaultdict(dict)
        self.excluded_unknown_clock_rows = 0
        self.identical_duplicate_rows = 0
        # A complete team snapshot can contain no QB records. Retain its clock
        # before projecting positions so it cannot resurrect an older QB row.
        for row in team_snapshots:
            team = _identity(row, 'team')
            stamp = _clock(row.get('dt'))
            if stamp is not None:
                self.snapshots[team].setdefault(stamp, {})
        seen = {}
        for row in records:
            team, player = _identity(row, 'team'), _identity(row, 'player_id')
            dt = _clock(row.get('dt'))
            if dt is None:
                self.excluded_unknown_clock_rows += 1
                continue
            rank = _rank(row.get('rank'))
            key = team, player, dt
            if key in seen:
                if seen[key] != rank:
                    raise ValueError('Conflicting depth rank for canonical identity/version')
                self.identical_duplicate_rows += 1
                continue
            seen[key] = rank
            self.snapshots[team].setdefault(dt, {})[player] = rank
        self.times = {team: sorted(snapshots)
                      for team, snapshots in self.snapshots.items()}

    def _lookup(self, team, player, cutoff):
        times = self.times.get(team, ())
        index = bisect.bisect_left(times, cutoff) - 1
        if index < 0:
            return dict(dt=None, player_present=False, rank=None,
                        status='NO_EARLIER_TEAM_SNAPSHOT')
        dt = times[index]
        snapshot = self.snapshots[team][dt]
        present = player in snapshot
        rank = snapshot.get(player)
        return dict(dt=dt, player_present=present, rank=rank,
                    status='ABSENT_LATEST_TEAM_SNAPSHOT' if not present else
                    'UNKNOWN_REPORTED_RANK' if rank is None else
                    'OBSERVED_SOURCE_REPORTED_RANK')

    def describe(self, q, previous=None):
        team, player = _identity(q, 'team'), _identity(q, 'player_id')
        cutoff = _clock(q.get('kickoff'))
        if cutoff is None:
            raise ValueError('Query requires finite kickoff cutoff')
        current = self._lookup(team, player, cutoff)
        prior = dict(dt=None, player_present=False, rank=None,
                     status='NO_SAME_TEAM_ELIGIBLE_OWN_GAME')
        previous_kickoff = None
        if previous is not None:
            # Eligibility of this own game is the caller's registered history
            # contract. Never infer it from target outcomes or depth rank.
            previous_kickoff = _clock(previous.get('kickoff'))
            if (previous.get('team') == team and previous.get('player_id') == player
                    and previous_kickoff is not None and previous_kickoff < cutoff):
                prior = self._lookup(team, player, previous_kickoff)
            else:
                previous_kickoff = None
        rank, prior_rank = current['rank'], prior['rank']
        values = dict(
            current_depth_rank=rank,
            rank_change_since_eligible_own_game=None if rank is None or prior_rank is None
            else rank - prior_rank,
            current_snapshot_age_hours=None if current['dt'] is None
            else (cutoff - current['dt']) / 3600.,
        )
        return dict(
            values=values,
            missing_flags={name: value is None for name, value in values.items()},
            support=dict(current_snapshot_available=current['dt'] is not None,
                         current_player_in_snapshot=current['player_present'],
                         current_rank_available=rank is not None,
                         previous_role_available=prior_rank is not None),
            clocks=dict(current_snapshot_dt=current['dt'],
                        previous_snapshot_dt=prior['dt'],
                        previous_game_kickoff=previous_kickoff),
            current_status=current['status'], previous_status=prior['status'],
            excluded_unknown_clock_rows=self.excluded_unknown_clock_rows,
            semantics='SOURCE_REPORTED_DEPTH_RANK_NOT_STARTER_HEALTH_OR_PARTICIPATION_PROBABILITY',
        )


def feature_names(arm):
    if arm not in ('S0', 'S1', 'S2'):
        raise ValueError('Unknown depth-role arm')
    return [] if arm == 'S0' else list(SUPPORT_FEATURES) + (
        ['current_depth_rank', 'rank_change_since_eligible_own_game'] if arm == 'S2' else [])


def feature_values(description, arm):
    """Numeric neutral fills always accompany declared missing indicators."""
    values = dict(description['support'])
    values.update(description['values'])
    values.update({name + '_missing': missing
                   for name, missing in description['missing_flags'].items()})
    return [0. if values[name] is None else float(values[name])
            for name in feature_names(arm)]
