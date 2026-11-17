#!/usr/bin/env python3
"""Read retained source-bound chunks only; no model or future-label acquisition."""
import argparse,collections,csv,gzip,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from nfl_v2.shadow_grading import canonical,digest


def load(root,descriptor):
    blob=(root/descriptor['name']).read_bytes();body=gzip.decompress(blob)
    if len(blob)!=descriptor['bytes']or digest(blob)!=descriptor['sha256']or digest(body)!=descriptor['uncompressed_sha256']:raise ValueError('retainedbyteshash mismatch')
    return json.loads(body)['rows']


def key(r):return tuple(r[k]for k in('game_id','player_id','target','population'))


def compare(new_public,new_private,old_public,old_private):
    new_public,new_private,old_public,old_private=map(Path,(new_public,new_private,old_public,old_private))
    grouped=collections.defaultdict(list);future=[];read_receipts=[]
    for path in sorted(new_public.glob('W*-FORECAST.json')):
        receipt=json.loads(path.read_bytes());rows=load(new_private,receipt['packet'])
        if path.name.startswith('W08'):future.extend(rows);continue
        if not rows:continue
        sample=rows[0];oldarm=sample['history_regime'];oldroot=f"W{int(sample['week']):02}-{sample['target']}-{oldarm}-"
        # STRICT is a full feature-policy comparison against commoncurrent;
        # it is never called an isolated fit-window or pure role-only effect.
        for oldobjective in('absolute_error_point','squared_error_mean'):
            oldreceipt=json.loads((old_public/(oldroot+oldobjective+'-FORECAST.json')).read_bytes())
            oldrows=load(old_private,oldreceipt['packet']);mapping={key(r):r for r in oldrows}
            if len(mapping)!=len(oldrows):raise ValueError('duplicateoldidentity')
            for r in rows:
                other=mapping.get(key(r))
                if other is None or other['position']!=r['position']or other['actual']!=r['actual']:raise ValueError('pairedcohort/labelmismatch')
                if r['actual']is None or r['prediction']is None or other['prediction']is None:continue
                grouped[(r['procedure_family_id'],r['policy_id'],r['target'],r['population'],oldobjective)].append((r,other))
        read_receipts.append(dict(name=path.name,sha256=digest(path.read_bytes()),chunk_sha256=receipt['packet']['sha256']))
    pairs=[]
    for(family,policy,target,population,oldobjective),rows in sorted(grouped.items()):
        losses=[abs(r['prediction']-r['actual'])for r,o in rows];old=[abs(o['prediction']-o['actual'])for r,o in rows]
        diffs=[a-b for a,b in zip(losses,old)];newmse=sum((r['prediction']-r['actual'])**2 for r,o in rows)/len(rows);oldmse=sum((o['prediction']-o['actual'])**2 for r,o in rows)/len(rows)
        cohort=digest(canonical(sorted([dict(game_id=r['game_id'],player_id=r['player_id'],target=r['target'],population=r['population'])for r,o in rows],key=lambda r:(r['game_id'],r['player_id']))))
        pairs.append(dict(family=family,policy_id=policy,target=target,population=population,old_objective=oldobjective,n=len(rows),unique_games=len({r['game_id']for r,o in rows}),new_mae=sum(losses)/len(rows),old_mae=sum(old)/len(rows),paired_mae_difference=sum(diffs)/len(rows),new_mse=newmse,old_mse=oldmse,new_rmse=math.sqrt(newmse),old_rmse=math.sqrt(oldmse),row_wins=sum(d<0 for d in diffs),row_losses=sum(d>0 for d in diffs),row_ties=sum(d==0 for d in diffs),scored_cohort_sha256=cohort,interpretation='completeinformationpolicychange'if policy.endswith('STRICT')else'trainingrolesonly'if'rush-att-qb-rb'in family else'objectiveandregisteredfallbackchange'))
    future_summary=[]
    fg=collections.defaultdict(list)
    for r in future:
        if r['actual']is not None:raise ValueError('futureactualmustremainnull')
        fg[(r['procedure_family_id'],r['policy_id'],r['target'])].append(r)
    for(family,policy,target),rows in sorted(fg.items()):
        issued=[r for r in rows if r['prediction']is not None]
        future_summary.append(dict(family=family,policy_id=policy,target=target,query_rows=len(rows),issued=len(issued),abstentions=len(rows)-len(issued),zeros=sum(r['prediction']==0 for r in issued),min_prediction=min((r['prediction']for r in issued),default=None),max_prediction=max((r['prediction']for r in issued),default=None),actual_labels=0))
    result=dict(version='v2-count-ablation-same-historical-query-report-v1',source_receipts=read_receipts,paired_results=pairs,future_forecast_shape_only=future_summary,new_fits_in_report=0,new_forecasts_in_report=0,week8_outcomes_read=0,limits='Exposed2026W1-W7current-vintage participant diagnostic; pairedloss is descriptive, no selection/out-of-time or significance claim. Future newasof crosses NECHIavailability boundary, so old versus newfuturepointshape is not pure trainingrole effect.')
    result['correction']='V2 fixes draftV1 population grouping from first chunk row to each actual row; original native rows and canonicalSCORES were correct and unchanged'
    with(new_public/'PAIRED_OLD_CONTROL_COMPARISON_V2.json').open('xb')as h:h.write(canonical(result))
    with(new_public/'PAIRED_OLD_CONTROL_COMPARISON_V2.csv').open('x',newline='')as h:
        w=csv.DictWriter(h,fieldnames=list(pairs[0]));w.writeheader();w.writerows(pairs)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for a in('new-public','new-private','old-public','old-private'):p.add_argument('--'+a,type=Path,required=True)
    r=compare(**vars(p.parse_args()));print(json.dumps(dict(paired_views=len(r['paired_results']),future_views=len(r['future_forecast_shape_only']),new_fits=0,new_forecasts=0,week8_outcomes_read=0)))
