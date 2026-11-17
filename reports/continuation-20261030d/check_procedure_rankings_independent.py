"""Independently select matched-panel procedure representatives and top fives."""
import argparse,collections,hashlib,json,math,resource,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SOURCES={
 'reports/continuation-20261029/history-diagnostic-v1/SEASON_RESULTS_2022_2026.csv',
 'reports/continuation-20261029/hgb-history-v1/SCORES.json',
 'reports/continuation-20261030/distribution-wave-v2/SCORES.json',
 'reports/continuation-20261030/count-ablation-wave-v1/SCORES.json',
 'reports/continuation-20261030/chart-wave-v1/SCORES.json',
 'reports/continuation-20261030/chart-wave-v1/EMPIRICAL_SCORES.json',
 'reports/continuation-20261030b/ordered-information-ablation-v1/SCORES.json',
 'reports/continuation-20261030c/qualified-defense-information-v1/SCORES.json'}
CORRECTION='reports/continuation-20261030/chart-grid-precision-correction-v1/SCORES.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mechanism(proc):
 if proc in('empirical-player-history-control-v1','v2-qualified-partial-chart-direct-wave-v1:empirical'):return'EMPIRICAL','empirical-history-control'
 if proc.startswith('v2-qualified-position-defense-information-wave-v1:D1:'):return'LEAF_CDF','leaf-cdf-observed-defense-D1'
 if proc.startswith('v2-qualified-position-defense-information-wave-v1:D2:'):return'LEAF_CDF','leaf-cdf-observed-defense-D2'
 if proc.startswith('v2-c02-explicit-lag-block-removal-leaf-cdf-v1:'):return'LEAF_CDF','leaf-cdf-without-explicit-lag-block'
 if ':ordered_leaf_cdf:'in proc:return'LEAF_CDF','ordered-leaf-cdf-base'
 if ':regularized_glm_law:'in proc:return'GLM_LAW','regularized-glm-law'
 if proc.startswith('v2-hgb-poisson-count-point-reconstruction-v1:'):return'HGB','hgb-poisson-objective-point'
 if proc.startswith('v2-hgb-rush-att-qb-rb-specialization-v1:'):return'HGB','hgb-L1-QB-RB-training'
 if proc.startswith('hgb-direct-history-controls-v1:'):
  for token,label in(('absolute_error_point','hgb-L1'),('squared_error_mean','hgb-L2'),('log_loss_probability','hgb-binary-logloss')):
   if token in proc:return'HGB',label
 return None
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--ranking-root',type=Path,required=True);parser.add_argument('--builder',type=Path,required=True);args=parser.parse_args();ranking_root=args.ranking_root.resolve()
 start,cpu=time.monotonic(),time.process_time();current=json.loads((ranking_root/'current-valid-results/CURRENT_MANIFEST.json').read_bytes());manifest=ROOT/current['audit_manifest'];assert sha(manifest)==current['audit_manifest_sha256'];m=json.loads(manifest.read_bytes());excluded={x['test_id']for x in json.loads((ROOT/current['exclusion_manifest']).read_bytes())['exclusion_rows']};candidates=[];checks=collections.Counter();source_hashes={};target_n=collections.defaultdict(set)
 for part in m['shards']:
  for r in json.loads((ROOT/part['path']).read_bytes()):
   if r['kind']=='software_verification'or r['test_id']in excluded:continue
   raw=r.get('source_aggregate_fields')or{};src=r['source_artifact'];mech=mechanism(r.get('procedure_id')or'')
   if not mech or r['seasons']!=[2026]or r['weeks']!=list(range(1,8))or r['population']!='primary'or r.get('position')not in(None,'ALL')or r.get('fallback_view')not in(None,'ALL')or raw.get('cohort_id'):continue
   direct=src in SOURCES and r['evidence']=='NEW_EXPERIMENT'
   corrected=src==CORRECTION and r['evidence']=='REPRODUCED_FROM_DATA'and raw.get('correction_kind')=='precision_only_no_predictive_gain'and raw.get('supersedes_score_artifact')in SOURCES
   if not(direct or corrected):continue
   assert r['n']and r['n']>0;target_n[r['category']].add(r['n']);source_hashes[src]=r['source_artifact_sha256']
   if corrected:assert sha(ROOT/raw['supersedes_score_artifact'])==raw['supersedes_source_sha256'];checks['qualified_corrected_chart_full_primary_views']+=1
   products=[('event_probability','brier')]if r['category']=='anytime_td'else[('display_point','mae'),('genuine_mean','mse'),('forecast_distribution','crps')]
   for product,metric in products:
    if product=='genuine_mean'and'mean'not in(r['product_id']or''):continue
    value=r['metrics'].get(metric)
    if value is None:continue
    assert isinstance(value,(int,float))and not isinstance(value,bool)and math.isfinite(value)and value>=0
    candidates.append(dict(category=r['category'],ranking_product=product,ranking_metric=metric,ranking_loss=value,
      mechanism_id=mech[1],family_id=mech[0],actual_procedure=r['procedure_id'],history_regime=r['history_regime'],native_point_view=r['product_id'],test_id=r['test_id'],source_artifact=src,n=r['n'],precision=r.get('precision_metrics')or{},status=r.get('metric_status')or{}))
 for path,digest in source_hashes.items():assert sha(ROOT/path)==digest
 assert checks['qualified_corrected_chart_full_primary_views']==11 and len(target_n)==12 and all(len(ns)==1 for ns in target_n.values())
 grouped=collections.defaultdict(list)
 for r in candidates:grouped[r['category'],r['ranking_product'],r['mechanism_id']].append(r)
 expected={}
 for key,rs in grouped.items():
  best=min(rs,key=lambda x:(x['ranking_loss'],x['actual_procedure'],x['history_regime'],x['native_point_view'],x['test_id']));expected[key]=dict(best,ties=sum(math.isclose(x['ranking_loss'],best['ranking_loss'],rel_tol=0,abs_tol=1e-12)for x in rs))
 actual=json.loads((ranking_root/'PROCEDURE_RANKINGS.json').read_bytes());top=json.loads((ranking_root/'TOP5_BY_CATEGORY_PRODUCT.json').read_bytes());seen=set();rank_groups=collections.defaultdict(list)
 for r in actual:
  key=r['category'],r['ranking_product'],r['mechanism_id'];assert key in expected and key not in seen;seen.add(key);best=expected[key]
  for field in('ranking_metric','ranking_loss','family_id','actual_procedure','history_regime','native_point_view','test_id','source_artifact','n'):assert r[field]==best[field],(key,field,r[field],best[field])
  assert r['view_history_ties_within_1e12']==best['ties'];assert json.loads(r['precision_counts'])=={k:[v['numerator'],v['denominator']]for k,v in best['precision'].items()};assert json.loads(r['nonfinite_status'])=={k:v for k,v in best['status'].items()if v=='positive_infinite_loss'};rank_groups[key[:2]].append(r);checks['procedure_representative_source_metric_precision_bindings']+=1
 assert seen==set(expected);chosen=[];boundary_ties=[]
 for key,rs in rank_groups.items():
  rs.sort(key=lambda r:(r['ranking_loss'],r['mechanism_id']));rank=0;prev=None
  for i,r in enumerate(rs):
   if prev is None or not math.isclose(r['ranking_loss'],prev,rel_tol=0,abs_tol=1e-12):rank=i+1
   assert r['rank']==rank and r['in_top_five_distinct_procedures']==(i<5);prev=r['ranking_loss']
   if i<5:chosen.append(r)
  if len(rs)>5 and math.isclose(rs[4]['ranking_loss'],rs[5]['ranking_loss'],rel_tol=0,abs_tol=1e-12):boundary_ties.append(dict(category=key[0],product=key[1],loss=rs[4]['ranking_loss']))
 assert {r['test_id']+'|'+r['ranking_product']for r in top}=={r['test_id']+'|'+r['ranking_product']for r in chosen};assert len(top)==len(chosen)==170
 assert any(r['category']=='nick-chart-ppr-v1'and r['mechanism_id']=='empirical-history-control'for r in actual)
 old_current=json.loads((HERE/'current-valid-results/CURRENT_MANIFEST.json').read_bytes())
 assert [(x['sha256'],x['rows'],x['bytes'])for x in current['csv_parts']]==[(x['sha256'],x['rows'],x['bytes'])for x in old_current['csv_parts']]
 assert current['selected_ids']['sha256']==old_current['selected_ids']['sha256']
 for part in current['csv_parts']:assert sha(ROOT/part['path'])==part['sha256']
 assert sha(ROOT/current['selected_ids']['path'])==current['selected_ids']['sha256']
 result=dict(state='PASS_CURRENT_FIXED_2026_PANEL_PROCEDURE_RANKS_AND_TOP_FIVES',ranking_artifact=(ranking_root/'PROCEDURE_RANKINGS.json').relative_to(ROOT).as_posix(),ranking_sha256=sha(ranking_root/'PROCEDURE_RANKINGS.json'),top5_sha256=sha(ranking_root/'TOP5_BY_CATEGORY_PRODUCT.json'),builder_sha256=sha(args.builder),canonical_csv_and_ID_bytes_unchanged_from_independent_full_readback=True,candidate_output_views=len(candidates),procedure_product_representatives=len(actual),top5_rows=len(top),distinct_scientific_families=sorted({r['family_id']for r in actual}),source_artifact_sha256=source_hashes,scored_n_by_category={k:next(iter(v))for k,v in target_n.items()},top_five_boundary_ties=boundary_ties,checks=dict(checks),scope='Explicit previously row-verified full-primary2026W1W7sources only; source-bound exact-grid corrections retain originalnew-experiment lineage. Reported/provider/smaller-horizon/cohort/partial/zero-n records excluded from this tournament. Mean/median/history alternatives collapse perproceduremechanism/product; D1,D2,C02/objectives/trainingpopulation are distinct measuredprocedures, not newfamilies or seeds. MAE/genuine-meanMSE/proper-lawCRPS/Brier remain separate. Tieswithin1e-12retaincompetitionrank; exactlyfive are selected by deterministic mechanism order at boundary, with all ties visible in fullranking. Source prediction/label math was independently verified in earlier retained-row reviews; no new NFL replay here.',new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
 (HERE/'CURRENT_PROCEDURE_RANKING_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
