#!/usr/bin/env python3
"""Append exact-grid median precision scores; retain original forecasts/losses."""
import hashlib,json,csv,datetime,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
BASE=ROOT/'reports/continuation-20261030'
DIMS=('record_id','procedure_id','history_regime','policy_id','target','population','product_id','week','season','position','fallback_view','cohort_id')
def key(r):return tuple(r.get(k)for k in DIMS)
def main():
 out=BASE/'chart-grid-precision-correction-v1'
 if out.exists():raise ValueError('fresh immutable score version required')
 out.mkdir()
 path=BASE/'CHART_EXACT_GRID_PRECISION_AUDIT.json';audit=json.loads(path.read_text())
 protocol=dict(version='v2-chart-median-exact-grid-precision-correction-v1',registered_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  kind='saved-row precision-only correction; no forecast/fit/primary-error improvement',
  rule='For genuine0.02gridmedians+labels, compare abs(integer_prediction_coordinate-integer_actual_coordinate) against50/250/500; meanproductsretainoriginalstored-point semantics',
  source_audit_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source_scores=audit['source_hashes'],new_fits=0,new_forecasts=0,week8_outcomes_read=0)
 (out/'FROZEN_CORRECTION_PROTOCOL.json').write_text(json.dumps(protocol,indent=2)+'\n')
 sources={}
 for name,expected in audit['source_hashes'].items():
  b=(ROOT/name).read_bytes()
  if hashlib.sha256(b).hexdigest()!=expected:raise ValueError('old scores changed')
  rows=json.loads(b);sources[name]={key(r):r for r in rows}
  if len(sources[name])!=len(rows):raise ValueError('ambiguous correction source dimensions')
 output=[]
 for item in audit['projection']:
  original=sources[item['source_score_artifact']][key(item)]
  if original['product_id']!='lower_median':raise ValueError('do not round mean products')
  row=dict(original);row['original_float_precision']={k:original.get(k)for k in item['precision']}
  for metric,value in item['precision'].items():
   if value['denominator']!=original['n'] or not 0<=value['numerator']<=value['denominator']:raise ValueError('correction count mismatch')
   row[metric]=value['exact_grid_rate']
  row.update(record_id='EXACT-GRID-'+hashlib.sha256(json.dumps([item['source_score_artifact'],key(item)],separators=(',',':')).encode()).hexdigest()[:24],
   supersedes_score_artifact=item['source_score_artifact'],supersedes_source_identity={k:item.get(k)for k in DIMS},
   supersedes_source_sha256=audit['source_hashes'][item['source_score_artifact']],
   precision_counts_exact_grid=item['precision'],exact_grid_denominator=50,
   correction_kind='precision_only_no_predictive_gain',scoring_version='chart-grid-median-precision-v2',
   evidence='REPRODUCED_FROM_DATA',point_errors_and_forecast_bytes_unchanged=True)
  output.append(row)
 body=json.dumps(output,separators=(',',':'),allow_nan=False).encode()+b'\n';(out/'SCORES.json').write_bytes(body)
 fields=list(dict.fromkeys(k for r in output for k in r))
 with(out/'SCORES.csv').open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:json.dumps(v,sort_keys=True)if isinstance(v,(dict,list))else v for k,v in r.items()}for r in output)
 receipt=dict(state='SCORED_PRECISION_ONLY_CORRECTION',score_views=len(output),affected_original_views=audit['score_views_with_any_precision_difference'],source_audit_sha256=protocol['source_audit_sha256'],score_sha256=hashlib.sha256(body).hexdigest(),new_fits=0,new_forecasts=0,week8_outcomes_read=0,primary_error_changed=False,original_scores_unchanged=True)
 (out/'RUN_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
 (out/'README.md').write_text('# Exact chart-grid median precision correction\n\nThis append-only score version corrects strict/inclusive1/5/10-point accuracy diagnostics for genuine chart medians on the signed0.02 grid. The original1007score views remain, with478having at least one changed tolerance rate. Forecasts, mean products, MAE/MSE/RMSE/bias, ranks and NFL sample counts are unchanged. This is scoring correctness, not a predictive improvement.\n\nThe independent audit proves integer coordinates using Decimal and retains exact hit numerators/denominators. Original float subtraction can cross an exact boundary. Use these corrected rates; the permanent index labels earlier median precision superseded. No fit, new forecast or Week8 outcome was used.\n')
 print(json.dumps(receipt))
if __name__=='__main__':main()
