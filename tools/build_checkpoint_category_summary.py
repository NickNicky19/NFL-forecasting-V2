#!/usr/bin/env python3
"""Exposed same-row family representatives, never a live selection policy."""
import collections,csv,json,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
OUT=ROOT/'reports/continuation-20261030'
TARGETS=('pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','nick-chart-ppr-v1','anytime_td')

def number(x):return None if x in (None,'') else float(x)
def family(row,path):
 if 'hgb-history' in path or 'count-ablation' in path:return 'HGB'
 name=row.get('procedure_family_id','')
 if 'leaf' in name:return 'ORDERED_LEAF_CDF'
 if 'glm' in name:return 'GLM_LAW'
 return 'EMPIRICAL'

def main():
 correction_artifact='reports/continuation-20261030/chart-grid-precision-correction-v1/SCORES.json'
 correction_dims=('record_id','procedure_id','history_regime','policy_id','target','population','product_id','week','season','position','fallback_view','cohort_id')
 corrected={}
 if (ROOT/correction_artifact).exists():
  for r in json.loads((ROOT/correction_artifact).read_text()):
   corrected[(r['supersedes_score_artifact'],tuple(r['supersedes_source_identity'].get(k)for k in correction_dims))]=r
 specs=[('reports/continuation-20261029/history-diagnostic-v1/HISTORY_COMPARISON_2026_W1_W7.csv','csv'),
        ('reports/continuation-20261029/hgb-history-v1/SCORES.json','json'),
        ('reports/continuation-20261030/distribution-wave-v2/SCORES.json','json'),
        ('reports/continuation-20261030/count-ablation-wave-v1/SCORES.json','json'),
        ('reports/continuation-20261030/chart-wave-v1/SCORES.json','json'),
        ('reports/continuation-20261030/chart-wave-v1/EMPIRICAL_SCORES.json','json')]
 candidates=[]
 for artifact,kind in specs:
  p=ROOT/artifact
  if not p.exists():continue
  rows=list(csv.DictReader(p.open(newline=''))) if kind=='csv' else json.loads(p.read_text())
  for r in rows:
   if (r.get('population')!='primary' or str(r.get('season',2026))!='2026' or str(r.get('week'))!='ALL'
       or r.get('position','ALL')!='ALL' or r.get('fallback_view','ALL')!='ALL'):continue
   product=r.get('product_id',r.get('product',r.get('objective')))
   if not product:raise ValueError('missing product')
   n=int(r.get('n',r.get('scored_n',0)))
   if not n:continue
   correction=corrected.get((artifact,tuple(r.get(k)for k in correction_dims)))
   if correction:r=dict(r,**{k:correction[k]for k in correction['precision_counts_exact_grid']})
   candidates.append(dict(target=r['target'],family=family(r,artifact),procedure_id=r.get('procedure_id','empirical-player-history-control-v1' if kind=='csv' else 'hgb-direct-history-controls-v1:'+r.get('objective','')),
    product=product,history_regime=r['history_regime'],information_policy=r.get('information_policy','COMMON-2022-MEMORY' if 'hgb' in artifact else 'per-arm outcome history'),
    n=n,mae=number(r.get('mae')),mse=number(r.get('mse')),rmse=number(r.get('rmse')),brier=number(r.get('brier')),CRPS=number(r.get('CRPS')),
    abs_le_1=number(r.get('abs_le_1')),abs_lt_1=number(r.get('abs_lt_1')),abs_le_5=number(r.get('abs_le_5')),abs_lt_10=number(r.get('abs_lt_10')),abs_le_10=number(r.get('abs_le_10')),
    fallback_rows=int(float(r.get('fallback_n',r.get('fallback_rows',0)) or 0)),forecast_rows=int(r.get('forecast_queries',r.get('forecast_rows',n))),
    source_artifact=artifact,precision_source_artifact=correction_artifact if correction else artifact,precision_status='exact_integer_chart_grid_median'if correction else'original_registered_precision',scientific_state='exposed observed family minimum; not a frozen selector',source_record=r.get('record_id')))
 rankings=[]
 for target in TARGETS:
  source=[r for r in candidates if r['target']==target]
  # Counts must agree before claiming this is a matched primary population.
  if len({r['n'] for r in source})!=1:raise ValueError('unmatched supported counts for '+target)
  for product,metric in [('display_point','brier' if target=='anytime_td' else 'mae'),('intended_mean','mse'),('forecast_law','CRPS')]:
   if target=='anytime_td' and product=='intended_mean':continue
   pool=[r for r in source if r.get(metric) is not None and (product!='intended_mean' or 'mean' in r['product'])]
   if not pool:continue
   reps=[]
   for fam in sorted({r['family'] for r in pool}):
    rs=[r for r in pool if r['family']==fam];best=min(rs,key=lambda r:(r[metric],r['procedure_id'],r['history_regime'],r['product']))
    reps.append(dict(best,ranking_product=product,ranking_metric=metric,ranking_loss=best[metric],family_ties_within_1e12=sum(math.isclose(r[metric],best[metric],abs_tol=1e-12,rel_tol=0) for r in rs)))
   reps.sort(key=lambda r:(r['ranking_loss'],r['family']));last=None;rank=0
   for i,r in enumerate(reps):
    if last is None or not math.isclose(r['ranking_loss'],last,abs_tol=1e-12,rel_tol=0):rank=i+1
    r['rank']=rank;last=r['ranking_loss'];rankings.append(r)
 fields=list(dict.fromkeys(k for r in rankings for k in r))
 with (OUT/'TOP5_BY_CATEGORY_PRODUCT.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rankings)
 (OUT/'TOP5_BY_CATEGORY_PRODUCT.json').write_text(json.dumps(rankings,indent=2,allow_nan=False)+'\n')
 lines=['# Twelve-category checkpoint: observed family representatives','',
  'Up to four distinct families are represented, never padded to five. Original losses, all fixed variants and fallbacks remain in the permanent index. These exposed minima choose product/history/settings after examining Weeks1–7 errors; they are not an earlier-frozen method-selection policy.',
  '', 'Primary populations/labels are matched within each target. Counts alone do not prove identity: retained-row independent comparisons provide that check. Chart uses its separate qualified partial-label panel; rare/missing cases remain in coverage. Different units/populations prevent ranking categories by raw MAE. Native-point, intended-mean MSE and proper-law CRPS ranks stay separate in the CSV.',
  '', '| Target | n | Lowest observed family / product / history | Primary error | Empirical recent-mean reference | Baseline-relative skill |','|---|---:|---|---:|---:|---:|']
 for target in TARGETS:
  wins=[r for r in rankings if r['target']==target and r['ranking_product']=='display_point' and r['rank']==1]
  refs=[r for r in candidates if r['target']==target and r['family']=='EMPIRICAL' and r['history_regime']=='H-RECENT' and ('mean' in r['product'] or target=='anytime_td')]
  if not wins or not refs:continue
  metric='brier' if target=='anytime_td' else 'mae';ref=refs[0][metric]
  if not ref or ref<=0:raise ValueError('nonpositive baseline loss denominator')
  winner=wins[0];skill=1-winner['ranking_loss']/ref
  lines.append(f"| {target} | {winner['n']} | {'; '.join(r['family']+' / '+r['product']+' / '+r['history_regime'] for r in wins)} | {winner['ranking_loss']:.6f} | {ref:.6f} | {skill:.2%} |")
 lines+=['','Skill here is `1 - procedure loss / fixed empirical H-RECENT mean loss`, on the same supported outcomes. TD uses event Brier. This is a declared nonzero baseline-loss denominator, not error divided by actual production or percentage prediction accuracy. It is descriptive current-season skill; no significance, permanent optimality or live policy claim follows.',
  '', 'The upcoming shadow shortlist contains the executable captured empirical, ordered-leaf, GLM-law and HGB versions for their supported targets. Chart has empirical/leaf/GLM shadows only, with unresolved rare-label qualification. The owner’s existing production stream remains unchanged; none of these research ranks means admission, official capture or deployment.',
  '', 'Seven week clusters limit uncertainty; paired learned-only, shared prior-workload/top-player bands, strict-current information and adverse extended-role effects remain separate evidence. Authentic priced offers, source-vintage/finality checks for future labels, additional legacy families and rolling older-season tests for new learned procedures remain open.','']
 (OUT/'TWELVE_CATEGORY_SUMMARY.md').write_text('\n'.join(lines))
 print(json.dumps(dict(candidate_views=len(candidates),family_representatives=len(rankings),targets=12,families=sorted({r['family'] for r in candidates}))))
if __name__=='__main__':main()
