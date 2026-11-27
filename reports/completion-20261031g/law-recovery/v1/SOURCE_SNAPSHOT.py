"""Recover admitted base/C02 laws from saved leaf IDs and retained histograms."""
from __future__ import annotations
import argparse,collections,csv,gc,gzip,hashlib,json,math,pickle,resource,sys,time
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import distribution_wave_v2 as base,distribution_wave as old
from nfl_v2 import distribution_laws,scoring
from nfl_v2.saved_leaf_law_lookup import lookup
from nfl_v2.shared_subgroups import packet_rows,canonical,sha,now,write

VERSION='v2-retained-leaf-histogram-law-lookup-20261031g-v1'
ROOT=Path(__file__).resolve().parents[1]


def prepare(a):
    if a.output.exists()or a.private_output.exists():raise ValueError('fresh destinations required')
    a.output.mkdir(parents=True);a.private_output.mkdir(parents=True);bindings=[];models={}
    for panel in a.panel:
        name,public,private,metadata=panel.split('|');public,private,metadata=map(Path,(public,private,metadata));ap=json.loads((public/'FROZEN_PROTOCOL.json').read_bytes());receipt=json.loads((public/'RUN_RECEIPT.json').read_bytes());mask=private/'ADMISSIBILITY_MASK.json.gz'
        assert sha(mask)==receipt['mask_sha256'];mm=json.loads(gzip.decompress(mask.read_bytes()))['rows'];eligible=[r for r in mm if r['source_id']in('laws','c02')and r['p1_state']=='ELIGIBLE_NEW_RETROSPECTIVE_SAVED_VECTOR'and r['p2_state']=='LEARNED_LEAF_WEIGHTS_SUPPORT_REQUIRE_RECOVERY_EXTRACTION']
        for r in eligible:
            fit=r['fit_receipt'];f=json.loads((ROOT/fit).read_bytes());packet=f.get('model')
            if not packet:raise ValueError('admitted learned leaf row lacks retained model binding')
            member=packet.get('bundle_name',packet.get('name'));model_root=a.private_root/('distribution-wave-v2'if r['source_id']=='laws'else'ordered-information-ablation-v1');path=model_root/member
            if not path.exists()and packet.get('reused_from')=='v2-distribution-controls-reconstruction-v1':path=a.private_root/'distribution-wave-v1'/member
            if not path.exists()or sha(path)!=packet['sha256']:raise ValueError('specific model file missing or hash mismatch:'+fit)
            models[fit]=dict(fit_receipt=fit,fit_sha256=sha(ROOT/fit),model_sha256=packet['sha256'],model_artifact_id=packet.get('artifact_id'),source_id=r['source_id'],member=path.relative_to(a.private_root).as_posix(),training_membership_sha256=f['training_membership_sha256'])
        bindings.append(dict(panel_id=name,admission_protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),admission_receipt_sha256=sha(public/'RUN_RECEIPT.json'),mask_sha256=sha(mask),metadata_sha256=sha(metadata),eligible_leaf_output_views=len(eligible),raw_sources=ap['raw_sources']))
    private=dict(panels=a.panel,private_root=str(a.private_root));write(a.private_output/'INPUT_BINDINGS.json',private)
    p=dict(version=VERSION,registered_at_utc=now(),state='FROZEN_BEFORE_MODEL_UNPICKLE_HISTOGRAM_LOOKUP_OR_THRESHOLD_CDF_EXPORT',code_sha256=sha(__file__),lookup_code_sha256=sha(ROOT/'nfl_v2/saved_leaf_law_lookup.py'),law_code_sha256=sha(Path(distribution_laws.__file__)),base_model_source_sha256=sha(Path(base.__file__)),original_base_model_source_sha256=sha(Path(old.__file__)),private_binding_sha256=sha(a.private_output/'INPUT_BINDINGS.json'),panels=bindings,models=list(models.values()),
       mechanism='Exact lookup of32 retained per-tree normalized response histograms at the32 originally saved leaf IDs; arithmeticmean of tree PMFs plus0.05 samefit role/global prior. Preservefull signed/countsupport and infinite prior tails. No estimator/transform/predict/apply/fit or new feature vector.',
       chronology='Only already admitted exact sourcecase/recipe/offer masks. Verify original fit/model/trainingmembership/prior hashes, saved leaf cardinality, eligible training/source prior maxima by decisiontime; preserve separatelyregistered nominal-later-fit identical-prefix rule where applicable. No originalissuance claim for reconstructed earlier decision.',
       validation='Before exporting, recovermean/lowerMedian/q05/q95/zeroMass and match saved summaries; verify original pointview value, allPMFweights normalized, signedinteger support, monotoneCDF and exactpayload roundtrip. No target outcomes used.',
       export='Perpanel private complete-law augmentation keyed original offer source index/procedure/history/target with sourceidentity,population,model+fit+source hashes, params={kind:mixture,support,weights,prior,mixture},CDFfloorandfloorMinus1. Numericworker alone applies existing one-core threshold/selection/proper-score engine; no P1 or prior-parametric scores rerun.',
       scoring_contract='Integeroutcomes: half-line over=1-F(floorL),under=F(floorL),push0; integerline under=F(L-1),push=F(L)-F(L-1). Conditionalmodeledappearance; booknonvoid andpricesunverified. No truncation/smoothing/newcalibration, no scores calculated by this exporter.',
       budget=dict(wall_seconds=300,max_RSS_bytes=1073741824,max_threads=2,max_private_bytes=16777216),new_fits=0,new_model_inference=0,new_forecasts=0,new_scores=0,Week8_outcomes_read=0)
    write(a.output/'FROZEN_PROTOCOL.json',p);(a.output/'SOURCE_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes());print(dict(state=p['state'],models=len(models),leaf_output_views=sum(x['eligible_leaf_output_views']for x in bindings),protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json')))


def run(a):
    p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes());start=time.monotonic();assert sha(__file__)==p['code_sha256']and sha(ROOT/'nfl_v2/saved_leaf_law_lookup.py')==p['lookup_code_sha256']and sha(Path(distribution_laws.__file__))==p['law_code_sha256']
    assert sha(a.private_output/'INPUT_BINDINGS.json')==p['private_binding_sha256'];bindings=json.loads((a.private_output/'INPUT_BINDINGS.json').read_bytes());private_root=Path(bindings['private_root']);wanted=collections.defaultdict(lambda:collections.defaultdict(list));meta={};fitmeta={m['fit_receipt']:m for m in p['models']}
    def guard():
        if time.monotonic()-start>300 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('law recovery resource bound')
    for panel,b in zip(bindings['panels'],p['panels'],strict=True):
        name,public,private,metadata=panel.split('|');assert name==b['panel_id'];mask=Path(private)/'ADMISSIBILITY_MASK.json.gz';assert sha(mask)==b['mask_sha256']and sha(metadata)==b['metadata_sha256'];meta[name]={r['source_row_index']:r for r in json.loads(gzip.decompress(Path(metadata).read_bytes()))['rows']}
        for r in json.loads(gzip.decompress(mask.read_bytes()))['rows']:
            if r['source_id']in('laws','c02')and r['p1_state']=='ELIGIBLE_NEW_RETROSPECTIVE_SAVED_VECTOR'and r['p2_state']=='LEARNED_LEAF_WEIGHTS_SUPPORT_REQUIRE_RECOVERY_EXTRACTION':wanted[r['source_member']][r['source_row_index_in_member']].append((name,r))
    entries=collections.defaultdict(list);rows_read=0
    for member,indices in wanted.items():
        path=private_root/member;expected={m['source_member_sha256']for rr in indices.values()for _,m in rr};assert expected=={sha(path)}
        it=csv.DictReader(gzip.open(path,'rt'))if path.name.endswith('.csv.gz')else packet_rows(path)
        for index,r in enumerate(it):
            rows_read+=1
            if rows_read%10000==0:guard()
            if index not in indices:continue
            detail=r.get('law_reference');detail=json.loads(detail)if isinstance(detail,str)else detail;summary=r.get('distribution_summary');summary=json.loads(summary)if isinstance(summary,str)else summary
            for name,m in indices[index]:
                f=json.loads((ROOT/m['fit_receipt']).read_bytes());assert sha(ROOT/m['fit_receipt'])==fitmeta[m['fit_receipt']]['fit_sha256'];assert r['fit_slot']==f['slot']and r['position']==m['position']and r['target']==m['target']and not m['reasons']
                t=__import__('datetime').datetime.fromisoformat(m['decision_time'].replace('Z','+00:00')).timestamp();maxima=[f.get(k)for k in('latest_training_label_available','latest_training_feature_available')]
                assert all(v is None or v<t for v in maxima)and(m['latest_consumed_available']is None or m['latest_consumed_available']<t)
                if m['fit_cutoff']>=t:assert m.get('nominal_fit_after_decision')and'Identicalearliertrainingprefix'in m.get('nominal_fit_reuse_rule','')
                entries[m['fit_receipt']].append(dict(panel_id=name,mask=m,game_id=r['game_id'],player_id=r['player_id'],population=r['population'],position=r['position'],leaf_ids=detail['leaf_ids'],summary={k:summary[k]for k in('mean','lower_median','q05','q95','zero_mass')},point=float(r['prediction'])))
    # Explicitly deny every estimator evaluation route while deserializing only
    # hash-verified model bytes produced by these retained V2 runs.
    def forbidden(*args,**kwargs):raise AssertionError('ESTIMATOR_OR_TRANSFORM_EXECUTION_FORBIDDEN')
    exported=collections.defaultdict(dict);modelproof=[];maxdiff=0.;law_count=0
    from sklearn.ensemble import ExtraTreesRegressor
    with ExitStack()as stack:
        for cls,names in[(base.FittedLawModel,('predict','fit')),(old.FittedLawModel,('predict','fit')),(ExtraTreesRegressor,('predict','apply','fit','decision_path')),(base.Design,('transform','fit')),(old.Design,('transform','fit'))]:
            for name in names:stack.enter_context(patch.object(cls,name,forbidden))
        for fit,queries in entries.items():
            guard();fm=fitmeta[fit];f=json.loads((ROOT/fit).read_bytes());file=private_root/fm['member'];assert sha(file)==fm['model_sha256'];model=pickle.loads(gzip.decompress(file.read_bytes()));assert model.family=='ordered_leaf_cdf'and model.target==f['target']and len(model.hist)==32
            local={};witnesses=0
            for q in queries:
                m=q['mask'];prior=f['prior_parameters'][q['position']];key=(tuple(q['leaf_ids']),canonical(prior))
                if key not in local:
                    law,params=lookup(model.support,model.hist,q['leaf_ids'],prior);summary=law.summary();local[key]=(law,params,summary);law_count+=1
                law,params,s=local[key]
                for k,v in q['summary'].items():
                    delta=abs(float(s[k])-float(v));maxdiff=max(maxdiff,delta)
                    if not math.isclose(float(s[k]),float(v),rel_tol=1e-10,abs_tol=1e-9):raise ValueError('recovered distribution summary differs:'+fit+':'+k)
                expected=q['summary']['mean'if m['product_id']=='mean'else'lower_median'];assert math.isclose(q['point'],expected,rel_tol=1e-10,abs_tol=1e-9)
                o=meta[q['panel_id']][m['source_row_index']];L=scoring.exact_decimal(o['line']);k=int(L.to_integral_value(rounding='ROUND_FLOOR'));fm1=law.cdf(k-1);fc=law.cdf(k);fp1=law.cdf(k+1);assert-1e-12<=fm1<=fc+1e-12 and fc<=fp1+1e-12 and fp1<=1+1e-12
                ek=(m['source_row_index'],m['procedure_id'],m['history_regime'],m['target']);value=dict(source_row_index=m['source_row_index'],offer_safe_id=m['offer_safe_id'],procedure_id=m['procedure_id'],history_regime=m['history_regime'],target=m['target'],game_id=q['game_id'],player_id=q['player_id'],population=q['population'],position=q['position'],decision_time=m['decision_time'],line=o['line'],params=params,cdf_at_line_floor=fc,cdf_at_line_floor_minus_one=fm1,fit_receipt=fit,fit_sha256=fm['fit_sha256'],model_sha256=fm['model_sha256'],training_membership_sha256=f['training_membership_sha256'],source_member=m['source_member'],source_member_sha256=m['source_member_sha256'],source_row_indices_in_member=[m['source_row_index_in_member']],source_products=[m['product_id']],fallback='none',qualification='EXACT_RETAINED_LEAF_HISTOGRAM_LOOKUP_AND_SUMMARY_PARITY_NO_INFERENCE')
                previous=exported[q['panel_id']].get(ek)
                if previous:
                    assert previous['params']==params and(previous['game_id'],previous['player_id'],previous['population'],previous['position'])==(q['game_id'],q['player_id'],q['population'],q['position']);previous['source_row_indices_in_member'].extend(value['source_row_indices_in_member']);previous['source_products'].extend(value['source_products'])
                else:exported[q['panel_id']][ek]=value
                witnesses+=1
            modelproof.append(dict(fit_receipt=fit,fit_sha256=fm['fit_sha256'],model_sha256=fm['model_sha256'],training_membership_sha256=f['training_membership_sha256'],target=f['target'],history_regime=f['history_regime'],feature_floor=f['feature_floor'],fit_cutoff_utc=f['fit_cutoff_utc'],latest_training_label_available=f['latest_training_label_available'],latest_training_feature_available=f['latest_training_feature_available'],trees=len(model.hist),support_size=len(model.support),verified_saved_view_witnesses=witnesses,unique_leaf_prior_lookups=len(local)))
            del local,model;gc.collect()
    artifacts=[]
    for name,rr in exported.items():
        body=gzip.compress(canonical(dict(schema=VERSION,panel_id=name,rows=list(rr.values()))),mtime=0);target=a.private_output/(name+'-LEARNED_LAW_AUGMENTATION.json.gz')
        if sum(x.stat().st_size for x in a.private_output.iterdir()if x.is_file())+len(body)>16777216:raise RuntimeError('private sixteen MiB cap')
        with target.open('xb')as f:f.write(body)
        artifacts.append(dict(panel_id=name,artifact_id='G-LEAF-LAW-LOOKUP-'+name,sha256=sha(target),bytes=len(body),complete_law_offer_rows=len(rr),by_source_procedure=dict(collections.Counter(r['procedure_id']for r in rr.values()))))
    write(a.output/'MODEL_AND_LAW_PARITY_PROOF.json',dict(models=modelproof,max_summary_absolute_difference=maxdiff,verified_saved_view_witnesses=sum(x['verified_saved_view_witnesses']for x in modelproof),unique_model_leaf_prior_lookups=law_count,no_inference_guards='ExtraTreespredict/apply/fit/decisionpath, modelpredict/fit, Designtransform/fit patchedtofail; allhistlookup passed.',estimator_calls=0,new_fits=0,new_forecasts=0,new_scores=0))
    receipt=dict(state='COMPLETE_QUALIFIED_LEARNED_CDF_RECOVERY_BY_LOOKUP_ONLY',protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),artifacts=artifacts,models=len(modelproof),source_rows_scanned=rows_read,private_derivative_bytes=sum(x.stat().st_size for x in a.private_output.iterdir()if x.is_file()),wall_seconds=time.monotonic()-start,max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,new_fits=0,new_model_inference=0,new_scores=0,Week8_outcomes_read=0)
    write(a.output/'RUN_RECEIPT.json',receipt);print(json.dumps(receipt))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','run']);p.add_argument('--output',type=Path,required=True);p.add_argument('--private-output',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--panel',action='append',default=[]);a=p.parse_args();prepare(a)if a.action=='prepare'else run(a)
