"""Readable side tables and weighted period summaries of registered score views."""
import argparse,collections,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import write,sha,now
from tools.numerical_championship import csvwrite
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT/'reports/completion-20261031g/roster'
PANELS={'F7':('w7-method-comparison-v2','fixed-w7-complete-leaf-law-v1'),'W6':('w6-rolling-method-comparison-v1','w6-complete-leaf-law-v1'),'W7':('w7-rolling-method-comparison-v1','w7-complete-leaf-law-v1')}

def main(a):
 out=a.output
 if out.exists():raise ValueError('fresh report projection required')
 out.mkdir(parents=True);wide=[];native=[];sources=[]
 for panel,(parent,leaf)in PANELS.items():
  by=collections.defaultdict(dict)
  for name,isleaf in((parent,False),(leaf,True)):
   folder=BASE/name;paths=[folder/'SCORES.json']+[ROOT/r['path']for r in json.loads((folder/'SUPPLEMENTAL_SCORE_ARTIFACTS.json').read_bytes())]
   for path in paths:
    digest=sha(path);sources.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=digest,panel=panel))
    for idx,r in enumerate(json.loads(path.read_bytes())):
     proc=r['procedure_id'];isoldleaf=('ordered_leaf_cdf'in proc or'c02'in proc)and not isleaf
     if r['record_kind']=='prop_selection_evaluation':
      if isoldleaf and r.get('decision_rule')=='P2':continue
      key=(r['method_id'],r['target'],r['cohort_id'],r.get('K'),r.get('rank_scope'));by[key][r['side']]=dict(r,source_artifact=path.relative_to(ROOT).as_posix(),source_row_index=idx,source_sha256=digest)
     elif not(isoldleaf and r['record_kind']=='prop_threshold_probability_evaluation'):native.append(dict(r,panel=panel,source_artifact=path.relative_to(ROOT).as_posix(),source_row_index=idx,source_sha256=digest))
  for key,sides in by.items():
   if set(sides)!={'over','under','Combined'}:raise ValueError('missing side bucket')
   c=sides['Combined'];row=dict(panel=panel,target=c['target'],procedure_id=c['procedure_id'],history_regime=c['history_regime'],product_id=c['product_id'],decision_rule=c.get('decision_rule','CONTROL'),method_id=c['method_id'],cohort_id=c['cohort_id'],K=c.get('K'),rank_scope=c.get('rank_scope'),week=c['week'],evaluation_weeks=c['evaluation_weeks'],evidence='RETROSPECTIVE_RULE_REPLAY_NOT_ORIGINAL_ISSUANCE',eligible_opportunities=c['selection_metrics']['selection_pool_count'],admitted_forecasts=c['selection_metrics'].get('admitted_forecast_opportunities'),forecast_unavailable=c['selection_metrics'].get('unavailable_forecast_opportunities'),admitted_rule_abstentions=c['selection_metrics'].get('admitted_rule_abstentions'),unique_games=c['unique_games'],prices=None,EV=None,ROI=None,CLV=None,price_missing_reason='NO_QUALIFIED_PRICE_OR_SPORTSBOOK_SETTLEMENT',source_refs=[])
   for side,name in(('over','Over'),('under','Under'),('Combined','Combined')):
    r=sides[side];m=r['selection_metrics'];counts=m['status_counts'];row.update({name+'_selected':r['forecast_rows'],name+'_wins':counts['WIN'],name+'_losses':counts['LOSS'],name+'_decided':counts['WIN']+counts['LOSS'],name+'_hit_rate':counts['WIN']/(counts['WIN']+counts['LOSS'])if counts['WIN']+counts['LOSS']else None,name+'_push':counts['PUSH'],name+'_void':counts['VOID'],name+'_pending':counts['PENDING'],name+'_unknown_participation':counts['UNKNOWN_PARTICIPATION'],name+'_missing_actual':counts['MISSING_ACTUAL'],name+'_unresolved_contract':counts['UNRESOLVED_CONTRACT'],name+'_uncertainty':m['game_uncertainty']});row['source_refs'].append(dict(source_artifact=r['source_artifact'],source_sha256=r['source_sha256'],source_row_index=r['source_row_index'],record_id=r['record_id']))
   for suffix in('selected','wins','losses','decided','push','void','pending','unknown_participation','missing_actual','unresolved_contract'):
    if row['Combined_'+suffix]!=row['Over_'+suffix]+row['Under_'+suffix]:raise ValueError('side reconciliation fails')
   wide.append(row)
 write(out/'ALL_WEEKLY_METHOD_SIDE_TABLES.json',wide);csvwrite(out/'ALL_WEEKLY_METHOD_SIDE_TABLES.csv',wide);write(out/'ALL_NATIVE_AND_PROPER_PRODUCTS.json',native);csvwrite(out/'ALL_NATIVE_AND_PROPER_PRODUCTS.csv',native)
 # Cumulative means W6+W7 rolling only, one source per game/offer; F7 excluded.
 cumgroups=collections.defaultdict(list)
 for r in wide:
  if r['panel']in('W6','W7')and not r['procedure_id'].startswith('MATCHED_RETAINED_CONTROL:'):
   k=tuple(r[x]for x in('target','procedure_id','history_regime','product_id','decision_rule','cohort_id','K','rank_scope'));cumgroups[k].append(r)
 cumulative=[]
 for k,rr in sorted(cumgroups.items(),key=lambda x:str(x[0])):
  if len({r['panel']for r in rr})!=len(rr):raise ValueError('duplicate version in cumulative panel')
  z={name:value for name,value in zip(('target','procedure_id','history_regime','product_id','decision_rule','cohort_id','K','rank_scope'),k)};z.update(panel='2026_W6_W7_ROLLING_CUMULATIVE_NOT_FULL_W1_W7',evaluation_weeks=[6,7],weeks_with_rows=sorted(r['week']for r in rr),missing_current_periods=[1,2,3,4,5],cumulative_definition='Sumunderlyingweeklycounts;Kisperweek; noFfixedW7overlap or seasonaliases counted.',eligible_opportunities=sum(r['eligible_opportunities']for r in rr),admitted_forecasts=sum(r['admitted_forecasts']or 0 for r in rr),forecast_unavailable=sum(r['forecast_unavailable']or 0 for r in rr),admitted_rule_abstentions=sum(r['admitted_rule_abstentions']or 0 for r in rr),source_refs=[ref for r in rr for ref in r['source_refs']],uncertainty='Twoobservedweeks: insufficientweekclusters; no recomputedpooledgameinterval fromweeklyaggregatecounts; per-week gameintervals retained.',prices=None,EV=None,ROI=None,CLV=None)
  for name in('Over','Under','Combined'):
   for suffix in('selected','wins','losses','decided','push','void','pending','unknown_participation','missing_actual','unresolved_contract'):z[name+'_'+suffix]=sum(r[name+'_'+suffix]for r in rr)
   z[name+'_hit_rate']=z[name+'_wins']/z[name+'_decided']if z[name+'_decided']else None
  cumulative.append(z)
 write(out/'CUMULATIVE_W6_W7_METHOD_SIDE_TABLES.json',cumulative);csvwrite(out/'CUMULATIVE_W6_W7_METHOD_SIDE_TABLES.csv',cumulative)
 ng=collections.defaultdict(list)
 for r in native:
  if r['panel']in('W6','W7'):ng[r['target'],r['procedure_id'],r['history_regime'],r['product_id'],r['record_kind']].append(r)
 pooled=[]
 for k,rr in ng.items():
  z={name:v for name,v in zip(('target','procedure_id','history_regime','product_id','record_kind'),k)};n=sum(r['n']for r in rr);z.update(n=n,evaluation_weeks=[6,7],weeks_with_rows=sorted(r['week']for r in rr),current_missing_weeks=[1,2,3,4,5],source_refs=[dict(artifact=r['source_artifact'],sha256=r['source_sha256'],row_index=r['source_row_index'],record_id=r['record_id'])for r in rr],definition='sum(n*loss)/sum(n); no meanof weeklypercentages; current-vintage retrospectiveactual-offerpanel, not originalissuance')
  for metric in('mae','mse','brier','log_loss'):
   if any(r.get(metric)=='Infinity'for r in rr):z[metric]='Infinity'
   elif all(isinstance(r.get(metric),(int,float))for r in rr):z[metric]=math.fsum(r['n']*r[metric]for r in rr)/n if n else None
   else:z[metric]=None
  z['rmse']=math.sqrt(z['mse'])if isinstance(z['mse'],(int,float))else None;pooled.append(z)
 write(out/'CUMULATIVE_W6_W7_NATIVE_AND_PROPER.json',pooled);csvwrite(out/'CUMULATIVE_W6_W7_NATIVE_AND_PROPER.csv',pooled)
 # Raw observed maxima remain visible, with exact support and side pools.
 winners=[]
 for panel in PANELS:
  for target in sorted({r['target']for r in wide}):
   rr=[r for r in wide if r['panel']==panel and r['target']==target and r['cohort_id']=='ALL'and r['K']is None and not r['procedure_id'].startswith('MATCHED_RETAINED_CONTROL:')]
   for side in('Over','Under','Combined'):
    supported=[r for r in rr if r[side+'_decided']]
    if not supported:continue
    best=max(r[side+'_hit_rate']for r in supported)
    for r in supported:
     if abs(r[side+'_hit_rate']-best)<=1e-12:winners.append(dict(panel=panel,target=target,side=side,procedure_id=r['procedure_id'],history_regime=r['history_regime'],product_id=r['product_id'],decision_rule=r['decision_rule'],wins=r[side+'_wins'],losses=r[side+'_losses'],decided=r[side+'_decided'],hit_rate=best,full_offer_universe=r['eligible_opportunities'],admitted_forecasts=r['admitted_forecasts'],selection_limit='Raw exposed maximum; unequal sidepools/support andmultiplicity; no posthoc supportgate or releaseclaim'))
 write(out/'OBSERVED_RAW_SIDE_MAXIMA.json',winners);csvwrite(out/'OBSERVED_RAW_SIDE_MAXIMA.csv',winners)
 lines=['# Actual-method threshold comparisons: Weeks6and7','', 'These comparisons execute the forecasting procedures at retained actual provider-labelled thresholds. Numerical points, legitimate line probabilities and selected-side hit rates remain separate. They use current/revised football inputs under the registered seven-day availability assumption plus authenticated pregame snapshot context/clocks. They are retrospective reconstructions, not recovered original model issuance or verified sportsbook settlement. Prices/EV/ROI/CLV remain unavailable.','', 'The rolling panels cover all14games inWeek6 (**670offers**) and all14games inWeek7 (**649offers**). The older fixed-Friday13-gameWeek7panel (**462offers**) remains separate. The cumulative view sums only the rolling W6+W7panels:1319offers across28games. Weeks1–5actual-offer method comparisons remain absent; this is **not full2026Weeks1–7 or season-to-date completion**.','', '## Example of an actual method gain and an adverse expansion','', 'On the fixed-Friday Week7passing-attempt panel, H-MULTI C02lower-median P1 wins14/20(70%) versus baseLeaf11/20(55%) on identical admitted offers. The larger rolling Week7panel changes C02to16/25(64%). In rolling Week6 it wins11/27(40.74%). This preserves a seasonal/week reversal and prevents the favorable fixed slice from becoming a universal winner.','', '| C02 H-MULTI lower-median P1 category | W6 Over W/L | W6 Under W/L | W6 Combined | W7 Over W/L | W7 Under W/L | W7 Combined | W6–7 weighted Combined |','|---|---|---|---|---|---|---|---|']
 for target in sorted({r['target']for r in cumulative}):
  def chosen(panel):return next(r for r in wide if r['panel']==panel and r['target']==target and 'c02'in r['procedure_id']and r['history_regime']=='H-MULTI'and r['product_id']=='lower_median'and r['decision_rule']=='P1'and r['cohort_id']=='ALL'and r['K']is None)
  aa,bb=chosen('W6'),chosen('W7');w=aa['Combined_wins']+bb['Combined_wins'];n=aa['Combined_decided']+bb['Combined_decided'];cells=[]
  for r in(aa,bb):cells.extend([f"{r['Over_wins']}/{r['Over_losses']} (n={r['Over_decided']})",f"{r['Under_wins']}/{r['Under_losses']} (n={r['Under_decided']})",f"{r['Combined_wins']}/{r['Combined_decided']} ({100*r['Combined_hit_rate']:.2f}%)"if r['Combined_hit_rate']is not None else'N/A'])
  lines.append('| '+target+' | '+' | '.join(cells)+f' | {w}/{n} ({100*w/n:.2f}%) |')
 lines+=['','Side buckets use the side selected before the outcome. Combined percentages are wins divided by total decided Over+Under picks, never averages of side percentages. Full readable machine tables retain every method/history/output/rule/cohort/K row, losses, pushes, unknowns, coverage and abstentions; zero decided picks stay N/A. The example is a named fixed control, not an assertion that it wins all categories.','', '## Where to find every winner and loss','', '[All weekly method/strategy/Over/Under/Combined rows](ALL_WEEKLY_METHOD_SIDE_TABLES.csv) include source score IDs/hashes, numerators, denominators and per-week game-cluster uncertainty. [All cumulative rows](CUMULATIVE_W6_W7_METHOD_SIDE_TABLES.csv) preserve per-week K policies and subgroup memberships. [Raw observed side maxima](OBSERVED_RAW_SIDE_MAXIMA.csv) show all tied maxima with exact sample sizes, including very small selected pools. Unequal selected pools and research multiplicity prevent their raw percentages from being a pure learner comparison or automatic release recommendation.','', '[Native point and proper line-probability products](ALL_NATIVE_AND_PROPER_PRODUCTS.csv) keep MAE separate from half-multiclass Brier/log loss. [Cumulative native/proper products](CUMULATIVE_W6_W7_NATIVE_AND_PROPER.csv) use sum(n×loss)/sum(n). Means/medians are output recipes, not independent learners. Both sides, alternate rules and overlapping cohorts are dependent NFL observations.','', 'Complete baseLeaf/C02 laws now come from saved leaf IDs and verified retained support/histograms plus the original5%full-support prior, with no fitted-model predict/apply or refits. Their complete-law coverage version supersedes the old fallback-only P2view as the default comparable product; every old partial view remains in the audit. GLM/other retained complete parametric laws remain included. D1/D2learned laws await their own model recovery; complete fallback-only probabilities remain explicitly partial.','', 'P2chooses the larger conditional-appearance win probability, retains push mass and abstains on ties. Proper scores cover all qualified laws, including direction ties; selected-side/cohort/K diagnostics are separate. This does not authenticate bookmaker nonvoid conditioning or price-aware value.','', 'Every listed top-K policy is selectable under its registered horizon: the fixed Fpanel is a partial-week as-of reconstruction; new rolling panels rank only candidates available at each source-clock batch and consume remaining weekly slots. Top6/10/20is percategory, with separate combined/Over-only/Under-only pools. Later snapshots are never combined into an originally issued weekly list.','', 'Research ranks and scientific claims remain separate from operational eligibility under the retained owner’s existing admission policy. Exact target/source, restored model/input evidence, deterministic runtime, missing/stale-source fallback and rollback still need their applicable operational checks. This report introduces no new universal holdout gate or waiting period, and changes no website selection or publisher.']
 (out/'README.md').write_text('\n'.join(lines)+'\n');write(out/'REPORT_RECEIPT.json',dict(at=now(),source_scores=sources,default_projection='ParentP1andnonleafP2 retained; matchingcompleteLeaf/C02P2 replacesoldpartialfallbackonlydefault; oldauditunchanged',weekly_side_rows=len(wide),cumulative_side_rows=len(cumulative),native_products=len(native),cumulative_native_products=len(pooled),raw_side_maxima=len(winners),new_fits=0,new_direction_grades=0,new_CDF_evaluations=0,new_issued_forecasts=0,new_NFL_observations=0,script_sha256=sha(__file__)));print(json.dumps(dict(weekly_rows=len(wide),cumulative_rows=len(cumulative),native_products=len(native),raw_maxima=len(winners))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);main(p.parse_args())
