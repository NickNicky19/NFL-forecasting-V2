#!/usr/bin/env python3
"""Descriptive same-recipe micro/season-balanced summaries, never history tests."""
import argparse,collections,csv,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.report_oct30c_checkpoint import OUT,ROOT,SEASONS,score_sources,primary,csvwrite,save
from tools.compare_season_with_2026 import proc,product

SPECS=[('reports/continuation-20261029/history-diagnostic-v1/HISTORY_COMPARISON_2026_W1_W7.csv','csv'),('reports/continuation-20261029/hgb-history-v1/SCORES.json','json'),('reports/continuation-20261030/distribution-wave-v2/SCORES.json','json'),('reports/continuation-20261030/count-ablation-wave-v1/SCORES.json','json'),('reports/continuation-20261030/chart-wave-v1/SCORES.json','json'),('reports/continuation-20261030/chart-wave-v1/EMPIRICAL_SCORES.json','json'),('reports/continuation-20261030b/ordered-information-ablation-v1/SCORES.json','json')]
def numeric(x):return None if x in('',None,'Infinity')else float(x)
def normalized(r,artifact):
 return dict(target=r['target'],procedure_id=proc(r,artifact),product_id=product(r),history_regime=r['history_regime'],season=int(r.get('season',2026)),n=int(r.get('n',r.get('scored_n',0))),mae=numeric(r.get('mae')),mse=numeric(r.get('mse')),bias=numeric(r.get('bias')),brier=numeric(r.get('brier')),CRPS=numeric(r.get('CRPS')),source_artifact=artifact,source_vintage='current-vintage reconstruction; kickoffquery/seven-dayassumption',population='retrospectiveprimaryqualifiedparticipant')
def main():
 rows=[]
 for year,p,rr in score_sources():
  rows.extend(normalized(r,r.get('_score_source',p.relative_to(ROOT).as_posix()))for r in rr if primary(r))
 for artifact,kind in SPECS:
  p=ROOT/artifact;rr=list(csv.DictReader(p.open()))if kind=='csv'else json.loads(p.read_text())
  for r in rr:
   if primary(r)and str(r.get('season',2026))=='2026':rows.append(normalized(r,artifact))
 # Source-limited2022 RECENT does not enter the requested RECENT aggregate.
 for r in rows:
  if r['season']==2022 and r['history_regime']=='H-RECENT':r['history_regime']='H-RECENT-AVAILABLE2022-PROXY'
 groups=collections.defaultdict(list)
 for r in rows:groups[r['target'],r['procedure_id'],r['product_id'],r['history_regime']].append(r)
 results=[]
 for key,rs in sorted(groups.items()):
  seasons=[r['season']for r in rs]
  if len(set(seasons))!=len(seasons):raise ValueError('duplicate recipe/season; resolve aliases rather than double-weight')
  n=sum(r['n']for r in rs);out=dict(zip(('target','procedure_id','product_id','history_regime'),key));out.update(seasons=sorted(seasons),season_count=len(rs),n=sum(r['n']for r in rs),source_rows=rs,meaning='Descriptivedifferentgamepanels;notisolated2026historyeffect;notselectorperformance')
  for metric in('mae','mse','bias','brier','CRPS'):
   valid=[r for r in rs if r[metric]is not None and r['n']>0]
   out[metric+'_pooled_micro']=sum(r['n']*r[metric]for r in valid)/sum(r['n']for r in valid)if valid else None
   out[metric+'_season_balanced']=sum(r[metric]for r in valid)/len(valid)if valid else None
  out['rmse_pooled_micro']=math.sqrt(out['mse_pooled_micro'])if out['mse_pooled_micro']is not None else None
  out['rmse_season_balanced']=math.sqrt(out['mse_season_balanced'])if out['mse_season_balanced']is not None else None
  results.append(out)
 save('SEASON_BALANCED_SUMMARY.json',results);csvwrite('SEASON_BALANCED_SUMMARY.csv',results)
 choices=json.loads((ROOT/'reports/continuation-20261030b/TOP5_BY_CATEGORY_PRODUCT.json').read_text());history=[]
 for choice in choices:
  if choice['ranking_product']!='display_point'or choice['rank']!=1:continue
  fixedproc=choice['procedure_id'].replace(':common-feature-memory','')
  if fixedproc.endswith(':empirical'):fixedproc='empirical-player-history-control-v1'
  fixedproduct='mean'if choice['product']=='empirical_mean'else choice['product'];metric='brier'if choice['target']=='anytime_td'else'mae'
  for year in range(2022,2027):
   rr=[r for r in rows if r['target']==choice['target']and r['procedure_id']==fixedproc and r['product_id']==fixedproduct and r['season']==year]
   byarm={r['history_regime']:r for r in rr};one=dict(target=choice['target'],season=year,fixed_2026_procedure=fixedproc,product_id=fixedproduct,metric=metric,choice_source='acceptedfcfe2026observedminimum;notearlierfrozenselector',comparison_type='completeinformationpolicy'if fixedproc=='empirical-player-history-control-v1'else'fitwindowwithcommonolderfeaturememory')
   for arm,label in [('H-CURRENT','current'),('H-RECENT','recent'),('H-MULTI','multi')]:
    r=byarm.get(arm);one[label+'_error']=r.get(metric)if r else None;one[label+'_n']=r['n']if r else None
   current,multi=one['current_error'],one['multi_error'];one['multi_minus_current']=multi-current if current is not None and multi is not None else None
   one['relative_multi_minus_current']=(multi-current)/current if current and multi is not None else None
   one['recent_missing_reason']='2021notadmitted;available2022proxyseparate'if year==2022 else None
   eligible=[(arm,r[metric])for arm,r in byarm.items()if arm in('H-CURRENT','H-RECENT','H-MULTI')and r.get(metric)is not None]
   minimum=min((v for _,v in eligible),default=None);one['lowest_observed_arms']=[arm for arm,v in eligible if abs(v-minimum)<=1e-12]
   one['source_artifacts']=[r['source_artifact']for r in rr];history.append(one)
 csvwrite('FIXED_PROCEDURE_HISTORY_BY_SEASON.csv',history);save('FIXED_PROCEDURE_HISTORY_BY_SEASON.json',history)
 (OUT/'SEASON_BALANCE_DEFINITIONS.md').write_text('# Cross-season aggregate definitions\n\nEach row is one fixed normalized recipe/product/history policy across its explicitly listed supported seasons. Pooled micro loss is `sum(n_s * loss_s) / sum(n_s)`. Season-balanced loss is the arithmetic mean of the supported seasonal losses; season-balanced RMSE is the square root of season-balanced MSE. It is not the mean of seasonal RMSE. Every2022–2025 season is full18weeks;2026 stays fixed atWeeks1–7. Missing seasons are not zero. The requested2022RECENT arm is excluded and its available-data proxy has a separate identity.\n\nDifferent histories may have different supported-year sets; compare season columns before using any aggregate. Neither pooled figure answers the training-history effect on the same2026games. Selection is exposed; these are descriptive fixed-recipe summaries, not live weekly selector results. Explicit source rows and all per-season errors remain in the JSON.\n')
 print(json.dumps(dict(recipe_aggregates=len(results),season_rows=len(rows),newfits=0)))
if __name__=='__main__':main()
