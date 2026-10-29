"""Post-fit paired reporting from immutable rows, with no fit or model inference."""
from __future__ import annotations
import argparse, collections, csv, gzip, hashlib, json, math
from pathlib import Path
from statistics import fmean, stdev


def write(path, rows):
    with path.open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows)


p=argparse.ArgumentParser();p.add_argument('--private',type=Path,required=True);p.add_argument('--public',type=Path,required=True);p.add_argument('--empirical',type=Path,required=True);a=p.parse_args()
records=[]
for path in sorted((a.private/'prediction-chunks').glob('W0[1-7]-*.json.gz')):
    records.extend(json.loads(gzip.decompress(path.read_bytes()))['rows'])
groups=collections.defaultdict(dict)
for r in records:
    key=(r['target'],r['population'],r['objective'],int(r['week']),r['game_id'],r['player_id'])
    if r['history_regime'] in groups[key]:raise AssertionError('duplicate forecast arm')
    groups[key][r['history_regime']]=r
base={}
with gzip.open(a.empirical,'rt',newline='') as f:
    for r in csv.DictReader(f):
        if r['season']!='2026':continue
        key=(r['target'],r['population'],r['history_regime'],r['product'],int(r['week']),r['game_id'],r['player_id'])
        if key in base:raise AssertionError('duplicate baseline')
        base[key]=None if r['actual']=='' else (float(r['prediction']),float(r['actual']))
contrasts=collections.defaultdict(list);game_counts=collections.defaultdict(set)
for key,arms in groups.items():
    if set(arms)!={'H-CURRENT','H-RECENT','H-MULTI'}:raise AssertionError('missing history arm')
    target,population,objective,week,game,player=key
    score='Brier' if target=='anytime_td' else 'MSE' if objective=='squared_error_mean' else 'MAE'
    def loss(pred,actual):return (pred-actual)**2 if score in ('Brier','MSE') else abs(pred-actual)
    current=arms['H-CURRENT']
    if current['actual'] is None:continue
    for arm in ('H-RECENT','H-MULTI'):
        r=arms[arm]
        if r['actual']!=current['actual']:raise AssertionError('unmatched labels')
        delta=loss(r['prediction'],r['actual'])-loss(current['prediction'],current['actual'])
        ckey=(target,population,objective,arm+'_minus_H-CURRENT',score)
        contrasts[ckey].append((week,game,delta,r['fallback']=='none' and current['fallback']=='none'))
    product='event_probability' if target=='anytime_td' else 'lower_median' if objective=='absolute_error_point' else 'empirical_mean'
    for arm,r in arms.items():
        b=base[(target,population,arm,product,week,game,player)]
        if b is None or b[1]!=r['actual']:raise AssertionError('baseline label mismatch')
        ckey=(target,population,objective,'HGB_minus_empirical_'+arm,score)
        contrasts[ckey].append((week,game,loss(r['prediction'],r['actual'])-loss(*b),r['fallback']=='none'))
rows=[]
for key,values in sorted(contrasts.items()):
    weeks=collections.defaultdict(list)
    for week,game,delta,learned in values:weeks[week].append(delta)
    wm=[fmean(v) for _,v in sorted(weeks.items())];estimate=fmean(wm)
    half=2.447*stdev(wm)/math.sqrt(7) if len(wm)==7 else None
    learned=[v[2] for v in values if v[3]]
    rows.append(dict(target=key[0],population=key[1],objective=key[2],comparison=key[3],score=key[4],paired_rows=len(values),games=len({v[1] for v in values}),weeks=len(wm),micro_loss_difference=fmean(v[2] for v in values),week_balanced_loss_difference=estimate,week_t95_low=estimate-half if half is not None else None,week_t95_high=estimate+half if half is not None else None,learned_only_paired_rows=len(learned),learned_only_micro_difference=fmean(learned) if learned else None,uncertainty='descriptivepostfitsample;t7clustersweak;unadjustedresearchselection;notqualification'))
write(a.public/'PAIRED_HISTORY_AND_BASELINE.csv',rows)
scores=list(csv.DictReader((a.public/'SCORES.csv').open()));summary=[]
for target in ('pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','anytime_td'):
    eligible=[r for r in scores if r['target']==target and r['population']=='primary' and r['week']=='ALL' and r['position']=='ALL']
    metric='brier' if target=='anytime_td' else 'mae';best=min(eligible,key=lambda r:float(r[metric]))
    summary.append(dict(target=target,best_observed_HGB_history=best['history_regime'],objective=best['objective'],ranking_metric=metric,loss=float(best[metric]),scored_rows=int(best['scored_n']),fallback_rows=int(best['fallback_n']),bias=float(best['bias']),p95_abs=float(best['p95_abs']),selection='exposedminimumamongnewHGBviews;notafrozenpre2026selector'))
write(a.public/'PRIMARY_HGB_DISPLAY_SUMMARY.csv',summary)
fits=[json.loads(x.read_text()) for x in a.public.glob('*-FIT.json')]
checks={'fit_cutoff_checks':0,'query_feature_cutoff_checks':0,'fallback_cutoff_checks':0,'paired_label_checks':len(groups),'fit_failure_count':sum(x['state']=='FIT_FAILED_FALLBACK' for x in fits),'new_fits_or_inference':0}
for r in fits:
    cutoff=__import__('datetime').datetime.fromisoformat(r['fit_cutoff_utc']).timestamp()
    for field in ('latest_training_label_available','latest_training_feature_available'):
        if r[field] is not None:assert r[field]<cutoff;checks['fit_cutoff_checks']+=1
for r in records:
    if r['latest_feature_available'] is not None:assert r['latest_feature_available']<r['cutoff'];checks['query_feature_cutoff_checks']+=1
    if r['latest_fallback_available'] is not None:assert r['latest_fallback_available']<r['cutoff'];checks['fallback_cutoff_checks']+=1
with (a.public/'POSTRUN_REPORT_CHECKS.json').open('x') as f:json.dump(checks,f,indent=2)
print(json.dumps({'paired_contrasts':len(rows),'historical_prediction_views':len(records),'primary_summary':summary,'checks':checks},indent=2))
