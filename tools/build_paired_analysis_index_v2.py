#!/usr/bin/env python3
"""Index derived paired analyses separately from forecast evaluations and fits."""
import collections,csv,hashlib,json,math,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/continuation-20261030d'
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
 sources=[OUT/'history-adjacent-v1/PAIRED_HISTORY_ANALYSIS.json']+sorted(p for p in(OUT/'carry-older-robustness-v1').glob('PAIR_ANALYSIS_*.json')if re.fullmatch(r'PAIR_ANALYSIS_202[2-5]\.json',p.name));records=[];inputs=[];ids=set();status_counts=collections.Counter()
 for path in sources:
  value=json.loads(path.read_text());rows=value if isinstance(value,list)else value['rows'];source=path.relative_to(ROOT).as_posix();source_sha=digest(path);semantic=set()
  for i,r in enumerate(rows):
   carry='candidate_metrics'in r
   n=r.get('paired_n',r.get('n'));candidate=r['candidate_metrics'].get('mae')if carry else r.get('candidate_error');control=r['comparator_metrics'].get('mae')if carry else r.get('comparator_error');delta=r.get('native_error_delta')if carry else r.get('delta');metric='MAE'if carry else r['metric'];uncertainty=r.get('uncertainty',r)
   if not isinstance(n,int)or n<0:raise ValueError('nonnegative paired denominator required')
   if n:
    if not all(isinstance(x,(int,float))and math.isfinite(x)and x>=0 for x in(candidate,control)):raise ValueError('finite paired point/event losses required')
    if not math.isclose(candidate-control,delta,abs_tol=1e-10,rel_tol=1e-10):raise ValueError('paired native delta mismatch')
   elif any(x is not None for x in(candidate,control,delta)):raise ValueError('empty paired cases must retain null errors')
   contrast=r.get('comparison',r.get('contrast'));proc=r.get('candidate_procedure_id',r.get('procedure_id'));product=r.get('candidate_product_id',r.get('product_id'));target=r.get('target','rush_att'if carry else None)
   identity=(proc,product,target,r['population'],r['season'],r['history_regime'],r.get('policy_id'),metric,contrast,r['fallback_view'],r.get('cohort_id'),r.get('position'),r.get('comparator_procedure_id'),r.get('comparator_history_regime'))
   if identity in semantic:raise ValueError('duplicate semantic comparison within source')
   semantic.add(identity);analysis_id='PAIR-'+hashlib.sha256(json.dumps([source,identity],separators=(',',':')).encode()).hexdigest()[:20]
   if analysis_id in ids:raise ValueError('duplicate analysis identity')
   ids.add(analysis_id);state='PAIRED_LOSS_SCORED'if n else'NO_SUPPORTED_PAIRED_ROWS';status_counts[state]+=1
   history_pair=(r['history_regime'],r.get('comparator_history_regime'))if carry else contrast.split('_MINUS_')
   records.append(dict(candidate_history_regime=history_pair[0],comparator_history_regime=history_pair[1],comparator_procedure_id=r.get('comparator_procedure_id',proc),comparator_product_id=r.get('comparator_product_id',product),query_rows=r.get('query_rows'),unresolved_rows=r.get('unresolved_rows'),fullsystem_n=r.get('fullsystem_n'),contribution_to_fullsystem_delta=r.get('contribution_to_fullsystem_delta'),candidate_fallback_rows=r['candidate_metrics'].get('fallback_rows')if carry else None,comparator_fallback_rows=r['comparator_metrics'].get('fallback_rows')if carry else None,analysis_id=analysis_id,kind='DERIVED_PAIRED_LOSS_ANALYSIS',state=state,procedure_id=proc,product_id=product,target=target,population=r['population'],season=r['season'],history_regime=r['history_regime'],policy_id=r.get('policy_id'),contrast=contrast,view=r['fallback_view'],cohort_id=r.get('cohort_id'),position=r.get('position'),metric=metric,n=n,candidate_error=candidate,comparator_error=control,absolute_error_change=delta,relative_error_change=r.get('relative_error_delta',r.get('relative_error_change')),membership_sha256=r.get('paired_membership_sha256',r.get('membership_sha256')),week_clusters=uncertainty.get('week_clusters'),week_interval=uncertainty.get('week_interval'),week_interval_status=uncertainty.get('week_interval_status'),game_cluster_se=uncertainty.get('game_cluster_sensitivity_se'),history_status=r.get('requested_history_status',r.get('history_limit')),precision_status='No new per-mask precision claim; retained univariate precision remains linked in audit index',source_artifact=source,source_artifact_sha256=source_sha,source_row_index=i,new_fits=0,new_forecasts=0,new_NFL_observations=0))
  inputs.append(dict(artifact=source,sha256=source_sha,rows=len(rows),state='DERIVED_PAIRED_ANALYSIS_SCORED_WITH_EMPTY_STATES_RETAINED',new_univariate_forecast_views=0))
 out=OUT/'paired-analysis-index-v2';out.mkdir(exist_ok=True)
 with(out/'PAIRED_ANALYSES.csv').open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader()
  for r in records:w.writerow({k:json.dumps(v,separators=(',',':'))if isinstance(v,(dict,list))else v for k,v in r.items()})
 (out/'PAIRED_ANALYSES.json').write_text(json.dumps(records,separators=(',',':'))+'\n')
 manifest=dict(schema='v2-derived-paired-analysis-index-v2',inputs=inputs,record_count=len(records),status_counts=dict(status_counts),records_json=dict(path=(out/'PAIRED_ANALYSES.json').relative_to(ROOT).as_posix(),sha256=digest(out/'PAIRED_ANALYSES.json')),records_csv=dict(path=(out/'PAIRED_ANALYSES.csv').relative_to(ROOT).as_posix(),sha256=digest(out/'PAIRED_ANALYSES.csv')),metric_meaning='candidatepairednativeloss/comparatorpairednativeloss;differentcriteriaretainunits;notgenericpercentageaccuracy',new_fits=0,new_forecasts=0,new_NFL_observations=0,univariate_audit_index='reports/continuation-20261030c/results-index/INDEX_MANIFEST.json')
 (out/'ANALYSIS_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n');Path(ROOT/'registries/ANALYSIS_ARTIFACTS.json').write_text(json.dumps(inputs,indent=2)+'\n');print(json.dumps(dict(records=len(records),states=dict(status_counts),new_fits=0,new_forecasts=0)))
if __name__=='__main__':main()
