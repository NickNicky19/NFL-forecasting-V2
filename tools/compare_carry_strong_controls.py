#!/usr/bin/env python3
"""Independent retained-row carry comparison; no fits or future records."""
import argparse,collections,csv,gzip,hashlib,json,math,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2.shadow_grading import canonical,digest

METHODS={'collapsed_l1':('hgb-direct-history-controls-v1:absolute_error_point','absolute_error_point'),
 'prior_best_mean':('hgb-direct-history-controls-v1:squared_error_mean','squared_error_mean'),
 'primary_role_l1':('v2-hgb-rush-att-qb-rb-specialization-v1:common-feature-memory','absolute_loss_point'),
 'ordered_cdf_median':('v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory','lower_median'),
 'empirical_median':('empirical-player-history-control-v1','lower_median')}
def sha(path):return digest(Path(path).read_bytes())
def key(r):return tuple(r[k]for k in('game_id','player_id','target','population'))
def native(rows):
    scored=[r for r in rows if r['actual']is not None and r['prediction']is not None];e=[r['prediction']-r['actual']for r in scored];a=sorted(map(abs,e));n=len(e)
    out=dict(n=n,forecast_rows=len(rows),fallback_rows=sum(r['fallback']!='none'for r in rows),scored_fallback_rows=sum(r['fallback']!='none'for r in scored),unique_games=len({r['game_id']for r in scored}),coverage=dict(scored_rows=n,offered_rows=len(rows),scored_games=len({r['game_id']for r in scored}),forecast_games=len({r['game_id']for r in rows})))
    if not n:return dict(out,mae=None,mse=None,rmse=None,bias=None)
    mse=math.fsum(v*v for v in e)/n
    def q(p):
        x=(n-1)*p;i,j=math.floor(x),math.ceil(x);return a[i]+(a[j]-a[i])*(x-i)
    out.update(mae=math.fsum(a)/n,mse=mse,rmse=math.sqrt(mse),bias=math.fsum(e)/n,p90_abs=q(.9),p95_abs=q(.95),max_abs=a[-1],exact_rate=sum(v==0 for v in e)/n)
    for t in(1,5,10):out['abs_lt_'+str(t)]=sum(v<t for v in a)/n;out['abs_le_'+str(t)]=sum(v<=t for v in a)/n
    return out
def write(path,value):
    with Path(path).open('xb')as f:f.write(canonical(value))

def run(old_public,old_private,empirical,counts,distributions,public_output,private_output):
    old_public,old_private,empirical,counts,distributions,public_output,private_output=map(Path,(old_public,old_private,empirical,counts,distributions,public_output,private_output))
    if public_output.exists()or private_output.exists():raise ValueError('freshimmutableoutputsrequired')
    public_output.mkdir(parents=True);private_output.mkdir(parents=True);inputs={};records=collections.defaultdict(dict)
    registration=dict(version='v2-matched-carry-strong-control-replay-v1',registered_at_utc=datetime.now(timezone.utc).isoformat(),code_sha256=sha(__file__),methods=METHODS,regime='H-MULTI',populations=['primaryQB/RB','extendedWR/TE'],fixed_source_panel='same2026W1-W7frozen2394querycells; score844primary+1516extendedsupported; unknownlabelsretained',views=['full_system','own_learned_only','all_five_learned_overlap','fallback_only'],contrasts='everymethodversusprior_best_mean; orderedCDFversusroleL1; absoluteandrelativepairedMAEdifference; gameclusterSEsensitivity;7weekinsufficientCI; no futureselection',new_fits=0,new_forecasts=0,week8_outcomes_read=0)
    write(public_output/'FROZEN_PROTOCOL.json',registration)
    def admit(r,name):
        if int(r['week'])>7 or int(r.get('season',2026))!=2026 or r['target']!='rush_att'or r['history_regime']!='H-MULTI':return
        row={k:r[k]for k in('game_id','player_id','target','population','position','history_regime','fallback')};row['week']=int(r['week']);row['season']=2026
        for k in('actual','prediction'):row[k]=None if r.get(k)in(None,'')else float(r[k])
        if key(row)in records[name]:raise ValueError('duplicatecarryquery')
        records[name][key(row)]=row
    for w in range(1,8):
        for objective,name in [('absolute_error_point','collapsed_l1'),('squared_error_mean','prior_best_mean')]:
            path=old_public/f'W{w:02}-rush_att-H-MULTI-{objective}-FORECAST.json';receipt=json.loads(path.read_bytes());d=receipt['packet'];file=old_private/d['name'];blob=file.read_bytes();body=gzip.decompress(blob)
            if sha(file)!=d['sha256']or digest(body)!=d['uncompressed_sha256']:raise ValueError('oldcapturebytebinding')
            inputs[path.name]=dict(receipt_sha256=sha(path),prediction_sha256=sha(file))
            for r in json.loads(body)['rows']:admit(r,name)
    for path,sourceid in [(empirical,'empirical'),(counts,'role_ablation'),(distributions,'ordered_law')]:
        inputs[sourceid]=dict(artifact_id=path.name,sha256=sha(path))
        with gzip.open(path,'rt',newline='')as h:
            for r in csv.DictReader(h):
                if r['target']!='rush_att'or r['season']!='2026'or int(r['week'])>7 or r['history_regime']!='H-MULTI':continue
                name=None
                if sourceid=='empirical'and r['product']=='lower_median':name='empirical_median'
                if sourceid=='role_ablation'and r['procedure_id']==METHODS['primary_role_l1'][0]:name='primary_role_l1'
                if sourceid=='ordered_law'and r['procedure_id']==METHODS['ordered_cdf_median'][0]and r['product_id']=='lower_median':name='ordered_cdf_median'
                if name:admit(r,name)
    reference=records['prior_best_mean']
    if set(records)!=set(METHODS)or any(set(rows)!=set(reference)for rows in records.values()):raise ValueError('differentcarryquerycohorts')
    if any(r['actual']!=reference[k]['actual']or r['position']!=reference[k]['position']for rows in records.values()for k,r in rows.items()):raise ValueError('carrylabel/positionmismatch')
    overlap=set.intersection(*[{k for k,r in rs.items()if r['fallback']=='none'and r['actual']is not None and r['prediction']is not None}for rs in records.values()]);scores=[];contrasts=[]
    for pop in('primary','extended'):
        for view in registration['views']:
            for name,rs in records.items():
                rows=[r for k,r in rs.items()if r['population']==pop and(view=='full_system'or view=='own_learned_only'and r['fallback']=='none'or view=='fallback_only'and r['fallback']!='none'or view=='all_five_learned_overlap'and k in overlap)]
                value=native(rows);scores.append(dict(record_id=f'carry:{name}:{pop}:{view}',procedure_id=METHODS[name][0],procedure_family_id='retained-source-matched-carry-control',product_id=METHODS[name][1],target='rush_att',population=pop,season=2026,week='ALL',history_regime='H-MULTI',period='REG',fallback_view=view,evaluation_panel_id='v2-strong-carry-controls-identical-2026W1-W7-v1',evidence='REPRODUCED_FROM_DATA',record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',scored_membership_sha256=digest(canonical(sorted(key(r)for r in rows if r['actual']is not None and r['prediction']is not None))),**value))
        for new,old in [(m,'prior_best_mean')for m in METHODS if m!='prior_best_mean']+[('ordered_cdf_median','primary_role_l1')]:
            for view in('full_system','pair_learned_overlap','all_five_learned_overlap'):
                keys=[k for k,r in reference.items()if r['population']==pop and r['actual']is not None and(view=='full_system'or view=='all_five_learned_overlap'and k in overlap or view=='pair_learned_overlap'and records[new][k]['fallback']=='none'and records[old][k]['fallback']=='none')]
                if not keys:continue
                diffs=[];lossnew=[];lossold=[];bygame=collections.defaultdict(list);byweek=collections.defaultdict(list)
                for k in keys:
                    a,b=records[new][k],records[old][k];la=abs(a['prediction']-a['actual']);lb=abs(b['prediction']-b['actual']);diffs.append(la-lb);lossnew.append(la);lossold.append(lb);bygame[a['game_id']].append(la-lb);byweek[a['week']].append(la-lb)
                n=len(keys);delta=math.fsum(diffs)/n;meanold=math.fsum(lossold)/n;g=len(bygame);se=math.sqrt(g/(g-1)*math.fsum((math.fsum(v)-len(v)*delta)**2 for v in bygame.values())/n**2)if g>=8 else None
                contrasts.append(dict(new=new,old=old,population=pop,view=view,n=n,unique_games=g,new_mae=math.fsum(lossnew)/n,old_mae=meanold,paired_mae_difference=delta,relative_mae_improvement=-delta/meanold if meanold else None,row_wins=sum(d<0 for d in diffs),row_losses=sum(d>0 for d in diffs),row_ties=sum(d==0 for d in diffs),game_cluster_sensitivity_se=se,game_cluster_normal95_sensitivity=[delta-1.96*se,delta+1.96*se]if se is not None else None,week_clusters=len(byweek),week_interval=None,uncertainty_reason='only7exposedweeks;gameclustersensitivitynotmultiplicity/selectionadjustedorindependentweeklyconfirmation',weekly_paired_deltas={str(w):math.fsum(v)/len(v)for w,v in byweek.items()},scored_membership_sha256=digest(canonical(sorted(keys)))))
    privatebody=gzip.compress(canonical(dict(schema=registration['version'],methods={name:list(rs.values())for name,rs in records.items()})),mtime=0)
    with(private_output/'CARRY_CONTROL_ROWS.json.gz').open('xb')as h:h.write(privatebody)
    write(public_output/'SCORES.json',scores);write(public_output/'PAIRED_CONTRASTS.json',contrasts)
    with(public_output/'PAIRED_CONTRASTS.csv').open('x',newline='')as h:
        w=csv.DictWriter(h,fieldnames=list(contrasts[0]));w.writeheader();w.writerows(contrasts)
    receipt=dict(version=registration['version'],state='INDEPENDENT_RETAINED_ROW_COMPARISON_COMPLETE',completed_at_utc=datetime.now(timezone.utc).isoformat(),inputs=inputs,query_cells=len(reference),supported_primary_rows=sum(r['population']=='primary'and r['actual']is not None for r in reference.values()),supported_extended_rows=sum(r['population']=='extended'and r['actual']is not None for r in reference.values()),score_views=len(scores),paired_views=len(contrasts),private_rows_sha256=digest(privatebody),scores_sha256=sha(public_output/'SCORES.json'),new_fits=0,new_forecasts=0,week8_outcomes_read=0)
    write(public_output/'RUN_RECEIPT.json',receipt);return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for a in('old-public','old-private','empirical','counts','distributions','public-output','private-output'):p.add_argument('--'+a,type=Path,required=True)
    print(json.dumps(run(**vars(p.parse_args())),indent=2))
