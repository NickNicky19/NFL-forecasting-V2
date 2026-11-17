"""Four missing strict-current origin fits, safe JSON only, after root ACK.

Same registered C02 Leaf-CDF and direct GLM count learners. No training on
non-QB outcomes, old pickle loads, new features or hyperparameter selection.
Derived statistical features/models: nflverse/nflfastR, CC-BY-4.0.
"""
import argparse,gzip,hashlib,json,math,resource,sys,time,warnings
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from nfl_v2 import hgb_control as source
from nfl_v2 import distribution_wave_v2 as dist
from nfl_v2 import ordered_information_ablation as c02
from nfl_v2 import player_context_matchup as safe
from nfl_v2.distribution_laws import Law,prior
BASE=Path(__file__).resolve().parent

def now():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b)if Path(p).suffix=='.gz'else b)
def clean(x):
 if isinstance(x,dict):return{k:clean(v)for k,v in x.items()}
 if isinstance(x,(list,tuple,np.ndarray)):return[clean(v)for v in x]
 if isinstance(x,np.generic):return clean(x.item())
 if isinstance(x,float)and not math.isfinite(x):return None
 return x
def save(p,x):
 if p.exists():raise FileExistsError(p)
 p.parent.mkdir(parents=True,exist_ok=True);b=(json.dumps(clean(x),separators=(',',':'),allow_nan=False)+'\n').encode();p.write_bytes(gzip.compress(b,mtime=0)if p.suffix=='.gz'else b)
def restore(payload,features,names,pr):
 if names!=payload['feature_order']:raise ValueError('Namedfeatureorder mismatch')
 x=np.asarray(features,float)
 if len(x)!=len(names):raise ValueError('Featurewidth')
 if payload['family']=='C02':return safe.restored_forest_law(payload['model'],x,pr)
 d=payload['model'];median=np.asarray(d['median']);raw=np.concatenate([np.where(np.isfinite(x),x,median),~np.isfinite(x)]).astype(float);z=(raw-np.asarray(d['mean']))/np.asarray(d['scale']);mu=math.exp(float(z@np.asarray(d['coefficient'])+d['intercept']));return Law('poisson',mean=mu)
def feature(history,q,family):
 x,_=history.get(q['player_id'],q['position'],'pass_cmp',q['cutoff']);return c02.project(x)if family=='C02'else np.asarray(x,float)

def main():
 a=argparse.ArgumentParser();a.add_argument('action',choices=['freeze','run']);a.add_argument('--publication-ack',type=Path);z=a.parse_args()
 ip=BASE/'STRICT_2026_COMPLETION_INPUTS_V1.json.gz';pp=BASE/'FEATURE_PARITY_AND_PREFLIGHT_V1.json';pfile=BASE/'FROZEN_PROTOCOL_V1.json';pre=read(pp)
 modules=[Path(__file__),ROOT/'nfl_v2/hgb_control.py',ROOT/'nfl_v2/empirical_benchmark.py',ROOT/'nfl_v2/distribution_wave_v2.py',ROOT/'nfl_v2/ordered_information_ablation.py',ROOT/'nfl_v2/player_context_matchup.py',ROOT/'nfl_v2/distribution_laws.py']
 if z.action=='freeze':
  p=dict(id='B-LEGACY-COMPLETION-MISSING-ORIGINS-2026-v1',state='FROZEN_BEFORE_ANY_FOUR_NFL_FITS',frozen_UTC=now(),owner='B delegatedlegacycompletionexecutor;rootfit/sourcepublicationlease',input_sha256=sha(ip),preflight_sha256=sha(pp),code_sha256={f.relative_to(ROOT).as_posix():sha(f)for f in modules},origin_plan=pre['origin_plan'],families=['C02','DIRECT_GLM'],feature_orders=dict(C02=list(c02.KEEP_NAMES),DIRECT_GLM=list(source.FEATURES)),history='H-CURRENT-STRICT:2026labels/features/priors/transforms;existingfixedarchitecturewasexposedhistoricalchoice',source='Frozenoriginal2026W1-7valuesunmodified;qualifiedcurrent-vintageW8-9appendonly; no newrawsourceaccess',cutoff='Earliestactualweekkickoffweeklyfit; strictavailable<origin; querykickoffleftlimit; cutoffderivedfromretainedawaregamesCSV. NotoriginalpartialW8late-issuedforecast.',procedure_ids=dict(C02='v2-c02-explicit-lag-block-removal-leaf-cdf-v1:strict-current-inputs',DIRECT_GLM='v2-distribution-controls-reconstruction-v2:regularized_glm_law:strict-current-inputs'),new_scope='NewW8/W9historicalweeklyprefixreconstruction, notknown-target-timeadmissionororiginalW8issue. Samefixedfamilyfeatures/history/update/sideproducts; fittedparameters legitimatelyvarybyorigin. EarlierW1-7sourcearrayspreserved.',training='QB-onlyqualifiedknowncompletiontargets; ownhistorymayincludethesameplayer\'searlierrole rows; no irrelevantall-positionzerotraining',fallback='Originalno-model/coldstartn8<=0→eligibleQBrole/globalprior; noNFlstartupfixed0onlyifnoearlierlabels. Equalpointlineorlawtieseparatesideabstention; missingforecastsnotintentionalabstention.',families_settings=dict(forest=dist.FOREST,glm=dist.GLM,leaf_prior_mixture=.05),serialization='SafeJSONtree/leafhistogram+trainimputerorPoissoncoefficients+trainimputer/scaler; no pickle deserialization. Namedorderguard output-preserving.',root_scope_authorization='Rootdirectmessage authorizesatmost4strict2026originfits aftersource/code/readbackACK. Doesnotopenunrestored2022-24expandedlargefitgate; no oldarchive/modelconsumed.',publication_gate='Root publication ACK must bind exact frozen input, protocol and execute code prior to firstfit; verify actual readback separately.',budgets=dict(max_new_NFL_fits=4,max_threads=2,CPU_seconds=240,wall_seconds=180,max_RSS_bytes=2147483648,public_new_bytes=8388608),new_features=0,new_learner_families=0,new_tuning_searches=0,source_HTTP_attempts=0,license='CC-BY-4.0nflverse/nflfastRderivedstatisticalinputs;codeoriginalrepositoryterms')
  save(pfile,p);print(json.dumps(dict(state=p['state'],protocol_sha256=sha(pfile))));return
 if z.publication_ack is None:raise ValueError('PublicationACKrequired')
 ack=read(z.publication_ack);assert ack['state']=='PASS_ROOT_PREFIT_SOURCE_CODE_READBACK';assert len(ack['source_commit'])==40
 for f in [ip,pfile,Path(__file__)]:assert ack['members'][f.relative_to(ROOT).as_posix()]==sha(f)
 p=read(pfile)
 for name,h in p['code_sha256'].items():assert sha(ROOT/name)==h,name
 assert sha(ip)==p['input_sha256']and sha(pp)==p['preflight_sha256']
 inputs=read(ip);rows=inputs['rows'];queries=inputs['queries'];history=source.FeatureHistory(rows);lookup={(r['game_id'],r['player_id']):r for r in rows};start=time.monotonic();cpu=time.process_time();fits=0;allpred=[];max_restore=0.;negative_checks=0;future_checks=0
 # Before fitting, adversarial future-value mutations cannot change features.
 for q in queries:
  mutated=[dict(r,values={'pass_cmp':99999.})if r['available']>=q['cutoff']else r for r in rows];other=source.FeatureHistory(mutated)
  for fam in p['families']:
   assert np.allclose(feature(history,q,fam),feature(other,q,fam),rtol=0,atol=0,equal_nan=True);future_checks+=1
 with threadpool_limits(limits=2):
  for plan in p['origin_plan']:
   week=plan['week'];origin=plan['origin_epoch'];train=[r for r in rows if r['position']=='QB'and r['values']['pass_cmp']is not None and r['available']<origin];qrows=[q for q in queries if q['week']==week];y=np.asarray([r['values']['pass_cmp']for r in train]);pr=prior(y,'pass_cmp')
   assert len(train)==plan['training_rows'];assert hashlib.sha256(source.canonical([(r['game_id'],r['player_id'])for r in train])).hexdigest()==plan['training_membership_sha256']
   for family in p['families']:
    assert fits<4 and time.monotonic()-start<p['budgets']['wall_seconds']and time.process_time()-cpu<p['budgets']['CPU_seconds']
    fits+=1;slot=f'2026-W{week:02}-{family}';started=now();x=np.asarray([feature(history,dict(r,cutoff=r['kickoff']),family)for r in train]);qx=np.asarray([feature(history,q,family)for q in qrows]);name='ordered_leaf_cdf'if family=='C02'else'regularized_glm_law'
    with warnings.catch_warnings(record=True)as ws:
     warnings.simplefilter('always');model=dist.FittedLawModel(name,'pass_cmp').fit(x,y,['QB']*len(y))
    if family=='C02':typed=safe.export_forest(model)
    else:typed=dict(median=model.design.median.tolist(),mean=model.design.mean.tolist(),scale=model.design.scale.tolist(),coefficient=model.estimator.coef_.tolist(),intercept=float(model.estimator.intercept_),n_iter=int(model.estimator.n_iter_))
    payload=dict(family=family,feature_order=p['feature_orders'][family],model=typed)
    mpath=BASE/'fits'/(slot+'.json.gz');save(mpath,dict(slot=slot,model=payload,training_rows=len(train),fit_cutoff=origin,latest_training_label=max(r['available']for r in train),training_membership_sha256=plan['training_membership_sha256'],prior=pr.parameters(),started_UTC=started,completed_UTC=now(),warnings=[str(w.message)for w in ws],new_fit=1))
    original=model.predict(qx,['QB']*len(qrows),{'QB':pr})
    for i,q in enumerate(qrows):
     law=restore(payload,qx[i],p['feature_orders'][family],pr);expected=original[i][0];max_restore=max(max_restore,abs(law.mean-expected.mean));assert abs(law.mean-expected.mean)<1e-10 and law.quantile(.5)==expected.quantile(.5)
     fallback='none'
     if qx[i][3]<=0:law=pr;fallback='cold_start_role_prior'
     try:restore(payload,qx[i],list(reversed(p['feature_orders'][family])),pr)
     except ValueError:negative_checks+=1
     else:raise AssertionError('Namedfeatureorderguard')
     actual=lookup.get((q['game_id'],q['player_id']),{}).get('values',{}).get('pass_cmp')
     detail=dict(kind='leaf_mixture',support=law.support.tolist(),weights=law.weights.tolist(),prior=law.prior.parameters(),mixture=law.b)if law.kind=='mixture'else law.parameters()
     allpred.append(dict(game_id=q['game_id'],player_id=q['player_id'],season=2026,week=week,team=q['team'],opponent=q['opponent'],position='QB',target='pass_cmp',method=family,procedure_id=p['procedure_ids'][family],extension_scope=p['new_scope'],complete_query_policy='HISTORICAL_WEEKLY_EARLIEST_ORIGIN_QUERY_KICKOFF_7DAY_RECONSTRUCTION-v1',original_issuance=False,history_regime='H-CURRENT',feature_memory='STRICT_2026',fit_cutoff=origin,feature_cutoff=q['cutoff'],mean=law.mean,lower_median=law.quantile(.5),law=detail,features=qx[i].tolist(),feature_order=p['feature_orders'][family],model_sha256=sha(mpath),fallback=fallback,actual=actual,actual_status='EXPLICIT_OFFICIAL_PLAYED_STAT'if actual is not None else'UNKNOWN_NOT_ZERO',actual_execution_UTC=now(),actual_offer=None,selected_side=None,source_vintage='CURRENT_VINTAGE_HYBRID_FROZEN_W1_7_PLUS_LATER_W8_9;HISTORICAL_CLOCK_RECONSTRUCTION',license='CC-BY-4.0nflverse/nflfastR'))
    assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<p['budgets']['max_RSS_bytes']
 save(BASE/'PREDICTIONS_W8_W9_V1.json.gz',dict(rows=allpred,fit_calls=fits,actual_completed_UTC=now(),not_original_issuance=True))
 save(BASE/'RUN_RECEIPT_V1.json',dict(id=p['id'],state='COMPLETE_FOUR_MISSING_STRICT_CURRENT_ORIGIN_FITS',completed_UTC=now(),new_fits=fits,forecasts=len(allpred),unique_queries=len(queries),original_week8_packets_unchanged=True,source_HTTP_attempts=0,unsafe_model_loads=0,preflight_sha256=sha(pp),protocol_sha256=sha(pfile),publication_ack_sha256=sha(z.publication_ack),output_sha256=sha(BASE/'PREDICTIONS_W8_W9_V1.json.gz'),batch_vs_safe_restore_max_mean_error=max_restore,named_order_negative_checks=negative_checks,future_value_mutation_feature_checks=future_checks,resources=dict(CPU_seconds=time.process_time()-cpu,wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),new_scores=0,new_offers_or_sides=0,common_C_admission=False))
 print(json.dumps(read(BASE/'RUN_RECEIPT_V1.json')))
if __name__=='__main__':main()
