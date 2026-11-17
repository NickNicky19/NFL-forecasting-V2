"""Complete one missing origin of existing QB procedures, without searching.

Only the original E3 forest, aligned-48h F2 forest, and shared P1 conversion
model are fitted. The common attempt law is analytic. All old bytes remain.
"""
import argparse,hashlib,json,platform,sys
from pathlib import Path
import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import player_context_matchup as ctx
from nfl_v2.qb_aligned_freshness import AlignedFreshnessBundle,ALTERNATIVE
from nfl_v2.distribution_laws import prior
from nfl_v2.distribution_wave_v2 import FittedLawModel
from tools.run_player_context_wave import read,write,sha,now,prediction,Budget

BASE=ROOT/'reports/w1w9-comparison-closure-01/B'
OUT=BASE/'modern-completion-extension'
OLD=ROOT/'reports/player-context-matchup-01/B'
INCREMENT=ROOT/'reports/profile-increment-to-release-01/B'
ALIGNED=ROOT/'reports/profile-increment-closure-next-02/B/aligned-wave-v1'
INPUTS=ROOT/'reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz'
OPPORTUNITY=INCREMENT/'source-profiles/PASSING_OPPORTUNITY_GAME_INPUTS_V2.json.gz'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run']);a=ap.parse_args()
    rows=ctx.load_inputs(INPUTS);history=ctx.ContextHistory(rows,8,20)
    bundle=AlignedFreshnessBundle(rows,read(OPPORTUNITY),policy_id=ALTERNATIVE)
    fixed=read(OLD/'qb-wave-v1/SELECTED_EARLIER_CONFIG.json')
    assert fixed['window']==8 and fixed['strength']==20.
    if a.action=='prepare':
        OUT.mkdir(exist_ok=False)
        max_diff={};checks={};old_bindings=[]
        for label,folder,arm,h in [('E3',OLD/'qb-wave-v1/predictions','E3',history),('F2',ALIGNED/'predictions','F2',bundle.history)]:
            maximum=0.;n=0
            bykey={(q['game_id'],q['player_id']):q for q in(h.all_rows)}
            for path in sorted(folder.glob('*.json.gz')):
                old_bindings.append(dict(path=str(path.relative_to(ROOT)),sha256=sha(path)))
                for r in read(path)['rows']:
                    if r['method']!=arm:continue
                    q=bykey[r['game_id'],r['player_id']]
                    x=h.direct_features(q,'E3')if label=='E3'else bundle.direct_features(q,'F2')
                    old=np.asarray(r['features'],float)
                    assert np.allclose(x,old,rtol=0,atol=1e-10,equal_nan=True),(label,r['game_id'],r['player_id'])
                    ok=np.isfinite(x)&np.isfinite(old)
                    maximum=max(maximum,float(np.max(np.abs(x[ok]-old[ok]))));n+=1
            assert n==941,(label,n);max_diff[label]=maximum;checks[label]=n
        # R0/F0 is an alias of E3, not a newly named fit.
        e3={(r['game_id'],r['player_id']):r for p in(OLD/'qb-wave-v1/predictions').glob('*.json.gz')for r in read(p)['rows']if r['method']=='E3'}
        aliases=0
        for p in(INCREMENT/'opportunity-wave-v1/predictions').glob('*.json.gz'):
            for r in read(p)['rows']:
                if r['method']!='R0':continue
                old=e3[r['game_id'],r['player_id']]
                assert r['mean']==old['mean']and r['lower_median']==old['lower_median']and r['law']==old['law'];aliases+=1
        assert aliases==941
        write(OUT/'FEATURE_AND_ALIAS_PARITY_V1.json',dict(old_feature_rows_checked=checks,max_finite_difference=max_diff,tolerance=1e-10,E3_R0_alias_rows=aliases,future_W9_records_added=True,old_predictions_unchanged=True))
        code=[Path(__file__),ROOT/'nfl_v2/player_context_matchup.py',ROOT/'nfl_v2/qb_aligned_freshness.py',ROOT/'nfl_v2/qb_opportunity_increment.py',ROOT/'nfl_v2/distribution_wave_v2.py',ROOT/'nfl_v2/distribution_laws.py',ROOT/'nfl_v2/hgb_control.py']
        write(OUT/'FROZEN_EXECUTION_PROTOCOL_V1.json',dict(id='B_EXISTING_QB_W9_ORIGIN_COMPLETION_v1',registered_UTC=now(),owner='B_ROOT',state='FROZEN_BEFORE_THREE_NEW_MISSING_ORIGIN_FITS_AND_COMPARATIVE_SCORING',
            frozen_roster_sha256=sha(BASE/'roster/FROZEN_B_CONTRIBUTION_ROSTER_V1.json'),inputs=dict(path=str(INPUTS.relative_to(ROOT)),sha256=sha(INPUTS)),opportunity=dict(path=str(OPPORTUNITY.relative_to(ROOT)),sha256=sha(OPPORTUNITY)),
            code_sha256={str(p.relative_to(ROOT)):sha(p)for p in code},old_bindings=old_bindings,
            exact_recipes=dict(E3=ctx.VERSION+':E3 = R0/F0 unchanged7day',F2='B-QB-ALIGNED-FRESHNESS-v1:F2 unchangedaligned48h',P1=ctx.VERSION+':P1 sharedconditional;own8strength20',COMMON_EXPOSURE=ctx.VERSION+':COMMON_EXPOSURE analyticattemptlaw'),
            origin=dict(season=2026,week=9,fit_cutoff='Beforeearliesttargetweekgame',feature_cutoff='Eachquerykickoffleftlimit;historicaldiagnosticnotoriginalissuance',training='H-RECENTpreviousseason+eligibleearliercurrent;strictavailable<fitcutoff;preprocessing/priorsfitearlieronly'),
            source_tier='Current-vintage7dayandretained48hreconstructedpoliciesseparate;nohistoricalpublicationauthentication',
            no_new_mechanism=True,no_new_settings=True,no_new_history_selection=True,new_origin_only=True,old_completed_studies_not_reopened=True,
            unused_opportunity_W9='E3/F2useR0(emptyappendedprofile);P1/COMMON_EXPOSUREusecontext history. No W9opportunity-profileinputrequirementimposedwhennotconsumed.',
            output='Typedmean,lower_median,fullstandalonecompletionlaw;P1retainsthinnedexposurecomponents. No arbitrarycross-statcapsontheforestlaw.',
            environment=dict(python=platform.python_version(),numpy=np.__version__,sklearn=sklearn.__version__),
            budget=dict(max_optimizer_fits=3,wall_seconds=600,cpu_seconds=900,max_threads=2,max_RSS_bytes=2147483648,public_retention_bytes=8388608,reserve_bytes=1048576),
            retention='Existinglicensedsource/modelcodeandcombinedW9inputs alreadypublished/readbackinpriorwave;thisassembly+parity/protocolpublishedbeforeoriginfits;trustedJSONonly. No protectedofferrowsincluded.',original_issuance=False))
        print(json.dumps(dict(state='FROZEN',parity=checks,max_diff=max_diff,E3_alias=aliases)));return
    p=read(OUT/'FROZEN_EXECUTION_PROTOCOL_V1.json')
    assert sha(INPUTS)==p['inputs']['sha256']and sha(OPPORTUNITY)==p['opportunity']['sha256']
    for name,h in p['code_sha256'].items():assert sha(ROOT/name)==h
    for r in p['old_bindings']:assert sha(ROOT/r['path'])==r['sha256']
    budget=Budget(OUT,p);forecasts=[];query=[r for r in rows if(r['season'],r['week'])==(2026,9)];cutoff=min(r['kickoff']for r in query)
    with threadpool_limits(limits=2):
        for arm,h,source in [('E3',history,rows),('F2',bundle.history,bundle.rows),('P1',history,rows)]:
            train=[r for r in source if r['physical_participation']and r['target_parity']and r['season']>=2025 and r['available']<cutoff]
            targets=np.asarray([r['official_completions']for r in train]);qs=[r for r in source if(r['season'],r['week'])==(2026,9)]
            fp=OUT/'fits'/(arm+'.json.gz');budget.fit('2026-W09-'+arm);started=now()
            if arm in('E3','F2'):
                feature=lambda q:h.direct_features(q,'E3')if arm=='E3'else bundle.direct_features(q,'F2')
                xx=np.asarray([feature(r)for r in train]);model=FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(xx,targets,['QB']*len(train));payload=ctx.export_forest(model);pr=prior(targets,'pass_cmp')
            else:
                model=ctx.CompletionModel(False,20).fit(train,h);assert model is not None;payload=model.payload()
            write(fp,dict(model=payload,new_optimizer_fits=1,actual_started_UTC=started,actual_completed_UTC=now(),training_rows=len(train),fit_cutoff=cutoff,latest_training_label=max(r['available']for r in train),
                training_membership_sha256=hashlib.sha256(json.dumps([(r['game_id'],r['player_id'])for r in train]).encode()).hexdigest(),original_procedure=ctx.VERSION+':'+arm if arm!='F2'else'B-QB-ALIGNED-FRESHNESS-v1:F2'))
            for q in qs:
                extra={}
                if arm in('E3','F2'):
                    x=feature(q);law=ctx.restored_forest_law(payload,x,pr);fresh=model.predict(x[None,:],['QB'],{'QB':pr})[0][0]
                    assert abs(law.mean-fresh.mean)<1e-10 and law.quantile(.5)==fresh.quantile(.5);extra['features']=x
                else:
                    exposure=h.exposure(q);d=h.describe(q);prob=model.probabilities(q,h);integrated=float(d['mix']@prob);assert 0<=integrated<=1
                    law=ctx.CountLaw(exposure.mean*integrated,exposure.shape);restored=ctx.CompletionModel.restore(payload).probabilities(q,h);assert np.allclose(restored,prob,rtol=0,atol=1e-12)
                    extra['components']=dict(attempt_law=exposure.parameters(),predicted_context_mix=d['mix'],conditional_completion_probability=prob,integrated_completion_probability=integrated)
                r=prediction(q,arm,'pass_cmp',law,cutoff,h,model_slot='2026-W09-'+arm,fallback=h.describe(q)['fallback']if arm=='P1'else'none',**extra)
                r['procedure_id']=ctx.VERSION+':'+arm if arm!='F2'else'B-QB-ALIGNED-FRESHNESS-v1:F2';r['source_vintage']=p['source_tier'];r['new_origin_extension']=True;forecasts.append(r)
        for q in query:
            law=history.exposure(q);forecasts.append(prediction(q,'COMMON_EXPOSURE','pass_att',law,cutoff,history,components=dict(attempt_law=law.parameters()),fallback=history.describe(q)['fallback']))
    write(OUT/'PREDICTIONS_2026_W09.json.gz',dict(season=2026,week=9,rows=forecasts,fit_cutoff=cutoff,actual_persisted_UTC=now(),original_issuance=False))
    write(OUT/'RUN_RECEIPT_V1.json',dict(state='COMPLETE_THREE_EXISTING_ORIGIN_FITS',new_fits=3,new_forecast_rows=len(forecasts),completion_rows=sum(r['target']=='pass_cmp'for r in forecasts),attempt_rows=sum(r['target']=='pass_att'for r in forecasts),resources=budget.resources(),new_NFL_observations=0,original_issuance=False,new_mechanisms=0))
    print(json.dumps(dict(state='COMPLETE',forecasts=len(forecasts),fits=budget.fit_calls)))


if __name__=='__main__':main()
