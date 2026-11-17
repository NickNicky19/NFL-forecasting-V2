"""Frozen earlier-workload views, separate from retrospective query eligibility.

No fitting, acquisition or selection from realized performance. Membership is
common to competitors; it does not authenticate the historical query universe.
"""
from __future__ import annotations
import bisect
import collections
import csv
import gzip
import hashlib
import json
import math
from datetime import datetime,timezone
from pathlib import Path
from statistics import fmean

from . import empirical_benchmark as emp
from .hgb_control import load_source


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def query_player_key(row):
    if row.get('player_id'):return row['player_id']
    if not row.get('query_id'):raise ValueError('unqualified identity needs original exact query ID')
    return 'UNQUALIFIED_QUERY:'+row['query_id']

def identity(row):return (row['game_id'],query_player_key(row),row['target'],row['population'])


def opportunity(target,values):
    if target.startswith('pass_'):return values.get('attempts')
    if target in {'rush_att','rush_yd'}:return values.get('carries')
    if target in {'rec','rec_yd'}:return values.get('targets')
    if target in {'rush_rec_yd','anytime_td'}:
        a,b=values.get('carries'),values.get('targets')
        return a+b if a is not None and b is not None else None
    raise ValueError('unsupported workload contract')


class PriorWorkload:
    def __init__(self,rows):
        self.rows=collections.defaultdict(list)
        for row in rows:self.rows[row['player_id']].append(row)
        self.times={}
        for pid,items in self.rows.items():
            items.sort(key=lambda r:(r['available'],r['game_id']))
            self.times[pid]=[r['available'] for r in items]

    def at(self,pid,target,cutoff):
        items=self.rows.get(pid,[]);end=bisect.bisect_left(self.times.get(pid,[]),cutoff)
        selected=items[max(0,end-3):end]
        values=[opportunity(target,r['workload']) for r in selected]
        finite=[v for v in values if v is not None]
        return dict(mean=fmean(finite) if finite else None,supported_slots=len(finite),
            history_slots=len(selected),latest_available=max((r['available'] for r in selected),default=None))


def band(target,value):
    if value is None:return 'unknown'
    if value==0:return 'zero'
    if value<0:raise ValueError('negative opportunity')
    cuts=(20,35) if target.startswith('pass_') else (5,12) if target in {'rush_att','rush_yd','rush_rec_yd','anytime_td'} else (3,7)
    return 'low' if value<=cuts[0] else 'middle' if value<=cuts[1] else 'high'


def memberships(queries,history,origins):
    groups=collections.defaultdict(list)
    for q in queries:
        groups[(int(q['week']),q['target'],q['population'])].append(q)
    result={};summary=[]
    for (week,target,population),rows in sorted(groups.items()):
        cutoff=origins[week];by_player={}
        for row in rows:
            pid=query_player_key(row)
            if pid in by_player:raise ValueError('multiple fixed query games for one player/week/target; requires explicit shared ranking')
            by_player[pid]=history.at(pid,target,cutoff)
        ranked=sorted((pid for pid,p in by_player.items() if p['mean'] is not None),key=lambda pid:(-by_player[pid]['mean'],pid))
        ranks={pid:i+1 for i,pid in enumerate(ranked)}
        for q in rows:
            pid=query_player_key(q);rank=ranks.get(pid);profile=by_player[pid];views=['all']
            if rank is None:views.append('unranked')
            else:
                for n in (10,15,20):
                    if rank<=n:views.append('top'+str(n))
                views.append('rank1_10' if rank<=10 else 'rank11_15' if rank<=15 else 'rank16_20' if rank<=20 else 'rank21plus')
            views.append('workload_'+band(target,profile['mean']))
            key=identity(q)
            if key in result:raise ValueError('duplicate fixed cohort identity')
            result[key]=dict(rank=rank,cohorts=views,ranking_cutoff=cutoff,**profile)
        summary.append(dict(week=week,target=target,population=population,query_rows=len(rows),known_workload=len(ranked),
            unranked=len(rows)-len(ranked),membership_sha256=digest([dict(key=identity(q),membership=result[identity(q)]) for q in sorted(rows,key=identity)])))
    return result,summary


def source_history(source_root,protocol):
    """Reuse admitted participation/identity checks; read only W1–7 opportunities."""
    rows,games,counts=load_source(source_root,protocol)
    lookup={(r['game_id'],r['player_id']):r for r in rows}
    output=[]
    for year in range(2022,2027):
        with (Path(source_root)/f'stats_player_week_{year}.csv').open() as f:
            for r in csv.DictReader(f):
                if r['season_type']!='REG' or (year==2026 and int(r['week'])>7):continue
                qualified=lookup.get((r['game_id'],r['player_id']))
                if not qualified:continue
                values={k:emp.numeric(r[k]) if qualified['played'] else None for k in ('attempts','carries','targets')}
                if any(v is not None and not emp.valid_count(v) for v in values.values()):raise ValueError('invalid opportunity support')
                output.append(dict(player_id=r['player_id'],game_id=r['game_id'],available=qualified['available'],workload=values))
    return PriorWorkload(output),games,counts


def normalize(row,family):
    """Explicit adapters preserve objectives; never create missing predictions."""
    r=dict(row);r['week']=int(r['week']);r['season']=int(r.get('season',2026))
    r['procedure_id']=r.get('procedure_id') or ('empirical-player-history-control-v1' if family=='empirical' else 'hgb-direct-history-controls-v1:'+r['objective'])
    r['product_id']=r.get('product_id') or r.get('product') or r.get('objective')
    r.setdefault('family',family)
    for k in ('prediction','actual'):
        if r.get(k) in (None,''):r[k]=None
        else:
            r[k]=float(r[k])
            if not math.isfinite(r[k]):raise ValueError('nonfinite retained point')
    if r.get('fallback') is None:raise ValueError('explicit fallback state required')
    return r


def read_predictions(kind,path):
    path=Path(path)
    if kind=='hgb':
        for p in sorted(path.glob('W0[1-7]-*.json.gz')):
            with gzip.open(p,'rt') as f:
                packet=json.load(f)
                if not isinstance(packet,dict) or not isinstance(packet.get('rows'),list):raise ValueError('wrapped original HGB row packet required')
                for r in packet['rows']:yield normalize(r,kind)
    elif kind in {'empirical','normalized'}:
        with gzip.open(path,'rt',newline='') as f:
            for r in csv.DictReader(f):
                if str(r['season'])=='2026' and int(r['week'])<=7:yield normalize(r,kind)
    else:raise ValueError('unknown explicit prediction adapter')


def evaluate(records,membership,protocol_sha):
    records=list(records);seen=set();eligible=collections.defaultdict(dict)
    for r in records:
        rid=(r['procedure_id'],r['product_id'],r['history_regime'],identity(r))
        if rid in seen:raise ValueError('duplicate retained forecast view')
        seen.add(rid)
        if identity(r) not in membership:raise ValueError('forecast not in frozen membership')
        eligible[(r['procedure_id'],r['product_id'],r['target'],r['population'])].setdefault(r['history_regime'],set())
        if r['fallback']=='none' and r['prediction'] is not None and r['actual'] is not None:
            eligible[(r['procedure_id'],r['product_id'],r['target'],r['population'])][r['history_regime']].add(identity(r))
    overlaps={};competitor_sets=collections.defaultdict(list)
    for key,arms in eligible.items():
        core=('H-CURRENT','H-RECENT','H-MULTI')
        overlaps[key]=set.intersection(*(arms.get(a,set()) for a in core))
        for values in arms.values():competitor_sets[(key[2],key[3])].append(values)
    shared={key:set.intersection(*sets) for key,sets in competitor_sets.items()}
    groups=collections.defaultdict(list)
    for r in records:
        m=membership[identity(r)]
        views=['full_system']
        if r['fallback']=='none':views.append('own_learned_only')
        key=(r['procedure_id'],r['product_id'],r['target'],r['population'])
        if identity(r) in overlaps[key]:views.append('three_history_learned_overlap')
        if identity(r) in shared[(r['target'],r['population'])]:views.append('all_competitor_learned_overlap')
        for cohort in m['cohorts']:
            for view in views:groups[(r['procedure_id'],r['product_id'],r['target'],r['population'],r['history_regime'],cohort,view)].append(r)
    output=[]
    for dims,rows in sorted(groups.items()):
        proc,product,target,pop,arm,cohort,view=dims;metric=emp.Metrics()
        for r in rows:
            if r['prediction'] is not None:metric.add(r['prediction'],r['actual'],r['fallback'],target)
        result=metric.result();scored=[r for r in rows if r['prediction'] is not None and r['actual'] is not None]
        loss_by_game=collections.defaultdict(list)
        for r in scored:loss_by_game[r['game_id']].append((r['prediction']-r['actual'])**2 if target=='anytime_td' else abs(r['prediction']-r['actual']))
        n=len(scored);g=len(loss_by_game);mean=fmean(x for xs in loss_by_game.values() for x in xs) if n else None
        game_se=(math.sqrt(g/(g-1)*sum((sum(xs)-len(xs)*mean)**2 for xs in loss_by_game.values())/n**2) if g>=8 else None)
        out=dict(record_id='COHORT-'+digest(dims)[:24],procedure_id=proc,procedure_family_id=rows[0]['family'],product_id=product,target=target,population=pop,
            history_regime=arm,cohort_id=cohort,fallback_view=view,season=2026,week='ALL',
            evaluation_seasons=[2026],evaluation_weeks=sorted({r['week'] for r in rows}),
            evaluation_panel_id='v2-fixed-retrospective-query-prior-workload-20261030-v1',record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',
            evidence='NEW_EXPERIMENT',n=n,unique_games=g,forecast_rows=len(rows),fallback_rows=sum(r['fallback']!='none' for r in rows),
            scored_fallback_rows=sum(r['fallback']!='none' for r in scored),
            cohort_membership_sha256=digest(sorted(identity(r) for r in rows)),scored_membership_sha256=digest(sorted(identity(r) for r in scored)),
            cohort_protocol_sha256=protocol_sha,cohort_limit='earlier-feature-defined membership within retrospective fixed stat-row query universe; not authenticated exante offers/starters',
            uncertainty=dict(week_clusters=len({r['week'] for r in scored}),week_interval=None,reason='fewer than8 current-season week clusters',game_cluster_sensitivity_se=game_se,game_cluster_sensitivity_only=True),
            **{k:v for k,v in result.items() if k not in {'scored_n','forecast_queries'}})
        if result.get('infinite_log_losses'):out['log_loss']='Infinity'
        output.append(out)
    return output
