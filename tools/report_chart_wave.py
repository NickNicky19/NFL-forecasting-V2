#!/usr/bin/env python3
"""Saved-row chart export, dates, paired contrasts and readable partial-panel report."""
from __future__ import annotations
import argparse,collections,csv,gzip,hashlib,io,json,math,os,statistics,tempfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public-root',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);a=p.parse_args();P,D=a.public_root,a.private_root
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,obj):
 body=json.dumps(obj,indent=2,allow_nan=False)+'\n';path=P/name
 if path.exists():assert path.read_text()==body;return
 with path.open('x') as f:f.write(body)
def write(name,rows):
 f=io.StringIO(newline='');w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows);body=f.getvalue();path=P/name
 if path.exists():assert path.read_bytes()==body.encode();return
 with path.open('x',newline='') as f:f.write(body)
run=json.loads((P/'RUN_RECEIPT.json').read_text());assert run['state']=='COMPLETE';direct=[]
for f in sorted(P.glob('*-FORECAST.json')):
 receipt=json.loads(f.read_text());packet=receipt['packet'];path=D/packet['bundle_name'];assert sha(path)==packet['sha256'];direct.extend(json.loads(gzip.decompress(path.read_bytes()))['rows'])
assert len(direct)==run['forecast_output_views'];epacket=run['empirical_prediction_packet'];assert sha(D/epacket['bundle_name'])==epacket['sha256'];arith=json.loads(gzip.decompress((D/epacket['bundle_name']).read_bytes()))['rows'];fr=json.loads((P/'EMPIRICAL_FUTURE_CAPTURE_RECEIPT.json').read_text());assert sha(D/fr['packet']['bundle_name'])==fr['packet']['sha256'];future_arith=json.loads(gzip.decompress((D/fr['packet']['bundle_name']).read_bytes()))['rows'];allrows=direct+arith+future_arith
fields=['game_id','player_id','sleeper_id','target','population','position','season','week','history_regime','policy_id','information_policy','family','procedure_id','product_id','prediction','actual','actual_grid','actual_status','fallback','fallback_source','fallback_source_n','status','abstention_reason','fit_slot','fit_state','latest_feature_available','latest_training_label_available','cutoff','actual_generated_at','issued_at_utc','actual_horizon_seconds','owner_cutoff_status','run_id','query_id','distribution_summary','law_reference']
target=D/'all-chart-predictions.csv.gz'
if target.exists():
 fd,temporary=tempfile.mkstemp(prefix='chart-flat-check-',suffix='.gz');os.close(fd);Path(temporary).unlink();path=Path(temporary)
else:path=target
with path.open('xb') as raw:
 with gzip.GzipFile(fileobj=raw,filename='',mode='wb',mtime=0) as z:
  with io.TextIOWrapper(z,encoding='utf-8',newline='') as f:
   w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
   for r in allrows:
    out={k:r.get(k) for k in fields};out['query_id']=r.get('query_id') or hashlib.sha256(json.dumps([r['game_id'],r.get('player_id'),r.get('sleeper_id'),r['target']],separators=(',',':')).encode()).hexdigest();out['policy_id']=r.get('policy_id') or r['history_regime']+'-ARITHMETIC';out['distribution_summary']=json.dumps(r.get('distribution_summary'),sort_keys=True,separators=(',',':'));out['law_reference']=json.dumps(r.get('law_reference'),sort_keys=True,separators=(',',':'));w.writerow(out)
 raw.flush();os.fsync(raw.fileno())
if path!=target:
 assert sha(path)==sha(target);path.unlink();path=target
scores=json.loads((P/'SCORES.json').read_text());escores=json.loads((P/'EMPIRICAL_SCORES.json').read_text());primary=[r for r in scores if r['week']=='ALL' and r['position']=='ALL' and r['fallback_view']=='ALL'];eprimary=[r for r in escores if r['season']==2026 and r['week']=='ALL' and r['position']=='ALL']
# Per-source-row dates projections preserve actual supported/query weeks, not textALL.
def date_projection(rows,source_rows,filename):
 census=collections.defaultdict(lambda:dict(n=0,forecast_n=0,weeks=set(),fw=set(),years=set(),fy=set(),games=set()))
 for r in rows:
  if (int(r['season'])==2026 and int(r['week'])==8) or r['prediction'] is None:continue
  if filename=='SCORES.json':
   variants=[('ALL','ALL','ALL'),(str(r['week']),'ALL','ALL'),('ALL',r['position'],'ALL')]+([('ALL','ALL','LEARNED_ONLY')] if r['fallback']=='none' else [])
   keys=[(r['procedure_id'],r['history_regime'],r['product_id'],str(r['season']),wk,pos,view) for wk,pos,view in variants]
  else:
   keys=[(r['procedure_id'],r['history_regime'],r['product_id'],season,wk,pos,'ALL') for season,wk,pos in [(str(r['season']),'ALL','ALL'),(str(r['season']),str(r['week']),'ALL'),(str(r['season']),'ALL',r['position']),('POOLED_2022_2026','ALL','ALL')]]
  for key in keys:
   v=census[key];v['forecast_n']+=1;v['fw'].add(int(r['week']));v['fy'].add(int(r['season']))
   if r['actual'] is not None:v['n']+=1;v['weeks'].add(int(r['week']));v['years'].add(int(r['season']));v['games'].add(r['game_id'])
 projection=[]
 for i,r in enumerate(source_rows):
  key=(r['procedure_id'],r['history_regime'],r['product_id'],str(r['season']),str(r['week']),r['position'],r['fallback_view']);c=census[key];assert c['n']==r['n'] and c['forecast_n']==r['forecast_rows'] and len(c['games'])==r['unique_games']
  projection.append(dict(source_row_index=i,evaluation_seasons=sorted(c['years']),evaluation_weeks=sorted(c['weeks']),forecast_query_seasons=sorted(c['fy']),forecast_query_weeks=sorted(c['fw']),scored_rows=c['n'],forecast_rows=c['forecast_n'],unique_games=len(c['games'])))
 return dict(source_score_artifact='reports/continuation-20261030/chart-wave-v1/'+filename,source_score_sha256=sha(P/filename),date_definition='actual supported/forecast weeks per exact retained aggregate; integergridlabels convertednativepoints before scoring',rows=projection,new_fits=0,new_predictions=0)
dump('SCORE_DATE_PROJECTION.json',date_projection(direct,scores,'SCORES.json'));dump('EMPIRICAL_SCORE_DATE_PROJECTION.json',date_projection(arith,escores,'EMPIRICAL_SCORES.json'))
dump('SCORE_INFINITE_NLL_PROJECTION.json',dict(source_score_artifact='reports/continuation-20261030/chart-wave-v1/SCORES.json',source_score_sha256=sha(P/'SCORES.json'),definition='nonzeroinfinite_NLL authenticates true positive-infinitePMF loss,notunscored',rows=[dict(source_row_index=i,NLL='Infinity',nll_status='positive_infinite_loss',infinite_NLL=r['infinite_NLL']) for i,r in enumerate(scores) if r['infinite_NLL']],new_fits=0,new_predictions=0))
# Paired full/learned overlaps only among exact direct query identities.
groups=collections.defaultdict(dict)
for r in direct:
 if int(r['week'])==8:continue
 key=(r['family'],r['product_id'],r['game_id'],r['player_id']);assert r['policy_id'] not in groups[key];groups[key][r['policy_id']]=r
contrast=collections.defaultdict(list)
for key,policy in groups.items():
 assert len(policy)==4;base=policy['H-CURRENT-COMMON']
 if base['actual'] is None:continue
 for contender in ('H-RECENT-COMMON','H-MULTI-COMMON','H-CURRENT-STRICT'):
  r=policy[contender];assert r['actual']==base['actual'];learned=r['fallback']=='none' and base['fallback']=='none'
  for metric in (['MAE','MSE'] if r['product_id']=='mean' else ['MAE'])+['CRPS','NLL']:
   if metric=='NLL' and (r['distribution_summary']['infinite_nll'] or base['distribution_summary']['infinite_nll']):continue
   def loss(x):return abs(x['prediction']-x['actual']) if metric=='MAE' else (x['prediction']-x['actual'])**2 if metric=='MSE' else x['distribution_summary'][metric.lower()]
   contrast[key[:2]+(contender,metric)].append((int(r['week']),r['game_id'],loss(r)-loss(base),learned))
paired=[]
for key,values in sorted(contrast.items()):
 wk=collections.defaultdict(list)
 for week,game,delta,learned in values:wk[week].append(delta)
 wm=[statistics.fmean(v) for _,v in sorted(wk.items())];mean=statistics.fmean(wm);half=2.447*statistics.stdev(wm)/math.sqrt(7) if len(wm)==7 else None;learned=[d for _,_,d,b in values if b]
 paired.append(dict(family=key[0],product_id=key[1],comparison=key[2]+'_minus_H-CURRENT-COMMON',metric=key[3],paired_rows=len(values),games=len({g for _,g,_,_ in values}),weeks=len(wm),full_system_micro_difference=statistics.fmean(x[2] for x in values),week_balanced_difference=mean,week_t95_low=None if half is None else mean-half,week_t95_high=None if half is None else mean+half,learned_only_overlap_rows=len(learned),learned_only_overlap_difference=statistics.fmean(learned) if learned else None,uncertainty='exposedresearch;7weekclusters;unadjusted;tintervaldescriptive',comparison_contract='STRICTchangescompleteinformationpolicy;commonmemoryarmsisolatefittingwindow',nll_scope='finitepairsonly;infinitefullscoresretainedseparately' if key[3]=='NLL' else None))
write('PAIRED_HISTORY_AND_INFORMATION_POLICY.csv',paired)
summary=[]
for family in ['ordered_leaf_cdf','regularized_glm_law']:
 candidates=[r for r in primary if r['procedure_family_id']==family];best=min((r for r in candidates if r['information_policy']=='COMMON-2022-MEMORY'),key=lambda r:r['mae']);same={r['policy_id']:r for r in candidates if r['product_id']==best['product_id']}
 summary.append(dict(family=family,display_product=best['product_id'],scored_rows=best['n'],query_rows=best['forecast_rows'],best_observed_common_history=best['history_regime'],best_observed_common_mae=best['mae'],current_common_mae=same['H-CURRENT-COMMON']['mae'],recent_common_mae=same['H-RECENT-COMMON']['mae'],multi_common_mae=same['H-MULTI-COMMON']['mae'],strict_current_mae=same['H-CURRENT-STRICT']['mae'],current_common_fallback_rows=same['H-CURRENT-COMMON']['fallback_rows'],strict_fallback_rows=same['H-CURRENT-STRICT']['fallback_rows'],best_common_CRPS=best['CRPS'],best_common_NLL=best['NLL'],selection='exposedbestobservedproduct/commonhistory,notprospectiveselector'))
best=min(eprimary,key=lambda r:r['mae']);same={r['history_regime']:r for r in eprimary if r['product_id']==best['product_id']};summary.append(dict(family='empirical_history_control',display_product=best['product_id'],scored_rows=best['n'],query_rows=best['forecast_rows'],best_observed_common_history=best['history_regime'],best_observed_common_mae=best['mae'],current_common_mae=same['H-CURRENT']['mae'],recent_common_mae=same['H-RECENT']['mae'],multi_common_mae=same['H-MULTI']['mae'],strict_current_mae=same['H-CURRENT']['mae'],current_common_fallback_rows=same['H-CURRENT']['fallback_rows'],strict_fallback_rows=same['H-CURRENT']['fallback_rows'],best_common_CRPS=None,best_common_NLL=None,selection='STRICTexactCURRENTalias; exposedminimumamongpointviews/history'))
write('PRIMARY_CHART_HISTORY_SUMMARY.csv',summary)
balanced=[]
for arm in ('H-CURRENT','H-RECENT','H-MULTI'):
 for product in ('mean','lower_median'):
  rows=[r for r in escores if isinstance(r['season'],int) and r['week']=='ALL' and r['position']=='ALL' and r['history_regime']==arm and r['product_id']==product];assert len(rows)==5;v=dict(history_regime=arm,product_id=product,seasons=5,definition='equalweightperseason2022–25fullREGand2026W1–7; doesnotanswerthefixed2026historyquestion',mean_season_MAE=statistics.fmean(r['mae'] for r in rows),mean_season_MSE=statistics.fmean(r['mse'] for r in rows),mean_season_bias=statistics.fmean(r['bias'] for r in rows));v['root_mean_season_MSE']=math.sqrt(v['mean_season_MSE']);balanced.append(v)
write('SEASON_BALANCED_RESULTS.csv',balanced)
# Safe artifact manifests; actual filesystem bindings remain private.
artifacts=[];private={}
for f in sorted(D.rglob('*')):
 if not f.is_file() or f.suffix not in ('.gz','.json'):continue
 if f.name=='REPLAY_ARTIFACTS_PRIVATE.json':continue
 digest=sha(f);aid='ART-CHART-'+digest;artifacts.append(dict(artifact_id=aid,bundle_name=f.relative_to(D).as_posix(),bytes=f.stat().st_size,sha256=digest));private[aid]=str(f)
dump('PUBLIC_ARTIFACT_MANIFEST.json',dict(state='PUBLIC_SAFE_LOGICAL_ARCHIVE_NAMES_NOT_STORAGE_LOCATORS',artifacts=artifacts));(D/'REPLAY_ARTIFACTS_PRIVATE.json').write_text(json.dumps(dict(artifact_ids_to_local_files=private),indent=2)+'\n')
receipt=dict(state='SAVED_ROW_EXPORT_SOURCE_DATE_CENSUS_AND_PAIRING_COMPLETE',flat_prediction_sha256=sha(path),flat_prediction_bytes=path.stat().st_size,total_output_views=len(allrows),direct_output_views=len(direct),rolling_arithmetic_views=len(arith),arithmetic_future_views=len(future_arith),current_2026_chart_query_cells=2394,current_supported_labels=2359,missing_current_labels=35,paired_contrasts=len(paired),distribution_date_views=208,empirical_date_views=630,new_fits=0,new_predictions=0,script_sha256=sha(Path(__file__)),family_aliases={'empirical_chart_history_control':'empirical_history_control'})
dump('POSTRUN_REPLAY_RECEIPT.json',receipt)
lines=['# Qualified chart-PPR: executed direct and history controls','', '**Three procedure families now have measured same-chart results.** These are new source-specific partial-label reconstructions of the requested chart, not generic provider fantasy totals or an independent replay of every rare NFL event. The exact16-component policy uses unique fumbles lost and separately credited two-point conversions, preserves signed yards, and proves rare zeros only when both qualified complete-source supersets explicitly equal zero. Positive/unknown rare credits remain null.','', 'The direct wave completed64/64 registered opportunities:56 actual fits/retained models,8 insufficient-training fallback cells,0 failed fits. Empirical mean/median histories added155,424 rolling2022–26 point views with0 optimizer fits and630 aggregate views. The two direct families add208 current aggregate views. Histories and mean/median products do not create additional independent learners. These extend existing families and do not add three new scientific discoveries.','', '[Protocol](FROZEN_PROTOCOL.json) · [Qualified source policy](../CHART_PPR_PARTIAL_LABEL_POLICY_V2.json) · [Direct scores](SCORES.csv) · [Empirical season/week scores](EMPIRICAL_SCORES.csv) · [Three-family summary](PRIMARY_CHART_HISTORY_SUMMARY.csv) · [Paired full/learned-only comparisons](PAIRED_HISTORY_AND_INFORMATION_POLICY.csv) · [Season-balanced definition/results](SEASON_BALANCED_RESULTS.csv)','', '## Fixed2026 Weeks1–7, same2394queries','', 'The supported outcome panel is2359 player-games in107 games;34 query rows lack verified appearance and1 has unresolved rare attribution. All2394 are retained. The full source policy still retains eight unresolved rare rows in2026; seven lie outside the preregisteredQB/RB/WR/TE cohort. This is a retrospective statistical-row/appearance diagnostic, with current-vintage provider completeness assumptions and no full ex-ante population claim.','', '| Family | Display product | Supported/query rows | Current | Recent | Multi | Strict current | Best common arm |','|---|---|---:|---:|---:|---:|---:|---|']
for r in summary:lines.append(f"| {r['family']} | {r['display_product']} | {r['scored_rows']}/{r['query_rows']} | {r['current_common_mae']:.6f} | {r['recent_common_mae']:.6f} | {r['multi_common_mae']:.6f} | {r['strict_current_mae']:.6f} | {r['best_observed_common_history']} |")
lines+=['', 'Errors are MAE in chart points. Display views are chosen after observing errors, so this is an exploratory best-observed summary, not a frozen future selection policy. Genuine law means retain separate MSE/RMSE; medians are extracted from the direct total law, never sums of component medians. Direct CRPS, exact PMF log loss, zero mass and90%interval coverage/width remain in the full scores. The data live on an exact0.02point grid: integer-grid means/quantiles/widths/CRPS divide by50; discrete logPMF mass does not change. No continuous density is evaluated at a count or chart value.','', 'Common-memory arms isolate fitting windows with identical2022+feature memory. STRICT uses2026 labels/features/priors/transforms only and changes the full information policy; architecture was chosen in previously exposed research. The empirical strict view is exactly its H-CURRENT alias and is not separately fitted or counted. Weekly fits precede the first game in the week; per-game features use strictly earlier assumed kickoff+7day source availability. Earlier season pooled and season-balanced results are separate from the same-game2026 comparison.','', '## Full system, learned-only overlap and adverse results','', '| Family / product | Comparison | All supported rows | All-row delta | Learned overlap | Learned delta |','|---|---|---:|---:|---:|---:|']
for r in paired:
 if r['metric']!='MAE' or r['product_id']!='lower_median':continue
 d='—' if r['learned_only_overlap_difference'] is None else f"{r['learned_only_overlap_difference']:+.6f}"
 lines.append(f"| {r['family']} / {r['product_id']} | {r['comparison']} | {r['paired_rows']} | {r['full_system_micro_difference']:+.6f} | {r['learned_only_overlap_rows']} | {d} |")
lines+=['', 'Negative deltas favor the first named policy. Startup priors/zero controls remain in full-system errors; learned overlap requires neither arm to fall back. Finite-NLL paired subsets explicitly exclude impossible-event infinities while the original full aggregates retain their infinite counts. Seven week clusters, repeated research exposure and product/history selection limit certainty; no universal optimum or deployable selection-policy benefit is established. All losses and missing rows remain.','', '## Future research shadows and remaining source work','', 'The new chart future-query union has434 player-games:432 qualified contexts plus two distinct raw-Sleeper contexts with missing board identity/position retained as abstentions. It covers thirteen OPEN-T90 games; CAR–GB was already closed and is excluded. Direct capture persisted at00:50:01UTC with6912 issued views plus32 abstentions; separately registered arithmetic capture persisted00:52:52UTC with2592 issued plus12 abstentions. All valid rows persisted before their T90 deadlines. The shared fixed feature/fit asof is00:27:36.688096UTC; these are early same-asof snapshots with real later issue clocks, not T90 observations. No Week8 outcomes were read or scored. No official owner capture, production workflow or website changed. Offhost durability is attested separately by the root companion-store receipt.','', 'The remaining rare positives need event-level scorer/unit/lateral attribution; current zeros rely on the qualified full-week provider contract, not independently reconstructed official event truth. Other positions/return-only populations require their own preregistered extension. A source-contract contradiction must invalidate affected labels through a new version. Website integration remains owner-only after review of adapters, scoring, fallbacks and rollback.','']
(P/'README.md').write_text('\n'.join(lines));print(json.dumps(receipt,indent=2))
