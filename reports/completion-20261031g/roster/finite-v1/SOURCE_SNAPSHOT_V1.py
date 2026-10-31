"""Finite method/recipe reconciliation and saved-current-score projection, no scoring."""
import argparse,collections,csv,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import sha,now,write
from tools.numerical_championship import key,csvwrite
from tools.build_current_valid_view_v2 import recipe
D='reports/continuation-20261030d/current-ranking-v2/current-valid-results'
N='reports/championship-20261030f/numerical-v2'
INFO={
'empirical-history-control':('Earlier eligible own target mean/lower-median/event frequency; matching-position history then literal0 fallback; no NFLoptimizer.','nfl_v2/empirical_benchmark.py','reports/continuation-20261029/history-diagnostic-v1/FROZEN_PROTOCOL.json'),
'hgb-L1':('HGB absolute_error:64iterations/depth3/minleaf10/LR.05/L2=10/seed1701; countmax0projection, signedyards retained.','nfl_v2/hgb_control.py','reports/continuation-20261029/hgb-history-v1/FROZEN_PROTOCOL.json'),
'hgb-L2':('Same HGB settings, squared_error intendedmean objective; distinct objective procedure.','nfl_v2/hgb_control.py','reports/continuation-20261029/hgb-history-v1/FROZEN_PROTOCOL.json'),
'hgb-binary-logloss':('HGBClassifier log_loss, same64iteration settings; rushing/receivingTD eventprobability, not expectedTDcount.','nfl_v2/hgb_control.py','reports/continuation-20261029/hgb-history-v1/FROZEN_PROTOCOL.json'),
'ordered-leaf-cdf-base':('32ExtraTrees L2partitions/depth8/minleaf30/seed1701; equal-tree leafPMF95%+same-arm role/global supportprior5%; signed chartgrid adapter separately bound.','nfl_v2/distribution_wave_v2.py','reports/continuation-20261030/distribution-wave-v2/FROZEN_PROTOCOL.json'),
'regularized-glm-law':('CountsPoissonRegressor alpha10; signedRidge alpha10 then roundedlocation+pooleddiscreteLaplace scale; binaryLogistic C.1;maxiter100/tol1e-6; chartgrid adapter separately bound.','nfl_v2/distribution_wave_v2.py','reports/continuation-20261030/distribution-wave-v2/FROZEN_PROTOCOL.json'),
'hgb-poisson-objective-point':('HGB Poisson objective, same64iteration settings; intendedmean point only, no authenticated law.','nfl_v2/count_ablations.py','reports/continuation-20261030/count-ablation-wave-v1/FROZEN_PROTOCOL.json'),
'hgb-L1-QB-RB-training':('HGB absolute-error with QB/RB training for rush_att; WR/TE query losses retained; no implicit role router.','nfl_v2/count_ablations.py','reports/continuation-20261030/count-ablation-wave-v1/FROZEN_PROTOCOL.json'),
'leaf-cdf-without-explicit-lag-block':('Same Leaf-CDF; remove4lag value/age/missing triplets+imputationflags; retain mean3/n3/mean8/n8+position; unchanged fit/prior/fallback.','nfl_v2/ordered_information_ablation.py','reports/continuation-20261030b/ordered-information-ablation-v1/FROZEN_PROTOCOL.json'),
'leaf-cdf-observed-defense-D1':('Same Leaf-CDF plus four observed opponent-position groups qualified target totals/coverage; NOT four scheduled teamgames.','nfl_v2/qualified_defense_wave.py','reports/continuation-20261030c/qualified-defense-information-v1/FROZEN_PROTOCOL.json'),
'leaf-cdf-observed-defense-D2':('D1 plus compatible-exposure rate/κ20league shrinkage/deviation/coverage/age; same learner/train/prior/fallback.','nfl_v2/qualified_defense_wave.py','reports/continuation-20261030c/qualified-defense-information-v1/FROZEN_PROTOCOL.json')}

def main(a):
 root=a.root;out=a.output
 if out.exists():raise ValueError('fresh immutable projection required')
 out.mkdir(parents=True);manifest=root/D/'CURRENT_MANIFEST.json';m=json.loads(manifest.read_bytes());allprocs=collections.Counter();known=collections.defaultdict(list);full={};bindings=[]
 for part in m['csv_parts']:
  path=root/part['path']
  if sha(path)!=part['sha256']:raise ValueError('canonical shard changed')
  bindings.append(dict(path=part['path'],sha256=part['sha256']))
  with path.open()as f:
   for r in csv.DictReader(f):
    allprocs[r['procedure_id']]+=1;mech=recipe(r)
    if mech:known[mech[1]].append(r)
    if not mech or r['season']!='2026'or r['week']!='ALL'or r['population']!='primary'or r['position']not in('','ALL')or r['fallback_view']not in('','ALL')or r.get('cohort_id')or json.loads(r['evaluation_weeks'])!=list(range(1,8)):continue
    if r['evidence']!='NEW_EXPERIMENT'and r['source_artifact']!='reports/continuation-20261030/chart-grid-precision-correction-v1/SCORES.json':continue
    k=key(dict(r,target=r['category']))
    if k in full:raise ValueError('duplicate canonical exact current recipe')
    full[k]=r
 grid=json.loads((root/N/'NUMERICAL_COVERAGE_GRID.json').read_bytes());current=[]
 def number(v):
  if v in(None,''):return None
  x=float(v);return x if math.isfinite(x)else'Infinity'if x>0 else'-Infinity'
 for base in grid:
  if base['season']!=2026:continue
  r=full.get(key(base));z=dict(base,procedure_kind='FIXED_FORECAST_RECIPE',comparison_scope='Fixed2026REGW1-7 primary participant/statrow; not authentic offer universe',source_test_id=r['test_id']if r else None)
  if r:
   z['source_artifact']=r['source_artifact']
   for metric in('mae','mse','rmse','bias','p90_abs','p95_abs','max_abs','brier','crps','nll','log_loss'):z[metric]=number(r.get(metric))
   z['precision_counts']={name:dict(numerator=v[0],denominator=v[1],rate=v[0]/v[1]if v[1]else None)for name,v in json.loads(r['precision_counts']or'{}').items()};z['n']=int(r['n']);z['forecast_rows']=int(r['forecast_or_offered_rows'])if r['forecast_or_offered_rows']else None;z['fallback_rows']=int(r['fallback_rows'])if r['fallback_rows']else 0;z['fallback_rate']=z['fallback_rows']/z['forecast_rows']if z['forecast_rows']else None;z['evidence']=r['evidence'];z['metric_nonfinite_status']=json.loads(r['nonfinite_status']or'{}')
  else:z.update(precision_counts=None,evidence='UNSCORED_EXACT_CURRENT_RECIPE',null_reason=base['missing_reason'])
  current.append(z)
 selectors=json.loads((root/'reports/championship-20261030f/category-selector-v2/SCORES.json').read_bytes())
 for r in selectors:current.append(dict(r,procedure_kind='COMPOSITE_EARLIER_ONLY_CATEGORY_SELECTION_POLICY',state='COMPLETED_VALID',comparison_scope='Separate exposed earlier-only policy product, not new learner',source_artifact='reports/championship-20261030f/category-selector-v2/SCORES.json',source_test_id=r['record_id']))
 write(out/'CURRENT_METHOD_COMPARISONS.json',current);csvwrite(out/'CURRENT_METHOD_COMPARISONS.csv',current)
 roster=[]
 for mech,rr in sorted(known.items()):
  formula,code,config=INFO[mech];roster.append(dict(roster_id='PROC:'+mech,unit_kind='FIXED_DISTINCT_SCIENTIFIC_MECHANISM',mechanism_id=mech,family_id=recipe(rr[0])[0],procedure_aliases=sorted({r['procedure_id']for r in rr}),formula=formula,code=code,code_sha256=sha(root/code),config=config,config_sha256=sha(root/config),targets=sorted({r['category']for r in rr}),history_regimes=sorted({r['history_regime']for r in rr}),products=sorted({r['product_id']for r in rr}),numerical_seasons=sorted({int(r['season'])for r in rr if r['season'].isdigit()}),feature_memory_policies=sorted({r['information_policy']for r in rr if r.get('information_policy')}),input_policy='Pinned NFLverse stats/identities/schedules, current-vintage seven-day availability assumption; chart16-component policy separate; no market/injury/tracking/routes.',calibration='NONE; architecture/settings exposed historical research; parametriclaw assumptions and rolepriors are partof recipe.',fallback='Source-specific same-arm empirical or fixed-fit role/global law prior, literal0/startup asregistered. Fullsystem/commonlearned both retained. STRICT excludes older fittedpriors.',update_rule='Trainable learners once before earliest weekly kickoff; queryfeatures ownkickoff; empirical prefix refresh eachquery. Strict original HGB147origins remain prepared, not fitted.',information_tier='FOOTBALL_CURRENT_VINTAGE_RECONSTRUCTION; originalcapture and newGqualified-retained-context tiers separate',horizon='Historical ownkickoff; Gknown-target-time earlier-asof equality is a newlyregistered reconstruction, never original issuance.',evaluation_views=len(rr),source_artifacts=sorted({r['source_artifact']for r in rr}),status='IMPLEMENTED_SCORED_EXACT_CELL_GAPS_PRESERVED'))
 extra=[('qualified-query-freshness-B','nfl_v2/availability_wave.py','reports/continuation-20261030b/availability-wave-v1/FROZEN_PROTOCOL.json','CAPTURED_UNSCORED','Keep A fitted model/prior; qualified fresher query features only.'),('qualified-query-plus-refit-C','nfl_v2/availability_wave.py','reports/continuation-20261030b/availability-wave-v1/FROZEN_PROTOCOL.json','CAPTURED_UNSCORED','Separate qualified-fresh features plus refit policy versus B; old99Cfits/captures reused.'),('scheduled-team-game-D1','nfl_v2/scheduled_defense_wave.py','reports/continuation-20261030d/scheduled-defense-fit-prepared-v3/REUSE_PLAN.json','IMPLEMENTED_NOT_FITTED_RETENTION_GATE','Four scheduled teamgames with absent-position-group missingness; selective reuse/refit plan.'),('scheduled-team-game-D2','nfl_v2/scheduled_defense_wave.py','reports/continuation-20261030d/scheduled-defense-fit-prepared-v3/REUSE_PLAN.json','IMPLEMENTED_NOT_FITTED_RETENTION_GATE','Scheduled D2 window, distinct from observed-position D2.')]
 for mid,code,config,state,formula in extra:roster.append(dict(roster_id=mid,unit_kind='DISTINCT_IMPLEMENTED_INFORMATION_UPDATE_PROCEDURE',mechanism_id=mid,code=code,code_sha256=sha(root/code),config=config,config_sha256=sha(root/config),formula=formula,status=state,new_family=False))
 for policy in('FROZEN_2025_BEST','EARLIER_AVAILABLE_2026_SCORE_MEMORY','POOLED_2025_AND_AVAILABLE_2026_MEMORY'):roster.append(dict(roster_id='SELECTOR:'+policy,unit_kind='COMPOSITE_SELECTION_POLICY_NOT_NEW_LEARNER',mechanism_id=policy,code='tools/chronological_category_selector.py',config='reports/championship-20261030f/category-selector-v2/FROZEN_PROTOCOL.json',targets=sorted({r['target']for r in selectors}),status='SCORED_EXPOSED_EARLIER_ONLY_POLICY',formula='Native MAE/Brier weighted by eligible n; wholeweeks lastkickoff+7d<origin, LeafMULTIstartup,tie1e-12stableID. No hindsight weeklywinner.'))
 write(out/'FINITE_IMPLEMENTED_PROCEDURE_ROSTER.json',roster);csvwrite(out/'FINITE_IMPLEMENTED_PROCEDURE_ROSTER.csv',roster)
 old=json.loads((root/'reports/inventory/ALL_METHOD_SCORES.json').read_bytes());years={r['record_id']:r for r in json.loads((root/'reports/inventory/METHOD_YEAR_INVENTORY.json').read_bytes())};legacy=collections.defaultdict(list)
 for r in old:legacy[r['procedure_label']].append(r)
 references=json.loads((root/'registries/PROCEDURE_REFERENCES.json').read_bytes());refby=collections.defaultdict(list)
 for r in references:refby[r['procedure_label']].append(r['reference_id'])
 lrows=[]
 for label,rr in sorted(legacy.items()):lrows.append(dict(procedure_label=label,unit_kind='LEGACY_LABEL_REFERENCE_NOT_ASSUMED_DISTINCT_LEARNER',canonical_procedure_id=None,state='EXACT_ORIGINAL_CODE_CONFIG_ROWS_CONTRACT_RECONCILIATION_REQUIRED',targets=sorted({r['target']for r in rr}),products=sorted({r['product_id']for r in rr}),source_ids=sorted({r['source_id']for r in rr}),reported_record_ids=[r['record_id']for r in rr],evaluation_seasons=sorted({y for r in rr for y in years[r['record_id']]['evaluation_seasons']}),period_literals=sorted({str(years[r['record_id']]['evaluation_period_literal'])for r in rr}),limits=list({json.dumps(r.get('limits_or_aliases'),sort_keys=True):r.get('limits_or_aliases')for r in rr if r.get('limits_or_aliases')}.values()),reference_ids=refby[label],next_action='Inspect exact pinned source/config/row capsule; preserve source-specific losses. Reconstruct executable recipes under new identities; missing originals block only their issuance/reproduction claims. No history-grid padding or blind V2 alias.',evidence='REPORTED_NOT_REPRODUCED'))
 write(out/'LEGACY_LABEL_RECONCILIATION.json',lrows);csvwrite(out/'LEGACY_LABEL_RECONCILIATION.csv',lrows)
 census=[dict(procedure_string=p,evaluation_views=n,mechanism=recipe(dict(procedure_id=p))[1]if recipe(dict(procedure_id=p))else None,legacy_label_present=p in legacy,disposition='IMPLEMENTED_MECHANISM_ALIAS_POLICY_OR_OUTPUT_REFERENCE'if recipe(dict(procedure_id=p))else'LEGACY_LABEL_TRACE'if p in legacy else'RETAINED_OR_ADDITIONAL_REFERENCE_REQUIRES_EXACT_CONTRACT')for p,n in sorted(allprocs.items())];write(out/'ALL_CURRENT_PROCEDURE_STRING_CENSUS.json',census);csvwrite(out/'ALL_CURRENT_PROCEDURE_STRING_CENSUS.csv',census)
 admissions=json.loads((a.admission/'THRESHOLD_ADMISSIBILITY.json').read_bytes());adm={(r['target'],r['procedure_id'],r['history_regime'],r['product_id']):r for r in admissions};fg=[]
 for r in grid:
  ad=adm.get((r['target'],r['procedure_id'],r['history_regime'],r['product_id']))if r['season']==2026 else None;fg.append(dict(r,selection_period='2026W7fixed13gameFthresholds only'if ad else None,P1_state='PARTIAL_W7_ADMITTED_RECONSTRUCTION'if ad and ad['P1_admissible']else'NO_ADMITTED_ROWS'if ad else'NO_MATCHING_THRESHOLD_PANEL_IN_THIS_INSPECTED_GRID',P1_rows=ad['P1_admissible']if ad else None,offer_universe=ad['eligible_offer_universe']if ad else None,P2_rows=ad['P2_complete_law_admissible']if ad else None,selection_dependency='GrollingW6/W7qualifiedsource panels separate, adapter running/completed. Older offers unlocated within inspected source scope; no global absence claim.'if not ad else'Use frozen G admission/selection/missing-support masks; this partialW7 panel does not completeW1-7actual-line comparison.'))
 write(out/'FINITE_RECIPE_CATEGORY_PERIOD_PRODUCT_GRID.json',fg);csvwrite(out/'FINITE_RECIPE_CATEGORY_PERIOD_PRODUCT_GRID.csv',fg)
 counts=dict(state='FINITE_SOURCE_BOUND_RECONCILIATION_NO_NEW_SCORES',at=now(),source_manifest=dict(path=manifest.relative_to(root).as_posix(),sha256=sha(manifest)),source_shards=bindings,current_valid_views=m['selected_evaluation_views'],current_procedure_strings=len(allprocs),known_scientific_mechanisms=len(known),raw_implemented_procedure_strings=len({r['procedure_id']for rr in known.values()for r in rr}),normalized_fixed_recipe_procedure_strings=len({r['procedure_id']for r in grid}),fixed_current_union_rows=sum(r['procedure_kind']=='FIXED_FORECAST_RECIPE'for r in current),current_fixed_completed=sum(r['procedure_kind']=='FIXED_FORECAST_RECIPE'and r['state']=='COMPLETED_VALID'for r in current),separate_composite_target_products=len(selectors),legacy_labels=len(lrows),reported_aggregate_views=len(old),legacy_reference_records=len(references),finite_recipe_period_cells=len(fg),F_representatives=237,F_selected_specs=982,F_selector_output_recipes=120,new_fits=0,new_scores=0,new_forecasts=0,lifetime_census_complete=False,denominator_note='Procedure strings/aliases, scientific mechanisms, target/history/output recipes, source references and evaluation views are different counts. No completionpercentage or every-method-ever claim.')
 write(out/'ROSTER_RECONCILIATION_RECEIPT.json',counts);print(json.dumps({k:v for k,v in counts.items()if k!='source_shards'}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);p.add_argument('--admission',type=Path,required=True);main(p.parse_args())
