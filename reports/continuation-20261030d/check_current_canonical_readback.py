"""Stream current canonical CSV/ID projection against immutable audit shards."""
import collections,csv,hashlib,json,math,resource,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def equal_csv(value,expected):
 if expected is None:assert value=='',(value,expected)
 elif isinstance(expected,(int,float)):assert value!=''and math.isclose(float(value),expected,rel_tol=1e-12,abs_tol=1e-12),(value,expected)
 else:assert value==str(expected),(value,expected)
def main():
 start,cpu=time.monotonic(),time.process_time();pub=HERE/'current-valid-results';manifest=pub/'CURRENT_MANIFEST.json';m=json.loads(manifest.read_bytes());audit=ROOT/m['audit_manifest'];assert sha(audit)==m['audit_manifest_sha256'];old=json.loads(audit.read_bytes());exclusion=ROOT/m['exclusion_manifest'];assert sha(exclusion)==m['exclusion_manifest_sha256'];exc={x['test_id']for x in json.loads(exclusion.read_bytes())['exclusion_rows']};idfile=ROOT/m['selected_ids']['path'];assert sha(idfile)==m['selected_ids']['sha256'];ids=json.loads(idfile.read_bytes());seen=set();evidence=collections.Counter();checks=collections.Counter();count=software=excluded=0
 def csvrows():
  for part in m['csv_parts']:
   path=ROOT/part['path'];assert path.stat().st_size==part['bytes']and sha(path)==part['sha256'];n=0
   with path.open(newline='')as f:
    for row in csv.DictReader(f):n+=1;yield row
   assert n==part['rows'];checks['current_csv_part_hashes_and_censuses']+=1
 iterator=iter(csvrows())
 for part in old['shards']:
  path=ROOT/part['path'];assert sha(path)==part['sha256']and path.stat().st_size==part['bytes']
  for record in json.loads(path.read_bytes()):
   if record['kind']=='software_verification':software+=1;continue
   if record['test_id']in exc:excluded+=1;continue
   row=next(iterator);assert row['test_id']==ids[count]==record['test_id']and row['test_id']not in seen;seen.add(row['test_id']);count+=1;evidence[record['evidence']]+=1
   for k in('procedure_id','history_regime','product_id','category','population','season','week','position','fallback_view','n','forecast_or_offered_rows','fallback_rows','evidence','native_units','source_artifact'):equal_csv(row[k],record.get(k))
   assert json.loads(row['evaluation_seasons'])==record['seasons']and json.loads(row['evaluation_weeks'])==record['weeks'];equal_csv(row['evidence_panel'],record.get('evaluation_panel_id'))
   for metric in('mae','mse','rmse','bias','p90_abs','p95_abs','max_abs','brier','crps','nll','log_loss'):equal_csv(row[metric],record['metrics'].get(metric));checks['native_metric_readbacks']+=1
   precisions={k:[x['numerator'],x['denominator']]for k,x in(record.get('precision_metrics')or{}).items()};assert json.loads(row['precision_counts'])==precisions;checks['precision_numerator_denominator_objects']+=1
   assert json.loads(row['nonfinite_status'])=={k:v for k,v in record['metric_status'].items()if v=='positive_infinite_loss'}
   raw=record.get('source_aggregate_fields')or{};comparison=record.get('reporting_comparison')or raw.get('comparison')
   if comparison and comparison.get('status')=='PAIRED_RETAINED_ROWS':
    equal_csv(row['paired_n'],comparison['paired_n']);equal_csv(row['comparator'],comparison['comparator_procedure_id']);a,b=comparison['candidate_error'],comparison['comparator_error'];equal_csv(row['absolute_error_change'],a-b);equal_csv(row['relative_error_change'],(a-b)/b if b else None);checks['independent_paired_error_delta_readbacks']+=1
   if record.get('n')==0:assert not row['mae']and not row['brier'];checks['zero_support_no_fabricated_error']+=1
 assert next(iterator,None)is None;assert count==len(ids)==m['selected_evaluation_views']==124630 and excluded==len(exc)==m['excluded_evaluation_views']==20567 and software==m['software_receipts_separate']==22;assert dict(evidence)==m['by_evidence'];assert count+excluded+software==old['record_count']==145219
 result=dict(state='PASS_CURRENT_CANONICAL_VERSION_CSV_AND_ID_READBACK_RANKINGS_SEPARATELY_REVIEWED',manifest_sha256=sha(manifest),audit_manifest_sha256=sha(audit),selected_evaluation_views=count,excluded_evaluation_views=excluded,software_separate=software,by_evidence=dict(evidence),checks=dict(checks),ranking_scope_note='Canonicalversionprojectiononly. Source-reportandprovider/replaytiersremainseparate; dedicatedrankingadmissioncorrection/review required. ThisPASSdoesnotcertifytheinitial235-representativechart-omittingdraft.',new_fits=0,inference_calls=0,new_forecasts=0,current2026_week8_outcomes_read=0,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
 (HERE/'CURRENT_CANONICAL_INDEPENDENT_READBACK.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
