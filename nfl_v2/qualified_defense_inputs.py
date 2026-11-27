"""Source-bound qualified-position opponent information for a NEW ablation.

No source is acquired; callers supply the previously admitted immutable files.
This helper does not fit, infer, score, or consume 2026Week8 outcomes.
"""
from __future__ import annotations
import collections,csv,json,math
from pathlib import Path
import numpy as np
from . import hgb_control as source,qualified_defense as defense,week8_shadow as identity_adapter
CHART='nick-chart-ppr-v1'
GROUPS={'D1':defense.RAW_COLUMNS,'D2':defense.RATE_COLUMNS}

def attach_context(rows,games,source_root):
 lookup={(r['game_id'],r['player_id']):r for r in rows};seen=set()
 for year in range(2022,2027):
  with(Path(source_root)/f'stats_player_week_{year}.csv').open()as f:
   for raw in csv.DictReader(f):
    # No current-season Week8 (or later) values are decoded.
    if raw['season_type']!='REG'or(year==2026 and int(raw['week'])>7):continue
    key=raw['game_id'],raw['player_id'];r=lookup.get(key)
    if r is None:continue
    if key in seen:raise ValueError('duplicate qualified context')
    seen.add(key);g=games[r['game_id']]
    if(raw['team'],raw['opponent_team'])not in((g['home'],g['away']),(g['away'],g['home'])):raise ValueError('exact historical source/schedule team binding required')
    if raw['position']!=r['position']:raise ValueError('historical position mismatch')
    r['defense']=raw['opponent_team'];r['team']=raw['team'];r['workload']={k:source.empirical.numeric(raw[k])if r['played']else None for k in('attempts','carries','targets')}
    if any(v is not None and not source.empirical.valid_count(v)for v in r['workload'].values()):raise ValueError('invalid explicit opportunity denominator')
 if seen!=set(lookup):raise ValueError('missing historical context row')
 return rows

def build_history(rows,targets):
 groups=collections.defaultdict(list)
 for r in rows:groups[r['game_id'],r['defense'],r['position']].append(r)
 observations=[defense.game_observation(rs,target)for rs in groups.values()for target in targets]
 return defense.QualifiedDefenseHistory(observations,kappa=20.)

def augment(own,history,q,feature_floor,group):
 own=np.asarray(own,dtype=float)
 if own.shape!=(20,):raise ValueError('unchanged full20 own-player raw features required')
 if group not in GROUPS:raise ValueError('unregistered information group')
 if q.get('blocked_reason')or q.get('position')not in source.POSITIONS:
  # These values are retained only to preserve abstention coverage. Never infer.
  return np.concatenate((own,np.full(len(GROUPS[group]),np.nan))),dict(state='BLOCKED_QUERY_NO_CONTEXT_LOOKUP',latest_local_available=None,latest_league_available=None)
 if not q.get('defense'):raise ValueError('exact qualified opponent context required')
 features,audit=history.at(q['defense'],q['position'],q['target'],q['cutoff'],feature_floor=feature_floor)
 extra=np.asarray([math.nan if features[c]is None else features[c]for c in GROUPS[group]],dtype=float)
 return np.concatenate((own,extra)),dict(state='QUALIFIED_POSITION_POPULATION',columns=list(GROUPS[group]),values=features,**audit)

def attach_future_context(queries,games,board):
 if(board.get('season'),board.get('week'))!=(2026,8):raise ValueError('wrong frozen board season/week')
 rows=collections.defaultdict(list)
 for r in board['players']:rows[str(r['id']),str(r['game_id'])].append(r)
 result=[]
 for raw in queries:
  q=dict(raw);g=games[q['game_id']]
  if(g['season'],g['week'])!=(2026,8):raise ValueError('wrong scheduled future game')
  found=rows[str(q.get('sleeper_id')),str(g['espn'])]
  reason=q.get('blocked_reason')
  if not reason:
   if len(found)!=1:raise ValueError('admitted query missing exact frozen board context')
   b=found[0];team=identity_adapter.TEAM_ALIASES.get(b['team'],b['team']);opp=identity_adapter.TEAM_ALIASES.get(b['opp'],b['opp'])
   if(team,opp)not in((g['home'],g['away']),(g['away'],g['home']))or b['pos']!=q['position']:raise ValueError('future exact player/position/team/opponent binding failed')
   q.update(team=team,defense=opp)
  else:q.update(team=None,defense=None)
  result.append(q)
 return result
