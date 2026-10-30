"""Older-season C02 subgroup replay on separately frozen memberships.

The grouping/scoring implementation follows the frozen current-season scorer;
season identity, 18-week bounds, source aliases and week bootstrap are explicit.
No fitting or inference occurs. References are frozen before subgroup scoring.
"""
from __future__ import annotations
import collections,csv,gzip,json,math,resource,sys,time
from pathlib import Path
from . import shared_subgroups as base,paired_uncertainty
from .shared_subgroups import canonical,digest,sha,write,load,now,identity,modelkey,metrics,loss,CHART,CORE,C02
VERSION='v2-older-season-c02-frozen-subgroup-replay-v1'

def paired(rows,other,metric):
 c=base.paired(rows,other,metric)
 if c['status']!='PAIRED_RETAINED_ROWS':return c
 selected=[(r,other[identity(r)])for r in rows if identity(r)in other and loss(r,metric)is not None and loss(other[identity(r)],metric)is not None]
 u=paired_uncertainty.paired_losses([loss(a,metric)for a,b in selected],[loss(b,metric)for a,b in selected],[a['week']for a,b in selected],[a['game_id']for a,b in selected],replicates=500,seed=1703)
 c['uncertainty']=u
 return c

def evaluate(candidates,controls,membership,protocol_sha,specs,year):
 indexed={};labels={};own=collections.defaultdict(dict)
 for r in candidates:
  k=modelkey(r);ident=identity(r)
  if ident not in membership:raise ValueError('candidate outside frozen membership')
  if ident in own[k]:raise ValueError('duplicate candidate view')
  own[k][ident]=r
  if ident in labels and labels[ident]!=(r['actual'],r['position']):raise ValueError('candidate labels differ')
  labels[ident]=(r['actual'],r['position'])
 for r in controls:
  ident=identity(r)
  if ident not in membership:raise ValueError('control outside frozen historical query')
  if labels.get(ident)!=(r['actual'],r['position']):raise ValueError('control label/role mismatch')
  k=modelkey(r)
  if ident in indexed.setdefault(k,{}):raise ValueError('duplicate control view')
  indexed[k][ident]=r
 # Freeze a balanced all-selected-controls learned mask independent of errors.
 panels=collections.defaultdict(list)
 for k,rs in own.items():
  for t,pop in {(r['target'],r['population'])for r in rs.values()}:panels[t,pop].append({i for i,r in rs.items()if(r['target'],r['population'])==(t,pop)and r['fallback']=='none'and r['prediction']is not None and r['actual']is not None})
 for s in specs:
  rs=indexed.get((s['procedure_id'],s['history_regime'],s['product_id']),{})
  for t,pop in {(r['target'],r['population'])for r in rs.values()if r['target']==s['target']}:
   panels[t,pop].append({i for i,r in rs.items()if(r['target'],r['population'])==(t,pop)and r['fallback']=='none'and r['prediction']is not None and r['actual']is not None})
 shared={k:set.intersection(*v)for k,v in panels.items()};core={}
 for proc,arm,product in own:
  if proc.endswith(':strict-current-inputs'):continue
  if all((proc,a,product)in own for a in CORE):core[proc,product]=set.intersection(*({i for i,r in own[proc,a,product].items()if r['fallback']=='none'and r['prediction']is not None and r['actual']is not None}for a in CORE))
 grouped=collections.defaultdict(list)
 for r in candidates:
  i=identity(r);views=['full_system']
  if r['fallback']=='none':views.append('own_learned_only')
  else:views.append('fallback_only')
  if i in shared[r['target'],r['population']]:views.append('selected_controls_and_all_four_candidate_policies_learned_overlap')
  if i in core.get((r['procedure_id'],r['product_id']),set()):views.append('three_core_history_learned_overlap')
  for cohort in membership[i]['cohorts']:
   for view in views:grouped[(*modelkey(r),r['target'],r['population'],cohort,view)].append(r)
 output=[];comparisons=[];dates=[]
 for dims,rows in sorted(grouped.items()):
  proc,arm,product,target,pop,cohort,view=dims;record='SEASON-SUBGROUP-'+digest([year,*dims])[:24];scored=[r for r in rows if r['actual']is not None and r['prediction']is not None];policy=rows[0]['policy_id'];strict=proc.endswith(':strict-current-inputs');oldproc=('v2-qualified-partial-chart-direct-wave-v1:'if target==CHART else'v2-distribution-controls-reconstruction-v2:')+'ordered_leaf_cdf:'+('strict-current-inputs'if strict else'common-feature-memory');primary=paired(rows,indexed.get((oldproc,arm,product),{}),'brier'if target=='anytime_td'else'mae')
  out=dict(record_id=record,procedure_id=proc,procedure_family_id='ordered_leaf_cdf',product_id=product,target=target,population=pop,history_regime=arm,policy_id=policy,information_policy=rows[0]['information_policy'],cohort_id=cohort,fallback_view=view,season=year,week='ALL',position='ALL',evaluation_seasons=[year],evaluation_weeks=sorted({r['week']for r in scored}),evaluation_panel_id=VERSION+':'+str(year),record_kind='NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC',evidence='NEW_EXPERIMENT',source_vintage='current_vintage_reconstruction',cohort_membership_sha256=digest(sorted(identity(r)for r in rows)),scored_membership_sha256=digest(sorted(identity(r)for r in scored)),cohort_protocol_sha256=protocol_sha,cohort_limit='Retrospective observed-stat-row universe; same inherited earlier-feature-defined ranks. Chart point history is not workload; common older selector means strict subgroup system is not information-pure.',selector_quantity='prior_chart_point_mean_last3_slots'if target==CHART else'prior_opportunity_mean_last3_slots',comparison=primary,**metrics(rows,target,product))
  if target==CHART:out.update(point_grid_denominator=50,chart_source_policy='v2-nick-chart-ppr-nflverse-explicit-zero-subset-v2')
  output.append(out)
  dates.append(dict(source_row_index=len(output)-1,evaluation_seasons=[year],evaluation_weeks=out['evaluation_weeks'],actual_scored_weeks=out['evaluation_weeks'],forecast_query_weeks=sorted({r['week']for r in rows}),registered_panel_weeks=list(range(1,19))))
  for s in specs:
   if s['target']!=target:continue
   if s['purpose']=='intended_mean'and product!='mean':continue
   if s['purpose']=='forecast_law'and product not in('mean','event_probability'):continue
   metric=('brier'if target=='anytime_td'else'mae')if s['purpose']=='display_point'else'mse'if s['purpose']=='intended_mean'else'brier'if target=='anytime_td'else'crps'
   c=paired(rows,indexed.get((s['procedure_id'],s['history_regime'],s['product_id']),{}),metric)
   comparisons.append(dict(source_record_id=record,purpose=s['purpose'],comparator_family=s['family'],old_full_primary_rank=s['old_rank'],selector='Frozen previous full-primary family representative, held fixed across subgroups; exposed descriptive comparator, not pregame routing',**c))
 return output,comparisons,dates,{f'{t}:{p}':len(v)for(t,p),v in shared.items()}


def family(row):
 p=row['procedure_id']
 return 'ORDERED_LEAF_CDF'if'ordered_leaf_cdf:'in p else'GLM_LAW'if'regularized_glm_law:'in p else'EMPIRICAL'if'empirical'in p else'HGB'
def alias_fixed(s):
 s=dict(s,purpose=s['purpose'],reference_view='FIXED_2026_DEVELOPED_PRE_C02_FAMILY_CHOICE')
 if s['procedure_id'].startswith('hgb-direct-history-controls-v1:')and not s['procedure_id'].endswith((':common-feature-memory',':strict-current-inputs')):s['procedure_id']+=':common-feature-memory'
 if s['target']==CHART and s['procedure_id'].endswith(':empirical'):s['procedure_id']='empirical-player-history-control-v1'
 return s

def same_season_specs(score_rows):
 full=[r for r in score_rows if r['week']=='ALL'and r['position']=='ALL'and r['fallback_view']=='ALL'and r['population']=='primary'and not r['procedure_id'].startswith(C02)]
 output=[]
 for target in sorted({r['target']for r in full}):
  rows=[r for r in full if r['target']==target];n=max(r['n']for r in rows)
  for purpose in('display_point','intended_mean','forecast_law'):
   if target=='anytime_td'and purpose=='intended_mean':continue
   metric=('brier'if target=='anytime_td'else'mae')if purpose=='display_point'else'mse'if purpose=='intended_mean'else'brier'if target=='anytime_td'else'CRPS'
   allowed=[r for r in rows if r['n']==n and r.get(metric)is not None and(purpose!='intended_mean'or r['product_id']in('mean','empirical_mean','squared_error_mean','poisson_intended_mean_point'))]
   by=collections.defaultdict(list)
   for r in allowed:by[family(r)].append(r)
   winners=[]
   for f,rs in by.items():
    r=min(rs,key=lambda x:(x[metric],x['procedure_id'],x['policy_id'],x['product_id']));winners.append((r[metric],f,r))
   for rank,(_,f,r)in enumerate(sorted(winners,key=lambda x:(x[0],x[1])),1):
    output.append(dict(target=target,purpose=purpose,family='SAME_SEASON:'+f,procedure_id=r['procedure_id'],history_regime=r['history_regime'],product_id=r['product_id'],prior_full_error=r[metric],old_rank=rank,source_artifact='same_season_full_primary_scores',reference_view='SAME_SEASON_FULL_PRIMARY_OBSERVED_FAMILY_CHOICE',selection='excludeC02; highestcompletepopulationn; minimumregisterednativeerrorwithinexistingfamily; heldfixedforallsubgroups; exposedretrospectivechoiceNOTearlierlivepolicy'))
 return output

def prepare(*,year,season_public,season_private,cohort_public,cohort_private,leader_file,candidate_minima,candidate_scores,public_root,repair_public=None,repair_private=None):
 year=int(year);season_public,season_private,cohort_public,cohort_private,leader_file,candidate_minima,candidate_scores,public_root=map(Path,(season_public,season_private,cohort_public,cohort_private,leader_file,candidate_minima,candidate_scores,public_root))
 if year not in(2022,2023,2024,2025)or public_root.exists():raise ValueError('fresh older-season output required')
 receipt=load(season_public/'RUN_RECEIPT.json');sp=load(season_public/'FROZEN_PROTOCOL.json');membership=cohort_private/f'memberships-{year}.json.gz';mr=load(cohort_public/f'SEASON_{year}_MEMBERSHIP_RECEIPT.json');flat=season_private/receipt['private_flat']['bundle_name']
 if receipt['state']!='COMPLETE'or receipt['evaluation_season']!=year or sp['frozen_queries_sha256']!=mr['query_sha256']or sha(flat)!=receipt['private_flat']['sha256']or sha(membership)!=mr['membership_sha256']:raise ValueError('qualified completed source/query/membership binding failed')
 scores=load(season_public/'SCORES.json');sources=[dict(artifact_id='BASE_SEASON_PREDICTIONS',sha256=sha(flat),bytes=flat.stat().st_size,source_receipt_artifact=(season_public/'RUN_RECEIPT.json').as_posix(),source_receipt_sha256=sha(season_public/'RUN_RECEIPT.json'))];repair=None
 if repair_public is not None or repair_private is not None:
  if repair_public is None or repair_private is None:raise ValueError('bothrepairbindingsrequired')
  repair_public,repair_private=Path(repair_public),Path(repair_private);rr=load(repair_public/'RUN_RECEIPT.json');repair=repair_private/rr['private_flat']['bundle_name']
  if rr['source_prediction_sha256']!=sha(flat)or sha(repair)!=rr['private_flat']['sha256']:raise ValueError('repair source binding failed')
  corrected=load(repair_public/'SCORES.json');scores=[r for r in scores if'qb-rb-specialization'not in r['procedure_id']]+corrected;sources.append(dict(artifact_id='ROLE_CONTINUITY_REPAIR_OVERLAY',sha256=sha(repair),bytes=repair.stat().st_size,source_receipt_artifact=(repair_public/'RUN_RECEIPT.json').as_posix(),source_receipt_sha256=sha(repair_public/'RUN_RECEIPT.json'),overlay_rule='dropallbaseqb-rb-specialization rows, replace entirecorrectedpacket; no numericchangeselsewhere; no refits'))
 fixed=[alias_fixed(s)for s in base.selected_specs(leader_file)]
 if any(s['procedure_id'].startswith(C02)for s in fixed):raise ValueError('fixed2026controlselectionmustpredateC02')
 specs=fixed+same_season_specs(scores);public_root.mkdir(parents=True)
 p=dict(version=VERSION,state='FROZEN_BEFORE_NEW_SEASONAL_SUBGROUP_METRIC_DECODE',registered_at_utc=now(),evaluation_season=year,code_sha256=sha(__file__),source_helper_sha256=sha(base.__file__),scoring_helper_sha256=sha(Path(__file__).with_name('scoring.py')),precision_helper_sha256=sha(Path(__file__).with_name('precision_grid.py')),uncertainty_helper_sha256=sha(paired_uncertainty.__file__),source_bindings=sources,source_protocol_artifact=(season_public/'FROZEN_PROTOCOL.json').as_posix(),source_protocol_sha256=sha(season_public/'FROZEN_PROTOCOL.json'),source_score_artifact=(season_public/'SCORES.json').as_posix(),source_score_sha256=sha(season_public/'SCORES.json'),membership_sha256=sha(membership),membership_receipt_artifact=(cohort_public/f'SEASON_{year}_MEMBERSHIP_RECEIPT.json').as_posix(),membership_receipt_sha256=sha(cohort_public/f'SEASON_{year}_MEMBERSHIP_RECEIPT.json'),query_sha256=mr['query_sha256'],query_cells=mr['query_cells'],source_qualification='samequalifiedseasonalproducer current-vintageobserved-stat-row/positivephysicalproof; samepartialchartlabelcontract; nofutureyearsource; oldC02/modelsettingspreviouslyexposed',fixed_2026_leader_artifact=leader_file.as_posix(),fixed_2026_leader_sha256=sha(leader_file),candidate_minima_artifact=candidate_minima.as_posix(),candidate_minima_sha256=sha(candidate_minima),candidate_score_artifact=candidate_scores.as_posix(),candidate_score_sha256=sha(candidate_scores),references=specs,reference_views=['fixed2026-developedpre-C02familychoices','strongestsame-seasonfull-primaryexistingfamily/productchoicesexcludeC02'],reference_limit='Bothviewsretrospectiveexposedcomparisons; neitherisearlierlivepolicy. Same-seasonfullerrorsalreadyknownbeforefrozencohortmetricdecode; neverchoosewithinrank/workloadbands.',candidate_primary_choice='fixedpublished2026C02history/productchoiceforpersist/reversal; all4policies/pointviewsremaincanonical',membership='Exactpreviouslyfrozenlast3AVAILABLEslot footballopportunity/chartscore ranks, samecompetitormembers; all18weeksincludinghistoricalWeek8; retrospectiveparticipantuniverseNOTexante. Strictmodelwitholdercohortselectorisnotpurecurrentselectedsystem.',uncertainty='Whole-weekpairedbootstrap500replicatesPCG64seed1703resetpercontrast, only>=8observedweeks; game-clustersensitivity separately; no multiplicity/selectionadjustment.',budget=dict(max_source_prediction_rows=2000000,max_selected_prediction_rows=1600000,max_score_views=12000,max_comparison_views=200000,wall_seconds=900,max_peak_memory_bytes=2147483648,max_threads=1),new_univariate_procedures='C02only; oldmodelsusedaspairedreferencesnotrecountedasnewunivariates',new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
 write(public_root/'FROZEN_PROTOCOL.json',p);return p

def normalize(raw,year,summary_cache):
 if int(raw['season'])!=year or not 1<=int(raw['week'])<=18:raise ValueError('source outside fixedolderseasonREGpanel')
 r={k:sys.intern(raw[k])for k in('game_id','player_id','target','population','position','history_regime','procedure_id','product_id','policy_id','information_policy','fallback')};r.update(season=year,week=int(raw['week']),prediction=base.number(raw['prediction']),actual=base.number(raw['actual']),procedure_family_id=sys.intern(raw['family']))
 ds=raw.get('distribution_summary');key=(r['game_id'],r['player_id'],r['target'],r['population'],r['procedure_id'],r['policy_id'])
 if ds:
  if key not in summary_cache:summary_cache[key]=json.loads(ds)
  ds=summary_cache[key]
 else:ds=None
 r['distribution_summary']=ds;return r

def run(*,year,season_public,season_private,cohort_public,cohort_private,public_root,repair_public=None,repair_private=None):
 year=int(year);season_public,season_private,cohort_public,cohort_private,public_root=map(Path,(season_public,season_private,cohort_public,cohort_private,public_root));p=load(public_root/'FROZEN_PROTOCOL.json');start=time.monotonic()
 for key,path in [('code_sha256',__file__),('source_helper_sha256',base.__file__),('scoring_helper_sha256',Path(__file__).with_name('scoring.py')),('precision_helper_sha256',Path(__file__).with_name('precision_grid.py')),('uncertainty_helper_sha256',paired_uncertainty.__file__),('source_protocol_sha256',season_public/'FROZEN_PROTOCOL.json'),('source_score_sha256',season_public/'SCORES.json'),('membership_receipt_sha256',cohort_public/f'SEASON_{year}_MEMBERSHIP_RECEIPT.json')]:
  if sha(path)!=p[key]:raise ValueError('frozen source/helper changed')
 checks=load(public_root/'SOFTWARE_CHECKS.json')
 if checks.get('status')!='PASS'or checks.get('code_sha256')!=sha(__file__):raise ValueError('exact-code software checks required')
 path=cohort_private/f'memberships-{year}.json.gz'
 if sha(path)!=p['membership_sha256']:raise ValueError('membership changed')
 membership={tuple(m['key']):{k:v for k,v in m.items()if k!='key'}for m in json.loads(gzip.decompress(path.read_bytes()))};sources=[season_private/'predictions.csv.gz']
 if len(p['source_bindings'])==2:
  if repair_private is None:raise ValueError('requiredcontinuityoverlaymissing')
  sources.append(Path(repair_private)/'CORRECTED_PREDICTIONS.csv.gz')
 for path,b in zip(sources,p['source_bindings']):
  if sha(path)!=b['sha256']:raise ValueError('prediction source changed')
 write(public_root/'EXECUTION_REGISTRATION.json',dict(version=VERSION,season=year,actual_started_at_utc=now(),protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0))
 needed={(s['procedure_id'],s['history_regime'],s['product_id'])for s in p['references']};candidates=[];controls=[];cache={};source_n=0
 for idx,path in enumerate(sources):
  with gzip.open(path,'rt',newline='')as f:
   for raw in csv.DictReader(f):
    source_n+=1
    if source_n>p['budget']['max_source_prediction_rows']:raise RuntimeError('SOURCE_ROW_BUDGET')
    if idx==0 and len(sources)==2 and'qb-rb-specialization'in raw['procedure_id']:continue
    key=raw['procedure_id'],raw['history_regime'],raw['product_id'];iscandidate=raw['procedure_id'].startswith(C02)
    if not iscandidate and key not in needed and'ordered_leaf_cdf:'not in raw['procedure_id']:continue
    r=normalize(raw,year,cache)
    (candidates if iscandidate else controls).append(r)
    if len(candidates)+len(controls)>p['budget']['max_selected_prediction_rows']or time.monotonic()-start>p['budget']['wall_seconds']or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>p['budget']['max_peak_memory_bytes']:raise RuntimeError('BOUNDED_REPLAY_STOP')
 del cache
 scores,comparisons,dates,overlap=evaluate(candidates,controls,membership,sha(public_root/'FROZEN_PROTOCOL.json'),p['references'],year)
 # Keep fixed-2026 and same-season observed references explicit, including ties.
 for c in comparisons:c['reference_view']='SAME_SEASON_FULL_PRIMARY_OBSERVED_FAMILY_CHOICE'if c['comparator_family'].startswith('SAME_SEASON:')else'FIXED_2026_DEVELOPED_PRE_C02_FAMILY_CHOICE'
 if len(scores)>p['budget']['max_score_views']or len(comparisons)>p['budget']['max_comparison_views']or time.monotonic()-start>p['budget']['wall_seconds']:raise RuntimeError('OUTPUT_REPLAY_BUDGET')
 write(public_root/'SCORES.json',scores);write(public_root/'PAIRED_COMPARISONS.json',dict(source_score_sha256=sha(public_root/'SCORES.json'),rows=comparisons));write(public_root/'SCORE_DATE_PROJECTION.json',dict(source_score_sha256=sha(public_root/'SCORES.json'),rows=dates))
 receipt=dict(version=VERSION,state='COMPLETE_SAVED_ROW_SEASONAL_C02_SUBGROUP_REPLAY',evaluation_season=year,completed_at_utc=now(),protocol_sha256=sha(public_root/'FROZEN_PROTOCOL.json'),source_prediction_rows=source_n,candidate_views=len(candidates),reference_views=len(controls),query_cells=len(membership),unique_games=len({k[0]for k in membership}),unique_player_games=len({k[:2]for k in membership}),score_views=len(scores),paired_comparison_views=len(comparisons),score_sha256=sha(public_root/'SCORES.json'),comparison_sha256=sha(public_root/'PAIRED_COMPARISONS.json'),shared_learned_query_counts=overlap,resource=dict(wall_seconds=time.monotonic()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=1),new_fits=0,new_forecasts=0,new_private_artifacts=0,current2026_week8_outcomes_read=0,old_univariate_views_recounted=0)
 write(public_root/'RUN_RECEIPT.json',receipt);return receipt
