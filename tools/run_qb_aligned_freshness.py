"""One aligned timing x retained-profile information test; no learner search."""
import argparse, hashlib, json, platform, sys
from pathlib import Path
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import player_context_matchup as ctx
from nfl_v2 import qb_opportunity_increment as inc
from nfl_v2.qb_aligned_freshness import AlignedFreshnessBundle, ALTERNATIVE
from nfl_v2.distribution_laws import prior
from nfl_v2.distribution_wave_v2 import FittedLawModel
from tools.run_player_context_wave import read,write,sha,now,prediction,Budget
BASE=ROOT/'reports/player-context-matchup-01/B'
PREV=ROOT/'reports/profile-increment-to-release-01/B'
VERSION='B-QB-ALIGNED-FRESHNESS-v1'
POLICY=ALTERNATIVE

def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run'])
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--max-origins',type=int)
    a=ap.parse_args();a.out=a.out.resolve()
    inputs=BASE/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz'
    source=PREV/'source-profiles/PASSING_OPPORTUNITY_GAME_INPUTS_V2.json.gz'
    old=sorted((PREV/'opportunity-wave-v1/predictions').glob('*.json.gz'))
    files=[Path(__file__),ROOT/'nfl_v2/qb_aligned_freshness.py',ROOT/'nfl_v2/qb_opportunity_increment.py',
           ROOT/'nfl_v2/passing_opportunity_profiles.py',ROOT/'nfl_v2/player_context_matchup.py',
           ROOT/'nfl_v2/distribution_wave_v2.py',ROOT/'nfl_v2/distribution_laws.py',ROOT/'nfl_v2/hgb_control.py']
    if a.action=='prepare':
        a.out.mkdir(parents=True,exist_ok=False)
        orders=read(PREV/'opportunity-wave-v1/FEATURE_ORDER_V1.json')['orders']
        write(a.out/'FEATURE_ORDER_V1.json',dict(orders={f:orders[r]for f,r in [('F0','R0'),('F1','R2'),('F2','R0'),('F3','R2')]},
            unchanged_prior_order_sha256=sha(PREV/'opportunity-wave-v1/FEATURE_ORDER_V1.json')))
        write(a.out/'FROZEN_PROTOCOL.json',dict(id=VERSION,continuation='PROFILE-INCREMENT-CLOSURE-AND-NEXT-02',
            registered_utc=now(),owner='B',coordinator='C',state='FROZEN_BEFORE_NEW_FITS_AND_SCORES',
            code_sha256={str(p.relative_to(ROOT)):sha(p)for p in files},
            feature_order_sha256=sha(a.out/'FEATURE_ORDER_V1.json'),
            inputs=dict(path=str(inputs.relative_to(ROOT)),sha256=sha(inputs)),
            opportunity_source=dict(path=str(source.relative_to(ROOT)),sha256=sha(source)),
            reused_predictions=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p))for p in old],
            environment=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__),
            closest_completed='Old availability A/B/C transferred query information and limited Week7 refit; historical training features retained seven days. No complete aligned E3/R2 timing/profile test found. Prior R0/R1/R2/R3 and failed confidence/catchability recipes remain closed.',
            bottleneck='Measured age of admitted history and weak confidence ordering motivate a timing hypothesis; source clocks are not authenticated. No implementation bug or freshness benefit presumed.',
            alternative_policy=POLICY,alternative_delay_hours=48,
            rationale='A fixed two-day delay tests exclusion of the immediately preceding completed-game information without putting results at kickoff. It is an operational sensitivity assumption chosen before scores, not an observed release time, guarantee of final corrections, or evidence that revised values existed then.',
            source_tier='CURRENT_REVISED_SOURCE_RECONSTRUCTED_TIMING_SENSITIVITY_NOT_AUTHENTICATED_HISTORICAL_VINTAGES',
            unknown_clock='Require original finite declared seven-day source clock; explicitly unknown clocks remain unadmitted, never replaced with the alternative. Strict less-than unchanged; recent games chosen by game time after admission.',
            alignment='Alternative clocks govern EVERY historical feature, upstream offense-quality reference/defense residual, training label, prior, and query. Existing E3 defensive information is retained and recomputed under its policy. No NEW R3 defense or current-role addition.',
            arms=dict(F0='Reuse exact original E3/R0 under original7day policy.',F1='Reuse exact original R2 profile recipe under original7day policy.',
                      F2='Same E3 columns/learner under aligned48h reconstruction.',F3='Same R2 columns/learner under aligned48h reconstruction.'),
            contrasts=['F1-F0 PROFILE_AT_7D','F2-F0 TIMING_WITHOUT_ADDED_PROFILE','F3-F2 PROFILE_AT_48H','F3-F1 TIMING_WITH_ADDED_PROFILE'],
            separate_defense='Previously executed R3-R2 defense effect retained from prior package; not refit/reinterpreted as new defense evidence.',
            learner='Unchanged 32-tree ExtraTrees Leaf-CDF settings/objective, seed1701, empirical95%+sameorigin5%prior. Mean/lower median/exact law separate.',
            fit='Weekly origins before earliest game; H-RECENT previousseason+earliercurrent labels. Feature memory expanding2022. No current fitted model substituted for historical origin.',
            tuning='Reuse fixed own8/team16, strength20 selected on earlier2024 under originalpolicy; profile100pseudocount/4gameprior unchanged. No new tuning. This fixed-settings information ablation does not claim48h-optimal settings.',
            population='Same941retrospective QB-stat-row queries; source/role membership limitation preserved. Fixed original7day history-priority/cohort labels; no target starter/usage filtering.',
            recommendation_panel='Retained112CMPoffers2026W5-8. EarlierA88CMP inventory is a separate owner-local join; privateArows not assumed accessible. Prices missing, quote execution unverified.',
            evaluation=[dict(season=2025,weeks=list(range(1,19))),dict(season=2026,weeks=list(range(1,9)))],
            outputs=['mean','lower_median','explicit_leaf_count_law'],
            full_system='All query rows retained. No technical-failure-to-abstention conversion. Prior/own-history and profile support reported separately; no invented direct-model component forecasts.',
            controls='Own unchanged baseline first; savedadjusted/raw, prevalence, bothconstants, neutral0.25; retainedstrictCURRENT on84sharedrows; incompatible origins/populations not merged into a champion.',
            decision='Complete52neworiginfits once. Existing practical/support/tie policies, no new accuracy/significance floor. No forced90%picks. Close a valid negative timing hypothesis; inconclusive is not equivalence. Later capture requires actualqualifiedsources/owner; no automatic release.',
            budget=dict(max_optimizer_fits=52,wall_seconds=1200,cpu_seconds=1800,max_threads=2,max_RSS_bytes=2147483648,
                        public_retention_bytes=25165824,reserve_bytes=2097152,new_private_restricted_bytes=0),
            retention='Publish/readback bound original inputs/code/protocol and two typedpilot models/predictions before broad run. Existing public-source derivative lane, legacy protected recovery obligations unchanged.',
            original_issuance=False,production_changes=0))
        print('FROZEN');return
    p=read(a.out/'FROZEN_PROTOCOL.json')
    for file,h in p['code_sha256'].items():assert sha(ROOT/file)==h,file
    assert sha(inputs)==p['inputs']['sha256']and sha(source)==p['opportunity_source']['sha256']
    assert sha(a.out/'FEATURE_ORDER_V1.json')==p['feature_order_sha256']
    for r in p['reused_predictions']:assert sha(ROOT/r['path'])==r['sha256']
    budget=Budget(a.out,p);original=ctx.load_inputs(inputs);raw_source=read(source)
    bundle=AlignedFreshnessBundle(original,raw_source,policy_id=POLICY)
    rows=bundle.rows;history=bundle.history
    # Cohort selection stays identical across the four information policies.
    original_history=ctx.ContextHistory(original,8,20)
    completed=[]
    with threadpool_limits(limits=2):
        matrices={arm:np.asarray([bundle.direct_features(q,arm)for q in rows])for arm in ('F2','F3')}
        for oldfile in old:
            saved=read(oldfile);season,week,cutoff=saved['season'],saved['week'],saved['fit_cutoff']
            dest=a.out/'predictions'/f'{season}-W{week:02}.json.gz'
            if dest.exists():completed.append([season,week]);continue
            if a.max_origins is not None and len(completed)>=a.max_origins:break
            train=bundle.training_rows(season,cutoff);identities={(r['game_id'],r['player_id'])for r in train}
            indices=[i for i,r in enumerate(rows)if(r['game_id'],r['player_id'])in identities]
            assert len(indices)==len(train)
            queries=[(i,r)for i,r in enumerate(rows)if(r['season'],r['week'])==(season,week)]
            y=np.asarray([rows[i]['official_completions']for i in indices]);pr=prior(y,'pass_cmp');pred=[]
            original_refs={(r['game_id'],r['player_id']):r for r in saved['rows']if r['method']=='R0'}
            for r in saved['rows']:
                if r['method']in('R0','R2'):
                    arm='F0'if r['method']=='R0'else'F1'
                    pred.append(dict(r,procedure_id=VERSION+':'+arm,method=arm,reused_original_procedure_id=r['procedure_id'],
                                     reused_artifact_sha256=sha(oldfile),information_policy='ORIGINAL_SEVEN_DAY_RECONSTRUCTION',new_inference=False))
            for arm in ('F2','F3'):
                slot=f'{season}-W{week:02}-{arm}';fp=a.out/'fits'/(slot+'.json.gz')
                if fp.exists():payload=read(fp)['model']
                else:
                    budget.fit(slot);started=now()
                    m=FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(matrices[arm][indices],y,['QB']*len(indices));payload=ctx.export_forest(m)
                    sample=matrices[arm][queries[0][0]];a1=m.predict(sample[None,:],['QB'],{'QB':pr})[0][0];b1=ctx.restored_forest_law(payload,sample,pr)
                    assert abs(a1.mean-b1.mean)<1e-10 and a1.quantile(.5)==b1.quantile(.5)
                    write(fp,dict(slot=slot,model=payload,new_optimizer_fits=1,fit_cutoff=cutoff,training_rows=len(indices),
                        training_membership_sha256=hashlib.sha256(json.dumps([(rows[i]['game_id'],rows[i]['player_id'])for i in indices]).encode()).hexdigest(),
                        latest_training_label=max(r['available']for r in train),feature_count=matrices[arm].shape[1],
                        feature_order_sha256=p['feature_order_sha256'],information_policy=POLICY,
                        actual_started_utc=started,actual_completed_utc=now(),restoration_mean_tolerance=1e-10))
                for i,q in queries:
                    l=ctx.restored_forest_law(payload,matrices[arm][i],pr)
                    r=prediction(q,arm,'pass_cmp',l,cutoff,history,model_slot=slot,features=matrices[arm][i],fallback='none')
                    fixed=original_refs[q['game_id'],q['player_id']]
                    r.update(procedure_id=VERSION+':'+arm,information_policy=POLICY,new_inference=True,
                        source_vintage=p['source_tier'],model_policy_role_band=r['pregame_role_band'],pregame_role_band=fixed['pregame_role_band'],
                        profile_priority=fixed['profile_priority'],latest_source_policy_assumption_hours=48)
                    pred.append(r)
            write(dest,dict(season=season,week=week,fit_cutoff=cutoff,rows=pred,actual_persisted_utc=now(),original_issuance=False,resources=budget.resources()))
            completed.append([season,week]);print(json.dumps(dict(origin=[season,week],fits=budget.fit_calls)),flush=True)
    complete=len(completed)==26
    write(a.out/('RUN_RECEIPT.json'if complete else'PILOT_RECEIPT_1.json'),dict(state='COMPLETE'if complete else'PARTIAL_PILOT_RETAINED',
        completed_origins=completed,remaining_origins=26-len(completed),resources=budget.resources(),reused_F0_F1_origins=len(completed),
        new_original_forecasts=0,new_real_calendar_weeks=0,source_vintage=p['source_tier']))

if __name__=='__main__':main()
