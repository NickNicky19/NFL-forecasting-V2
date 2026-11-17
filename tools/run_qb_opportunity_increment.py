"""Bounded new profile-value ablation; reuse every exact R0 forecast/model."""
import argparse, hashlib, json, platform, sys
from pathlib import Path
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import player_context_matchup as ctx
from nfl_v2 import qb_opportunity_increment as inc
from nfl_v2.passing_opportunity_profiles import OpportunityHistory, SOURCE_TIER
from nfl_v2.distribution_laws import prior
from nfl_v2.distribution_wave_v2 import FittedLawModel
from tools.run_player_context_wave import read,write,sha,now,prediction,Budget
BASE=ROOT/'reports/player-context-matchup-01/B'
OUT=ROOT/'reports/profile-increment-to-release-01/B'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run'])
    ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--max-origins',type=int);a=ap.parse_args();a.out=a.out.resolve();a.source=a.source.resolve()
    inputs=BASE/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz'
    files=[Path(__file__),ROOT/'nfl_v2/qb_opportunity_increment.py',ROOT/'nfl_v2/passing_opportunity_profiles.py',
           ROOT/'nfl_v2/player_context_matchup.py',ROOT/'nfl_v2/distribution_wave_v2.py',ROOT/'nfl_v2/distribution_laws.py']
    old=sorted((BASE/'qb-wave-v1/predictions').glob('*.json.gz'))
    if a.action=='prepare':
        a.out.mkdir(parents=True,exist_ok=False)
        base_order=read(BASE/'qb-wave-v1/FEATURE_ORDER_V1.json')['orders']['E3']
        write(a.out/'FEATURE_ORDER_V1.json',dict(orders={arm:inc.feature_order(base_order,arm)for arm in inc.ARMS},
            base_order_sha256=sha(BASE/'qb-wave-v1/FEATURE_ORDER_V1.json'),null_fill='Fixed0with explicitmissingindicator; no learned imputation.'))
        write(a.out/'FROZEN_PROTOCOL.json',dict(id=inc.VERSION,assignment='PROFILE-INCREMENT-TO-RELEASE-01 version2',
            registered_utc=now(),owner='B',coordinator='C',state='FROZEN_BEFORE_NEW_FITS_AND_SCORES',
            code_sha256={str(p.relative_to(ROOT)):sha(p)for p in files},feature_order_sha256=sha(a.out/'FEATURE_ORDER_V1.json'),inputs=dict(path=str(inputs.relative_to(ROOT)),sha256=sha(inputs)),
            source=dict(path=str(a.source.relative_to(ROOT)),sha256=sha(a.source)),
            reused_predictions=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p))for p in old],
            environment=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__),
            family='Exact retained E3 32-tree Leaf-CDF pass_cmp; new input columns require separately fitted R1/R2/R3. No changed optimizer or tuning.',
            arms=dict(R0='Reuse unchanged E3 forecasts and typed model; zero refits.',
                      R1='E3 plus opportunity-source denominator/unknown-dropback support. Existing age/games/depth support ALREADY_PRESENT.',
                      R2='R1 plus own/offense opportunity/dropback/attempt/sack/scramble/spike values, dropback context mixes and own share of past team dropbacks/attempts.',
                      R3='R2 plus raw/league-shrunk defensive opportunity and conversion-to-attempt values. Existing offense-adjusted completion residual retained in E3; new raw values are not newly opponent-adjusted talent.'),
            no_R4='No new interaction or unrestricted learner search; existing E3 interactions retained.',
            feature_policy='Original E3 own8/team16 + earlier2024 window/strength selection reused. New block fixed own8/team16,100pseudo-opportunity ratio shrinkage and4game volume shrinkage; no evaluated-outcome window tuning.',
            information_policy='H-RECENT fits previous season+earlier current labels; expanding2022 featurememory. Strict available<cutoff, available=kickoff+7days both training/query. Current revised data; not authenticated historical snapshots.',
            training_population='All role-appropriate qualified QB rows, not restricted to profiling priority or realized target starters.',
            query_population='Retained retrospective official-QB-stat-row panel; authentic pregame historical roster unavailable. Basic profiles for every retained query; no silent sparse-player deletion.',
            profiling_priority='UNCHANGED_COMMON_EXPOSURE_HISTORY_PRIORITY-v1: eligible own_games>0 and reference expected attempts>=10; reconstructed workload proxy only. No QB top20, no inferred actual starter. Basic nonpriority records retained.',
            recommendation_population='Separate exact retained112completion offers2026W5-8, all retained regardless of priority; quote timing unverified. No fabricated earlier or2025offers.',
            outputs=['mean','lower_median','valid_leaf_count_law'],joint_support='Standalone completion law; no claim of a coherent joint completion/attempt model or probability for saved unrelated attempt points.',
            fallback='Fixed missing-value0plus missing indicator in augmented features; no augmented-model fallback if fitted law valid. Existing5%earlier-label prior component remains part of every law, not a new coverage gain.',
            evaluation=[dict(season=2025,weeks=list(range(1,19))),dict(season=2026,weeks=list(range(1,9)))],
            strong_controls='E3/R0, saved adjusted/raw, constant sides, earlier prevalence, neutral0.25; strict-current-input Leaf on its84offered rows; prior H-RECENT Leaf/GLM controls remain visible. No universal ranking across unmatched scopes.',
            decisions=['CLOSE_RECIPE_NO_GAIN','INCONCLUSIVE','SHADOW_CANDIDATE','RELEASE_CANDIDATE'],
            stopping='Finish26origins for this one family/block, no outcome-driven retry. Use existing practical/support/tie policy; useful gain must survive strongest matched controls/coverage review. Inconclusive interval is not equivalence;90%not required. Exact direction/probability has4offerweeks, numerical26seasonweeks assessed separately. No production switch.',
            budget=dict(max_optimizer_fits=78,wall_seconds=1200,cpu_seconds=1800,max_threads=2,max_RSS_bytes=2147483648,public_retention_bytes=33554432,reserve_bytes=2097152,new_private_restricted_bytes=0),
            retention='Pilot3newtypedmodels and bound inputs/code/predictions must be GitHub-published/readback before broad run. Public-source derivatives only; private offer rows remain owner-local. Legacy recovery conditions unchanged.',
            original_issuance=False,new_paid_acquisition=False))
        print('FROZEN');return
    p=read(a.out/'FROZEN_PROTOCOL.json')
    for name,h in p['code_sha256'].items():assert sha(ROOT/name)==h,name
    assert sha(a.out/'FEATURE_ORDER_V1.json')==p['feature_order_sha256']
    assert sha(inputs)==p['inputs']['sha256']and sha(a.source)==p['source']['sha256']
    for r in p['reused_predictions']:assert sha(ROOT/r['path'])==r['sha256']
    budget=Budget(a.out,p);rows=ctx.load_inputs(inputs);history=ctx.ContextHistory(rows,8,20)
    source=read(a.source);op=OpportunityHistory(source['team_games'],source['QB_games'])
    completed=[]
    with threadpool_limits(limits=2):
        groups=[op.feature_groups(q)for q in rows]
        base=[history.direct_features(q,'E3')for q in rows]
        matrices={arm:np.asarray([np.concatenate([b,inc.appended_features(g,arm)])for b,g in zip(base,groups)])for arm in inc.ARMS[1:]}
        for oldfile in old:
            saved=read(oldfile);season,week,cutoff=saved['season'],saved['week'],saved['fit_cutoff']
            dest=a.out/'predictions'/f'{season}-W{week:02}.json.gz'
            if dest.exists():completed.append([season,week]);continue
            if a.max_origins is not None and len(completed)>=a.max_origins:break
            indices=[i for i,r in enumerate(rows)if r['physical_participation']and r['target_parity']and r['season']>=season-1 and r['available']<cutoff]
            train=[rows[i]for i in indices];queries=[(i,r)for i,r in enumerate(rows)if(r['season'],r['week'])==(season,week)]
            y=np.asarray([r['official_completions']for r in train]);pr=prior(y,'pass_cmp');pred=[]
            for r in saved['rows']:
                if r['method']=='E3':
                    q=next(q for _,q in queries if q['player_id']==r['player_id']and q['game_id']==r['game_id'])
                    pred.append(dict(r,procedure_id=inc.VERSION+':R0',method='R0',reused_original_procedure_id=r['procedure_id'],
                                     reused_artifact_sha256=sha(oldfile),profile_priority=inc.priority(q,history),new_inference=False))
            for arm in inc.ARMS[1:]:
                slot=f'{season}-W{week:02}-{arm}';fp=a.out/'fits'/(slot+'.json.gz')
                if fp.exists():payload=read(fp)['model']
                else:
                    budget.fit(slot);started=now()
                    m=FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(matrices[arm][indices],y,['QB']*len(train));payload=ctx.export_forest(m)
                    sample=matrices[arm][queries[0][0]];a1=m.predict(sample[None,:],['QB'],{'QB':pr})[0][0];b1=ctx.restored_forest_law(payload,sample,pr)
                    assert abs(a1.mean-b1.mean)<1e-10 and a1.quantile(.5)==b1.quantile(.5)
                    write(fp,dict(slot=slot,model=payload,training_rows=len(train),fit_cutoff=cutoff,new_optimizer_fits=1,
                        latest_training_label=max(r['available']for r in train),
                        training_membership_sha256=hashlib.sha256(json.dumps([(r['game_id'],r['player_id'])for r in train]).encode()).hexdigest(),
                        feature_count=matrices[arm].shape[1],actual_started_utc=started,actual_completed_utc=now(),restoration_mean_tolerance=1e-10))
                for i,q in queries:
                    l=ctx.restored_forest_law(payload,matrices[arm][i],pr)
                    r=prediction(q,arm,'pass_cmp',l,cutoff,history,model_slot=slot,features=matrices[arm][i],fallback='none')
                    r.update(procedure_id=inc.VERSION+':'+arm,profile_priority=inc.priority(q,history),
                             profile_source_tier=SOURCE_TIER,new_inference=True)
                    pred.append(r)
            write(dest,dict(season=season,week=week,fit_cutoff=cutoff,rows=pred,actual_persisted_utc=now(),original_issuance=False,resources=budget.resources()))
            completed.append([season,week]);print(json.dumps(dict(origin=[season,week],fits=budget.fit_calls)),flush=True)
    complete=len(completed)==26
    write(a.out/('RUN_RECEIPT.json'if complete else'PILOT_RECEIPT_1.json'),dict(state='COMPLETE'if complete else'PARTIAL_PILOT_RETAINED',
        completed_origins=completed,resources=budget.resources(),new_original_forecasts=0,reused_R0_origins=len(completed),
        remaining_origins=26-len(completed),source_vintage=p['information_policy']))

if __name__=='__main__':main()
