#!/usr/bin/env python3
"""Export original retained prediction chunks and exact score-date coverage.

No fitting, inference, new source, label acquisition or alteration of old scores.
"""
import argparse,collections,csv,gzip,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from nfl_v2.shadow_grading import canonical,digest


def export(public_root,private_root):
    public_root,private_root=map(Path,(public_root,private_root));rows=[];source_receipts=[]
    for path in sorted(public_root.glob('W*-FORECAST.json')):
        receipt=json.loads(path.read_bytes());d=receipt['packet'];blob=(private_root/d['name']).read_bytes();body=gzip.decompress(blob)
        if digest(blob)!=d['sha256']or digest(body)!=d['uncompressed_sha256']:raise ValueError('originalchunkbyte mismatch')
        rs=json.loads(body)['rows']
        if len(rs)!=receipt['rows']:raise ValueError('chunkcensus mismatch')
        if path.name.startswith('W08')and any(r['actual']is not None for r in rs):raise ValueError('futureactualmustbenull')
        rows.extend(rs);source_receipts.append(dict(receipt_name=path.name,receipt_sha256=digest(path.read_bytes()),chunk_sha256=d['sha256'],rows=len(rs)))
    fields=['procedure_id','procedure_family_id','product_id','game_id','player_id','target','population','position','season','week','history_regime','information_policy','policy_id','feature_floor','prediction','actual','fallback','status','query_id','cutoff','latest_feature_available','issued_at_utc','source_cutoff_utc']
    text=io.StringIO(newline='');w=csv.DictWriter(text,fieldnames=fields);w.writeheader()
    for r in rows:w.writerow({k:r.get(k)for k in fields})
    body=gzip.compress(text.getvalue().encode(),mtime=0);dest=private_root/'PREDICTIONS_FLAT.csv.gz'
    if dest.exists():
        if dest.read_bytes()!=body:raise ValueError('existingexportdiffers; retainundernewversion')
    else:
        with dest.open('xb')as handle:handle.write(body)
    if dest.read_bytes()!=body:raise ValueError('exportreadback mismatch')
    score_path=public_root/'SCORES.json';scores=json.loads(score_path.read_bytes());base=collections.defaultdict(list)
    dims=('procedure_id','target','history_regime','policy_id','product_id','population')
    for r in rows:
        if r['week']!=8:base[tuple(r[k]for k in dims)].append(r)
    projection=[]
    for i,s in enumerate(scores):
        rs=base[tuple(s[k]for k in dims)]
        rs=[r for r in rs if(s['week']=='ALL'or r['week']==s['week'])and(s['position']=='ALL'or r['position']==s['position'])and(s['fallback_view']=='ALL'or r['fallback']=='none')]
        scored=[r for r in rs if r['prediction']is not None and r['actual']is not None]
        if len(rs)!=s['forecast_rows']or len(scored)!=s['n']or len({r['game_id']for r in scored})!=s['unique_games']:raise ValueError('scoreviewcount mismatch')
        projection.append(dict(source_row_index=i,evaluation_seasons=[2026],evaluation_weeks=sorted({r['week']for r in scored}),actual_scored_weeks=sorted({r['week']for r in scored}),forecast_query_weeks=sorted({r['week']for r in rs}),registered_panel_weeks=list(range(1,8)),dimensions={k:s[k]for k in(*dims,'week','position','fallback_view')}))
    dates=dict(source_score_artifact=score_path.resolve().relative_to(ROOT).as_posix(),source_score_sha256=digest(score_path.read_bytes()),source_row_unit='zero-based index in immutable sourceSCORES.json',date_definition='evaluation_weeks are actual retained supported outcome weeks in this exact view; forecast_query_weeks include missingactuals; registeredpanelW1-W7doesnotimplyeachlearned-onlyviewcoversallweeks',rows=projection)
    with(public_root/'SCORE_DATE_PROJECTION.json').open('xb')as handle:handle.write(canonical(dates))
    receipt=dict(version='v2-count-ablation-retained-row-export-v1',private_safe_artifact_id='V2-PRIVATE-COUNT-ABLATION-FLAT-0001',private_export_sha256=digest(body),private_export_bytes=len(body),rows=len(rows),historical_rows=sum(r['week']!=8 for r in rows),future_rows=sum(r['week']==8 for r in rows),future_actuals=0,fields=fields,source_receipts=source_receipts,source_score_sha256=dates['source_score_sha256'],date_projection_views=len(projection),date_projection_sha256=digest(canonical(dates)),new_fits=0,new_forecasts=0,week8_outcomes_read=0,private_durability='LOCAL_READBACK_PENDING_COMPANION_RECEIPT')
    with(public_root/'RETAINED_ROW_EXPORT_RECEIPT.json').open('xb')as handle:handle.write(canonical(receipt))
    return{k:v for k,v in receipt.items()if k!='source_receipts'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for a in('public-root','private-root'):p.add_argument('--'+a,type=Path,required=True)
    print(json.dumps(export(**vars(p.parse_args())),indent=2))
