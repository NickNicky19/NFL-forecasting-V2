#!/usr/bin/env python3
"""Public aggregate projections for the October30C checkpoint; no NFL fits."""
import collections,csv,hashlib,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT))
OUT=ROOT/'reports/continuation-20261030c'
BASE=ROOT/'reports/continuation-20261030b'
TARGETS=('pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','nick-chart-ppr-v1','anytime_td')
SEASONS={2025:'season-2025-v1',2024:'season-2024-v2',2023:'season-2023-complete-replay-v1',2022:'season-2022-v2'}

def load(p):return json.loads(Path(p).read_text())
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,rows):
 p=OUT/name;p.write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
def csvwrite(name,rows):
 rows=list(rows)
 if not rows:return
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with (OUT/name).open('w',newline='')as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
  for r in rows:w.writerow({k:json.dumps(v,separators=(',',':'))if isinstance(v,(dict,list))else v for k,v in r.items()})
def primary(r):return r.get('population')=='primary'and str(r.get('week'))=='ALL'and r.get('position','ALL')=='ALL'and r.get('fallback_view','ALL')=='ALL'
def feature_floor(r,year):
 strict=r['policy_id'].endswith('STRICT');arm=r['history_regime']
 floor=year if arm=='H-CURRENT' else max(2022,year-1) if arm=='H-RECENT' else 2022
 return floor if r['procedure_id']=='empirical-player-history-control-v1' else year if strict else 2022

def score_sources():
 for year,folder in SEASONS.items():
  p=OUT/folder/'SCORES.json'
  if not p.exists():continue
  rows=load(p)
  if year==2025:
   mapping=load(OUT/'season-2025-continuity-repair-v1/SUPERSESSION_MAPPING.json')['rows'];repair=load(OUT/'season-2025-continuity-repair-v1/SCORES.json')
   for m in mapping:rows[m['source_row_index']]=dict(repair[m['replacement_row_index']],_score_source=m['replacement_artifact'])
  yield year,p,rows
def main():
 inventories=[];season_rows=[];season_primary=[];coverage=[];source_receipts=[]
 for year,p,rows in score_sources():
  rel=p.relative_to(ROOT).as_posix();source_receipts.append(dict(season=year,artifact=rel,sha256=digest(p),score_views=len(rows)))
  if year==2025:
   repair=OUT/'season-2025-continuity-repair-v1/SCORES.json';mapping=OUT/'season-2025-continuity-repair-v1/SUPERSESSION_MAPPING.json'
   source_receipts[-1].update(replacement_artifact=repair.relative_to(ROOT).as_posix(),replacement_sha256=digest(repair),replacement_views=len(load(mapping)['rows']),supersession_mapping_sha256=digest(mapping))
  for r in rows:
   source=r.get('_score_source',rel)
   # All weekly/position/fallback views remain in canonical source/index; this
   # readable season table retains full-system ALL-position primary+extended.
   if r.get('position','ALL')=='ALL'and r.get('fallback_view','ALL')=='ALL':
    season_rows.append({**{k:r.get(k)for k in ('season','week','target','population','procedure_id','procedure_family_id','policy_id','history_regime','product_id','evaluation_seasons','evaluation_weeks','n','unique_games','forecast_rows','fallback_rows','mae','mse','rmse','bias','p90_abs','p95_abs','max_abs','brier','CRPS','NLL','log_loss','precision_counts','infinite_NLL','infinite_log_losses')},'source_artifact':source,'evidence':'NEW_EXPERIMENT;independent retained-row QA linked separately','requested_history_status':'PARTIAL_SOURCE_LIMITED_AVAILABLE_2022_PROXY'if year==2022 and r['history_regime']=='H-RECENT'else'REGISTERED_SOURCE_WINDOW'})
   if not primary(r):continue
   season_primary.append(dict(r,_source=source))
   policy=r['policy_id'];strict=policy.endswith('STRICT');arm=r['history_regime'];floor=year if arm=='H-CURRENT'else max(2022,year-1)if arm=='H-RECENT'else 2022
   inventories.append(dict(procedure_id=r['procedure_id'],target=r['target'],product_id=r['product_id'],policy_id=policy,history_regime=arm,fit_seasons=list(range(floor,year+1)),feature_memory_floor=feature_floor(r,year),evaluation_seasons=[year],evaluation_weeks=r.get('evaluation_weeks'),n=r['n'],query_rows=r.get('forecast_rows'),fallback_rows=r.get('fallback_rows'),source=source,chronology='earliereligiblelabels;weeklyfit/pergamefeature;strict7dayassumption',startup='fixednoNFLfallbackplusown/rolepriorsasperrecipe;includedfullsystem',source_vintage='current-vintage reconstruction; not authenticated historical issuance',strict_setting_limit='architecture/settingshistoricallyexposed; data window alone is strict',requested_recent_status='PARTIAL_SOURCE_LIMITED_AVAILABLE_2022_PROXY'if year==2022 and arm=='H-RECENT'else'REGISTERED'))
  cp=p.with_name('EVALUATION_COVERAGE.json')
  if cp.exists():coverage.extend(dict(x,season=year)for x in load(cp)if x.get('week')=='ALL')
 # Keep the accepted2026 weekly/full-season rows in the same readable file;
 # their forecasts and original source artifacts are not regenerated.
 from tools.report_season_balance import SPECS,normalized
 corrections={}
 correction=ROOT/'reports/continuation-20261030/chart-grid-precision-correction-v1/SCORES.json'
 dims=('record_id','procedure_id','history_regime','policy_id','target','population','product_id','week','season','position','fallback_view','cohort_id')
 for c in load(correction):corrections[c['supersedes_score_artifact'],tuple(c['supersedes_source_identity'].get(k)for k in dims)]=c
 for artifact,kind in SPECS:
  path=ROOT/artifact;rr=list(csv.DictReader(path.open()))if kind=='csv'else load(path)
  for r in rr:
   if str(r.get('season',2026))!='2026'or r.get('position','ALL')!='ALL'or r.get('fallback_view','ALL')!='ALL':continue
   nr=normalized(r,artifact);nr.update(week=r.get('week'),population=r['population'],fallback_rows=r.get('fallback_rows',r.get('fallback_n')),forecast_rows=r.get('forecast_rows',r.get('forecast_queries')),requested_history_status='ACCEPTED_FIXED_2026_PANEL_UNCHANGED')
   fix=corrections.get((artifact,tuple(r.get(k)for k in dims)))
   nr['precision_counts']=fix.get('precision_counts_exact_grid')if fix else r.get('precision_counts')
   nr['precision_source_artifact']=correction.relative_to(ROOT).as_posix()if fix else artifact
   season_rows.append(nr)
   if primary(r):
    arm=nr['history_regime'];floor=2026 if arm=='H-CURRENT'else 2025 if arm=='H-RECENT'else 2022;strict='strict-current'in nr['procedure_id'];empirical='empirical'in nr['procedure_id']
    policy=r.get('policy_id')or arm+('-EMPIRICAL'if empirical else'-STRICT'if strict else'-COMMON')
    inventories.append(dict(procedure_id=nr['procedure_id'],target=nr['target'],product_id=nr['product_id'],policy_id=policy,policy_id_provenance='source_declared'if r.get('policy_id')else'derived_from_registered_history_and_feature_contract',history_regime=arm,fit_seasons=list(range(floor,2027)),feature_memory_floor=floor if empirical else 2026 if strict else 2022,evaluation_seasons=[2026],evaluation_weeks=list(range(1,8)),n=nr['n'],query_rows=nr['forecast_rows'],fallback_rows=nr['fallback_rows'],source=artifact,chronology='AcceptedfixedW1W7kickoff/7dayreconstruction',source_vintage='current-vintage reconstruction',requested_recent_status='REGISTERED',strict_setting_limit='architecture/settingshistoricallyexposed;strictdatawindowisaseparatepolicy'))
 csvwrite('METHOD_YEAR_INVENTORY.csv',inventories);save('METHOD_YEAR_INVENTORY.json',inventories)
 csvwrite('SEASON_RESULTS_2022_2026.csv',season_rows);save('SEASON_SOURCE_MANIFEST.json',dict(sources=source_receipts,current_2026='Fixed2026W1–7sourcesremainunchanged;seeTOP5andpermanentindex',season_rows_scope='newlearnedolderseasonsplusretainedempirical;currentpanelseparate;noimplicitpooling'))
 csvwrite('SEASON_COVERAGE.csv',coverage)
 # Observed minima are descriptive. Product and history selection are exposed.
 lines=['# Twelve-category seasonal results','', 'Older seasons are internally matched rolling-origin comparisons. Their games differ from the fixed 2026 test panel, so this table does not answer the 2026 training-window question. Numeric cells are MAE; anytime TD uses Brier. These are observed minima among the executed V2 library, not earlier-frozen selection policies. Historical query features use the registered kickoff cutoff, not a reconstructed T-minus-90 product; subgroup selectors and future eligibility have separately stated clocks.','', '| Target | 2025 minimum | 2024 minimum | 2023 minimum | 2022 available-data minimum |','|---|---|---|---|---|']
 winners=[]
 for target in TARGETS:
  cells=[]
  for year in SEASONS:
   metric='brier'if target=='anytime_td'else'mae';pool=[r for r in season_primary if r['season']==year and r['target']==target and isinstance(r.get(metric),(int,float))]
   if not pool:cells.append('Pending');continue
   best=min(pool,key=lambda r:(r[metric],r['procedure_id'],r['history_regime'],r['product_id']));winners.append(dict(best,ranking_metric=metric,ranking_loss=best[metric]))
   proc=best['procedure_id'];name='Leaf-CDF'if'ordered_leaf_cdf'in proc else'GLM-law'if'glm'in proc else'HGB-L1'if'absolute_error'in proc else'HGB-L2'if'squared_error'in proc else'HGB-probability'if'log_loss'in proc else'Empirical '+best['product_id']
   if 'c02' in best['procedure_id']:name='C02'
   if 'poisson' in best['procedure_id']:name='HGB-count'
   cells.append(f"{best[metric]:.6f} · {name} · {best['history_regime']} (n={best['n']})")
  lines.append('| '+target+' | '+' | '.join(cells)+' |')
 lines+=['','2025: the same-history C02 gains for current-season interceptions, receptions and chart PPR reverse against Leaf-CDF. In 2024 anytime-TD GLM RECENT Brier0.145935 beats fixed-2026 HGB MULTI0.146578; their current-season ordering is opposite. See each seasonal fixed-choice/reversal file for exact matching and all adverse results.','', '2022 has no admitted2021 data. Its RECENT values are explicitly source-limited proxies, not the completed preceding-year comparison. Complete requested history effects cannot be inferred from their equality.','', '[All seasonal rows](SEASON_RESULTS_2022_2026.csv) · [Method/year inventory](METHOD_YEAR_INVENTORY.csv) · [Shared subgroup summaries](SHARED_SUBGROUP_RESULTS.md) · [Opponent-information experiment](qualified-defense-information-v1/EXECUTED_RESULTS.md) · [Permanent results index](results-index/README.md).']
 (OUT/'TWELVE_CATEGORY_SUMMARY.md').write_text('\n'.join(lines)+'\n');csvwrite('OLDER_SEASON_OBSERVED_WINNERS.csv',winners)
 # Append information variants to family representatives, retaining four
 # scientific families instead of padding the requested five.
 ranks=load(BASE/'TOP5_BY_CATEGORY_PRODUCT.json');candidates=list(ranks)
 defense=OUT/'qualified-defense-information-v1/SCORES.json'
 for r in load(defense):
  if not primary(r):continue
  for product,metric in [('display_point','brier'if r['target']=='anytime_td'else'mae'),('intended_mean','mse'),('forecast_law','CRPS')]:
   if product=='intended_mean'and(r['target']=='anytime_td'or'mean'not in r['product_id']):continue
   if not isinstance(r.get(metric),(int,float)):continue
   candidates.append(dict(target=r['target'],family='ORDERED_LEAF_CDF',procedure_id=r['procedure_id'],product=r['product_id'],history_regime=r['history_regime'],information_policy=r['information_policy'],n=r['n'],mae=r.get('mae'),mse=r.get('mse'),rmse=r.get('rmse'),brier=r.get('brier'),CRPS=r.get('CRPS'),fallback_rows=r['fallback_rows'],forecast_rows=r['forecast_rows'],source_artifact=defense.relative_to(ROOT).as_posix(),source_record=r['record_id'],scientific_state='exposedobservedfamilyminimum;notafrozenselector',ranking_product=product,ranking_metric=metric,ranking_loss=r[metric]))
 groups=collections.defaultdict(list)
 for r in candidates:groups[r['target'],r['ranking_product'],r['family']].append(r)
 reps=[min(rs,key=lambda r:(r['ranking_loss'],r['procedure_id'],r['history_regime'],r['product']))for rs in groups.values()];final=[]
 for target in TARGETS:
  for product in ('display_point','intended_mean','forecast_law'):
   rs=sorted((dict(r)for r in reps if r['target']==target and r['ranking_product']==product),key=lambda r:(r['ranking_loss'],r['family']))
   prior=None;rank=0
   for i,r in enumerate(rs):
    if prior is None or not math.isclose(r['ranking_loss'],prior,abs_tol=1e-12,rel_tol=0):rank=i+1
    r['rank']=rank;prior=r['ranking_loss'];final.append(r)
 save('TOP5_BY_CATEGORY_PRODUCT.json',final);csvwrite('TOP5_BY_CATEGORY_PRODUCT.csv',final)
 # The grid preserves all original statuses and every executed/new-unrun cell.
 grid=[dict(x,source_checkpoint='accepted30b')for x in load(BASE/'EXPERIMENT_GRID.json')]
 for f in sorted(OUT.rglob('*GRID_STATUS.json')):
  for i,r in enumerate(load(f)):
   grid.append(dict(r,cell_id=f.relative_to(OUT).as_posix()+':'+str(i),source_artifact=f.relative_to(ROOT).as_posix(),cell_unit='registeredorigin/target/procedure/policyopportunity;aliasesnotfits'))
 save('EXPERIMENT_GRID.json',grid);csvwrite('EXPERIMENT_GRID.csv',grid)
 ou=[dict(target=t,state='BLOCKED_AUTHENTICATED_OFFER_PANEL',scored_offers=None,selected_wins=None,selected_losses=None,pushes=None,voids=None,ROI=None,missing_source='actualofferssamebook/line/time/price/settlement+frozenV2selection',original_owner_receipts='reportedseparate;notauthenticatedV2pricedresults')for t in TARGETS];csvwrite('OVER_UNDER_SCORECARD.csv',ou)
 print(json.dumps(dict(season_inventory_views=len(inventories),season_rows=len(season_rows),grid_rows=len(grid),family_representatives=len(final),new_NFL_fits=0)))

if __name__=='__main__':main()
