"""Bounded safe C02 CDF recovery; frozen settings, no offers scored or pickle.

Prior local source/feature preflight and four missing-origin fits are retained.
This appends up to four W4--7 reproductions solely to recover complete laws.
"""
import argparse,collections,csv,gzip,hashlib,json,math,resource,sys,time,warnings
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
BASE=Path(__file__).resolve().parent;ROOT=BASE.parents[3];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(BASE))
from nfl_v2 import hgb_control as source,ordered_information_ablation as c02,distribution_wave_v2 as dist,player_context_matchup as safe
from nfl_v2.distribution_laws import Law,prior
from run_legacy_completion_v1 import read,save,sha,now,feature,restore
OLD=ROOT/'reports/continuation-20261030b/ordered-information-ablation-v1'
OLDGLM=ROOT/'reports/continuation-20261030/distribution-wave-v2'

def params(p):return Law(**p)
def detail(law):
 return dict(kind='leaf_mixture',support=law.support.tolist(),weights=law.weights.tolist(),prior=law.prior.parameters(),mixture=law.b)if law.kind=='mixture'else law.parameters()
def old_rows(private):
 data=read(private/'ordered-information-ablation-v1/ALL_PREDICTIONS.json.gz')['rows']
 old=[r for r in data if r['target']=='pass_cmp'and r['policy_id']=='H-CURRENT-STRICT'and r['population']=='primary']
 by=collections.defaultdict(dict)
 for r in old:by[r['week'],r['game_id'],r['player_id']][r['product_id']]=r
 assert len(by)==242 and all(set(v)=={'mean','lower_median'}for v in by.values())
 return by
def sources(private):
 out=[]
 for w in range(1,8):
  f=OLD/f'W{w:02}-pass_cmp-H-CURRENT-STRICT-FIT.json';q=private/'ordered-information-ablation-v1/query-features'/f'W{w:02}-pass_cmp-H-CURRENT-STRICT.json.gz';fit=read(f);assert sha(q)==fit['query_features']['sha256'];out.append(dict(week=w,fit_receipt=f.relative_to(ROOT).as_posix(),fit_sha256=sha(f),query_features_sha256=sha(q),queries=len(read(q)),training_rows=fit['training_n'],training_membership_sha256=fit['training_membership_sha256'],origin=fit['fit_cutoff_utc'],prior_parameters=fit['prior_parameters']))
 return out
def normalized(base):return base+':known-target-time-v1'

def main():
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['freeze','run']);ap.add_argument('--private',type=Path,required=True);ap.add_argument('--native-sources',type=Path);a=ap.parse_args()
 ip=BASE/'STRICT_2026_COMPLETION_INPUTS_V1.json.gz';protocol=BASE/'RECOVERY_EXTENSION_PROTOCOL_V2.json';oldc=a.private/'ordered-information-ablation-v1/ALL_PREDICTIONS.json.gz';oldg=a.private/'distribution-wave-v2/all-predictions.csv.gz';inputs=read(ip);rows=inputs['rows'];history=source.FeatureHistory(rows)
 if a.action=='freeze':
  p=dict(id='B-C02-COMPLETE-LAW-RECOVERY-STRICT2026-v1',state='FROZEN_BEFORE_ADDITIONAL_AT_MOST_FOUR_NFL_FITS',frozen_UTC=now(),prior_protocol_sha256=sha(BASE/'RECOVERY_EXTENSION_PROTOCOL_V1.json'),prefit_repair_receipt_sha256=sha(BASE/'RECOVERY_EXTENSION_IMPLEMENTATION_REPAIR_V1.json'),purpose='Recover missing complete empirical CDF for existing exact-line contenders, not a new learner or repeated improvement experiment',root_authorization='Root explicit message authorizes at most four C02 strict2026 W4-7 safe origin reproductions after the previous four completed fits; global root cap16, known allocation3modern+4legacy+4recovery=11maximum',input_sha256=sha(ip),code_sha256={Path(__file__).relative_to(ROOT).as_posix():sha(__file__),**{str((ROOT/'nfl_v2'/n).relative_to(ROOT)):sha(ROOT/'nfl_v2'/n)for n in ['ordered_information_ablation.py','distribution_wave_v2.py','hgb_control.py','player_context_matchup.py','distribution_laws.py']}},original_prediction_bindings=dict(C02=dict(name='OriginalC02ALL_PREDICTIONS',sha256=sha(oldc),bytes=oldc.stat().st_size),DIRECT_GLM=dict(name='OriginalDirectGLMAllPredictions',sha256=sha(oldg),bytes=oldg.stat().st_size)),original_origins=sources(a.private),history='Exactly original H-CURRENT-STRICT: only 2026 labels/features/priors/transforms, available=kickoff+7days and strict <; training vectors at own kickoff, saved query vectors at target kickoff. Later W8/9 appended rows in input are ineligible at old origins.',learner=dict(family='ordered_leaf_cdf',forest=dist.FOREST,projected_features=list(c02.KEEP_NAMES),minimum_training_rows=60,prior_mixture=.05),parity_gate='Verify training membership, prior parameters and all 242 old query features/clocks; before release require all original mean and lower-median outputs within1e-10/exact integer and restored model within1e-10. Any discrepancy stops and preserves old outputs.',startup='W1-3 no NFL fits; restore original explicit per-origin zero/geometric QB priors, retaining original no-model/cold-start attribution',direct_glm='No fit; parse existing fully specified parametric/fallback scalar law references and verify mean/median summaries',new_fits_allowed=4,previous_task_completed_fits=4,cumulative_delegated_fit_cap=8,global_root_fit_cap=16,wall_seconds=180,CPU_seconds=240,max_RSS_bytes=2147483648,max_threads=2,new_HTTP=0,unsafe_model_loads=0,new_scores=0,new_offers=0,source_vintage='Current-vintage reconstruction; old original source and exact query packet bytes, no historical availability authentication',source_rights='CC-BY-4.0 nflverse/nflfastR statistical derivatives; no FTN/raw/protected offer export',global_expanded_recovery_gate='Remains closed; no missing prior-season source/archive or old unsafe model consumed')
  save(protocol,p);print(json.dumps(dict(state=p['state'],protocol_sha256=sha(protocol))));return
 p=read(protocol);assert sha(ip)==p['input_sha256']
 for name,h in p['code_sha256'].items():assert sha(ROOT/name)==h,name
 assert sha(oldc)==p['original_prediction_bindings']['C02']['sha256']and sha(oldg)==p['original_prediction_bindings']['DIRECT_GLM']['sha256']
 original=old_rows(a.private);out=[];fits=0;start=time.monotonic();cpu=time.process_time();maxmean=maxrestore=0.;checked=0;warnings_seen=[];querykeys={};future_checks=0
 with threadpool_limits(limits=2):
  for bound in p['original_origins']:
   w=bound['week'];fit=read(ROOT/bound['fit_receipt']);assert sha(ROOT/bound['fit_receipt'])==bound['fit_sha256'];qp=a.private/'ordered-information-ablation-v1/query-features'/f'W{w:02}-pass_cmp-H-CURRENT-STRICT.json.gz';qs=read(qp);origin=datetime.fromisoformat(bound['origin']).timestamp();train=[r for r in rows if r['position']=='QB'and r['values']['pass_cmp']is not None and r['available']<origin]
   assert len(train)==bound['training_rows'];assert hashlib.sha256(source.canonical([(r['game_id'],r['player_id'])for r in train])).hexdigest()==bound['training_membership_sha256'];y=np.asarray([r['values']['pass_cmp']for r in train]);pr=prior(y,'pass_cmp');assert pr.parameters()==fit['prior_parameters']['QB']
   qx=np.asarray([r['features']for r in qs],float)
   for item in qs:
    q=item['query'];v,clock=history.get(q['player_id'],'QB','pass_cmp',q['cutoff']);assert np.allclose(c02.project(v),np.asarray(item['features'],float),rtol=0,atol=0,equal_nan=True)and clock==item['latest_feature_available'];future=source.FeatureHistory([dict(r,values={'pass_cmp':99999.})if r['available']>=q['cutoff']else r for r in rows]);assert np.allclose(feature(history,q,'C02'),feature(future,q,'C02'),rtol=0,atol=0,equal_nan=True);future_checks+=1
   model=None;modelsha=None
   if len(train)>=60:
    assert fits<4 and w in{4,5,6,7};assert time.monotonic()-start<180 and time.process_time()-cpu<240;fits+=1;x=np.asarray([feature(history,dict(r,cutoff=r['kickoff']),'C02')for r in train]);started=now()
    with warnings.catch_warnings(record=True)as ws:
     warnings.simplefilter('always');model=dist.FittedLawModel('ordered_leaf_cdf','pass_cmp').fit(x,y,['QB']*len(y))
    warnings_seen.extend(str(m.message)for m in ws);payload=dict(family='C02',feature_order=list(c02.KEEP_NAMES),model=safe.export_forest(model));mp=BASE/'recovery-fits'/f'2026-W{w:02}-C02.json.gz';save(mp,dict(model=payload,origin=bound['origin'],training_membership_sha256=bound['training_membership_sha256'],prior=pr.parameters(),started_UTC=started,completed_UTC=now(),new_fit=1));modelsha=sha(mp);inferred=model.predict(qx,['QB']*len(qs),{'QB':pr})
   else:inferred=[(None,None)]*len(qs)
   for i,item in enumerate(qs):
    q=item['query'];key=w,q['game_id'],q['player_id'];old=original[key];saved=old['mean'];law=inferred[i][0]
    if model is None or qx[i][3]<=0:law=pr
    else:
     restored=restore(payload,qx[i],list(c02.KEEP_NAMES),pr);maxrestore=max(maxrestore,abs(restored.mean-law.mean));assert abs(restored.mean-law.mean)<1e-10 and restored.quantile(.5)==law.quantile(.5)
    e=abs(law.mean-saved['distribution_summary']['mean']);maxmean=max(maxmean,e);assert e<1e-10 and law.quantile(.5)==old['lower_median']['prediction'],('ORIGINAL_POINT_PARITY_FAILED',key,e)
    assert all(law.cdf(k)<=law.cdf(k+1)+1e-12 for k in range(-1,120));assert law.cdf(-1)==0 and law.cdf(100000)>1-1e-12;checked+=1
    querykeys[key]=saved
    out.append(dict(game_id=q['game_id'],player_id=q['player_id'],season=2026,week=w,position='QB',target='pass_cmp',method='C02',procedure_id=saved['procedure_id'],normalized_comparison_procedure_id=normalized(saved['procedure_id']),normalization_requires='Known-target-time source/fit/prior/fallback admission at each selected offer clock; alias is conditional, not a permission to ignore timing',history_regime='H-CURRENT',feature_memory='STRICT_2026',fit_cutoff=origin,feature_cutoff=q['cutoff'],latest_feature_available=item['latest_feature_available'],latest_training_label_available=fit['latest_training_label_available'],mean=law.mean,lower_median=law.quantile(.5),law=detail(law),features=item['features'],feature_order=list(c02.KEEP_NAMES),fallback=saved['fallback'],model_sha256=modelsha,original_prediction_mean=saved['prediction'],original_prediction_median=old['lower_median']['prediction'],original_issuance=False,recovery='Complete law recovered with original point parity; no old point overwritten',actual_offer=None,selected_side=None))
   assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<2147483648
 # Existing GLM parameters uniquely specify the original complete law.
 glm={}
 with gzip.open(oldg,'rt')as f:
  for r in csv.DictReader(f):
   if r['target']!='pass_cmp'or r['policy_id']!='H-CURRENT-STRICT'or r['family']!='regularized_glm_law'or r['population']!='primary':continue
   key=int(r['week']),r['game_id'],r['player_id'];d=json.loads(r['law_reference']);par=d.get('fallback_prior',d.get('parametric'));assert par is not None;law=params(par);summary=json.loads(r['distribution_summary']);assert abs(law.mean-summary['mean'])<1e-10 and law.quantile(.5)==summary['lower_median'];v=dict(game_id=r['game_id'],player_id=r['player_id'],season=2026,week=int(r['week']),position='QB',target='pass_cmp',method='DIRECT_GLM',procedure_id=r['procedure_id'],normalized_comparison_procedure_id=normalized(r['procedure_id']),history_regime='H-CURRENT',feature_memory='STRICT_2026',feature_cutoff=float(r['cutoff']),latest_feature_available=float(r['latest_feature_available'])if r['latest_feature_available']else None,mean=law.mean,lower_median=law.quantile(.5),law=par,fallback=r['fallback'],original_issuance=False,recovery='Existing safe explicit parametric/fallback law; zero new GLM fits',actual_offer=None,selected_side=None)
   if key in glm:assert glm[key]==v
   glm[key]=v
 assert len(glm)==242;out+=list(glm.values());save(BASE/'OLD_W1_W7_PREDICTIONS_V1.json.gz',dict(rows=out,scope='Existing strict2026 original kickoff-query policy; known-target-time suffix requires actual per-offer admission proof',new_scores=0,new_C02_reproduction_fits=fits,new_GLM_fits=0))
 # Identity/clock gap reconciliation only; never read grades or lines for decisions.
 gap=[];admission=[]
 if a.native_sources:
  natives=read(a.native_sources);new=read(BASE/'PREDICTIONS_W8_W9_V1.json.gz')['rows'];allmaps={(r['method'],r['week'],r['game_id'],r['player_id']):r for r in out+new}
  for sw,path in natives.items():
   w=int(sw);offerrows=read(Path(path))['rows']
   for raw in offerrows:
    if raw['target']!='pass_cmp':continue
    for method in ['C02','DIRECT_GLM']:
     key=method,w,raw['game_id'],raw['player_id'];pred=allmaps.get(key)
     if pred is None:
      sameplayer=[r for r in out if r['method']==method and r['week']==w and r['player_id']==raw['player_id']];gap.append(dict(method=method,week=w,game_id=raw['game_id'],player_id=raw['player_id'],state='CANONICAL_GAME_MISMATCH'if sameplayer else'ABSENT_FROM_ORIGINAL_STAT_ROW_QUERY_UNIVERSE',reason='Do not substitute another game/player, infer participation, or manufacture a saved forecast',same_player_other_game_ids=sorted({r['game_id']for r in sameplayer})));continue
     clock=raw.get('source_server_clock');clock=datetime.fromisoformat(clock.replace('Z','+00:00')).timestamp()if clock else None;latest=pred.get('latest_feature_available')
     if latest is None:
      _,latest=history.get(raw['player_id'],'QB','pass_cmp',pred['feature_cutoff'])
     fitrow=read(OLD/f'W{w:02}-pass_cmp-H-CURRENT-STRICT-FIT.json')if w<=7 else None;fitcut=pred.get('fit_cutoff')or datetime.fromisoformat(fitrow['fit_cutoff_utc']).timestamp();trainmax=read(BASE/'fits'/f'2026-W{w:02}-{method}.json.gz')['latest_training_label']if w>7 else fitrow['latest_training_label_available']
     state='SOURCE_CLOCK_UNKNOWN'if clock is None else'PASS_KNOWN_TARGET_INPUT_TIMING'if fitcut<clock and(latest is None or latest<clock)and(trainmax is None or trainmax<clock)else'NOT_ADMITTED_AT_SOURCE_CLOCK'
     admission.append(dict(method=method,week=w,game_id=raw['game_id'],player_id=raw['player_id'],fit_cutoff=fitcut,feature_cutoff=pred['feature_cutoff'],latest_feature_available=latest,latest_training_label_available=trainmax,decision_clock=clock,state=state))
  save(BASE/'NATIVE_QUERY_GAPS_AND_ALIAS_ADMISSION_V1.json',dict(id='B-LEGACY-NATIVE-IDENTITY-AND-TIMING-RECONCILIATION-v1',at_UTC=now(),scope='Identity/sourceclock only; no offer line/outcome/side regrading',gaps=gap,admission=admission,by_week_method=dict((f'{w}:{m}',dict(available=sum(r['week']==w and r['method']==m for r in admission),missing=sum(r['week']==w and r['method']==m for r in gap),admission_states=dict(collections.Counter(r['state']for r in admission if r['week']==w and r['method']==m))))for w in range(5,10)for m in['C02','DIRECT_GLM'])))
 save(BASE/'RECOVERY_EXTENSION_RUN_V1.json',dict(state='COMPLETE_ORIGINAL_POINT_PARITY_AND_FULL_LAW_RECOVERY',at_UTC=now(),new_reproduction_fits=fits,previous_delegated_fits=4,cumulative_delegated_fits=4+fits,original_C02_mean_median_pairs_checked=checked,max_original_mean_error=maxmean,max_restoration_mean_error=maxrestore,future_mutation_checks=future_checks,rows=len(out),protocol_sha256=sha(protocol),output_sha256=sha(BASE/'OLD_W1_W7_PREDICTIONS_V1.json.gz'),source_HTTP_attempts=0,unsafe_model_loads=0,new_scores=0,new_offers_or_sides=0,warnings=warnings_seen,resources=dict(CPU_seconds=time.process_time()-cpu,wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)))
 print(json.dumps(read(BASE/'RECOVERY_EXTENSION_RUN_V1.json')))
if __name__=='__main__':main()
