"""Finite FTN support-versus-value addition to the already fitted QB E1 control.

Charted catchability is not completion or CP/CPOE. Its denominator here is
official credited non-sack/non-two-point throws with actual chart matches.
"""
import argparse, collections, gzip, hashlib, json, math, os, resource, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import player_context_matchup as ctx
from nfl_v2.distribution_laws import prior
from nfl_v2.distribution_wave_v2 import FittedLawModel
from tools.run_player_context_wave import read,write,sha,now,prediction

VERSION='B-QB-CHARTED-CATCHABILITY-CONTEXT-v1'
FLAGS=('is_catchable_ball','is_contested_ball','is_drop')

def features(rows,chart,history):
    by={ (r['game_id'],r['player_id']):r for r in chart }
    pool=[]
    for q in rows:
        c=by.get((q['game_id'],q['player_id']))
        if c and q.get('physical_participation'):pool.append((q,c))
    out={};description={}
    for q in rows:
        eligible=[(p,c)for p,c in pool if p['available']<q['kickoff']]
        own=[(p,c)for p,c in eligible if p['player_id']==q['player_id']][-8:]
        n=sum(c['eligible_throws']for p,c in own)
        support=[float(len(own)),math.log1p(n)]
        rates=[];flagdetail={}
        for flag in FLAGS:
            known=sum(c['flags'][flag]['known']for p,c in own);positive=sum(c['flags'][flag]['positive']for p,c in own)
            pk=sum(c['flags'][flag]['known']for p,c in eligible);pp=sum(c['flags'][flag]['positive']for p,c in eligible)
            baseline=(pp+1)/(pk+2)
            observed=[p for p,c in own if c['flags'][flag]['known']>0]
            age=(q['kickoff']-max(p['available']for p in observed))/86400 if observed else math.nan
            support += [known/n if n else math.nan,math.log1p(known),age,float(not known)]
            rates.append((positive+20*baseline)/(known+20)if known else math.nan)
            flagdetail[flag]=dict(known=known,positive=positive,eligible_throws=n,global_known=pk,global_positive=pp,
                                  latest_own_source_age_days=age if math.isfinite(age)else None)
        base=history.direct_features(q,'E1');out[q['game_id'],q['player_id']]=(np.r_[base,support],np.r_[base,support,rates])
        description[q['game_id'],q['player_id']]=dict(flags=flagdetail,own_games=len(own),
            latest_feature_available=max([p['available']for p,c in eligible],default=None),
            historical_clock_policy='Same strict kickoff+7day reconstruction for chart features; not authenticated historical chart release.')
    return out,description

def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run']);ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--chart',type=Path,required=True)
    ap.add_argument('--base-wave',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--max-origins',type=int);a=ap.parse_args()
    if a.action=='prepare':
        a.out.mkdir(parents=True,exist_ok=False)
        write(a.out/'FROZEN_PROTOCOL.json',dict(id=VERSION,registered_utc=now(),state='FROZEN_BEFORE_FITS_OR_NEW_SCORES',owner='B',
            code_sha256=sha(__file__),base_code_sha256=sha(ROOT/'nfl_v2/player_context_matchup.py'),inputs_sha256=sha(a.inputs),chart_sha256=sha(a.chart),
            base_protocol_sha256=sha(a.base_wave/'FROZEN_PROTOCOL.json'),base_run_sha256=sha(a.base_wave/'RUN_RECEIPT.json'),
            mechanism='Added earlier own charted catchability/drop/contested-rate information at forecast mixture level; no new classifier or calibration search.',
            control='Exact frozen E1 own down/depth Leaf-CDF models reused without refit. F1=E1+chart support/age/missingness. F2=F1+3shrunk charted rates.',
            history='H-RECENT fit, expanding2022featurememory,8owneligibleappearances,20throwspooledprior; all fixed by earlier base validation or declared before this wave.',
            clock_policy='Current/revised charting with strict kickoff+7day reconstructed availability, aligned in training and query. No original publication clock claim.',
            chart_contract='FTN Data via nflverse, CC-BY-SA4.0; eligible official throws, explicit known/positive counts; missing annotation is not false.',
            nonclaims='No alignment/route denominator, no CP/CPOE or target-game charting, no receiver skill or causal interpretation.',
            scope='2025W1-18;2026W1-8 retrospective QB-stat membership. Actual lines onlywhere retained and separately qualified. Not original issuance.',
            output_license='CC-BY-SA-4.0 derived charting inputs/models/forecasts; keep source attribution and sharealike in permitted exports.',
            budget=dict(max_new_fits=52,wall_seconds=180,cpu_seconds=300,max_RSS_bytes=2147483648,max_threads=2,retention_bytes=16777216,reserve_bytes=2097152),
            pilot_retention='First2typedmodels+code/protocolpublished andfreshreadback before remaining origins. Reuse completed E1, no extra raw source download.',
            selection='Same unrounded mean/median and legitimate exact-line law policies as base; no evaluated-outcome gate. Five-week product floor unchanged.'))
        print('FROZEN');return
    p=read(a.out/'FROZEN_PROTOCOL.json');assert p['code_sha256']==sha(__file__)and p['inputs_sha256']==sha(a.inputs)and p['chart_sha256']==sha(a.chart)
    assert p['base_code_sha256']==sha(ROOT/'nfl_v2/player_context_matchup.py')
    started=time.monotonic();cpu=time.process_time();rows=ctx.load_inputs(a.inputs);history=ctx.ContextHistory(rows,8,20)
    xx,descriptions=features(rows,read(a.chart),history);attempts=a.out/'FIT_ATTEMPTS.jsonl';charged=len(attempts.read_text().splitlines())if attempts.exists()else 0
    receipts=[read(f).get('resources',{})for f in a.out.glob('*RECEIPT*.json')];previous_cpu=max([r.get('cpu_seconds',0)for r in receipts],default=0);previous_wall=max([r.get('wall_seconds',0)for r in receipts],default=0)
    def resources():return dict(wall_seconds=previous_wall+time.monotonic()-started,cpu_seconds=previous_cpu+time.process_time()-cpu,optimizer_fits_charged=charged,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    def guard():
        r=resources();b=p['budget']
        if r['wall_seconds']>b['wall_seconds']or r['cpu_seconds']>b['cpu_seconds']or r['peak_RSS_bytes']>b['max_RSS_bytes']:raise RuntimeError('CHART_CONTEXT_RESOURCE_LIMIT')
        if sum(f.stat().st_size for f in a.out.rglob('*')if f.is_file())>b['retention_bytes']-b['reserve_bytes']:raise RuntimeError('CHART_CONTEXT_RETENTION_LIMIT')
    plan=[(r['season'],r['week'],r['fit_cutoff'])for f in sorted((a.base_wave/'predictions').glob('*.json.gz'))for r in [read(f)]];completed=[]
    with threadpool_limits(limits=2):
        for season,week,cutoff in plan:
            dest=a.out/'predictions'/f'{season}-W{week:02}.json.gz'
            if dest.exists():completed.append([season,week]);continue
            if a.max_origins is not None and len(completed)>=a.max_origins:break
            train=[r for r in rows if r.get('physical_participation')and r['target_parity']and r['season']>=season-1 and r['available']<cutoff]
            queries=[r for r in rows if(r['season'],r['week'])==(season,week)];y=np.asarray([r['official_completions']for r in train],float);fallback_prior=prior(y,'pass_cmp');pred=[]
            for index,arm in enumerate(('F1','F2')):
                guard();slot=f'{season}-W{week:02}-{arm}';fp=a.out/'fits'/(slot+'.json.gz')
                if fp.exists():payload=read(fp)['model']
                else:
                    if charged>=p['budget']['max_new_fits']:raise RuntimeError('FIT_LIMIT')
                    charged+=1
                    with attempts.open('a')as f:f.write(json.dumps(dict(attempt=charged,slot=slot,actual_started_utc=now()))+'\n')
                    matrix=np.asarray([xx[r['game_id'],r['player_id']][index]for r in train]);model=FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(matrix,y,['QB']*len(y));payload=ctx.export_forest(model)
                    sample=xx[queries[0]['game_id'],queries[0]['player_id']][index];before=model.predict(sample[None,:],['QB'],{'QB':fallback_prior})[0][0];after=ctx.restored_forest_law(payload,sample,fallback_prior)
                    if abs(before.mean-after.mean)>1e-10 or before.quantile(.5)!=after.quantile(.5):raise RuntimeError('CHART_TYPED_PARITY')
                    write(fp,dict(slot=slot,model=payload,training_rows=len(train),fit_cutoff=cutoff,latest_training_label=max(r['available']for r in train),actual_completed_utc=now(),new_optimizer_fits=1))
                for q in queries:
                    x=xx[q['game_id'],q['player_id']][index];l=ctx.restored_forest_law(payload,x,fallback_prior)
                    r=prediction(q,arm,'pass_cmp',l,cutoff,history,features=x,model_slot=slot,fallback='none',charted_feature_support=descriptions[q['game_id'],q['player_id']]);r['procedure_id']=VERSION+':'+arm;r['charting_license']='CC-BY-SA-4.0';pred.append(r)
            write(dest,dict(season=season,week=week,fit_cutoff=cutoff,rows=pred,actual_persisted_utc=now(),original_issuance=False,resources=resources()));completed.append([season,week]);print(json.dumps(dict(completed_origin=[season,week],fits=charged)),flush=True)
    complete=len(completed)==len(plan);receipt=dict(state='COMPLETE'if complete else'PARTIAL_PILOT_RETAINED',completed_origins=completed,remaining_origins=[[s,w]for s,w,t in plan if[s,w]not in completed],resources=resources(),original_issuance=False,license='CC-BY-SA-4.0')
    write(a.out/('RUN_RECEIPT.json'if complete else'PILOT_RECEIPT.json'),receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
