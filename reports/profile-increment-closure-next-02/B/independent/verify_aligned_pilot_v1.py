"""Independent E3/profile equations, origin prior, and typed-tree inference."""
import bisect,gzip,hashlib,importlib.util,json,math
from collections import defaultdict
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;BASE=OUT.parent;WAVE=BASE/'aligned-wave-v1'
def read(p):
 p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
data=read(BASE/'source-policy/ALIGNED_48H_DERIVATIVES_V1.json.gz');full=data['QB_inputs'];rows=sorted([r for r in full if r['physical_participation']and r['target_parity']],key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
times=[r['available']for r in rows];aa=np.vstack([np.zeros(25),np.cumsum([r['context_attempts']for r in rows],axis=0)]);cc=np.vstack([np.zeros(25),np.cumsum([r['context_completions']for r in rows],axis=0)])
players=defaultdict(list)
for r in rows:players[r['player_id']].append(r)
cache={}
def counts(rr,name):return np.sum([r[name]for r in rr],axis=0,dtype=float)if rr else np.zeros(25)
def own(q):return[r for r in players[q['player_id']]if r['available']<q['kickoff']][-8:]
def expected_context(r):
 key=r['game_id'],r['player_id']
 if key not in cache:
  i=bisect.bisect_left(times,r['kickoff']);past=own(r);pooled=(cc[i]+1)/(aa[i]+2);rate=(counts(past,'context_completions')+20*pooled)/(counts(past,'context_attempts')+20);cache[key]=np.asarray(r['context_attempts'])*rate
 return cache[key]
def e3(q):
 cutoff=q['kickoff'];i=bisect.bisect_left(times,cutoff);a,c=aa[i],cc[i];history=own(q);oa,oc=counts(history,'context_attempts'),counts(history,'context_completions');pooled=(c+1)/(a+2)
 mix=(oa+20*(a+1)/(a.sum()+25))/(oa.sum()+20);rates=(oc+20*pooled)/(oa+20)
 base=[]
 for window in(3,8):
  values=[r['official_completions']for r in history[-window:]];base.extend([sum(values)/len(values)if values else math.nan,float(len(values))])
 for lag in range(1,5):
  r=history[-lag]if len(history)>=lag else None;base.extend([r['official_completions']if r else math.nan,(cutoff-r['kickoff'])/86400 if r else math.nan,float(r is None)])
 base.extend([1.,0.,0.,0.]);base+=mix.tolist()+rates.tolist()+np.log1p(oa).tolist();base+=[len(history),oa.sum(),(cutoff-history[-1]['kickoff'])/86400 if history else math.nan]
 for field in('ydstogo','yardline_100','game_seconds_remaining','score_differential'):
  cases=[r['field_context'][field]for r in history if r['field_context'][field]['mean']is not None];n=sum(r['n']for r in cases);base.append(sum(r['mean']*r['n']for r in cases)/n if n else math.nan)
 defense=[r for r in rows if r['opponent']==q['opponent']and r['available']<cutoff];games=sorted({(r['kickoff'],r['game_id'])for r in defense})[-16:];ids={g for t,g in games};defense=[r for r in defense if r['game_id']in ids]
 da,dc=counts(defense,'context_attempts'),counts(defense,'context_completions');exp=np.sum([expected_context(r)for r in defense],axis=0)if defense else np.zeros(25);res=(dc-exp)/(da+100.)
 base+=res.tolist()+np.log1p(da).tolist()+[float((dc.sum()-exp.sum())/(da.sum()+100)),len(games)]+(mix*res).tolist()
 return base
defs={'dropback_per_opportunity':('dropbacks','dropback_known_opportunities'),'attempt_per_dropback':('attempts_on_dropbacks','dropbacks'),'sack_per_dropback':('sacks','sack_known_dropbacks'),'scramble_per_dropback':('scrambles','scramble_known_dropbacks'),'spike_per_attempt':('spikes','spike_known_attempts'),'QB_dropback_share':('dropbacks','attributed_team_dropbacks'),'QB_attempt_share':('credited_attempts','attributed_team_attempts')}
def extras(q,names):
 cutoff=q['kickoff'];summaries={}
 for group in('own','offense','defense'):
  source=data['QB_games']if group=='own'else data['team_games'];prior=[r for r in source if r['available']<cutoff]
  history=[r for r in prior if r['player_id']==q['player_id']]if group=='own'else[r for r in prior if r['team'if group=='offense'else'opponent']==q['team'if group=='offense'else'opponent']]
  history=sorted(history,key=lambda r:(r['kickoff'],r['game_id']))[-(8 if group=='own'else 16):]
  c={k:sum(r['counts'][k]for r in history)for k in source[0]['counts']};p={k:sum(r['counts'][k]for r in prior)for k in c};summaries[group]=history,prior,c,p
 result=[]
 for label in names:
  if label.endswith(':MISSING'):continue
  block,name=label.split(':',1);group,field=name.split('_',1);history,prior,c,p=summaries[group]
  if block=='R1_support':v=math.log1p(c[field])
  elif field.endswith('_per_game'):
   count=field[:-9];mu=p[count]/len(prior)if prior else None;v=(c[count]+4*mu)/(len(history)+4)if mu is not None else None
  elif field.endswith('_dropback_mix'):
   context,j=field[:-13].rsplit('_',1);num=sum(r['cells'][context][int(j)]['dropbacks']for r in history);v=num/c['dropbacks']if c['dropbacks']else None
  else:
   num,den=defs[field];rate=p[num]/p[den]if p[den]else None;v=(c[num]+100*rate)/(c[den]+100)if rate is not None else None
  missing=v is None or not math.isfinite(v);result.extend([0. if missing else v,float(missing)])
 return result
spec=importlib.util.spec_from_file_location('manual_tree',ROOT/'reports/profile-increment-to-release-01/B/independent/verify_pilot_inference_v1.py');manual=importlib.util.module_from_spec(spec);spec.loader.exec_module(manual)
payload=read(WAVE/'predictions/2025-W01.json.gz');orders=read(WAVE/'FEATURE_ORDER_V1.json')['orders'];cutoff=payload['fit_cutoff'];train=[r for r in rows if r['season']>=2024 and r['available']<cutoff];mu=max(.05,sum(r['official_completions']for r in train)/len(train));priorq=mu/(1+mu)
query={(r['game_id'],r['player_id']):r for r in full};models={arm:read(WAVE/'fits'/('2025-W01-'+arm+'.json.gz'))for arm in('F2','F3')};max_feature=max_mean=max_mass=0.;n=0;feature_n=0
for arm,rec in models.items():
 assert rec['training_rows']==len(train)and rec['latest_training_label']==max(r['available']for r in train)
 assert rec['training_membership_sha256']==hashlib.sha256(json.dumps([(r['game_id'],r['player_id'])for r in train]).encode()).hexdigest()
 assert rec['model']['forest_config']==dict(n_estimators=32,criterion='squared_error',max_depth=8,min_samples_leaf=30,max_features=1.,bootstrap=False,random_state=1701,n_jobs=2)
for r in payload['rows']:
 if r['method']not in models:continue
 q=query[r['game_id'],r['player_id']];expected=e3(q)
 if r['method']=='F3':expected+=extras(q,orders['F3'][len(orders['F2']):])
 assert len(expected)==len(r['features'])==len(orders[r['method']])
 for a,b in zip(expected,r['features']):
  if not math.isfinite(a):assert b is None
  else:assert b is not None;d=abs(a-b);max_feature=max(max_feature,d);assert d<1e-10
  feature_n+=1
 mean,median,w,cdf=manual.manual_law(models[r['method']]['model'],expected,priorq)
 max_mean=max(max_mean,abs(mean-r['mean']));max_mass=max(max_mass,float(np.max(np.abs(w-np.asarray(r['law']['weights'])))))
 assert abs(mean-r['mean'])<1e-10 and median==r['lower_median']and abs(priorq-r['law']['prior']['q'])<1e-14;n+=1
receipt=dict(id='B-ALIGNED-PILOT-INDEPENDENT-FEATURE-TREE-v1',status='PASS_IN_CHECKED_SCOPE',origin=[2025,1],model_hashes={a:sha(WAVE/'fits'/('2025-W01-'+a+'.json.gz'))for a in models},prediction_sha256=sha(WAVE/'predictions/2025-W01.json.gz'),training_rows=len(train),forecasts_checked=n,feature_scalar_checks=feature_n,max_feature_difference=max_feature,max_mean_difference=max_mean,max_mass_difference=max_mass,new_fits=0,independence='Manual E3 equations including earlier-origin offense expectations/opponent residuals, independent profile denominator/shrinkage equations and origin prior; separately reused independenttypedtree traversal. Author feature/restoration/scorer not called.',limits=['Representative firstorigin only; no independent newfreshfitclaimed.','Aligned48h iscurrent-vintage sensitivity, notauthenticatedsourcehistory ornewNFLaccuracyobservation.'])
dest=OUT/'ALIGNED_PILOT_INDEPENDENT_REVIEW_V1.json';assert not dest.exists();dest.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
