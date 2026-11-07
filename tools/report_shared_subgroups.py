"""Readable twelve-target projection; no new model or subgroup selection rule."""
import argparse,csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import load,write,sha,C02,CHART

def run(public_root,canonical_candidate_scores,comparison_root=None):
 root=Path(public_root);out=Path(comparison_root)if comparison_root else root;p=load(root/'FROZEN_PROTOCOL.json');cp=load(out/'FROZEN_PROTOCOL.json');scores=load(root/'SCORES.json');packet=load(out/'PAIRED_COMPARISONS.json');cs=Path(canonical_candidate_scores)
 if packet['source_score_sha256']!=sha(root/'SCORES.json'):raise ValueError('comparison source changed')
 byid={r['record_id']:r for r in scores};comp={}
 for r in packet['rows']:comp.setdefault(r['source_record_id'],[]).append(r)
 with open(p['candidate_minima_artifact'])as f:chosen=list(csv.DictReader(f))
 native=[]
 for choose in chosen:
  t=choose['target'];policy=choose['candidate_policy'];product=choose['candidate_product'];proc=C02+(':strict-current-inputs'if policy=='H-CURRENT-STRICT'else':common-feature-memory')
  for r in scores:
   if(r['target'],r['population'],r['policy_id'],r['product_id'],r['procedure_id'])!=(t,'primary',policy,product,proc):continue
   old=[x for x in comp.get(r['record_id'],[])if x['purpose']=='display_point'and x['old_full_primary_rank']==1]
   if not old:raise ValueError('missing frozen strongest comparator')
   c=old[0];native.append(dict(target=t,policy_id=policy,product_id=product,cohort_id=r['cohort_id'],fallback_view=r['fallback_view'],candidate_n=r['n'],forecast_rows=r['forecast_rows'],fallback_rows=r['fallback_rows'],candidate_error=r['brier']if t=='anytime_td'else r['mae'],paired_n=c['paired_n'],comparator_procedure_id=c.get('comparator_procedure_id'),comparator_history_regime=c.get('comparator_history_regime'),comparator_product_id=c.get('comparator_product_id'),comparator_error=c.get('comparator_error'),absolute_error_delta=c.get('absolute_error_delta'),relative_error_delta=c.get('relative_error_delta'),uncertainty=c.get('uncertainty'),source_record_id=r['record_id'],status=c['status']))
 # Freeze the candidate law and genuine-mean view from its earlier full-panel
 # scores, rather than choosing again on any new subgroup's outcomes.
 old=load(cs);selected=[]
 for target in [r['target']for r in chosen]:
  for purpose,metric in [('forecast_law','brier'if target=='anytime_td'else'CRPS'),('intended_mean','mse')]:
   if target=='anytime_td'and purpose=='intended_mean':continue
   rows=[r for r in old if r['target']==target and r['population']=='primary'and r['week']=='ALL'and r['position']=='ALL'and r['fallback_view']=='ALL'and r['product_id']==('event_probability'if target=='anytime_td'else'mean')and r.get(metric)is not None]
   frozen=min(rows,key=lambda r:(r[metric],r['policy_id']))
   for r in scores:
    if(r['target'],r['population'],r['policy_id'],r['product_id'],r['procedure_id'])!=(target,'primary',frozen['policy_id'],frozen['product_id'],frozen['procedure_id']):continue
    refs=[x for x in comp.get(r['record_id'],[])if x['purpose']==purpose and x['old_full_primary_rank']==1]
    if not refs:raise ValueError('missing mean/law rank1 comparator')
    c=refs[0];selected.append(dict(target=target,purpose=purpose,metric=c['metric'],policy_id=r['policy_id'],cohort_id=r['cohort_id'],fallback_view=r['fallback_view'],paired_n=c['paired_n'],candidate_error=c.get('candidate_error'),comparator_error=c.get('comparator_error'),absolute_error_delta=c.get('absolute_error_delta'),comparator_procedure_id=c.get('comparator_procedure_id'),source_record_id=r['record_id'],status=c['status']))
 for name,rows in [('CATEGORY_POINT_SUBGROUP_SUMMARY.csv',native),('CATEGORY_MEAN_LAW_SUBGROUP_SUMMARY.csv',selected)]:
  with(out/name).open('x',newline='')as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows({k:json.dumps(v,sort_keys=True)if isinstance(v,(dict,list))else v for k,v in r.items()}for r in rows)
 def cell(rows,target,cohort,view='full_system',purpose=None):
  rs=[r for r in rows if r['target']==target and r['cohort_id']==cohort and r['fallback_view']==view and(purpose is None or r.get('purpose')==purpose)]
  if not rs:return '—'
  r=rs[0];v=r.get('absolute_error_delta');return '—'if v is None else f"{v:+.4f} ({r['paired_n']})"
 lines=['# C02 on shared top-player and role subgroups','',
'These are saved-row comparisons on the original fixed2026Weeks1–7 participant diagnostic. No fits, forecasts, rankings or Week8outcomes were added. All competitors use the same frozen membership for each subgroup; this historical universe is retrospective, not an authenticated pregame offer/starter list. Positive error changes below are losses for C02; negative changes favor C02. Parentheses give identical supported paired rows. Numeric points use MAE; rushing-or-receivingTDprobabilities use Brier.','',
'The C02 history/product in each row was fixed from its already published full-primary observed minimum. Its strongest comparator was fixed from the preceding full-primary family table. Neither is reselected within top-player or workload groups. These exposed choices are descriptive research summaries, not a policy that could have selected next-week methods earlier.','',
'| Target | C02 policy/product | Full Δ (n) | Top10 Δ (n) | Top20 Δ (n) | High prior band Δ (n) | Low prior band Δ (n) | Shared learned full Δ (n) |','| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |']
 for r in chosen:
  t=r['target'];prefix='score_history_'if t==CHART else'workload_'
  lines.append('| '+ ' | '.join([t,r['candidate_policy']+' / '+r['candidate_product'],cell(native,t,'all'),cell(native,t,'top10'),cell(native,t,'top20'),cell(native,t,prefix+'high'),cell(native,t,prefix+'low'),cell(native,t,'all','selected_controls_and_all_four_candidate_policies_learned_overlap')])+' |')
 lines+=['','The full tables retain top15, disjoint ranks1–10/11–15/16–20/remainder, unranked players, zero/unknown/middle bands, own-learned, three-core-history learned overlap, common learned overlap and fallback-only cases. Empty bands remain absent with no fabricated zero error. The paired common mask intersects the selected old controls and allfourC02policies, including strict; it is stricter than each procedure’s own learned population. Strict-only C02 never receives a three-core-history score.','',
'Football selector units are earlier passing attempts, carries, targets, or carries+targets as appropriate. They are not snaps or routes. Chart bands are earlier signed chart points: zero, low≤5includingnegative, middle≤15, high>15, and unknown. Chart point history is not workload. All selectors use the frozen lastthreeearlier-available player-game slots, with missing slots consuming the window; availability is the inherited seven-day reconstruction, not authenticated historical publication. Common older selector memory also prevents calling the entire strict subgroup system pure-current information.','',
'## Mean and distribution products','',
'The next table keeps intended-mean MSE and genuine-law CRPS separate. TD’s proper event score is Brier. The policy for each product is chosen from the earlier full-primary C02scores and then held fixed. PMFnegative-logloss, zero mass, interval width/coverage and infinite-loss counts are retained in canonical scores; no continuous density or fabricated distribution is assigned to point-only HGB/empirical controls.','',
'| Target / product | Full Δ (n) | Top10 Δ (n) | Top20 Δ (n) | High prior band Δ (n) |','| --- | ---: | ---: | ---: | ---: |']
 for t in [r['target']for r in chosen]:
  for purpose in('forecast_law','intended_mean'):
   rs=[r for r in selected if r['target']==t and r['purpose']==purpose]
   if not rs:continue
   prefix='score_history_'if t==CHART else'workload_';lines.append('| '+' | '.join([t+' / '+rs[0]['metric'],cell(selected,t,'all',purpose=purpose),cell(selected,t,'top10',purpose=purpose),cell(selected,t,'top20',purpose=purpose),cell(selected,t,prefix+'high',purpose=purpose)])+' |')
 lines+=['','## Coverage, fallback and uncertainty','',
'Unknown chart outcomes remain in forecast coverage; valid signed production and explicit zero values retain their original contracts. Chart median1/5/10point tolerances use exact0.02integer-grid coordinates. Mean forecasts remain unrounded. Each canonical view records fallback and learned loss sums and their contributions to full-system error, so startup/role-prior performance is visible.','',
'Every paired comparison retains native and relative error deltas, its exact query-membership hash, game counts, fallback counts and per-week changes. Seven exposed week clusters do not meet the registered eight-week interval threshold. Game-cluster standard errors and normal intervals are sensitivity checks, without selection or multiplicity adjustment. A smaller subgroup can reverse a pooled result or produce a large uncertain difference; no subgroup winner is promoted to a future routing rule.','',
'[Native point detail](CATEGORY_POINT_SUBGROUP_SUMMARY.csv) · [Mean/law detail](CATEGORY_MEAN_LAW_SUBGROUP_SUMMARY.csv) · [Canonical new C02views](SCORES.json) · [Every retained paired family comparison](PAIRED_COMPARISONS.json) · [Protocol](FROZEN_PROTOCOL.json) · [Resource and coverage receipt](RUN_RECEIPT.json)','',
'Existing old-control univariate subgroup scores are reused through source-bound references. They are not counted again as new experiments, fits or NFL observations. Frozen future football1795/chart434membership profiles are retained unscored; no original capture or existing production state changes.']
 text='\n'.join(lines)+'\n'
 if comparison_root:text=text.replace('[Canonical new C02views](SCORES.json)','[Canonical new C02views](../shared-subgroups-2026-v1/SCORES.json)')+'\nThis comparison-only correction supersedes the initial v1 comparator sidecar and initial readable projection. The full univariate score array, masks and primary ordered comparisons reproduced exactly; see [reuse verification](UNIVARIATE_REUSE_VERIFICATION.json). No additional univariate score views are counted.\n'
 (out/'README.md').write_text(text)
 write(out/'SUMMARY_SOURCE_BINDINGS.json',dict(canonical_score_sha256=sha(root/'SCORES.json'),paired_comparison_sha256=sha(out/'PAIRED_COMPARISONS.json'),earlier_candidate_score_sha256=sha(cs),earlier_candidate_score_artifact=cs.as_posix(),candidate_choice_sha256=p['candidate_minima_sha256'],old_family_representative_sha256=cp.get('leader_sha256',p['old_leader_sha256']),new_fits=0,new_forecasts=0,week8_outcomes_read=0))
 return dict(native_summary_rows=len(native),mean_law_summary_rows=len(selected))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--public-root',type=Path,required=True);p.add_argument('--canonical-candidate-scores',type=Path,required=True);p.add_argument('--comparison-root',type=Path);print(json.dumps(run(**vars(p.parse_args()))))
