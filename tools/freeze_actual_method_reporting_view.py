"""Freeze source selection, field semantics and leaf fallback lineage annotations."""
import argparse,collections,csv,gzip,hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as core
from nfl_v2.shared_subgroups import write,sha,now
from tools.numerical_championship import csvwrite
BASE=Path(__file__).resolve().parents[1]/'reports/completion-20261031g/roster'
PANELS={'F7':('w7-method-comparison-v2','fixed-w7-complete-leaf-law-v1','completion-20261031g-fixed-w7-complete-leaf-law-v1'),'W6':('w6-rolling-method-comparison-v1','w6-complete-leaf-law-v1','completion-20261031g-w6-complete-leaf-law-v1'),'W7':('w7-rolling-method-comparison-v1','w7-complete-leaf-law-v1','completion-20261031g-w7-complete-leaf-law-v1')}
def main(a):
 out=a.report;rules=[];annotations=[];decomp=[]
 for panel,(parent,leaf,private_member)in PANELS.items():
  par=BASE/parent;new=BASE/leaf;newproper=[r for r in json.loads((new/'SCORES.json').read_bytes())if r['record_kind']=='prop_threshold_probability_evaluation'];signatures={(r['target'],r['procedure_id'],r['history_regime'])for r in newproper};parents=[par/'SCORES.json']+[a.root/r['path']for r in json.loads((par/'SUPPLEMENTAL_SCORE_ARTIFACTS.json').read_bytes())];news=[new/'SCORES.json']+[a.root/r['path']for r in json.loads((new/'SUPPLEMENTAL_SCORE_ARTIFACTS.json').read_bytes())]
  rules.append(dict(panel=panel,parent_sources=[dict(path=p.relative_to(a.root).as_posix(),sha256=sha(p))for p in parents],complete_leaf_sources=[dict(path=p.relative_to(a.root).as_posix(),sha256=sha(p))for p in news],exclude_parent_only_when=dict(signature_fields=['target','procedure_id','history_regime'],matching_complete_leaf_signatures=[list(k)for k in sorted(signatures)],predicate="record_kind=='prop_threshold_probability_evaluation' OR (record_kind=='prop_selection_evaluation' AND decision_rule=='P2')",reason='Expandedcompleteleaflawcoverage supersedespartialfallbackonlyP2defaultview, not a forecastcorrection. Preserveoldpartial audit views. P1/GLM/otherprocedures unchanged.'),point_records_unchanged=True))
  priv=a.private_root/private_member;g=json.loads(gzip.decompress((priv/'GRADED_COMPLETE_LEAF_LAWS.json.gz').read_bytes()));f=json.loads(gzip.decompress((priv/'FROZEN_LAW_DIRECTIONS_K.json.gz').read_bytes()));loss={(r['method_id'],r['source_row_index']):r for r in g['proper_losses']};kmap={(r['method_id'],r['K'],r['scope']):r for r in f['Kplans']}
  for tag,rr in g['graded'].items():
   recipe=f['plans'][tag]['recipe']
   for view in('FULL_SYSTEM','LEARNED_LAW_ONLY','FALLBACK_LAW_ONLY'):
    chosen=[r for r in rr if r['admitted']and(view=='FULL_SYSTEM'or(r['source']=='REUSED_ELIGIBLE_FALLBACK_LAW')==(view=='FALLBACK_LAW_ONLY'))];ll=[loss[tag,r['source_row_index']]for r in chosen if(tag,r['source_row_index'])in loss];n=len(ll);inf=sum(r['log_loss']=='Infinity'for r in ll);decomp.append(dict(panel=panel,target=recipe[0],procedure_id=recipe[1],history_regime=recipe[2],view=view,admitted_law_rows=len(chosen),scored_law_rows=n,brier=math.fsum(r['brier']for r in ll)/n if n else None,log_loss='Infinity'if inf else math.fsum(r['log_loss']for r in ll)/n if n else None,infinite_log_losses=inf,partition_proof='Fullsystem=learned+fallback onidenticalsourceofferpopulation; exactlaworigin field, not inheritedparentfallbackmetadata',evidence='DERIVED_FROM_ALREADY_SCORED_RETAINED_LAW_ROWS'))
  for path in news:
   digest=sha(path)
   for index,r in enumerate(json.loads(path.read_bytes())):
    if r['record_kind']=='prop_threshold_probability_evaluation':
     tag=r['record_id'].removeprefix('LEAF-PROB-');pool=g['graded'][tag];chosen=[x for x in pool if x['admitted']]
    else:
     tag=r['method_id'];pool=g['graded'][tag]
     if r.get('K')is not None:
      ids=set(kmap[tag,r['K'],r['rank_scope']]['source_indices']);chosen=[x for x in pool if x['source_row_index']in ids]
     else:
      pool=[x for x in pool if core.in_cohort(x,r['cohort_id'])];chosen=[x for x in pool if x['selected_side']and(r['side']=='Combined'or x['selected_side']==r['side'])]
    fallback=sum(x['source']=='REUSED_ELIGIBLE_FALLBACK_LAW'for x in chosen if x['admitted']);annotations.append(dict(source_artifact=path.relative_to(a.root).as_posix(),source_artifact_sha256=digest,source_row_index=index,record_id=r['record_id'],law_coverage_version='COMPLETE_RETAINED_LEAF_AND_FALLBACK_V1',exact_law_origin_fallback_rows=fallback,exact_law_origin_learned_rows=sum(x['admitted']for x in chosen)-fallback,bookmaker_unresolved_contract_selected_rows=r['forecast_rows']if r['record_kind']=='prop_selection_evaluation'else None,origin_contract='Use explicitsource=REUSED_ELIGIBLE_FALLBACK_LAW vsRECOVERED_SAVED_LEAF_IDS_HISTOGRAM_NO_MODEL_INFERENCE. Inheritedprivateparentfallbackfield isnotusedforlawlineage.'))
 write(out/'CURRENT_ACTUAL_METHOD_SCORE_PROJECTION.json',dict(schema='v2-actual-method-score-default-coverage-view-v1',at=now(),source_rules=rules,all_originals_retained=True,scientific_procedure_count_unchanged=True,bookmaker_settlement='UNRESOLVED_CONTRACT_FOR_EVERY_SELECTED_CASE',interpretation='Same target/procedure/history but expanded lawcoverage getsdefaultP2view. Do not pool oldpartial+expandedviews or Ffixed+rollingW7 as independent observations.'))
 write(out/'COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS.json',annotations);write(out/'COMPLETE_LEAF_FALLBACK_DECOMPOSITION.json',decomp);csvwrite(out/'COMPLETE_LEAF_FALLBACK_DECOMPOSITION.csv',decomp)
 # Explicit statistical-versus-book settlement semantics in compact human table.
 src=out/'ALL_METHOD_PRIMARY_SIDE_TABLES.csv';dest=out/'ALL_METHOD_PRIMARY_SIDE_TABLES_V2.csv'
 with src.open()as f,dest.open('x',newline='')as w:
  reader=csv.DictReader(f);fields=reader.fieldnames+['grading_scope','bookmaker_settlement','Over_book_unresolved_contract','Under_book_unresolved_contract','Combined_book_unresolved_contract'];writer=csv.DictWriter(w,fieldnames=fields);writer.writeheader()
  for row in reader:
   row.update(grading_scope='STATISTICAL_THRESHOLD_CROSSING',bookmaker_settlement='UNRESOLVED_CONTRACT',Over_book_unresolved_contract=row['Over_selected'],Under_book_unresolved_contract=row['Under_selected'],Combined_book_unresolved_contract=row['Combined_selected']);writer.writerow(row)
 # Mark intended wholeperiod offer denominator even for partial lawproducts.
 universe={}
 with src.open()as f:
  for r in csv.DictReader(f):
   if r['panel']in('W6','W7'):universe[r['panel'],r['target']]=int(r['eligible_opportunities'])
 completeness=[]
 with gzip.open(out/'CUMULATIVE_W6_W7_METHOD_SIDE_TABLES.csv.gz','rt')as f:
  for index,r in enumerate(csv.DictReader(f)):
   weeks=json.loads(r['weeks_with_rows']);full=sum(universe[p,r['target']]for p in('W6','W7'));completeness.append(dict(cumulative_row_index=index,intended_weeks=[6,7],weeks_with_rows=weeks,intended_full_offer_universe=full,reported_supported_period_offer_universe=int(r['eligible_opportunities']),unrepresented_week_offer_rows=full-int(r['eligible_opportunities']),period_state='COMPLETE_TWO_WEEK_SOURCE_ROWS'if weeks==[6,7]else'PARTIAL_PROCEDURE_LAW_COVERAGE',admitted_forecast_coverage_of_intended_period=int(r['admitted_forecasts'])/full if full else None))
 write(out/'CUMULATIVE_COMPLETENESS_ANNOTATIONS.json',completeness);write(out/'FIELD_SEMANTICS.json',dict(hit_rates='Statistical crossings conditionalonqualifiedappearance; booksettlement remainsunresolvedforallselectedrecords.',unresolved_contract_fields='Original *_unresolved_contract fields describe statisticalgrading-statecounts, not establishedbookcontracts. *_book_unresolved_contract equalsselectedcount for allrows.',coverage='Selected+admittedruleabstention+unavailableforecast=fullopportunitypool; Knonselection additionallyincludeseligibleunpickedrankcandidates.',cumulative='Use CUMULATIVE_COMPLETENESS_ANNOTATIONS for intended W6+W7denominators; partiallawproducts mustnotpretend missingweeks unavailablecases disappeared. W1–5remainoutside these sourcepanels.',probabilities='MODELED_APPEARANCE; HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1; bookmaker_nonvoid_conditioning UNESTABLISHED'))
 p=out/'README.md';txt=p.read_text().replace('(ALL_METHOD_PRIMARY_SIDE_TABLES.csv)','(ALL_METHOD_PRIMARY_SIDE_TABLES_V2.csv)');txt+='\nThe [current source projection](CURRENT_ACTUAL_METHOD_SCORE_PROJECTION.json) defines exact complete-law replacements while retaining old partial views. [Law fallback decomposition](COMPLETE_LEAF_FALLBACK_DECOMPOSITION.csv) uses explicit recovered-versus-prior law origin. [Cumulative completeness annotations](CUMULATIVE_COMPLETENESS_ANNOTATIONS.json) preserve intended offer denominators for law recipes lacking a week. [Field semantics](FIELD_SEMANTICS.json) distinguish statistical unresolved states from unverified bookmaker settlement.\n';p.write_text(txt)
 write(out/'FINAL_REPORTING_VIEW_RECEIPT.json',dict(at=now(),code_sha256=sha(__file__),current_projection_sha256=sha(out/'CURRENT_ACTUAL_METHOD_SCORE_PROJECTION.json'),law_origin_annotations=len(annotations),law_fallback_views=len(decomp),cumulative_completeness_rows=len(completeness),new_scores=0,new_CDF_evaluations=0,new_model_inference=0,new_fits=0,original_canonical_score_bytes_changed=False));print(json.dumps(dict(law_origin_annotations=len(annotations),fallback_views=len(decomp),cumulative_completeness_rows=len(completeness))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--report',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);a=p.parse_args();a.report=a.report.resolve();main(a)
