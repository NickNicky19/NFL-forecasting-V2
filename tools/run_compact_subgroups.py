"""Prepare/run compact corrected cohorts without fitting or new sources."""
import argparse,csv,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import compact_subgroups as s,paired_uncertainty
from nfl_v2.shared_subgroups import load,write,sha,now
p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare-season','prepare-defense','run'));p.add_argument('--year',type=int,default=2026);p.add_argument('--public-root',type=Path,required=True);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--season-public',type=Path);p.add_argument('--season-private-member');p.add_argument('--repair-public',type=Path);p.add_argument('--repair-private-member');p.add_argument('--leader-file',type=Path);p.add_argument('--candidate-minima',type=Path)
a=p.parse_args()
if a.action=='run':print(json.dumps(s.run(public_root=a.public_root,private_root=a.private_root)));raise SystemExit
if a.public_root.exists():raise ValueError('fresh output required')
refs=[];pred=[];members=['pregame-cohort-scorecards-v2/memberships.json.gz','chart-cohort-scorecards-v1/memberships.json.gz']if a.year==2026 else[f'shared-season-cohort-memberships-v1/memberships-{a.year}.json.gz'];choices=[];extra=[]
fixed=s.select_fixed(a.leader_file,a.year)
if a.action=='prepare-season':
 with a.candidate_minima.open()as f:mins=list(csv.DictReader(f))
 for r in mins:choices.append(dict(group='C02_fixed_2026',target=r['target'],procedure_id=s.C02+(':strict-current-inputs'if r['candidate_policy']=='H-CURRENT-STRICT'else':common-feature-memory'),history_regime=r['candidate_policy'].replace('-COMMON','').replace('-STRICT',''),product_id=r['candidate_product'],policy_id=r['candidate_policy']))
 rows=load(a.season_public/'SCORES.json');pred.append(dict(private_member=a.season_private_member,format='csv',kind='season_base'));extra+=[dict(artifact=(a.season_public/'SCORES.json').as_posix(),sha256=sha(a.season_public/'SCORES.json')),dict(artifact=a.candidate_minima.as_posix(),sha256=sha(a.candidate_minima))]
 if a.repair_public:
  rows=[r for r in rows if'qb-rb-specialization'not in r['procedure_id']]+load(a.repair_public/'SCORES.json');pred.append(dict(private_member=a.repair_private_member,format='csv',kind='season_repair'));extra.append(dict(artifact=(a.repair_public/'SCORES.json').as_posix(),sha256=sha(a.repair_public/'SCORES.json')))
 strong=s.select_season(rows)
 for c in choices:refs.extend([dict(fixed[c['target']],group=c['group']),dict(strong[c['target']],group=c['group'])])
 mode='season';limit='fixed2026C02recipe replay on qualifiedretrospective older-season source cohort; same memberships for both references; corrected empirical point aliases; older selector memory not strict-information selected system'
else:
 source=Path('reports/continuation-20261030c/qualified-defense-information-v1');rows=load(source/'SCORES.json');full=[r for r in rows if r['week']=='ALL'and r['position']=='ALL'and r['fallback_view']=='ALL'and r['population']=='primary'];extra.append(dict(artifact=(source/'SCORES.json').as_posix(),sha256=sha(source/'SCORES.json')))
 for group in('D1','D2'):
  for target in sorted({r['target']for r in full}):
   metric='brier'if target=='anytime_td'else'mae';r=min((r for r in full if r['information_group']==group and r['target']==target),key=lambda r:(r[metric],r['policy_id'],r['product_id']));c=dict(group=group,target=target,procedure_id=r['procedure_id'],history_regime=r['history_regime'],product_id=r['product_id'],policy_id=r['policy_id']);choices.append(c);refs.append(dict(fixed[target],reference='fixed_strong_control',group=group))
 pred=[dict(private_member='qualified-defense-information-v1/ALL_HISTORICAL_PREDICTIONS.json.gz',format='packet',kind='defense'),dict(private_member='ordered-information-ablation-v1/ALL_PREDICTIONS.json.gz',format='packet',kind='existing'),dict(private_member='distribution-wave-v2/all-predictions.csv.gz',format='csv',kind='existing'),dict(private_member='chart-wave-v1/all-chart-predictions.csv.gz',format='csv',kind='existing'),dict(private_member='empirical-history-diagnostic-v1/predictions.csv.gz',format='csv',kind='empirical')]
 # Only original HGB chunks required by the frozen strongest references.
 hgb=[r for r in fixed.values()if r['procedure_id'].startswith('hgb-direct-history-controls-v1:')]
 for f in sorted((a.private_root/'hgb-history-v1/prediction-chunks').glob('W0[1-7]-*.json.gz')):
  if any(f'-{r["target"]}-{r["history_regime"]}-{r["product_id"]}.json.gz'in f.name for r in hgb):pred.append(dict(private_member=f.relative_to(a.private_root).as_posix(),format='packet',kind='hgb'))
 mode='defense';limit='current-vintage2026W1–7retrospective participant queries; D1/D2actual last4OBSERVED qualifiedpositiongroups (notallcalendarteamgames), perindependentfinding; same frozen cohorts; no deployment'
a.public_root.mkdir(parents=True)
bindings=[]
for name in list(dict.fromkeys(members+[r['private_member']for r in pred])):bindings.append(dict(artifact_id='RETAINED-'+sha(a.private_root/name),private_member=name,sha256=sha(a.private_root/name)))
proto=dict(version=s.VERSION,mode=mode,state='REGISTERED_BEFORE_COMPACT_CORRECTION_REPLAY',registered_at_utc=now(),evaluation_season=a.year,code_sha256=sha(s.__file__),base_helper_sha256=sha(s.base.__file__),paired_helper_sha256=sha(paired_uncertainty.__file__),metric_helpers={name:sha(Path(s.__file__).with_name(name))for name in('scoring.py','precision_grid.py')},bindings=bindings,memberships=members,prediction_sources=pred,role_overlay=bool(a.repair_public),choices=choices,reference_specs=refs,source_public_bindings=extra+[dict(artifact=a.leader_file.as_posix(),sha256=sha(a.leader_file))],cohort_limit=limit,exposure='full2026/olderseasonresults andv2cohortoutputs alreadyexposed; correction/newsubgroupviewnotuntouchedconfirmation; referencesfixedatfull-primarylevel, neverreselectedwithinbands',views=['full_system','own_learned_only','selected_candidate_and_controls_common_learned_overlap','fallback_only'],alias_correction={'empirical_mean':'mean','empirical_lower_median':'lower_median'},comparison_limit='twoexactsamequeryreferences perregisteredrecipe; completecandidate+twocontrollearnedintersection, notthreehistoryoverlap; no live routing policy',budget=dict(wall_seconds=180,max_peak_memory_bytes=1073741824,max_score_views=2500,max_threads=1),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
write(a.public_root/'FROZEN_PROTOCOL.json',proto);print(json.dumps(dict(protocol_sha256=sha(a.public_root/'FROZEN_PROTOCOL.json'),choices=len(choices),references=len(refs))))
