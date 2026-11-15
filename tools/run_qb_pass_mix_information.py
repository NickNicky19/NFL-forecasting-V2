"""Bounded INFORMATION-SKILL-01 origin fits; no source acquisition/selection search.

FTN-dependent parameters/derived predictions: FTN Data via nflverse, CC-BY-SA4.0.
Ordinary PBP derivatives: nflverse/nflfastR, CC-BY4.0. Source vintages and
seven-day reconstructed availability are retained, not original publication.
"""
from __future__ import annotations
import argparse,atexit,copy,gzip,hashlib,json,math,platform,resource,sys,time
from pathlib import Path
import numpy as np
import scipy
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import player_context_matchup as ctx,qb_pass_mix_information as skill
from nfl_v2.qb_depth_catchability import DepthHistory
from tools.run_player_context_wave import read,write,sha,now,clean
INPUT=ROOT/'reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz'
CHART=ROOT/'reports/player-context-completion-decision-01/B/source-depth-v1/FTN_DEPTH_QB_GAME_INPUTS.json.gz'
BASE=ROOT/'reports/information-skill-01/B';OUT=BASE/'wave-v1'
PARENT=ROOT/'reports/targeted-accuracy-w1w9-01/B/wave-v1/predictions'
IDENTITY=('game_id','player_id','season','week','team','opponent','kickoff')
ARMS=('SKILL_C0','SKILL_C1','SKILL_R0','SKILL_R1')

def query_only(row):return {k:row[k]for k in IDENTITY}
def context():
 rows=ctx.load_inputs(INPUT);h=ctx.ContextHistory(rows,8,20.);ch=DepthHistory(rows,read(CHART),8,20.)
 return rows,h,ch,skill.PassMixHistory(h)
def parent_rows():
 out={};paths={}
 for p in sorted(PARENT.glob('2026-*.json.gz')):
  paths[str(p.relative_to(ROOT))]=sha(p)
  for r in read(p)['rows']:
   if r['method']=='M2_C2_BIN':out[r['game_id'],r['player_id']]=r
 assert len(out)==315
 return out,paths

class Budget:
 def __init__(self):
  self.path=OUT/'OPTIMIZER_ATTEMPTS.jsonl';self.resources=OUT/'RESOURCE_EVENTS.jsonl'
  self.start=time.monotonic();self.cpu=time.process_time();self.child0=resource.getrusage(resource.RUSAGE_CHILDREN)
  self.previous=0.
  for overhead_path in (OUT/'PREPARATION_RESOURCE_V1.json', BASE/'independent/PREFIT_RESOURCE_V1.json'):
   if overhead_path.exists():self.previous+=float(read(overhead_path).get('CPU_seconds',0.))
  if self.resources.exists():
   events=[json.loads(v)for v in self.resources.read_text().splitlines()];self.previous=events[-1]['cumulative_recorded_CPU_seconds']if events else 0.
  atexit.register(self.checkpoint,'PROCESS_EXIT')
 def calls(self):return len(self.path.read_text().splitlines())if self.path.exists()else 0
 def cpu_used(self):
  child=resource.getrusage(resource.RUSAGE_CHILDREN)
  return time.process_time()-self.cpu+child.ru_utime+child.ru_stime-self.child0.ru_utime-self.child0.ru_stime
 def checkpoint(self,phase):
  r=dict(UTC=now(),phase=phase,process_CPU_seconds=self.cpu_used(),prior_recorded_CPU_seconds=self.previous,
    cumulative_recorded_CPU_seconds=self.previous+self.cpu_used(),process_wall_seconds=time.monotonic()-self.start,
    peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,optimizer_calls=self.calls(),
    accounting='Measured runnerprocess+childCPU; separate preparation/software/sourcequalification overhead recorded separately, not claimed complete taskCPU')
  with self.resources.open('a')as f:f.write(json.dumps(r)+'\n')
  return r
 def charge(self,slot):
  if self.calls()>=48:raise RuntimeError('REGISTERED_OPTIMIZER_CAP48')
  if self.previous+self.cpu_used()>1020:raise RuntimeError('CPU_COMPLETION_RESERVE180_UNDER_CAP1200')
  if time.monotonic()-self.start>900:raise RuntimeError('REGISTERED_FIT_WALL_CAP900')
  if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('REGISTERED_RSS_CAP')
  with self.path.open('a')as f:f.write(json.dumps(dict(slot=slot,attempt=self.calls()+1,started_UTC=now(),NFL_fit=True))+'\n')
  self.checkpoint('BEFORE_'+slot)

def prepare():
 OUT.mkdir(exist_ok=False);start=time.monotonic();cpu=time.process_time();rows,h,ch,profiles=context();parents,pbindings=parent_rows()
 qrows=[q for q in rows if q['season']==2026 and q['week']in range(1,10)]
 assert len(qrows)==315 and {(q['game_id'],q['player_id'])for q in qrows}==set(parents)
 inputs=[]
 for q in qrows:
  qq=query_only(q);d=profiles.describe(qq);pr=parents[q['game_id'],q['player_id']]
  assert np.array_equal(np.asarray(pr['components']['predicted_context_mix']),d['base_mix'])
  attempt=h.exposure(qq);assert attempt.parameters()==pr['components']['attempt_law']
  inputs.append(dict(query=qq,profile=d,conversion_numeric=skill.AugmentedConversion().matrix(qq,h,ch,profiles).tolist(),
    original_composition_design=[x.tolist()for x in skill.composition_design(qq,profiles,False)],
    enriched_composition_design=[x.tolist()for x in skill.composition_design(qq,profiles,True)],parent_attempt_law=pr['components']['attempt_law']))
 write(OUT/'QUERY_FEATURE_TRACE_V1.json.gz',dict(rows=inputs,feature_order=list(skill.CONVERSION_FEATURE_ORDER),query_target_fields_consumed=False))
 code=[Path(__file__),ROOT/'nfl_v2/qb_pass_mix_information.py',ROOT/'nfl_v2/player_context_matchup.py',ROOT/'nfl_v2/qb_depth_catchability.py',ROOT/'nfl_v2/qb_depth_catchability_v2.py']
 proto=dict(id=skill.VERSION,design_sha256=sha(BASE/'FROZEN_DESIGN_V1.json'),source_inputs={str(p.relative_to(ROOT)):sha(p)for p in(INPUT,CHART)},code={str(p.relative_to(ROOT)):sha(p)for p in code},parent_predictions=pbindings,arms=list(ARMS),plan=[[2026,w]for w in range(1,10)],source_clock='UNMODIFIED7DAY_RECONSTRUCTED_STRICT_LT',same_ATT_law_checked315=True,query_rows315=True,prepared_UTC=now(),state='CODE_INPUTS_PARENT_AND_QUERYTRACE_SEALED_BEFORE_FITS')
 write(OUT/'SEALED_INPUTS_AND_CODE_V1.json',proto)
 write(OUT/'ENVIRONMENT_V1.json',dict(Python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform()))
 write(OUT/'PREPARATION_RESOURCE_V1.json',dict(wall_seconds=time.monotonic()-start,CPU_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,new_fits=0))
 print(json.dumps(dict(state='PREPARED_NO_FIT',queries315=True,CPU_seconds=time.process_time()-cpu)))

def fitted(path,slot,budget,factory,fitargs,cutoff,train):
 if path.exists():
  obj=read(path);return factory.restore(obj['model']),obj
 budget.charge(slot);start=time.process_time()
 try:
  model=factory().fit(*fitargs)
  successful=bool(model is not None and model.optimization['success'])
  obj=dict(slot=slot,model=model.payload()if model is not None else None,fit_cutoff=cutoff,
    source_latest=max((r['available']for r in train),default=None),training_games=len(train),
    training_membership_sha256=hashlib.sha256(json.dumps([(r['game_id'],r['player_id'])for r in train]).encode()).hexdigest(),
    optimization_success=successful,registered_fallback=not successful,CPU_seconds=time.process_time()-start,completed_UTC=now())
  write(path,obj)
  return model,obj
 finally:budget.checkpoint('AFTER_'+slot)

def run(max_origins=None):
 proto=read(OUT/('SEALED_INPUTS_AND_CODE_V2.json'if(OUT/'SEALED_INPUTS_AND_CODE_V2.json').exists()else'SEALED_INPUTS_AND_CODE_V1.json'))
 assert proto['design_sha256']==sha(BASE/'FROZEN_DESIGN_V1.json')
 for p,digest in {**proto['source_inputs'],**proto['code'],**proto['parent_predictions']}.items():assert sha(ROOT/p)==digest,p
 budget=Budget();rows,h,ch,profiles=context();parents,_=parent_rows();count=0
 with threadpool_limits(limits=2):
  for season,week in proto['plan']:
   path=OUT/'predictions'/f'{season}-W{week:02}.json.gz'
   if path.exists():continue
   if max_origins is not None and count>=max_origins:break
   qs=[q for q in rows if(q['season'],q['week'])==(season,week)];cutoff=min(q['kickoff']for q in qs)
   train=h.eligible(cutoff,season-1);assert all(r['available']<cutoff for r in train)
   conv,co=fitted(OUT/'fits'/f'{season}-W{week:02}-C1.json.gz',f'{season}-W{week:02}-C1_CONVERSION',budget,skill.AugmentedConversion,(train,h,ch,profiles),cutoff,train)
   mixes={}
   for name,enriched in [('R0',False),('R1',True)]:
    class Factory:
     def __new__(cls):return skill.CompositionModel(enriched)
     @staticmethod
     def restore(p):return skill.CompositionModel.restore(p)
    mixes[name]=fitted(OUT/'fits'/f'{season}-W{week:02}-{name}.json.gz',f'{season}-W{week:02}-{name}_MIX',budget,Factory,(train,profiles),cutoff,train)
   outputs=[];components=[]
   for q in qs:
    qq=query_only(q);parent=parents[q['game_id'],q['player_id']];d=profiles.describe(qq);fixed=parent['components'];p0=np.asarray(fixed['conditional_completion_probability']);m0=np.asarray(fixed['predicted_context_mix']);a=fixed['attempt_law']
    p1=conv.probabilities(qq,h,ch,profiles)if co['optimization_success']else p0
    for arm in ARMS:
     fp=[];mix=m0;p=p0
     if arm in('SKILL_C1','SKILL_R1'):
      p=p1
      if not co['optimization_success']:fp.append('C1_CONVERSION_OPTIMIZATION_FALLBACK_TO_PARENT')
     if arm in('SKILL_R0','SKILL_R1'):
      name=arm[-2:];model,fit=mixes[name]
      if fit['optimization_success']:mix=model.probabilities(qq,profiles)
      else:fp.append(name+'_MIX_OPTIMIZATION_FALLBACK_TO_PARENT')
     prob=float(np.dot(mix,p));law=ctx.CountLaw(a['mean']*prob,a['shape'])
     assert 0<=prob<=1 and np.isfinite(mix).all()and abs(sum(mix)-1)<1e-10
     if arm=='SKILL_C0':assert abs(law.mean-parent['mean'])<1e-10
     parentfallback=parent.get('fallback','none');fallback=fp if fp else parentfallback
     output=dict(qq,method=arm,procedure_id=skill.VERSION+':'+arm,target='pass_cmp',fit_cutoff=cutoff,feature_cutoff=q['kickoff'],
       mean=law.mean,lower_median=law.quantile(.5),law=law.parameters(),
       components=dict(attempt_law=a,predicted_context_mix=mix.tolist(),conditional_completion_probability=p.tolist(),integrated_completion_probability=prob),
       original_parent_fit_cutoff=parent.get('original_parent_fit_cutoff',parent['fit_cutoff']),parent_method='M2_C2_BIN',
       fallback=fallback,implementation_fallbacks=fp,original_issuance=False,evidence_tier='CURRENT_VINTAGE7DAY_CHRONOLOGICAL_QB_STATROW_CONDITIONAL_RECONSTRUCTION')
     # Labels are attached only after inference, never passed into a predictor.
     output.update(actual=parent.get('actual'),actual_status=parent.get('actual_status'))
     outputs.append(output)
     n=np.asarray(q['context_attempts'],float);c=np.asarray(q['context_completions'],float)
     components.append(dict(method=arm,game_id=q['game_id'],player_id=q['player_id'],season=season,week=week,
       observed_attempts=float(n.sum()),observed_completions=float(c.sum()),physical_participation=q['physical_participation'],target_parity=q['target_parity'],
       predicted_attempt_mean=a['mean'],predicted_conversion=prob,predicted_completion_mean=law.mean,
       mix_cross_entropy=float(-np.dot(n,np.log(mix))/n.sum())if n.sum()else None,
       mix_multinomial_Brier=float(np.sum(n*(1-2*mix))/n.sum()+np.sum(mix*mix))if n.sum()else None,
       conditional_conversion_logloss=float(-np.sum(c*np.log(p)+(n-c)*np.log1p(-p))/n.sum())if n.sum()else None,
       diagnostic_actual_attempt_mean_prediction=float(n.sum()*prob),diagnostic_actual_mix_conversion=float(np.dot(n,p)/n.sum())if n.sum()else None,
       deployment_note='Actual attempts/mix used only in postforecast diagnostic metrics; not in saved forecast inputs'))
   write(path,dict(rows=outputs,fit_cutoff=cutoff,origin_UTC=now(),original_issuance=False))
   write(OUT/'component-metrics'/f'{season}-W{week:02}.json.gz',dict(rows=components))
   budget.checkpoint(f'ORIGIN_{season}_{week}_SAVED');count+=1
 write(OUT/'RUN_RECEIPT_V1.json',dict(state='FROZEN_ORIGINS_EXECUTED',new_origins_in_process=count,resource=budget.checkpoint('RUN_COMPLETE'),retention_reserve_CPU_seconds=180,source_discovery_reads=0,new_selection_rules=0))
 print(json.dumps(dict(state='RUN_COMPLETE',origins=count,resource=budget.checkpoint('PRINT_RESULT'))))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['prepare','run']);ap.add_argument('--max-origins',type=int);a=ap.parse_args()
 prepare()if a.action=='prepare'else run(a.max_origins)
