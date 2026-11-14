"""Verify consolidated awards/aggregates against bound canonical main score records."""
import argparse,collections,hashlib,importlib.util,json,math
from pathlib import Path
sp=importlib.util.spec_from_file_location('p',Path(__file__).with_name('check_w7_methods.py'));p=importlib.util.module_from_spec(sp);sp.loader.exec_module(p)
read,sha,close=p.read,p.sha,p.close

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();pub=a.root/'reports/completion-20261031g';bind=read(pub/'REPORT_BINDINGS.json');cache={};rawsel=[];rawprob=[]
 for b in bind['sources']:
  path=a.root/b['path'];h=sha(path);assert h==b['sha256'];rows=cache.setdefault(b['path'],read(path));excluded={tuple(x)for x in b.get('exclude_partial_leaf_signatures',[])}
  for r in rows:
   if(r['record_kind']=='prop_threshold_probability_evaluation'or(r['record_kind']=='prop_selection_evaluation'and r.get('decision_rule')=='P2'))and(r.get('target'),r.get('procedure_id'),r.get('history_regime'))in excluded:continue
   if str(r.get('method_id',r.get('strategy',''))).startswith('CONTROL-'):continue
   if b['role']=='rolling_selection'and r['record_kind']=='prop_selection_evaluation'and r.get('cohort_id','ALL')=='ALL'and r.get('K')is None and r.get('rank_scope')is None:rawsel.append((r,b['path']))
   if b['role']=='rolling_probability'and r['record_kind']=='prop_threshold_probability_evaluation':rawprob.append((r,b['path']))
 def sk(r):return(r['target'],r['procedure_id'],r.get('history_regime'),r.get('product_id'),r.get('decision_rule',r.get('strategy')),r['side'])
 groups=collections.defaultdict(list)
 for r,path in rawsel:groups[sk(r)].append((r,path))
 claimed=read(pub/'ROLLING_CUMULATIVE_SELECTION_RESULTS.json');assert len(claimed)==len(groups)
 for r in claimed:
  rr=groups[sk(r)];assert len({v['week']for v,_ in rr})==len(rr);m=[v['selection_metrics']for v,_ in rr];assert r['source_records']==[dict(path=path,record_id=v['record_id'])for v,path in rr];assert r['weeks']==sorted(v['week']for v,_ in rr)
  for dst,src in [('n','n'),('selected','forecast_rows')]:assert r[dst]==sum(v[src]for v,_ in rr)
  for dst,src in [('wins','WIN'),('losses','LOSS')]:assert r[dst]==sum(v[src]for v in m)
  close(r['hit_rate'],r['wins']/r['n']if r['n']else None);assert r['eligible']==sum(v.get('full_offer_universe',v['selection_pool_count'])for v in m);adm=sum(v['admitted_forecast_opportunities']for v in m)if all('admitted_forecast_opportunities'in v for v in m)else None;assert r['admitted']==adm;close(r['coverage'],r['selected']/r['eligible']if r['eligible']else None);ct=collections.Counter()
  for v in m:ct.update(v['status_counts'])
  assert r['status']==dict(ct)
 pg=collections.defaultdict(list)
 for r,path in rawprob:pg[(r['target'],r['procedure_id'],r.get('history_regime'),r.get('product_id'))].append((r,path))
 probs=read(pub/'ROLLING_CUMULATIVE_PROBABILITY_RESULTS.json');assert len(probs)==len(pg)
 for r in probs:
  rr=pg[r['target'],r['procedure_id'],r.get('history_regime'),r.get('product_id')];assert len(set(v['week']for v,_ in rr))==len(rr);n=sum(v['n']for v,_ in rr if v.get('brier')is not None);assert r['n']==n and r['eligible']==sum(v['forecast_rows']for v,_ in rr);close(r['brier'],math.fsum(v['n']*v['brier']for v,_ in rr if v.get('brier')is not None)/n if n else None);close(r['coverage'],n/r['eligible']if r['eligible']else None)
 def maxima(rr,key,minimum=False):
  rr=[r for r in rr if r[key]is not None and r['n']];full=[r for r in rr if r['weeks']==[6,7]];rr=full or rr
  if not rr:return[]
  best=(min if minimum else max)(r[key]for r in rr);return sorted([r for r in rr if abs(r[key]-best)<=1e-12],key=lambda r:(-r['n'],r['procedure_id'],str(r.get('product_id'))))
 f=read(a.root/'reports/championship-20261030f/CATEGORY_CHAMPIONS.json');fw={r['category']:r for r in f};decisions=read(pub/'EXECUTIVE_CATEGORY_DECISIONS.json');assert len(decisions)==12
 for r in decisions:
  cat=r['category'];assert r['current_numerical']==fw[cat]['best_numeric_including_registered_category_policies'];assert r['numerical_static_leaders']==fw[cat]['numeric_leaders']
  for side,dst in [('over','over_maxima'),('under','under_maxima'),('Combined','combined_maxima')]:assert r[dst]==maxima([x for x in claimed if x['target']==cat and x['side']==side],'hit_rate')
  assert r['threshold_probability_maxima']==maxima([x for x in probs if x['target']==cat],'brier',True);assert r['price_aware_state']=='UNESTABLISHED_NO_AUTHENTICATED_PRICE_OR_NONVOID_CONTRACT';assert r['website_improvement_claim'].startswith('UNESTABLISHED_FULL_PERIOD')
 body=(pub/'FULL_CATEGORY_CHAMPIONSHIP_REPORT.md').read_text();assert'Static-procedure point leader'in body and'UNCAPTURED'in(pub/'UPCOMING_POLICY_IDENTITY_NOTE.md').read_text();assert'N/A: recorded/saved source'in body and' / 0 |'not in body;assert'445/801'in body and'236/446'in body and'209/355'in body;assert'fallback-only law subset'in body;assert'not full2026'in body or'No full 2026'in body
 out=dict(state='PASS_INDEPENDENT_ROOT_CHAMPIONSHIP_AGGREGATES_AWARDS_AND_BINDINGS',report_sha256=sha(pub/'FULL_CATEGORY_CHAMPIONSHIP_REPORT.md'),bindings_sha256=sha(pub/'REPORT_BINDINGS.json'),executive_decisions_sha256=sha(pub/'EXECUTIVE_CATEGORY_DECISIONS.json'),categories=len(decisions),rolling_side_aggregate_rows=len(claimed),rolling_probability_products=len(probs),bound_main_score_sources=len(cache),genuine_recorded_admission_unretained_is_null=True,statics_and_composite_policy_numeric_winners_distinct=True,complete_ties_preserved=True,new_fits=0,new_inference=0,new_grades=0,scope='All consolidated source sums/side maxima/proper-score minima and exact source hashes; human source-vintage/release/capture review accompanies this snapshot.',limitations=['Ownselectedpools differ; executable matchedcomparisons are separately bound.','Fulltwo-weeksource groups are preferred for executive awards; one-weekrawmaxima remain separatelyretained.','No price/currentserved/incumbentfullperiod or lifetimeallmethod claim is established.'])
 with a.output.open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps(out))
if __name__=='__main__':main()
