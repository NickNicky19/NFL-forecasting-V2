#!/usr/bin/env python3
"""Export readable core method/season/week views from the complete index."""
import csv,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from nfl_v2.comparison_reporting import comparison_fields
OUT=ROOT/'reports/continuation-20261030c'

def main():
 manifest=OUT/'results-index/INDEX_MANIFEST.json';m=json.loads(manifest.read_text());file=OUT/'ALL_METHOD_SCORES.csv';count=0;writer=None
 with file.open('w',newline='')as f:
  for shard in m['shards']:
   b=(ROOT/shard['path']).read_bytes()
   if hashlib.sha256(b).hexdigest()!=shard['sha256']:raise ValueError('index changed during export')
   for r in json.loads(b):
    if r['kind']=='software_verification':continue
    s=r.get('source_aggregate_fields')or{}
    if s.get('cohort_id')or r.get('position')not in(None,'ALL')or r.get('fallback_view')not in(None,'ALL'):continue
    metrics=r.get('metrics')or{};cmp=comparison_fields(r)
    row={k:r.get(k)for k in('test_id','procedure_id','history_regime','product_id','category','population','season','week','n','forecast_or_offered_rows','fallback_rows','native_units','accuracy_status','evidence','score_version_state','source_artifact')}
    row.update({k:metrics.get(k)for k in('mae','mse','rmse','bias','p90_abs','p95_abs','max_abs','brier','crps','nll','log_loss')})
    row.update(precision_numerator_denominator=json.dumps({k:[p['numerator'],p['denominator']]for k,p in(r.get('precision_metrics')or{}).items()},separators=(',',':')),nonfinite_loss_status=json.dumps({k:v for k,v in(r.get('metric_status')or{}).items()if v=='positive_infinite_loss'},separators=(',',':')),evaluation_seasons=json.dumps(r.get('seasons'),separators=(',',':')),evaluation_weeks=json.dumps(r.get('weeks'),separators=(',',':')))
    row.update({k:cmp.get(k)for k in('comparison_status','comparator_procedure_id','comparator_history_regime','comparator_product_id','absolute_error_change','relative_error_change','paired_n','fallback_rate')})
    row['source_version_note']=r.get('source_version_note')
    if writer is None:writer=csv.DictWriter(f,fieldnames=list(row));writer.writeheader()
    writer.writerow(row);count+=1
 if file.stat().st_size>95*1024*1024:raise ValueError('compact CSV exceeds public-file budget; use bounded complete CSV parts')
 alias=dict(schema='v2-all-method-score-recordset-references-v1',full_JSON_recordset='results-index/INDEX_MANIFEST.json',full_JSON_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),full_record_count=m['record_count'],main_CSV=dict(path=file.name,rows=count,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),bytes=file.stat().st_size,scope='ALLposition/full-systemcoremethod-season-weekviews;allcohort/position/learned/fallbackviewsremaininthecompleteindex'),complete_CSV_parts=m['csv_parts'],accuracy_definition='precisionmetricnamesretainstrict/inclusivebounds;cell=[numerator,denominator];MAEisnotpercentageaccuracy',new_NFL_fits_or_scores=0)
 (OUT/'ALL_METHOD_SCORE_REFERENCES.json').write_text(json.dumps(alias,indent=2)+'\n');print(json.dumps(dict(core_views=count,bytes=file.stat().st_size,full_index_records=m['record_count'],new_fits=0)))
if __name__=='__main__':main()
