"""One FTN information ablation on the retained R3 completion law.

FTN-derived feature/model/prediction artifacts: CC-BY-SA-4.0, FTN Data via
nflverse, with separately attributed nflverse/nflfastR PBP/player-stat inputs.
"""
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import player_context_matchup as ctx
from nfl_v2 import qb_opportunity_increment as inc
from nfl_v2 import qb_ftn_information as info
from nfl_v2.passing_opportunity_profiles import OpportunityHistory
from nfl_v2.distribution_laws import prior
from nfl_v2.distribution_wave_v2 import FittedLawModel
from tools.run_player_context_wave import Budget, read,write,sha,now,prediction

BASE=ROOT/'reports/player-context-matchup-01/B'
PREV=ROOT/'reports/profile-increment-to-release-01/B'
PACKAGE=ROOT/'reports/information-first-20261112-01/B'
VERSION='B-FTN-BALL-QUALITY-COMPLETION-v1'
TIER='CURRENT_VINTAGE_FTN_SEVEN_DAY_CHRONOLOGICAL_DIAGNOSTIC_NOT_ORIGINAL_ISSUANCE'


def old_predictions():
    return {(r['game_id'],r['player_id']):r for f in sorted((PREV/'opportunity-wave-v1/predictions').glob('*.json.gz'))
            for r in read(f)['rows']if r['method']=='R3'}


def source_rows():
    old=read(BASE/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz')
    new=read(PACKAGE/'source-qualification/QB_CONTEXT_W9_EXTENSION_V1.json.gz')
    assert len(old)==2901 and len(new)==38
    rows=old+new;assert len({(r['game_id'],r['player_id'])for r in rows})==2939
    return rows


def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run'])
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--max-origins',type=int)
    a=ap.parse_args();a.out=a.out.resolve()
    rows=source_rows();old=old_predictions()
    if a.action=='prepare':
        a.out.mkdir(parents=True,exist_ok=False)
        write(a.out/'QB_CONTEXT_W1_W9_INPUTS_V1.json.gz',rows)
        history=ctx.ContextHistory(rows,8,20)
        qpath=PACKAGE/'source-qualification/FTN_BALL_QUALITY_QB_GAME_INPUTS_V1.json.gz'
        quality=read(qpath);information=info.QBFTNInformation(history,quality,window=8,strength=20)
        opath=PREV/'source-profiles/PASSING_OPPORTUNITY_GAME_INPUTS_V2.json.gz'
        osource=read(opath);op=OpportunityHistory(osource['team_games'],osource['QB_games'])
        features=[];max_parity=0.;oldchecked=0
        for q in rows:
            d=information.describe(q)
            if q['season']<2024:continue
            k=q['game_id'],q['player_id']
            fresh=np.concatenate([history.direct_features(q,'E3'),inc.appended_features(op.feature_groups(q),'R3')])
            if k in old:
                saved=np.asarray(old[k]['features'],dtype=float)
                assert fresh.shape==saved.shape and np.allclose(fresh,saved,rtol=0,atol=1e-10,equal_nan=True),k
                finite=np.isfinite(fresh)&np.isfinite(saved)
                max_parity=max(max_parity,float(np.max(np.abs(fresh[finite]-saved[finite]))))
                base=saved.tolist();oldchecked+=1
            else:base=fresh.tolist()
            features.append(dict(game_id=q['game_id'],player_id=q['player_id'],season=q['season'],week=q['week'],
                B0_features=base,information=d,B2_appended=info.feature_values(d,'B2')if d['complete_required_charting']else[None,None],
                fallback_to_B0=not d['complete_required_charting']))
        assert oldchecked==941
        write(a.out/'FEATURE_INPUTS_V1.json.gz',features)
        order=read(PREV/'opportunity-wave-v1/FEATURE_ORDER_V1.json')['orders']['R3']
        write(a.out/'FEATURE_ORDER_V1.json',dict(orders={'B0':order,'B1':order,'B2':order+info.feature_order('B2')},
            B1='ExactB0alias: allcreditedattemptsFTNmatched/known; chart-specificsupportcontainsnonewmeasurement; ordinaryhistoryrepresentationdiagnosticsnotappended.'))
        files=[Path(__file__),ROOT/'nfl_v2/qb_ftn_information.py',ROOT/'nfl_v2/player_context_matchup.py',ROOT/'nfl_v2/qb_opportunity_increment.py',
               ROOT/'nfl_v2/passing_opportunity_profiles.py',ROOT/'nfl_v2/distribution_wave_v2.py',ROOT/'nfl_v2/distribution_laws.py',ROOT/'nfl_v2/hgb_control.py']
        write(a.out/'BASE_FEATURE_PARITY_V1.json',dict(rows_checked=941,max_finite_difference=max_parity,tolerance=1e-10,
            old_arrays_reused=True,W9_future_target_rows_added=True,source_feature_history_unchanged=True,
            scope='EveryretainedR3evaluationfeaturearrayrecomputedwithcombinedW9source; noearlierfeaturechange.'))
        write(a.out/'FROZEN_PROTOCOL.json',dict(id=VERSION,document='ABC-INFORMATION-FIRST-20261112-01',registered_UTC=now(),state='FROZEN_BEFORE_NEW_FITS_AND_COMPARATIVE_SCORES',
            owner='B',coordinator='C',code_sha256={str(p.relative_to(ROOT)):sha(p)for p in files},
            inputs_sha256=sha(a.out/'QB_CONTEXT_W1_W9_INPUTS_V1.json.gz'),features_sha256=sha(a.out/'FEATURE_INPUTS_V1.json.gz'),
            quality_source_sha256=sha(qpath),opportunity_source_sha256=sha(opath),feature_order_sha256=sha(a.out/'FEATURE_ORDER_V1.json'),
            old_predictions=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p))for p in sorted((PREV/'opportunity-wave-v1/predictions').glob('*.json.gz'))],
            hypothesis='Laggedthrowawayandinterception-worthy rates improveexact-linecompletions beyondordinaryR3history; no repeatedcatchability/drop/contestedtest.',
            arms={'B0':'Strongestinspectednativebroad112mean-directionR3(61/112); exactsavedoutputsreused,W9baselinefitonlywhereabsent.',
                  'B1':'Output-preservingB0alias aftercompletechartingcoverage/supportequivalencecheck; nonewFTNsupportblockexistsinthissourcepanel. Donotfitredundantcolumnsjusttorandomizeforest.',
                  'B2':'SamefixedR3learner plus two earlier-onlyBeta-shrunk own8throwaway/IWP rates. Partialrequiredcharting→exactB0fallback, neverabstention/zeroimputation.'},
            support_scope='Counts/knownness/agesretainedintrace. Thisdoesnotclaimall17diagnosticcolumnsarealreadyR3featurecolumns: ordinary-history-derivedrepresentationsareoutsideoneFTNvaluecontrast.',
            feature_policy='Selectlast8eligibleQBappearancesbygametimeafteravailabilityadmission, thenjoincharting; no matched-game reachback. GlobalprioronlyeligiblecanonicalQBhistory; Beta(1,1) pooledrate,20pseudoattemptshrinkstrength fixedbeforecomparisons.',
            chronology='Sameoriginal7daydeclaredavailabilitypolicyintrainingandquery; strict<; weeklyfitbeforeearliestgame; H-RECENTpreviousseason+earliercurrentlabels; expanding2022featurememory. FTNdate_pulled is retrieval, neverhistoricalpubtime.',
            vintage=TIER,raw_sources='Frozen2022-25/frozen2026W1-8, current2026W9appendonly; sourcebindingsinqualificationreceipt. No revisedold-week substitution.',
            evaluation=[dict(season=2025,weeks=list(range(1,19))),dict(season=2026,weeks=list(range(1,10)))],
            population='RetrospectiveofficialQBstat-rowqueries,notauthenticatedpregamestarteruniverse; expected979evalqueries including315current2026. Allzeroattempt/sparsecaseskeptunderqualifiedcredits.',
            main_offers='Native112CMPW5-8plusseparatelyserver-bound30W9=142diagnosticthresholds; W1-4missing, Aannual88privatepanelnotinherited.',
            learner='Unchanged32-treeExtraTreesLeaf-CDF seed1701,maxdepth8,minleaf30,95%empirical+5%sameoriginprior; no settings/tuning change.',
            outputs=['mean','lower_median','standalone_completion_count_law'],primary_policy='P1_MEAN strictunroundedpoint/line; no website margin substitution.',
            probability_policy='ExactlawOver/Under mass,tieabstain,retainpushmass; no confidence/EVfrompoint. StandaloneCMP,notanewjointATT/CMPmodel.',
            selective='UnchangedP90andregisteredchronologicalrollingTop6/10/20; wholeboardmandatory, no forcedquota/thresholdorconfidenceoptimization. RetrospectivediagnosticnotwebsiteTopPicks.',
            earlier_validation='Own8/strength20retained2024selection; no2022-24earlier-onlyperformanceclaimunderthisconfiguration. Historical2022-24sourcecoverageisnotpredictiveevidence.',
            controls='OwnR3baseline, savedadjusted/rawpoints,actualsavedincumbentleanswhereboundwithcoverage,separateconstants/earlierprevalence/neutral. StrongAannualcontrolsseparateownerlocalpanel.',
            stopping='Finishone27originpackage;nooutcome-drivenseeds/lags/offsets/gates/newfamilies. TARGET_NOT_ESTABLISHEDunlessactualsupportedfixedpolicyrecordqualifies; zeroselN/A. Keepusefulsub90numericalseparate.',
            license='FTNData via nflverse CC-BY-SA-4.0 forFTN-derivedinputs/models/predictions/scores; underlyingPBPstatsCC-BY-4.0attribution. No rawfeed/protectedofferredistribution.',
            retention='Publish/readbacksource/code/derivedinputs/protocolandfirsttypedpilotmodelbeforebroadexecution. AlltypedJSON,safeinference,nopickleloading.',
            environment=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__),
            budget=dict(max_optimizer_fits=28,wall_seconds=1200,cpu_seconds=1800,max_threads=2,max_RSS_bytes=2147483648,public_retention_bytes=33554432,reserve_bytes=2097152,new_private_restricted_bytes=0),
            verification_budget='Oneindependent2026W1B2freshfit plusoptionaltwocurrentoriginreference/challengerfitswithinadopted58NFLcap;nosyntheticfitcountsasNFLdata.',
            original_issuance=False,original_site_writes=0))
        print(json.dumps(dict(state='FROZEN',inputs=len(rows),feature_rows=len(features),reused_old_features=oldchecked,max_parity=max_parity)))
        return
    p=read(a.out/'FROZEN_PROTOCOL.json')
    for name,h in p['code_sha256'].items():assert sha(ROOT/name)==h,name
    for name,k in [('QB_CONTEXT_W1_W9_INPUTS_V1.json.gz','inputs_sha256'),('FEATURE_INPUTS_V1.json.gz','features_sha256'),('FEATURE_ORDER_V1.json','feature_order_sha256')]:assert sha(a.out/name)==p[k]
    for r in p['old_predictions']:assert sha(ROOT/r['path'])==r['sha256']
    rows=ctx.load_inputs(a.out/'QB_CONTEXT_W1_W9_INPUTS_V1.json.gz');history=ctx.ContextHistory(rows,8,20)
    feature_rows=read(a.out/'FEATURE_INPUTS_V1.json.gz');fm={(r['game_id'],r['player_id']):r for r in feature_rows}
    fitrows=[q for q in rows if q['season']>=2024];x0=np.asarray([fm[q['game_id'],q['player_id']]['B0_features']for q in fitrows],dtype=float)
    x2=np.asarray([fm[q['game_id'],q['player_id']]['B0_features']+fm[q['game_id'],q['player_id']]['B2_appended']for q in fitrows],dtype=float)
    budget=Budget(a.out,p);completed=[]
    plan=[(season,w)for season,ww in [(2025,range(1,19)),(2026,range(1,10))]for w in ww]
    with threadpool_limits(limits=2):
        for season,week in plan:
            dest=a.out/'predictions'/f'{season}-W{week:02}.json.gz'
            if dest.exists():completed.append([season,week]);continue
            if a.max_origins is not None and len(completed)>=a.max_origins:break
            queries=[(i,q)for i,q in enumerate(fitrows)if(q['season'],q['week'])==(season,week)]
            cutoff=min(q['kickoff']for i,q in queries)
            indices=[i for i,q in enumerate(fitrows)if q['physical_participation']and q['target_parity']and q['season']>=season-1 and q['available']<cutoff]
            y=np.asarray([fitrows[i]['official_completions']for i in indices]);pr=prior(y,'pass_cmp');forecasts=[];basepayload=None
            for arm,x in [('B0',x0),('B2',x2)]:
                needfit=arm=='B2'or(season,week)==(2026,9)
                payload=None
                if needfit:
                    slot=f'{season}-W{week:02}-{arm}';fp=a.out/'fits'/(slot+'.json.gz')
                    if fp.exists():payload=read(fp)['model']
                    else:
                        budget.fit(slot);started=now();model=FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(x[indices],y,['QB']*len(indices));payload=ctx.export_forest(model)
                        sample=x[queries[0][0]];l=model.predict(sample[None,:],['QB'],{'QB':pr})[0][0];r=ctx.restored_forest_law(payload,sample,pr)
                        assert abs(l.mean-r.mean)<1e-10 and l.quantile(.5)==r.quantile(.5)
                        write(fp,dict(slot=slot,model=payload,training_rows=len(indices),fit_cutoff=cutoff,latest_training_label=max(fitrows[i]['available']for i in indices),
                            training_membership_sha256=hashlib.sha256(json.dumps([(fitrows[i]['game_id'],fitrows[i]['player_id'])for i in indices]).encode()).hexdigest(),
                            actual_started_UTC=started,actual_completed_UTC=now(),feature_count=x.shape[1],feature_order_sha256=p['feature_order_sha256'],new_optimizer_fits=1))
                for i,q in queries:
                    k=q['game_id'],q['player_id'];f=fm[k]
                    if arm=='B0'and not needfit:
                        r=dict(old[k],method='B0',procedure_id=VERSION+':B0',reused_original_procedure_id=old[k]['procedure_id'],new_inference=False)
                    elif arm=='B2'and f['fallback_to_B0']:
                        r=dict(next(z for z in forecasts if z['method']=='B0'and(z['game_id'],z['player_id'])==k),method='B2',procedure_id=VERSION+':B2',fallback='B0_INCOMPLETE_FTN_SOURCE',new_inference=False)
                    else:
                        law=ctx.restored_forest_law(payload,x[i],pr)
                        r=prediction(q,arm,'pass_cmp',law,cutoff,history,model_slot=f'{season}-W{week:02}-{arm}',features=x[i],fallback='none')
                        r.update(procedure_id=VERSION+':'+arm,new_inference=True)
                    r.update(FTN_information=f['information'],source_vintage=TIER,FTN_license='CC-BY-SA-4.0;FTNData via nflverse')
                    forecasts.append(r)
                    if arm=='B0':forecasts.append(dict(r,method='B1',procedure_id=VERSION+':B1',support_alias_of=VERSION+':B0',new_inference=False))
            write(dest,dict(season=season,week=week,fit_cutoff=cutoff,rows=forecasts,actual_persisted_UTC=now(),original_issuance=False,resources=budget.resources()))
            completed.append([season,week]);print(json.dumps(dict(origin=[season,week],fits=budget.fit_calls)),flush=True)
    complete=len(completed)==27
    write(a.out/('RUN_RECEIPT.json'if complete else'PILOT_RECEIPT_V1.json'),dict(state='COMPLETE'if complete else'PILOT_RETAINED',completed_origins=completed,remaining_origins=27-len(completed),
        resources=budget.resources(),B1_alias_fits=0,new_NFL_calendar_games=0,new_original_issues=0,source_vintage=TIER))


if __name__=='__main__':main()
