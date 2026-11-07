"""Independent public-only ID/census/metric integration check; no model imports."""
from __future__ import annotations
import collections,csv,hashlib,json,math,subprocess,sys,datetime,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)
def stable_id(artifact,identity):return 'TEST-'+hashlib.sha256(canonical([artifact,identity]).encode()).hexdigest()[:20]
def load(path):return json.loads((ROOT/path).read_text())
def identity(r):
 return dict(source_record_id=r.get('record_id'),source_pointer=r.get('source_pointer'),procedure_id=r.get('procedure_id',r.get('procedure_label')),category=r.get('target'),product_id=r.get('product_id'),evaluation_panel_id=r.get('evaluation_panel_id'),population=r.get('population'),period=r.get('period'),season=r.get('season'),week=r.get('week'),history_regime=r.get('history_regime','UNKNOWN_NOT_H_CLASSIFIED'))
def main():
 index=load('reports/continuation-20261029/TEST_RESULTS_INDEX.json');records=index['records'];byid={r['test_id']:r for r in records};assert len(byid)==len(records)
 expected=set();legacy_counts={}
 for artifact in ['reports/inventory/ALL_METHOD_SCORES.json','reports/replay/REPLAY_SCORES.json','reports/week7-label-extension-v1/SCORES.json']:
  raw=load(artifact);legacy_counts[artifact]=len(raw)
  for r in raw:
   ident=identity(r)
   for key in ['position','fallback_view']:
    if r.get(key) is not None:ident[key]=r[key]
   tid=stable_id(artifact,ident);assert tid in byid;expected.add(tid)
 artifact='reports/continuation-20261029/history-diagnostic-v1/SEASON_RESULTS_2022_2026.csv'
 dims=('target','population','history_regime','product','season','week','position','fallback_view')
 with (ROOT/artifact).open(newline='') as f:raw=list(csv.DictReader(f))
 for r in raw:
  ident=dict(source_record_id=None,source_pointer='CSV dimensions: '+canonical({k:r[k] for k in dims}),procedure_id='empirical-player-history-control-v1',category=r['target'],product_id=r['product'],evaluation_panel_id='nflverse-observed-stat-row-2022-2026-current-vintage-diagnostic-v1',population=r['population'],period='REG',season=int(r['season']) if r['season'].isdigit() else None,week=int(r['week']) if r['week'].isdigit() else None,history_regime=r['history_regime'],position=r['position'],fallback_view=r['fallback_view'])
  tid=stable_id(artifact,ident);assert tid in byid;expected.add(tid)
 assert len(expected)==15118
 artifact='reports/continuation-20261029/hgb-history-v1/SCORES.json';scores=load(artifact);hgb=[r for r in records if r.get('source_artifact')==artifact];assert len(scores)==len(hgb)==930
 dims=('target','population','history_regime','objective','week','position')
 census=load('reports/verification/HGB_VIEW_GAME_COUNTS.json');games={tuple(str(r[k]) for k in dims):r for r in census['rows']};assert len(games)==930
 hi={tuple(str(r['source_aggregate_fields'][k]) for k in dims):r for r in hgb};assert len(hi)==930
 metrics=('mae','mse','rmse','bias','p90_abs','p95_abs','max_abs','brier','log_loss');metricchecks=0;precisionchecks=0;countchecks=0;gamechecks=0
 for s in scores:
  k=tuple(str(s[d]) for d in dims);r=hi[k];g=games[k]
  assert r['source_aggregate_fields']==s
  assert r['source_artifact_sha256']==hashlib.sha256((ROOT/artifact).read_bytes()).hexdigest()
  assert r['n']==s['scored_n'] and r['forecast_or_offered_rows']==s['forecast_queries'] and r['fallback_rows']==s['fallback_n'];countchecks+=3
  assert r['games']==g['scored_games'] and r['game_count_provenance']['forecast_games']==g['forecast_games'];gamechecks+=2
  for m in metrics:
   if m=='log_loss' and s.get('infinite_log_losses',0):
    assert r['metrics'][m] is None and r['metric_status'][m]=='positive_infinite_loss';assert r['source_infinite_nll_rows']==s['infinite_log_losses'];metricchecks+=1;continue
   assert r['metrics'][m]==s.get(m);metricchecks+=1
  for m in ['exact_rate','abs_lt_1','abs_le_1','abs_lt_5','abs_le_5','abs_lt_10','abs_le_10']:
   p=r['precision_metrics'][m];assert p['rate']==s[m] and p['denominator']==s['scored_n']
   if p['numerator'] is not None:assert math.isclose(p['numerator']/p['denominator'],s[m],rel_tol=0,abs_tol=1e-9)
   precisionchecks+=1
  assert r['primary_metric']==('brier' if s['target']=='anytime_td' else 'mae')
  assert r['feature_memory_policy'].endswith('not pure current information')
  assert r['kind']=='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC'
  assert 'distribution' not in r['product_id']
 pairs=load('reports/verification/HGB_PAIRED_COMPARISONS.json')['hgb_vs_empirical'];examples=[]
 for target,objective,want_sign in [('pass_yd','absolute_error_point',-1),('rush_att','absolute_error_point',1)]:
  p=next(p for p in pairs if p['target']==target and p['objective']==objective and p['history_regime']=='H-MULTI')
  r=hi[(target,'primary','H-MULTI',objective,'ALL','ALL')]
  assert r['n']==p['n'] and math.isclose(r['primary_error'],p['hgb_primary_error'],abs_tol=1e-10)
  assert math.copysign(1,p['hgb_minus_empirical'])==want_sign
  examples.append({'target':target,'objective':objective,'history_regime':'H-MULTI','index_test_id':r['test_id'],'n':r['n'],'hgb_mae':r['primary_error'],'empirical_matched_product_mae':p['empirical_primary_error'],'hgb_minus_empirical':p['hgb_minus_empirical']})
 proc=subprocess.run([sys.executable,'tools/check_result_index_coverage.py'],cwd=ROOT,capture_output=True,text=True);assert proc.returncode==0,proc.stdout+proc.stderr
 package=tomllib.loads((ROOT/'pyproject.toml').read_text());assert package['tool']['setuptools']['packages']['find']['include']==['nfl_v2*'];assert package['project']['optional-dependencies']['boosting']==['numpy==2.3.5','scikit-learn==1.8.0']
 workflow=(ROOT/'.github/workflows/research-checks.yml').read_text()
 for text in ["permissions:\n  contents: read","timeout-minutes: 10","python -m pip install '.[boosting]'","python -m unittest discover -s tests -v","python tools/validate_checkpoint.py","python tools/check_result_index_coverage.py"]:assert text in workflow
 for prohibited in ['schedule:','workflow_dispatch:','hgb_control_run.py','run_week8_shadow.py','run_empirical_benchmark.py']:assert prohibited not in workflow
 output={'status':'PASS_PUBLIC_INDEX_HGB_INTEGRATION_WITH_LIMITS','completed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'index_records':len(records),'evaluation_views':sum(r['kind']!='software_verification' for r in records),'software_receipts':sum(r['kind']=='software_verification' for r in records),'pre_hgb_evaluation_ids_rederived_and_present':len(expected),'old_id_verification_scope':'Independent reconstruction of pre-HGB ID recipe from immutable original aggregates and explicit diagnostic dimensions; no archived previous complete-index byte snapshot was supplied.','legacy_aggregate_counts':legacy_counts,'hgb_views':len(hgb),'game_census_views':len(games),'hgb_count_checks':countchecks,'hgb_game_count_checks':gamechecks,'hgb_metric_checks':metricchecks,'hgb_precision_checks':precisionchecks,'source_aggregate_preservation_checks':len(hgb),'win_loss_mapping_examples':examples,'coverage_command':json.loads(proc.stdout),'ci_packaging_checks':'explicitnfl_v2package discovery; Python3.12 and pinnedboostingextras; checkout/read-onlyCI runssoftware/coverage checks, no scheduler or NFLfit/captureCLI','wheel_build':'REPORTED_BY_ROOT_PASSED_NOT_REBUILT_BY_THIS_REVIEW','new_nfl_fits':0,'new_forecasts':0,'new_outcomes':0,'limits':['Public aggregate/index integration review; original NFL label truth and retained model inference independently reviewed elsewhere.','Future max_forecast_rows guard remains a separate versioned patch; frozen v1 source unchanged.'],'reviewed_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['tools/build_test_index.py','nfl_v2/result_index.py','tools/check_result_index_coverage.py','pyproject.toml','.github/workflows/research-checks.yml','reports/continuation-20261029/TEST_RESULTS_INDEX.json','reports/verification/HGB_VIEW_GAME_COUNTS.json']}}
 out=ROOT/'reports/verification/INDEX_HGB_INTEGRATION_QA.json';out.write_text(json.dumps(output,indent=2)+'\n');print(json.dumps(output,indent=2))
if __name__=='__main__':main()
