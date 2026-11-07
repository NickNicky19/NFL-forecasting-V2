"""New explanatory bucket/band views from immutable I rows; no forecast execution."""
import argparse,collections,csv,gzip,hashlib,importlib.util,json,math,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import right_wrong_diagnostic as diagnostic,scoring
from nfl_v2.shared_subgroups import canonical,sha,write,now

VERSION='v2-right-wrong-diagnostic-stage-a-v1'
def csvwrite(path,rows):
 if not rows:return
 fields=list(dict.fromkeys(k for row in rows for k in row))
 with Path(path).open('x',newline='')as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:json.dumps(v,sort_keys=True)if isinstance(v,(dict,list))else v for k,v in r.items()}for r in rows)
def recipe_key(row):return tuple(row['recipe'])
def row_key(row):return(int(row['week']),row['source_row_index'],row['game_id'],row['player_id'],row['target'])
def load_rows(path,root_protocol):
 packet=json.loads(gzip.decompress(path.read_bytes()));allowed={(t,*recipe)for t in root_protocol['stage_A']['targets']for recipe in root_protocol['stage_A']['recipes']}
 allowed|={(t,c,'ARCHIVED','saved_precision_point')for t in root_protocol['stage_A']['targets']for c in root_protocol['stage_A']['saved_controls']}
 groups={k:{}for k in allowed};duplicates=0
 for r in packet['rows']:
  if r.get('population_diagnostic')or recipe_key(r)not in allowed:continue
  key=recipe_key(r);qid=row_key(r)
  if qid in groups[key]:
   if groups[key][qid]!=r:raise ValueError('same identity retained with conflicting diagnostic context')
   duplicates+=1
  groups[key][qid]=r
 if any(not r for r in groups.values()):raise ValueError('root-frozen recipe missing retained rows')
 return groups,duplicates
def prepare(a):
 if a.output.exists()or a.private_output.exists():raise ValueError('fresh diagnostic identity required')
 rp=json.loads(a.root_protocol.read_bytes());groups,duplicates=load_rows(a.input,rp);a.output.mkdir(parents=True);a.private_output.mkdir(parents=True)
 lineage=a.root/'reports/right-and-wrong-diagnostic-20261031k/lineage/INSPECT_RETAINED_LINEAGE.py'
 p=dict(version=VERSION,state='FROZEN_BEFORE_STAGE_A_BUCKET_AND_BAND_METRICS',at=now(),root_protocol_path=a.root_protocol.relative_to(a.root).as_posix(),root_protocol_sha256=sha(a.root_protocol),source_artifact_id='I-RETAINED-POINT-DIAGNOSTIC-ROWS-V1',source_sha256=sha(a.input),source_bytes=a.input.stat().st_size,source_original_protocol_sha256=sha(a.root/'reports/point-prop-diagnostic-20261031i/point-offer/v1/FROZEN_PROTOCOL.json'),code_sha256=sha(__file__),core_sha256=sha(diagnostic.__file__),grader_sha256=sha(scoring.__file__),lineage_helper_path=lineage.relative_to(a.root).as_posix(),lineage_helper_sha256=sha(lineage),lineage_protocol_sha256=sha(lineage.parent/'FROZEN_LINEAGE_PROTOCOL.json'),realized_context_helper_sha256=sha(lineage.parent/'REALIZED_CONTEXT_LOOKUP.py'),realized_context_admission_sha256=sha(lineage.parent/'POSTGAME_CONTEXT_ADMISSION.json'),roster=[dict(recipe=list(k),outer_rows=len(rows),admitted_metadata_rows=sum(bool(r['admitted'])for r in rows.values()),preoutcome_membership_sha256=hashlib.sha256(canonical(sorted(row_key(r)for r in rows.values()))).hexdigest())for k,rows in sorted(groups.items())],deduplicated_equal_context_rows=duplicates,tolerances=rp['tolerances'],bands={'forecast_gap':rp['gap_bands'],'absolute_error':rp['error_bands']},source_point_rule='I point field is its alreadyverified ranking_point projection; raw/adjusted controls retain saved precision, not invented internaldigits.',rule='P1',sampling=rp['examples'],interpretation_fields=rp['interpretation_fields'],diagnostic_only=True,default_rank_eligible=False,membership='Outcome-conditioned explanatory groups; not selectablepregamecohorts',budget=rp['budget'])
 write(a.output/'FROZEN_PROTOCOL.json',p);(a.output/'EXECUTOR_SOURCE_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes());(a.output/'DIAGNOSTIC_CORE_SOURCE_SNAPSHOT.py').write_bytes(Path(diagnostic.__file__).read_bytes());print(json.dumps(dict(protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),recipes=len(groups),retained_rows=sum(len(x)for x in groups.values()))))
def run(a):
 p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes());rp=json.loads(a.root_protocol.read_bytes());started=time.monotonic();cpu=time.process_time()
 for path,expected in [(Path(__file__),p['code_sha256']),(Path(diagnostic.__file__),p['core_sha256']),(a.input,p['source_sha256']),(a.root_protocol,p['root_protocol_sha256']),(a.root/p['lineage_helper_path'],p['lineage_helper_sha256'])]:
  if sha(path)!=expected:raise ValueError('frozen input/helper changed')
 groups,duplicates=load_rows(a.input,rp);spec=importlib.util.spec_from_file_location('k_lineage',a.root/p['lineage_helper_path']);lineage=importlib.util.module_from_spec(spec);spec.loader.exec_module(lineage);lookup=lineage.load_focal_feature_metadata(a.private_root)
 realizedpath=(a.root/p['lineage_helper_path']).parent/'REALIZED_CONTEXT_LOOKUP.py'
 if sha(realizedpath)!=p['realized_context_helper_sha256']:raise ValueError('frozen realizedcontext helper changed')
 spec=importlib.util.spec_from_file_location('k_realized_context',realizedpath);realized=importlib.util.module_from_spec(spec);spec.loader.exec_module(realized);actual_context=realized.load_realized_context(a.private_root)
 scores=[];summaries=[];private_rows=[];examples=[];public_examples=[];unique_queries=set();unique_games=set();source_rows=0
 for recipe,dd in sorted(groups.items()):
  target,proc,arm,product=recipe;tolerance=p['tolerances'][target];rows=[]
  for _,r in sorted(dd.items()):
   meta,reason=lineage.feature_metadata_for(r,lookup);facts=dict(feature_lineage=meta,components=None,component_null_reason='DIRECT_MARGINAL_HAS_NO_EXPLICIT_COMPONENT_FORECASTS')
   if meta is not None:
    decision=diagnostic.clock(r['decision_time']).timestamp();available=meta.get('latest_consumed_feature_available');fit=diagnostic.clock(meta['fit_cutoff_utc']).timestamp()
    facts['source_age']=dict(prior_game_age_at_scheduled_kickoff_days=meta.get('lag1_game_age_at_target_kickoff_days'),decision_minus_assumed_feature_availability_days=(decision-available)/86400 if available is not None else None,decision_minus_nominal_fit_origin_days=(decision-fit)/86400,quote_update_age_days=None,quote_update_age_null_reason=meta['quote_age_status'],availability_evidence=meta['available_time_evidence'],age_reference='Features remainfrozen atknownscheduledtargetkickoff; ages not recomputed fromdecisionclock')
   row=diagnostic.diagnose(r,tolerance=tolerance,rule='P1',lineage=facts);row['source_feature_metadata_status']=reason or'EXACT_FOCAL_QUERY_HASH_JOIN';row['source_evidence_tier']='RETAINED_CURRENT_VINTAGE_FOOTBALL_RECONSTRUCTION_AND_SERVER_BOUND_THRESHOLD_METADATA'if arm!='ARCHIVED'else'SAVED_WEBSITE_POINT_AND_LINE_PRECISION; MODEL_INPUT_VINTAGE_UNVERIFIED';row['bookmaker_settlement']='UNRESOLVED_CONTRACT_PARALLEL_TO_STATISTICAL_GRADE'
   row['WHY_RULE_SELECTED_SIDE']='Point greaterthanline selectsOver; less selectsUnder; exactequality abstains. Savedcontrols use retainedprecision.'
   row['OBSERVED_ERROR_PATTERN']='NUMERIC_ERROR_SMALL_BUT_SELECTED_SIDE_WRONG'if row.get('close_wrong')else'LARGE_NUMERIC_ERROR_BUT_SELECTED_SIDE_CORRECT'if row.get('large_error_right')else'OTHER_RETAINED_ERROR_PATTERN'if row.get('bucket')else'OUTSIDE_DECIDED_BUCKETS'
   row['SUPPORTED_PREGAME_INFORMATION_POSSIBLY_MISSED']=None;row['supported_pregame_information_null_reason']='NOT_CAUSALLY_ESTABLISHED; retained actualinputs separately traced'
   context,context_reason=realized.context_for(r,actual_context);row['POSTGAME_DESCRIPTIVE_CONTEXT']=context;row['postgame_descriptive_context_null_reason']=context_reason;row['realized_context_use']='Observedpassingcomponents/ratiosonly; not predictedcomponents, predictors orcausalattribution'
   row['retained_numeric_tokens']={name:str(r.get(name))if r.get(name)is not None else None for name in ['point','line','actual']}
   row['CAUSE_OR_REMEDY_UNTESTED']='CAUSE_UNRESOLVED; no inversion,repair,calibration,routing orcausaltest'
   row['case_id']='K-CASE-'+hashlib.sha256(canonical([VERSION,recipe,row_key(r)])).hexdigest()[:24];rows.append(row);private_rows.append(row);unique_queries.add(row_key(r));unique_games.add(r['game_id']);source_rows+=1
  decided=[r for r in rows if r['bucket']];coverage=collections.Counter(r.get('diagnostic_exclusion_reason')or'DECIDED'for r in rows);buckets=collections.Counter(r['bucket']for r in decided);admitted=sum(bool(r['admitted'])for r in rows)
  for side in ['OVER','UNDER']:
   count=sum(r['selected_side']==side.lower()and r['admitted']for r in rows);wins=buckets[side+'_WIN'];loss=buckets[side+'_LOSS'];coverage[side+'_selected']=count
  summary=dict(target=target,procedure_id=proc,history_regime=arm,product_id=product,outer_opportunities=len(rows),admitted_forecasts=admitted,unavailable_forecasts=len(rows)-admitted,bucket_counts={b:buckets[b]for b in diagnostic.BUCKETS},outside_counts=dict(coverage),close_wrong=sum(bool(r.get('close_wrong'))for r in rows),large_error_right=sum(bool(r.get('large_error_right'))for r in rows),feature_metadata_rows=sum(r.get('feature_lineage')is not None for r in rows),component_status='NOT_APPLICABLE_DIRECT_MARGINAL_NO_COMPONENT_FORECAST',tolerance=tolerance,diagnostic_only=True,default_rank_eligible=False)
  if sum(buckets.values())!=len(decided):raise ValueError('fourbucket partition differs')
  summaries.append(summary)
  for item in diagnostic.aggregate(rows,tolerance=tolerance):
   rr=[r for r in rows if r['bucket']==item['bucket']and(item['dimension']=='BUCKET'or r[item['dimension'].lower()]==item['band'])];membership=hashlib.sha256(canonical(sorted(row_key(r)for r in rr))).hexdigest();n=len(rr);known=[r for r in rr if r.get('fallback')is not None];fallback=sum(r['fallback']!='none'for r in known);tolname=str(tolerance)
   score=dict(item,record_id='K-DIAG-'+hashlib.sha256(canonical([VERSION,recipe,item['bucket'],item['dimension'],item['band']])).hexdigest()[:24],record_kind='right_and_wrong_prediction_diagnostic',procedure_id=proc,history_regime=arm,product_id=product,target=target,season=2026,week='ALL',evaluation_seasons=[2026],evaluation_weeks=[5,6,7],evaluation_panel_id=VERSION,horizon_id='RETAINED_DECISION_ELIGIBLE_KNOWN_TARGET_TIME',decision_rule='P1',population='POST_OUTCOME_'+item['bucket']+':'+item['dimension']+':'+item['band'],forecast_rows=n,outer_opportunities=len(rows),source_admitted_forecasts=admitted,full_source_coverage=admitted/len(rows)if rows else None,diagnostic_subset_fraction=n/len(rows)if rows else None,fallback_rows=fallback if len(known)==n else None,fallback_rate=fallback/n if n and len(known)==n else None,fallback_scope='Withinthisoutcomeconditioneddiagnosticmask; archivedcontrolfallbackunknown',membership_sha256=membership,precision_counts={f'abs_le_{tolname}':dict(numerator=item['abs_le_t_numerator'],denominator=n,rate=item['abs_le_t']),f'abs_lt_{tolname}':dict(numerator=item['abs_lt_t_numerator'],denominator=n,rate=item['abs_lt_t'])},rmse=math.sqrt(item['mse'])if item['mse']is not None else None,diagnostic_only=True,default_rank_eligible=False,conditioning='SELECTED_SIDE_AND_REALIZED_OUTCOME',diagnostic_bucket=item['bucket'],diagnostic_dimension=item['dimension'],diagnostic_band=item['band'],cohort_id=item['bucket']+':'+item['dimension']+':'+item['band'],outcome_conditioned_membership=True,evidence='NEW_EXPLANATORY_VIEW_OF_PREVIOUSLY_EXPOSED_RETAINED_FORECASTS',source_vintage='RETAINED_SAVEDPOINT_PRECISION'if arm=='ARCHIVED'else'CURRENT_VINTAGE7DAY_FOOTBALL_RECONSTRUCTION;SERVER_BOUND_THRESHOLD_CONTEXT',source_artifact_sha256=p['source_sha256'],uncertainty=None,uncertainty_reason='POST_OUTCOME_DESCRIPTIVE_GROUP; THREE_EXPOSED_WEEKS_INSUFFICIENT_FOR_GENERALIZABLE_SKILL_OR_CAUSAL_INFERENCE')
   scores.append(score)
  for e in diagnostic.representatives(rows):
   case=e['row'];public=dict(recipe=list(recipe),selection=e['selection'],bucket=e['bucket'],case_id=case['case_id']if case else None,null_reason=e['null_reason'],source_derivative_sha256=p['source_sha256'],sampling='OUTCOME_CONDITIONED_EXPLANATORY; extremespurposive,notrepresentatives');public_examples.append(public);examples.append(dict(public,row=case))
  if time.monotonic()-started>300 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('bounded Kdiagnosticwave')
 payload=gzip.compress(canonical(dict(schema=VERSION,rows=private_rows,examples=examples)),mtime=0)
 if len(payload)>12582912:raise ValueError('Kprivate derivative budget')
 file=a.private_output/'RIGHT_WRONG_ROWS_AND_EXAMPLES.json.gz'
 with file.open('xb')as f:f.write(payload)
 write(a.output/'SCORES.json',scores);write(a.output/'BUCKET_AND_BAND_METRICS.json',scores);csvwrite(a.output/'BUCKET_AND_BAND_METRICS.csv',scores);write(a.output/'METHOD_BUCKET_SUMMARIES.json',summaries);csvwrite(a.output/'METHOD_BUCKET_SUMMARIES.csv',summaries);write(a.output/'PUBLIC_EXAMPLE_MANIFEST.json',public_examples)
 write(a.output/'RUN_RECEIPT.json',dict(state='COMPLETE_NEW_EXPLANATORY_BUCKET_AND_BAND_DIAGNOSTIC',at=now(),protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),source_derivative_sha256=p['source_sha256'],score_sha256=sha(a.output/'SCORES.json'),recipe_target_outputs=len(groups),retained_recipe_offer_rows=source_rows,unique_offer_query_keys=len(unique_queries),unique_games=len(unique_games),new_diagnostic_views=len(scores),private_artifact_id='K-STAGE-A-ROWS-EXAMPLES-V1',private_sha256=sha(file),private_bytes=len(payload),deduplicated_equal_context_rows=duplicates,new_fits=0,new_inference=0,new_forecasts=0,new_NFL_observations=0,new_grading_pipeline=False,original_grade_assertions='Sharedexactgrader validates retainedstatistics; no rewritten grades',diagnostic_only=True,default_rank_eligible=False,resources=dict(wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)))
 print(json.dumps(dict(recipe_target_outputs=len(groups),diagnostic_views=len(scores),private_bytes=len(payload),wall_seconds=time.monotonic()-started)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--root-protocol',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--private-output',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);a=p.parse_args();a.root_protocol=a.root_protocol.resolve();a.output=a.output.resolve();prepare(a)if a.action=='prepare'else run(a)
