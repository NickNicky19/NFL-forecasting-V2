"""Independent retained-pilot verification; no fits, unsafe models or grading."""
import argparse,collections,gzip,hashlib,importlib,json,math,sys,types
from pathlib import Path
import numpy as np
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def eq(a,b,tol=2e-10):assert math.isclose(a,b,rel_tol=tol,abs_tol=tol),(a,b)
def forbidden(*args,**kwargs):raise AssertionError('Fitting forbidden during independent pilot audit')
def primitive_median(cdf):
 for n in range(1000):
  if cdf(n)>=.5:return n
 raise AssertionError('Count median outside bounded audit range')
def nb_cdf(n,mu,shape):
 if n<0:return 0.
 if not mu:return 1.
 p=shape/(shape+mu);mass=p**shape;total=mass
 for k in range(n):mass*=((shape+k)/(k+1))*(1-p);total+=mass
 return total
def main():
 ap=argparse.ArgumentParser()
 for k in('repo','restored','output'):ap.add_argument('--'+k,type=Path,required=True)
 a=ap.parse_args();base='reports/player-context-matchup-01/B';live=a.repo/base;fresh=a.restored/base
 manifest=read(live/'PILOT_SOURCE_RETENTION_MANIFEST_V1.json');receipt=read(live/'PILOT_GITHUB_RESTORATION_RECEIPT_V1.json')
 assert sha(live/'PILOT_SOURCE_RETENTION_MANIFEST_V1.json')==receipt['manifest_sha256']
 expected={r['path']:r for r in manifest['source_files']};assert len(expected)==receipt['files_verified']==123
 total=0
 for r in receipt['files']:
  p=a.restored/r['path'];assert r['path']in expected and sha(p)==r['sha256']==expected[r['path']]['sha256']and p.stat().st_size==r['bytes']==expected[r['path']]['bytes'];total+=r['bytes']
 assert total==receipt['total_bytes']==3531059
 protocol=read(fresh/'qb-wave-v1/FROZEN_PROTOCOL.json')
 for path,digest in protocol['code_sha256'].items():
  candidate=a.restored/path
  if not candidate.exists():candidate=a.repo/path
  assert sha(candidate)==digest
 package=types.ModuleType('fresh_b_qb_audit');package.__path__=[str(a.restored/'nfl_v2'),str(a.repo/'nfl_v2')];sys.modules[package.__name__]=package
 ctx=importlib.import_module('fresh_b_qb_audit.player_context_matchup')
 portable=importlib.import_module('fresh_b_qb_audit.player_context_typed_adapter_v2')
 ctx.CompletionModel.fit=forbidden;ctx.FittedLawModel.fit=forbidden;ctx.Design.fit=forbidden
 rows=read(a.restored/protocol['inputs']['path']);assert len(rows)==2901 and sha(a.restored/protocol['inputs']['path'])==protocol['inputs']['sha256']
 good=sorted([r for r in rows if r['physical_participation']and r['target_parity']],key=lambda r:(r['available'],r['kickoff'],r['game_id'],r['player_id']))
 chosen=read(fresh/'qb-wave-v1/SELECTED_EARLIER_CONFIG.json');assert (chosen['window'],chosen['strength'])==(8,20.)
 for r in chosen['validation']:
  assert sum(w['n']for w in r['weekly'])==r['n']==302
  eq(sum(w['n']*w['NLL']for w in r['weekly'])/r['n'],r['NLL'])
 assert min(chosen['validation'],key=lambda r:r['NLL'])['window']==8
 history=ctx.ContextHistory(rows,8,20.)
 packet=read(fresh/'qb-wave-v1/predictions/2025-W01.json.gz');pred=packet['rows'];assert len(pred)==272
 qby={(r['game_id'],r['player_id']):r for r in rows};queries={k:qby[k]for k in{(r['game_id'],r['player_id'])for r in pred}};assert len(queries)==34
 origin=min(q['kickoff']for q in queries.values());train=[r for r in good if r['season']>=2024 and r['available']<origin]
 priormu=max(.05,sum(r['official_completions']for r in train)/len(train));priorq=priormu/(1+priormu)
 # Verify fit lineage for all48 tuning and33 pilot fits, without re-fitting.
 fits={};conditional=0;chronology=0
 for path in(fresh/'qb-wave-v1/fits').glob('*.json.gz'):
  f=read(path);slot=f['slot'];fits[slot]=f
  if slot.startswith('TUNE-'):
   week=int(slot.split('-W')[1][:2]);cut=min(r['kickoff']for r in rows if r['season']==2024 and r['week']==week);tr=[r for r in good if r['season']>=2023 and r['available']<cut]
  else:
   cut=origin;tr=train
   if '-P3-'in slot:
    suffix=slot.split('-P3-')[1];pid=next(q['player_id']for q in queries.values()if hashlib.sha256(q['player_id'].encode()).hexdigest()[:16]==suffix)
    tr=sorted([r for r in train if r['player_id']==pid],key=lambda r:(r['kickoff'],r['game_id']))[-16:]
    assert len(tr)>=8 and sum(r['official_attempts']for r in tr)>=160
  assert f['training_rows']==len(tr)and f['latest_training_label']==max(r['available']for r in tr)<cut
  assert f['latest_training_feature']is None or f['latest_training_feature']<cut
  if 'training_membership_sha256'in f:
   assert hashlib.sha256(json.dumps([(r['game_id'],r['player_id'])for r in tr]).encode()).hexdigest()==f['training_membership_sha256']
  if 'optimization'in f['model']:
   assert f['model']['optimization']['success']and f['model']['optimization']['finite'];conditional+=1
  chronology+=1
 assert len(fits)==81 and conditional==77
 width={};forest_checks=0;conditional_checks=0;exposure_checks=0;sorted_parity=0;fallback=0;max_error=0.
 for record in pred:
  q=queries[record['game_id'],record['player_id']];method=record['method'];d=history.describe(q);cut=q['kickoff']
  assert record['fit_cutoff']==origin<cut+1 and record['feature_cutoff']==cut and not record['original_issuance']
  assert record['latest_source_available']is None or record['latest_source_available']<cut
  actual=q['official_attempts']if record['target']=='pass_att'else q['official_completions'];assert record['actual']==(actual if q['physical_participation']else None)
  earlier=[r for r in good if r['available']<cut];own=sorted([r for r in earlier if r['player_id']==q['player_id']],key=lambda r:(r['kickoff'],r['game_id']))[-8:]
  aa=np.sum([r['context_attempts']for r in earlier],axis=0);cc=np.sum([r['context_completions']for r in earlier],axis=0)
  oa=np.sum([r['context_attempts']for r in own],axis=0)if own else np.zeros(25);oc=np.sum([r['context_completions']for r in own],axis=0)if own else np.zeros(25)
  pooled=(cc+1)/(aa+2);mix=(oa+20*(aa+1)/(aa.sum()+25))/(oa.sum()+20)
  assert np.allclose(d['pooled'],pooled,rtol=1e-13,atol=1e-13)and np.allclose(d['mix'],mix,rtol=1e-13,atol=1e-13)
  assert d['own_attempts']==oa.sum()and d['own_completions']==oc.sum()
  exp_earlier=[r['official_attempts']for r in earlier if r['season']>=q['season']-1];own_attempts=[r['official_attempts']for r in own]
  mu=(sum(own_attempts)+4*np.mean(exp_earlier))/(len(own_attempts)+4)
  var=(sum(v*v for v in own_attempts)+4*np.mean(np.square(exp_earlier)))/(len(own_attempts)+4)-mu*mu
  shape=min(200.,max(.5,mu*mu/max(.01,var-mu)))if mu else 200.
  if method.startswith('E'):
   f=fits[record['model_slot']]['model'];raw=np.asarray(record['features'],float);width[method]=len(raw)
   assert np.allclose(raw,history.direct_features(q,method),equal_nan=True)
   med=np.asarray(f['design']['median']);xx=np.r_[np.where(np.isfinite(raw),raw,med),~np.isfinite(raw)].astype(np.float32);support=np.asarray(f['support']);weights=np.zeros(len(support))
   for tree in f['trees']:
    node=0;depth=0
    while tree['left'][node]!=-1:
     col=tree['feature'][node];node=tree['left'][node]if xx[col]<=tree['threshold'][node]else tree['right'][node];depth+=1;assert depth<=8
    h=tree['leaf_histogram']
    for n,c,v in zip(h['rows'],h['columns'],h['values']):
     if n==node:weights[c]+=v/32
   assert math.isclose(float(weights.sum()),1,abs_tol=1e-10);weights/=weights.sum()
   expected=.95*float(weights@support)+.05*priormu;median=primitive_median(lambda n:.95*float(weights[support<=n].sum())+.05*(1-priorq**(n+1)))
   eq(expected,record['mean']);assert median==record['lower_median'];assert np.allclose(weights,record['law']['weights'],rtol=1e-12,atol=1e-12)
   eq(record['law']['prior']['q'],priorq);forest_checks+=1
  else:
   if method=='COMMON_EXPOSURE':expected=mu;exposure_checks+=1
   else:
    if method=='P3'and record['fallback']=='shared_no_pooling_support_fallback':slot='2025-W01-P1';fallback+=1
    elif method=='P3':slot='2025-W01-P3-'+hashlib.sha256(q['player_id'].encode()).hexdigest()[:16]
    else:slot='2025-W01-'+method
    payload=fits[slot]['model'];beta=payload['beta'];manual=[]
    for context in range(25):
     x=[0.]*len(beta);x[context]=1.;x[25]=math.log((d['own_completions']+1)/(d['own_attempts']-d['own_completions']+1));x[26]=d['opponent_residual_main'];x[27]=d['opponent_residual'][context];x[28]=d['team_residual'];offset=29
     for field in('team','opponent','player_id'):
      if field not in payload['levels']:continue
      levels=payload['levels'][field]
      if q[field]in levels:x[offset+levels.index(q[field])]=1.
      offset+=len(levels)
     eta=math.fsum(b*v for b,v in zip(beta,x));manual.append(1/(1+math.exp(-eta)))
    assert np.allclose(manual,record['components']['conditional_completion_probability'],rtol=1e-12,atol=1e-12)
    normal=portable.restore_completion(payload,producer_version=ctx.VERSION).probabilities(q,history)
    reordered=portable.restore_completion(json.loads(json.dumps(payload,sort_keys=True)),producer_version=ctx.VERSION).probabilities(q,history)
    assert np.allclose(normal,reordered,rtol=0,atol=0)and np.allclose(normal,manual,rtol=1e-12,atol=1e-12);sorted_parity+=1
    probability=math.fsum(m*v for m,v in zip(mix,manual));eq(probability,record['components']['integrated_completion_probability']);assert 0<=probability<=1
    expected=mu*probability;conditional_checks+=1
   eq(record['mean'],expected);eq(record['law']['mean'],expected);eq(record['law']['shape'],shape)
   assert primitive_median(lambda n:nb_cdf(n,expected,shape))==record['lower_median']
   # Shared gamma-Poisson thinning: completion marginal has lower mean and
   # the same shape; probability ordering follows without mean-as-probability.
   if method!='COMMON_EXPOSURE':
    for threshold in(0,10,20,40):assert nb_cdf(threshold,expected,shape)+1e-12>=nb_cdf(threshold,mu,shape)
  max_error=max(max_error,abs(record['mean']-expected))
 assert (forest_checks,conditional_checks,exposure_checks,sorted_parity)==(136,102,34,102)
 assert width==dict(E0=20,E1=102,E2=154,E3=179)
 annotations=read(fresh/'qb-wave-v1/PILOT_CLOCK_SCOPE_ANNOTATIONS_V2.json')
 for r in annotations['rows']:
  q=queries[r['game_id'],r['player_id']];_,latest=history.base_history.get(q['player_id'],'QB','pass_cmp',q['kickoff']);assert latest==r['actual_latest_query_feature_available']
 # Freeze fitted parameters; mutate later outcomes only. Earlier query
 # features must not use them. No optimizer or forecast scorer is invoked.
 changed=[dict(r,official_completions=r['official_completions']+100)if r['kickoff']>=origin else r for r in rows]
 mutant=ctx.ContextHistory(changed,8,20.)
 for q in queries.values():
  for method in('E0','E1','E2','E3'):assert np.allclose(history.direct_features(q,method),mutant.direct_features(q,method),equal_nan=True)
 result=dict(state='PASS_INDEPENDENT_FRESH_RESTORED_PILOT_TYPED_PARITY',producer_commit=receipt['producer_commit'],
  source_manifest_sha256=receipt['manifest_sha256'],restoration_receipt_sha256=sha(live/'PILOT_GITHUB_RESTORATION_RECEIPT_V1.json'),fresh_files_rehashed=123,fresh_bytes_rehashed=total,
  original_pilot_prediction_sha256=sha(fresh/'qb-wave-v1/predictions/2025-W01.json.gz'),
  fitted_payload_lineages_checked=chronology,successful_conditional_payloads=conditional,forest_rows_independently_checked=forest_checks,
  conditional_rows_independent_dot_sigmoid=conditional_checks,common_exposure_rows_independent_moments=exposure_checks,
  normal_sorted_JSON_adapter_parity_rows=sorted_parity,P3_shared_fallback_queries=fallback,queries=34,prediction_records=272,
  direct_raw_widths=width,maximum_mean_roundoff=max_error,future_outcome_mutation_feature_checks=136,E0_clock_annotations_checked=len(annotations['rows']),
  typing='Mean/lower_median/fullcountlaw remain separate; empirical moment-shrunk gamma-Poisson exposure, not a fully Bayesian posterior. Conditional coefficients and context mix are point estimates. Shared latent thinning assumption, not independent ATT/CMP draws.',
  independent_scope='All123restoredfilebytes and81fitlineages. Primitive treehistogram/prior moments, NBrecurrence medians, fixed-order coefficient dot-sigmoid; actualportableadapter normal/sortedJSON parity. Existing producer ContextHistory reused for descriptions, independently checked pooled/mix counts and exposure moments. No rawPBP/FTN re-derivation.',
  preserved_limits=['One unscored2025W1pilot; software verificationadds0NFLtestweeks','Sourcecurrent/revised+7dayreconstruction, notauthenticated historicalpublication','RetrospectiveQBstat membership, not exante offers','Observed16gamewindow and E0upperbound sidecars apply','Pilotthreadenforcement limitation retained; no repeatedfits','No sharedC admission or ownerrelease from readback'],
  NFL_fits=0,unsafe_model_loads=0,scoring_runs=0,new_forecasts=0,source_downloads=0)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(state=result['state'],files=123,rows=272,sha256=sha(a.output))))
if __name__=='__main__':main()
