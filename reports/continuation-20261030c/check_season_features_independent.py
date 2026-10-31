"""Independent season-relative prefixes, fit memberships and retained-model replay.

Only inference from hash-bound self-created models; no fits or source requests.
"""
import argparse,bisect,csv,gzip,hashlib,json,math,pickle,resource,sys,time
from collections import Counter,defaultdict
from functools import lru_cache
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'reports/continuation-20261030c';sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT))
from review_paths import companion_root,source_root
from check_season_scores_independent import load_truth,sha,close,TARGETS,COUNTS,read_row
from check_defense_features_independent import Prefixes,prior,compare,canonical,unzip,POSITIONS,CHART
from check_retained_distribution_math import summaries,bounds,masses
class OwnOnly:
 own=Prefixes.own
 def __init__(self,rows):
  self.players=defaultdict(list)
  for r in rows:self.players[r['player_id']].append(r)
  for rs in self.players.values():rs.sort(key=lambda r:(r['available'],r['kickoff'],r['game_id']))
  self.times={p:[r['available']for r in rs]for p,rs in self.players.items()}
def verify(public,private,source):
 start,cpu=time.monotonic(),time.process_time();p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());run=json.loads((public/'RUN_RECEIPT.json').read_text());year=p['evaluation_season'];rows,lookup,games=load_truth(source,p,year);own=OwnOnly(rows);queries={q['query_id']:q for q in json.loads((private/'frozen-queries.json').read_text())};c=Counter();traincache={};seenfeatures=set();seenmodels=set();seenmodelpaths=set();samples=set();weekcache={};maximum=0.;near=0
 for name,digest in p['helpers'].items():assert sha(ROOT/'nfl_v2'/name)==digest;c['frozen_helper_hashes']+=1
 assert sha(ROOT/'nfl_v2/distribution_laws.py')==p['law_code_sha256'];assert sha(private/'frozen-queries.json')==p['frozen_queries_sha256']
 def training(target,method,policy,origin,memory):
  fitfloor=year if policy.startswith('H-CURRENT')else max(2022,year-1)if policy.startswith('H-RECENT')else 2022
  key=target,method=='hgb_carry_primary',fitfloor,memory,origin
  if key in traincache:return traincache[key]
  roles=set(POSITIONS)if target==CHART else set(p['source_role_contract']['primary'][target])|set(p['source_role_contract']['extended'].get(target,[]));train=[r for r in rows if r['position']in roles and r['season']>=fitfloor and r['values'][target]is not None and r['available']<origin and(method!='hgb_carry_primary'or r['position']in('QB','RB'))];values=[r['values'][target]for r in train];glob=prior(values,target);priors={pos:prior([r['values'][target]for r in train if r['position']==pos],target)if any(r['position']==pos for r in train)else glob for pos in POSITIONS};tm=max((own.own(r['player_id'],r['position'],target,r['kickoff'],memory)[1]for r in train if own.own(r['player_id'],r['position'],target,r['kickoff'],memory)[1]is not None),default=None)
  for r in train:
   m=own.own(r['player_id'],r['position'],target,r['kickoff'],memory)[1]
   assert m is None or m<r['kickoff'];c['independent_training_row_feature_cutoffs']+=1
  expected=dict(training_n=len(train),training_seasons=sorted({r['season']for r in train}),training_membership_sha256=hashlib.sha256(canonical([(r['game_id'],r['player_id'])for r in train])).hexdigest(),latest_training_label_available=max((r['available']for r in train),default=None),latest_training_feature_available=tm,prior_parameters=priors,prior_position_sample_counts={pos:sum(r['position']==pos for r in train)for pos in POSITIONS});traincache[key]=expected,train;return expected,train
 def weekrows(week):
  # Only one week of saved output at a time; no current2026Week8 input.
  if week not in weekcache:
   weekcache.clear();mapped={}
   with gzip.open(private/'predictions'/f'W{week:02}.csv.gz','rt',newline='')as f:
    for text in csv.DictReader(f):
     if text.get('fit_slot'):mapped[text['fit_slot'],text['query_id'],text['product_id']]=read_row(text)
   weekcache[week]=mapped
  return weekcache[week]
 from threadpoolctl import threadpool_limits
 with threadpool_limits(limits=2):
  for ff in sorted(public.glob('*-FIT.json')):
   fit=json.loads(ff.read_text());target=fit['target'];method=fit['method'];policy=fit['policy_id'];memory=year if policy.endswith('STRICT')else 2022;assert fit['feature_floor']==memory;week=int(fit['slot'][1:3]);origin=min(g['kickoff']for g in games.values()if g['year']==year and g['week']==week);assert fit['fit_cutoff']==origin;expected,train=training(target,method,policy,origin,memory);compare(fit,expected,c);c['exact_fit_membership_seasons_priors_and_cutoff_receipts']+=1
   if method=='glm_law'and target in COUNTS and len(train)>=40:c['GLM_count_eligible_frames']+=1;c['GLM_count_all_zero_eligible_frames']+=all(r['values'][target]==0 for r in train)
   fd=fit['query_features'];path=private/fd['bundle_name'];assert sha(path)==fd['sha256'];entries=unzip(path)
   if fd['sha256']not in seenfeatures:
    seenfeatures.add(fd['sha256']);c['unique_query_feature_hashes']+=1
    for entry in entries:
     q=queries[entry['query_id']];r=lookup[q['game_id'],q['player_id']];assert q['season']==year and q['target']==target and q['week']==week;values,latest=own.own(q['player_id'],q['position'],target,r['kickoff'],memory);compare(entry['features'],values,c);close(entry['latest_feature_available'],latest);c['full_query_source_prefixes']+=1
   if not fit['model']:continue
   md=fit['model'];mp=private/md['bundle_name'];assert sha(mp)==md['sha256'];c['model_references_hash_checked']+=1;seenmodelpaths.add(md['bundle_name'])
   if md['sha256']in seenmodels:continue
   seenmodels.add(md['sha256']);model=pickle.loads(gzip.decompress(mp.read_bytes()));c['unique_models_hash_checked_before_decode']+=1
   if method in('leaf','c02'):assert model.estimator.n_estimators==32 and model.estimator.min_samples_leaf==30 and model.estimator.max_depth==8 and model.estimator.random_state==1701;c['forest_parameter_contracts']+=1
   elif method.startswith('hgb'):
    params=model.get_params();assert model.n_iter_==64 and params['early_stopping']is False and params['max_depth']==3 and params['min_samples_leaf']==10 and params['learning_rate']==.05 and params['l2_regularization']==10 and params['random_state']==1701;c['HGB_parameter_and_iteration_contracts']+=1
   samplekey=target,method,policy
   if samplekey in samples:continue
   chosen=next((e for e in entries if method.startswith('hgb')or e['features'][3]>0),None)
   if chosen is None:continue
   samples.add(samplekey);q=queries[chosen['query_id']];features=chosen['features'];project=lambda f:list(f[:4])+list(f[16:]);features=project(features)if method=='c02'else features;x=np.asarray([[math.nan if v is None else v for v in features]],dtype=float)
   # Rebuild imputer transform statistics from the source training rows for
   # sampled model; no estimator is fitted and no transformation is changed.
   if method in('leaf','c02','glm_law'):
    tx=np.asarray([[math.nan if v is None else v for v in(project(own.own(r['player_id'],r['position'],target,r['kickoff'],memory)[0])if method=='c02'else own.own(r['player_id'],r['position'],target,r['kickoff'],memory)[0])]for r in train]);med=[]
    for column in tx.T:
     vals=sorted(float(v)for v in column if math.isfinite(v));n=len(vals);med.append((vals[(n-1)//2]+vals[n//2])/2 if n else 0.)
    assert np.allclose(model.design.median,med,rtol=0,atol=1e-9);c['sampled_imputer_medians_source_rebuilt']+=1
    transformed=np.column_stack((np.where(np.isfinite(x),x,model.design.median),~np.isfinite(x))).astype(float);design=(transformed-model.design.mean)/model.design.scale if method=='glm_law'else transformed;position=q['position'];role=expected['prior_parameters'][position]
    if method in('leaf','c02'):
     leaves=model.estimator.apply(design)[0];weights=np.zeros(len(model.support))
     for j,hist in enumerate(model.hist):weights+=hist[leaves[j]].toarray().ravel()/32
     weights/=weights.sum();law=dict(kind='mixture',support=model.support,weights=weights,prior=role)
    elif target=='anytime_td':law=dict(kind='bernoulli',p=float(model.estimator.predict_proba(design)[0,list(model.estimator.classes_).index(1.)]))
    else:
     val=float(model.estimator.predict(design)[0]);law=dict(kind='poisson',mean=val)if target in COUNTS else dict(kind='signed',center=int(np.rint(val)),q=model.scale[position]/(1+model.scale[position]))
    product='event_probability'if target=='anytime_td'else'mean';r=weekrows(week)[fit['slot'],q['query_id'],product];wanted=summaries(law,r['actual_grid']if target==CHART else r['actual']);saved=dict(r['distribution_summary'])
    if target==CHART:
     assert saved['grid_denominator']==50
     for field in('mean','lower_median','q05','q95','interval90_width','crps'):
      if saved[field]is not None:saved[field]*=50
    for field,v in wanted.items():
     if isinstance(v,(bool,type(None))):assert saved[field]==v
     elif field in('q05','lower_median','q95')and not math.isclose(v,saved[field],rel_tol=0,abs_tol=1e-8):
      low,high=bounds(law);z=np.arange(low,high+1,dtype=float);cdf=float(masses(law,z[z<=saved[field]]).sum());prob={'q05':.05,'lower_median':.5,'q95':.95}[field];assert abs(cdf-prob)<3e-12 and abs(v-saved[field])<=1;near+=1
     else:
      maximum=max(maximum,abs(saved[field]-v));assert math.isclose(saved[field],v,rel_tol=2e-9,abs_tol=3e-7),(fit['slot'],field,saved[field],v)
     c['independent_PMF_summary_fields']+=1
    c['sampled_fitted_laws']+=1
   else:
    pred=float(model.predict_proba(x)[0,list(model.classes_).index(1.)])if method=='hgb_TD'else float(model.predict(x)[0]);pred=max(0.,pred)if target in COUNTS else pred;product='log_loss_probability'if method=='hgb_TD'else'absolute_error_point'if method in('hgb_L1','hgb_carry_primary')else'squared_error_mean'if method=='hgb_L2'else'poisson_intended_mean_point'
    if method=='hgb_carry_primary':
     registered=next(cell['products']for cell in p['method_cells']if cell['method']==method and cell['target']==target);assert len(registered)==1;product=registered[0]
    r=weekrows(week)[fit['slot'],q['query_id'],product];close(r['prediction'],pred);c['sampled_HGB_point_inferences']+=1
 # Separately fitted models can serialize to identical bytes. Count retained
 # artifact paths separately from distinct model hashes and alias references.
 assert len(seenmodelpaths)==run['retained_models'];c['retained_model_artifact_paths']=len(seenmodelpaths)
 return dict(state='PASS_SEASON_RELATIVE_FULL_FEATURE_TRAINING_MEMBER_AND_RETAINED_MODEL_SAMPLE_REPLAY',season=year,protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),run_receipt_sha256=sha(public/'RUN_RECEIPT.json'),checks=dict(c),max_law_float_difference=maximum,near_exact_quantile_boundary_cases=near,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),scope='Allfitreceipts/modelhashes/queryprefixes; sampledmodelimputation/inference/independentPMFsums. Sourcecurrentvintage+seven-dayavailability assumption, notauthenticatedhistoricalissuance. 2025v1RAfallback/productgap separatelyrepaired.',new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--public',type=Path,required=True);a.add_argument('--private',type=Path,required=True);a.add_argument('--source',type=Path,required=True);v=a.parse_args();r=verify(v.public,v.private,v.source);(HERE/('SEASON_'+str(r['season'])+'_FEATURE_MODEL_INDEPENDENT_REVIEW.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
