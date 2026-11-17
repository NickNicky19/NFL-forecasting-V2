"""Independent typed parameter math; no fit or author summary scorer."""
import argparse,datetime,gzip,hashlib,json,math,resource,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from nfl_v2 import player_context_matchup as ctx
from nfl_v2.qb_depth_catchability import DepthHistory,DepthCompletionModel
from nfl_v2.distribution_laws import prior

def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def close(a,b,tol=2e-11):assert abs(float(a)-float(b))<=tol,(a,b)
def nbcdf(k,mu,r):
 if k<0:return 0.
 if mu==0:return 1.
 p=r/(r+mu);term=math.exp(r*math.log(p));terms=[term]
 for i in range(1,int(math.floor(k))+1):term*=((i-1+r)/i)*(1-p);terms.append(term)
 return math.fsum(terms)
def priorq(rows,cutoff):
 ys=[r['official_completions']for r in rows if r['physical_participation']and r['target_parity']and r['season']>=2024 and r['available']<cutoff]
 mu=max(.05,math.fsum(ys)/len(ys));return mu/(1+mu)
def leaf(payload,features,q):
 x=np.asarray(features,float);med=payload['design']['median'];d=np.asarray([a if math.isfinite(a)else b for a,b in zip(x,med)]+[float(not math.isfinite(a))for a in x],np.float32)
 w=[0.]*len(payload['support'])
 for tree in payload['trees']:
  n=0
  while tree['left'][n]!=-1:n=tree['left'][n]if d[tree['feature'][n]]<=tree['threshold'][n]else tree['right'][n]
  h=tree['leaf_histogram']
  for i,j,v in zip(h['rows'],h['columns'],h['values']):
   if i==n:w[j]+=v/32
 z=math.fsum(w);w=[v/z for v in w];support=payload['support']
 mean=.95*math.fsum(a*b for a,b in zip(support,w))+.05*q/(1-q)
 def cdf(k):return 0. if k<0 else .95*math.fsum(v for a,v in zip(support,w)if a<=math.floor(k))+.05*(1-q**(math.floor(k)+1))
 return mean,cdf,w

def probs_manual(model,q,history,chart):
 dd=history.describe(q);cd=chart.describe(q);levels=model['levels'];width=34+int(model['values']);beta=model['beta'];out=[]
 for j in range(25):
  x=[0.]*len(beta);x[j]=1.;a=dd['own_attempts'];c=dd['own_completions'];x[25]=math.log((c+1)/(a-c+1));x[26]=dd['opponent_residual_main'];x[27]=dd['opponent_residual'][j];x[28]=dd['team_residual'];x[29:34]=cd['support'][j%5]
  if model['values']:
   p=cd['shrunk'][j%5];x[34]=math.log(p/(1-p))
  at=width
  for group in ('team','opponent'):
   if q[group]in levels[group]:x[at+levels[group].index(q[group])]=1.
   at+=len(levels[group])
  eta=math.fsum(a*b for a,b in zip(x,beta));out.append(1/(1+math.exp(-eta)))
 return out

def run(base,chartfile,wave,out):
 started=time.monotonic();rows=read(base);history=ctx.ContextHistory(rows,8,20);chart=DepthHistory(rows,read(chartfile),8,20);packet=read(wave/'predictions/2025-W01.json.gz');by={(r['game_id'],r['player_id']):r for r in rows};fq=priorq(rows,packet['fit_cutoff']);saved=packet['rows'];models={a:read(wave/f'fits/2025-W01-{a}.json.gz')['model']for a in ('D1','D2','C1','C2')};checks=[];maxmean=0.;maxprob=0.;sortederrors=[]
 for r in saved:
  q=by[r['game_id'],r['player_id']];a=r['method'];payload=models[a]
  if a.startswith('D'):
   mean,cdf,weights=leaf(payload,r['features'],fq);old=ctx.restored_forest_law(payload,np.asarray(r['features']),prior([x['official_completions']for x in rows if x['physical_participation']and x['target_parity']and x['season']>=2024 and x['available']<packet['fit_cutoff']],'pass_cmp'))
   for k in (-1,0,1,10,19,20,30,60):close(cdf(k),old.cdf(k));maxprob=max(maxprob,abs(cdf(k)-old.cdf(k)))
   sortedpayload=json.loads(json.dumps(payload,sort_keys=True));sm,sc,sw=leaf(sortedpayload,r['features'],fq);close(sm,mean);assert sw==weights
  else:
   ps=probs_manual(payload,q,history,chart);cc=r['components'];assert len(ps)==25 and all(0<=p<=1 for p in ps)
   for p,z in zip(ps,cc['conditional_completion_probability']):close(p,z);maxprob=max(maxprob,abs(p-z))
   mix=cc['predicted_context_mix'];close(math.fsum(mix),1.);ip=math.fsum(m*p for m,p in zip(mix,ps));close(ip,cc['integrated_completion_probability'])
   attempt=cc['attempt_law'];mean=attempt['mean']*ip;shape=attempt['shape'];cdf=lambda k:nbcdf(k,mean,shape)
   close(r['law']['mean'],mean);close(r['law']['shape'],shape)
   restored=DepthCompletionModel.restore(json.loads(json.dumps(payload,sort_keys=True)));rp=restored.probabilities(q,history,chart)
   for p,z in zip(ps,rp):close(p,z);maxprob=max(maxprob,abs(p-z))
   # A count A followed by C|A~Binomial(A,p) gives C<=A and these marginals.
   assert mean<=attempt['mean']+1e-12
  close(mean,r['mean']);maxmean=max(maxmean,abs(mean-r['mean']));median=next(k for k in range(500)if cdf(k)>=.5);assert median==r['lower_median']
  previous=0.
  for k in range(61):
   at=cdf(k);assert at+1e-12>=previous and 0<=at<=1+1e-12;previous=at
   for line in(k,k+.5):
    below=cdf(k-1)if line==k else at;push=(at-below)if line==k else 0.;over=1-at;close(below+push+over,1.);assert min(below,push,over)>-1e-12
  checks.append({'method':a,'query_hash':hashlib.sha256((r['game_id']+':'+r['player_id']).encode()).hexdigest(),'mean':mean,'median':median,'inference':'PASS'})
 # Re-execute the actual saved-model inference in reversed query order.
 # The manual calculations above remain the independent reference.
 errors=[]
 for r in reversed(saved):
  a=r['method'];q=by[r['game_id'],r['player_id']];payload=json.loads(json.dumps(models[a],sort_keys=True))
  if a.startswith('D'):
   fx=chart.direct(q,history,a=='D2');assert np.allclose(fx,r['features'],equal_nan=True,atol=0,rtol=0)
   trained=[x['official_completions']for x in rows if x['physical_participation']and x['target_parity']and x['season']>=2024 and x['available']<packet['fit_cutoff']]
   law=ctx.restored_forest_law(payload,fx,prior(trained,'pass_cmp'));am=law.mean;amed=law.quantile(.5)
  else:
   restored=DepthCompletionModel.restore(payload);ps=restored.probabilities(q,history,chart);mix=history.describe(q)['mix'];am=history.exposure(q).mean*float(mix@ps);amed=next(k for k in range(500)if nbcdf(k,am,history.exposure(q).shape)>=.5)
  close(am,r['mean']);assert amed==r['lower_median'];errors.append(abs(am-r['mean']))
 # Same query identity can occur under4methods; include method to avoid collisions.
 keyed={(r['method'],r['query_hash']):(r['mean'],r['median'])for r in checks};assert len(keyed)==len(checks)
 keyed_reverse={(r['method'],r['query_hash']):(r['mean'],r['median'])for r in reversed(checks)};assert keyed==keyed_reverse
 assert nbcdf(0,0.,20)==1. and nbcdf(-1,0.,20)==0.
 result={'id':'B-DEPTH-PILOT-TYPED-INFERENCE-INDEPENDENT-v2','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS_FINITE_SAVED_INFERENCE_SEPARATE_FROM_OPTIMIZER_ADEQUACY','pilot_prediction_sha256':sha(wave/'predictions/2025-W01.json.gz'),'fit_hashes':[{ 'method':a,'sha256':sha(wave/f'fits/2025-W01-{a}.json.gz'),'optimizer':models[a].get('optimization')}for a in models],'records':len(checks),'unique_QB_queries':len({r['query_hash']for r in checks}),'checks':checks,'max_absolute_mean_difference':maxmean,'max_absolute_probability_difference':maxprob,'sorted_JSON_restore':'PASS','single_reversed_batch_identity':'PASS_ACTUAL_REEXECUTION_REVERSED_ORDER_METHOD_PLUS_QUERY','max_reexecuted_batch_mean_error':max(errors),'CDF_complement_monotonicity_push':'PASS_INTEGER_AND_HALFPOINT_COUNT_GRID','joint_support':'C1/C2 exact binomialthinning only; directD1/D2 remain unrelatedmarginals, no silentcap','zero_attempt_fixture':'PASS_ZERO_COMPLETIONS','optimizer_adequacy':'v2 C1/C2 pilot converged225/223iterations; priorv1 nonconvergence and outputs remain held and preserved. No score chose optimizer amendment.','NFL_fits':0,'NFL_accuracy_scoring':False,'resources':{'wall_seconds':time.monotonic()-started,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}}
 out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({'status':result['status'],'records':len(checks),'maxmean':maxmean,'maxprob':maxprob,'resources':result['resources']}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--chart',type=Path,required=True);p.add_argument('--wave',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.base,a.chart,a.wave,a.out)
