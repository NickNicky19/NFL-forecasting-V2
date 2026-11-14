"""Bounded exposed diagnosis of retained rows; no fitting, new gate or grader."""
import gzip,hashlib,importlib.util,json,math
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
OLD=ROOT/'reports/profile-increment-to-release-01/B';CONTEXT=ROOT/'reports/player-context-matchup-01/B'
def read(p):
 p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def key(r):return r['game_id'],r['player_id'],r['target']
def cdf(law,x):
 y=math.floor(x);return .95*math.fsum(w for s,w in zip(law['support'],law['weights'])if s<=y)+.05*(0. if y<0 else 1-law['prior']['q']**(y+1))
def summary(rows):
 n=len(rows);out=dict(n=n,wins=sum(r['grade']=='WIN'for r in rows),losses=sum(r['grade']=='LOSS'for r in rows))
 out['hit_rate']=out['wins']/n if n else None
 for name in('mean_error','absolute_mean_error','forecast_minus_line','actual_minus_line','own_age_days','source_age_days','confidence'):
  values=[r[name]for r in rows if r[name]is not None];out[name]=dict(n=len(values),mean=float(np.mean(values))if values else None,min=min(values)if values else None,max=max(values)if values else None)
 return out
spec=importlib.util.spec_from_file_location('retained_offers',CONTEXT/'independent/inventory_retained_qb_offers_v1.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sources=read('/tmp/b-context-offer-sources.json');offers=[dict(r,source_hash=sha(p))for w,p in sorted(sources.items())for r in m.iter_offers(Path(p),int(w))if r['target']=='pass_cmp']
assert len(offers)==112
preds={};pred_bindings={}
for path in sorted((OLD/'opportunity-wave-v1/predictions').glob('2026-W*.json.gz')):
 for i,r in enumerate(read(path)['rows']):
  if r['method']in('R0','R2','R3'):preds[r['method'],key(r)]=r;pred_bindings[r['method'],key(r)]=dict(artifact=str(path.relative_to(ROOT)),sha256=sha(path),row_offset=i)
inputs=read(CONTEXT/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz');im={(r['game_id'],r['player_id']):r for r in inputs}
profiles={ (p['identity']['game_id'],p['identity']['player_id']):p for p in read(OLD/'source-profiles/QB_OPPORTUNITY_ASOF_PROFILES_V2.json.gz')}
public_table=read(OLD/'opportunity-scores-v1/COMMON_CONTROL_TABLE.json');numeric=read(OLD/'opportunity-scores-v1/SCORES.json')
method_results=[];example_index=[];offsets=[]
for arm in('R0','R2','R3'):
 rows=[];lag_ages=[];raw_newer=Counter();prior_ages=[]
 for offer in offers:
  p=preds[arm,key(offer)];prob_over=1-cdf(p['law'],offer['line']);prob_under=cdf(p['law'],math.ceil(offer['line'])-1)
  side='over'if prob_over>prob_under else'under'if prob_under>prob_over else None;assert side is not None
  a,l=Decimal(str(offer['actual'])),Decimal(str(offer['line']));assert a!=l
  grade='WIN'if(side=='over')==(a>l)else'LOSS';q=im[p['game_id'],p['player_id']];profile=profiles[p['game_id'],p['player_id']]
  prior=[r for r in inputs if r['player_id']==p['player_id']and r['physical_participation']and r['target_parity']and r['available']<q['kickoff']];prior.sort(key=lambda r:(r['kickoff'],r['game_id'],r['player_id']));prior=prior[-8:]
  assert prior and prior[-1]['game_id']==p['last_prior_game']
  raw_prior=[r for r in inputs if r['player_id']==p['player_id']and r['physical_participation']and r['target_parity']and r['kickoff']<q['kickoff']]
  raw_prior.sort(key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
  newly_excluded=[r for r in raw_prior if r['available']>=q['kickoff']];raw_newer['offers_with_earlier_kickoff_excluded_by_proxy']+=bool(newly_excluded);raw_newer['earlier_game_rows_excluded_by_proxy']+=len(newly_excluded)
  latest_raw_age=(q['kickoff']-raw_prior[-1]['kickoff'])/86400 if raw_prior else None
  own_age=(q['kickoff']-prior[-1]['kickoff'])/86400;source_age=(q['kickoff']-prior[-1]['available'])/86400
  lag_ages.append(own_age);prior_ages.append(latest_raw_age)
  row=dict(example_key=digest([arm,*key(offer)]),method=arm,side=side,grade=grade,mean_error=p['mean']-offer['actual'],absolute_mean_error=abs(p['mean']-offer['actual']),forecast_minus_line=p['mean']-offer['line'],actual_minus_line=offer['actual']-offer['line'],own_age_days=own_age,source_age_days=source_age,confidence=max(prob_over,prob_under),support=p['pregame_role_band'],fallback=p['fallback'],prior_games=len(prior),prior_game_index_sha256=digest([r['game_id']for r in prior]),decision_time=q['kickoff'],retained_inference_time=p['actual_execution_utc'],evidence='CURRENT_REVISED_7D_RECONSTRUCTION_TIMING_UNVERIFIED_ACTUAL_LINE_DIAGNOSTIC',forecast=pred_bindings[arm,key(offer)],offer_source_sha256=offer['source_hash'],offer_membership_sha256=digest([*key(offer),str(offer['line'])]))
  row['age_bin']='7_TO_LT14'if own_age<14 else'14_TO_LT21'if own_age<21 else'21_PLUS'
  rows.append(row)
 groups={}
 for group in('side','grade','age_bin','support'):
  groups[group]={value:summary([r for r in rows if r[group]==value])for value in sorted({r[group]for r in rows})}
 for side in('over','under'):
  for grade in('WIN','LOSS'):
   selected=sorted([r for r in rows if r['side']==side and r['grade']==grade],key=lambda r:r['example_key'])[0]
   example_index.append({k:selected[k]for k in('example_key','method','side','grade','evidence','forecast','offer_source_sha256','offer_membership_sha256','prior_game_index_sha256')})
 selected=sorted([r for r in rows if r['grade']=='WIN'],key=lambda r:(-r['absolute_mean_error'],r['example_key']))[0]
 example_index.append(dict({k:selected[k]for k in('example_key','method','side','grade','evidence','forecast','offer_source_sha256','offer_membership_sha256','prior_game_index_sha256')},diagnostic='MAX_ABSOLUTE_MEAN_ERROR_AMONG_CORRECT; numerical error can be large while the selected side remains right'))
 reliability=next(r['probability']for r in public_table if r['method'].endswith(':'+arm)and r['window']=='ALL'and r['policy']=='P2_STATISTICAL_LAW')
 numerical={}
 for scope in('ALL','MATCHED_OFFERS_W5_W8'):
  numerical[scope]={r['product_id']:{k:r[k]for k in('n','mae','bias','rmse','p90_abs','p95_abs')}for r in numeric if r.get('record_kind')=='forecast_evaluation_view'and r['season']==2026 and r['week']==scope and r['procedure_id'].endswith(':'+arm)and r['fallback_view']=='FULL_SYSTEM'}
 method_results.append(dict(method=arm,full_board=summary(rows),groups=groups,reused_probability_discrimination_and_reliability=reliability,reused_numerical=numerical,earlier_proxy_exclusions=dict(raw_newer),own_last_game_age_quantiles=np.quantile(lag_ages,[0,.25,.5,.75,1]).tolist(),latest_earlier_kickoff_age_quantiles=np.quantile(prior_ages,[0,.25,.5,.75,1]).tolist(),source_age_note='Age since constructed kickoff+7d admission, not authentic source observation age.',component_forecast_status='NOT_APPLICABLE; direct forest law has no frozen opportunity/conversion forecast components. Historical profile values are inputs, not predicted components.',prior_and_fallback=dict(no_own_history_offers=0,declared_fallback_counts=dict(Counter(r['fallback']for r in rows)),earlier_label_prior_mass=.05,learned_leaf_mass=.95)))
# Separate unchanged explicit-component procedure. Algebra uses postgame A,C
# only for diagnosis; it is never supplied to inference or used as a repair.
p1={key(r):r for f in sorted((CONTEXT/'qb-wave-v1/predictions').glob('2026-W*.json.gz'))for r in read(f)['rows']if r['method']=='P1'}
component_rows=[]
for o in offers:
 r=p1[key(o)];q=im[r['game_id'],r['player_id']];a=q['official_attempts'];c=q['official_completions'];ah=r['components']['attempt_law']['mean'];ph=r['components']['integrated_completion_probability']
 assert a>0;actual_rate=c/a;volume=(ah-a)*ph;conversion=a*(ph-actual_rate);assert abs(volume+conversion-(r['mean']-c))<1e-10
 component_rows.append(dict(workload_error=ah-a,conversion_rate_error=ph-actual_rate,workload_term=volume,conversion_term=conversion,total_error=r['mean']-c,opposing=volume*conversion<0))
component=dict(procedure='B-player-context-matchup-01-v1:P1',n=len(component_rows),formula='C_hat-C=(A_hat-A)*p_hat + A*(p_hat-C/A); descriptive postgame decomposition using frozen component forecasts.',mean_attempt_error=float(np.mean([r['workload_error']for r in component_rows])),attempt_MAE=float(np.mean([abs(r['workload_error'])for r in component_rows])),mean_conversion_rate_error=float(np.mean([r['conversion_rate_error']for r in component_rows])),mean_workload_term=float(np.mean([r['workload_term']for r in component_rows])),mean_conversion_term=float(np.mean([r['conversion_term']for r in component_rows])),offsetting_sign_cases=sum(r['opposing']for r in component_rows),limit='No causal attribution, deployable component substitution, repair, or transfer of this explanation to direct E3/R2/R3. Actual context-mix versus conversion contribution is not isolated by this two-factor aggregate algebra.')
reuse_paths=['reports/right-and-wrong-diagnostic-20261031k/ALL_METHOD_DIAGNOSTIC_SUMMARIES.json','reports/right-and-wrong-diagnostic-20261031k/lineage/inspection-v2/QUERY_FRESHNESS_AND_FALLBACK.json','reports/profile-increment-to-release-01/B/independent/MUTATION_FEATURE_USE_INDEPENDENT_REVIEW_V1.json','reports/audit-remediation-20261105-v1/B/B_FRESHNESS_RECIPE_SCOPE_V1.json']
out=dict(id='B-PROFILE-INCREMENT-RETAINED-CMP-DIAGNOSIS-v1',registration_sha256=sha(OUT/'DIAGNOSTIC_SCOPE_BEFORE_ROW_INSPECTION_V1.json'),reused_evidence=[dict(path=p,sha256=sha(ROOT/p))for p in reuse_paths],methods=method_results,explicit_component_diagnostic=component,safe_example_index=example_index,classification=[dict(status='VERIFIED_DEFECT',finding='None newly demonstrated in inspected retained forecast/scoring path. Prefit V1 source denominator and runner-key issues were already corrected before any fit; do not reopen them.'),dict(status='MEASURED_WEAKNESS',finding='R0/R2/R3 over-event AUC below0.5 and poor higher-confidence groups on112exposedoffers; negative completion bias stronger on offered than broad rows. Fourweek descriptive result, not universal lackofsignal.'),dict(status='MEASURED_WEAKNESS',finding='The strict7d policy excludes eligible-by-kickoff prior-game rows; counts quantify coverage only. Kickoffbeforecutoff does not prove completed statistics were originally available.'),dict(status='PLAUSIBLE_HYPOTHESIS',finding='Aligning a separately named earlier reconstructed availability policy in both trainingandquery may improve useofrecentgameinformation. Requires next registered matched test; no causal accuracy cost yet measured.'),dict(status='UNRESOLVED',finding='Whether timing, role/context drift, model ranking capacity or missing pregame role information causes these misses. No authenticated historical snapshot or intervening experiment establishes cause.')],new_fits=0,new_source_collections=0,new_original_forecasts=0,new_NFL_weeks=0,protected_rows_exported=False)
dest=OUT/'RETAINED_CMP_BOTTLENECK_DIAGNOSTIC_V1.json';assert not dest.exists();dest.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(methods=[dict(method=r['method'],age=r['own_last_game_age_quantiles'],proxy_exclusions=r['earlier_proxy_exclusions'],full_board=r['full_board'])for r in method_results],components=component),indent=2))
