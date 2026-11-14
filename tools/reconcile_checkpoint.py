import csv,json,pathlib,hashlib,collections,shutil,argparse
ROOT=pathlib.Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description='Generate an initial projection in a NEW staging directory, never overwrite canonical checkpoint registries.')
parser.add_argument('--staging-dir',type=pathlib.Path,required=True)
args=parser.parse_args();P=args.staging_dir.resolve()
if P==ROOT or ROOT in P.parents or P.exists():raise SystemExit('Use a new staging directory outside the repository; canonical outputs are immutable')
P.mkdir(parents=True);R=P/'reports';G=P/'registries';G.mkdir();R.mkdir()
shutil.copytree(ROOT/'reports/inventory',R/'inventory');shutil.copytree(ROOT/'reports/replay',R/'replay')
def write(name,rows,where=R):
 (where/(name+'.json')).write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
 keys=list(dict.fromkeys(k for x in rows for k in x))
 with (where/(name+'.csv')).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
  w.writerows({k:json.dumps(v,separators=(',',':')) if isinstance(v,(dict,list)) else v for k,v in x.items()} for x in rows)
T=['pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','nick-chart-ppr-v1','anytime_td']
menus={
'pass_yd':('PY',['Direct CDF/quantile boosting plus isolated QB/receiver availability and matchup group','Joint uncertain attempts, completions and signed gains, volume/gain ablations','Conditional changing-spread and explosive-tail distribution on identical inputs','TabICLv2 median then distinct qualified learned retrieval versus analog controls','Authenticated market-only and restrained football correction, multiple-line assumptions']),
'pass_att':('PA',['Ordered direct count CDF and separate QB playing-time group','Team opportunities/dropbacks/attempts/sacks/scrambles with uncertain QB shares','Partially pooled dynamic team/QB tendency and predicted conditions','Qualified TabICLv2 or learned role retrieval versus fixed analogs','Count market and restrained corrections; separate line-as-point control']),
'pass_cmp':('PC',['Direct CDF/absolute boosting plus isolated receiver catch-quality group','Conversion conditional on forecast attempt law with reversible fixed-law ablations','Throw-difficulty/type mixture and shrunk QB effect using qualified NGS/FTN','Coherent joint passing allocation versus marginals on identical information','Market-only/small hybrid completion CDF and chronological football-law blend']),
'pass_td':('PT',['Regularized direct count CDF with scoring role and zero mass','Field-position/opportunity process passing versus rushing/other and explosive scores','Pooled conversion conditional on predicted completions/location mix','Qualified QB/receiver full/limited/substitution scenarios, unchanged-learner ablation','Qualified count market with small correction and coherent multi-threshold probabilities']),
'pass_int':('PI',['Count CDF/regularized risk with exposure/current role; zero/pooled controls','Risk under forecast attempts, depth and projected pressure with pooled effects','Precisely new risky-throw/conversion hypothesis; otherwise reuse prior FTN losses','Joint passing outcome allocation with fixed-risk-marginal ablation','Market/blended zero/one/multiple interception probabilities; no MAE-only selection']),
'rush_att':('RA',['Ordered/count boosting with isolated role/replacement/teammate groups','Dynamic finite team-run/backfield allocation with uncertain totals and shares','Forward-filtered role changepoints versus recency weights','Permitted participation or explicitly named carry shares; separate QB run types','Learned role analogs or capped relevance training versus fixed analogs and markets']),
'rush_yd':('RY',['Direct median/CDF boosting using identical role/carry information','Uncertain carries compounded with signed loss/zero/ordinary/explosive gains','Prior opportunity quality and shrunk execution/opponent using eligible prior NGS','Qualified TabICLv2 median and bounded learned retrieval with sparse-role fallbacks','Market curve/point correction and conservative combinations versus strong controls']),
'rec':('R',['Ordered count CDF with current competition/QB/teammate information','Targetable pass volume, finite targets and catch conversion; no-credited-target bucket','True routes, targets per route and catches versus snap/share controls','Qualified lagged catchability/drop/type conversion holding target law fixed','Distinct TabICLv2, learned retrieval and restrained stack variants with count markets']),
'rec_yd':('REY',['Direct CDF/quantile with ordered targets and role/QB/teammate group','Target-type, catches and signed gain process sharing volume/quality uncertainty','Air-gain and YAC opportunity separated from pooled residual execution','Qualified TabICLv2/retrieval versus categorical/distribution boosting controls','Authenticated alternate-line distribution/correction; quote path versus same-cutoff static']),
'rush_rec_yd':('RR',['Direct-total CDF/quantile with current role information','Shared role/game-state joint carries/targets and common draws','Multivariate conditional production law versus same-row direct total','Regularized reconciliation/dependence with fixed marginals; preserve copula losses','Direct/derived distribution mixture and distinct compatible market extension']),
'anytime_td':('AT',['Direct CatBoost/CDF/logistic plus isolated qualified goal-line/end-zone roles','Team offensive TD opportunities allocated by player/field position, including explosive','Full/limited/replacement event mixture using 1-E[exp(-Lambda)]','Pooled exposure/conversion over uncertain carries/targets with credited events','Same-contract Yes/No reference and constrained calibration/small correction']),
'nick-chart-ppr-v1':('PPR',['Exact-chart Leaf-CDF median/distribution control','Finite direct HGB/CatBoost/LightGBM/XGBoost absolute/quantile library','Qualified TabICLv2 or proper signed-score law with distinct mean/median products','Exact chart on coherent joint components including rare credits; separate mean sum','Chronological direct/component-law blend with shrunk earlier-OOF role weights'])}
requests=[]
for target,(prefix,options) in menus.items():
 for i,text in enumerate(options,1):
  requests.append(dict(request_id=prefix+str(i),delivery='DIRECT_USER_INSTRUCTION_THIS_SESSION',amendment_group='CONTROLLING_V2_20261029',target=target,requested_mechanism=text,procedure_id=None,equivalence_status='LEGACY_EQUIVALENCE_REVIEW_REQUIRED',completion_condition='Qualified source/chronology, exact procedure and variants registered; core histories scored or exact dependency retained; forecast rows recoverable; independent scoring; release separate',status='PROPOSED_NOT_COMPLETED',seasons=[2022,2023,2024,2025,2026],source_id='OWNER-V2-20261029'))
for i in range(1,15):requests.append(dict(request_id=f'Q{i:02}',delivery='DIRECT_USER_INSTRUCTION_THIS_SESSION',requested_mechanism=f'Answer question {i} with code, numbers, limits and next test',source_id='OWNER-V2-20261029',status='CHECKPOINT_ANSWER_WRITTEN_NOT_FULL_TOURNAMENT_COMPLETE'))
for id,mechanism in [('HISTORY-A','Fixed 2026 W1-W7 fit-window comparison with same features and separate strict-current-information'),('HISTORY-B','Rolling-origin 2022-2026 season/week robustness'),('PHASE-ZERO','Requests/runs/forecasts/labels/artifacts bidirectional census'),('TOP5','Up to five distinct verified comparable procedures/category/product/tier'),('HANDOFF','Reviewable package and retained-owner-only capture/release'),('OFFERS','Authenticated offered thresholds, frozen selections, coherent push/void/price analysis')]:
 requests.append(dict(request_id=id,delivery='DIRECT_USER_INSTRUCTION_THIS_SESSION',requested_mechanism=mechanism,status='PARTIAL_OR_BLOCKED',source_id='OWNER-V2-20261029'))
write('REQUEST_METHOD_CROSSWALK',requests,G)
legacy=json.loads((R/'inventory/ALL_METHOD_SCORES.json').read_text());replay=json.loads((R/'replay/REPLAY_SCORES.json').read_text())
all_scores=legacy+[dict(x,record_id=f'V2R-{i:03}',source_id='REPLAY-RETAINED-W7',new_fits_in_V2=0,new_NFL_scores_in_V2=x['n']) for i,x in enumerate(replay,1)]
write('ALL_METHOD_SCORES',all_scores)
years=json.loads((R/'inventory/METHOD_YEAR_INVENTORY.json').read_text())
years += [dict(record_id=f'V2R-{i:03}',procedure_id=x['procedure_id'],target=x['target'],product_id=x['product_id'],population=x['population'],evaluation_panel_id=x['evaluation_panel_id'],evaluation_seasons=[2026],evaluation_weeks=[7],scored_rows=x['n'],unique_games=x['unique_games'],train_seasons=None,tune_seasons=None,calibrate_seasons=None,feature_memory_seasons=None,dates_reason='Saved rows replayed; full original fitted input history not restored',status='REPRODUCED_FROM_DATA') for i,x in enumerate(replay,1)]
write('METHOD_YEAR_INVENTORY',years)
# Preserve raw labels as references, NOT canonical method counts.
refs={}
for x in legacy:
 key=(x['source_id'],x['procedure_label'],x['target'],x['product_id'])
 refs.setdefault(key,dict(reference_id='LREF-'+hashlib.sha256(json.dumps(key).encode()).hexdigest()[:14],source_id=x['source_id'],procedure_label=x['procedure_label'],target=x['target'],product_id=x['product_id'],canonical_procedure_id=None,canonicalization='UNRESOLVED_label_may_alias_other_sources_or_views'))
write('PROCEDURE_REFERENCES',list(refs.values()),G)
grid=[]
for x in refs.values():
 for h in ['H-CURRENT','H-RECENT','H-MULTI']:
  fixed=any(s in x['procedure_label'].lower() for s in ['raw_sleeper','original_site','pinned_website','actual_site'])
  grid.append(dict(cell_id=f"{x['reference_id']}-{h}",procedure_reference_id=x['reference_id'],procedure_id=None,procedure_label=x['procedure_label'],target=x['target'],product_id=x['product_id'],history_regime=h,evaluation_panel_id='2026-REG-W1-W7-fixed-v1',information_tier='SOURCE_SPECIFIC_UNQUALIFIED_FOR_V2_GRID',feature_memory=None,startup_policy=None,history_applicability='REVIEW_REQUIRED' if not fixed else 'POTENTIALLY_NA_FIXED_ARCHIVE_CONFIRM_ADAPTER',status='INACCESSIBLE_PENDING_CONTRACT' if not fixed else 'NOT_RETRAINABLE_IF_FIXED_ARCHIVE',reason='Exact original input/fitted-feature contract, qualified 2026 W7 full query/outcomes and private artifact restoration unavailable; label-reference deduplication required before allocating fits' if not fixed else 'An original fixed provider/site forecast is not retrainable; preserve exact original scores; verify reference identity',fit_count=None,score=None,source_id=x['source_id']))
for x in requests[:60]:
 for h in ['H-CURRENT','H-RECENT','H-MULTI','STRICT-CURRENT-INFORMATION']:
  grid.append(dict(cell_id=x['request_id']+'-'+h,request_id=x['request_id'],procedure_id=None,target=x['target'],product_id='event_probability' if x['target']=='anytime_td' else 'display_point_MAE_and_separate_mean_distribution',history_regime=h,evaluation_panel_id='2026-REG-W1-W7-fixed-v1',status='PROPOSED_EQUIVALENCE_AND_SOURCE_ADMISSION_REQUIRED',reason='Pathway is not a completed procedure; first map legacy equivalents, then freeze exact variants, source prerequisites and bounded wave. No unqualified route/market/external-prior data admitted.',fit_count=0,score=None))
write('EXPERIMENT_GRID',grid,G)
# Requested history table intentionally contains nulls; never fill with W1-W6 or legacy recent/pooled.
history=[dict(cell_id=x['cell_id'],procedure_reference_id=x.get('procedure_reference_id'),request_id=x.get('request_id'),target=x['target'],product_id=x['product_id'],history_regime=x['history_regime'],evaluation_panel_id=x['evaluation_panel_id'],paired_rows=None,loss=None,feature_memory=None,startup=None,status=x['status'],reason=x['reason']) for x in grid]
write('HISTORY_COMPARISON_2026_W1_W7',history)
# Numeric season records remain scoped to the original exact panels, not falsely rolling-origin.
season=[]
for x in all_scores:
 if x.get('period') in ('2022','2023','2024','2025','2026') or x.get('week')==7:
  season.append(dict(record_id=x['record_id'],procedure_reference=x.get('procedure_label',x.get('procedure_id')),target=x['target'],product_id=x['product_id'],evaluation_panel_id=x['evaluation_panel_id'],season=x.get('season',x.get('period')),week=x.get('week'),population=x.get('population'),MAE=x.get('MAE',x.get('mae')),MSE=x.get('MSE',x.get('mse')),Brier=x.get('Brier',x.get('brier')),coverage=x.get('coverage',dict(n=x.get('n'),games=x.get('unique_games'))),evidence=x['evidence'],aggregate_rule='ORIGINAL_PANEL_ONLY_NOT_NEW_ROLLING_ORIGIN'))
write('SEASON_RESULTS_2022_2026',season)
# The requested ranking remains explicitly blocked rather than substituting a shorter target.
leaders=json.loads((R/'inventory/REPORTED_TOP5_2026_W1_W6.json').read_text())
top=[]
for t in T:
 product='event_probability' if t=='anytime_td' else 'display_point_MAE'
 top.append(dict(target=t,product_id=product,rank=None,procedure_id=None,history_regime=None,evaluation_panel_id='2026-REG-W1-W7-fixed-v1',status='BLOCKED_COMMON_W1_W7_ROWS_NOT_RESTORED',score=None,evidence='UNKNOWN/BLOCKED',shorter_panel_report='inventory/REPORTED_TOP5_2026_W1_W6.csv',readiness='NO_NEW_V2_ADMISSION',actual_website='See production/FUTURE_CAPTURE_AND_RELEASE_HANDOFF.md'))
write('TOP5_BY_CATEGORY_PRODUCT',top)
write('TOP_PLAYER_AND_ROLE_SCORECARD',[dict(target=t,cohort='pregame_top10_top15_top20_disjoint_and_remainder',status='BLOCKED_MEMBERSHIP_AND_MATCHED_ROWS_NOT_RESTORED',n=None,loss=None,reason='Existing upstream top-player study retained as reported evidence; replay package lacks frozen pregame rank membership. Future totals/outcome-based ranks prohibited.',source='reports/top-player-cached-20261028/README.md') for t in T])
write('OVER_UNDER_SCORECARD',[dict(target=t,population='all_authenticated_offers_and_frozen_selected_subsets',side=s,status='BLOCKED_NO_MATCHED_AUTHENTIC_OFFERS_SELECTION_PRICES',wins=None,losses=None,pushes=None,voids=None,unresolved=None,hit_rate=None,Brier=None,log_loss=None,ROI=None,reason='Retained baseline packet has no recorded offers. Existing Week6 direction-classification study is separate reported evidence; lines alone cannot establish prices, selections or profitability.') for t in T for s in ('over','under')])
manifest=[]
for x in json.loads((R/'inventory/REPORTED_SOURCE_MANIFEST.json').read_text()):manifest.append(dict(artifact_id='UP-'+str(x.get('source_id',len(manifest))),kind='reported_public_aggregate_source',original=x,evidence_availability='PUBLIC_AGGREGATES_ONLY',status='LOCATED_NOT_ROW_REPRODUCED',private_locator=None))
for id,file,kind in [('REPLAY-RETAINED-W7','replay/REPLAY_SCORES.json','independent_retained_row_scores'),('REPLAY-CHECKS','replay/REPRODUCTION_CHECKS.json','independent_arithmetic_checks')]:
 b=(R/file).read_bytes();manifest.append(dict(artifact_id=id,run_id='v2-replay-retained-20261029-v1',file='reports/'+file,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),kind=kind,status='REPRODUCED',private_locator=None))
write('RUN_RESULT_ARTIFACT_MANIFEST',manifest,G)
# Run evidence is an append-only factual event, not invented fit counts.
event=dict(experiment_id='inherited-reproduction',run_id='v2-replay-retained-20261029-v1',state_dimensions=dict(proposed=True,implemented=True,software_tested=True,running=False,failed=False,fitted_unforecasted=False,forecasted_unscored=False,scored=True,reproduced=True,inaccessible=False,invalidated=False,operationally_ready=False,captured_pregame=False,deployed=False),counts=json.loads((R/'replay/REPLAY_RECEIPT.json').read_text()),note='V2 score computation only; original forecasts retained. Original NFL truth/feature vintages not independently authenticated.')
(G/'EXECUTIONS.jsonl').write_text(json.dumps(event)+'\n')
(G/'REQUESTS.json').write_text(json.dumps(requests,indent=2)+'\n')
summary=dict(direct_request_items=len(requests),priority_pathways=60,provisional_legacy_references=len(refs),canonical_procedures=None,grid_cells=len(grid),grid_by_status=dict(collections.Counter(x['status'] for x in grid)),reported_score_cells=len(legacy),replay_metric_cells=len(replay),new_fit_count=0,new_inference_count=0,unique_supported_NFL_player_games=16,unique_supported_NFL_games=1,total_task_completion_percentage=None)
(R/'CHECKPOINT_COUNTS.json').write_text(json.dumps(summary,indent=2)+'\n')
print(summary)
