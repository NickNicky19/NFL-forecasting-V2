"""A separate four-SCHEDULED-game alternative to retained observed groups.

No acquisition, fitting, prediction or scoring. An absent qualified-position
group is an unknown slot, never an observed zero. The league rate continues to
use precisely the original compatible observed groups.
"""
from __future__ import annotations

import bisect
import collections
import math

from .qualified_defense import QualifiedDefenseHistory, finite, game_observation

VERSION = 'v2-scheduled-four-game-qualified-defense-v1'
AVAILABILITY_SECONDS = 7 * 86400


class ScheduledQualifiedDefenseHistory:
    """Use four eligible scheduled REG team games; missing groups consume slots."""

    def __init__(self, observations, scheduled_games, *, kappa=20.):
        observations = list(observations)
        self.observed = QualifiedDefenseHistory(observations, kappa=kappa)
        self.kappa = self.observed.kappa
        self.lookup = {(r['game_id'], r['defense'], r['position'], r['target']): r
                       for r in observations}
        self.teams = collections.defaultdict(list)
        self.games = {}
        for g in scheduled_games:
            gid = g['game_id']
            if gid in self.games:
                raise ValueError('duplicate scheduled game')
            if (g.get('period', 'REG') != 'REG' or not isinstance(g['season'], int)
                    or g['season'] not in range(2022, 2027)
                    or not isinstance(g['week'], int) or not 1 <= g['week'] <= 18
                    or (g['season'] == 2026 and g['week'] > 7)
                    or not finite(g['kickoff']) or g['home'] == g['away']
                    or not g['home'] or not g['away']):
                raise ValueError('supported scheduled REG history through 2026W7 required')
            slot = dict(game_id=gid, season=g['season'], week=g['week'],
                        kickoff=g['kickoff'], available=g['kickoff'] + AVAILABILITY_SECONDS)
            self.games[gid] = slot
            for team in (g['home'], g['away']):
                self.teams[team].append(dict(slot, defense=team))
        self.times = {}
        for team, slots in self.teams.items():
            slots.sort(key=lambda x: (x['available'], x['kickoff'], x['game_id']))
            self.times[team] = [s['available'] for s in slots]
        for r in observations:
            slot = self.games.get(r['game_id'])
            if (slot is None or any(r[k] != slot[k] for k in ('season', 'kickoff', 'available'))
                    or not any(s['game_id'] == r['game_id'] for s in self.teams[r['defense']])):
                raise ValueError('observed group must bind exact admitted schedule/availability')

    def at(self, defense, position, target, cutoff, *, feature_floor=2022):
        if not finite(cutoff) or feature_floor not in (2022, 2026):
            raise ValueError('finite registered cutoff and feature floor required')
        end = bisect.bisect_left(self.times.get(defense, []), cutoff)
        slots = [s for s in self.teams.get(defense, [])[:end]
                 if s['season'] >= feature_floor][-4:]
        local = [self.lookup.get((s['game_id'], defense, position, target)) for s in slots]
        observed = [r for r in local if r is not None]
        # Keep the league numerator, denominator, support and chronology exactly
        # the same as the retained observed-group implementation.
        _, league_audit = self.observed.at(defense, position, target, cutoff,
                                          feature_floor=feature_floor)
        totals = [r['target_sum'] for r in observed if r['target_sum'] is not None]
        rates = [r for r in observed if r['opportunities'] is not None]
        local_n = math.fsum(r['opportunities'] for r in rates)
        local_y = math.fsum(r['rate_target_sum'] for r in rates)
        r0 = league_audit['league_rate']
        shrunk = ((self.kappa * r0 + local_y) / (self.kappa + local_n)
                  if r0 is not None else None)
        result = dict(
            qualified_allowed_mean4=math.fsum(totals) / len(totals) if totals else None,
            complete_target_games4=len(totals),
            qualified_rows4=sum(r['rows'] for r in observed),
            known_target_rows4=sum(r['known_rows'] for r in observed),
            shrunk_allowed_per_opportunity4=shrunk,
            allowed_rate_minus_league=shrunk - r0 if shrunk is not None else None,
            compatible_opportunities4=local_n, complete_rate_games4=len(rates),
            latest_eligible_age_days=(cutoff - slots[-1]['kickoff']) / 86400 if slots else None)
        audit = dict(league_audit,
            window_contract='FOUR_ELIGIBLE_SCHEDULED_REG_TEAM_GAMES',
            local_game_ids=[s['game_id'] for s in slots], local_game_slots=len(slots),
            observed_group_game_ids=[r['game_id'] for r in observed],
            absent_group_game_ids=[s['game_id'] for s, r in zip(slots, local) if r is None],
            absent_group_slots=sum(r is None for r in local),
            latest_local_available=slots[-1]['available'] if slots else None,
            age_contract='days since latest eligible scheduled kickoff, even if group absent')
        if any(t is not None and t >= cutoff for t in
               (audit['latest_local_available'], audit['latest_league_available'])):
            raise AssertionError('scheduled defense chronology')
        return result, audit


def build_history(rows, games, targets):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r['game_id'], r['defense'], r['position']].append(r)
    observations = [game_observation(rs, target) for rs in groups.values() for target in targets]
    schedule = [dict(g, game_id=gid) for gid, g in games.items()
                if g['season'] in range(2022, 2027) and 1 <= g['week'] <= 18
                and not (g['season'] == 2026 and g['week'] > 7)]
    return ScheduledQualifiedDefenseHistory(observations, schedule, kappa=20.)
