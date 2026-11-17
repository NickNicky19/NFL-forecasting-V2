"""Source-bound index projection for W1--9 closure; never regrade or refit.

Run only after root approval and final independent receipts. Original aggregate
scores and record IDs remain immutable; the established index is append-only.
"""
import argparse,collections,csv,gzip,hashlib,io,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import build_test_index_v3 as index
from tools.check_analysis_index_coverage import read_bound
from nfl_v2.result_index import evaluation,validate_index
BASE=Path('reports/w1w9-comparison-closure-01/B')
SOURCES=[BASE/'native-completion-scoring/NATIVE_SCORES.json',BASE/'nine-week-completion/SCORES.json']
PAIRS=[BASE/'native-completion-scoring/PAIRED_NATIVE_COMPARISONS.json',BASE/'nine-week-completion/PAIRED_COMPARISONS.json']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')
def fresh(p,x):
 if Path(p).exists():raise FileExistsError(p)
 save(p,x)
def binding(p,body):
 data=gzip.compress(body,compresslevel=9,mtime=0);Path(p).write_bytes(data)
 return dict(path=str(Path(p).relative_to(ROOT)),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),compression='gzip',uncompressed_bytes=len(body),uncompressed_sha256=hashlib.sha256(body).hexdigest())
def history(proc):
 if 'strict-current-inputs'in proc:return 'H-CURRENT-STRICT_2026'
 if proc.startswith(('ALWAYS_','EARLIER_','ORIGINAL_','SAVED_')):return 'EXACT_RETAINED_CONTROL_CONTRACT'
 return 'H-RECENT_ORIGIN_RECIPE_BOUND'

def canonical(r):
 """Project declared combined counts; preserve both own sides in raw source."""
 group=lambda v:dict(v,wins=0 if v['decided']==0 and v['wins']is None else v['wins'],losses=0 if v['decided']==0 and v['losses']is None else v['losses'])
 c=group(r['COMBINED']);over=group(r['OVER']);under=group(r['UNDER']);n=c['wins']+c['losses'];assert n==c['decided']==r['decided'];assert over['wins']+under['wins']==c['wins'];assert over['losses']+under['losses']==c['losses']
 assert c['rate']==(c['wins']/n if n else None)
 for side in['OVER','UNDER']:
  v=group(r[side]);assert v['wins']+v['losses']==v['decided'];assert v['rate']==(v['wins']/v['decided']if v['decided']else None)
 weeks=r.get('actual_weeks',r.get('distinct_scored_weeks',r.get('weeks',[])));policy=r['policy'];product=policy
 if r.get('K')is not None:product+=':'+str(r.get('component_policy'))+':K'+str(r['K'])+':'+str(r.get('pool'))
 states=dict(r.get('states',{}));stats=dict(WIN=c['wins'],LOSS=c['losses'],wins=c['wins'],losses=c['losses'],status_counts=states,denominators=dict(outer_rows=r['eligible'],decided=n,selected=r['selected']),eligible_rank_pool_n=r['eligible'],selection_pool_count=r['eligible'],selected_opportunities=r['selected'],abstentions=r['abstentions'],technical_unavailable=r['unavailable'],admitted_forecast_opportunities=r['available'],unavailable_forecast_opportunities=r['unavailable'],admitted_rule_abstentions=r['abstentions'],fallback_issued=sum(v for k,v in r.get('fallback_states',{}).items()if k not in{'none','',None}),fallback_attribution='Blank source flags remain UNKNOWN, not learned-only.',bookmaker_settlement_status_counts={'UNRESOLVED_CONTRACT':r['selected']},selected_week_count=len(r.get('distinct_scored_weeks',weeks)),source_own_Over=r['OVER'],source_own_Under=r['UNDER'])
 if any(k in('',None,'None','null','UNKNOWN')or 'UNKNOWN'in str(k)for k in r.get('fallback_states',{})):stats['fallback_issued']=None
 if r['model_key']=='ORIGINAL_SOURCE_LEAN':stats.update(abstentions=None,admitted_rule_abstentions=None,mechanical_no_side_count=r['abstentions'],abstention_reporting_note='Unresolved whether missing original side is declared abstention or missing data; original counts unchanged.')
 # Zero states are introduced only where the complete source state census
 # explicitly accounts for every eligible row; otherwise leave them unknown.
 if sum(states.values())==r['eligible']:
  for state in['PUSH','VOID','PENDING','MISSING_ACTUAL','UNKNOWN_PARTICIPATION','UNRESOLVED_CONTRACT']:stats[state]=states.get(state,0)
 out=dict(record_id=r['record_id'],record_kind='prop_selection_evaluation',procedure_id=r['procedure_id'],product_id=product,strategy=policy,target=r.get('target',r.get('category')),side='Combined',season=r.get('season',2026),week=r.get('week_view','ALL'),evaluation_seasons=[r.get('season',2026)],evaluation_weeks=weeks,evaluation_panel_id=r['evaluation_panel_id'],history_regime=history(r['procedure_id']),population='FIXED_RETAINED_QB_ACTUAL_SOURCE_LINE_PANEL_NOT_EXANTE_ROSTER',position='QB',n=n,forecast_rows=r['eligible'],unique_games=r['games'],unique_player_games=r.get('player_games'),unique_weeks=len(weeks),registered_weeks=r.get('scheduled_week_domain',weeks),registered_week_count=len(r.get('scheduled_week_domain',weeks)),selection_metrics=stats,selection_loss_rate=c['losses']/n if n else None,mae=None,mse=None,bias=None,brier=None,log_loss=None,evidence=r['evidence_tier'],source_vintage=r.get('source_vintage'),selection_evidence='RETROSPECTIVE_RULE_REPLAY',horizon_id='KNOWN_TARGET_TIME_ROW_ADMISSION_RECONSTRUCTION'if ':known-target-time-v1'in r['procedure_id']else'KICKOFF_LEFT_LIMIT_CURRENT_VINTAGE_RECONSTRUCTION',threshold_provenance='RETAINED_REAL_PROVIDER_LABELLED_LINES;QUOTE_CLOCK_UNKNOWN;MAIN_ALTERNATE_UNCLASSIFIED',season_type='REG',statistic_period='full_game',overtime=True,K=r.get('K'),rank_scope='PER_CATEGORY_PER_WEEK_REGISTERED_DIAGNOSTIC_BATCHES'if r.get('K')else None,cohort_id=str(r.get('pool','Combined')),query_membership_sha256=r.get('membership_SHA256',r.get('membership_sha256')),uncertainty=r.get('uncertainty'),fallback_rows=stats['fallback_issued'],settlement_verified=False,primary_admission=r.get('primary_admission'))
 numeric=r.get('numerical')or{}
 if numeric.get('scored')==n and policy in{'P1_MEAN','P1_LOWER_MEDIAN'}:
  out.update(mae=numeric.get('MAE'),mse=numeric.get('MSE'),bias=numeric.get('bias'))
 # Probability tables retain their own complete events and score contracts
 # in the unchanged source. They are not borrowed as this selected-side law.
 return out

def projected_records(root,item,inputs):
 """Hook only registered source-bound projections; all old paths unchanged."""
 path=item.get('w1w9_index_projection')
 if path is None:
  yield from ORIGINAL_NEW_RECORDS(root,item,inputs);return
 raw=(root/item['artifact']).read_bytes();source=json.loads(raw);p=read(root/path);assert p['source_artifact_sha256']==hashlib.sha256(raw).hexdigest();assert len(p['rows'])==len(source)
 for i,(row,original)in enumerate(zip(p['rows'],source)):
  assert row['record_id']==original['record_id'];record=evaluation(row,item['artifact'],year_record={k:row[k]for k in['evaluation_seasons','evaluation_weeks']});record.update(source_artifact_sha256=p['source_artifact_sha256'],source_aggregate_fields=original,source_registry_kind=item['kind'],source_version_note=item['version_note'],source_bound_index_projection=dict(path=path,sha256=sha(root/path),source_row_index=i,no_regrading=True));validate_index([record]);yield record
 inputs.append(dict(source_artifact=item['artifact'],sha256=p['source_artifact_sha256'],rows=len(source),kind=item['kind']))
 inputs.append(dict(source_artifact=path,sha256=sha(root/path),rows=len(source),kind='SOURCE_BOUND_CANONICAL_INDEX_PROJECTION_NO_NEW_SCORES'))
ORIGINAL_NEW_RECORDS=index.new_records

def normalize_pairs():
 model={r['model_key']:r['procedure_id']for r in read(ROOT/SOURCES[0])};result=[]
 for path in PAIRS:
  body=(ROOT/path).read_bytes()
  for i,r in enumerate(json.loads(body)):
   union='left'in r
   if union and ('B-FTN-BALL-QUALITY-COMPLETION-v1:B1::'in r['left']or 'B-FTN-BALL-QUALITY-COMPLETION-v1:B1::'in r['right']):continue
   if union:
    split=lambda value:tuple(value.rsplit('::',1))if '::'in value else(value,'REGISTERED_DIRECTION')
    candidate,product=split(r['left']);control,control_product=split(r['right']);ce=(r['n']-r['candidate_wins'])/r['n']if r['n']else None;be=(r['n']-r['comparator_wins'])/r['n']if r['n']else None;delta=-r['accuracy_change'];metric='SELECTION_LOSS_RATE';mask=None;scope=r.get('sensitivity','ALL');interval=r.get('loss_difference_interval95')
   else:
    candidate=model.get(r['candidate'],r['candidate']);control=model.get(r['control'],r['control']);product=r['policy'];control_product=r.get('control_policy',product);ce=r.get('candidate_error');be=r.get('comparator_error');delta=r.get('delta');metric=r.get('metric','SELECTION_LOSS_RATE');mask=r.get('membership_SHA256');scope='NATIVE_W5_W9_COMMON_DECIDED';interval=r.get('week_interval')
   relative=delta/be if delta is not None and be not in(None,0)else None
   result.append(dict(r,procedure_id=candidate,comparator_procedure_id=control,product_id=product,comparator_product_id=control_product,target='pass_cmp',population='EXACT_SOURCE_BOUND_COMMON_DECIDED_QB_ACTUAL_LINES',season=2026,history_regime=history(candidate),comparator_history_regime=history(control),contrast=candidate+'_MINUS_'+control,metric=metric,n=r['n'],candidate_error=ce,comparator_error=be,delta=delta,relative_error_change=relative,membership_sha256=mask,week_interval=interval,week_interval_status=r.get('week_interval_status','SOURCE_REPORTED_WEEK_INTERVAL'if interval else'NOT_REPORTED'),cohort_id=scope,position='QB',policy_id=product,fallback_view='COMMON_DECIDED',history_limit='Current-vintage chronology, retained real lines and exposed development. Early private rows owner-local; aggregate parity is not private-row/source-clock/fit verification.',original_pair_source=str(path),original_pair_source_sha256=hashlib.sha256(body).hexdigest(),original_pair_row_index=i))
 return result

def append_analysis(pointer,normalized,*,relative=None,output_name='paired-analysis-index-v1'):
 old_binding=pointer['derived_comparison_manifest'];prior=json.loads(read_bound(old_binding));old=json.loads(read_bound(prior['records_json']));ar=ROOT/'registries/ANALYSIS_ARTIFACTS.json';registry=read(ar);assert registry==prior['inputs'];relative=relative or str(BASE/'INDEX_BOUND_PAIRED_ANALYSIS.json');fresh(ROOT/relative,normalized);digest=sha(ROOT/relative);new=[]
 for i,r in enumerate(normalized):
  z={k:None for k in old[0]};z.update(analysis_id='PAIR-'+hashlib.sha256(json.dumps([relative,i,r['procedure_id'],r['comparator_procedure_id'],r['product_id'],r['cohort_id']],separators=(',',':')).encode()).hexdigest()[:20],kind='DERIVED_PAIRED_LOSS_ANALYSIS',state='PAIRED_LOSS_SCORED'if r['n']else'NO_SUPPORTED_PAIRED_ROWS',procedure_id=r['procedure_id'],comparator_procedure_id=r['comparator_procedure_id'],product_id=r['product_id'],comparator_product_id=r['comparator_product_id'],target=r.get('target','pass_cmp'),population=r['population'],season=2026,history_regime=r['history_regime'],candidate_history_regime=r['history_regime'],comparator_history_regime=r['comparator_history_regime'],policy_id=r['policy_id'],contrast=r['contrast'],view=r['fallback_view'],cohort_id=r['cohort_id'],position='QB',metric=r['metric'],n=r['n'],candidate_error=r['candidate_error'],comparator_error=r['comparator_error'],absolute_error_change=r['delta'],relative_error_change=r['relative_error_change'],membership_sha256=r['membership_sha256'],week_clusters=r.get('week_clusters'),week_interval=r.get('week_interval'),week_interval_status=r.get('week_interval_status'),game_cluster_se=r.get('game_cluster_sensitivity_se'),history_status=r['history_limit'],precision_status='Own side denominators and exact source pair preserved; no new NFL observations.',source_artifact=relative,source_artifact_sha256=digest,source_row_index=i,new_fits=0,new_forecasts=0,new_NFL_observations=0);new.append(z)
 merged=old+new;assert len({r['analysis_id']for r in merged})==len(merged);dest=ROOT/BASE/output_name;dest.mkdir(exist_ok=False);rb=binding(dest/'PAIRED_ANALYSES.json.gz',(json.dumps(merged,separators=(',',':'),allow_nan=False)+'\n').encode());buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(merged[0]));writer.writeheader()
 for r in merged:writer.writerow({k:json.dumps(v,separators=(',',':'))if isinstance(v,(dict,list))else v for k,v in r.items()})
 cb=binding(dest/'PAIRED_ANALYSES.csv.gz',buffer.getvalue().encode());registry.append(dict(artifact=relative,sha256=digest,rows=len(new),state='DERIVED_PAIRED_ANALYSIS_SCORED_WITH_EMPTY_STATES_RETAINED',new_univariate_forecast_views=0));manifest=dict(prior,inputs=registry,record_count=len(merged),status_counts=dict(collections.Counter(r['state']for r in merged)),records_json=rb,records_csv=cb,previous_manifest=old_binding,old_records_preserved=len(old),new_records=len(new));mp=dest/'ANALYSIS_MANIFEST.json';save(mp,manifest);save(ar,registry);pointer['derived_comparison_manifest']=dict(path=str(mp.relative_to(ROOT)),sha256=sha(mp));return len(new),len(old)

def supplemental_attempts(a):
 """Append only the newly scored retained ATT control; preserve first build."""
 source=BASE/'receipt-union/native-attempts/SCORES.json';pairs=BASE/'receipt-union/native-attempts/PAIRED_V1.json'
 if a.verification is None:raise ValueError('Exact independent ATT verification receipt required before registration')
 verification=read(a.verification if a.verification.is_absolute()else ROOT/a.verification);state=verification.get('state',verification.get('status',''));assert 'PASS'in state,state
 raw=read(ROOT/source);assert len(raw)==63 and all(r.get('target',r.get('category'))=='pass_att'for r in raw);assert len({r['record_id']for r in raw})==63;projected=[canonical(r)for r in raw]
 for row in projected:validate_index([evaluation(row,str(source),year_record={k:row[k]for k in['evaluation_seasons','evaluation_weeks']})])
 model={r['model_key']:r['procedure_id']for r in raw};pairrows=read(ROOT/pairs);assert len(pairrows)==15;normalized=[]
 for i,r in enumerate(pairrows):
  product=r['left'];candidate=model['COMMON_EXPOSURE'];control=model[r['right']];be=r['comparator_error'];delta=r['delta'];normalized.append(dict(r,procedure_id=candidate,comparator_procedure_id=control,product_id=product,comparator_product_id=r['right'],target='pass_att',population='EXACT_SOURCE_BOUND_COMMON_DECIDED_QB_ATTEMPT_LINES',season=2026,history_regime=history(candidate),comparator_history_regime=history(control),contrast=candidate+'_MINUS_'+control,metric='SELECTION_LOSS_RATE',n=r['n'],candidate_error=r['candidate_error'],comparator_error=be,delta=delta,relative_error_change=delta/be if be not in(None,0)else None,membership_sha256=r.get('membership_sha256'),week_interval=r.get('week_interval'),week_interval_status=r.get('week_interval_status'),cohort_id='NATIVE_W5_W9_ATT_COMMON_DECIDED',position='QB',policy_id=product,fallback_view='COMMON_DECIDED',history_limit='Fixed retained COMMON_EXPOSURE attempt recipe; current-vintage chronological real-source-line diagnostic, not original issuance or a nine-week union. No inherited completion coverage.',original_pair_source=str(pairs),original_pair_source_sha256=sha(ROOT/pairs),original_pair_row_index=i))
 ptr=ROOT/'registries/CURRENT_RESULTS_INDEX.json';pointer=read(ptr);previous=pointer['manifest'];reg=ROOT/'registries/RESULT_ARTIFACTS.json';registry=read(reg);assert not any(r['artifact']==str(source)for r in registry);export=ROOT/'reports/abc-championship/EXPORT_INDEX.json';export_bytes=export.read_bytes();projection=BASE/'native-attempts_INDEX_PROJECTION_V1.json';fresh(ROOT/projection,dict(source_artifact=str(source),source_artifact_sha256=sha(ROOT/source),source_rows=63,transformation='Source-bound ATT field projection; original own-side counts/metrics remain unchanged, no grading or fitting',rows=projected));registry.append(dict(artifact=str(source),state='SCORED',kind='SAVED_COMMON_EXPOSURE_ATTEMPT_NATIVE_ACTUAL_LINE_DIAGNOSTIC',w1w9_index_projection=str(projection),version_note='Exact retained COMMON_EXPOSURE mean/median/law/P90 plus same-case controls;142real-source-labelled W5-9 lines,141DK+1Sleeper. Quoteclock/main-altunverified; no W1-9union, no original issuance or C/production admission.'));save(reg,registry);index.new_records=projected_records;out=str(BASE/'results-index-v2');result=index.write(previous=previous,output=out,reuse_prior_csv=True,compressed_delivery=True);pointer['previous_checkpoint']=previous;pointer['manifest']=out+'/INDEX_MANIFEST.json';new,old=append_analysis(pointer,normalized,relative=str(BASE/'ATT_INDEX_BOUND_PAIRED_ANALYSIS_V1.json'),output_name='paired-analysis-index-v2');pointer['w1w9_comparison_closure_20261114']['native_attempts_supplement']=dict(scores=str(source),source_views=63,paired_analyses=15,target='pass_att',status='FIVE_NATIVE_DIAGNOSTIC_WEEKS_ONLY_NOT_NINE_WEEK_UNION',verification=str(a.verification));save(ptr,pointer);assert export.read_bytes()==export_bytes;receipt=dict(state='APPENDED_ATT_SUPPLEMENT_PRESERVING_PREVIOUS_CMP_RECORDS',source_artifact=str(source),source_sha256=sha(ROOT/source),new_source_score_views=63,new_pairs=new,old_pairs_preserved=old,prior_result_manifest=previous,current_result_manifest=pointer['manifest'],original_completion_source_views_preserved=798,original_completion_analysis_views_preserved=155,export_index_unchanged=True,new_scoring=0,new_fits=0,new_HTTP=0,index=result);fresh(ROOT/BASE/'ATT_REGISTRATION_RECEIPT_V1.json',receipt);print(json.dumps(receipt))

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--supplement-attempts',action='store_true');ap.add_argument('--verification',type=Path);ap.add_argument('--report',default=str(BASE/'README.md'));a=ap.parse_args()
 if not a.execute:raise SystemExit('Prepared helper only. Root approval and --execute required; no registry/index writes performed.')
 if a.supplement_attempts:return supplemental_attempts(a)
 ptr=ROOT/'registries/CURRENT_RESULTS_INDEX.json';pointer=read(ptr);previous=pointer['manifest'];reg=ROOT/'registries/RESULT_ARTIFACTS.json';registry=read(reg);export=ROOT/'reports/abc-championship/EXPORT_INDEX.json';export_bytes=export.read_bytes();assert(ROOT/a.report).exists()
 prepared=[]
 for path,expected in zip(SOURCES,[636,162]):
  raw=read(ROOT/path);assert len(raw)==expected and not any(r.get('model_key')=='B1'for r in raw);assert len({r['record_id']for r in raw})==len(raw);rows=[canonical(r)for r in raw]
  for row in rows:validate_index([evaluation(row,str(path),year_record={k:row[k]for k in['evaluation_seasons','evaluation_weeks']})])
  if any(r['artifact']==str(path)for r in registry):raise ValueError('Already registered; preserve state and do not duplicate')
  projection=BASE/(path.parent.name+'_INDEX_PROJECTION_V1.json');prepared.append((path,projection,dict(source_artifact=str(path),source_artifact_sha256=sha(ROOT/path),source_rows=len(raw),transformation='Source-bound field projection only; original own-side counts and nested metric scopes retained, no grading/fitting',rows=rows)))
 normalized=normalize_pairs();assert len(normalized)==155
 # All compatibility validation above precedes the first canonical mutation.
 for path,projection,payload in prepared:
  fresh(ROOT/projection,payload);registry.append(dict(artifact=str(path),state='SCORED',kind='FROZEN_EXISTING_PROCEDURE_ACTUAL_LINE_RETROSPECTIVE_COMPARISON',w1w9_index_projection=str(projection),version_note='NativeW5-9five represented weeks or exact226rowW1-9multi-source diagnostic; partialboards, quoteclock/main-altunknown, exposed development. Own means/medians/laws/selectors and known-time exclusions separately typed. No original issuance, C admission or production change.'))
 save(reg,registry);index.new_records=projected_records;out=str(BASE/'results-index-v1');result=index.write(previous=previous,output=out,reuse_prior_csv=True,compressed_delivery=True);pointer['previous_checkpoint']=previous;pointer['manifest']=out+'/INDEX_MANIFEST.json';pointer['readable_checkpoint']=a.report;pointer['w1w9_comparison_closure_20261114']=dict(report=a.report,protocol=str(BASE/'ADOPTED_SCOPE_AND_BUDGET_V1.json'),frozen_roster=str(BASE/'roster/FROZEN_B_CONTRIBUTION_ROSTER_V1.json'),native_scores=str(SOURCES[0]),nine_week_scores=str(SOURCES[1]),scope='Frozen B contribution; native142 plus exact early84 comparable modern union, not all-category A/B/C champion. Known-target-time exclusions separate; no production activation or new 90% claim.',new_source_score_views=798,new_common_C_admission=False,new_production_release=False)
 new,old=append_analysis(pointer,normalized);save(ptr,pointer);assert export.read_bytes()==export_bytes
 receipt=dict(state='APPENDED_SOURCE_BOUND_SCORES_AND_PAIRED_ANALYSES',score_artifacts=[dict(path=str(p),sha256=sha(ROOT/p),rows=len(read(ROOT/p)))for p in SOURCES],new_source_score_views=798,new_pairs=new,old_pairs_preserved=old,prior_result_manifest=previous,current_result_manifest=pointer['manifest'],old_export_index_sha256=hashlib.sha256(export_bytes).hexdigest(),export_index_unchanged=True,new_fits=0,new_scoring=0,new_NFL_observations=0,index=result);fresh(ROOT/BASE/'REGISTRATION_RECEIPT_V1.json',receipt);print(json.dumps(receipt))
if __name__=='__main__':main()
