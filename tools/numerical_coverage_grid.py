"""Exact recipe/year coverage projection from valid retained numerical scores."""
import argparse,csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.numerical_championship import choices_older,key,csvwrite,SEASONS
from tools.chronological_category_selector import eligible
from tools.build_current_valid_view_v2 import recipe
from nfl_v2.shared_subgroups import write,sha

def main(a):
 m=json.loads((a.root/'reports/continuation-20261030d/current-ranking-v2/current-valid-results/CURRENT_MANIFEST.json').read_bytes());by={};bindings=[]
 for part in m['csv_parts']:
  p=a.root/part['path']
  if sha(p)!=part['sha256']:raise ValueError('canonical current shard changed')
  bindings.append(dict(path=part['path'],sha256=part['sha256']))
  with p.open()as f:
   for r in csv.DictReader(f):
    if r['season']!='2026'or r['week']!='ALL'or r['population']!='primary'or r['position']not in('','ALL')or r['fallback_view']not in('','ALL')or r.get('cohort_id')or not recipe(r):continue
    if r['evidence']!='NEW_EXPERIMENT'and r['source_artifact']!='reports/continuation-20261030/chart-grid-precision-correction-v1/SCORES.json':continue
    r=dict(r,target=r['category']);k=key(r)
    if(2026,k)in by:raise ValueError('duplicate canonical exact recipe')
    by[2026,k]=r
 for y in SEASONS[1:]:
  for r in choices_older(a.root,y):
   # A single exact forecast row serves several ranking products; count once.
   k=key(r)
   if(y,k)in by:continue
   by[y,k]=r
 union=sorted({k for year,k in by});out=[]
 for k in union:
  target,proc,history,product=k
  for year in SEASONS:
   r=by.get((year,k));state='COMPLETED_VALID'if r else'FIT_REQUIRED';reason=None if r else'Exact procedure/history/output has no retained complete-period numerical score; no alias or base-method substitution.'
   if r and year==2022 and history=='H-RECENT':state='COMPLETED_PARTIAL';reason='Available2022-only proxy retained; exact preceding2021 RECENT arm remains SOURCE_BLOCKED under separately required source extension.'
   out.append(dict(procedure_id=proc,target=target,history_regime=history,product_id=product,season=year,weeks=list(range(1,8 if year==2026 else 19)),forecast_product='event_probability'if target=='anytime_td'else'numeric_point'+(' and retainedlaw'if product=='lower_median'and r and r.get('CRPS',r.get('crps'))not in(None,'')else''),information_policy='STRICT_CURRENT_INFORMATION'if'strict'in proc.lower()else'CURRENT_FITTING_OR_MULTISEASON_WITH_REGISTERED_OLDER_FEATURE_MEMORY',horizon='per-game kickoff reconstruction; not T90 original issue',evaluation_policy='primary retrospective participant/stat-row; fullsystem; allsupportedlabels',state=state,missing_reason=reason,n=None if not r else int(r['n']),forecast_rows=None if not r else r.get('forecast_rows',r.get('forecast_or_offered_rows')),fallback_rows=None if not r else r.get('fallback_rows'),mae=None if not r else r.get('mae'),mse=None if not r else r.get('mse'),brier=None if not r else r.get('brier'),CRPS=None if not r else r.get('CRPS',r.get('crps')),source_artifact=None if not r else r['source_artifact'],new_fits=0))
 write(a.output/'NUMERICAL_COVERAGE_GRID.json',out);csvwrite(a.output/'NUMERICAL_COVERAGE_GRID.csv',out);write(a.output/'NUMERICAL_COVERAGE_SOURCES.json',dict(current_shards=bindings,oldsource='Frozen original seasonal source artifacts and2025 continuity overlay in numerical FROZEN_PROTOCOL/specs; original bytes preserved',scope='Accessible executed V2 numerical library only; original60pathway/unrestoredlegacy grid remains parent registry; outputviews are not distinct learners.'))
 print(json.dumps(dict(exact_target_history_output_recipes=len(union),coverage_cells=len(out),completed_valid=sum(r['state']=='COMPLETED_VALID'for r in out),completed_partial=sum(r['state']=='COMPLETED_PARTIAL'for r in out),fit_required=sum(r['state']=='FIT_REQUIRED'for r in out))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a)
