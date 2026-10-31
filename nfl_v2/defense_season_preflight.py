"""Older-season D1/D2 metadata planner and tested feature adapter, no fit action.

The frozen2026 runners remain untouched. This module cannot load NFL rows,
models, predictions or labels and exposes no run/fit/predict CLI operation.
"""
from __future__ import annotations
from .qualified_defense import QualifiedDefenseHistory
from .scheduled_defense import ScheduledQualifiedDefenseHistory

VERSION='v2-I-older-season-defense-readiness-v1'
OBSERVED='v2-qualified-position-defense-information-wave-v1'
SCHEDULED='v2-scheduled-team-game-defense-alternative-v3'

def validate_year(year):
    if isinstance(year,bool)or year not in(2022,2023,2024,2025):
        raise ValueError('one explicitly registered older season2022-2025 required')
    return year

def policies(year):
    """Reuse the completed seasonal runner's history definitions verbatim."""
    validate_year(year)
    from .seasonal_rolling_v2 import policies as existing
    return existing(year)

def procedure(window,group,strict):
    if window not in('observed','scheduled')or group not in('D1','D2'):
        raise ValueError('exact registered window and information group required')
    return (OBSERVED if window=='observed'else SCHEDULED)+':'+group+(':strict-current-inputs'if strict else':common-feature-memory')

def logical_grid(year,targets,weeks=range(1,19),windows=('observed','scheduled')):
    pp=policies(year);out=[]
    for window in windows:
      for week in weeks:
       if isinstance(week,bool)or not 1<=week<=18:raise ValueError('REG week1-18 required')
       for target in targets:
        for group in('D1','D2'):
         for policy,(arm,fit_floor,feature_floor)in pp.items():
          alias=next(p for p,v in pp.items()if v[1:]==(fit_floor,feature_floor))
          out.append(dict(season=year,week=week,target=target,window=window,information_group=group,policy_id=policy,history_regime=arm,fit_floor=fit_floor,feature_floor=feature_floor,
            fit_alias_policy=alias,procedure_id=procedure(window,group,policy=='H-CURRENT-STRICT'),
            output_products=['event_probability']if target=='anytime_td'else['mean','lower_median'],
            state='FIT_REQUIRED_RUNNER_INTEGRATION_AND_RECOVERY_GATE',alias_of_unrun_origin=policy!=alias,
            recent2022_status='SOURCE_LIMITED_EXPANDING_FROM2022_PROXY_NOT_PRIOR_YEAR'if year==2022 and arm=='H-RECENT'else None))
    return out

def eligible_training(rows,year,policy,origin):
    """Metadata predicate only; callers supply fixtures or separately admitted rows."""
    validate_year(year);arm,floor,memory=policies(year)[policy]
    if any(r['season']>year or r['season']<2022 for r in rows):
        raise ValueError('no future season or pre2022 source admitted')
    return [r for r in rows if r['season']>=floor and r['available']<origin]

class SeasonBoundDefenseHistory:
    """Reuse exact old feature laws with explicit season-relative memory.

    The scheduled helper permits only2022/2026 floor tokens. For an older strict
    floor, filter both original observations and scheduled games to that floor
    before constructing it, then use2022 as the implementation token. This is
    identical eligibility algebra; no date relabeling or copied feature formula.
    """
    def __init__(self,observations,scheduled_games,*,year,feature_floor,window):
        validate_year(year)
        if feature_floor not in(2022,year):raise ValueError('common2022 or current-year feature memory required')
        if window not in('observed','scheduled'):raise ValueError('registered defense window required')
        observations=list(observations);scheduled_games=list(scheduled_games)
        if any(r['season']>year or r['season']<2022 for r in observations+scheduled_games):
            raise ValueError('source bounded by actual evaluation season; no pre2022')
        self.floor,self.window=feature_floor,window
        obs=[r for r in observations if r['season']>=feature_floor]
        games=[r for r in scheduled_games if r['season']>=feature_floor]
        self.inner=QualifiedDefenseHistory(obs,kappa=20.)if window=='observed'else ScheduledQualifiedDefenseHistory(obs,games,kappa=20.)

    def at(self,defense,position,target,cutoff):
        values,audit=self.inner.at(defense,position,target,cutoff,feature_floor=2022)
        return values,dict(audit,feature_floor=self.floor,source_filter_floor=self.floor,implementation_floor_token=2022,
          season_adapter=VERSION,window_contract='FOUR_OBSERVED_QUALIFIED_POSITION_GROUPS'if self.window=='observed'else'FOUR_ELIGIBLE_SCHEDULED_REG_TEAM_GAMES')
