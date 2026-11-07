#!/usr/bin/env python3
"""Select canonical score versions without changing the immutable audit index."""
import collections,csv,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2.comparison_reporting import comparison_fields
from tools.build_test_index import category_slug
OUT=ROOT/'reports/continuation-20261030d'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
def recipe(record):
 p=record.get('procedure_id')or''
 if p=='empirical-player-history-control-v1':return'EMPIRICAL','empirical-history-control'
 if p.startswith('v2-qualified-position-defense-information-wave-v1:D1:'):return'LEAF_CDF','leaf-cdf-observed-defense-D1'
 if p.startswith('v2-qualified-position-defense-information-wave-v1:D2:'):return'LEAF_CDF','leaf-cdf-observed-defense-D2'
 if p.startswith('v2-c02-explicit-lag-block-removal-leaf-cdf-v1:'):return'LEAF_CDF','leaf-cdf-without-explicit-lag-block'
 if ':ordered_leaf_cdf:'in p:return'LEAF_CDF','ordered-leaf-cdf-base'
 if ':regularized_glm_law:'in p:return'GLM_LAW','regularized-glm-law'
 if p.startswith('v2-hgb-poisson-count-point-reconstruction-v1:'):return'HGB','hgb-poisson-objective-point'
 if p.startswith('v2-hgb-rush-att-qb-rb-specialization-v1:'):return'HGB','hgb-L1-QB-RB-training'
 if p.startswith('hgb-direct-history-controls-v1:'):
  for objective,name in [('absolute_error_point','hgb-L1'),('squared_error_mean','hgb-L2'),('log_loss_probability','hgb-binary-logloss')]:
   if objective in p:return'HGB',name
 return None
def compact(r):
 s=r.get('source_aggregate_fields')or{};m=r.get('metrics')or{};c=comparison_fields(r)
 row={k:r.get(k)for k in('test_id','procedure_id','history_regime','product_id','category','population','season','week','position','fallback_view','n','forecast_or_offered_rows','fallback_rows','evidence','native_units','source_artifact')}
 row.update(cohort_id=s.get('cohort_id'),information_policy=s.get('information_policy',r.get('feature_memory_policy')),evaluation_seasons=json.dumps(r.get('seasons')),evaluation_weeks=json.dumps(r.get('weeks')),evidence_panel=r.get('evaluation_panel_id'),comparison_status=c['comparison_status'],comparator=c['comparator_procedure_id'],paired_n=c['paired_n'],absolute_error_change=c['absolute_error_change'],relative_error_change=c['relative_error_change'],fallback_rate=c['fallback_rate'])
 row.update({k:m.get(k)for k in('mae','mse','rmse','bias','p90_abs','p95_abs','max_abs','brier','crps','nll','log_loss')});row['precision_counts']=json.dumps({k:[v['numerator'],v['denominator']]for k,v in(r.get('precision_metrics')or{}).items()},separators=(',',':'));row['nonfinite_status']=json.dumps({k:v for k,v in(r.get('metric_status')or{}).items()if v=='positive_infinite_loss'},separators=(',',':'));return row
def writecsv(path,rows):
 rows=list(rows)
 if not rows:return
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with Path(path).open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,separators=(',',':'))if isinstance(v,(dict,list))else v for k,v in r.items()})
def main():
 recommendation=OUT/'CURRENT_SCORE_VERSION_EXCLUSIONS_RECOMMENDATION.json';policy=json.loads(recommendation.read_text());audit=ROOT/policy['audit_manifest']
 if sha(audit)!=policy['audit_manifest_sha256']:raise ValueError('frozen audit manifest changed')
 parent=json.loads(audit.read_text());excluded={r['test_id']:r for r in policy['exclusion_rows']}
 if len(excluded)!=len(policy['exclusion_rows']):raise ValueError('duplicate exclusion')
 out=OUT/'current-valid-results';out.mkdir(exist_ok=True);ids=[];seen=set();software=[];by_evidence=collections.Counter();by_reason=collections.Counter();candidate=[];parts=[];f=None;w=None;fields=None;part_count=0
 try:
  for shard in parent['shards']:
   b=(ROOT/shard['path']).read_bytes()
   if hashlib.sha256(b).hexdigest()!=shard['sha256']:raise ValueError('audit shard changed')
   for r in json.loads(b):
    if r['test_id']in seen:raise ValueError('duplicate audit result')
    seen.add(r['test_id'])
    if r['kind']=='software_verification':software.append(r['test_id']);continue
    if r['test_id']in excluded:
     x=excluded[r['test_id']]
     if r['source_artifact']!=x['source_artifact']or r['source_artifact_sha256']!=x['source_artifact_sha256']:raise ValueError('exclusion source binding changed')
     by_reason[x['state']]+=1;continue
    ids.append(r['test_id']);by_evidence[r['evidence']]+=1;row=compact(r)
    if fields is None:fields=list(row)
    if w is None or part_count==10000:
     if f:f.close();parts[-1].update(rows=part_count,bytes=path.stat().st_size,sha256=sha(path))
     path=out/f'CURRENT-{len(parts):04d}.csv';f=path.open('w',newline='');w=csv.DictWriter(f,fieldnames=fields);w.writeheader();part_count=0;parts.append(dict(path=path.relative_to(ROOT).as_posix()))
    w.writerow(row);part_count+=1
    source=r.get('source_aggregate_fields')or{};mech=recipe(r)
    # Membership is inherited from the independently verified matched primary
    # panel, never inferred from equal n. Smaller reference panels stay apart.
    if mech and r.get('seasons')==[2026]and r.get('weeks')==list(range(1,8))and r['population']=='primary'and r.get('position')in(None,'ALL')and r.get('fallback_view')in(None,'ALL')and not source.get('cohort_id')and r['evidence']=='NEW_EXPERIMENT':
     m=r['metrics'];target=r['category'];base=dict(row,family_id=mech[0],mechanism_id=mech[1],native_point_view=r['product_id'],actual_procedure=r['procedure_id'],source_score_version='CURRENT_CANONICAL',selection='exposedobservedminimum;notfrozenlivepolicy',same_family_procedures_allowed=True)
     products=[('event_probability','brier')]if target=='anytime_td'else[('display_point','mae'),('genuine_mean','mse'),('forecast_distribution','crps')]
     for product,metric in products:
      if product=='genuine_mean'and'mean'not in(r['product_id']or''):continue
      if not isinstance(m.get(metric),(int,float)):continue
      candidate.append(dict(base,ranking_product=product,ranking_metric=metric,ranking_loss=m[metric]))
  if f:f.close();f=None;parts[-1].update(rows=part_count,bytes=path.stat().st_size,sha256=sha(path))
 finally:
  if f:f.close()
 if set(excluded)-seen:raise ValueError('exclusion is not in the audit index')
 idpath=out/'CURRENT_RECORD_IDS.json';save(idpath,ids)
 manifest=dict(schema='v2-current-canonical-score-selection-v1',default_view='CURRENT_CANONICAL_SCORE_VERSIONS',audit_manifest=policy['audit_manifest'],audit_manifest_sha256=sha(audit),exclusion_manifest=recommendation.relative_to(ROOT).as_posix(),exclusion_manifest_sha256=sha(recommendation),audit_records=parent['record_count'],selected_evaluation_views=len(ids),excluded_evaluation_views=len(excluded),software_receipts_separate=len(software),by_exclusion_reason=dict(by_reason),by_evidence=dict(by_evidence),selected_ids=dict(path=idpath.relative_to(ROOT).as_posix(),sha256=sha(idpath)),csv_parts=parts,semantics='Versionselectiononly;reported/unreproduced/reference/offer/population/horizonpanelsremainseparate.Noglobalpoolingorclaimthatallretainedrecordsarequalifiedfortournament.Originalauditscores/shardsunchanged.')
 save(out/'CURRENT_MANIFEST.json',manifest)
 groups=collections.defaultdict(list)
 for r in candidate:groups[r['category'],r['ranking_product'],r['mechanism_id']].append(r)
 representatives=[]
 for rs in groups.values():
  best=min(rs,key=lambda r:(r['ranking_loss'],r['actual_procedure'],r['history_regime'],r['native_point_view'],r['test_id']));best=dict(best,view_history_ties_within_1e12=sum(math.isclose(r['ranking_loss'],best['ranking_loss'],abs_tol=1e-12,rel_tol=0)for r in rs));representatives.append(best)
 final=[]
 for group in sorted({(r['category'],r['ranking_product'])for r in representatives}):
  rs=sorted((r for r in representatives if(r['category'],r['ranking_product'])==group),key=lambda r:(r['ranking_loss'],r['mechanism_id']));previous=None;rank=0
  for i,r in enumerate(rs):
   if previous is None or not math.isclose(r['ranking_loss'],previous,abs_tol=1e-12,rel_tol=0):rank=i+1
   final.append(dict(r,rank=rank,in_top_five_distinct_procedures=i<5));previous=r['ranking_loss']
 save(OUT/'PROCEDURE_RANKINGS.json',final);writecsv(OUT/'PROCEDURE_RANKINGS.csv',final);writecsv(OUT/'TOP5_BY_CATEGORY_PRODUCT.csv',[r for r in final if r['in_top_five_distinct_procedures']]);save(OUT/'TOP5_BY_CATEGORY_PRODUCT.json',[r for r in final if r['in_top_five_distinct_procedures']])
 writecsv(OUT/'REFERENCE_CONTROL_RESULTS.csv',representatives)
 ready=[dict(r,readiness='MODEL_ARCHIVE_QUOTA_BLOCKED'if'observed-defense'in r['mechanism_id']else'RESEARCH_ADAPTER_CAPTURED_OWNER_ADMISSION_PENDING',deployed=False)for r in final if r['ranking_product']in('display_point','event_probability')]
 writecsv(OUT/'UPCOMING_READINESS_SHORTLIST.csv',ready)
 (out/'README.md').write_text('# Current canonical score versions\n\n'+f"Default: {len(ids):,} evaluation views. Excludes {len(excluded):,} superseded, invalidated or component-version views; {len(software)} software receipts remain separate. All {parent['record_count']:,} audit records remain unchanged.\n\n"+'[Current CSV parts](CURRENT_MANIFEST.json) · [Top procedures](../TOP5_BY_CATEGORY_PRODUCT.csv) · [All audit history](../../continuation-20261030c/results-index/README.md)\n\nVersion selection does not pool different seasons, horizons, source vintages or populations. Reported original results are not automatically verified tournament entrants. Numerical loss, tolerance accuracy, probability skill and priced offer results remain different products.\n')
 print(json.dumps(dict(selected=len(ids),excluded=len(excluded),candidate_output_views=len(candidate),distinct_recipe_representatives=len(representatives),top5_rows=sum(r['in_top_five_distinct_procedures']for r in final),newfits=0)))
if __name__=='__main__':main()
