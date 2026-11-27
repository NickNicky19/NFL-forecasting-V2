"""Recover retained leaf laws on C's board; no estimator calls or new fits."""
import collections,gc,gzip,hashlib,json,math,pickle,resource,sys,time
from contextlib import ExitStack
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import abc_b_c_bound_replay as a,abc_b_glm_exact_line_replay as g,grade_saved_week8 as existing
from nfl_v2 import distribution_wave_v2 as base,distribution_wave as old,scoring,full_provider_prop_replay as core
from nfl_v2.saved_leaf_law_lookup import lookup
from nfl_v2.distribution_laws import Law
SPECS=[('distribution-wave-v2','reports/continuation-20261030/distribution-wave-v2'),('ordered-information-ablation-v1','reports/continuation-20261030b/ordered-information-ablation-v1'),('qualified-defense-information-v1','reports/continuation-20261030c/qualified-defense-information-v1')]
TARGETS={'pass_yd','rush_yd','rec','rec_yd'}
def digest_ids(ids):return hashlib.sha256(json.dumps(sorted(ids),separators=(',',':')).encode()).hexdigest()
def sources(evidence):
 for folder,public in SPECS:
  for p in sorted((evidence/folder/'prediction-chunks').glob('W0[23]-*.json.gz')):
   j=a.load(p)
   if not j['rows']or j['rows'][0]['target']not in TARGETS:continue
   if folder=='distribution-wave-v2'and j['rows'][0]['family']!='ordered_leaf_cdf':continue
   yield folder,public,p,j
def prepare(evidence,out):
 out.mkdir(exist_ok=False);members=[];fits={};rows=0
 for folder,public,p,j in sources(evidence):
  members.append(dict(member_id=folder+'/prediction-chunks/'+p.name,sha256=a.sha(p),bytes=p.stat().st_size))
  for r in j['rows']:
   if r['population']!='primary'or r['product_id']!='mean':continue
   rows+=1;fit=public+'/'+r['fit_slot']+'-FIT.json'
   if fit in fits:continue
   f=a.load(ROOT/fit);m=f.get('model');binding=dict(fit_receipt=fit,fit_sha256=a.sha(ROOT/fit),source_folder=folder,training_membership_sha256=f.get('training_membership_sha256'),model=None)
   if m:
    member=m.get('bundle_name',m.get('name'));mp=evidence/folder/member
    if not mp.exists()and m.get('reused_from')=='v2-distribution-controls-reconstruction-v1':mp=evidence/'distribution-wave-v1'/member
    if not mp.exists()or a.sha(mp)!=m['sha256']:raise ValueError('MODEL_MEMBER_UNAVAILABLE_OR_HASH_MISMATCH:'+fit)
    binding['model']=dict(member_id=str(mp.relative_to(evidence)),sha256=m['sha256'],bytes=mp.stat().st_size)
   fits[fit]=binding
 a.save(out/'FROZEN_PACKAGE.json',dict(id='B-C-RETAINED-LEAF-EXACT-LINE-LAWS-v1',at_utc=datetime.now(timezone.utc).isoformat(),source_C_ref=a.CREF,core_protocol_sha256='fa19581487519a854948269bc1ce328cbbcdc734afee2464f1ff778d1ff241a1',code_sha256=a.sha(__file__),lookup_sha256=a.sha(ROOT/'nfl_v2/saved_leaf_law_lookup.py'),members=members,fits=list(fits.values()),source_primary_mean_rows=rows,
  choice='All four C W2-W3 targets and every retained base Leaf/C02/D1/D2 history policy, chosen for recoverable source/model coverage. No result-based pruning. Earlier point/GLM scores remain unchanged.',
  mechanism='Original32tree response histograms at saved leafIDs, original0.05 samefit prior mixture; fallback law from original parameters. Validate retained moments/quantiles before scoring. No estimator predict/apply/transform/fit; only hash-qualified own-run model objects.',
  history='Exact CURRENT-common older memory, strict CURRENT, RECENT and MULTI policies retained; four-observed-position-group D1/D2 windows, not scheduled-team-game alternative.',
  selection='Existing P2 choose higher exact-line over/under probability; tie tolerance1e-12 abstain. Modelled appearance, not authenticated bookmaker nonvoid. Technical unavailable is not confidence abstention.',
  grading='Reuse B core threshold engine and probability metrics; C alone admits shared results. Source C corrected v7.1 board; current/revised football reconstruction, last-recorded quote timing unverified.',
  retention='Existing original models/chunks retain approved retention contracts; bounded reproducible derivatives owner-local only, no offhost restoration claimed. Large-fit recovery gate unchanged.',
  budget=dict(new_fits=0,new_model_inference=0,max_wall_seconds=300,max_RSS_bytes=1610612736,max_private_bytes=8388608,max_threads=2),research_exposure='All target periods already exposed; no new holdout, calibration, inversion or remedy.',new_issued_forecasts=0))
 print(json.dumps(dict(state='PREFLIGHT_HASH_VERIFIED_BEFORE_UNPICKLE',fit_slots=len(fits),models=sum(v['model']is not None for v in fits.values()),members=len(members))))
def run(evidence,private,snapshot,out):
 start=time.monotonic();p=a.load(out/'FROZEN_PACKAGE.json');assert a.sha(__file__)==p['code_sha256']and a.sha(ROOT/'nfl_v2/saved_leaf_law_lookup.py')==p['lookup_sha256'];assert not(out/'SCORES.json').exists();private.mkdir(exist_ok=False)
 bindings={v['member_id']:v for v in p['members']};fits={v['fit_receipt']:v for v in p['fits']};wanted=collections.defaultdict(list);receipts={};proof=[];checks=collections.Counter();laws=collections.defaultdict(dict)
 c,_=a.c_rows(snapshot);byoffer=collections.defaultdict(dict)
 for r in c:byoffer[r['offer_id']][r['method_id']]=r
 offers={oid:v['P2_LAW']for oid,v in byoffer.items()};opportunity={(q['game_id'],q['player_id'],q['category']):q for q in offers.values()};assert len(opportunity)==len(offers)==968
 for folder,public,path,j in sources(evidence):
  mid=folder+'/prediction-chunks/'+path.name;assert a.sha(path)==bindings[mid]['sha256']
  for r in j['rows']:
   if r['population']!='primary'or r['product_id']!='mean'or(r['game_id'],r['player_id'],r['target'])not in opportunity:continue
   fit=public+'/'+r['fit_slot']+'-FIT.json';f=a.load(ROOT/fit);assert a.sha(ROOT/fit)==fits[fit]['fit_sha256'];receipts[fit]=f;q=opportunity[r['game_id'],r['player_id'],r['target']]
   assert r['cutoff']==a.instant(q['decision_UTC'])and r['position']==q['position']
   for v in [r['latest_feature_available'],f.get('latest_training_label_available'),f.get('latest_training_feature_available')]:assert v is None or v<r['cutoff']
   assert a.instant(f['fit_cutoff_utc'])<=r['cutoff'];wanted[fit].append((r,q));checks['chronology']+=1
 def guard():
  if time.monotonic()-start>p['budget']['max_wall_seconds']or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>p['budget']['max_RSS_bytes']:raise RuntimeError('REGISTERED_RESOURCE_BOUND')
 def forbidden(*args,**kwargs):raise AssertionError('ESTIMATOR_EXECUTION_FORBIDDEN')
 from sklearn.ensemble import ExtraTreesRegressor
 with ExitStack()as stack:
  for cls,names in [(base.FittedLawModel,('predict','fit')),(old.FittedLawModel,('predict','fit')),(ExtraTreesRegressor,('predict','apply','fit','decision_path')),(base.Design,('transform','fit')),(old.Design,('transform','fit'))]:
   for name in names:stack.enter_context(patch.object(cls,name,forbidden))
  for fit,qq in sorted(wanted.items()):
   guard();binding=fits[fit];f=receipts[fit];model=None
   if binding['model']:
    mp=evidence/binding['model']['member_id'];assert a.sha(mp)==binding['model']['sha256'];model=pickle.loads(gzip.decompress(mp.read_bytes()));assert model.family=='ordered_leaf_cdf'and len(model.hist)==32
   maximum=0.
   for r,q in qq:
    ref=r['law_reference'];params=ref.get('fallback_prior')
    if params:law=Law(**params)
    elif ref.get('leaf_ids')is not None and model is not None:law,params=lookup(model.support,model.hist,ref['leaf_ids'],f['prior_parameters'][r['position']]);checks['histogram_lookup']+=1
    else:raise ValueError('NO_QUALIFIED_RETAINED_LAW:'+fit)
    s=law.summary()
    for field in ['mean','lower_median','q05','q95','zero_mass']:
     d=abs(s[field]-r['distribution_summary'][field]);maximum=max(maximum,d);assert math.isclose(s[field],r['distribution_summary'][field],rel_tol=1e-10,abs_tol=1e-9),(fit,field)
    assert math.isclose(s['mean'],r['prediction'],rel_tol=1e-10,abs_tol=1e-9)
    L=scoring.exact_decimal(q['line']);k=int(L.to_integral_value(rounding='ROUND_FLOOR'));fm1,fc,fp1=law.cdf(k-1),law.cdf(k),law.cdf(k+1);assert-1e-12<=fm1<=fc+1e-12 and fc<=fp1+1e-12 and fp1<=1+1e-12
    under=fm1 if L==k else fc;pp=dict(over=1-fc,under=under,push=fc-under if L==k else 0.);assert min(pp.values())>=-1e-12 and abs(sum(pp.values())-1)<1e-12;checks['probability_complement_and_monotonicity']+=1
    pp={side:max(0.,min(1.,v))for side,v in pp.items()};z=sum(pp.values());pp={side:v/z for side,v in pp.items()};side=None if abs(pp['over']-pp['under'])<=1e-12 else'over'if pp['over']>pp['under']else'under'
    if L%1==scoring.exact_decimal('.5')and side:
     assert side==('over'if s['lower_median']>L else'under');checks['median_probability_direction']+=1
    key=(r['procedure_id'],r['policy_id'],r['target']);oid=q['offer_id'];assert oid not in laws[key]
    laws[key][oid]=dict(original=r,probabilities=pp,side=side,law_parameters=params,fit_receipt=fit,saved_summary=r['distribution_summary'])
   proof.append(dict(fit_receipt=fit,fit_sha256=binding['fit_sha256'],model=binding['model'],training_membership_sha256=binding['training_membership_sha256'],lookup_rows=len(qq),max_summary_absolute_difference=maximum))
   del model;gc.collect()
 scores=[];proper=[];pairs=[];baselines=[];allrows=[];masks=[]
 for (proc,policy,target),ll in sorted(laws.items()):
  name='B::'+proc+'::'+policy+'::P2_EXACT_LINE_CDF-v1';pool=[];first=next(iter(ll.values()))['original']
  for oid,q in sorted(offers.items()):
   if q['category']!=target:continue
   b=ll.get(oid);pp=b['probabilities']if b else None;side=b['side']if b else None
   rr=dict(offer_id=oid,source_row_index=oid,game_id=q['game_id'],player_id=q['player_id'],target=target,season=2026,week=q['week'],position=q['position'],line=q['line'],prediction=None,raw_prediction=None,side=side,original_side=None,source_cohorts=[],actual=q['actual'],participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL'if q['appearance']=='PLAYED'else'UNKNOWN',outcome_state='final',fallback=b['original']['fallback']if b else None,probabilities=pp,method_key=name,decision_time=q['decision_UTC'],kickoff=q['kickoff_UTC'],evidence_tier=a.TIER,law_parameters=b['law_parameters']if b else None,fit_receipt=b['fit_receipt']if b else None,saved_summary=b['saved_summary']if b else None)
   rr=core.grade([rr],strategies=('original',))[0]
   if pp is None:rr['statistical_state']='UNAVAILABLE_FORECAST'
   pool.append(rr)
  allrows+=pool
  for wk in ['ALL','2','3']:
   rr=[r for r in pool if wk=='ALL'or r['week']==int(wk)];panel='B_C_PINNACLE_RETAINED_LEAF_LAWS_'+wk;meta=dict(history_regime=first['history_regime'],information_policy=first['information_policy'],product_id='actual_line_categorical_law',base_procedure_id=proc,decision_rule='P2',probability_conditioning='MODELED_APPEARANCE',bookmaker_nonvoid_conditioning='UNESTABLISHED');ss=a.score(rr,name,target,wk,meta,panel)
   for v in ss:v['strategy']='P2';v['selection_metrics']['probability_scores']=g.metrics([r for r in rr if r['selected_side']and(v['side']=='Combined'or r['selected_side']==v['side'])])
   scores+=ss;pm=g.metrics(rr);proper.append(dict(record_id='ABC-B-LEAF-PROB-'+hashlib.sha256(json.dumps([name,target,wk]).encode()).hexdigest()[:24],record_kind='prop_threshold_probability_evaluation',procedure_id=name,history_regime=first['history_regime'],product_id='actual_line_categorical_law',target=target,season=2026,week=wk,evaluation_seasons=[2026],evaluation_weeks=sorted({r['week']for r in rr}),evaluation_panel_id=panel,evidence='REPRODUCED_FROM_DATA',evidence_tier=a.TIER,forecast_rows=len(rr),admitted_forecast_rows=sum(r['probabilities']is not None for r in rr),probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',bookmaker_nonvoid_conditioning='UNESTABLISHED',**{k:pm[k]for k in ['n','brier','log_loss','infinite_log_losses','null_reason']}))
   mask={r['offer_id']for r in rr if r['probabilities']is not None and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'};masks.append(dict(procedure_id=name,target=target,week=wk,n=len(mask),safe_C_offer_ids=sorted(mask),sha256=digest_ids(mask)))
   for cid in ['NEUTRAL_HALFPOINT_50_50','EARLIER_PREVALENCE_V8','P2_LAW','P3_DIRECT']:
    cr=[]
    for r in rr:
     if r['offer_id']not in mask:continue
     if cid=='NEUTRAL_HALFPOINT_50_50':
      if scoring.exact_decimal(r['line'])%1!=scoring.exact_decimal('.5'):continue
      cp=dict(over=.5,under=.5,push=0.)
     else:
      q=byoffer[r['offer_id']].get(cid)
      if q is None or q.get('p_over')is None:continue
      cp={s:q['p_'+s]for s in ['over','under','push']}
     cr.append(dict(r,probabilities=cp))
    cm=g.metrics(cr);own=g.metrics([r for r in rr if r['offer_id']in {x['offer_id']for x in cr}]);baselines.append(dict(target=target,procedure_id=name,week_view=wk,control=cid,n=cm['n'],candidate_brier=own['brier'],control_brier=cm['brier'],brier_delta=own['brier']-cm['brier']if cm['n']else None))
   for cid in ['ALWAYS_OVER','ALWAYS_UNDER','EARLIER_PREVALENCE_V8','P3_DIRECT']:
    cr=[dict(r,statistical_state=r['status'],selected_side=r['selected_side'].lower()if r['selected_side']in ['OVER','UNDER']else None)for r in c if r['category']==target and r['method_id']==cid and(wk=='ALL'or r['week']==int(wk))];pairs.append(a.pair(rr,cr,target,name,cid,wk,panel))
 a.gzsave(private/'RETAINED_LEAF_C_LAW_ROWS.json.gz',dict(rows=allrows));file=private/'RETAINED_LEAF_C_LAW_ROWS.json.gz';assert file.stat().st_size<=p['budget']['max_private_bytes'];guard()
 a.save(out/'SCORES.json',scores+proper);a.save(out/'PROBABILITY_BASELINES.json',baselines);a.save(out/'PAIRED_CONTROLS.json',pairs);a.save(out/'OWNER_LOCAL_MASKS.json',masks);a.save(out/'MODEL_LAW_PARITY.json',dict(models=proof,checks=dict(checks),estimator_calls=0));a.save(out/'SIDE_TABLE.json',existing.wide(scores));existing.write_csv(out/'SIDE_TABLE.csv',existing.wide(scores));a.save(out/'PRIVATE_DERIVATIVE_MANIFEST.json',dict(safe_id='B_RETAINED_LEAF_C_LAW_ROWS',sha256=a.sha(file),bytes=file.stat().st_size,rows=len(allrows),offhost_restored=False))
 a.save(out/'RUN_RECEIPT.json',dict(state='COMPLETE_SAVED_HISTOGRAM_LAW_REPLAY_NOT_C_ADMITTED',law_cells=len(laws),actual_weeks=[2,3],side_views=len(scores),proper_views=len(proper),new_fits=0,new_model_inference=0,new_issued_forecasts=0,new_NFL_observations=0,source_offers=968,source_games=32,checks=dict(checks),private_derivative_bytes=file.stat().st_size,wall_seconds=time.monotonic()-start,max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,code_sha256=a.sha(__file__)))
 print(json.dumps(dict(law_cells=len(laws),side_views=len(scores),proper_views=len(proper),private_bytes=file.stat().st_size,wall_seconds=time.monotonic()-start)))
if __name__=='__main__':
 with threadpool_limits(limits=2):
  if sys.argv[1]=='prepare':prepare(Path(sys.argv[2]),Path(sys.argv[3]))
  else:run(*map(Path,sys.argv[2:6]))
