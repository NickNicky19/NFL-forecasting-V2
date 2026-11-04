"""B owner-local replay against C's pinned opportunities; no competing scorer.

Uses B's existing threshold engine. Independent C arithmetic is verification,
not a replacement canonical benchmark. Restricted B rows never leave private root.
"""
import collections,csv,gzip,hashlib,json,sys,time
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import full_provider_prop_replay as shared
from nfl_v2.paired_uncertainty import paired_losses
from tools import grade_saved_week8 as existing
OUT=ROOT/'reports/abc-championship/continuation-20261103-v2'
PREVIOUS=ROOT/'reports/abc-championship/continuation-20261103-v1'
TARGETS=tuple(shared.TARGETS)+('anytime_td','nick-chart-ppr-v1')
CREF='ac9cb1000bcb8f1197505b68ccfe246ea61bbafe'
TIER='TIMING_UNVERIFIED_ACTUAL_LINE_DIAGNOSTIC'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 p=Path(p);return json.loads(gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes())
def save(p,j):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x')as f:json.dump(j,f,indent=2,allow_nan=False);f.write('\n')
def gzsave(p,j):
 with Path(p).open('xb')as f:f.write(gzip.compress(json.dumps(j,separators=(',',':'),allow_nan=False).encode(),mtime=0))
def instant(s):return datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def pid(r):return 'C::'+r['method_version']+'::'+r['method_id']+'::'+r['selector_id']
def c_rows(snapshot):
 """Separate calculation path: correction chain, first deterministic snapshot."""
 binding=load(snapshot/'reports/abc-championship/C_INPUT_BINDINGS.json');versions={};receipts=[]
 for d in binding['datasets']:
  p=snapshot/d['path'];assert sha(p)==d['SHA256'];j=load(p);receipts.append(d)
  for r in j['rows']:
   old=versions.get(r['record_id'])
   if old and old!=r:
    assert r['supersedes_grade_id']==old['grade_id']
    for k in ['offer_id','line','selected_side','decision_UTC','point','p_over','p_under','p_push']:
     assert r.get(k)==old.get(k),(k,'CORRECTION_CHANGED_DECISION')
   versions[r['record_id']]=r
 first={}
 fields=['category','game_id','player_id','method_id','method_version','selector_id','policy_id','venue','product','line_tier','evidence_tier']
 for r in versions.values():
  key=tuple(r[k]for k in fields);order=(instant(r['decision_UTC']),r['scoring_snapshot_id'])
  if key not in first or order<first[key][0]:first[key]=(order,r)
 rows=[r for _,r in first.values()if r['venue']=='pinnacle'and r['season']==2026 and r['week']<=8]
 for r in rows:
  if r['status']in ['WIN','LOSS','PUSH']:
   y,l=Decimal(str(r['actual'])),Decimal(str(r['line']));s=r['selected_side']
   state='PUSH'if y==l else'WIN'if((y>l)==(s=='OVER'))else'LOSS'
   assert state==r['status']
 return rows,receipts
def independent_c(snapshot,rows):
 expected=load(snapshot/'reports/abc-championship/SCORES-v2-C-1.json');checks=[]
 for s in expected:
  rr=[r for r in rows if r['category']==s['category']and pid(r)==s['procedure_id']and(s['week_view']=='ALL'or r['week']==int(s['week_view']))]
  assert len(rr)==s['eligible']
  for side in ['OVER','UNDER','COMBINED']:
   sub=[r for r in rr if r['selected_side']in(['OVER','UNDER','YES']if side=='COMBINED'else[side])]
   w=sum(r['status']=='WIN'for r in sub);l=sum(r['status']=='LOSS'for r in sub);v=s[side]
   assert (len(sub),w+l)==(v['selected'],v['decided'])
   assert (w if w+l else None)==v['wins']and(l if w+l else None)==v['losses']
   assert (w/(w+l)if w+l else None)==v['rate']
  checks.append(dict(category=s['category'],procedure_id=s['procedure_id'],week_view=s['week_view'],eligible=len(rr),state='INDEPENDENT_ARITHMETIC_MATCH'))
 save(OUT/'C_INDEPENDENT_ARITHMETIC.json',dict(protocol_ref=CREF,score_sha256=sha(snapshot/'reports/abc-championship/SCORES-v2-C-1.json'),checks=checks,score_views=len(checks),new_C_fits=0,scope='B separate Decimal calculation and correction/snapshot selection; not independent full NFL source re-inference or C admission'))
 return expected
def score(rr,procedure,target,weekview,meta,scope):
 views=[];weeks=sorted({r['week']for r in rr});selected=[r for r in rr if r.get('selected_side')]
 for side in ['over','under','Combined']:
  sub=[r for r in selected if side=='Combined'or r['selected_side']==side]
  s=shared.score_row(sub,rr,strategy='P1'if procedure.startswith('B::')else procedure,target=target,cohort='ALL',side=side)
  key=[scope,procedure,target,weekview,side]
  s.update(record_id='ABC-B-C-'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:24],procedure_id=procedure,
   evaluation_panel_id=scope,time_panel_id='E1_'+weekview,period_id='E1',season=2026,week=int(weekview)if weekview!='ALL'else'ALL',
   evaluation_seasons=[2026],evaluation_weeks=weeks,requested_weeks=list(range(1,9)),horizon_id='KICKOFF_RECONSTRUCTION_VS_LAST_RECORDED_PREKICK_CLOSE',
   evidence='REPRODUCED_FROM_DATA',selection_evidence='RETROSPECTIVE_RULE_REPLAY',evidence_tier=TIER,
   source_vintage='B_CURRENT_REVISED_7DAY_RECONSTRUCTION;C_LAST_RECORDED_QUOTE_TIMING_UNVERIFIED;C_PINNED_CORRECTED_LABELS',
   whole_week_complete=False,shared_benchmark_status='B_OWNER_LOCAL_C_PROTOCOL_PINNED_NOT_C_ADMITTED',**meta)
  technical=sum(r['statistical_state']=='UNAVAILABLE_FORECAST'for r in rr);abstain=sum(r['statistical_state']=='ABSTAIN'for r in rr)
  s['selection_metrics'].update(technical_unavailable=technical,admitted_rule_abstentions=abstain,abstentions_outside_selected_partition=abstain,
    fallback_issued=sum(r.get('fallback')not in ['none',False,None,'NOT_RETAINED']for r in rr),fallback_status_unknown=sum(r.get('fallback')=='NOT_RETAINED'for r in rr))
  num=[r for r in sub if r.get('prediction')is not None and r['actual']is not None and r['statistical_state']in ['WIN','LOSS','PUSH']]
  s['mae']=sum(abs(r['prediction']-r['actual'])for r in num)/len(num)if num else None
  s['bias']=sum(r['prediction']-r['actual']for r in num)/len(num)if num else None
  s['numerical_n']=len(num);s['numerical_panel']='Same decided offered rows of this side; not broad participant MAE'
  views.append(s)
 shared.check_triplet(views)
 return views
def pair(candidate,control,target,procedure,control_id,weekview,scope):
 a={r['offer_id']:r for r in candidate};b={r['offer_id']:r for r in control};keys=sorted(a.keys()&b.keys())
 rr=[(a[k],b[k])for k in keys if a[k]['statistical_state']in ['WIN','LOSS']and b[k]['statistical_state']in ['WIN','LOSS']]
 aa=[x['statistical_state']=='LOSS'for x,y in rr];bb=[y['statistical_state']=='LOSS'for x,y in rr]
 return dict(target=target,procedure_id=procedure,control_id=control_id,week_view=weekview,scope=scope,common_decided=len(rr),
  candidate_wins=sum(not x for x in aa),control_wins=sum(not x for x in bb),win_difference=sum(bb)-sum(aa),
  disagreements=sum(x['selected_side']!=y['selected_side']for x,y in rr),
  uncertainty=paired_losses(aa,bb,[x['week']for x,y in rr],[x['game_id']for x,y in rr]))
def main(private,snapshot,chunks):
 start=time.monotonic();OUT.mkdir(parents=True,exist_ok=True);assert not(OUT/'FROZEN_PACKAGE.json').exists();private.mkdir(parents=True,exist_ok=True)
 protocol=dict(id='B-C-BOUND-OWNER-LOCAL-ZERO-REFIT-W2-W3-v1',registered_at_utc=datetime.now(timezone.utc).isoformat(),
  C_ref=CREF,C_protocol_id='ABC-ACTUAL-PROP-CHAMPIONSHIP-v2-C-1',C_protocol_sha256=sha(snapshot/'reports/abc-championship/PROTOCOL-v2-C-1.json'),
  purpose='Extend B method time coverage on existing C full Pinnacle board; owner-local B evidence remains private; C alone admits shared results.',
  choice_before_new_scores='All four qualified C categories; Weeks2/3; all existing B D1/D2 and retained ordered controls; all four registered policy arms and both saved point products. Chosen for source/chunk availability, not hit rate.',
  targets=['pass_yd','rush_yd','rec','rec_yd'],rules='Unrounded retained P1 point >line OVER,<line UNDER, equality abstain. Missing B row/point is technical unavailable, never confidence abstention. C correction chain and first snapshot, primary Pinnacle frozen by C.',
  comparison='Full C eligible board, own complete coverage; pairwise common decided masks against C own methods/strong controls; no sparse candidate global intersection.',
  history='CURRENT/RECENT/MULTI common2022 memory and strict-current CURRENT retain source contracts. D1/D2 four-observed-position-group windows; NOT scheduled-team-game alternative.',
  time='B historical query cutoff equals C kickoff reconstruction decision; latest feature strictly earlier. Revised seven-day availability policy is not authenticated as-of source history. C quote clock/executability remains unverified.',
  controls='C P1/P2/P3/earlierprevalence and always sides; B embedded unchanged ordered-CDF controls. No fitted calibration, inversion, offset or learned selector.',
  original_W8_diagnostic='Same original-selected415decided mask; alwaysUnder diagnostic is constant control, not newlivepolicy; missing12 remain in full427 selected pool.',
  budget=dict(new_fits=0,new_inference=0,max_private_derived_bytes=8388608,max_source_snapshot_bytes=67108864,max_public_bytes=16777216,max_wall_seconds=180,threads=1),
  retention='Source C public licensed minimum evidence stays pinned upstream; B restricted chunks original governed retention; bounded reconstructable private derivatives local readback only, no new offhost claim; large-fit gate unchanged.',
  release='No production modification, capture or C admission implied; all years previously exposed research.')
 save(OUT/'FROZEN_PACKAGE.json',protocol)
 c,receipts=c_rows(snapshot)
 assert(PREVIOUS/'C_INDEPENDENT_ARITHMETIC.json').exists()
 save(OUT/'RESUMPTION.json',dict(previous='reports/abc-championship/continuation-20261103-v1',reason='v1 completed passing-yard and original-selected control calculations, then category aggregation failed because target was absent from the internal lookup key. Predictions and completed PY/control calculations unchanged; reuse them, execute remaining three categories only.',preserved=True))
 byoffer=collections.defaultdict(dict)
 for r in c:
  assert r['method_id']not in byoffer[r['offer_id']];byoffer[r['offer_id']][r['method_id']]=r
 offers={k:v['P2_LAW']for k,v in byoffer.items()};assert len(offers)==968
 candidates=collections.defaultdict(dict);bindings=[]
 for p in sorted(chunks.glob('W0[23]-*.json.gz')):
  j=load(p)
  if not j['rows']or j['rows'][0]['target']not in protocol['targets']:continue
  bindings.append(dict(member_id=p.name,sha256=sha(p),bytes=p.stat().st_size,rows=len(j['rows'])))
  for r in j['rows']:
   if r['population']!='primary':continue
   assert r['latest_feature_available']is None or r['latest_feature_available']<r['cutoff']
   for kind in ['candidate','ordered_control']:
    proc=r['procedure_id']if kind=='candidate'else r['control_procedure_id'];name='B::'+proc+'::'+r['policy_id']+'::'+r['product_id']
    key=(r['game_id'],r['player_id'],r['target']);value=dict(r)
    if kind=='ordered_control':value.update(prediction=r['control_prediction'],fallback=r['control_fallback'],procedure_id=proc)
    old=candidates[name,r['target']].get(key)
    if old:assert all(old[k]==value[k]for k in ['prediction','fallback','cutoff','actual','position']),('CONTROL_DUPLICATE_CONFLICT',name)
    candidates[name,r['target']][key]=value
 scores=load(PREVIOUS/'SCORES.json');paired=load(PREVIOUS/'PAIRED_CONTROLS.json');allgraded=load(private/'B_OWNER_LOCAL_C_MATCHED_ROWS.json.gz')['rows'];mismatches=[];cohorts=load(PREVIOUS/'LEARNED_FALLBACK_SCOPE.json');counts=collections.Counter(r['missing_reason']or'SUPPORTED'for r in allgraded)
 assert {r['target']for r in scores}=={'pass_yd'}
 for (name,category),lookup in sorted(candidates.items()):
  if category=='pass_yd':continue
  first=next(iter(lookup.values()));target=first['target'];pool=[]
  for oid,q in sorted(offers.items()):
   if q['category']!=target:continue
   b=lookup.get((q['game_id'],q['player_id'],target));reason=None
   if b:
    assert b['cutoff']==instant(q['decision_UTC'])==instant(q['kickoff_UTC'])
    if b['position']!=q['position']:reason='ROLE_CONTRACT_MISMATCH'
    if q['actual']is not None and b['actual']is not None and q['actual']!=b['actual']:
     mismatches.append(dict(offer_id=oid,procedure_id=name,kind='OUTCOME_DIFFERENCE'));reason='OUTCOME_VERSION_MISMATCH'
   point=b['prediction']if b and reason is None else None
   r=dict(offer_id=oid,source_row_index=oid,game_id=q['game_id'],player_id=q['player_id'],target=target,season=2026,week=q['week'],position=q['position'],
    line=q['line'],line_from='pinnacle',prediction=point,raw_prediction=None,side=None,original_side=None,source_cohorts=[],actual=q['actual'],
    participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL'if q['appearance']=='PLAYED'else'UNKNOWN',outcome_state='final',fallback=b['fallback']if b else None,
    missing_reason=reason or('MISSING_RETAINED_FORECAST_POPULATION'if not b else'FORECAST_OUTPUT_UNAVAILABLE'if point is None else None),
    decision_time=q['decision_UTC'],kickoff=q['kickoff_UTC'],method_key=name,evidence_tier=TIER,forecast_cutoff=b['cutoff']if b else None,
    latest_feature_available=b['latest_feature_available']if b else None,source_chunk_slot=b['fit_slot']if b else None)
   g=shared.grade([r],strategies=(shared.ADJUSTED,))[0]
   if point is None:g['statistical_state']='UNAVAILABLE_FORECAST'
   pool.append(g);counts[g['missing_reason']or'SUPPORTED']+=1
  allgraded.extend(pool)
  meta=dict(history_regime=first['history_regime'],information_policy=first['information_policy'],product_id=first['product_id'],
   base_procedure_id=first['procedure_id'],window_contract='FOUR_OBSERVED_POSITION_GROUP_GAMES',information_group=first.get('information_group')if'qualified-position-defense'in first['procedure_id']else'RETAINED_ORDERED_CONTROL')
  for wk in ['ALL','2','3']:
   rr=[r for r in pool if wk=='ALL'or r['week']==int(wk)];scope='B_OWNER_LOCAL_C_PINNACLE_W2_W3_'+wk
   scores.extend(score(rr,name,target,wk,meta,scope))
   for cid in ['ALWAYS_OVER','ALWAYS_UNDER','EARLIER_PREVALENCE_V8','P1_MEDIAN','P1_MEAN','P2_LAW','P3_DIRECT']:
    controls=[dict(r,statistical_state=r['status'],selected_side=r['selected_side'].lower()if r['selected_side']in ['OVER','UNDER']else None)for r in c if r['category']==target and r['method_id']==cid and(wk=='ALL'or r['week']==int(wk))]
    paired.append(pair(rr,controls,target,name,cid,wk,scope))
  for kind,subset in [('LEARNED_ONLY',[r for r in pool if r['fallback']=='none']),('FALLBACK_ONLY',[r for r in pool if r['fallback']not in ['none',None]]),('UNAVAILABLE',[r for r in pool if r['statistical_state']=='UNAVAILABLE_FORECAST'])]:
   cohorts.append(dict(procedure_id=name,target=target,scope=kind,issued=len(subset),decided=sum(r['statistical_state']in ['WIN','LOSS']for r in subset),wins=sum(r['statistical_state']=='WIN'for r in subset)))
 assert not mismatches,('OUTCOME_JOIN_MISMATCH',len(mismatches))
 save(OUT/'SCORES.json',scores);save(OUT/'PAIRED_CONTROLS.json',paired);save(OUT/'LEARNED_FALLBACK_SCOPE.json',cohorts)
 save(OUT/'B_INPUT_MEMBER_BINDINGS.json',dict(source_protocol='reports/continuation-20261030c/qualified-defense-information-v1/FROZEN_PROTOCOL.json',source_protocol_sha256=sha(ROOT/'reports/continuation-20261030c/qualified-defense-information-v1/FROZEN_PROTOCOL.json'),members=bindings,private_rows_not_public=True))
 gzsave(private/'B_OWNER_LOCAL_C_MATCHED_ROWS_V2.json.gz',dict(rows=allgraded));save(OUT/'PRIVATE_DERIVATIVE_MANIFEST.json',dict(safe_id='B_OWNER_LOCAL_C_MATCHED_ROWS_V2',sha256=sha(private/'B_OWNER_LOCAL_C_MATCHED_ROWS_V2.json.gz'),bytes=(private/'B_OWNER_LOCAL_C_MATCHED_ROWS_V2.json.gz').stat().st_size,rows=len(allgraded),offhost_restored=False,route='EXISTING_APPROVED_OWNER_LOCAL_ANALYSIS_ONLY;NO_PRIVATE_LOCATOR'))
 # Preserve the completed original-selected control; this continuation does not repeat it.
 total=load(PREVIOUS/'original-selected-under-control-v1/PAIRED_CONTROLS.json')[-1]
 wide=existing.wide(scores);save(OUT/'SIDE_TABLE.json',wide);existing.write_csv(OUT/'SIDE_TABLE.csv',wide)
 leaders=[]
 for target in protocol['targets']:
  rr=[r for r in scores if r['target']==target and r['week']=='ALL'and r['side']=='Combined'];best=max(r['selection_metrics']['hit_rate']for r in rr if r['n']);win=[r for r in rr if r['selection_metrics']['hit_rate']==best]
  leaders.append(dict(target=target,leaders=[r['procedure_id']for r in win],wins=win[0]['selection_metrics']['WIN'],decided=win[0]['n'],rate=best,raw_maximum_scope='OWN_POOL_NOT_AUTOMATIC_MATCHED_CHAMPION',side_maxima={side:[dict(procedure_id=r['procedure_id'],wins=r['selection_metrics']['WIN'],n=r['n'],rate=r['selection_metrics']['hit_rate'])for r in scores if r['target']==target and r['week']=='ALL'and r['side']==side and r['n']and r['selection_metrics']['hit_rate']==max(x['selection_metrics']['hit_rate']for x in scores if x['target']==target and x['week']=='ALL'and x['side']==side and x['n'])]for side in ['over','under']}))
 save(OUT/'LEADERS.json',leaders)
 assert (private/'B_OWNER_LOCAL_C_MATCHED_ROWS_V2.json.gz').stat().st_size<protocol['budget']['max_private_derived_bytes']
 save(OUT/'RUN_RECEIPT.json',dict(state='EXECUTED_B_OWNER_LOCAL_C_BOUND_NOT_C_ADMITTED',at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=sha(OUT/'FROZEN_PACKAGE.json'),code_sha256=sha(__file__),C_ref=CREF,
  new_fits=0,new_inference=0,new_forecasts=0,actual_weeks=[2,3],source_offers=len(offers),source_games=len({r['game_id']for r in offers.values()}),unique_player_games=len({(r['game_id'],r['player_id'])for r in offers.values()}),B_procedure_product_configurations=len({name for name,target in candidates}),procedure_category_product_cells=len(candidates),score_views=len(scores),matched_method_rows=len(allgraded),input_chunks=len(bindings),missing_counts=dict(counts),outcome_conflicts=0,wall_seconds=time.monotonic()-start,original_W8_control=total))
 print(json.dumps(dict(leaders=leaders,rows=len(allgraded),score_views=len(scores),runtime=time.monotonic()-start)))
if __name__=='__main__':main(*map(Path,sys.argv[1:4]))
