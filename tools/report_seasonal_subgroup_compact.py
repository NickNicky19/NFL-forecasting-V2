"""Compact fixed-2026 recipe projections from completed older C02 cohort scores."""
import argparse,csv,json,gzip,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import load,sha,write,packet_rows,C02

def run(public_root):
 root=Path(public_root);p=load(root/'FROZEN_PROTOCOL.json');scores=load(root/'SCORES.json');year=p['evaluation_season']
 with open(p['candidate_minima_artifact'])as f:choices={r['target']:r for r in csv.DictReader(f)}
 selected={}
 for r in scores:
  c=choices[r['target']]
  if r['policy_id']==c['candidate_policy']and r['product_id']==c['candidate_product']:selected[r['record_id']]=r
 desired={}
 for t in choices:
  for view in('FIXED_2026_DEVELOPED_PRE_C02_FAMILY_CHOICE','SAME_SEASON_FULL_PRIMARY_OBSERVED_FAMILY_CHOICE'):
   refs=[s for s in p['references']if s['target']==t and s['purpose']=='display_point'and s['reference_view']==view]
   if not refs:raise ValueError('missing frozen reference')
   desired[t,view]=min(refs,key=lambda x:(x['old_rank'],x['family'],x['procedure_id']))
 comparisons=[]
 for c in packet_rows(root/'PAIRED_COMPARISONS.json.gz'):
  s=selected.get(c['source_record_id'])
  if s is None or c['purpose']!='display_point':continue
  ref=desired[s['target'],c['reference_view']]
  if c['comparator_family']!=ref['family']:continue
  if c['status']=='PAIRED_RETAINED_ROWS'and(c['comparator_procedure_id'],c['comparator_history_regime'],c['comparator_product_id'])!=(ref['procedure_id'],ref['history_regime'],ref['product_id']):continue
  u=c.get('uncertainty')or{};ci=u.get('week_interval')
  comparisons.append(dict(season=year,target=s['target'],population=s['population'],cohort_id=s['cohort_id'],fallback_view=s['fallback_view'],candidate_procedure_id=s['procedure_id'],candidate_history_regime=s['history_regime'],candidate_policy_id=s['policy_id'],candidate_product_id=s['product_id'],reference_view=c['reference_view'],reference_procedure_id=c.get('comparator_procedure_id'),reference_history_regime=c.get('comparator_history_regime'),reference_product_id=c.get('comparator_product_id'),metric=c['metric'],candidate_n=s['n'],candidate_forecast_rows=s['forecast_rows'],candidate_fallback_rows=s['fallback_rows'],paired_n=c['paired_n'],candidate_error=c.get('candidate_error'),reference_error=c.get('comparator_error'),error_delta=c.get('absolute_error_delta'),relative_error_delta=c.get('relative_error_delta'),week_clusters=u.get('week_clusters'),week_ci_low=None if ci is None else ci[0],week_ci_high=None if ci is None else ci[1],game_clusters=u.get('game_clusters'),membership_sha256=c.get('membership_sha256'),source_record_id=s['record_id'],source_score_sha256=sha(root/'SCORES.json'),status=c['status']))
 with(root/'FIXED_2026_RECIPE_SUBGROUP_SCORECARD.csv').open('x',newline='')as f:
  w=csv.DictWriter(f,fieldnames=list(comparisons[0]));w.writeheader();w.writerows(comparisons)
 def row(t,cohort,ref,view='full_system'):
  rs=[r for r in comparisons if(r['target'],r['population'],r['cohort_id'],r['reference_view'],r['fallback_view'])==(t,'primary',cohort,ref,view)]
  return rs[0]if rs else None
 def cell(t,cohort,ref,view='full_system'):
  r=row(t,cohort,ref,view)
  return '—'if not r or r['error_delta']is None else f"{r['error_delta']:+.4f} ({r['paired_n']})"
 fixed='FIXED_2026_DEVELOPED_PRE_C02_FAMILY_CHOICE';strong='SAME_SEASON_FULL_PRIMARY_OBSERVED_FAMILY_CHOICE'
 lines=[f'# {year}: fixed 2026 C02 recipes on shared subgroups','',
'These tables reuse retained forecasts and the cohort memberships frozen before seasonal loss decoding. No fits, new forecasts, or 2026 Week 8 outcomes are added. Every row keeps the same C02 history/product chosen from the already exposed 2026 full-primary result. It compares (1) the fixed pre-C02 2026 control and (2) the strongest observed same-season full-primary existing control. References were fixed before subgroup scoring and are not reselected within bands. Neither view is an earlier live policy. Numeric errors use MAE; anytime TD uses Brier. Negative change favors C02; parentheses give identical supported paired rows.','',
'| Target | C02 full error | Δ fixed-2026 control: full | Top 10 | Top 15 | Top 20 | High prior band | Δ strongest same-season: full | Top 20 |','| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
 for t in sorted(choices):
  a=row(t,'all',fixed);error='—'if not a or a['candidate_error']is None else f"{a['candidate_error']:.4f}";band='score_history_high'if t=='nick-chart-ppr-v1'else'workload_high'
  lines.append('| '+' | '.join([t,error,cell(t,'all',fixed),cell(t,'top10',fixed),cell(t,'top15',fixed),cell(t,'top20',fixed),cell(t,band,fixed),cell(t,'all',strong),cell(t,'top20',strong)])+' |')
 lines+=['','## Learned-only and common membership','',
'Own-learned rows can differ by procedure. The common-learned view intersects all selected references and all four C02 policies; it includes strict models explicitly. Common older cohort-selector memory means this selected system is not a pure-current-information claim.','',
'| Target | Own-learned full Δ vs fixed control | Shared-learned full Δ vs fixed control | Shared-learned top 20 Δ |','| --- | ---: | ---: | ---: |']
 for t in sorted(choices):lines.append('| '+' | '.join([t,cell(t,'all',fixed,'own_learned_only'),cell(t,'all',fixed,'selected_controls_and_all_four_candidate_policies_learned_overlap'),cell(t,'top20',fixed,'selected_controls_and_all_four_candidate_policies_learned_overlap')])+' |')
 lines+=['','The [compact scorecard](FIXED_2026_RECIPE_SUBGROUP_SCORECARD.csv) also retains disjoint ranks 1–10, 11–15, 16–20, remainder, unranked players, every prior workload/score band, primary/extended populations, fallbacks and whole-week paired bootstrap intervals. Football ranks use earlier opportunities; chart ranks use signed chart points, not workload. The source remains a retrospective statistical-row/physical-participation diagnostic, with assumed seven-day availability, not authenticated historical offers or starters.','',
'All 18 regular-season weeks, including historical Week 8, are evaluated. Bootstrap intervals resample whole weeks, 500 replicates with fixed seed, where at least eight clusters exist. They are descriptive exposed-sample intervals, without selection or multiplicity adjustment. Canonical scores retain mean/median identity, genuine-law diagnostics and exact chart median precision; this compact table projects displayed points only.','',
'[Canonical C02 cohort scores](SCORES.json) · [Compressed paired matrix](PAIRED_COMPARISONS.json.gz) · [Exact encoding receipt](PAIRED_COMPARISONS_ENCODING_RECEIPT.json) · [Protocol](FROZEN_PROTOCOL.json) · [Run receipt](RUN_RECEIPT.json)','',
'No website improvement follows from this older-season diagnostic. The separate server-retained R0 reference wins eight of ten numeric categories on a matched 13-game 2026 Week 7 panel; its server availability does not establish internal capture/input vintage or today’s website method.']
 (root/'README.md').write_text('\n'.join(lines)+'\n')
 write(root/'COMPACT_SUMMARY_BINDING.json',dict(source_score_sha256=sha(root/'SCORES.json'),source_comparison_gzip_sha256=sha(root/'PAIRED_COMPARISONS.json.gz'),source_encoding_receipt_sha256=sha(root/'PAIRED_COMPARISONS_ENCODING_RECEIPT.json'),source_protocol_sha256=sha(root/'FROZEN_PROTOCOL.json'),code_sha256=sha(__file__),compact_rows=len(comparisons),new_univariate_views=0,new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0))
 return dict(compact_rows=len(comparisons),targets=len(choices),new_univariate_views=0)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--public-root',type=Path,required=True);print(json.dumps(run(**vars(p.parse_args()))))
