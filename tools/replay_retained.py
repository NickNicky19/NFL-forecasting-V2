#!/usr/bin/env python3
"""Replay only retained rows. Use --private-dir outside the public repository."""
import argparse, collections, csv, gzip, hashlib, json, math, pathlib, sys, time
from datetime import datetime
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from nfl_v2.scoring import point_metrics, valid_actual, finite

def dump(path,obj):
    path.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')

def csvwrite(path,rows):
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)

def dt(s):
    return datetime.fromisoformat(s.replace('Z','+00:00'))

def role(target,position):
    if target.startswith('pass_'): return position=='QB'
    if target in ('rush_yd','rush_att'): return position=='RB'
    return position in ('RB','WR','TE')

def replay(private,output):
    started=time.monotonic(); cpu=time.process_time()
    raw=(private/'forecast.json.gz').read_bytes()
    forecasts=json.loads(gzip.decompress(raw))['rows']
    outcomes=json.loads((private/'outcomes.json').read_text())
    bykey={}; duplicate_outcomes=0
    for o in outcomes:
        k=(o['game_id'],o['player_id'],o['target'])
        if k in bykey:
            duplicate_outcomes+=1
            # Do not infer revisions from observed-at; fail safely rather than overwrite.
            if o!=bykey[k]: raise ValueError('conflicting outcomes need revision adjudication')
        bykey[k]=o
    seen=set(); cells=collections.defaultdict(list); coverage=collections.defaultdict(collections.Counter)
    chronology=collections.Counter(); private_scored=[]
    for f in forecasts:
        k=(f['game_id'],f['player_id'],f['target']); fk=(f['model_id'],)+k
        if fk in seen: raise ValueError('duplicate forecast key')
        seen.add(fk)
        ok=dt(f['feature_cutoff_utc'])<=dt(f['issued_at'])<dt(f['kickoff_utc'])
        chronology['valid' if ok else 'invalid']+=1
        o=bykey.get(k)
        reason=('not_in_retained_outcome_batch' if o is None else
                'participation_'+o.get('participation_state','unknown') if o.get('participation_state')!='played' else
                'missing_or_invalid_actual' if not valid_actual(f['target'],o.get('actual')) else
                'invalid_forecast' if not finite(f.get('mean')) else
                'invalid_chronology' if not ok else 'scored')
        for population in ('all_offered','primary_roles'):
            if population=='primary_roles' and not role(f['target'],f['position']): continue
            ck=(f['model_id'],f['target'],population)
            coverage[ck]['forecast_rows']+=1;coverage[ck][reason]+=1
            coverage[ck]['fallback_rows']+=bool(f.get('fallback'))
            if reason=='scored':
                cells[ck].append((f,o))
                coverage[ck]['scored_fallback_rows']+=bool(f.get('fallback'))
        if reason=='scored':
            private_scored.append(dict(procedure_id=f['model_id'],game_id=f['game_id'],player_id=f['player_id'],target=f['target'],season=f['season'],week=f['week'],prediction=f['mean'],actual=o['actual'],error=f['mean']-o['actual'],fallback=f.get('fallback'),position=f['position'],issued_at=f['issued_at']))
    results=[]
    for ck,c in sorted(coverage.items()):
        rows=cells[ck]; metrics=point_metrics([f['mean'] for f,o in rows],[o['actual'] for f,o in rows],ck[1])
        r=dict(procedure_id=ck[0],target=ck[1],population=ck[2],product_id='conditional_played_mean' if ck[1]!='anytime_td' else 'event_probability',evaluation_panel_id='retained-2026-W7-one-game-explicit-outcomes-v1',evidence='REPRODUCED_FROM_DATA',history_regime='LEGACY_NOT_H_CLASSIFIED',season=2026,week=7,unique_games=len({f['game_id'] for f,o in rows}),unique_players=len({f['player_id'] for f,o in rows}),**metrics,**c)
        r['primary_metric']='brier' if ck[1]=='anytime_td' else 'mae';r['primary_loss']=r.get(r['primary_metric']);r['uncertainty']='insufficient_clusters_one_game_one_week';results.append(r)
    original=json.loads((private/'original-scorecard.json').read_text())
    checks=[]
    originals=original['scorecard']['categories']
    for old in originals:
        matches=[x for x in results if x['procedure_id']==old['model'] and x['target']==old['target'] and x['population']=='all_offered']
        if not matches: continue
        new=matches[0]
        for a,b in [('mae','mae'),('rmse','rmse'),('bias','bias'),('p95_abs','p95_absolute_error'),('n','scored_rows')]:
            delta=abs(new[a]-old[b]) if new[a] is not None and old[b] is not None else None
            checks.append(dict(procedure_id=old['model'],target=old['target'],metric=a,delta=delta,passed=delta is not None and delta<1e-10))
        if old['target']=='anytime_td':
            checks.append(dict(procedure_id=old['model'],target=old['target'],metric='brier',delta=abs(new['brier']-old['bernoulli']['brier']),passed=abs(new['brier']-old['bernoulli']['brier'])<1e-10))
    paired=[]
    for target in sorted({f['target'] for f in forecasts}):
        for population in ('all_offered','primary_roles'):
            maps=[]
            for method in ('lab-v1.1-recent','lab-v1.1-pooled'):
                maps.append({(f['game_id'],f['player_id'],f['target']):(f,o) for f,o in cells[(method,target,population)]})
            common=sorted(maps[0].keys()&maps[1].keys())
            a=[];b=[];learned=[]
            for k in common:
                f,o=maps[0][k];g,other=maps[1][k]
                if o['actual']!=other['actual']: raise ValueError('unpaired labels')
                power=2 if target=='anytime_td' else 1
                a.append(abs(f['mean']-o['actual'])**power);b.append(abs(g['mean']-o['actual'])**power)
                if not f.get('fallback') and not g.get('fallback'): learned.append(len(a)-1)
            paired.append(dict(target=target,population=population,n=len(common),games=len({k[0] for k in common}),metric='brier' if target=='anytime_td' else 'mae',recent_loss=sum(a)/len(a) if a else None,pooled_loss=sum(b)/len(b) if b else None,delta_pooled_minus_recent=sum(y-x for x,y in zip(a,b))/len(a) if a else None,learned_only_n=len(learned),learned_delta=sum(b[i]-a[i] for i in learned)/len(learned) if learned else None,uncertainty='insufficient_clusters',history_question='NOT_ANSWERED_distinct_legacy_recipes_not_fixed_learner_fit_windows'))
    output.mkdir(parents=True,exist_ok=True)
    dump(output/'REPLAY_SCORES.json',results);csvwrite(output/'REPLAY_SCORES.csv',results)
    dump(output/'REPRODUCTION_CHECKS.json',checks);csvwrite(output/'BASELINE_PAIRED.csv',paired)
    csvwrite(private/'scored-player-games.csv',private_scored)
    dump(output/'REPLAY_RECEIPT.json',dict(forecast_rows=len(forecasts),forecast_games=len({f['game_id'] for f in forecasts}),forecast_players=len({f['player_id'] for f in forecasts}),outcome_rows=len(outcomes),outcome_games=len({o['game_id'] for o in outcomes}),supported_unique_player_game_target=len({(o['game_id'],o['player_id'],o['target']) for o in outcomes if o.get('participation_state')=='played' and valid_actual(o['target'],o.get('actual'))}),supported_unique_player_games=len({(o['game_id'],o['player_id']) for o in outcomes if o.get('participation_state')=='played' and valid_actual(o['target'],o.get('actual'))}),scored_method_rows=len(private_scored),chronology=dict(chronology),duplicate_outcomes=duplicate_outcomes,new_fits=0,new_forecasts=0,reproduction_checks=len(checks),reproduction_passed=sum(x['passed'] for x in checks),reproduced_original_cells=len({(x['procedure_id'],x['target']) for x in checks}),original_cells=len(originals),source_sha256=hashlib.sha256(raw).hexdigest(),wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,source_truth='not independently reobtained; arithmetic and internal chronology only',private_storage='local ephemeral; original bytes remain upstream pinned; no approved durable companion store bound'))
    print(json.dumps({'cells':len(results),'checks':len(checks),'passed':sum(x['passed'] for x in checks),'scored_rows':len(private_scored)}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-dir',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args();replay(a.private_dir,a.output)
