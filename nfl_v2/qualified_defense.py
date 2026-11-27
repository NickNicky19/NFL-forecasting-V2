"""Pregame opponent summaries of qualified historical player-stat rows.

These are observed-position population summaries, not complete official team
totals or causal defensive ratings. No acquisition, models or outcome scoring.
"""
from __future__ import annotations

import bisect
import collections
import math


CHART = 'nick-chart-ppr-v1'
RAW_COLUMNS = ('qualified_allowed_mean4', 'complete_target_games4',
               'qualified_rows4', 'known_target_rows4')
RATE_COLUMNS = RAW_COLUMNS + ('shrunk_allowed_per_opportunity4',
    'allowed_rate_minus_league', 'compatible_opportunities4',
    'complete_rate_games4', 'latest_eligible_age_days')


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def exposure(target, row):
    if target in {'pass_yd', 'pass_td', 'pass_cmp', 'pass_int'}:
        value = row['workload'].get('attempts')
    elif target == 'rush_yd':
        value = row['workload'].get('carries')
    elif target in {'rec', 'rec_yd'}:
        value = row['workload'].get('targets')
    elif target == 'rush_rec_yd':
        a, b = row['workload'].get('carries'), row['workload'].get('targets')
        value = a + b if finite(a) and finite(b) else None
    elif target in {'pass_att', 'rush_att', CHART, 'anytime_td'}:
        value = 1. if row.get('played') else None
    else:
        raise ValueError('unregistered target exposure')
    return float(value) if finite(value) and value >= 0 and int(value) == value else None


def game_observation(rows, target):
    if not rows:
        raise ValueError('a qualified source group is required')
    dims = ('game_id', 'defense', 'position', 'season', 'kickoff', 'available')
    if any(any(r[d] != rows[0][d] for d in dims) for r in rows):
        raise ValueError('mixed historical defense group')
    if len({r['player_id'] for r in rows}) != len(rows):
        raise ValueError('duplicate player in defense group')
    values = [r['values'].get(target) for r in rows]
    if target == CHART:
        values = [v / 50 if finite(v) else None for v in values]
    complete = all(finite(v) for v in values)
    opportunities = [exposure(target, r) for r in rows]
    # An exceptional nonzero credit with no compatible recorded exposure does
    # not become a fabricated rate. The ordinary target remains available.
    compatible = complete and all(n is not None and (n > 0 or y == 0)
                                  for n, y in zip(opportunities, values))
    return dict(**{d: rows[0][d] for d in dims}, target=target,
                rows=len(rows), known_rows=sum(finite(v) for v in values),
                target_sum=math.fsum(values) if complete else None,
                rate_target_sum=math.fsum(values) if compatible else None,
                opportunities=math.fsum(opportunities) if compatible else None,
                rate_state='COMPATIBLE' if compatible else 'MISSING_OR_INCOMPATIBLE_EXPOSURE')


class QualifiedDefenseHistory:
    def __init__(self, observations, *, kappa=20.):
        if not finite(kappa) or kappa <= 0:
            raise ValueError('positive compatible exposure shrinkage required')
        self.kappa = float(kappa)
        self.opponents = collections.defaultdict(list)
        self.league = collections.defaultdict(list)
        seen = set()
        for row in observations:
            key = (row['game_id'], row['defense'], row['position'], row['target'])
            if key in seen:
                raise ValueError('duplicate historical defense observation')
            if not finite(row['available']) or row['available'] <= row['kickoff']:
                raise ValueError('earlier-game availability contract required')
            seen.add(key)
            self.opponents[(row['defense'], row['position'], row['target'])].append(row)
            self.league[(row['position'], row['target'])].append(row)
        self.opponent_times = self._sort(self.opponents)
        self.league_times = self._sort(self.league)
        self._league_prefixes = {}

    @staticmethod
    def _sort(groups):
        times = {}
        for key, rows in groups.items():
            rows.sort(key=lambda r: (r['available'], r['kickoff'], r['game_id']))
            times[key] = [r['available'] for r in rows]
        return times

    @staticmethod
    def _eligible(groups, times, key, cutoff, floor):
        rows = groups.get(key, [])
        end = bisect.bisect_left(times.get(key, []), cutoff)
        return [r for r in rows[:end] if r['season'] >= floor]

    def at(self, defense, position, target, cutoff, *, feature_floor=2022):
        local = self._eligible(self.opponents, self.opponent_times,
                               (defense, position, target), cutoff, feature_floor)[-4:]
        prefix_key = (position, target, feature_floor)
        if prefix_key not in self._league_prefixes:
            rows = [r for r in self.league.get((position,target),[]) if r['season'] >= feature_floor]
            times = [r['available'] for r in rows]
            ns, ys, counts = [0.], [0.], [0]
            for r in rows:
                good = r['opportunities'] is not None
                ns.append(ns[-1] + (r['opportunities'] if good else 0.))
                ys.append(ys[-1] + (r['rate_target_sum'] if good else 0.))
                counts.append(counts[-1] + int(good))
            self._league_prefixes[prefix_key] = (times, ns, ys, counts)
        times, ns, ys, counts = self._league_prefixes[prefix_key]
        end = bisect.bisect_left(times, cutoff)
        totals = [r['target_sum'] for r in local if r['target_sum'] is not None]
        rates = [r for r in local if r['opportunities'] is not None]
        local_n = math.fsum(r['opportunities'] for r in rates)
        local_y = math.fsum(r['rate_target_sum'] for r in rates)
        league_n, league_y = ns[end], ys[end]
        r0 = league_y / league_n if league_n else None
        shrunk = ((self.kappa * r0 + local_y) / (self.kappa + local_n)
                  if r0 is not None else None)
        maximum = max((r['available'] for r in local), default=None)
        result = dict(qualified_allowed_mean4=math.fsum(totals)/len(totals) if totals else None,
                      complete_target_games4=len(totals), qualified_rows4=sum(r['rows'] for r in local),
                      known_target_rows4=sum(r['known_rows'] for r in local),
                      shrunk_allowed_per_opportunity4=shrunk,
                      allowed_rate_minus_league=shrunk-r0 if shrunk is not None else None,
                      compatible_opportunities4=local_n, complete_rate_games4=len(rates),
                      latest_eligible_age_days=(cutoff-max(r['kickoff'] for r in local))/86400 if local else None)
        audit = dict(latest_local_available=maximum,
                     latest_league_available=times[end-1] if end else None,
                     local_game_ids=[r['game_id'] for r in local], local_game_slots=len(local),
                     league_rate_games=counts[end], league_opportunities=league_n,
                     league_rate=r0, feature_floor=feature_floor, kappa=self.kappa)
        if any(t is not None and t >= cutoff for t in (maximum, audit['latest_league_available'])):
            raise AssertionError('defense chronology')
        return result, audit
