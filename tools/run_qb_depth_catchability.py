"""One finite depth-conditioned annotation block, matched direct/component arms."""
import argparse, hashlib, json, resource, sys, time
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import player_context_matchup as ctx
from nfl_v2.qb_depth_catchability import DepthHistory, DepthCompletionModel, VERSION
from nfl_v2.distribution_laws import prior
from nfl_v2.distribution_wave_v2 import FittedLawModel
from tools.run_player_context_wave import read,write,sha,now,prediction,Budget

BASE=ROOT/'reports/player-context-matchup-01/B'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run'])
    ap.add_argument('--chart',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--max-origins',type=int);a=ap.parse_args();a.chart=a.chart.resolve();a.out=a.out.resolve()
    inputs=BASE/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz'
    code=[Path(__file__),ROOT/'nfl_v2/qb_depth_catchability.py',ROOT/'nfl_v2/player_context_matchup.py',ROOT/'nfl_v2/distribution_wave_v2.py']
    if a.action=='prepare':
        a.out.mkdir(parents=True,exist_ok=False)
        write(a.out/'FROZEN_PROTOCOL.json',dict(id=VERSION,registered_utc=now(),owner='B',coordinator='C',
            continuation='PLAYER-CONTEXT-COMPLETION-DECISION-01 version1; additive, no prior result overwritten',
            state='FROZEN_BEFORE_NEW_FITS_AND_SCORES',code_sha256={str(p.relative_to(ROOT)):sha(p)for p in code},
            inputs=dict(path=str(inputs.relative_to(ROOT)),sha256=sha(inputs)),chart=dict(path=str(a.chart.relative_to(ROOT)),sha256=sha(a.chart)),
            closest_completed='F1/F2 own-game aggregate FTN support/3rates to E1; no depth-conditioned FTN field was consumed. E3/P1 and all negative probability/ranking results remain controls.',
            primary_mechanism='Five depth-specific earlier catchable annotations as a learned conversion covariate; no completion/catchability deterministic identity, no intercept or confidence search.',
            arms=dict(D1='Exact old E1 Leaf learner plus five-depth support; D2 adds five shrunk catchable logits.',
                      C1='Exact old P1 conditional-binomial learner/effects plus support at relevant depth; C2 adds shrunk catchable logit at that depth.'),
            shared_controls='Retained E1, P1, E3, F2, saved raw/adjusted, original Leaf/C02 where exact identities match; both constant sides, earlier prevalence and neutral0.25 on identical offers.',
            depth=['<0','0<=air_yards<10','10<=air_yards<20','>=20','UNKNOWN'],
            history='H-RECENT fit priorseason+earliercurrent; featurememory2022expanding; same existing8eligibleown games/20throw pooled prior from earlier2024choice. No new tuning.',
            support='perdepth known/eligible, log1p(known),log1p(source_age_days),no-own-known and no-pooled-known indicators; undefined coverage filled0 only with explicitmissing flag.',
            annotation='FTN is_catchable_ball TRUE/FALSE. Missing unknown. Own rate shrunk20toward earlier pooled perdepth Beta(1,1) mean; all-pooled-missing uses0.5 with support flag. Drop/contested retained descriptive, not consumed.',
            clock='Same strict kickoff+7day availability in training/query; revised current sources, not authenticated initial publication. Weekly origin before first game; pergame feature refresh.',
            population='Same retained retrospective officialQBstat-row queries, not authenticated pregame roster. Separate explicit-universe profile adapter has no outcome requirement.',
            integration='C1/C2 predict25conversion probabilities, integrate with old predicted25contextmix and gamma-Poissonattempt law. Exact binomial thinning; no actual targetgame exposure/context.',
            uncertainty='Attempt count uncertainty modeled; estimated contextweights/coefficients fixed. Numerical integration exact; no invented point uncertainty or new simulation.',
            evaluation=[dict(season=2025,weeks=list(range(1,19))),dict(season=2026,weeks=list(range(1,9)))],
            primary='Full-board exact-line own sides at retained2026W5-8,112CMPoffers; no primary switch with4offeredweeks. Full2025/W1-8 numeric and matched offer-subset numeric separate.',
            stopping='Complete26origins once, no outcome-driven extra search. Existing admission criteria: useful gain beyond strongest compatible control with coverage/uncertainty; no invented posthoc support/margin threshold. Five scored exactproductweeks and owner checks remain. No automatic retain from weak E0 comparison.',
            decisions=['RETAIN_FOR_OWNER_REVIEW','SHADOW','CLOSE_RECIPE_NO_GAIN','INCONCLUSIVE','SOURCE_OR_RESOURCE_BLOCKED'],
            budget=dict(max_optimizer_fits=104,wall_seconds=1200,cpu_seconds=1800,max_threads=2,max_RSS_bytes=2147483648,public_retention_bytes=33554432,reserve_bytes=2097152,new_private_restricted_bytes=0),
            retention='Source derivative+code+4pilot fits/predictions published and fresh readback before broader26origin execution. JSON only, no unsafe deserialization. Old large-fit gate unchanged.',
            license='CC-BY-SA-4.0; FTN Data via nflverse; PBP attribution nflverse/nflfastR',original_issuance=False))
        print('FROZEN');return
    p=read(a.out/'FROZEN_PROTOCOL.json')
    for s,h in p['code_sha256'].items():assert sha(ROOT/s)==h
    assert sha(inputs)==p['inputs']['sha256']and sha(a.chart)==p['chart']['sha256']
    budget=Budget(a.out,p);rows=ctx.load_inputs(inputs);history=ctx.ContextHistory(rows,8,20);chart=DepthHistory(rows,read(a.chart),8,20)
    plan=[(q['season'],q['week'],q['fit_cutoff'])for f in sorted((BASE/'qb-wave-v1/predictions').glob('*.json.gz'))for q in [read(f)]]
    completed=[]
    with threadpool_limits(limits=2):
        matrices={arm:np.asarray([chart.direct(q,history,arm=='D2')for q in rows])for arm in ('D1','D2')}
        for season,week,cutoff in plan:
            dest=a.out/'predictions'/f'{season}-W{week:02}.json.gz'
            if dest.exists():completed.append([season,week]);continue
            if a.max_origins is not None and len(completed)>=a.max_origins:break
            indices=[i for i,r in enumerate(rows)if r['physical_participation']and r['target_parity']and r['season']>=season-1 and r['available']<cutoff]
            train=[rows[i]for i in indices];queries=[(i,r)for i,r in enumerate(rows)if(r['season'],r['week'])==(season,week)]
            pr=prior([r['official_completions']for r in train],'pass_cmp');pred=[]
            for arm in ('D1','D2','C1','C2'):
                slot=f'{season}-W{week:02}-{arm}';fp=a.out/'fits'/(slot+'.json.gz')
                if fp.exists():payload=read(fp)['model']
                else:
                    budget.fit(slot)
                    if arm.startswith('D'):
                        m=FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(matrices[arm][indices],np.asarray([r['official_completions']for r in train]),['QB']*len(train));payload=ctx.export_forest(m)
                    else:
                        m=DepthCompletionModel(values=arm=='C2',penalty=20).fit(train,history,chart);payload=m.payload()
                    write(fp,dict(slot=slot,model=payload,training_rows=len(train),fit_cutoff=cutoff,latest_training_label=max(r['available']for r in train),
                        training_membership_sha256=hashlib.sha256(json.dumps([(r['game_id'],r['player_id'])for r in train]).encode()).hexdigest(),actual_completed_utc=now(),new_optimizer_fits=1))
                model=None if arm.startswith('D')else DepthCompletionModel.restore(payload)
                for i,q in queries:
                    detail=chart.describe(q)
                    if arm.startswith('D'):
                        l=ctx.restored_forest_law(payload,matrices[arm][i],pr);extra=dict(features=matrices[arm][i],fallback='none')
                    else:
                        probs=model.probabilities(q,history,chart);exposure=history.exposure(q);mix=history.describe(q)['mix'];prob=float(mix@probs)
                        l=ctx.CountLaw(exposure.mean*prob,exposure.shape);extra=dict(components=dict(attempt_law=exposure.parameters(),predicted_context_mix=mix,conditional_completion_probability=probs,integrated_completion_probability=prob),fallback=history.describe(q)['fallback'])
                    r=prediction(q,arm,'pass_cmp',l,cutoff,history,model_slot=slot,depth_chart_support=detail,**extra)
                    r['procedure_id']=VERSION+':'+arm;r['charting_license']='CC-BY-SA-4.0';pred.append(r)
            write(dest,dict(season=season,week=week,fit_cutoff=cutoff,rows=pred,actual_persisted_utc=now(),original_issuance=False,resources=budget.resources()))
            completed.append([season,week]);print(json.dumps(dict(origin=[season,week],fits=budget.fit_calls)),flush=True)
    complete=len(completed)==len(plan)
    write(a.out/('RUN_RECEIPT.json'if complete else'PILOT_RECEIPT_1.json'),dict(state='COMPLETE'if complete else'PARTIAL_PILOT_RETAINED',completed_origins=completed,remaining_origins=[[s,w]for s,w,t in plan if[s,w]not in completed],resources=budget.resources(),new_original_forecasts=0,source_vintage=p['clock']))

if __name__=='__main__':main()
