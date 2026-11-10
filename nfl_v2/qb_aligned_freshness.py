"""One fully aligned reconstructed timing sensitivity for existing E3/R2.

The 48-hour alternative is not an authenticated observation clock. All old
modules and source bytes remain unchanged; this wrapper binds new derivatives.
"""
from __future__ import annotations

import copy
import math

from . import player_context_matchup as ctx
from . import qb_opportunity_increment as inc
from .passing_opportunity_profiles import OpportunityHistory

VERSION='B-QB-ALIGNED-FRESHNESS-PROFILES-v1'
CONTROL='DECLARED_KICKOFF_PLUS_7D_RECONSTRUCTION'
ALTERNATIVE='DECLARED_KICKOFF_PLUS_48H_TIMING_SENSITIVITY'
DELAYS={CONTROL:7*86400,ALTERNATIVE:48*3600}
ARMS={'F0':(CONTROL,'R0'),'F1':(CONTROL,'R2'),
      'F2':(ALTERNATIVE,'R0'),'F3':(ALTERNATIVE,'R2')}


def finite_clock(value):
    return not isinstance(value,bool) and isinstance(value,(int,float)) and math.isfinite(value)


def identity(row):
    fields=('game_id','player_id','team','opponent') if 'player_id' in row else ('game_id','team','opponent')
    if any(not isinstance(row.get(key),str) or not row[key] for key in fields):
        raise ValueError('Missing canonical history identity')
    # Team/opponent are required metadata, not a way to count a conflicting
    # version of the same QB-game or team-game as another observation.
    primary=('game_id','player_id') if 'player_id' in row else ('game_id','team')
    return tuple(row[key] for key in primary)


def reconstruct_rows(rows,policy_id,*,allow_absent_column=False):
    """Convert only the declared original seven-day reconstruction contract.

    Explicit null/nonfinite row clocks are returned unresolved, never filled.
    A wholly absent clock column needs a separately declared permission.
    No observed clock is overwritten, relabelled or authenticated here.
    """
    if policy_id not in DELAYS:
        raise ValueError('Unregistered reconstruction policy')
    valid=[];unresolved=[];seen=set()
    absent_everywhere=bool(rows) and all('available' not in r for r in rows)
    for row in rows:
        key=identity(row)
        if key in seen:
            raise ValueError('Duplicate history identity/version requires source resolution')
        seen.add(key)
        kickoff=row.get('kickoff')
        reason=None
        if not finite_clock(kickoff):
            reason='UNKNOWN_OR_INVALID_GAME_TIME'
        elif 'available' not in row and not(absent_everywhere and allow_absent_column):
            reason='ABSENT_AVAILABILITY_COLUMN_NOT_DECLARED'
        elif 'available' in row and not finite_clock(row['available']):
            reason='EXPLICIT_UNKNOWN_AVAILABILITY'
        elif any(k in row and not finite_clock(row[k]) for k in ('observed_available_at','outcome_available_at')):
            reason='EXPLICIT_UNKNOWN_OBSERVATION_CLOCK'
        elif any(k in row for k in ('observed_available_at','outcome_available_at')):
            # An observed/versioned route must receive its own qualification;
            # this sensitivity must not replace a genuine observed clock.
            reason='OBSERVED_CLOCK_ROUTE_NOT_THIS_RECONSTRUCTION'
        elif 'available' in row and row['available']!=kickoff+DELAYS[CONTROL]:
            reason='INPUT_NOT_DECLARED_SEVEN_DAY_RECONSTRUCTION'
        if reason:
            unresolved.append(dict(identity=list(key),reason=reason));continue
        new=copy.deepcopy(row)
        new['retained_declared_7day_available']=row.get('available')
        new['available']=kickoff+DELAYS[policy_id]
        new['information_policy_id']=policy_id
        new['availability_evidence']='RECONSTRUCTED_TIMING_SENSITIVITY_NOT_HISTORICAL_PUBLICATION'
        valid.append(new)
    valid.sort(key=lambda r:(r['kickoff'],r['game_id'],r.get('player_id',''),r['team']))
    return valid,unresolved


def eligible_recent(rows,cutoff,limit,*,player_id=None):
    """Availability admission first; recent games selected by game time."""
    if not finite_clock(cutoff) or isinstance(limit,bool) or not isinstance(limit,int) or limit<1:
        raise ValueError('Invalid cutoff/window')
    admitted=[r for r in rows if finite_clock(r.get('available')) and finite_clock(r.get('kickoff'))
              and r['available']<cutoff and(player_id is None or r.get('player_id')==player_id)]
    admitted.sort(key=lambda r:(r['kickoff'],r['game_id'],r.get('player_id',''),r['team']))
    keys=[identity(r) for r in admitted]
    if len(keys)!=len(set(keys)):
        raise ValueError('Duplicate admitted history identity/version')
    return admitted[-limit:]


class PolicyOpportunityHistory(OpportunityHistory):
    """Same profile calculations; strict, explicitly bound alternative clock."""
    def __init__(self,team_rows,qb_rows,*,policy_id,own_window=8,team_window=16,strength=100.):
        if policy_id not in DELAYS:
            raise ValueError('Unregistered opportunity clock policy')
        self.policy_id=policy_id
        self.own_window,self.team_window,self.strength=own_window,team_window,strength
        self.team_rows=sorted(team_rows,key=lambda r:(r['kickoff'],r['game_id'],r['team']))
        self.qb_rows=sorted(qb_rows,key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
        for source in (self.team_rows,self.qb_rows):
            seen=set()
            for row in source:
                key=identity(row)
                if key in seen:
                    raise ValueError('Duplicate opportunity identity/version')
                seen.add(key)
                if (not finite_clock(row.get('available')) or not finite_clock(row.get('kickoff'))
                    or row.get('information_policy_id')!=policy_id
                    or row['available']!=row['kickoff']+DELAYS[policy_id]):
                    raise ValueError('Unknown or mismatched registered opportunity clock')

    def build(self,query):
        value=super().build(query)
        value.update(version=VERSION,information_policy_id=self.policy_id,
                     source_tier='CURRENT_REVISED_SOURCE_RECONSTRUCTED_TIMING_SENSITIVITY')
        return value

    def defense_profile(self,team,cutoff,season,week):
        value=super().defense_profile(team,cutoff,season,week)
        value.update(version=VERSION,information_policy_id=self.policy_id,
                     source_tier='CURRENT_REVISED_SOURCE_RECONSTRUCTED_TIMING_SENSITIVITY')
        return value


class AlignedFreshnessBundle:
    """Bound histories for one policy; no fitting, outcomes or offer scoring."""
    def __init__(self,qb_inputs,opportunity_source,*,policy_id):
        self.policy_id=policy_id
        self.rows,u1=reconstruct_rows(qb_inputs,policy_id)
        team,u2=reconstruct_rows(opportunity_source['team_games'],policy_id)
        qb,u3=reconstruct_rows(opportunity_source['QB_games'],policy_id)
        self.unresolved=dict(QB_inputs=u1,team_opportunities=u2,QB_opportunities=u3)
        self.history=ctx.ContextHistory(self.rows,8,20)
        self.opportunity=PolicyOpportunityHistory(team,qb,policy_id=policy_id)
        self.source=dict(version=VERSION,policy_id=policy_id,delay_seconds=DELAYS[policy_id],
                         QB_inputs=self.rows,team_games=team,QB_games=qb,unresolved=self.unresolved)

    def direct_features(self,query,arm):
        if arm not in ARMS or ARMS[arm][0]!=self.policy_id:
            raise ValueError('Arm/information policy mismatch')
        cutoff=query.get('cutoff',query['kickoff'])
        if not finite_clock(cutoff) or cutoff>query['kickoff']:
            raise ValueError('Invalid feature cutoff')
        work=dict(query,kickoff=cutoff)
        return inc.direct_features(work,self.history,self.opportunity,ARMS[arm][1])

    def training_rows(self,season,cutoff):
        if not finite_clock(cutoff):
            raise ValueError('Invalid training cutoff')
        return [r for r in self.rows if r['physical_participation'] and r['target_parity']
                and r['season']>=season-1 and r['available']<cutoff]

    def feature_order(self,base_order,arm):
        if arm not in ARMS or ARMS[arm][0]!=self.policy_id:
            raise ValueError('Arm/information policy mismatch')
        return inc.feature_order(base_order,ARMS[arm][1])

    def admitted_sources(self,query):
        cutoff=query.get('cutoff',query['kickoff'])
        return dict(policy_id=self.policy_id,strict_cutoff=cutoff,
            latest_training_or_feature_available=max((r['available'] for r in self.rows if r['available']<cutoff),default=None),
            own_games=[r['game_id'] for r in self.history.player_rows(query['player_id'],cutoff)],
            defense_games=[r['game_id'] for r in self.history.group_rows(query['opponent'],cutoff,True)],
            offense_opportunity_games=[r['game_id'] for r in self.opportunity.rows(cutoff,team=query['team'])],
            current_role='NO_NEW_ROLE_INFORMATION_ADDED',
            historical_vintage='CURRENT_REVISED_RECONSTRUCTION_NOT_AUTHENTICATED')
