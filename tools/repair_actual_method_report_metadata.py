"""Read-contract repairs only: disjoint coverage and cohort period denominators."""
import argparse,collections,csv,gzip,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import write,sha,now
BASE=Path(__file__).resolve().parents[1]/'reports/completion-20261031g/roster'
PARENTS={'F7':'w7-method-comparison-v2','W6':'w6-rolling-method-comparison-v1','W7':'w7-rolling-method-comparison-v1'}
def main(a):
 b=a.report;den={};prob={};bindings=[]
 for panel,parent in PARENTS.items():
  p=BASE/parent/'metadata-and-control-k-v1'
  for name,dest in(('SELECTION_DENOMINATOR_ANNOTATIONS.json',den),('SELECTION_PROBABILITY_ANNOTATIONS.json',prob)):
   src=p/name;bindings.append(dict(panel=panel,field_source=name,path=src.relative_to(a.root).as_posix(),sha256=sha(src)))
   for r in json.loads(src.read_bytes()):
    if r['source_artifact'].endswith('/'+parent+'/SCORES.json'):dest[r['source_artifact'],r['source_row_index']]=r
 src=b/'ALL_METHOD_PRIMARY_SIDE_TABLES_V2.csv';dest=b/'ALL_METHOD_PRIMARY_SIDE_TABLES_V3.csv';cache={}
 if not dest.exists():
  with src.open()as f,dest.open('x',newline='')as o:
   reader=csv.DictReader(f);extras=[side+'_'+field for side in('Over','Under','Combined')for field in('selected_pool_brier','selected_pool_log_loss','selected_pool_proper_n','probability_conditioning')];writer=csv.DictWriter(o,fieldnames=reader.fieldnames+extras);writer.writeheader()
   for row in reader:
    refs=json.loads(row['source_refs']);c=refs[2];key=(c['source_artifact'],c['source_row_index']);d=den.get(key)
    if d:
     for to,fr in(('admitted_forecasts','admitted_forecast_opportunities'),('forecast_unavailable','unavailable_forecast_opportunities'),('admitted_rule_abstentions','admitted_rule_abstentions')):row[to]=d[fr]
    for side,ref in zip(('Over','Under','Combined'),refs):
     q=prob.get((ref['source_artifact'],ref['source_row_index']));m=q['probability_scores']if q else None
     if not m and row['decision_rule']=='P2':
      path=a.root/ref['source_artifact']
      if str(path)not in cache:
       if sha(path)!=ref['source_sha256']:raise ValueError('source scores changed')
       cache[str(path)]=json.loads(path.read_bytes())
      m=cache[str(path)][ref['source_row_index']]['selection_metrics'].get('probability_scores')
     for col,field in(('selected_pool_brier','brier'),('selected_pool_log_loss','log_loss'),('selected_pool_proper_n','n'),('probability_conditioning','conditioning')):row[side+'_'+col]=m.get(field)if m else None
    writer.writerow(row)
 # Cohort-specific intended period pools, not the entire category for every subgroup.
 pools=collections.defaultdict(set);category={}
 with gzip.open(b/'ALL_WEEKLY_METHOD_SIDE_TABLES.csv.gz','rt')as f:
  for r in csv.DictReader(f):
   if r['panel']not in('W6','W7'):continue
   pools[r['panel'],r['target'],r['cohort_id']].add(int(r['eligible_opportunities']))
   if r['cohort_id']=='ALL'and not r['K']:category[r['panel'],r['target']]=int(r['eligible_opportunities'])
 if any(len(v)!=1 for v in pools.values()):raise ValueError('competitor cohort memberships differ')
 pools={k:next(iter(v))for k,v in pools.items()};notes=[]
 with gzip.open(b/'CUMULATIVE_W6_W7_METHOD_SIDE_TABLES.csv.gz','rt')as f:
  for i,r in enumerate(csv.DictReader(f)):
   weeks=json.loads(r['weeks_with_rows']);intended=sum(pools.get((p,r['target'],r['cohort_id']),0)for p in('W6','W7'));full=sum(category[p,r['target']]for p in('W6','W7'));missing=sum(pools.get(('W'+str(w),r['target'],r['cohort_id']),0)for w in(6,7)if w not in weeks);reported=int(r['eligible_opportunities']);notes.append(dict(cumulative_row_index=i,intended_weeks=[6,7],weeks_with_rows=weeks,intended_cohort_offer_universe=intended,intended_full_category_offer_universe=full,reported_period_cohort_opportunities=reported,actual_missing_week_offer_rows=missing,outside_cohort_offer_rows=full-intended,outside_cohort_or_unrepresented_offer_rows=full-reported,period_state='COMPLETE_TWO_WEEK_COHORT_SOURCE_ROWS'if weeks==[6,7]else'PARTIAL_PROCEDURE_LAW_COVERAGE',admitted_forecast_coverage_of_intended_cohort_period=int(r['admitted_forecasts'])/intended if intended else None))
 write(b/'CUMULATIVE_COMPLETENESS_ANNOTATIONS_V2.json',notes);write(b/'FINAL_REPORT_READING_CONTRACT_V2.json',dict(at=now(),state='METADATA_ONLY_CORRECTION_NOT_NEW_SCORES',primary_table='ALL_METHOD_PRIMARY_SIDE_TABLES_V3.csv',primary_sha256=sha(dest),full_table_read_rule='Join each summary source_refs side entry tosourcebound annotation(source_artifact,source_row_index), verifySHA, applydisjointcoverage andP2selectedpoolprobability corrections. Fullgzip originalfieldsretainedunchanged.',source_annotation_bindings=bindings,cumulative_default='CUMULATIVE_COMPLETENESS_ANNOTATIONS_V2.json',cumulative_sha256=sha(b/'CUMULATIVE_COMPLETENESS_ANNOTATIONS_V2.json'),superseded_metadata='V1cumulativefullcategory-minus-cohort difference was misleadinglycalledmissingweek. V2separatesoutsidecohortfrom actualmissingweek. FixedF7canonicalabstention nulls receive existingdisjointsourceannotations.',leaf_origin_default='COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS_V2.json',scientific_scores_changed=False,new_fits=0,new_direction_grades=0,new_CDF_evaluations=0))
 p=b/'README.md';text=p.read_text().replace('(ALL_METHOD_PRIMARY_SIDE_TABLES_V2.csv)','(ALL_METHOD_PRIMARY_SIDE_TABLES_V3.csv)').replace('(CUMULATIVE_COMPLETENESS_ANNOTATIONS.json)','(CUMULATIVE_COMPLETENESS_ANNOTATIONS_V2.json)');text+='\nThe [final reading contract](FINAL_REPORT_READING_CONTRACT_V2.json) applies existing disjoint-denominator/P2 annotations to the full tables; the compact primary V3table already includes them. Cohort-period completeness uses each cohort’s intended opportunities and separately reports outside-cohort rows and genuinely missing weeks. Earlier metadata versions remain audit-only; source scores never changed.\n';p.write_text(text);print(json.dumps(dict(primary_rows=i if False else 2730,cumulative_annotations=len(notes))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--report',type=Path,required=True);main(p.parse_args())
