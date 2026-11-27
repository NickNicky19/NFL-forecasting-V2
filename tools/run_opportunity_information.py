"""One frozen usage-only opportunity test; no acquisition or production writes.

PBP derivatives: nflverse/nflfastR CC-BY4.0. Fixed conversion uses the
retained FTN/nflverse CC-BY-SA4.0-derived SKILL_R0. Seven-day current-vintage
reconstruction is not authenticated original publication.
"""
from __future__ import annotations
import argparse,atexit,copy,hashlib,json,math,platform,resource,sys,time
from pathlib import Path
import numpy as np
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import player_context_matchup as ctx,opportunity_information as oi
from nfl_v2.passing_opportunity_profiles import OpportunityHistory
from nfl_v2.distribution_wave_v2 import FittedLawModel
from nfl_v2.distribution_laws import prior
from tools.run_player_context_wave import read,write,sha,now
BASE=ROOT/'reports/information-skill-follow-through-01/B/opportunity-v1'
OUT=BASE/'wave-v1'
INPUT=ROOT/'reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz'
SOURCE=ROOT/'reports/profile-increment-to-release-01/B/source-profiles/PASSING_OPPORTUNITY_GAME_INPUTS_V2.json.gz'
PARENT=ROOT/'reports/information-skill-01/B/wave-v1/predictions'
IDENTITY=('game_id','player_id','season','week','team','opponent','kickoff')
ARMS=('OPP_BASE','OPP_MEAN','OPP_JOINT','DIRECT_ATT')
def query(r):return {k:r[k]for k in IDENTITY}
def direct_features(qb,q):return np.asarray(qb.base_history.get(q['player_id'],'QB','pass_att',q['kickoff'])[0],float)
def context():
 rows=ctx.load_inputs(INPUT);body=read(SOURCE)
 h=OpportunityHistory(body['team_games'],body['QB_games'])
 qb=ctx.ContextHistory(rows,8,20.)
 parents={};bindings={}
 for p in sorted(PARENT.glob('2026-*.json.gz')):
  bindings[str(p.relative_to(ROOT))]=sha(p)
  for r in read(p)['rows']:
   if r['method']=='SKILL_R0':parents[r['game_id'],r['player_id']]=r
 assert len(parents)==315
 return rows,h,qb,parents,bindings
class Budget:
 def __init__(self):
  self.start=time.monotonic();self.cpu=time.process_time();self.path=OUT/'FIT_ATTEMPTS.jsonl';self.events=OUT/'RESOURCE_EVENTS.jsonl'
  previous=[json.loads(r)for r in self.events.read_text().splitlines()]if self.events.exists()else[]
  self.prior=previous[-1]['cumulative_recorded_CPU_seconds']if previous else read(OUT/'PREPARATION_RESOURCE_V1.json')['CPU_seconds']+read(BASE/'PREPARATION_FAILURE_V1.json')['conservative_budget_charge_seconds']
  if not previous:
   self.prior+=sum(float(read(p).get('resources',{}).get('CPU_seconds',0.))for p in(BASE/'independent').glob('PREFIT_CHECK_V*.json'))
  atexit.register(self.checkpoint,'PROCESS_EXIT')
 def calls(self):return len(self.path.read_text().splitlines())if self.path.exists()else 0
 def used(self):return self.prior+time.process_time()-self.cpu
 def checkpoint(self,stage):
  r=dict(UTC=now(),stage=stage,cumulative_recorded_CPU_seconds=self.used(),runner_wall=time.monotonic()-self.start,optimizer_calls=self.calls(),peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,accounting='Runner CPU and preparation; separate qualification/scoring/checks measured separately; not complete total CPU.')
  with self.events.open('a')as f:f.write(json.dumps(r)+'\n')
  return r
 def charge(self,slot):
  if self.calls()>=36 or self.used()>720 or time.monotonic()-self.start>600 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('FROZEN_RESOURCE_OR_COMPLETION_RESERVE_GUARD')
  with self.path.open('a')as f:f.write(json.dumps(dict(slot=slot,attempt=self.calls()+1,UTC=now()))+'\n')
  self.checkpoint('BEFORE_'+slot)
def prepare():
 start=time.process_time();OUT.mkdir(exist_ok=True);rows,h,qb,parents,bindings=context()
 teammap={(r['game_id'],r['team']):r for r in h.team_rows}
 bad=[];outside=0
 for r in h.qb_rows:
  t=teammap[r['game_id'],r['team']]
  if r['counts']['credited_attempts']>t['counts']['opportunities']:bad.append([r['game_id'],r['player_id']])
  outside+=max(0,r['counts']['credited_attempts']-r['counts']['dropbacks'])
 assert not bad
 trace=[]
 for r in rows:
  if r['season']!=2026:continue
  q=query(r);d=oi.build_design(h,q)
  trace.append(dict(query=q,design=d,direct_features=direct_features(qb,q).tolist(),conversion=parents[q['game_id'],q['player_id']]['components']['integrated_completion_probability']))
 write(OUT/'QUERY_TRACE_V1.json.gz',dict(rows=trace,query_target_fields_consumed=False))
 code=[Path(__file__),ROOT/'nfl_v2/opportunity_information.py',ROOT/'nfl_v2/passing_opportunity_profiles.py',ROOT/'nfl_v2/player_context_matchup.py',ROOT/'nfl_v2/distribution_wave_v2.py',ROOT/'nfl_v2/distribution_laws.py']
 write(OUT/'SEALED_INPUTS_AND_CODE_V1.json',dict(state='NO_NEW_NFL_FITS',UTC=now(),code={str(p.relative_to(ROOT)):sha(p)for p in code},inputs={str(p.relative_to(ROOT)):sha(p)for p in(INPUT,SOURCE)},parent_predictions=bindings,design_sha256=sha(BASE/'FROZEN_DESIGN_V1.json'),boundary_sha256=sha(BASE/'PREFIT_BOUNDARY_ADDENDUM_V1.json'),preflight=dict(QB_rows=len(h.qb_rows),team_rows=len(h.team_rows),A_over_T_violations=len(bad),credited_attempts_outside_dropbacks=outside),plan=[[2026,w]for w in range(1,10)]))
 write(OUT/'ENVIRONMENT_V1.json',dict(Python=platform.python_version(),numpy=np.__version__,source_vintage='CURRENT_REVISED',timing='SEVEN_DAY_STRICT_LT'))
 write(OUT/'PREPARATION_RESOURCE_V1.json',dict(CPU_seconds=time.process_time()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,new_NFL_fits=0))
 print('PREPARED_NO_FIT')
def fit_arrays(h,qb,rows,cutoff,season):
 teams=[r for r in h.team_rows if r['season']>=season-1 and r['available']<cutoff]
 qbs=[r for r in h.qb_rows if r['season']>=season-1 and r['available']<cutoff]
 tm={(r['game_id'],r['team']):r for r in h.team_rows};tx=[];to=[];ty=[];sx=[];so=[];sn=[];sy=[];tids=[];sids=[]
 for r in teams:
  d=oi.build_design(h,dict(r,player_id='__TEAM_ONLY__'))
  if d['team_offset']is None:continue
  tx.append(d['team_x']);to.append(d['team_offset']);ty.append(r['counts']['opportunities']);tids.append([r['game_id'],r['team']])
 for r in qbs:
  d=oi.build_design(h,r)
  if not d['eligible']:continue
  T=tm[r['game_id'],r['team']]['counts']['opportunities'];A=r['counts']['credited_attempts']
  x=list(d['share_x']);x[2]=math.log(T/d['T_reference'])if T else 0.
  sx.append(x);so.append(d['share_offset']);sn.append(T);sy.append(A);sids.append([r['game_id'],r['player_id']])
 direct=[r for r in rows if r['season']>=season-1 and r['available']<cutoff and r.get('physical_participation')and r.get('target_parity')and r.get('official_attempts')is not None]
 dx=np.asarray([direct_features(qb,r)for r in direct]);dy=np.asarray([r['official_attempts']for r in direct])
 return dict(team_X=np.asarray(tx),team_offset=np.asarray(to),team_y=np.asarray(ty),share_X=np.asarray(sx),share_offset=np.asarray(so),share_n=np.asarray(sn),share_y=np.asarray(sy),direct_X=dx,direct_y=dy,team_ids=tids,share_ids=sids,direct_ids=[[r['game_id'],r['player_id']]for r in direct])
def run():
 seals=sorted(OUT.glob('SEALED_INPUTS_AND_CODE_V*.json'),key=lambda p:int(p.stem.rsplit('V',1)[1]));seal=read(seals[-1])
 for p,digest in {**seal['code'],**seal['inputs'],**seal['parent_predictions']}.items():assert sha(ROOT/p)==digest,p
 assert seal['design_sha256']==sha(BASE/'FROZEN_DESIGN_V1.json')and seal['boundary_sha256']==sha(BASE/'PREFIT_BOUNDARY_ADDENDUM_V1.json')
 b=Budget();rows,h,qb,parents,_=context();tm={(r['game_id'],r['team']):r for r in h.team_rows}
 with threadpool_limits(limits=2):
  for season,week in seal['plan']:
   dest=OUT/'predictions'/f'{season}-W{week:02}.json.gz'
   if dest.exists():continue
   qs=[r for r in rows if(r['season'],r['week'])==(season,week)];cutoff=min(r['kickoff']for r in qs);a=fit_arrays(h,qb,rows,cutoff,season)
   states={}
   for kind in ('team','share','direct'):
    fp=OUT/'fits'/f'{season}-W{week:02}-{kind}.json.gz'
    if fp.exists():states[kind]=read(fp)['state'];continue
    b.charge(f'{season}_{week}_{kind}');start=time.process_time()
    if kind=='team':state=oi.fit_team(a['team_X'],a['team_offset'],a['team_y'])
    elif kind=='share':state=oi.fit_share(a['share_X'],a['share_offset'],a['share_n'],a['share_y'])
    else:
     m=FittedLawModel('ordered_leaf_cdf','pass_att').fit(a['direct_X'],a['direct_y'],['QB']*len(a['direct_y']));state=dict(model=ctx.export_forest(m),prior=prior(a['direct_y'],'pass_att').parameters(),optimization=dict(success=True,rows=len(a['direct_y'])))
    states[kind]=state
    write(fp,dict(state=state,fit_cutoff=cutoff,CPU_seconds=time.process_time()-start,member_sha256=hashlib.sha256(json.dumps(a[kind+'_ids']).encode()).hexdigest(),rows=len(a[kind+'_ids'])))
    b.checkpoint('AFTER_'+kind)
   # Raw designs are safe licensed derivatives; retain exact earlier arrays for independent fits.
   write(OUT/'training-designs'/f'{season}-W{week:02}.json.gz',a)
   result=[];components=[]
   for r in qs:
    q=query(r);d=oi.build_design(h,q);parent=parents[q['game_id'],q['player_id']];pi=parent['components']['integrated_completion_probability'];pa=parent['components']['attempt_law'];base=ctx.CountLaw(pa['mean'],pa['shape'])
    fallback=[]
    if not d['eligible']or not states['team']['optimization']['success']or not states['share']['optimization']['success']:
     joint=base;fallback.append(d.get('fallback_reason')or'OPTIMIZATION_FALLBACK')
    else:
     try:joint=oi.mixed_law(states['team'],states['share'],d)
     except(oi.SupportError,oi.IntegrationError)as exc:joint=base;fallback.append('PARENT_LAW_AFTER_'+type(exc).__name__+':'+str(exc))
    x=direct_features(qb,q);direct=ctx.restored_forest_law(states['direct']['model'],x,oi.restore_law(states['direct']['prior']))
    own_support=len(qb.player_rows(q['player_id'],q['kickoff']))
    if not own_support:direct=base
    for arm in ARMS:
     alaw=base if arm=='OPP_BASE'else ctx.CountLaw(joint.mean,pa['shape'])if arm=='OPP_MEAN'else joint if arm=='OPP_JOINT'else direct
     for target in ('pass_att','pass_cmp'):
      law=alaw if target=='pass_att'else oi.thin_law(alaw,pi)
      why=list(fallback)if arm in('OPP_MEAN','OPP_JOINT')else[]
      if arm=='DIRECT_ATT'and not own_support:why.append('NO_OWN_QB_HISTORY_PARENT_LAW')
      parentfb=parent.get('fallback','none')
      output=dict(q,target=target,method=arm,procedure_id='B-INFORMATION-SKILL-OPPORTUNITY-v1:'+arm,fit_cutoff=cutoff,feature_cutoff=q['kickoff'],mean=law.mean,lower_median=law.quantile(.5),law=oi._payload(law),fallback=why if why else parentfb,implementation_fallbacks=why,components=dict(conversion_fixed=pi,parent_attempt_law=pa,team_opportunity_proxy=True,personnel_used=False),original_issuance=False,evidence_tier='CURRENT_VINTAGE_7DAY_CONDITIONAL_QUERY_RECONSTRUCTION')
      output.update(actual=r['official_attempts'if target=='pass_att'else'official_completions'],actual_status=parent.get('actual_status'));result.append(output)
     components.append(dict(method=arm,game_id=q['game_id'],player_id=q['player_id'],season=season,week=week,predicted_attempt_mean=alaw.mean,actual_attempts=r['official_attempts'],predicted_completion_mean=alaw.mean*pi,actual_completions=r['official_completions'],conversion=pi,other_bucket_mean=joint.team_mean-alaw.mean if arm=='OPP_JOINT'and hasattr(joint,'team_mean')else None,team_opportunity_mean=getattr(joint,'team_mean',None)if arm=='OPP_JOINT'else None,actual_team_opportunities=tm.get((q['game_id'],q['team']),{}).get('counts',{}).get('opportunities'),fallback=why))
   write(dest,dict(rows=result,fit_cutoff=cutoff,origin_UTC=now(),original_issuance=False))
   write(OUT/'components'/f'{season}-W{week:02}.json.gz',dict(rows=components));b.checkpoint('ORIGIN_SAVED')
 write(OUT/'RUN_RECEIPT_V1.json',dict(state='FROZEN_ORIGINS_EXECUTED',resource=b.checkpoint('COMPLETE'),new_data_acquisition=0,personnel_used=False,production_activation=False))
 print(json.dumps(b.checkpoint('PRINT')))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));a=p.parse_args();prepare()if a.action=='prepare'else run()
