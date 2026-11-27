"""Independent replay audit of existing diagnostic rows; no model fit or run call."""
from collections import Counter,defaultdict
import csv
from datetime import datetime
from decimal import Decimal,localcontext
import gzip,hashlib,json,math
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check_label_extension import metrics

MAPPING={'pass_yd':'passing_yards','pass_td':'passing_tds','pass_cmp':'completions',
    'pass_att':'attempts','pass_int':'passing_interceptions','rush_yd':'rushing_yards',
    'rush_att':'carries','rec':'receptions','rec_yd':'receiving_yards'}
COUNT_TARGETS={'pass_td','pass_cmp','pass_att','pass_int','rush_att','rec'}
ACTION_COUNTS=('attempts completions carries targets receptions sacks_suffered passing_tds rushing_tds '
    'receiving_tds passing_2pt_conversions rushing_2pt_conversions receiving_2pt_conversions punt_returns '
    'kickoff_returns def_tackles_solo def_tackles_with_assist def_tackle_assists def_sacks def_interceptions '
    'fumble_recovery_own fumble_recovery_opp fg_att pt_att').split()
ACTION_YARDS=('passing_yards rushing_yards receiving_yards sack_yards_lost punt_return_yards kickoff_return_yards '
    'def_interception_yards fumble_recovery_yards_own fumble_recovery_yards_opp misc_yards').split()

def num(x):
    if x in ('',None):return None
    try:x=Decimal(x)
    except Exception:return None
    return x if x.is_finite() else None

def count(x):return x is not None and x>=0 and x==int(x)

def value(target,r):
    if target in MAPPING:
        x=num(r[MAPPING[target]])
        return x if x is not None and (target not in COUNT_TARGETS or count(x)) else None
    a,b=[num(r[k]) for k in (('rushing_yards','receiving_yards') if target=='rush_rec_yd' else ('rushing_tds','receiving_tds'))]
    if target=='rush_rec_yd':return a+b if a is not None and b is not None else None
    if any(x is not None and not count(x) for x in [a,b]):return None
    if any(x is not None and x>0 for x in [a,b]):return Decimal(1)
    return Decimal(0) if a==0 and b==0 else None

def key(r):return r['game_id'],r['player_id'],r['target'],r['population']
def dmetric(pred,actual,target):
    e=Decimal(pred)-Decimal(actual)
    return e*e if target=='anytime_td' else abs(e)

def audit(sources,private,public):
    protocol=json.loads((public/'FROZEN_PROTOCOL.json').read_text())
    receipt=json.loads((public/'RUN_RECEIPT.json').read_text())
    for item in protocol['source_ids']:
        p=sources/item['name'];assert p.stat().st_size==item['bytes']
        assert hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']
    assert hashlib.sha256(private.read_bytes()).hexdigest()==receipt['private_prediction_sha256']
    schedule={}
    with (sources/'games.csv').open() as f:
        for r in csv.DictReader(f):
            if r['game_type']!='REG' or int(r['season']) not in range(2022,2027):continue
            if int(r['season'])==2026 and int(r['week'])>7:continue
            t=datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York'))
            assert r['game_id'] not in schedule
            schedule[r['game_id']]=(int(t.timestamp()),int(r['season']),int(r['week']),r['home_team'],r['away_team'])
    source={};observed=defaultdict(list);raw_2026_participation=Counter()
    for year in range(2022,2027):
        with (sources/f'stats_player_week_{year}.csv').open() as f:
            for r in csv.DictReader(f):
                if r['season_type']!='REG' or int(r['season'])!=year or (year==2026 and int(r['week'])>7):continue
                if r['position'] not in {'QB','RB','WR','TE'}:continue
                # A full GSIS key is used; no names/current-roster identity join.
                if not(r['player_id'].startswith('00-') and len(r['player_id'])==10 and r['player_id'][3:].isdigit()):continue
                g=schedule[r['game_id']];assert (year,int(r['week']))==g[1:3]
                assert (r['team'],r['opponent_team']) in [(g[3],g[4]),(g[4],g[3])]
                played=any(count(num(r[k])) and num(r[k])>0 for k in ACTION_COUNTS) or any(num(r[k]) not in (None,0) for k in ACTION_YARDS)
                if year==2026:raw_2026_participation['played' if played else 'unknown']+=1
                k=(r['game_id'],r['player_id']);assert k not in source
                vals={t:value(t,r) if played else None for t in protocol['targets']}
                source[k]=dict(values=vals,played=played,position=r['position'],season=year,week=int(r['week']),kickoff=g[0])
                for target,y in vals.items():
                    roles=protocol['primary_roles'][target]+protocol['extended_roles'].get(target,[])
                    if y is not None and r['position'] in roles:
                        observed[(target,r['position'])].append((year,g[0]+7*86400,r['game_id'],r['player_id'],y))
    current=[];total=0;all_year_chronology=0
    with gzip.open(private,'rt') as f:
        for r in csv.DictReader(f):
            total+=1
            if r['latest_training_available_epoch_utc']:
                assert int(r['latest_training_available_epoch_utc'])<int(r['cutoff_epoch_utc'])
            assert int(r['cutoff_epoch_utc'])==schedule[r['game_id']][0];all_year_chronology+=1
            if r['season']=='2026':current.append(r)
    assert total==receipt['forecast_rows']
    source_checks=0;explicit=Counter();query_records={};samples={}
    for r in current:
        s=source[(r['game_id'],r['player_id'])];y=s['values'][r['target']]
        assert num(r['actual'])==y;assert r['participation']==('played' if s['played'] else 'unknown')
        source_checks+=2
        assert r['position']==s['position'];assert int(r['week'])==s['week']
        expected_pop='primary' if s['position'] in protocol['primary_roles'][r['target']] else 'extended'
        assert r['population']==expected_pop
        qk=key(r);query_records[qk]=r
        if r['population']=='primary' and r['product'] in {'empirical_mean','event_probability'}:
            sk=(r['week'],r['target'],r['position'],r['fallback'])
            if sk not in samples or hashlib.sha256(repr(qk).encode()).digest()<hashlib.sha256(repr(key(samples[sk])).encode()).digest():samples[sk]=r
    for r in query_records.values():
        y=num(r['actual']);state='missing' if y is None else 'zero' if y==0 else 'positive' if y>0 else 'negative'
        explicit[(r['target'],state)]+=1
    sample_checks=0;sample_records={key(r):r for r in samples.values()};by_q=defaultdict(list)
    for r in current:
        if key(r) in sample_records:by_q[key(r)].append(r)
    for rows in by_q.values():
        for r in rows:
            floor=2026 if r['history_regime']=='H-CURRENT' else 2025 if r['history_regime']=='H-RECENT' else 2022
            candidates=[o for o in observed[(r['target'],r['position'])] if floor<=o[0]<=2026 and o[1]<int(r['cutoff_epoch_utc'])]
            own=[o for o in candidates if o[3]==r['player_id']];chosen=own or candidates
            fallback='none' if own else 'position_empirical' if candidates else 'constant_zero'
            assert r['fallback']==fallback;assert int(r['own_n'])==len(own);assert int(r['used_n'])==len(chosen)
            assert int(r['fit_floor'])==floor and int(r['fit_ceiling'])==2026
            assert all(o[2]!=r['game_id'] for o in chosen)
            latest=max((o[1] for o in chosen),default=None)
            assert (int(r['latest_training_available_epoch_utc']) if r['latest_training_available_epoch_utc'] else None)==latest
            vs=sorted(o[4] for o in chosen)
            predicted=(sum(vs)/Decimal(len(vs)) if r['product']!='lower_median' else vs[(len(vs)-1)//2]) if vs else Decimal(0)
            assert math.isclose(float(predicted),float(r['prediction']),rel_tol=3e-14,abs_tol=3e-12)
            sample_checks+=8
    # Reaggregate every 2026 public view from retained rows with independent arithmetic.
    groups=defaultdict(list)
    for r in current:
        base=(r['target'],r['population'],r['history_regime'],r['product'])
        for ending in [('ALL','ALL','ALL'),(r['week'],'ALL','ALL'),('ALL',r['position'],'ALL'),('ALL','ALL',r['fallback'])]:
            groups[base+ending].append(r)
    with (public/'SEASON_RESULTS_2022_2026.csv').open() as f:published=[r for r in csv.DictReader(f) if r['season']=='2026']
    metric_checks=0;max_delta=0.;summary_counts=Counter()
    for row in published:
        gk=tuple(row[k] for k in ['target','population','history_regime','product','week','position','fallback_view']);rs=groups[gk]
        scored=[(float(r['prediction']),float(r['actual'])) for r in rs if r['actual']!='']
        assert len(rs)==int(row['forecast_queries']);assert len(scored)==int(row['scored_n'])
        assert sum(r['fallback']!='none' for r in rs)==int(row['fallback_n'])
        metric_checks+=3
        if not scored:continue
        ms=metrics(scored,row['target'])
        for name,val in ms.items():
            if name=='n':continue
            if val.is_infinite():assert row[name]=='' and int(row['infinite_log_losses'])>0
            else:
                delta=abs(float(val)-float(row[name]));max_delta=max(max_delta,delta)
                assert math.isclose(float(val),float(row[name]),rel_tol=3e-14,abs_tol=4e-12),(gk,name,val,row[name])
            metric_checks+=1
        summary_counts[row['target']]+=1
    # Common identities, full-system and learned-only history differences.
    paired=defaultdict(dict)
    for r in current:
        if r['population']=='primary' and r['actual']!='':
            pk=(r['target'],r['product'],r['week'],r['game_id'],r['player_id'])
            assert r['history_regime'] not in paired[pk];paired[pk][r['history_regime']]=r
    differences=defaultdict(list);learned=defaultdict(list);weekdiff=defaultdict(lambda:defaultdict(list));examples=[]
    for pk,arms in sorted(paired.items()):
        assert set(arms)=={'H-CURRENT','H-RECENT','H-MULTI'}
        assert len({r['actual'] for r in arms.values()})==1
        baseline=arms['H-CURRENT'];bl=dmetric(baseline['prediction'],baseline['actual'],pk[0])
        for other in ['H-RECENT','H-MULTI']:
            r=arms[other];loss=dmetric(r['prediction'],r['actual'],pk[0]);delta=loss-bl;k=(pk[0],pk[1],other)
            differences[k].append(delta);weekdiff[k][pk[2]].append(delta)
            if baseline['fallback']==r['fallback']=='none':learned[k].append(delta)
            kind='win' if delta<0 else 'loss' if delta>0 else 'tie'
            if kind!='tie' and not any(e['kind']==kind for e in examples):
                examples.append(dict(opaque_id=hashlib.sha256(repr((pk,other)).encode()).hexdigest()[:16],target=pk[0],product=pk[1],history=other,kind=kind,history_loss=str(loss),current_loss=str(bl),difference=str(delta)))
    paired_checks=0
    with (public/'PAIRED_HISTORY_DIFFERENCES.csv').open() as f:
        for row in csv.DictReader(f):
            k=(row['target'],row['product'],row['comparison'].split('_minus_')[0]);ds=differences[k]
            assert int(row['paired_n'])==len(ds);assert int(row['learned_only_paired_n'])==len(learned[k]);paired_checks+=2
            for field,val in [('pooled_mean_loss_difference',sum(ds)/Decimal(len(ds))),
                ('week_balanced_mean_loss_difference',sum(sum(v)/Decimal(len(v)) for v in weekdiff[k].values())/Decimal(len(weekdiff[k])))]:
                assert math.isclose(float(val),float(row[field]),rel_tol=3e-13,abs_tol=4e-12);paired_checks+=1
            if learned[k]:assert math.isclose(float(sum(learned[k])/Decimal(len(learned[k]))),float(row['learned_only_mean_loss_difference']),rel_tol=3e-13,abs_tol=4e-12);paired_checks+=1
    scheduled=Counter(g[2] for g in schedule.values() if g[1]==2026)
    by_week={str(w):dict(scheduled_games=scheduled[w],query_games=len({r['game_id'] for r in current if int(r['week'])==w}),
        forecast_rows=sum(int(r['week'])==w for r in current),target_coverage={t:dict(query_games=len({r['game_id'] for r in current if int(r['week'])==w and r['target']==t and r['population']=='primary'}),scored_games=len({r['game_id'] for r in current if int(r['week'])==w and r['target']==t and r['population']=='primary' and r['actual']!=''})) for t in protocol['targets']}) for w in range(1,8)}
    return dict(status='PASS_RETAINED_DIAGNOSTIC_REPLAY_WITH_COHORT_LIMITS',all_year_forecast_chronology_checks=all_year_chronology,
        checked_2026_forecast_rows=len(current),checked_2026_unique_query_targets=len(query_records),source_actual_and_participation_checks=source_checks,
        sampled_raw_prefix_query_targets=len(sample_records),sampled_raw_prefix_checks=sample_checks,
        checked_2026_summary_views=len(published),metric_checks=metric_checks,max_absolute_metric_difference=max_delta,
        paired_history_checks=paired_checks,paired_history_views=len(differences),weekly_2026_coverage=by_week,
        explicit_label_counts=[dict(target=t,state=s,n=n) for (t,s),n in sorted(explicit.items())],
        source_2026_participation=dict(raw_2026_participation),worked_redacted_history_win_and_loss=examples,
        original_optimization_fits_added=0,new_prediction_run_added=False,
        source_truth='source-byte and mapping verification; no independent official NFL source acquisition',
        limits=['Retrospective observed-stat-row cohort; no exante participation or offered-prop population.',
            'Historical source row positions and current-vintage revisions are not authentic pregame information.',
            'Earlier kickoff+7day is an assumption; no source publication clock authenticated.',
            '2026 Weeks1-7 only; chart labels and full legacy tournament remain uncompleted.'])

if __name__=='__main__':
    with localcontext() as ctx:
        ctx.prec=50
        result=audit(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]))
    (ROOT/'reports/verification/EMPIRICAL_HISTORY_DIAGNOSTIC_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','checked_2026_forecast_rows','checked_2026_summary_views','metric_checks','sampled_raw_prefix_checks','paired_history_checks']},indent=2))
