"""Source-bound coverage/probability annotations and missing matched-control K."""
import argparse,collections,gzip,hashlib,json,math,sys,time,resource
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as core,scoring
from nfl_v2.shared_subgroups import canonical,sha,now,write
from tools.numerical_championship import csvwrite

def main(a):
 out=a.output;priv=a.private;start=time.monotonic();files=[out/'SCORES.json']+[a.root/r['path']for r in json.loads((out/'SUPPLEMENTAL_SCORE_ARTIFACTS.json').read_bytes())]
 target=out/'metadata-and-control-k-v1'
 if target.exists():raise ValueError('fresh missing-only projection required')
 target.mkdir();bind=[dict(path=p.relative_to(a.root).as_posix(),sha256=sha(p))for p in files];write(target/'FROZEN_PROTOCOL.json',dict(at=now(),code_sha256=sha(__file__),source_scores=bind,source_grade_sha256=sha(priv/'GRADED_METHOD_ROWS.json.gz'),source_plans_sha256=sha(priv/'FROZEN_SELECTIONS_AND_K.json.gz'),purpose='Annotationonly: disjointcoverage and genuineP2probability fields fromalreadyretainedvectors/losses; missingmatchedcontrolK fromretainedgradedstates, nonewgrading/inference.',K='Per category/controlmask,K6/10/20,Combined/Over/Under; fixed13gamepartialweekasofOct23sourceclock. Rankabsretainedpoint-linegap,stablesourceidx; sourceeligibility/side frozenbeforeaggregation.',new_fits=0,new_inference=0,new_direction_grades=0,max_wall_seconds=180,max_RSS_bytes=1073741824))
 f=json.loads(gzip.decompress((priv/'FROZEN_SELECTIONS_AND_K.json.gz').read_bytes()));g=json.loads(gzip.decompress((priv/'GRADED_METHOD_ROWS.json.gz').read_bytes()));graded=g['graded'];pr={(r['method_id'],r['source_row_index']):r for r in g['probability_rows']};kp={(r['method_id'],r['K'],r['rank_scope']):r for r in f['Kplans']};annotations=[];denoms=[];pointann=[];cache={}
 for path,binding in zip(files,bind):
  for index,s in enumerate(json.loads(path.read_bytes())):
   tag=s.get('method_id')
   if s['record_kind']=='forecast_evaluation_view':
    tag=s['record_id'].removeprefix('METHOD-NUM-');rr=[r for r in graded[tag]if r['admitted']and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'];counts={}
    for tol in(1,5,10):
     for inclusive in(False,True):
      name=f"abs_{'le'if inclusive else'lt'}_{tol}";num=sum(abs(r['ranking_point']-r['actual'])<=tol if inclusive else abs(r['ranking_point']-r['actual'])<tol for r in rr);counts[name]=dict(numerator=num,denominator=len(rr),rate=num/len(rr)if rr else None)
    counts['exact_rate']=dict(numerator=sum(r['ranking_point']==r['actual']for r in rr),denominator=len(rr),rate=sum(r['ranking_point']==r['actual']for r in rr)/len(rr)if rr else None);pointann.append(dict(source_artifact=binding['path'],source_artifact_sha256=binding['sha256'],source_row_index=index,record_id=s['record_id'],precision_counts=counts));continue
   if s['record_kind']!='prop_selection_evaluation':continue
   cohort=s['cohort_id'];key=(tag,cohort,s.get('K'),s.get('rank_scope'))
   if key not in cache:
    full=graded[tag]
    if s.get('K')is not None:
     wanted=set(kp[tag,s['K'],s['rank_scope']]['source_indices']);pool=full;selected=[r for r in full if r['source_row_index']in wanted]
    else:pool=[r for r in full if core.in_cohort(r,cohort)];selected=[r for r in pool if r['selected_side']]
    cache[key]=(pool,selected)
   pool,chosen=cache[key];denoms.append(dict(source_artifact=binding['path'],source_artifact_sha256=binding['sha256'],source_row_index=index,record_id=s['record_id'],eligible_pool=len(pool),admitted_forecast_opportunities=sum(r['admitted']for r in pool),unavailable_forecast_opportunities=sum(not r['admitted']for r in pool),admitted_rule_abstentions=sum(r['admitted']and r['selected_side']is None for r in pool),selected_any_side_in_full_pool=sum(r['selected_side']is not None for r in pool),partition_check=len(pool)==sum(not r['admitted']for r in pool)+sum(r['admitted']and r['selected_side']is None for r in pool)+sum(r['selected_side']is not None for r in pool),original_abstention_field_semantics='Originalgenericabstentions includesunavailableforecasts; usedisjointannotationfields. Knonselection separatelyincludesunselectedrankedcandidates.'))
   if s['decision_rule']!='P2':continue
   rr=[r for r in chosen if s['side']=='Combined'or r['selected_side']==s['side']];pairs=[pr[tag,r['source_row_index']]for r in rr if(tag,r['source_row_index'])in pr];bs=[r['half3class_brier']for r in pairs];logs=[r['categorical_log_loss']for r in pairs];inf=sum(x=='Infinity'for x in logs);annotations.append(dict(source_artifact=binding['path'],source_artifact_sha256=binding['sha256'],source_row_index=index,record_id=s['record_id'],probability_scores=dict(status='AVAILABLE_FROM_RETAINED_QUALIFIED_LAW_VECTORS',brier=math.fsum(bs)/len(bs)if bs else None,log_loss='Infinity'if inf else math.fsum(logs)/len(logs)if logs else None,n=len(bs),infinite_log_losses=inf,conditioning='MODELED_APPEARANCE',bookmaker_nonvoid_conditioning='UNESTABLISHED',score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',null_reason=None if bs else'NO_QUALIFIED_LAW_AND_ACTUAL_ROWS_IN_THIS_SELECTED_SUBGROUP',proper_all_law_record_id='METHOD-PROB-'+tag,correction='ReplacesgenericNO_QUALIFIED_LINE_PROBABILITYmetadataonly; originalforecasts/directions/grades unchanged.')))
 if a.metadata_only:
  write(target/'SELECTION_PROBABILITY_ANNOTATIONS.json',annotations);write(target/'SELECTION_DENOMINATOR_ANNOTATIONS.json',denoms);write(target/'POINT_PRECISION_ANNOTATIONS.json',pointann);write(target/'RUN_RECEIPT.json',dict(state='COMPLETE_SOURCE_BOUND_METADATA_ONLY_PROJECTION',at=now(),probability_annotations=len(annotations),denominator_annotations=len(denoms),point_precision_annotations=len(pointann),new_fits=0,new_inference=0,new_direction_grades=0,new_CDF_evaluations=0,wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024));print(json.dumps(dict(probability_annotations=len(annotations),denominator_annotations=len(denoms),point_precision_annotations=len(pointann),metadata_only=True)));return
 # Freeze missing control K using saved point/side/eligibility only; retain actual grades unchanged.
 newK=[]
 for tag,cp in f['controls'].items():
  rr=graded[tag]
  for scope in('Combined','over','under'):
   pool=[r for r in rr if r['admitted']and r['selected_side']and r['ranking_point']is not None and(scope=='Combined'or r['selected_side']==scope)];ordered=sorted(pool,key=core.rank_key)
   for K in(6,10,20):newK.append(dict(method_id=tag,K=K,rank_scope=scope,eligible_pool_n=len(pool),source_indices=[r['source_row_index']for r in ordered[:K]]))
 frozen=gzip.compress(canonical(dict(rows=newK)),mtime=0)
 with(priv/'MATCHED_CONTROL_K_METADATA_FREEZE.json.gz').open('xb')as h:h.write(frozen)
 write(target/'CONTROL_K_FREEZE_RECEIPT.json',dict(at=now(),lists=len(newK),before_new_aggregate=True,source_sha256=sha(priv/'MATCHED_CONTROL_K_METADATA_FREEZE.json.gz'),no_new_direction_or_outcome_grades=True))
 scores=[]
 for k in newK:
  tag=k['method_id'];pool=graded[tag];wanted=set(k['source_indices']);chosen=[r for r in pool if r['source_row_index']in wanted];targetname=f['controls'][tag]['target'];views=[]
  for side in('over','under','Combined'):
   rr=[r for r in chosen if side=='Combined'or r['selected_side']==side];s=core.score_row(rr,pool,strategy=tag,target=targetname,cohort='MATCHED_CONTROL_FIXED_PARTIAL_WEEK_TOP_PICK_SUBSET',side=side,K=k['K'],rank_scope=k['rank_scope'],rank_eligible=k['eligible_pool_n']);s.update(record_id='CONTROL-K-'+hashlib.sha256(canonical([tag,k['K'],k['rank_scope'],side])).hexdigest()[:24],procedure_id='MATCHED_RETAINED_CONTROL:'+f['controls'][tag]['control'],history_regime='ARCHIVED',product_id='saved_precision_control',decision_rule='CONTROL',method_id=tag,evaluation_panel_id='v2-admitted-methods-W7-controlK-completion-v1',time_panel_id='2026_W7_ADMITTED_METHOD_RECONSTRUCTION_462_13_GAMES',selection_evidence='RETROSPECTIVE_RULE_REPLAY');s['selection_metrics'].update(admitted_rule_abstentions=sum(r['admitted']and r['selected_side']is None for r in pool),unavailable_forecast_opportunities=sum(not r['admitted']for r in pool));scores.append(s);views.append(s)
  core.check_triplet(views)
 write(target/'SCORES.json',scores);write(target/'SELECTION_PROBABILITY_ANNOTATIONS.json',annotations);write(target/'SELECTION_DENOMINATOR_ANNOTATIONS.json',denoms);write(target/'POINT_PRECISION_ANNOTATIONS.json',pointann);csvwrite(target/'PROBABILITY_ANNOTATIONS.csv',annotations);write(target/'RUN_RECEIPT.json',dict(state='COMPLETE_SOURCE_BOUND_METADATA_AND_MISSING_CONTROL_K_PROJECTION',at=now(),probability_annotations=len(annotations),denominator_annotations=len(denoms),point_precision_annotations=len(pointann),controlK_lists=len(newK),controlK_score_views=len(scores),score_sha256=sha(target/'SCORES.json'),new_fits=0,new_inference=0,new_direction_grades=0,new_CDF_evaluations=0,wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024));print(json.dumps(dict(probability_annotations=len(annotations),denominator_annotations=len(denoms),point_precision_annotations=len(pointann),controlK_score_views=len(scores))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);p.add_argument('--private',type=Path,required=True);p.add_argument('--metadata-only',action='store_true');a=p.parse_args();a.output=a.output.resolve();main(a)
