"""All numeric HGB points receive paired MAE, irrespective of fit objective."""
import argparse,collections,csv,gzip,json,math
from pathlib import Path
from statistics import fmean,stdev

p=argparse.ArgumentParser();p.add_argument('--private',type=Path,required=True);p.add_argument('--public',type=Path,required=True);a=p.parse_args()
groups=collections.defaultdict(dict)
for path in (a.private/'prediction-chunks').glob('W0[1-7]-*.json.gz'):
    for r in json.loads(gzip.decompress(path.read_bytes()))['rows']:
        if r['target']=='anytime_td' or r['actual'] is None:continue
        key=(r['target'],r['population'],r['objective'],int(r['week']),r['game_id'],r['player_id'])
        if r['history_regime'] in groups[key]:raise AssertionError('duplicate arm')
        groups[key][r['history_regime']]=r
contrasts=collections.defaultdict(list)
for key,arms in groups.items():
    if set(arms)!={'H-CURRENT','H-RECENT','H-MULTI'}:raise AssertionError('missing arm')
    current=arms['H-CURRENT']
    for arm in ('H-RECENT','H-MULTI'):
        other=arms[arm];assert other['actual']==current['actual']
        delta=abs(other['prediction']-other['actual'])-abs(current['prediction']-current['actual'])
        contrasts[key[:3]+(arm+'_minus_H-CURRENT',)].append((key[3],key[4],delta,current['fallback']=='none' and other['fallback']=='none'))
rows=[]
for key,values in sorted(contrasts.items()):
    weeks=collections.defaultdict(list)
    for week,game,delta,learned in values:weeks[week].append(delta)
    wm=[fmean(v) for _,v in sorted(weeks.items())];estimate=fmean(wm);half=2.447*stdev(wm)/math.sqrt(7) if len(wm)==7 else None
    learned=[r[2] for r in values if r[3]]
    rows.append(dict(target=key[0],population=key[1],objective=key[2],comparison=key[3],metric='MAE',paired_rows=len(values),games=len({v[1] for v in values}),weeks=len(wm),micro_loss_difference=fmean(v[2] for v in values),week_balanced_loss_difference=estimate,week_t95_low=estimate-half if half is not None else None,week_t95_high=estimate+half if half is not None else None,learned_only_paired_rows=len(learned),learned_only_micro_difference=fmean(learned) if learned else None,uncertainty='descriptivepostfit7clustersweak;unadjustedselection;notqualification'))
with (a.public/'ALL_NUMERIC_POINT_MAE_HISTORY_PAIRS.csv').open('x',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('Saved',len(rows),'paired MAE contrasts; no fit or model inference.')
