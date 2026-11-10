"""As-of QB/team passing opportunity profiles from qualified retained PBP.

These are descriptive inputs, not forecasts, starter declarations or offers.
The existing seven-day current-vintage reconstruction policy is unchanged.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

VERSION = 'B-PASSING-OPPORTUNITY-DEFENSE-PROFILES-v2'
SOURCE_TIER = 'CURRENT_REVISED_SOURCE_SEVEN_DAY_RECONSTRUCTION'
TEAMS = tuple('ARI ATL BAL BUF CAR CHI CIN CLE DAL DEN DET GB HOU IND JAX KC LA LAC LV MIA MIN NE NO NYG NYJ PHI PIT SEA SF TB TEN WAS'.split())
COUNT_NAMES = ('opportunities', 'dropbacks', 'credited_attempts', 'completions',
               'completion_known_attempts', 'sacks', 'scrambles', 'spikes', 'kneels',
               'unknown_dropback', 'unknown_sack', 'unknown_scramble', 'unknown_spike',
               'unknown_completion', 'unassigned_dropbacks', 'unassigned_attempts',
               'attributed_team_dropbacks', 'attributed_team_attempts',
               'attempts_on_dropbacks', 'dropback_known_opportunities',
               'sack_known_dropbacks', 'scramble_known_dropbacks', 'spike_known_attempts')
DOWNS = ('1', '2', '3', '4', 'UNKNOWN')
DISTANCES = ('0_TO_3', '4_TO_6', '7_TO_10', '11_PLUS', 'UNKNOWN')
FIELDS = ('OWN_0_TO_LT20', 'OWN20_TO_MIDFIELD', 'OPP_HALF_OUTSIDE_REDZONE', 'REDZONE', 'UNKNOWN')
RATE_DEFS = {
    'dropback_per_opportunity': ('dropbacks', 'dropback_known_opportunities'),
    'attempt_per_dropback': ('attempts_on_dropbacks', 'dropbacks'),
    'completion_per_attempt': ('completions', 'completion_known_attempts'),
    'sack_per_dropback': ('sacks', 'sack_known_dropbacks'),
    'scramble_per_dropback': ('scrambles', 'scramble_known_dropbacks'),
    'spike_per_attempt': ('spikes', 'spike_known_attempts'),
    'QB_dropback_share': ('dropbacks', 'attributed_team_dropbacks'),
    'QB_attempt_share': ('credited_attempts', 'attributed_team_attempts'),
}


def number(value):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def coarse_bins(row):
    down, distance, field = (number(row.get(k)) for k in ('down', 'ydstogo', 'yardline_100'))
    return (int(down)-1 if down in (1, 2, 3, 4) else 4,
            4 if distance is None or distance < 0 else 0 if distance <= 3 else 1 if distance <= 6 else 2 if distance <= 10 else 3,
            4 if field is None or not 0 <= field <= 100 else 0 if field > 80 else 1 if field >= 50 else 2 if field > 20 else 3)


def play_counts(row):
    """Return known indicator counts; explicit unknowns never become event zeros.

    Denominator is a documented offensive opportunity proxy: a nondeleted,
    non-two-point play with a reported rush attempt, pass attempt or dropback.
    It is not every snap, designed pass call, route or play including nullified
    penalties. Credited attempts retain the accepted sack exclusion, including
    any credited attempt whose play_type is no_play.
    """
    if number(row.get('play_deleted')) != 0 or number(row.get('two_point_attempt')) != 0:
        return None
    flags = {k: number(row.get(k)) for k in ('pass_attempt', 'rush_attempt', 'qb_dropback', 'sack', 'qb_scramble', 'qb_spike', 'qb_kneel', 'complete_pass')}
    if not any(flags[k] == 1 for k in ('pass_attempt', 'rush_attempt', 'qb_dropback')):
        return None
    attempt = flags['pass_attempt'] == 1 and flags['sack'] == 0
    result = dict.fromkeys(COUNT_NAMES, 0)
    result.update(opportunities=1, dropbacks=int(flags['qb_dropback'] == 1),
                  credited_attempts=int(attempt), completions=int(attempt and flags['complete_pass'] == 1),
                  completion_known_attempts=int(attempt and flags['complete_pass'] in (0, 1)),
                  sacks=int(flags['sack'] == 1), scrambles=int(flags['qb_scramble'] == 1),
                  spikes=int(attempt and flags['qb_spike'] == 1), kneels=int(flags['qb_kneel'] == 1),
                  unknown_dropback=int(flags['qb_dropback'] not in (0, 1)),
                  unknown_sack=int(flags['sack'] not in (0, 1)),
                  unknown_scramble=int(flags['qb_scramble'] not in (0, 1)),
                  unknown_spike=int(flags['qb_spike'] not in (0, 1)),
                  unknown_completion=int(attempt and flags['complete_pass'] not in (0, 1)))
    result.update(attempts_on_dropbacks=int(attempt and flags['qb_dropback']==1),
                  dropback_known_opportunities=int(flags['qb_dropback'] in (0,1)),
                  sack_known_dropbacks=int(flags['qb_dropback']==1 and flags['sack'] in (0,1)),
                  scramble_known_dropbacks=int(flags['qb_dropback']==1 and flags['qb_scramble'] in (0,1)),
                  spike_known_attempts=int(attempt and flags['qb_spike'] in (0,1)))
    return result


def blank_counts():
    return dict.fromkeys(COUNT_NAMES, 0)


def blank_cells():
    return {name: [blank_counts() for _ in range(5)] for name in ('down', 'distance', 'field')}


def add_counts(target, counts):
    for key in COUNT_NAMES:
        target[key] += counts[key]


def ratio(numerator, denominator):
    return dict(numerator=numerator, denominator=denominator,
                raw=numerator/denominator if denominator else None,
                state='UNDEFINED_ZERO_DENOMINATOR' if not denominator else 'KNOWN_ZERO' if not numerator else 'OBSERVED')


def _iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def _sum(rows):
    result = blank_counts()
    for row in rows:
        add_counts(result, row['counts'])
    return result


class OpportunityHistory:
    """History admission precedes game-time windowing; target data is unread."""
    def __init__(self, team_rows, qb_rows, *, own_window=8, team_window=16, strength=100.):
        self.team_rows = sorted(team_rows, key=lambda r: (r['kickoff'], r['game_id'], r['team']))
        self.qb_rows = sorted(qb_rows, key=lambda r: (r['kickoff'], r['game_id'], r['player_id']))
        self.own_window, self.team_window, self.strength = own_window, team_window, strength
        for rows, identity in ((self.team_rows, ('game_id', 'team')), (self.qb_rows, ('game_id', 'player_id'))):
            seen = set()
            for row in rows:
                key = tuple(row[k] for k in identity)
                if key in seen:
                    raise ValueError('Duplicate opportunity identity')
                seen.add(key)
                # Explicitly unknown source clocks cannot inherit the proxy.
                if number(row.get('available')) is None or number(row.get('kickoff')) is None:
                    raise ValueError('Unknown history clock')
                if row['available'] != row['kickoff'] + 7*86400:
                    raise ValueError('Changed seven-day information policy')

    def rows(self, cutoff, *, player=None, team=None, defense=None):
        if number(cutoff) is None:
            raise ValueError('Unknown cutoff')
        source = self.qb_rows if player is not None else self.team_rows
        rows = [r for r in source if r['available'] < cutoff
                and (player is None or r['player_id'] == player)
                and (team is None or r['team'] == team)
                and (defense is None or r['opponent'] == defense)]
        if player is not None:
            return rows[-self.own_window:]
        if team is not None or defense is not None:
            return rows[-self.team_window:]
        return rows

    def summarize(self, rows, cutoff, *, prior_rows=None):
        counts = _sum(rows)
        prior_rows = self.rows(cutoff) if prior_rows is None else prior_rows
        prior = _sum(prior_rows)
        rates = {}
        for name, (numerator, denominator) in RATE_DEFS.items():
            value = ratio(counts[numerator], counts[denominator])
            prior_rate = prior[numerator]/prior[denominator] if prior[denominator] else None
            value.update(prior=prior_rate, prior_denominator=prior[denominator], pseudo_opportunities=self.strength,
                         shrunk=(counts[numerator]+self.strength*prior_rate)/(counts[denominator]+self.strength) if prior_rate is not None else None)
            rates[name] = value
        volume = {}
        for key in ('opportunities', 'dropbacks', 'credited_attempts', 'completions', 'sacks'):
            prior_mean = prior[key]/len(prior_rows) if prior_rows else None
            volume[key] = dict(total=counts[key], games=len(rows), raw_per_game=counts[key]/len(rows) if rows else None,
                               earlier_league_per_game=prior_mean,
                               shrunk_per_game=(counts[key]+4*prior_mean)/(len(rows)+4) if prior_mean is not None else None)
        cells = blank_cells()
        for row in rows:
            for name in cells:
                for target, source in zip(cells[name], row['cells'][name]):
                    add_counts(target, source)
        return dict(status='OBSERVED_HISTORY' if rows else 'NO_OWN_HISTORY_EARLIER_LEAGUE_PRIOR' if prior_rows else 'NO_EARLIER_SUPPORT',
                    games=len(rows), game_ids=[r['game_id'] for r in rows], counts=counts, rates=rates, volume=volume,
                    uncertainty='DESCRIPTIVE_COUNTS_AND_PRIOR_SUPPORT; no game-dependent confidence interval or predictive uncertainty supplied',
                    contexts={name:[dict(label=label, counts=c, opportunity_frequency=ratio(c['opportunities'],counts['opportunities']),
                                        dropback_frequency=ratio(c['dropbacks'],counts['dropbacks']),
                                        completion_per_attempt=ratio(c['completions'],c['completion_known_attempts']))
                                    for label,c in zip(labels,cells[name])]
                              for name,labels in (('down',DOWNS),('distance',DISTANCES),('field',FIELDS))},
                    latest_prior_game=None if not rows else rows[-1]['game_id'],
                    latest_prior_game_at=None if not rows else _iso(rows[-1]['kickoff']),
                    latest_source_available_at=None if not rows else _iso(max(r['available'] for r in rows)),
                    feature_age_days=None if not rows else (cutoff-rows[-1]['kickoff'])/86400,
                    source_age_days=None if not rows else (cutoff-max(r['available'] for r in rows))/86400)

    def build(self, query):
        cutoff = query.get('cutoff', query['kickoff'])
        if number(cutoff) is None or cutoff > query['kickoff']:
            raise ValueError('Invalid query cutoff')
        prior = self.rows(cutoff)
        return dict(version=VERSION, source_tier=SOURCE_TIER,
                    identity={k:query[k] for k in ('player_id','game_id','team','opponent','season','week','kickoff')}, cutoff=cutoff,
                    query_population='RETROSPECTIVE_QB_STAT_ROWS_UNLESS_INDEPENDENT_PREGAME_MEMBERSHIP_QUALIFIED',
                    own=self.summarize(self.rows(cutoff,player=query['player_id']),cutoff,
                                       prior_rows=[r for r in self.qb_rows if r['available'] < cutoff]),
                    offense=self.summarize(self.rows(cutoff,team=query['team']),cutoff,prior_rows=prior),
                    defense=self.summarize(self.rows(cutoff,defense=query['opponent']),cutoff,prior_rows=prior))

    def defense_profile(self, team, cutoff, season, week):
        if team not in TEAMS:
            raise ValueError('Unknown canonical defense')
        return dict(version=VERSION, team=team, season=season, week=week, cutoff=cutoff,
                    source_tier=SOURCE_TIER, role='ALL_SUPPORTED_OFFENSES_FACED_NOT_PRIORITY_PLAYER_ONLY',
                    summary=self.summarize(self.rows(cutoff,defense=team),cutoff))

    def build_current(self, query):
        """Current adapter requires separately retained pregame membership."""
        from .qb_context_profiles import query_validation
        reason=query_validation(query,'SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE')
        if reason:
            return dict(version=VERSION,status='UNAVAILABLE_PROFILE',reason=reason)
        value=self.build(query)
        value['query_population']='SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE'
        return value

    def feature_groups(self, query):
        """Finite numerical blocks; null means no qualified support, not zero."""
        p = self.build(query)
        support, own, defense = {}, {}, {}
        for group in ('own','offense','defense'):
            x = p[group]
            support.update({f'{group}_games':float(x['games']), f'{group}_opportunities':float(x['counts']['opportunities']),
                            f'{group}_source_age_days':x['source_age_days'], f'{group}_no_history':float(not x['games']),
                            f'{group}_unknown_completion':float(x['counts']['unknown_completion']),
                            f'{group}_unknown_dropback':float(x['counts']['unknown_dropback'])})
        for group,target in (('own',own),('offense',own),('defense',defense)):
            x=p[group]
            for name,rate in x['rates'].items():
                target[f'{group}_{name}']=rate['shrunk']
            for name,volume in x['volume'].items():
                target[f'{group}_{name}_per_game']=volume['shrunk_per_game']
            for name,cells in x['contexts'].items():
                for j,cell in enumerate(cells):
                    target[f'{group}_{name}_{j}_dropback_mix']=cell['dropback_frequency']['raw']
                    target[f'{group}_{name}_{j}_completion_rate']=cell['completion_per_attempt']['raw']
        return dict(R1_support=support, R2_player_values=own, R3_defense_values=defense)
