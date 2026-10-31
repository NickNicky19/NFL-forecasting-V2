"""Independent source-to-label and Decimal scoring audit; no primary scorer imports.

Approved original/local source files are required. Only aggregates and opaque
worked examples are written to the public review. No network, fitting or issuance.
"""
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, localcontext
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]


def numeric(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)


def integer(value):
    return numeric(value) and value>=0 and value==int(value)


def time(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    assert result.tzinfo is not None and result.utcoffset() is not None
    return result


def primary(target,position):
    return (position=='QB' if target.startswith('pass_') else position=='RB'
            if target in {'rush_yd','rush_att'} else position in {'RB','WR','TE'})


def actual(target,stats):
    if target=='anytime_td':
        values=[stats[k] for k in ['rush_td','rec_td'] if k in stats]
        if not all(integer(x) for x in values):return None
        if any(x>0 for x in values):return 1
        return 0 if len(values)==2 else None
    if target=='rush_rec_yd':
        values=[stats.get('rush_yd'),stats.get('rec_yd')]
        return sum(values) if all(numeric(x) for x in values) else None
    x=stats.get(target)
    if target in {'pass_td','pass_cmp','pass_att','pass_int','rush_att','rec'}:
        return x if integer(x) else None
    return x if numeric(x) else None


def expected(context,stats,games,conflict=False):
    pid,gid=context['player_id'],context['game_id']
    if conflict or not pid.startswith('sleeper:') or not pid[8:]:return None,'unknown'
    if pid[8:]!=context['sleeper_id'] or not gid.startswith('espn:'):return None,'unknown'
    game=games.get(gid[5:]); p=stats.get(pid[8:])
    if not game or game['state']!='post' or game.get('completed') is not True:return None,'unknown'
    if time(context['kickoff_utc'])!=time(game['kickoff']):return None,'unknown'
    pair=(context['team'],context['opponent'])
    if pair not in [(game['home'],game['away']),(game['away'],game['home'])]:return None,'unknown'
    if not p or (p.get('team'),p.get('opp'))!=pair:return None,'unknown'
    s=p.get('stats',{})
    if not any(integer(s.get(k)) and s[k]>0 for k in ['gp','off_snp']):return None,'unknown'
    return actual(context['target'],s),'played'


def metrics(pairs,target):
    errors=[Decimal(str(p))-Decimal(str(y)) for p,y in pairs]
    absolute=sorted(abs(x) for x in errors);n=Decimal(len(errors))
    def q(num,den):
        rank=Decimal(len(absolute)-1)*Decimal(num)/Decimal(den)
        lo=int(rank);hi=min(lo+1,len(absolute)-1)
        return absolute[lo]+(absolute[hi]-absolute[lo])*(rank-lo)
    r=dict(n=len(errors),mae=sum(absolute)/n,mse=sum(x*x for x in errors)/n,
        bias=sum(errors)/n,p90_abs=q(9,10),p95_abs=q(19,20),max_abs=absolute[-1],
        exact_rate=Decimal(sum(x==0 for x in absolute))/n)
    r['rmse']=r['mse'].sqrt()
    for threshold in [1,5,10]:
        r[f'abs_lt_{threshold}']=Decimal(sum(x<threshold for x in absolute))/n
        r[f'abs_le_{threshold}']=Decimal(sum(x<=threshold for x in absolute))/n
    if target=='anytime_td':
        ps=[Decimal(str(p)) for p,y in pairs];ys=[Decimal(str(y)) for p,y in pairs]
        assert all(0<=p<=1 for p in ps) and all(y in {0,1} for y in ys)
        r['brier']=r['mse'];r['prevalence']=sum(ys)/n
        prob=[p if y else 1-p for p,y in zip(ps,ys)]
        r['log_loss']=sum(-p.ln() if p else Decimal('Infinity') for p in prob)/n
    return r


def check(private):
    files={'forecast':private/'forecast.json.gz','labels':private/'outcomes-week7-later-explicit.json',
        'stats':private/'production-stats-2026-w07.json','schedule':private/'production-week-2026-w07.json'}
    forecasts=json.loads(gzip.decompress(files['forecast'].read_bytes()))['rows']
    labels=json.loads(files['labels'].read_text());stats=json.loads(files['stats'].read_text())
    schedule=json.loads(files['schedule'].read_text());assert schedule['season']==2026 and schedule['week']==7
    games={g['id']:g for g in schedule['games']};assert len(games)==len(schedule['games'])
    assert all(n==1 for n in Counter(t for g in games.values() for t in [g['home'],g['away']]).values())
    identity=lambda r:(r['game_id'],r['player_id'],r['target'])
    lookup={identity(r):r for r in labels};assert len(lookup)==len(labels)
    contexts=defaultdict(list);seen=set();chronology=0
    context_keys=['player_id','sleeper_id','game_id','target','team','opponent','position','kickoff_utc','scoring_id']
    for f in forecasts:
        fk=(f['model_id'],*identity(f));assert fk not in seen;seen.add(fk)
        assert f['season']==2026 and f['week']==7 and f['period']=='full_game'
        assert time(f['feature_cutoff_utc'])<=time(f['issued_at'])<time(f['kickoff_utc']);chronology+=1
        contexts[identity(f)].append({k:f[k] for k in context_keys})
    assert set(contexts)==set(lookup)
    label_checks=0
    for key,views in contexts.items():
        y,state=expected(views[0],stats,games,any(v!=views[0] for v in views))
        row=lookup[key]
        assert row['actual']==y and row['participation_state']==state
        label_checks+=2
        assert time(row['observed_at'])>time(views[0]['kickoff_utc'])
        assert row['source_sha256']==hashlib.sha256(files['stats'].read_bytes()).hexdigest()
        assert row['status_sha256']==hashlib.sha256(files['schedule'].read_bytes()).hexdigest()
    groups=defaultdict(list);rows=defaultdict(dict);scored=0;fallbacks=Counter()
    for f in forecasts:
        label=lookup[identity(f)]
        if label['actual'] is None or label['participation_state']!='played':continue
        y,p=label['actual'],f['mean'];assert numeric(p);scored+=1
        fallbacks[bool(f.get('fallback'))]+=1
        for population in ['all_offered','primary_roles']:
            if population=='primary_roles' and not primary(f['target'],f['position']):continue
            groups[(f['model_id'],f['target'],population)].append((p,y))
        if primary(f['target'],f['position']):
            d=Decimal(str(p))-Decimal(str(y));loss=d*d if f['target']=='anytime_td' else abs(d)
            rows[identity(f)][f['model_id']]=loss
    root=json.loads((ROOT/'reports/week7-label-extension-v1/SCORES.json').read_text())
    rootmap={(r['procedure_id'],r['target'],r['population']):r for r in root}
    assert set(rootmap)==set(groups)
    metric_checks=0;max_delta=0.;summaries=[]
    for key,pairs in sorted(groups.items()):
        mine=metrics(pairs,key[1]);other=rootmap[key]
        for name,value in mine.items():
            delta=abs(float(value)-other[name]);max_delta=max(max_delta,delta)
            assert math.isclose(float(value),other[name],rel_tol=3e-14,abs_tol=3e-12)
            metric_checks+=1
        summaries.append(dict(procedure_id=key[0],target=key[1],population=key[2],
            metrics={k:str(v) for k,v in mine.items()}))
    examples=[];contrasts=defaultdict(list)
    baseline_pairs=0;baseline_identical=0
    for key,methods in sorted(rows.items()):
        if 'lab-v1.1-recent' not in methods:continue
        baseline=methods['lab-v1.1-recent']
        if 'lab-v1.1-pooled' in methods:
            baseline_pairs+=1;baseline_identical+=methods['lab-v1.1-pooled']==baseline
        for method,loss in methods.items():
            if method in {'lab-v1.1-recent','lab-v1.1-pooled'}:continue
            delta=loss-baseline;contrasts[(method,key[2])].append(delta)
            kind='win' if delta<0 else 'loss' if delta>0 else 'tie'
            if kind!='tie' and not any(x['kind']==kind for x in examples):
                examples.append(dict(opaque_id=hashlib.sha256(repr((method,key)).encode()).hexdigest()[:16],
                    target=key[2],procedure_id=method,kind=kind,challenger_loss=str(loss),
                    recent_loss=str(baseline),difference=str(delta)))
    supported=[r for r in labels if r['actual'] is not None]
    target_support={}
    for t in sorted({r['target'] for r in labels}):
        vs=[r['actual'] for r in supported if r['target']==t]
        target_support[t]=dict(n=len(vs),positive=sum(v>0 for v in vs),zero=sum(v==0 for v in vs),
            negative=sum(v<0 for v in vs))
    old=json.loads((private/'outcomes.json').read_text());overlap=Counter();dropped=Counter()
    for row in old:
        later=lookup.get(identity(row))
        if later is None:overlap['old_key_absent_later']+=1
        elif row['actual'] is None and later['actual'] is None:overlap['both_null']+=1
        elif row['actual'] is None:overlap['newly_explicit_on_original_key']+=1
        elif later['actual'] is None:
            overlap['original_explicit_now_null_in_separate_view']+=1;dropped[later['label_reason']]+=1
        elif row['actual']==later['actual']:overlap['same_explicit_actual']+=1
        else:overlap['changed_explicit_actual']+=1
    return dict(status='PASS_NARROW_SOURCE_RECONSTRUCTION_AND_ARITHMETIC',
        source_sha256={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()},
        source_join_field_checks=label_checks,forecast_internal_chronology_checks=chronology,
        original_forecast_rows=len(forecasts),label_opportunities=len(labels),
        explicit_target_outcomes=len(supported),null_target_outcomes=len(labels)-len(supported),
        supported_player_games=len({(r['game_id'],r['player_id']) for r in supported}),
        supported_games=len({r['game_id'] for r in supported}),scored_method_rows=scored,
        scored_fallback_method_rows=fallbacks[True],metric_cells=len(groups),metric_checks=metric_checks,
        max_absolute_metric_difference=max_delta,target_label_support=target_support,
        summaries=summaries,worked_redacted_examples=examples,
        primary_recent_pooled_paired_targets=baseline_pairs,
        primary_recent_pooled_identical_target_losses=baseline_identical,
        original_batch_overlap=dict(overlap),original_explicit_later_null_reasons=dict(dropped),
        paired_challenger_primary=[dict(procedure_id=m,target=t,n=len(ds),mean_loss_minus_recent=str(sum(ds)/Decimal(len(ds))),
            wins=sum(d<0 for d in ds),losses=sum(d>0 for d in ds),ties=sum(d==0 for d in ds))
            for (m,t),ds in sorted(contrasts.items())],
        nfl_fits=0,new_forecasts=0,independently_authenticated_official_truth=False,
        limitations=['Later same-provider normalized labels, not independently authenticated official NFL truth.',
            'Omitted zero/falsey source fields remain null; supported labels select positive production.',
            'All supported anytime-TD labels are positive; no representative probability-skill or calibration claim.',
            'One evaluation week, incomplete original population; this is no full Weeks1-7 tournament or fit-history test.'])


if __name__=='__main__':
    private=Path(sys.argv[1])
    with localcontext() as context:
        context.prec=50
        result=check(private)
    (ROOT/'reports/verification/LABEL_EXTENSION_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','explicit_target_outcomes','supported_player_games','supported_games',
        'scored_method_rows','source_join_field_checks','metric_cells','metric_checks','max_absolute_metric_difference']},indent=2))
