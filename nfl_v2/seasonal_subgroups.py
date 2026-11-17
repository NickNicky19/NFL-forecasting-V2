"""Freeze older-season subgroup membership before seasonal score inspection.

No models or forecast/output values are read. Source target values are consumed
only as earlier timestamp-qualified selector history; historical universe remains
retrospective. Separate saved-row grading can subsequently use these bytes.
"""
from __future__ import annotations
import csv,gzip,json,time
from pathlib import Path
from . import seasonal_rolling as season,empirical_benchmark as emp,pregame_views as football,chart_cohorts as chart
from .shared_subgroups import canonical,sha,write,load,now,VERSION as PARENT
VERSION='v2-seasonal-shared-subgroup-membership-freeze-v1'

def prepare(source_root,season_public_root,season_private_root,public_root,private_root):
 source_root,season_public_root,season_private_root,public_root,private_root=map(Path,(source_root,season_public_root,season_private_root,public_root,private_root))
 if public_root.exists()or private_root.exists():raise ValueError('fresh output required')
 if private_root.resolve().is_relative_to(Path(__file__).resolve().parents[1]):raise ValueError('private memberships outside publicGit required')
 years=[]
 for year in(2025,2024,2023,2022):
  pub=season_public_root/f'season-{year}-v1';priv=season_private_root/f'seasonal-rolling-{year}-v1';p=load(pub/'FROZEN_PROTOCOL.json')
  if p['evaluation_season']!=year or sha(season.__file__)!=p['code_sha256']:raise ValueError('frozen seasonal engine differs')
  if sha(priv/'frozen-queries.json')!=p['frozen_queries_sha256']:raise ValueError('frozen queries differ')
  for b in p['source_ids']:
   if sha(source_root/b['name'])!=b['sha256']:raise ValueError('source differs')
  years.append(dict(season=year,season_protocol_sha256=sha(pub/'FROZEN_PROTOCOL.json'),query_sha256=p['frozen_queries_sha256'],query_cells=p['query_cells'],query_games=p['query_games']))
 public_root.mkdir(parents=True);private_root.mkdir(parents=True)
 p=dict(version=VERSION,state='FROZEN_BEFORE_SEASONAL_SCORE_DECODE',registered_at_utc=now(),code_sha256=sha(__file__),helpers={Path(m.__file__).name:sha(m.__file__)for m in(season,emp,football,chart)},season_bindings=years,source_ids=load(season_public_root/'season-2025-v1/FROZEN_PROTOCOL.json')['source_ids'],membership='Separateperseasonregularweeks1–18includinghistoricalWeek8; samefrozenretrospectivequeryIDs. Rankwithinweek,target,population usinglast3strictlyearlierAVAILABLEplayergameslots; missingconsume window. Commonmembershipacrosscompetitors; tieIDascending.',origin='EarliestREGgameofevaluationseason/week minus90minutes. Availability assumed kickoff+7days strictlyearlier. No sourceyearafterevaluationyear is decoded; expandingfrom2022startupretained.',football='Prior attempts/carries/targets/carries+targets asoriginal11targetcontract; zero/low/middle/high/unknown bands; ranktop10/15/20 anddisjoint1–10/11–15/16–20/remainder.',chart='Prior qualifiedsignedchartpoints meanoverfinite valueswithinlast3slots; missingconsume. Pointscorebandszero/low≤5includingnegative/middle≤15/high>15/unknown, NOTworkload.',eligibility='Current-vintage retrospectiveobservedstatrow/physicalqualification, not exantehistoricalofferedpopulation. Commonolderselector memory prevents purecurrentselectedsystemclaim.',budget=dict(max_seasons=4,wall_seconds=300,max_private_bytes=16777216),models_fit=0,forecast_values_read=0,seasonal_score_values_read=0,week8_2026_outcomes_read=0)
 write(public_root/'FROZEN_PROTOCOL.json',p);return p

def run(source_root,season_public_root,season_private_root,public_root,private_root):
 source_root,season_public_root,season_private_root,public_root,private_root=map(Path,(source_root,season_public_root,season_private_root,public_root,private_root));p=load(public_root/'FROZEN_PROTOCOL.json');start=time.monotonic()
 if p['code_sha256']!=sha(__file__):raise ValueError('cohort engine changed')
 for m in(season,emp,football,chart):
  if p['helpers'][Path(m.__file__).name]!=sha(m.__file__):raise ValueError('selector/source helper changed')
 write(public_root/'EXECUTION_REGISTRATION.json',dict(version=VERSION,actual_started_at_utc=now(),protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),models_fit=0,seasonal_score_values_read=0))
 result=[];private_bytes=0
 for binding in p['season_bindings']:
  year=binding['season'];pub=season_public_root/f'season-{year}-v1';priv=season_private_root/f'seasonal-rolling-{year}-v1';sp=load(pub/'FROZEN_PROTOCOL.json')
  if sha(pub/'FROZEN_PROTOCOL.json')!=binding['season_protocol_sha256']or sha(priv/'frozen-queries.json')!=binding['query_sha256']:raise ValueError('season source protocol/queries changed')
  rows,games,counts=season.load_source(source_root,sp);lookup={(r['game_id'],r['player_id']):r for r in rows};slots=[]
  for sourceyear in range(2022,year+1):
   with(source_root/f'stats_player_week_{sourceyear}.csv').open()as f:
    for raw in csv.DictReader(f):
     q=lookup.get((raw['game_id'],raw['player_id']))
     if q is None:continue
     values={k:emp.numeric(raw[k])if q['played']else None for k in('attempts','carries','targets')}
     if any(v is not None and not emp.valid_count(v)for v in values.values()):raise ValueError('invalid opportunity support')
     slots.append(dict(player_id=q['player_id'],game_id=q['game_id'],available=q['available'],workload=values))
  queries=load(priv/'frozen-queries.json');weeks=sorted({int(q['week'])for q in queries});origins={w:min(g['kickoff']for g in games.values()if g['season']==year and g['week']==w)-5400 for w in weeks}
  fq=[q for q in queries if q['target']!=chart.TARGET];cq=[q for q in queries if q['target']==chart.TARGET]
  fm,fc=football.memberships(fq,football.PriorWorkload(slots),origins)
  scorehistory=chart.ScoreHistory([dict(player_id=r['player_id'],game_id=r['game_id'],available=r['available'],points=r['values'][chart.TARGET]/50 if r['values'][chart.TARGET]is not None else None)for r in rows])
  cm,cc=chart.memberships(cq,scorehistory,origins);members={**fm,**cm}
  if len(members)!=len(queries):raise ValueError('every query requires exactlyone membership')
  body=gzip.compress(canonical([dict(key=k,**v)for k,v in sorted(members.items())]),mtime=0);private_bytes+=len(body)
  if private_bytes>p['budget']['max_private_bytes']or time.monotonic()-start>p['budget']['wall_seconds']:raise RuntimeError('COHORT_BUDGET')
  path=private_root/f'memberships-{year}.json.gz'
  with path.open('xb')as f:f.write(body)
  if path.read_bytes()!=body:raise ValueError('membership readback failed')
  report=dict(season=year,query_cells=len(members),football_query_cells=len(fm),chart_query_cells=len(cm),unique_games=len({k[0]for k in members}),unique_player_games=len({k[:2]for k in members}),weeks=weeks,unranked=sum(m['rank']is None for m in members.values()),unknown_last3_slots=sum(m['history_slots']-m['supported_slots']for m in members.values()),membership_sha256=sha(path),membership_bytes=len(body),football_coverage=fc,chart_coverage=cc,season_protocol_sha256=binding['season_protocol_sha256'],query_sha256=binding['query_sha256'],source_counts=counts)
  write(public_root/f'SEASON_{year}_MEMBERSHIP_RECEIPT.json',report);result.append(report)
 receipt=dict(version=VERSION,state='ALL4SEASONS_COHORT_MEMBERSHIP_FROZEN',completed_at_utc=now(),protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),seasons=[{k:v for k,v in r.items()if k not in('football_coverage','chart_coverage','source_counts')}for r in result],private_new_bytes=private_bytes,new_fits=0,new_forecasts=0,seasonal_score_values_read=0,forecast_values_read=0,week8_2026_outcomes_read=0,wall_seconds=time.monotonic()-start,private_durability='NEW_MEMBERSHIPS_LOCAL_READBACK_PENDING_ROOT_COMPANION_BACKUP')
 write(public_root/'RUN_RECEIPT.json',receipt);return receipt
