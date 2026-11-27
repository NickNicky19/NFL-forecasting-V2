"""Finite saved-row extension using the existing B threshold and bound-C adapter."""
import collections,csv,gzip,json,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import abc_b_c_bound_replay as adapter
from nfl_v2 import full_provider_prop_replay as shared
from tools import grade_saved_week8 as existing
def main(private,snapshot,evidence):
 start=time.monotonic();out=ROOT/'reports/abc-championship/continuation-20261103-v3';out.mkdir(exist_ok=False)
 adapter.OUT=out
 protocol=dict(id='B-C-BOUND-OWNER-LOCAL-SAVED-POINT-EXTENSION-v1',at_utc=datetime.now(timezone.utc).isoformat(),C_ref=adapter.CREF,C_protocol_sha256=adapter.sha(snapshot/'reports/abc-championship/PROTOCOL-v2-C-1.json'),
  source_choice='All existing W2/3 qualified categories in empirical, original HGB objectives, regularized GLM, C02 and applicable count-ablation saved chunks; previous ordered/D1/D2 retained unchanged.',
  scope='Additional zero-refit P1 only; no probability inferred from points. Full source board with technical unavailable distinct from equality abstention. No original September issuance claim.',
  known_exposure='C outcomes, B W2/3 D1/D2 and prior point results already inspected; this is a complete existing-procedure saved-row replay, not untouched confirmation.',
  history='Each exact existing policy retained; CURRENT fitting with older feature memory is distinct from strict-current information; empirical arm-limited target history remains separate.',
  budget=dict(new_fits=0,new_inference=0,wall_seconds=180,max_private_derived_bytes=8388608,threads=1),
  unchanged_core='nfl_v2.full_provider_prop_replay.grade and score_row; C canonical scores/admission unchanged; source analysis/aggregate rights inherited pinned C review.',
  required_future='Missing law products, other method snapshots and historical offers remain queued separately; no unconditional all-method completion claim.')
 adapter.save(out/'FROZEN_PACKAGE.json',protocol)
 c,_=adapter.c_rows(snapshot);byoffer=collections.defaultdict(dict)
 for r in c:byoffer[r['offer_id']][r['method_id']]=r
 offers={k:v['P2_LAW']for k,v in byoffer.items()};targets={'pass_yd','rush_yd','rec','rec_yd'};candidates=collections.defaultdict(dict);bindings=[]
 def put(r):
  if r['target']not in targets or int(r['season'])!=2026 or int(r['week'])not in [2,3]or r['population']!='primary':return
  r=dict(r,season=2026,week=int(r['week']))
  assert r['latest_feature_available']is None or r['latest_feature_available']<r['cutoff']
  name='B::'+r['procedure_id']+'::'+r['policy_id']+'::'+r['product_id'];k=(r['game_id'],r['player_id'],r['target']);old=candidates[name,r['target']].get(k)
  if old:assert old==r,'DUPLICATE_FORECAST_CONFLICT'
  candidates[name,r['target']][k]=r
 specs=[('distribution-wave-v2','GLM'),('ordered-information-ablation-v1','C02'),('hgb-history-v1','HGB'),('count-ablation-wave-v1','COUNT')]
 for folder,kind in specs:
  for p in sorted((evidence/folder/'prediction-chunks').glob('W0[23]-*.json.gz')):
   j=adapter.load(p)
   if not j['rows']or j['rows'][0]['target']not in targets:continue
   if kind=='GLM'and j['rows'][0].get('family')!='regularized_glm_law':continue
   bindings.append(dict(safe_member_id=folder+'/'+p.name,sha256=adapter.sha(p),bytes=p.stat().st_size))
   for raw in j['rows']:
    r=dict(raw)
    if kind=='HGB':r.update(procedure_id=r['run_id']+':'+r['objective'],policy_id=r['history_regime']+'-COMMON',product_id=r['objective'],information_policy='COMMON_2022_FEATURE_MEMORY')
    put(r)
 p=evidence/'empirical-history-diagnostic-v1/predictions.csv.gz';bindings.append(dict(safe_member_id='empirical-history-diagnostic-v1/predictions.csv.gz',sha256=adapter.sha(p),bytes=p.stat().st_size))
 with gzip.open(p,'rt')as f:
  for raw in csv.DictReader(f):
   if raw['season']!='2026'or raw['week']not in ['2','3']or raw['target']not in targets or raw['population']!='primary':continue
   r=dict(raw,procedure_id='empirical-player-history-control-v1',policy_id=raw['history_regime']+'-EMPIRICAL',product_id=raw['product'],information_policy='ARM_LIMITED_TARGET_HISTORY',
    prediction=float(raw['prediction'])if raw['prediction']else None,actual=float(raw['actual'])if raw['actual']else None,cutoff=float(raw['cutoff_epoch_utc']),
    latest_feature_available=float(raw['latest_training_available_epoch_utc'])if raw['latest_training_available_epoch_utc']else None,fit_slot=None)
   put(r)
 scores=[];pairs=[];allrows=[];scope=[];conflicts=[]
 for (name,target),lookup in sorted(candidates.items()):
  first=next(iter(lookup.values()));pool=[]
  for oid,q in sorted(offers.items()):
   if q['category']!=target:continue
   b=lookup.get((q['game_id'],q['player_id'],target));reason=None
   if b:
    assert b['cutoff']==adapter.instant(q['decision_UTC'])==adapter.instant(q['kickoff_UTC'])
    assert b['position']==q['position']
    if q['actual']is not None and b['actual']is not None and q['actual']!=b['actual']:conflicts.append(dict(offer_id=oid,procedure_id=name));reason='OUTCOME_VERSION_MISMATCH'
   point=b['prediction']if b and reason is None else None
   r=dict(offer_id=oid,source_row_index=oid,game_id=q['game_id'],player_id=q['player_id'],target=target,season=2026,week=q['week'],position=q['position'],line=q['line'],line_from='pinnacle',prediction=point,raw_prediction=None,side=None,original_side=None,source_cohorts=[],actual=q['actual'],participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL'if q['appearance']=='PLAYED'else'UNKNOWN',outcome_state='final',fallback=b['fallback']if b else None,missing_reason=reason or('MISSING_RETAINED_FORECAST_POPULATION'if not b else'FORECAST_OUTPUT_UNAVAILABLE'if point is None else None),decision_time=q['decision_UTC'],kickoff=q['kickoff_UTC'],method_key=name,evidence_tier=adapter.TIER,forecast_cutoff=b['cutoff']if b else None,latest_feature_available=b['latest_feature_available']if b else None,source_chunk_slot=b.get('fit_slot')if b else None)
   g=shared.grade([r],strategies=(shared.ADJUSTED,))[0]
   if point is None:g['statistical_state']='UNAVAILABLE_FORECAST'
   pool.append(g)
  allrows+=pool;meta=dict(history_regime=first['history_regime'],information_policy=first['information_policy'],product_id=first['product_id'],base_procedure_id=first['procedure_id'],window_contract='NOT_APPLICABLE_NO_D1_D2_DEFENSE_WINDOW',information_group='EXISTING_SAVED_PROCEDURE')
  for wk in ['ALL','2','3']:
   rr=[r for r in pool if wk=='ALL'or r['week']==int(wk)];panel='B_OWNER_LOCAL_C_PINNACLE_W2_W3_'+wk
   scores+=adapter.score(rr,name,target,wk,meta,panel)
   for cid in ['ALWAYS_OVER','ALWAYS_UNDER','EARLIER_PREVALENCE_V8','P1_MEDIAN','P1_MEAN','P2_LAW','P3_DIRECT']:
    ctrl=[dict(r,statistical_state=r['status'],selected_side=r['selected_side'].lower()if r['selected_side']in ['OVER','UNDER']else None)for r in c if r['category']==target and r['method_id']==cid and(wk=='ALL'or r['week']==int(wk))]
    pairs.append(adapter.pair(rr,ctrl,target,name,cid,wk,panel))
  for k,rr in [('LEARNED_ONLY',[r for r in pool if r['fallback']=='none']),('FALLBACK_ONLY',[r for r in pool if r['fallback']not in ['none',None]]),('UNAVAILABLE',[r for r in pool if r['statistical_state']=='UNAVAILABLE_FORECAST'])]:scope.append(dict(procedure_id=name,target=target,scope=k,issued=len(rr),decided=sum(r['statistical_state']in ['WIN','LOSS']for r in rr),wins=sum(r['statistical_state']=='WIN'for r in rr)))
 assert not conflicts,('OUTCOME_MISMATCH',len(conflicts))
 adapter.save(out/'SCORES.json',scores);adapter.save(out/'PAIRED_CONTROLS.json',pairs);adapter.save(out/'LEARNED_FALLBACK_SCOPE.json',scope);adapter.save(out/'INPUT_BINDINGS.json',bindings)
 adapter.gzsave(private/'B_OWNER_LOCAL_C_ADDITIONAL_ROWS_V3.json.gz',dict(rows=allrows));p=private/'B_OWNER_LOCAL_C_ADDITIONAL_ROWS_V3.json.gz';assert p.stat().st_size<protocol['budget']['max_private_derived_bytes']
 adapter.save(out/'PRIVATE_DERIVATIVE_MANIFEST.json',dict(safe_id='B_OWNER_LOCAL_C_ADDITIONAL_ROWS_V3',sha256=adapter.sha(p),bytes=p.stat().st_size,rows=len(allrows),offhost_restored=False,rights='OWNER_LOCAL_B_RESTRICTED_ANALYSIS;PUBLIC_AGGREGATES_ONLY'))
 adapter.save(out/'SIDE_TABLE.json',existing.wide(scores));existing.write_csv(out/'SIDE_TABLE.csv',existing.wide(scores))
 adapter.save(out/'RUN_RECEIPT.json',dict(state='EXECUTED_OWNER_LOCAL_NOT_C_ADMITTED',new_fits=0,new_inference=0,new_forecasts=0,actual_weeks=[2,3],code_sha256=adapter.sha(__file__),adapter_sha256=adapter.sha(Path(adapter.__file__)),protocol_sha256=adapter.sha(out/'FROZEN_PACKAGE.json'),source_offers=968,source_games=32,procedure_category_product_cells=len(candidates),procedure_product_configurations=len({k[0]for k in candidates}),score_views=len(scores),method_rows=len(allrows),new_unique_source_offers=0,private_derived_bytes=p.stat().st_size,wall_seconds=time.monotonic()-start))
 print(json.dumps(dict(cells=len(candidates),views=len(scores),rows=len(allrows),seconds=time.monotonic()-start)))
if __name__=='__main__':main(*map(Path,sys.argv[1:4]))
