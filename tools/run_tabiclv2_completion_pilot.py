"""One frozen direct-classifier pilot; public predictions omit protected contexts.

Call only through guard_tabiclv2_pilot.py. No scoring occurs in the canary.
"""
from __future__ import annotations
import argparse,copy,datetime,gzip,hashlib,importlib.metadata,importlib.util,json,math,pathlib,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import numpy as np
from nfl_v2 import tabiclv2_direct_pilot as model
PUBLIC=ROOT/'reports/predictive-value-next-01/B/execution-authorization-02'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def write(p,d):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 if p.exists():raise FileExistsError('No overwritten output '+p.name)
 with p.open('x')as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n');f.flush();__import__('os').fsync(f.fileno())
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def runtime_probe(runtime):
 sys.path[:0]=[str(runtime/'site'),str(runtime/'source/src')]
 import torch,tabicl
 torch.set_num_threads(2);torch.set_num_interop_threads(2)
 if torch.__version__!='2.6.0+cpu':raise ValueError('Frozen exact Torch pin differs')
 if sha(runtime/model.CHECKPOINT)!=model.CHECKPOINT_SHA256 or(runtime/model.CHECKPOINT).stat().st_size!=model.CHECKPOINT_BYTES:raise ValueError('Exact trusted checkpoint')
 # weights-only loading, no custom globals/unsafe recovery. No model .fit here.
 body=torch.load(runtime/model.CHECKPOINT,map_location='cpu',weights_only=True)
 if not isinstance(body,dict)or set(body)!={'config','state_dict'}:raise ValueError('Exact approved primitive-config/tensor-state schema required')
 def primitive(x):
  if x is None or type(x)in(str,int,bool):return True
  if type(x)is float:return math.isfinite(x)
  if type(x)in(list,tuple):return all(primitive(y)for y in x)
  if type(x)is dict:return all(isinstance(k,str)and primitive(v)for k,v in x.items())
  return False
 if not primitive(body['config'])or not isinstance(body['state_dict'],dict):raise ValueError('Checkpoint config schema')
 tensors=body['state_dict']
 if not tensors or any(not isinstance(k,str)or not isinstance(v,torch.Tensor)or not torch.isfinite(v).all().item()for k,v in tensors.items()):raise ValueError('Invalid/nonfinite tensor state')
 from threadpoolctl import threadpool_info
 return dict(state='PASS_PINNED_SAFE_RUNTIME_SOURCE_RETENTION',checkpoint_sha256=sha(runtime/model.CHECKPOINT),checkpoint_bytes=model.CHECKPOINT_BYTES,checkpoint_config_sha256=digest(body['config']),state_tensor_count=len(tensors),state_parameters=sum(v.numel()for v in tensors.values()),torch=torch.__version__,tabicl=importlib.metadata.version('tabicl')if False else getattr(tabicl,'__version__','2.2.0_PINNED_SOURCE'),source_commit=model.LIBRARY_COMMIT,dependency_lock_sha256=sha(runtime/'DEPENDENCY_LOCK.json'),source_license_sha256=sha(runtime/'source/LICENSE'),safe_loader='torch.load weights_only=True; no added globals or pickle estimator',storage_policy='No KV/context serialization or disk offload; explicit local checkpoint, auto-download disabled',threadpools=threadpool_info(),NFL_fits=0)
def inputs(gradepath):
 from nfl_v2 import player_context_matchup as ctx
 from nfl_v2.hgb_control import FEATURES
 if sha(gradepath)!='dbdbf73a23fea1d7d8c90fde666163853f492b0e9686ae068b829b2bc2816a39':raise ValueError('Exact native source required')
 contextpath=ROOT/'reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz'
 if sha(contextpath)!='45aaab99d41f2e2643066c001355b26430f55dca06e7c7e366eace252f2e021b':raise ValueError('Exact qualified context')
 contexts=ctx.load_inputs(contextpath);history=ctx.ContextHistory(contexts,8,20.);lookup={(r['game_id'],r['player_id']):r for r in contexts}
 body=json.loads(gzip.decompress(gradepath.read_bytes()));source=body['rows']if isinstance(body,dict)else body;rows=[r for r in source if r['model_key']=='B0'and r['policy']=='P1_MEAN'];records=[]
 if len(rows)!=142:raise ValueError('Same142 board')
 for ordinal,r in enumerate(rows):
  q=lookup[r['game_id'],r['player_id']];x,_=history.base_history.get(q['player_id'],'QB','pass_cmp',q['kickoff']);x=np.r_[np.asarray(x,float),r['line']]
  if q['official_completions']!=r['actual']or float(r['line'])%1!=.5:raise ValueError('Qualified half-point event/label parity')
  records.append(dict(ordinal=ordinal,game_id=q['game_id'],player_id=q['player_id'],week=r['week'],kickoff=q['kickoff'],label_available=q['available'],line=r['line'],y=int(r['actual']>r['line']),x=x))
 return contexts,records

def designs(records,week):
 tests=[r for r in records if r['week']==week];origin=min(r['kickoff']for r in tests);games={r['game_id']for r in tests};train=[r for r in records if r['label_available']<origin and r['game_id']not in games]
 def array(rr):return np.asarray([r['x']for r in rr],float)
 def commitment(rr):return digest([dict(ordinal=r['ordinal'],game=r['game_id'],player=r['player_id'],line=r['line'],label=r['y'],features=[None if not np.isfinite(x)else float(x)for x in r['x']])for r in rr])
 return train,tests,array(train),np.asarray([r['y']for r in train]),array(tests),origin,commitment(train),commitment(tests)
def check_design_mutation(contexts,records):
 from nfl_v2 import player_context_matchup as ctx
 checks=[];rebuilt_cache={}
 for w in (7,8,9):
  train,tests,x,y,q,origin,tc,qc=designs(records,w);n=0
  # Fits use the weekly origin; history features use each row's own kickoff.
  # A prior label becoming available by a later query is a legitimate input.
  # Preserve those inputs while mutating only prohibited outcomes per cutoff.
  for cutoff in sorted({r['kickoff']for r in train+tests}):
   if cutoff in rebuilt_cache:continue
   mutated=copy.deepcopy(contexts);changed=0
   for r in mutated:
    if r['available']>=cutoff:
     r['official_completions']=0 if r['official_completions']else min(1,r['official_attempts']);changed+=1
   history=ctx.ContextHistory(mutated,8,20.)
   selected={}
   for r in records:
    if r['kickoff']==cutoff:
     xx,_=history.base_history.get(r['player_id'],'QB','pass_cmp',cutoff)
     selected[r['ordinal']]=np.r_[np.asarray(xx,float),r['line']]
   rebuilt_cache[cutoff]=(selected,changed)
  rebuilt=[]
  for r in train+tests:
   selected,changed=rebuilt_cache[r['kickoff']];rebuilt.append(selected[r['ordinal']]);n+=changed
  original=np.vstack((x,q))
  if not np.array_equal(np.asarray(rebuilt),original,equal_nan=True):raise ValueError('NFL future-outcome mutation altered consumed design')
  state=model.fit_common_transform(x);trans=model.transform(q,state)
  if not np.array_equal(model.transform(np.asarray(rebuilt)[len(train):],state),trans,equal_nan=True):raise ValueError('Transformed query mutation failed')
  checks.append(dict(week=w,mutated_future_rows=n,training_rows=len(train),query_rows=len(tests),train_joint_commitment_sha256=tc,query_joint_commitment_sha256=qc,raw_and_transformed_design_equal=True))
 return checks

def main():
 p=argparse.ArgumentParser();p.add_argument('--runtime',type=pathlib.Path,required=True);p.add_argument('--grades',type=pathlib.Path);p.add_argument('--probe-only',action='store_true');p.add_argument('--week',type=int,choices=[7,8,9]);a=p.parse_args();start=time.process_time();wall=time.monotonic()
 if a.probe_only:
  report=runtime_probe(a.runtime)
  if a.grades:
   contexts,records=inputs(a.grades);report['NFL_data_design_mutations']=check_design_mutation(contexts,records);report['source_retention']='Existing immutable QB context, W5-8 source restorations and W9fe369 original archive/qualified identity bridge; private grade re-creatable, never publicly serialized.'
  report.update(CPU_seconds=time.process_time()-start,wall_seconds=time.monotonic()-wall);write(PUBLIC/'RUNTIME_AND_INPUT_ADMISSION_V1.json',report);print(json.dumps({'state':report['state'],'NFL_fit_calls':0,'CPU_seconds':report['CPU_seconds']}));return
 admission=json.loads((PUBLIC/'RUNTIME_AND_INPUT_ADMISSION_V1.json').read_text())
 if admission['state']!='PASS_PINNED_SAFE_RUNTIME_SOURCE_RETENTION':raise ValueError('Runtime qualification absent')
 sys.path[:0]=[str(a.runtime/'site'),str(a.runtime/'source/src')]
 contexts,records=inputs(a.grades);train,tests,x,y,q,origin,tc,qc=designs(records,a.week)
 expected={7:28,8:56,9:86}
 if len(train)!=expected[a.week]:raise ValueError('Registered earlier training context changed')
 write(PUBLIC/'predictions'/('2026-W%02d_DESIGN.json'%a.week),dict(week=a.week,training_rows=len(train),query_rows=len(tests),train_joint_commitment_sha256=tc,query_joint_commitment_sha256=qc,preprocessing='TRAIN_ONLY_FROZEN_SHARED',fit_cutoff_UTC=datetime.datetime.fromtimestamp(origin,datetime.timezone.utc).isoformat(),not_original_issuance=True))
 from threadpoolctl import threadpool_limits
 original_probability=model.positive_probability
 # Output-preserving per-query retention hook. Each call delegates to the
 # unchanged single-query function; no later labels or query batches enter.
 progress=PUBLIC/'predictions'/('2026-W%02d_PARTIAL.jsonl'%a.week)
 if progress.exists():raise FileExistsError('Preserve original partial predictions')
 def retained_probability(estimator,query):
  name='TABICLV2'if estimator.__class__.__name__=='TabICLClassifier'else'LOGISTIC'
  values=[]
  with progress.open('a')as saved:
   for record,vector in zip(tests,query):
    value=float(original_probability(estimator,np.asarray(vector)[None,:])[0]);values.append(value)
    saved.write(json.dumps(dict(ordinal=record['ordinal'],week=a.week,method=name,p_over=value,event='HALFPOINT_OVER_BERNOULLI'))+'\n');saved.flush();__import__('os').fsync(saved.fileno())
  return np.asarray(values)
 model.positive_probability=retained_probability
 with threadpool_limits(limits=2):
  out=model.execute_origin(x,y,q,a.runtime/model.CHECKPOINT,allocation={'status':'ASSIGNED','experiment':model.VERSION},runtime_admission=admission)
 # Persist only ordinal-derived probabilities, not identities/lines/labels/context.
 rows=[dict(ordinal=r['ordinal'],week=r['week'],candidate_p_over=float(cp),ordinary_p_over=float(lp),attribution='LEARNED')for r,cp,lp in zip(tests,out['candidate_p_over'],out['ordinary_p_over'])]
 result=dict(procedure_id=model.VERSION,week=a.week,training_rows=len(train),query_rows=len(rows),rows=rows,train_joint_commitment_sha256=tc,query_joint_commitment_sha256=qc,configuration_sha256=digest(model.TABICL_CONFIG),source_grade_sha256=sha(a.grades),event='STRICT_HALFPOINT_OVER_BERNOULLI',mean=None,CPU_seconds=time.process_time()-start,wall_seconds=time.monotonic()-wall,quality_inspected=False,transform_sha256=digest(out['transform']),ordinary_model_sha256=digest({'coef':out['ordinary_coef'],'intercept':out['ordinary_intercept']}))
 write(PUBLIC/'predictions'/('2026-W%02d.json'%a.week),result)
 print(json.dumps({'state':'FROZEN_PREDICTIONS_DURABLE_LOCAL_UNGRADED','week':a.week,'queries':len(rows),'CPU_seconds':result['CPU_seconds'],'wall_seconds':result['wall_seconds']}))
if __name__=='__main__':main()
