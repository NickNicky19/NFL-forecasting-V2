"""Read original saved laws/leaf histograms at retained lines, without inference."""
from __future__ import annotations
import argparse,collections,gzip,hashlib,json,math,pickle,resource,sys,time
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import grade_saved_week8 as core,grade_week8_captured_library as library
from nfl_v2 import scoring,distribution_wave_v2 as base,distribution_wave as old
from nfl_v2.saved_leaf_law_lookup import lookup,from_payload
from nfl_v2.recorded_prop_grading import canonical
from threadpoolctl import threadpool_limits
VERSION='v2-week8-original-saved-law-lookup-at-retained-threshold-v1'


def probabilities(law,line):
    L=scoring.exact_decimal(line);k=int(L.to_integral_value(rounding='ROUND_FLOOR'))
    a,b,c=law.cdf(k-1),law.cdf(k),law.cdf(k+1)
    assert -1e-12<=a<=b+1e-12 and b<=c+1e-12 and c<=1+1e-12
    under=a if L==k else b
    p=dict(over=1-b,under=under,push=b-under if L==k else 0.)
    assert min(p.values())>=-1e-12 and max(p.values())<=1+1e-12 and abs(sum(p.values())-1)<1e-12
    p={k:min(1.,max(0.,v))for k,v in p.items()};total=sum(p.values())
    return {k:v/total for k,v in p.items()}


def run(private,public):
    started=time.monotonic();out=public/'saved-laws-v2';out.mkdir(exist_ok=False)
    labels=core.Labels(private);evidence=Path(labels.binding['private_evidence_root'])
    alloffers=[r for r in json.loads(gzip.decompress((private/'ORIGINAL_JOINED_ROWS_V1.json.gz').read_bytes()))['rows']if r['panel']=='ORIGINAL_PROVIDER_T90']
    offers={library.key(r):r for r in alloffers}
    fitdirs=[('reports/continuation-20261030/distribution-wave-v2','distribution-wave-v2'),('reports/continuation-20261030b/c02-future-shadow-v1','c02-future-shadow-v1'),('reports/continuation-20261030c/qualified-defense-information-v1','qualified-defense-information-v1')]
    bysha={};byslot={}
    for pubdir,privdir in fitdirs:
        for f in (ROOT/pubdir).glob('*FIT.json'):
            obj=core.read(f);m=obj.get('model')
            if not m:continue
            path=evidence/privdir/m.get('bundle_name',m.get('name',''))
            if not path.exists()and privdir=='distribution-wave-v2':path=evidence/'distribution-wave-v1'/m.get('bundle_name',m.get('name',''))
            binding=dict(fit=f,meta=obj,model_path=path,model_sha256=m['sha256'])
            bysha.setdefault(m['sha256'],binding)
            if obj.get('slot'):byslot[obj['slot']]=binding
    specs=[s for s in library.packet_specs(private,public)if s['capture_version']in('DISTRIBUTION_WAVE','C02','D1_D2')]
    wanted=[];blocked=collections.Counter();models={}
    for s in specs:
        obj=json.loads(gzip.decompress(s['source_path'].read_bytes()))
        for i,r in enumerate(obj['rows']):
            if r['target']not in core.ORDINARY or r.get('product_id')!='mean':continue
            q=library.normalize(r,capture=s['capture_version'],schema=obj['schema'],persisted=s['persisted_at'],labels=labels,index=i,source_sha=s['source_sha256'])
            if not q['original_forecast_issued']or not q['T90_eligible']:blocked['UNISSUED_OR_NOT_T90']+=1;continue
            offer=offers.get(library.key(q))
            if not offer:blocked['NO_PRIMARY_PROVIDER_LINE']+=1;continue
            ref=r.get('law_reference')or{}
            fit=byslot.get(r.get('fit_slot'))if r.get('fit_slot')else bysha.get(str(r.get('model_artifact_id','')).split('-')[-1])
            if not fit:raise ValueError('missing exact retained fit binding')
            assert fit['meta']['target']==r['target']and fit['meta']['history_regime']==r['history_regime']
            issuance=core.aware(q['issued_at_utc']).timestamp()
            for field in('latest_training_label_available','latest_training_feature_available','latest_training_consumed_feature_available'):
                v=fit['meta'].get(field);assert v is None or float(v)<issuance
            assert r.get('latest_feature_available')is None or float(r['latest_feature_available'])<issuance
            assert core.sha(fit['model_path'])==fit['model_sha256']
            if 'leaf_ids'in ref:models[fit['model_sha256']]=fit
            elif not({'parametric','fallback_prior'}&set(ref)):raise ValueError('original law incomplete; no fabricated law permitted')
            wanted.append(dict(original=r,normalized=q,offer=offer,fit=fit,source_sha256=s['source_sha256']))
    core.save(out/'FROZEN_PROTOCOL.json',dict(version=VERSION,at_utc=core.now(),state='FROZEN_BEFORE_NEW_LAW_LOOKUP_DIRECTION_OR_PROPER_SCORE',
        exposure='Week8 point/original losses already examined; this is exposed descriptive research, not untouched validation.',
        sources=[{k:v for k,v in s.items()if k!='source_path'}for s in specs],eligible_law_offer_rows=len(wanted),learned_histogram_model_files=len(models),excluded_source_rows=dict(blocked),
        rule='P2 higher valid over/under probability; tie abstains. Original mean/median summaries compared before scoring; mean and median are views of the same law, not independent methods.',
        law_contract='Exact original parametric law or32 original saved leaf IDs→normalized retained histograms plus same-fit5%role prior; no predict/apply/fit/transform. Full count/signed support, no calibration/tail floor.',
        probability_contract='Conditional modeled appearance; bookmaker nonvoid conditioning unestablished. Half categorical Brier across over/under/push, supported logs with impossible events Infinity. No prices, EV or returns.',
        references='50/50 on exactly matching half-point/no-push final masks only; same-fit earlier-estimated role/global prior law, separately scored. No fitted prevalence from evaluated outcomes. Market probabilities absent.',
        chronology='Early saved forecasts joined to later qualified retained T90 provider-labelled thresholds. This is retrospective rule replay, not an originally issued pick or a pure same-information learner comparison.',
        models=[dict(model_sha256=k,fit_receipt=v['fit'].relative_to(ROOT).as_posix(),fit_sha256=core.sha(v['fit']),training_membership_sha256=v['meta']['training_membership_sha256'])for k,v in models.items()],
        resource=dict(wall_seconds=300,RSS_bytes=1073741824,max_private_output_bytes=4194304,max_threads=2),code_sha256=core.sha(__file__),lookup_sha256=core.sha(ROOT/'nfl_v2/saved_leaf_law_lookup.py'),new_fits=0,new_inference=0,new_forecasts=0))
    def guard():
        if time.monotonic()-started>300 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('bounded saved-law wave exceeded')
    def forbidden(*args,**kwargs):raise AssertionError('MODEL_OR_TRANSFORM_EXECUTION_FORBIDDEN')
    from sklearn.ensemble import ExtraTreesRegressor
    cache={};loaded={};rows=[];parity=0.;matches=0
    with ExitStack()as stack:
        for cls,names in[(base.FittedLawModel,('predict','fit')),(old.FittedLawModel,('predict','fit')),(ExtraTreesRegressor,('predict','apply','fit','decision_path')),(base.Design,('transform','fit')),(old.Design,('transform','fit'))]:
            for name in names:stack.enter_context(patch.object(cls,name,forbidden))
        for item in wanted:
            guard();r,q,f=item['original'],item['normalized'],item['fit'];ref=r['law_reference'];prior=f['meta']['prior_parameters'][r['position']]
            ck=(f['model_sha256'],canonical(ref),canonical(prior))
            if ck not in cache:
                if 'parametric'in ref or 'fallback_prior'in ref:law=from_payload(ref.get('parametric',ref.get('fallback_prior')))
                else:
                    if f['model_sha256']not in loaded:
                        model=pickle.loads(gzip.decompress(f['model_path'].read_bytes()));assert model.family=='ordered_leaf_cdf'and model.target==r['target']and len(model.hist)==32
                        loaded[f['model_sha256']]=model
                    model=loaded[f['model_sha256']];law,_=lookup(model.support,model.hist,ref['leaf_ids'],prior)
                summary=law.summary()
                for key in('mean','lower_median','q05','q95','zero_mass'):
                    delta=abs(float(summary[key])-float(r['distribution_summary'][key]));parity=max(parity,delta)
                    assert math.isclose(float(summary[key]),float(r['distribution_summary'][key]),rel_tol=1e-10,abs_tol=1e-9),(key,delta)
                cache[ck]=law
            law=cache[ck];matches+=1
            g=list(library.group(q));g[3]='original_complete_law';g=tuple(g);mid=library.view_id(g)
            p=probabilities(law,item['offer']['line']);pr=probabilities(from_payload(prior),item['offer']['line'])
            side='over'if p['over']>p['under']else'under'if p['under']>p['over']else None
            row=dict(item['offer'],method_key=mid,procedure_id=g[1],capture_version=g[0],history_regime=g[2],product_id=g[3],information_policy=g[4],availability_arm=g[5],selected_side=side,side=side,original_side=None,
                probabilities=p,prior_probabilities=pr,forecast_issued_at=q['issued_at_utc'],forecast_persistence_at=q['persistence_completed_at'],fallback=q['fallback'],model_sha256=f['model_sha256'],fit_receipt=f['fit'].relative_to(ROOT).as_posix(),source_forecast_sha256=item['source_sha256'],saved_law_reference=ref,
                line_conditional_probability_source='ORIGINAL_PARAMETRIC'if'parametric'in ref else'ORIGINAL_FALLBACK_PRIOR'if'fallback_prior'in ref else'ORIGINAL_SAVED_LEAF_HISTOGRAM_LOOKUP_NO_INFERENCE',price=None,net_return=None,settlement_state='UNRESOLVED_CONTRACT')
            row['statistical_state']='ABSTAIN'if side is None else'PENDING'if row['outcome_state']=='pending'else'UNKNOWN_PARTICIPATION'if row['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL'else'MISSING_ACTUAL'if row['actual']is None else scoring.threshold_crossing(row['actual'],row['line'],side,target=row['target'])
            rows.append(row)
    core.savegz(private/'WEEK8_ORIGINAL_LAW_THRESHOLD_ROWS_V1.json.gz',dict(rows=rows));assert(private/'WEEK8_ORIGINAL_LAW_THRESHOLD_ROWS_V1.json.gz').stat().st_size<=4194304
    groups=collections.defaultdict(list)
    for r in rows:groups[r['method_key']].append(r)
    sides=[];proper=[]
    for mid,rr in sorted(groups.items()):
        first=rr[0];target=first['target'];ss=core.aggregate(rr,panel='SAVED_ORIGINAL_COMPLETE_LAW_AT_RETAINED_T90_LINE:'+first['capture_version'],method=first['procedure_id']+':'+mid,track='C_RESEARCH_REPLAY',strategy='P2',pool=rr)
        for s in ss:
            if s['target']!=target:continue
            s.update(method_key=mid,base_procedure_id=first['procedure_id'],capture_version=first['capture_version'],history_regime=first['history_regime'],product_id='original_complete_law',information_policy=first['information_policy']);sides.append(s)
        final=[r for r in rr if r['outcome_state']=='final'and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'and r['actual']is not None]
        for scope,valid in [('ALL_LINES',final),('HALF_POINT_NO_PUSH',[r for r in final if scoring.exact_decimal(r['line'])%1!=0])]:
            for ref in('FOOTBALL_ORIGINAL_LAW','EARLIER_FIT_ROLE_PRIOR','NEUTRAL_50_50'):
                if ref=='NEUTRAL_50_50'and scope!='HALF_POINT_NO_PUSH':continue
                bs=[];logs=[]
                for r in valid:
                    y='over'if scoring.exact_decimal(r['actual'])>scoring.exact_decimal(r['line'])else'under'if scoring.exact_decimal(r['actual'])<scoring.exact_decimal(r['line'])else'push'
                    p=r['probabilities']if ref=='FOOTBALL_ORIGINAL_LAW'else r['prior_probabilities']if ref=='EARLIER_FIT_ROLE_PRIOR'else dict(over=.5,under=.5,push=0.)
                    bs.append(.5*sum((p[s]-int(s==y))**2 for s in('over','under','push')));logs.append(-math.log(p[y])if p[y]>0 else float('inf'))
                tag=[VERSION,mid,scope,ref]
                proper.append(dict(record_id='W8-LAW-PROB-'+hashlib.sha256(canonical(tag)).hexdigest()[:24],record_kind='prop_threshold_probability_evaluation',procedure_id=first['procedure_id']if ref=='FOOTBALL_ORIGINAL_LAW'else ref+':MASK:'+mid,
                    compared_method_key=mid,method_key=mid,reference=ref,capture_version=first['capture_version'],history_regime=first['history_regime'],product_id='actual_line_categorical_law',target=target,
                    evaluation_panel_id=VERSION+':'+scope,probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',probability_conditioning='MODELED_APPEARANCE',bookmaker_nonvoid_conditioning='UNESTABLISHED',season=2026,week=8,evaluation_seasons=[2026],evaluation_weeks=[8],
                    n=len(valid),forecast_rows=len(rr),unique_games=len({r['game_id']for r in valid}),brier=math.fsum(bs)/len(bs)if bs else None,log_loss=('Infinity'if any(math.isinf(v)for v in logs)else math.fsum(logs)/len(logs))if logs else None,infinite_log_losses=sum(math.isinf(v)for v in logs),mae=None,mse=None,
                    fallback_rows=sum(r['fallback']not in(None,'none','NONE',False)for r in valid),evidence='REPRODUCED_FROM_ORIGINAL_SAVED_LAW_BY_LOOKUP_NO_INFERENCE',null_reason=None if valid else'NO_QUALIFIED_FINAL_LABELS',whole_week_complete=False,
                    uncertainty='INSUFFICIENT_WEEK_CLUSTERS_ONE_EXPOSED_WEEK',information_policy=first['information_policy']))
    core.save(out/'SCORES.json',proper);core.save(out/'SELECTION_SCORES.json',sides);core.write_csv(out/'PROBABILITY_TABLE.csv',proper)
    table=core.wide(sides);core.save(out/'SELECTION_SIDE_TABLE.json',table);core.write_csv(out/'SELECTION_SIDE_TABLE.csv',table)
    core.save(out/'RUN_RECEIPT.json',dict(state='ORIGINAL_SAVED_LAWS_SCORED_PARTIAL_WEEK',at_utc=core.now(),wall_seconds=time.monotonic()-started,models_loaded=len(loaded),unique_law_lookups=len(cache),verified_summary_rows=matches,max_summary_difference=parity,
        original_law_offer_rows=len(rows),method_law_groups=len(groups),proper_score_views=len(proper),side_views=len(sides),private_sha256=core.sha(private/'WEEK8_ORIGINAL_LAW_THRESHOLD_ROWS_V1.json.gz'),private_bytes=(private/'WEEK8_ORIGINAL_LAW_THRESHOLD_ROWS_V1.json.gz').stat().st_size,
        estimator_and_transform_guards='predict/apply/fit/decision_path/modelpredict/Designtransform/fit all forbidden during original histogram reading',peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,new_fits=0,new_inference=0,new_forecasts=0,code_sha256=core.sha(__file__)))
    print(json.dumps(dict(state='SAVED_LAWS_SCORED',rows=len(rows),law_groups=len(groups),proper_views=len(proper),side_views=len(sides),max_parity_error=parity,seconds=time.monotonic()-started)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-root',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);a=p.parse_args()
    with threadpool_limits(limits=2):run(a.private_root,a.public_root)
