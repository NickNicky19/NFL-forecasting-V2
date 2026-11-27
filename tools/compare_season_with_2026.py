#!/usr/bin/env python3
"""Compare fixed procedure choices across separately matched seasonal panels."""
import argparse,csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import seasonal_rolling as s

def proc(r,artifact):
 p=r.get('procedure_id') or ('hgb-direct-history-controls-v1:'+r['objective'] if 'hgb-history' in artifact else 'empirical-player-history-control-v1')
 if p.endswith(':empirical'):p='empirical-player-history-control-v1'
 return p.replace(':common-feature-memory','')
def product(r):
 p=r.get('product_id') or r.get('product') or r.get('objective');return 'mean' if p=='empirical_mean' else p
def key(r,artifact):return(r['target'],proc(r,artifact),product(r),r['history_regime'])
def main():
 p=argparse.ArgumentParser();p.add_argument('--season-public',type=Path,required=True);p.add_argument('--reference-public',type=Path,required=True);a=p.parse_args();pub=a.season_public;season=list(csv.DictReader((pub/'PRIMARY_PROCEDURE_HISTORY.csv').open()));old=[]
 specs=[('reports/continuation-20261029/history-diagnostic-v1/HISTORY_COMPARISON_2026_W1_W7.csv','csv'),('reports/continuation-20261029/hgb-history-v1/SCORES.json','json'),('reports/continuation-20261030/distribution-wave-v2/SCORES.json','json'),('reports/continuation-20261030/count-ablation-wave-v1/SCORES.json','json'),('reports/continuation-20261030/chart-wave-v1/SCORES.json','json'),('reports/continuation-20261030/chart-wave-v1/EMPIRICAL_SCORES.json','json'),('reports/continuation-20261030b/ordered-information-ablation-v1/SCORES.json','json')]
 for artifact,kind in specs:
  path=Path(artifact);rows=list(csv.DictReader(path.open())) if kind=='csv' else json.loads(path.read_text())
  for r in rows:
   if r.get('population')=='primary' and str(r.get('season',2026))=='2026' and str(r['week'])=='ALL' and r.get('position','ALL')=='ALL' and r.get('fallback_view','ALL')=='ALL':old.append(dict(r,_artifact=artifact))
 lookup26={key(r,r['_artifact']):r for r in old};lookupyear={key(r,'seasonal'):r for r in season};out=[];reversals=[]
 for choice in csv.DictReader((a.reference_public/'TOP5_BY_CATEGORY_PRODUCT.csv').open()):
  if choice['ranking_product']!='display_point' or choice['rank']!='1':continue
  metric='brier' if choice['target']=='anytime_td' else 'mae';fixedkey=(choice['target'],choice['procedure_id'].replace(':common-feature-memory',''),'mean' if choice['product']=='empirical_mean' else choice['product'],choice['history_regime'])
  if fixedkey[1].endswith(':empirical'):fixedkey=(fixedkey[0],'empirical-player-history-control-v1',fixedkey[2],fixedkey[3])
  current=lookupyear.get(fixedkey)
  candidates=[r for r in season if r['target']==choice['target'] and r.get(metric) not in ('',None)];best=min(candidates,key=lambda r:float(r[metric]));bk=key(best,'seasonal');best26=lookup26.get(bk)
  out.append(dict(target=choice['target'],metric=metric,fixed_2026_choice=choice['procedure_id'],fixed_2026_product=choice['product'],fixed_2026_history=choice['history_regime'],fixed_choice_2026_error=float(choice['ranking_loss']),fixed_choice_older_error=None if not current else float(current[metric]),older_best_procedure=best['procedure_id'],older_best_product=best['product_id'],older_best_history=best['history_regime'],older_best_error=float(best[metric]),older_best_2026_error=None if not best26 else float(best26[metric]),older_supported_n=int(best['n']),older_choice_n=None if not current else int(current['n']),current_supported_n=int(choice['n']),rank_reversal=bool(current and best26 and float(best26[metric])>float(choice['ranking_loss']) and float(best[metric])<float(current[metric])),scientific_limit='Eachseasoninternallymatched; differentevaluationgamesbetweenyears; exposedchoicecomparison, not2026historyeffect orfutureselector'))
 for r in old:
  if 'v2-c02-explicit-lag-block-removal' not in str(r.get('procedure_id')) or product(r) not in ('lower_median','event_probability') or 'STRICT' in str(r.get('policy_id')):continue
  target=r['target'];metric='brier' if target=='anytime_td' else'mae';c02key=key(r,r['_artifact']);leafproc=(s.chart.VERSION if target==s.chart.TARGET else s.laws.VERSION)+':ordered_leaf_cdf';leafkey=(target,leafproc,product(r),r['history_regime']);leaf26=lookup26.get(leafkey);cy,ly=lookupyear.get(c02key),lookupyear.get(leafkey)
  if not(leaf26 and cy and ly):continue
  d26=float(r[metric])-float(leaf26[metric]);dy=float(cy[metric])-float(ly[metric]);reversals.append(dict(target=target,product_id=product(r),history_regime=r['history_regime'],metric=metric,c02_2026_error=float(r[metric]),leaf_2026_error=float(leaf26[metric]),C02_minus_leaf_2026=d26,c02_older_error=float(cy[metric]),leaf_older_error=float(ly[metric]),C02_minus_leaf_older=dy,rank_reversal=d26*dy<0,older_n=int(cy['n']),older_leaf_n=int(ly['n']),current_n=int(r.get('n',r.get('scored_n'))),source2026_artifact=r['_artifact'],source2026_sha256=s.sha(r['_artifact']),negative_favors_C02=True))
 s.emp.write_csv(pub/'FIXED_2026_CHOICE_OLDER_COMPARISON.csv',out);s.emp.write_csv(pub/'C02_SAME_HISTORY_SEASON_REVERSALS.csv',reversals);s.write(pub/'CROSS_SEASON_COMPARISON_RECEIPT.json',dict(state='SOURCE_BOUND_CROSS_SEASON_OBSERVED_CHOICES',code_sha256=s.sha(__file__),older_primary_source_sha256=s.sha(pub/'PRIMARY_PROCEDURE_HISTORY.csv'),reference_choice_sha256=s.sha(a.reference_public/'TOP5_BY_CATEGORY_PRODUCT.csv'),choice_rows=len(out),same_history_C02_rows=len(reversals),reversals=sum(r['rank_reversal'] for r in reversals),new_NFL_fits=0,CURRENT_2026_Week8_outcomes_read=0))
 print(json.dumps(dict(fixed_choices=out,C02_reversals=[r for r in reversals if r['rank_reversal']])))
if __name__=='__main__':main()
