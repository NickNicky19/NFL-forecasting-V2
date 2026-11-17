"""Finite chronological QB context experiment; source and retained bytes first."""
import argparse
import collections
import gzip
import hashlib
import json
import math
import platform
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
import sklearn
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nfl_v2 import player_context_matchup as ctx
from nfl_v2.distribution_laws import prior
from nfl_v2.distribution_wave_v2 import FittedLawModel


def now():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def clean(value):
    if isinstance(value,dict):return {k:clean(v)for k,v in value.items()}
    if isinstance(value,(list,tuple,np.ndarray)):return [clean(v)for v in value]
    if isinstance(value,np.generic):return clean(value.item())
    if isinstance(value,float)and not math.isfinite(value):return None
    return value
def write(path,value):
    path=Path(path)
    if path.exists():raise FileExistsError(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    body=(json.dumps(clean(value),separators=(',',':'),allow_nan=False)+'\n').encode()
    path.write_bytes(gzip.compress(body,compresslevel=9,mtime=0)if path.suffix=='.gz'else body)
    return dict(path=str(path.relative_to(ROOT)),sha256=sha(path),bytes=path.stat().st_size)
def read(path):
    path=Path(path);body=path.read_bytes()
    return json.loads(gzip.decompress(body)if path.suffix=='.gz'else body)


class Budget:
    def __init__(self,out,protocol):
        self.out=out;self.limit=protocol['budget'];self.start=time.monotonic();self.cpu=time.process_time()
        self.attempts=out/'FIT_ATTEMPTS.jsonl'
        self.fit_calls=len(self.attempts.read_text().splitlines()) if self.attempts.exists() else 0
        prior=[read(p).get('resources',{})for p in out.glob('*RECEIPT*.json')]
        prior += [read(p).get('resources',{})for p in (out/'predictions').glob('*.json.gz')] if(out/'predictions').exists()else[]
        self.prior_cpu=max([r.get('cpu_seconds',0.)for r in prior],default=0.)
        self.prior_wall=max([r.get('wall_seconds',0.)for r in prior],default=0.)
    def check(self):
        if self.prior_wall+time.monotonic()-self.start>self.limit['wall_seconds']:raise RuntimeError('WALL_BUDGET')
        if self.prior_cpu+time.process_time()-self.cpu>self.limit['cpu_seconds']:raise RuntimeError('CPU_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>self.limit['max_RSS_bytes']:raise RuntimeError('MEMORY_BUDGET')
        size=sum(p.stat().st_size for p in self.out.rglob('*')if p.is_file())
        if size>self.limit['public_retention_bytes']-self.limit['reserve_bytes']:raise RuntimeError('RETENTION_BUDGET')
    def fit(self,slot):
        self.check()
        if self.fit_calls>=self.limit['max_optimizer_fits']:raise RuntimeError('FIT_BUDGET')
        self.fit_calls+=1
        with self.attempts.open('a')as f:f.write(json.dumps(dict(attempt=self.fit_calls,slot=slot,actual_started_utc=now()))+'\n')
    def resources(self):return dict(wall_seconds=self.prior_wall+time.monotonic()-self.start,cpu_seconds=self.prior_cpu+time.process_time()-self.cpu,
                                    peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                                    optimizer_fits_charged=self.fit_calls)


def origins(rows,season,weeks):
    return [(week,min(r['kickoff']for r in rows if r['season']==season and r['week']==week))for week in weeks]


def prepare(args):
    args.out.mkdir(parents=True,exist_ok=False)
    rows=ctx.load_inputs(args.inputs)
    code={str(p.relative_to(ROOT)):sha(p)for p in [Path(__file__),ROOT/'nfl_v2/player_context_matchup.py',ROOT/'nfl_v2/distribution_wave_v2.py',ROOT/'nfl_v2/distribution_laws.py',ROOT/'nfl_v2/hgb_control.py']}
    protocol=dict(id=ctx.VERSION,state='FROZEN_BEFORE_TUNING_OR_NFL_FITTING',registered_utc=now(),
        assignment='PLAYER-CONTEXT-MATCHUP-01 version1',owner='B',canonical_evaluation_owner='C',
        inputs=dict(path=str(args.inputs.relative_to(ROOT)),sha256=sha(args.inputs),rows=len(rows),license='CC-BY-4.0',
                    attribution='nflverse/nflfastR player-game derivatives; prepared by Session B'),
        code_sha256=code,history='H-RECENT season-relative preceding season + earlier current labels; feature memory expanding from2022',
        timing='Historical label and context availability=kickoff+7days strict<; weekly fit before earliest game kickoff; query refresh at own kickoff leftlimit.',
        source_vintage='Current/revised sources under disclosed +7day reconstruction; not authenticated historical publication.',
        population='Retrospective officialQBstat-row query panel; unknown participation retained. Not an exante roster or originally issued forecast.',
        evaluation=[dict(season=2025,weeks=list(range(1,19))),dict(season=2026,weeks=list(range(1,9)))],
        primary_target='pass_cmp',auxiliary_target='pass_att',targets_remaining='Other10categories remain in parent championship; A owns rushing and C receiving/alignment.',
        validation=dict(season=2024,weeks=list(range(1,9)),windows=[4,8,16],strengths=[20.,80.],
                        objective='Mean full-game completion gamma-Poisson NLL using predicted attempts and predicted down/depth mix',
                        tie_break='menu order4,8,16 then20,80; no evaluated2025/2026outcomes used for this selection'),
        direct=dict(learner='unchanged32-tree ExtraTrees/Leaf-CDF settings and95/5 empirical-prior law',training_scope='QB-only new controlled direct baseline, not a renamed old broad-position fit',
                    E0='Existing own-target mean3/8,last4/age/missing/position fields; new QB-only training control.',
                    E1='E0+earlier own25-state down/depth proportions, shrunk completion rates/support and historical field context summaries.',
                    E2='E1+16scheduled-defense-game context residuals versus earlier offense-quality reference; support retained.',
                    E3='E2+25explicit own predicted-mix x opponent-context residual products. Forest may already learn implicit interactions; no forced feature use.'),
        personalization=dict(P1='Shared conditional contextGLM with pregame history fields and offense/defense main effects.',
                            P2='Same inputs + penalized QB intercepts; pooling strength selected in earlier2024validation.',
                            P3='Player-only conditionalGLM trained only on own last16eligiblegames; shared feature definitions; min8priorgames and160attempts, else exact P1fallback.',
                            volume='One common empirical gamma-Poisson attempt forecast, not three independent exposure models.',
                            integration='Exact sum over25predicted contexts; binomial thinning of common gamma-Poisson attempts. No realized target-game mix/exposure supplied.',
                            uncertainty='Exposure gamma-Poisson uncertainty modeled; completion coefficients/context weights are point estimates. No claim of full posterior uncertainty.',
                            receiver_effects='Explicit QB-receiver/alignment extension awaits C; no causal attribution of all conversion to QB.'),
        selection=dict(primary='Existing P1 unrounded mean/median direction and exact-law statistical probability direction, kept separate.',
                       conditioning='Physical-participation statistical crossing; no bookmaker nonvoid/EV claim.',
                       selective_target=.90,top_k=[6,10,20],timing='Chronological game batches with remaining weekly slots, percategory and side; unqualified quote clocks remain diagnostic, never an original selectable list.'),
        audit_controls='Preserve collapse holds, explicitnull/playedzero/unknown labels and source versions. No intercept/ranker repair, Cfeature-use rerun, Aallocation or Astra study.',
        existing_strong_control='Reuse retained exact Leaf/R0 outputs on named common rows where cutoff/label/role contracts match; no completed equivalent refit.',
        budget=dict(max_optimizer_fits=1600,wall_seconds=1200,cpu_seconds=1800,max_threads=2,max_RSS_bytes=2147483648,
                    public_retention_bytes=67108864,reserve_bytes=4194304,new_private_restricted_bytes=0),
        legacy_recovery_gate='Unchanged;thisindependentqualifiedpublic-derivedpackage consumes no un-restored legacy model or source.',
        retention='Before broad run verify this input+code/protocol+pilot typed parameters through GitHub. No public rawfeeds, restricted offers, private paths or unsafe model serialization.',
        forecast_products=['mean','lower_median','valid_count_law'],original_issuance=False,release='No automatic release; five scored product-weeks and owner admission separately required.')
    write(args.out/'FROZEN_PROTOCOL.json',protocol)
    print(json.dumps(dict(state=protocol['state'],input_rows=len(rows),nominal_origins=26)))


def fit_completion(rows,history,personalized,strength,budget,slot,out):
    path=out/'fits'/(slot+'.json.gz')
    if path.exists():
        receipt=read(path)
        return ctx.CompletionModel.restore(receipt['model']),receipt
    budget.fit(slot);started=now();model=ctx.CompletionModel(personalized,strength).fit(rows,history)
    if model is None:raise RuntimeError('NO_CONDITIONAL_TRAINING_SUPPORT')
    receipt=dict(slot=slot,actual_started_utc=started,actual_completed_utc=now(),new_optimizer_fits=1,
        training_rows=len(rows),latest_training_label=max(r['available']for r in rows),
        latest_training_feature=max((history.describe(r)['latest_source_available']or-float('inf')for r in rows)),
        training_membership_sha256=hashlib.sha256(json.dumps([(r['game_id'],r['player_id'])for r in rows]).encode()).hexdigest(),
        model=model.payload())
    write(path,receipt);return model,receipt


def tune(rows,out,p,budget):
    selected=out/'SELECTED_EARLIER_CONFIG.json'
    if selected.exists():return read(selected)
    result=[]
    for window in p['validation']['windows']:
        for strength in p['validation']['strengths']:
            history=ctx.ContextHistory(rows,window,strength);losses=[];weekly=[]
            for week,origin in origins(rows,2024,p['validation']['weeks']):
                train=history.eligible(origin,2023);slot=f'TUNE-2024-W{week:02}-N{window}-S{int(strength)}'
                model,_=fit_completion(train,history,True,strength,budget,slot,out)
                values=[]
                for q in rows:
                    if q['season']!=2024 or q['week']!=week or not q.get('physical_participation'):continue
                    exposure=history.exposure(q);d=history.describe(q);prob=float(d['mix']@model.probabilities(q,history))
                    law=ctx.CountLaw(exposure.mean*prob,exposure.shape)
                    values.append(-law.logpmf(q['official_completions']))
                losses+=values;weekly.append(dict(week=week,n=len(values),NLL=float(np.mean(values))))
            result.append(dict(window=window,strength=strength,n=len(losses),NLL=float(np.mean(losses)),weekly=weekly))
    best=min(result,key=lambda r:(r['NLL'],p['validation']['windows'].index(r['window']),p['validation']['strengths'].index(r['strength'])))
    selection=dict(window=best['window'],strength=best['strength'],validation=result,
                   all_validation_outcomes_already_research_exposed=True,
                   selected_before_2025_2026_evaluation=True,score_kind='EARLIER_CONFIGURATION_SELECTION_NOT_NEW_INDEPENDENT_METHODS')
    write(selected,selection);return selection


def run(args):
    p=read(args.out/'FROZEN_PROTOCOL.json')
    for file,digest in p['code_sha256'].items():
        if sha(ROOT/file)!=digest:raise ValueError('Frozen code changed: '+file)
    if sha(args.inputs)!=p['inputs']['sha256']:raise ValueError('Input bytes changed')
    budget=Budget(args.out,p);rows=ctx.load_inputs(args.inputs)
    with threadpool_limits(limits=2):
        chosen=tune(rows,args.out,p,budget)
        history=ctx.ContextHistory(rows,chosen['window'],chosen['strength'])
        matrices={arm:np.asarray([history.direct_features(q,arm)for q in rows])for arm in ['E0','E1','E2','E3']}
        plan=[(e['season'],w,t)for e in p['evaluation']for w,t in origins(rows,e['season'],e['weeks'])]
        completed=[]
        for season,week,origin in plan:
            destination=args.out/'predictions'/f'{season}-W{week:02}.json.gz'
            if destination.exists():completed.append((season,week));continue
            if args.max_origins is not None and len(completed)>=args.max_origins:break
            budget.check();indices=[i for i,r in enumerate(rows)if r.get('physical_participation')and r['target_parity']and r['season']>=season-1 and r['available']<origin]
            train=[rows[i]for i in indices];queries=[(i,q)for i,q in enumerate(rows)if q['season']==season and q['week']==week]
            y=np.asarray([r['official_completions']for r in train],float);pr=prior(y,'pass_cmp');predictions=[]
            for arm in ['E0','E1','E2','E3']:
                slot=f'{season}-W{week:02}-{arm}';path=args.out/'fits'/(slot+'.json.gz')
                if path.exists():payload=read(path)['model']
                else:
                    budget.fit(slot);started=now();model=FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(matrices[arm][indices],y,['QB']*len(y));payload=ctx.export_forest(model)
                    # Restored parameters must reproduce their own fitted law.
                    sample=matrices[arm][queries[0][0]];a=model.predict(sample[None,:],['QB'],{'QB':pr})[0][0];b=ctx.restored_forest_law(payload,sample,pr)
                    if abs(a.mean-b.mean)>1e-10 or a.quantile(.5)!=b.quantile(.5):raise RuntimeError('TYPED_FOREST_PARITY')
                    write(path,dict(slot=slot,new_optimizer_fits=1,actual_started_utc=started,actual_completed_utc=now(),
                        fit_cutoff=origin,latest_training_label=max(r['available']for r in train),
                        latest_training_feature=max((history.describe(r)['latest_source_available']or-float('inf')for r in train)),
                        training_rows=len(train),model=payload))
                for i,q in queries:
                    law=ctx.restored_forest_law(payload,matrices[arm][i],pr)
                    predictions.append(prediction(q,arm,'pass_cmp',law,origin,history,
                                                  features=matrices[arm][i],model_slot=slot,fallback='none'))
            shared,shared_fit=fit_completion(train,history,False,chosen['strength'],budget,f'{season}-W{week:02}-P1',args.out)
            partial,partial_fit=fit_completion(train,history,True,chosen['strength'],budget,f'{season}-W{week:02}-P2',args.out)
            personal={}
            for _,q in queries:
                own=sorted([r for r in train if r['player_id']==q['player_id']],key=lambda r:(r['kickoff'],r['game_id']))[-16:]
                if len(own)>=8 and sum(r['official_attempts']for r in own)>=160:
                    key=hashlib.sha256(q['player_id'].encode()).hexdigest()[:16]
                    personal[q['player_id']]=fit_completion(own,history,False,chosen['strength'],budget,f'{season}-W{week:02}-P3-{key}',args.out)[0]
                else:personal[q['player_id']]=None
                exposure=history.exposure(q);d=history.describe(q)
                predictions.append(prediction(q,'COMMON_EXPOSURE','pass_att',exposure,origin,history,
                                              components=dict(attempt_law=exposure.parameters()),fallback=d['fallback']))
                for name,model in [('P1',shared),('P2',partial),('P3',personal[q['player_id']]or shared)]:
                    probabilities=model.probabilities(q,history);prob=float(d['mix']@probabilities)
                    law=ctx.CountLaw(exposure.mean*prob,exposure.shape)
                    fallback='shared_no_pooling_support_fallback'if name=='P3'and personal[q['player_id']]is None else d['fallback']
                    predictions.append(prediction(q,name,'pass_cmp',law,origin,history,
                        components=dict(attempt_law=exposure.parameters(),predicted_context_mix=d['mix'],
                                        conditional_completion_probability=probabilities,integrated_completion_probability=prob),fallback=fallback))
            write(destination,dict(season=season,week=week,fit_cutoff=origin,rows=predictions,actual_persisted_utc=now(),
                                  original_issuance=False,resources=budget.resources()))
            completed.append((season,week))
            print(json.dumps(dict(completed_origin=[season,week],rows=len(predictions),fits=budget.fit_calls)),flush=True)
        receipt=dict(state='COMPLETE'if len(completed)==len(plan)else'PARTIAL_PILOT_RETAINED',completed_origins=completed,
                     remaining_origins=[[s,w]for s,w,_ in plan if(s,w)not in completed],resources=budget.resources(),
                     new_original_forecasts=0,source_vintage=p['source_vintage'],new_scoring=False)
        name='RUN_RECEIPT.json'if receipt['state']=='COMPLETE'else f'PILOT_RECEIPT_{len(completed)}.json'
        write(args.out/name,receipt);print(json.dumps(receipt))


def prediction(query,method,target,law,origin,history,**extra):
    d=history.describe(query);exposure=history.exposure(query)
    band='NO_PRIOR'if not d['own_games']else'LOW_<10'if exposure.mean<10 else'MID_10_25'if exposure.mean<25 else'HIGH_25_PLUS'
    return clean(dict(procedure_id=ctx.VERSION+':'+method,method=method,history_regime='H-RECENT',feature_memory='2022_EXPANDING',
        game_id=query['game_id'],player_id=query['player_id'],team=query['team'],opponent=query['opponent'],position='QB',
        season=query['season'],week=query['week'],target=target,fit_cutoff=origin,feature_cutoff=query['kickoff'],
        actual_execution_utc=now(),original_issuance=False,mean=law.mean,lower_median=law.quantile(.5),
        law=law.parameters()if isinstance(law,ctx.CountLaw)else dict(kind='leaf_mixture',support=law.support.tolist(),weights=law.weights.tolist(),prior=law.prior.parameters(),mixture=law.b),
        actual=(query['official_completions']if target=='pass_cmp'else query['official_attempts'])if query['physical_participation']else None,
        actual_status=query['label_status'],pregame_role_band=band,own_prior_games=d['own_games'],own_prior_attempts=d['own_attempts'],
        last_prior_game=d['last_prior_game'],latest_source_available=d['latest_source_available'],
        latest_own_game_age_days=d['latest_own_game_age_days'],source_age_days=d['latest_own_source_age_days'],
        population=query['population'],**extra))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);parser.add_argument('--max-origins',type=int)
    args=parser.parse_args();args.inputs=args.inputs.resolve();args.out=args.out.resolve()
    if args.action=='prepare':prepare(args)
    else:
        try:run(args)
        except Exception as error:
            stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
            reason=str(error)
            if '/'in reason:reason='Bound input or filesystem failure; original detail in local execution output'
            write(args.out/('FAILED_RECEIPT_'+stamp+'.json'),dict(state='FAILED_PARTIAL_PRESERVED',
                actual_utc=now(),exception=type(error).__name__,reason=reason,
                actual_optimizer_attempts=len((args.out/'FIT_ATTEMPTS.jsonl').read_text().splitlines())if(args.out/'FIT_ATTEMPTS.jsonl').exists()else 0,
                completed_origin_chunks=len(list((args.out/'predictions').glob('*.json.gz'))),
                scope='All successful models/chunks and attempted-fit budget preserved; no implicit unchanged rerun.'))
            raise


if __name__=='__main__':main()
