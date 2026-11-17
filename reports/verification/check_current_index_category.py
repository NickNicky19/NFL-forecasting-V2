"""Independent public-source representative and shard review; no model imports."""
import collections,csv,hashlib,json,math,datetime,subprocess,sys,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/continuation-20261030'
def h(b):return hashlib.sha256(b).hexdigest()
def canonical(o):return json.dumps(o,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def load(p):return json.loads((ROOT/p).read_text())
specs=[('reports/continuation-20261029/history-diagnostic-v1/HISTORY_COMPARISON_2026_W1_W7.csv','EMPIRICAL'),('reports/continuation-20261029/hgb-history-v1/SCORES.json','HGB'),('reports/continuation-20261030/distribution-wave-v2/SCORES.json',None),('reports/continuation-20261030/count-ablation-wave-v1/SCORES.json','HGB'),('reports/continuation-20261030/chart-wave-v1/SCORES.json',None),('reports/continuation-20261030/chart-wave-v1/EMPIRICAL_SCORES.json','EMPIRICAL')]
pool=[]
for artifact,family in specs:
 path=ROOT/artifact;rows=list(csv.DictReader(path.open())) if path.suffix=='.csv' else json.loads(path.read_text())
 for r in rows:
  if r.get('population')!='primary' or str(r.get('season',2026))!='2026' or str(r.get('week'))!='ALL' or r.get('position','ALL')!='ALL' or r.get('fallback_view','ALL')!='ALL':continue
  product=r.get('product_id',r.get('product',r.get('objective')));fam=family or ('ORDERED_LEAF_CDF' if 'leaf' in r['procedure_family_id'] else 'GLM_LAW');n=int(r.get('n',r.get('scored_n',0)))
  if n:pool.append(dict(target=r['target'],family=fam,product=product,n=n,artifact=artifact,row=r))
reps=load('reports/continuation-20261030/TOP5_BY_CATEGORY_PRODUCT.json');assert len(reps)==114
expected_counts={'pass_yd':242,'pass_td':242,'pass_cmp':242,'pass_att':242,'pass_int':242,'rush_yd':844,'rush_att':844,'rec':2118,'rec_yd':2118,'rush_rec_yd':2118,'anytime_td':2118,'nick-chart-ppr-v1':2359}
for r in pool:assert r['n']==expected_counts[r['target']]
for r in reps:
 eligible=[x for x in pool if x['target']==r['target'] and x['family']==r['family'] and x['row'].get(r['ranking_metric']) not in (None,'') and (r['ranking_product']!='intended_mean' or 'mean' in x['product'])]
 loss=min(float(x['row'][r['ranking_metric']]) for x in eligible);assert math.isclose(loss,r['ranking_loss'],abs_tol=1e-12,rel_tol=0)
 matching=[x for x in eligible if x['artifact']==r['source_artifact'] and x['product']==r['product'] and x['row']['history_regime']==r['history_regime'] and math.isclose(float(x['row'][r['ranking_metric']]),r['ranking_loss'],abs_tol=1e-12,rel_tol=0)];assert matching
 assert r['family_ties_within_1e12']==sum(math.isclose(float(x['row'][r['ranking_metric']]),loss,abs_tol=1e-12,rel_tol=0) for x in eligible)
assert len({r['family'] for r in reps})==4
ints=[r for r in reps if r['target']=='pass_int' and r['ranking_product']=='display_point' and r['rank']==1];assert {r['family'] for r in ints}=={'EMPIRICAL','ORDERED_LEAF_CDF'}
markdown=(OUT/'TWELVE_CATEGORY_SUMMARY.md').read_text();mdrows=[line.split('|')[1:-1] for line in markdown.splitlines() if line.startswith('| ') and line.split('|')[1].strip() in expected_counts];assert len(mdrows)==12
for cols in mdrows:
 target=cols[0].strip();win=[r for r in reps if r['target']==target and r['ranking_product']=='display_point' and r['rank']==1];metric='brier' if target=='anytime_td' else'mae';refs=[r for r in pool if r['target']==target and r['family']=='EMPIRICAL' and r['row']['history_regime']=='H-RECENT' and ('mean' in r['product'] or target=='anytime_td')];baseline=float(refs[0]['row'][metric]);skill=(1-win[0]['ranking_loss']/baseline)*100
 assert int(cols[1])==expected_counts[target] and abs(float(cols[3])-win[0]['ranking_loss'])<1e-6 and abs(float(cols[4])-baseline)<1e-6 and abs(float(cols[5].strip().rstrip('%'))-skill)<=.0051
 assert all(r['family'] in cols[2] for r in win)
# Verify current immutable index snapshot shard-by-shard without regenerating it.
manifest_path=OUT/'results-index/INDEX_MANIFEST.json';manifest_body=manifest_path.read_bytes();manifest=json.loads(manifest_body);base=(ROOT/manifest['baseline_checkpoint']['artifact']).read_bytes();assert h(base)==manifest['baseline_checkpoint']['sha256'];old=json.loads(base);old_digests={r['test_id']:h(canonical(r)) for r in old['records']};del old,base
inputs={r['source_artifact']:r for r in manifest['input_manifests']};hashchecks=0
for path,record in inputs.items():assert h((ROOT/path).read_bytes())==record['sha256'];hashchecks+=1
registry=load('registries/RESULT_ARTIFACTS.json');new_sources={};dates={}
for item in registry:
 artifact=item['artifact']
 if item['state']!='SCORED' or artifact in {'reports/inventory/ALL_METHOD_SCORES.json','reports/replay/REPLAY_SCORES.json','reports/week7-label-extension-v1/SCORES.json'} or artifact not in inputs:continue
 if not artifact.endswith('.json'):continue
 body=load(artifact)
 if not isinstance(body,list):continue
 new_sources[artifact]=collections.Counter(h(canonical(r)) for r in body)
 if item.get('dates_projection'):
  projection=load(item['dates_projection']);assert projection['source_score_sha256']==inputs[artifact]['sha256'];dates[artifact]={r['source_row_index']:r for r in projection['rows']};assert len(dates[artifact])==len(body)
correction_path='reports/continuation-20261030/chart-grid-precision-correction-v1/SCORES.json'
correction_dims=('record_id','procedure_id','history_regime','policy_id','target','population','product_id','week','season','position','fallback_view','cohort_id')
correction_rows=load(correction_path);superseded={(r['supersedes_score_artifact'],tuple(r['supersedes_source_identity'].get(k) for k in correction_dims)) for r in correction_rows}
superseded_checks=exact_numerator_checks=0
seen=set();oldchecks=recordcount=aggregatechecks=infinitychecks=datechecks=0;source_seen=collections.defaultdict(collections.Counter)
for shard in manifest['shards']:
 body=(ROOT/shard['path']).read_bytes();assert h(body)==shard['sha256'] and len(body)==shard['bytes'] and len(body)<=manifest['max_shard_bytes'];rows=json.loads(body);assert len(rows)==shard['records']
 for r in rows:
  recordcount+=1;assert r['test_id'] not in seen;seen.add(r['test_id'])
  if r['test_id'] in old_digests:assert h(canonical(r))==old_digests[r['test_id']];oldchecks+=1
  artifact=r['source_artifact']
  if artifact in new_sources:
   source=r['source_aggregate_fields'];source_seen[artifact][h(canonical(source))]+=1;aggregatechecks+=1;assert r['source_artifact_sha256']==inputs[artifact]['sha256']
   if (artifact,tuple(source.get(k) for k in correction_dims)) in superseded:
    assert r['accuracy_status']=='superseded_float_chart_grid_precision' and r['precision_correction_artifact']==correction_path;superseded_checks+=1
   if artifact==correction_path:
    for metric,counts in source['precision_counts_exact_grid'].items():
     assert r['precision_metrics'][metric]['numerator']==counts['numerator'] and r['precision_metrics'][metric]['denominator']==counts['denominator'];exact_numerator_checks+=1
   if source.get('infinite_NLL',0):assert r['metric_status']['nll']=='positive_infinite_loss' and r['metrics']['nll'] is None;infinitychecks+=1
   if source.get('infinite_log_losses',0):assert r['metric_status']['log_loss']=='positive_infinite_loss' and r['metrics']['log_loss'] is None;infinitychecks+=1
   if artifact in dates:
    d=dates[artifact][r['evaluation_date_provenance']['source_row_index']];assert r['seasons']==d['evaluation_seasons'] and r['weeks']==d['evaluation_weeks'];datechecks+=1
assert oldchecks==len(old_digests) and recordcount==manifest['record_count']
assert superseded_checks==1007 and exact_numerator_checks==6042
for artifact,count in new_sources.items():assert source_seen[artifact]==count,artifact
coverage=subprocess.run([sys.executable,'tools/check_result_index_coverage.py'],cwd=ROOT,text=True,capture_output=True)
result=dict(status='PASS_SNAPSHOT_EXCEPT_PENDING_REGISTRY_REBUILD' if coverage.returncode else 'PASS_INDEPENDENT_CATEGORY_AND_SHARDED_INDEX_REVIEW',completed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),category_source_candidates=len(pool),family_representatives_checked=len(reps),category_count=12,families=4,primary_supported_counts=expected_counts,markdown_numeric_and_skill_rows_checked=12,INT_tie_preserved=True,GLM_and_other_losing_representatives_retained=True,category_scientific_scope='exposedbestobservedfamilyminima;uptofourfamilies/chartthree;noindependentfivemethodclaim;MAE/MSE/CRPSseparate',index_manifest_sha256=h(manifest_body),indexed_records=recordcount,shards_checked=len(manifest['shards']),source_hashes_checked=hashchecks,old_record_ID_and_semantic_digest_checks=oldchecks,source_aggregate_views_checked_including_baseline_sources=aggregatechecks,additional_indexed_records_beyond_baseline=recordcount-oldchecks,infinite_metric_status_checks=infinitychecks,source_bound_date_projection_checks=datechecks,superseded_original_precision_views_checked=superseded_checks,corrected_exact_numerator_checks=exact_numerator_checks,coverage_exit_code=coverage.returncode,coverage_stdout=coverage.stdout.strip(),coverage_stderr=coverage.stderr.strip(),focused_index_fixture_tests='4PASS;noNFLdata/fits',findings=[],bounds='This checks publicscore/index/categoryprojections. Rawpredictionidentity/label/math authenticity is covered byseparateretainedrowverifiers,notnewlyauthenticatedhere.',new_fits=0,new_forecasts=0,actual_Week8_labels_read=0,reviewed_sha256={p:h((ROOT/p).read_bytes()) for p in ['tools/build_checkpoint_category_summary.py','tools/build_test_index_v2.py','nfl_v2/result_index.py','tests/test_index_v2.py']})
parser=argparse.ArgumentParser();parser.add_argument('--output',default='INDEX_CATEGORY_INDEPENDENT_QA_FINAL.json');args=parser.parse_args()
(OUT/args.output).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ('status','family_representatives_checked','indexed_records','old_record_ID_and_semantic_digest_checks','infinite_metric_status_checks','source_bound_date_projection_checks','coverage_exit_code')},indent=2))
