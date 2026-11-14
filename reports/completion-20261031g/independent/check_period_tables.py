"""Stream public score projections and independently sum side/period numerators."""
import argparse,collections,functools,gzip,hashlib,importlib.util,json,math
from pathlib import Path
sp=importlib.util.spec_from_file_location('q',Path(__file__).with_name('check_w7_methods.py'));q=importlib.util.module_from_spec(sp);sp.loader.exec_module(q)
sha,close=q.sha,q.close

def array(path):
 d=json.JSONDecoder();buf=''
 with gzip.open(path,'rt')as f:
  while'['not in buf:buf+=f.read(131072)
  buf=buf[buf.index('[')+1:]
  while True:
   buf=buf.lstrip(' \r\n\t,')
   if buf.startswith(']'):return
   try:r,i=d.raw_decode(buf)
   except json.JSONDecodeError:
    s=f.read(131072)
    if not s:raise
    buf+=s
   else:yield r;buf=buf[i:]

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();p=a.root/'reports/completion-20261031g/roster/actual-method-period-summary-v2';sources=set()
 @functools.lru_cache(maxsize=4)
 def source(path,h):
  f=a.root/path;assert sha(f)==h;sources.add((path,h));return json.loads(f.read_bytes())
 def lookup(z):
  r=source(z.get('source_artifact',z.get('artifact')),z.get('source_sha256',z.get('sha256')))[z.get('source_row_index',z.get('row_index'))];assert r['record_id']==z['record_id'];return r
 fields={'selected':'forecast_rows','decided':'n','wins':'WIN','losses':'LOSS','push':'PUSH','void':'VOID','pending':'PENDING','unknown_participation':'UNKNOWN_PARTICIPATION','missing_actual':'MISSING_ACTUAL','unresolved_contract':'UNRESOLVED_CONTRACT'};weekly=0;cum=0;maxima=collections.defaultdict(list)
 def checks(r,rows):
  by=collections.defaultdict(list)
  for z in rows:by[z['side']].append(z)
  assert set(by)=={'over','under','Combined'}
  for side,name in[('over','Over'),('under','Under'),('Combined','Combined')]:
   for suffix,key in fields.items():
    expected=sum(z[key]if suffix in('selected','decided')else z['selection_metrics']['status_counts'][key]for z in by[side]);assert r[name+'_'+suffix]==expected
   n=r[name+'_decided'];close(r[name+'_hit_rate'],r[name+'_wins']/n if n else None)
  for suffix in fields:assert r['Combined_'+suffix]==r['Over_'+suffix]+r['Under_'+suffix]
  for k in('EV','ROI','CLV','prices'):assert r[k]is None
  assert r['eligible_opportunities']==sum(z['selection_metrics']['selection_pool_count']for z in by['Combined']);assert r['admitted_forecasts']==sum(z['selection_metrics'].get('admitted_forecast_opportunities')or 0 for z in by['Combined'])
 for r in array(p/'ALL_WEEKLY_METHOD_SIDE_TABLES.json.gz'):
  rr=[lookup(z)for z in r['source_refs']];checks(r,rr);weekly+=1
  if r['cohort_id']=='ALL'and r['K']is None and not r['procedure_id'].startswith('MATCHED_RETAINED_CONTROL:'):
   for side in('Over','Under','Combined'):
    if r[side+'_decided']:maxima[r['panel'],r['target'],side].append((r[side+'_hit_rate'],r['procedure_id'],r['history_regime'],r['product_id'],r['decision_rule'],r[side+'_wins'],r[side+'_losses'],r[side+'_decided']))
 for r in array(p/'CUMULATIVE_W6_W7_METHOD_SIDE_TABLES.json.gz'):
  rr=[lookup(z)for z in r['source_refs']];checks(r,rr);assert all('/w7-method-comparison-v2/'not in z['source_artifact']and'/fixed-w7-complete'not in z['source_artifact']for z in r['source_refs']);assert len({(z['week'],z['side'])for z in rr})==len(rr);assert sorted({z['week']for z in rr})==r['weeks_with_rows'];assert r['missing_current_periods']==[1,2,3,4,5];cum+=1
 obs=json.loads((p/'OBSERVED_RAW_SIDE_MAXIMA.json').read_bytes());expected=set()
 for key,vals in maxima.items():
  best=max(v[0]for v in vals)
  for v in vals:
   if math.isclose(v[0],best,abs_tol=1e-12,rel_tol=0):expected.add(key+v[1:])
 actual={(r['panel'],r['target'],r['side'],r['procedure_id'],r['history_regime'],r['product_id'],r['decision_rule'],r['wins'],r['losses'],r['decided'])for r in obs};assert actual==expected
 native=json.loads((p/'CUMULATIVE_W6_W7_NATIVE_AND_PROPER.json').read_bytes())
 for r in native:
  rr=[lookup(z)for z in r['source_refs']];assert r['n']==sum(z['n']for z in rr);assert sorted(z['week']for z in rr)==r['weeks_with_rows'];assert len(set(z['week']for z in rr))==len(rr)
  for k in('mae','mse','brier','log_loss'):
   expected='Infinity'if any(z.get(k)=='Infinity'for z in rr)else math.fsum(z['n']*z[k]for z in rr)/r['n']if r['n']and all(isinstance(z.get(k),(float,int))for z in rr)else None;close(r[k],expected)
  close(r['rmse'],math.sqrt(r['mse'])if isinstance(r['mse'],(float,int))else None)
 assert(weekly,cum,len(native),len(obs))==(85470,24316,716,300)
 report=dict(state='PASS_INDEPENDENT_WEEKLY_AND_CUMULATIVE_SIDE_TABLES_AND_RAW_MAXIMA',weekly_side_rows=weekly,cumulative_side_rows=cum,cumulative_native_probability_products=len(native),raw_side_maxima=len(obs),source_artifacts_checked=len(sources),fixed_Friday_week7_excluded_from_rolling_cumulative=True,side_rates_weighted_from_underlying_counts=True,new_fits=0,new_inference=0,new_grades=0,limitations=['Two rollingweeks are not fullW1–7; exposed side maxima include tinyselectedpools and multiplicity.','Cumulative fullcategory coverage and excludedcohortrows require explicit fieldsemantics; no probability/ROI claim arises from hitrate.','Point/distribution/fullperiod native championship is separate from this retained actual-offer view.'])
 with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report))
if __name__=='__main__':main()
