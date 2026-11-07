#!/usr/bin/env python3
"""Bounded adjacent-history comparison of immutable retained forecast rows."""
import argparse,collections,csv,gzip,hashlib,json,math,resource,sys,time
from array import array
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from threadpoolctl import threadpool_limits
from nfl_v2 import hgb_control as s, empirical_benchmark as emp
from nfl_v2.paired_uncertainty import paired_losses
from nfl_v2.shared_subgroups import packet_rows
CORE=('H-CURRENT','H-RECENT','H-MULTI')
VIEWS=('FULL_SYSTEM','COMMON_CORE_LEARNED','ANY_ARM_FALLBACK','ALL_ARM_FALLBACK','MIXED_FALLBACK','WEEK1_STARTUP')
SPECS=[
 ('season2025','seasonal-rolling-2025-v1/predictions.csv.gz','csv',2025),
 ('season2025repair','seasonal-rolling-2025-continuity-repair-v1/CORRECTED_PREDICTIONS.csv.gz','csv',2025),
 ('season2024','seasonal-rolling-2024-v2/predictions.csv.gz','csv',2024),
 ('season2023','seasonal-rolling-2023-complete-replay-v1/predictions.csv.gz','csv',2023),
 ('season2022','seasonal-rolling-2022-v2/predictions.csv.gz','csv',2022),
 ('empirical2026','empirical-history-diagnostic-v1/predictions.csv.gz','csv',2026),
 ('laws2026','distribution-wave-v2/all-predictions.csv.gz','csv',2026),
 ('chart2026','chart-wave-v1/all-chart-predictions.csv.gz','csv',2026),
 ('count2026','count-ablation-wave-v1/PREDICTIONS_FLAT.csv.gz','csv',2026),
 ('c022026','ordered-information-ablation-v1/ALL_PREDICTIONS.json.gz','packet',2026),
 ('defense2026','qualified-defense-information-v1/ALL_HISTORICAL_PREDICTIONS.json.gz','packet',2026),
 ('hgb2026','hgb-history-v1/prediction-chunks','chunks',2026)]
def number(x):return None if x is None or x=='' else float(x)
def procedure(r,kind):
 p=r.get('procedure_id')
 if kind=='empirical2026' or p and p.endswith(':empirical') or r.get('family')=='empirical_chart_history_control':p='empirical-player-history-control-v1'
 if kind=='hgb2026':p='hgb-direct-history-controls-v1:'+r['objective']
 return p.removesuffix(':common-feature-memory')
def membership(qs):return hashlib.sha256(s.canonical(sorted(qs))).hexdigest()
def view_names(fallbacks,week):
 learned=all(f=='none' for f in fallbacks);allfallback=all(f!='none' for f in fallbacks)
 return ['FULL_SYSTEM','COMMON_CORE_LEARNED' if learned else 'ANY_ARM_FALLBACK']+([] if learned else ['ALL_ARM_FALLBACK' if allfallback else 'MIXED_FALLBACK'])+(['WEEK1_STARTUP']if week==1 else [])
def source_files(private,rel,kind):
 p=private/rel
 return sorted(f for f in p.glob('W0[1-7]-*.json.gz'))if kind=='chunks'else[p]
def prepare(a):
 a.output.mkdir(parents=True);sources=[]
 for name,rel,kind,year in SPECS:
  files=source_files(a.private_root,rel,kind)
  if not files:raise ValueError('required retained source missing '+name)
  sources.append(dict(source_id=name,logical_members=[dict(member=f.relative_to(a.private_root).as_posix(),sha256=s.sha(f),bytes=f.stat().st_size)for f in files],kind=kind,evaluation_season=year))
 p=dict(version='v2-adjacent-history-retained-row-v1',registered_at=s.now(),state='FROZEN_BEFORE_NEW_COMPARATIVE_BULK_DECODE',code_sha256=s.sha(__file__),paired_helper_sha256=s.sha('nfl_v2/paired_uncertainty.py'),packet_reader_sha256=s.sha('nfl_v2/shared_subgroups.py'),sources=sources,pre_exposure='All historical data/results exposed by prior work; first schema sample rows inspected before this registration, no new comparative bulkdecode or fits',identity='Exact game/player/target/population/position across allthree core histories; matching actual required; sorted canonicalquerykey hash; only qualified2022–25REG and2026W1–7 from retainedprevious frozenpanels',core_policies=list(CORE),strict='STRICT-current is a separate completeinformation-policy comparison, excludedfrom clean adjacent fit-window contrasts; retained original strict results remainlinked',contrasts=['H-RECENT_MINUS_H-CURRENT','H-MULTI_MINUS_H-RECENT'],views=list(VIEWS),common_learned='Allthree core arms fallback=none on exactsamequery, not separatelydifferent pairmasks',metrics='MAEallnumeric compatiblepoints; BrierTD; MSEseparate intendedmeans. Existingproperdistribution comparisons remainretained; newadjacent proper-law score replay not silentlyinferredfrompointoutputs.',history='SeasonrelativeCURRENT/RECENT/MULTIexpanding2022floor;2022RECENT is available2022proxy, exact2021request unsupported. Common learnedmodels retain2022featurememory; empirical poolhistory changes asregistered estimator.',startup='EveryW1query retained; FULL=COMMON_LEARNED+ANY_FALLBACK; ANY=ALL_FALLBACK+MIXED. WEEK1overlap separate; fallback counts/totalerrorcontribution explicit.',repair='Skipall2025originalrole-specializationrows; replacewithcomplete24148correctedrows, keepotheroriginals andallsourceidentities',budget=dict(wall_seconds=180,cpu_seconds=240,max_rss_bytes=1073741824,max_threads=2,max_rows_read=10000000),new_fit_calls=0,new_forecasts=0,CURRENT_2026_Week8_outcomes_read=0,private_member_contract='Public-safe portable archive member IDs, not private filesystem/service locators')
 s.immutable_json(a.output/'FROZEN_PROTOCOL.json',p);return p

def rows_from(file,kind):
 if kind=='csv':
  with gzip.open(file,'rt')as f:yield from csv.DictReader(f)
 else:yield from packet_rows(file)

def run(a):
 p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_text());start,cpu=time.monotonic(),time.process_time();rowsread=0;allout=[];reports=[];state='COMPLETE';failure=None
 if p['code_sha256']!=s.sha(__file__)or p['paired_helper_sha256']!=s.sha('nfl_v2/paired_uncertainty.py')or p['packet_reader_sha256']!=s.sha('nfl_v2/shared_subgroups.py'):raise ValueError('frozen code changed')
 def guard():
  if time.monotonic()-start>180 or time.process_time()-cpu>240:raise RuntimeError('TIME_BUDGET')
  if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('RSS_BUDGET')
 groups={};pending={};done=set();gamecodes={};coverage=collections.Counter();source_coverage=[]
 def emit(key,arms,year):
  proc,target,pop,product,ident=key;actuals=[arms[h][1]for h in CORE]
  if len(set(actuals))!=1:raise ValueError('history label mismatch')
  if actuals[0]is None:coverage['unknown_label_cases']+=1;return
  ys=actuals[0];fb=[arms[h][2]for h in CORE];week=arms[CORE[0]][3]
  if any(arms[h][3]!=week for h in CORE):raise ValueError('history week mismatch')
  names=view_names(fb,week);qid=hashlib.sha256(s.canonical(ident)).hexdigest();game=gamecodes.setdefault(ident[0],len(gamecodes));metrics=['Brier']if target=='anytime_td'else['MAE']+(['MSE']if product in('mean','empirical_mean','squared_error_mean','poisson_intended_mean_point')else[])
  for label,new,old in [('H-RECENT_MINUS_H-CURRENT','H-RECENT','H-CURRENT'),('H-MULTI_MINUS_H-RECENT','H-MULTI','H-RECENT')]:
   for metric in metrics:
    k=(year,proc,target,pop,product,label,metric)
    for view in VIEWS:
     groupkey=k+(view,)
     if groupkey not in groups:groups[groupkey]=dict(a=array('d'),b=array('d'),w=array('B'),g=array('H'),ids=[],fallbacks=[collections.Counter()for _ in CORE])
     g=groups[groupkey]
     if view not in names:continue
     prednew,predold=arms[new][0],arms[old][0];la=(prednew-ys)**2 if metric in('MSE','Brier')else abs(prednew-ys);lb=(predold-ys)**2 if metric in('MSE','Brier')else abs(predold-ys);g['a'].append(la);g['b'].append(lb);g['w'].append(week);g['g'].append(game);g['ids'].append(qid)
     for count,flag in zip(g['fallbacks'],fb):count[flag]+=1
 def finish_year(year):
  nonlocal groups
  out=[]
  for key,g in sorted(groups.items()):
   guard();yr,proc,target,pop,product,contrast,metric,view=key;r=paired_losses(g['a'],g['b'],g['w'],g['g']);full=groups[key[:-1]+('FULL_SYSTEM',)];nfull=len(full['a']);n=len(g['a']);total_delta=math.fsum(x-y for x,y in zip(g['a'],g['b']))if n else 0.
   out.append(dict(procedure_id=proc,target=target,population=pop,product_id=product,evaluation_seasons=[yr],evaluation_weeks=sorted(set(g['w'])),season=yr,contrast=contrast,fallback_view=view,metric=metric,evaluation_panel_id=p['version']+':'+str(yr),record_kind='DERIVED_PAIRED_HISTORY_COMPARISON',evidence='NEW_EXPERIMENT_SAVED_ROW_REPLAY',history_regime='ADJACENT_CORE_COMPARISON',requested_history_status='SOURCE_LIMITED_AVAILABLE2022_PROXY_EXACT2021_REQUEST_INCOMPLETE'if yr==2022 else'REGISTERED_RELATIVE_HISTORY',membership_sha256=membership(g['ids']),fallback_source_counts={h:dict(c)for h,c in zip(CORE,g['fallbacks'])},fullsystem_n=nfull,loss_difference_sum=total_delta,contribution_to_fullsystem_delta=total_delta/nfull if nfull else None,negative_favors_new=True,**r))
  path=a.output/f'HISTORY_COMPARISONS_{year}.json';s.immutable_json(path,out);emp.write_csv(a.output/f'HISTORY_COMPARISONS_{year}.csv',out);allout.extend(out);groups={};r=dict(season=year,comparison_views=len(out),actual_completed_at=s.now(),source_output_sha256=s.sha(path),resource_so_far=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024));reports.append(r);s.immutable_json(a.output/f'YEAR_{year}_RECEIPT.json',r)
 with threadpool_limits(limits=2):
  try:
   previous_year=2025
   for (name,rel,kind,year),bound in zip(SPECS,p['sources']):
    if year!=previous_year:
     if pending:raise ValueError('incomplete core arm set at season boundary')
     finish_year(previous_year);done.clear();gamecodes.clear();previous_year=year
    count=0
    for member in bound['logical_members']:
     file=a.private_root/member['member']
     if s.sha(file)!=member['sha256']:raise ValueError('retained input changed')
     for raw in rows_from(file,kind):
      rowsread+=1
      if rowsread%10000==0:guard()
      if rowsread>10000000:raise RuntimeError('ROW_BUDGET')
      # Filter future/other-year metadata before prediction or actual conversion.
      if int(raw.get('season',year))!=year or year==2026 and not 1<=int(raw['week'])<=7:continue
      arm=raw['history_regime'];proc=procedure(raw,name)
      if arm not in CORE or 'strict' in proc.lower()or 'STRICT'in(raw.get('policy_id')or''):continue
      if name=='season2025'and'qb-rb-specialization'in proc:continue
      product=raw.get('product_id')or raw.get('product')or raw.get('objective');product='mean'if product=='empirical_mean'else product
      ident=tuple(raw[x]for x in('game_id','player_id','target','population','position'));key=(proc,raw['target'],raw['population'],product,ident)
      if key in done:raise ValueError('duplicate completed core case')
      arms=pending.setdefault(key,{})
      if arm in arms:raise ValueError('duplicate arm')
      arms[arm]=(number(raw['prediction']),number(raw.get('actual')),raw['fallback'],int(raw['week']));count+=1
      if len(arms)==3:emit(key,arms,year);del pending[key];done.add(key);coverage['complete_core_cases']+=1
    source_coverage.append(dict(source_id=name,admitted_rows=count,pending_cases=len(pending)))
   if pending:raise ValueError('incomplete final core arm set')
   finish_year(previous_year)
  except Exception as exc:state='PARTIAL_STOPPED';failure=dict(type=type(exc).__name__,reason=str(exc))
 s.immutable_json(a.output/'SCORES.json',allout);emp.write_csv(a.output/'SCORES.csv',allout)
 receipt=dict(state=state,actual_completed_at=s.now(),protocol_sha256=s.sha(a.output/'FROZEN_PROTOCOL.json'),code_sha256=s.sha(__file__),completed_years=[r['season']for r in reports],source_coverage=source_coverage,coverage=dict(coverage),pending_cases=len(pending),comparison_views=len(allout),rows_read=rowsread,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=2),failure=failure,new_fit_calls=0,new_forecasts=0,CURRENT_2026_Week8_outcomes_read=0)
 s.immutable_json(a.output/'RUN_RECEIPT.json',receipt);return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--private-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a)if a.action=='prepare'else run(a)))
