"""Independent source-prefix/feature/training/law replay; no fitting or acquisition."""
import bisect,csv,gzip,hashlib,json,math,pickle,resource,sys,time
from collections import Counter,defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];HERE=ROOT/'reports/continuation-20261030c'
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT))
from review_paths import companion_root,source_root
from check_season_scores_independent import load_truth,sha,close,TARGETS,COUNTS,ACTION_COUNTS,ACTION_YARDS,num,count
sys.path.insert(0,str(ROOT/'reports/continuation-20261030'))
from check_retained_distribution_math import summaries
CHART='nick-chart-ppr-v1';POSITIONS=('QB','RB','WR','TE')
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def unzip(p):return json.loads(gzip.decompress(p.read_bytes()))
def epoch(t):return datetime.fromisoformat(t.replace('Z','+00:00')).timestamp()
def compare(a,b,c):
 if isinstance(b,dict):
  for k,v in b.items():assert k in a;compare(a[k],v,c)
 elif isinstance(b,(list,tuple)):
  assert len(a)==len(b)
  for x,y in zip(a,b):compare(x,y,c)
 elif isinstance(b,(int,float))and not isinstance(b,bool):close(a,b);c['independent_numeric_fields']+=1
 else:assert a==b,(a,b)

class Prefixes:
 def __init__(self,rows):
  self.rows=rows;self.players=defaultdict(list);self.observed=defaultdict(list);self.league=defaultdict(list)
  for r in rows:self.players[r['player_id']].append(r)
  for rs in self.players.values():rs.sort(key=lambda r:(r['available'],r['kickoff'],r['game_id']))
  self.times={p:[r['available']for r in rs]for p,rs in self.players.items()}
  groups=defaultdict(list)
  for r in rows:groups[r['game_id'],r['defense'],r['position']].append(r)
  for (_,defense,position),rs in groups.items():
   for target in TARGETS:
    vals=[r['values'][target]/50 if target==CHART and r['values'][target]is not None else r['values'][target]for r in rs]
    ns=[]
    for r in rs:
     key='attempts'if target in('pass_yd','pass_td','pass_cmp','pass_int')else'carries'if target=='rush_yd'else'targets'if target in('rec','rec_yd')else None
     n=r['workload'][key]if key else (None if any(r['workload'][k]is None for k in('carries','targets'))else r['workload']['carries']+r['workload']['targets'])if target=='rush_rec_yd'else 1. if r['played']else None
     ns.append(n)
    complete=all(y is not None for y in vals);compatible=complete and all(n is not None and(n>0 or y==0)for n,y in zip(ns,vals))
    g=dict(game_id=rs[0]['game_id'],season=rs[0]['season'],kickoff=rs[0]['kickoff'],available=rs[0]['available'],rows=len(rs),known=sum(v is not None for v in vals),total=math.fsum(vals)if complete else None,n=math.fsum(ns)if compatible else None,y=math.fsum(vals)if compatible else None)
    self.observed[defense,position,target].append(g);self.league[position,target].append(g)
  for mapping in(self.observed,self.league):
   for gs in mapping.values():gs.sort(key=lambda g:(g['available'],g['kickoff'],g['game_id']))
  self.otimes={k:[g['available']for g in gs]for k,gs in self.observed.items()}
  self.league_cache={}
 @lru_cache(maxsize=None)
 def own(self,pid,position,target,cutoff,floor):
  rs=self.players.get(pid,[]);end=bisect.bisect_left(self.times.get(pid,[]),cutoff);rs=[r for r in rs[:end]if r['season']>=floor][-8:];out=[]
  for n in(3,8):
   v=[r['values'][target]for r in rs[-n:]if r['values'][target]is not None];out.extend((sum(v)/len(v)if v else None,float(len(v))))
  for lag in range(1,5):
   r=rs[-lag]if len(rs)>=lag else None;v=r['values'][target]if r else None;out.extend((v,(cutoff-r['kickoff'])/86400 if r else None,float(v is None)))
  out.extend(float(position==p)for p in POSITIONS)
  return out,max((r['available']for r in rs),default=None)
 @lru_cache(maxsize=None)
 def defense(self,defense,position,target,cutoff,floor):
  key=defense,position,target;gs=self.observed.get(key,[]);end=bisect.bisect_left(self.otimes.get(key,[]),cutoff);local=[g for g in gs[:end]if g['season']>=floor][-4:];lk=position,target,floor
  if lk not in self.league_cache:
   gs=[g for g in self.league[position,target]if g['season']>=floor];ns=[0.];ys=[0.];counts=[0]
   for g in gs:ns.append(ns[-1]+(g['n']if g['n']is not None else 0.));ys.append(ys[-1]+(g['y']if g['y']is not None else 0.));counts.append(counts[-1]+int(g['n']is not None))
   self.league_cache[lk]=gs,[g['available']for g in gs],ns,ys,counts
  gs,times,ns,ys,counts=self.league_cache[lk];end=bisect.bisect_left(times,cutoff);ln,ly=ns[end],ys[end];r0=ly/ln if ln else None;rates=[g for g in local if g['n']is not None];n=math.fsum(g['n']for g in rates);y=math.fsum(g['y']for g in rates);shrunk=(20*r0+y)/(20+n)if r0 is not None else None;totals=[g['total']for g in local if g['total']is not None]
  values=[math.fsum(totals)/len(totals)if totals else None,len(totals),sum(g['rows']for g in local),sum(g['known']for g in local),shrunk,shrunk-r0 if shrunk is not None else None,n,len(rates),(cutoff-max(g['kickoff']for g in local))/86400 if local else None]
  audit=dict(latest_local_available=max((g['available']for g in local),default=None),latest_league_available=times[end-1]if end else None,local_game_ids=[g['game_id']for g in local],local_game_slots=len(local),league_rate_games=counts[end],league_opportunities=ln,league_rate=r0,feature_floor=floor,kappa=20.)
  return values,audit

def attach(rows,source):
 lookup={(r['game_id'],r['player_id']):r for r in rows}
 for year in range(2022,max(r['season']for r in rows)+1):
  with(source/f'stats_player_week_{year}.csv').open()as f:
   for raw in csv.DictReader(f):
    if raw['season_type']!='REG'or(year==2026 and int(raw['week'])>7):continue
    r=lookup.get((raw['game_id'],raw['player_id']))
    if r is None:continue
    r['played']=any(count(num(raw[k]))and num(raw[k])>0 for k in ACTION_COUNTS)or any(num(raw[k])not in(None,0)for k in ACTION_YARDS);r['team']=raw['team'];r['defense']=raw['opponent_team'];r['workload']={k:num(raw[k])if r['played']else None for k in('attempts','carries','targets')}
 return rows
def prior(values,target):
 out=dict(kind='zero',mean=None,center=0,q=0.,p=.5)
 if target=='anytime_td':out.update(kind='bernoulli',p=(sum(values)+1)/(len(values)+2)if values else .5)
 elif values:
  if target in COUNTS:
   mu=max(.05,sum(values)/len(values));out.update(kind='geometric',q=mu/(1+mu))
  else:
   center=sorted(values)[(len(values)-1)//2];scale=max(50. if target==CHART else 1.,sum(abs(y-center)for y in values)/len(values));out.update(kind='signed',center=int(center),q=scale/(1+scale))
 return out

def verify(source,private):
 start,cpu=time.monotonic(),time.process_time();pub=HERE/'qualified-defense-information-v1';p=json.loads((pub/'FROZEN_PROTOCOL.json').read_text());rows,lookup,games=load_truth(source,p,2026);attach(rows,source);prefix=Prefixes(rows);c=Counter();maximum=0.;sample_slots=set();training_cache={};modelcount=0;lawcount=0
 for name,digest in p['helpers'].items():assert sha(ROOT/'nfl_v2'/name)==digest;c['frozen_helper_hashes']+=1
 assert sha(ROOT/'nfl_v2/distribution_laws.py')==p['law_code_sha256']
 def training(target,policy,origin,floor):
  key=target,policy,origin,floor
  if key in training_cache:return training_cache[key]
  fitfloor=p['policies'][policy]['fit_floor'];roles=set(POSITIONS)if target==CHART else set(p['source_role_contract']['primary'][target])|set(p['source_role_contract']['extended'].get(target,[]));train=[r for r in rows if r['position']in roles and r['season']>=fitfloor and r['available']<origin and r['values'][target]is not None];values=[r['values'][target]for r in train];globalprior=prior(values,target);priors={pos:prior([r['values'][target]for r in train if r['position']==pos],target)if any(r['position']==pos for r in train)else globalprior for pos in POSITIONS};member=hashlib.sha256(canonical([(r['game_id'],r['player_id'])for r in train])).hexdigest();ownmax=None;maxima={g:None for g in('D1','D2')}
  for r in train:
   _,own=prefix.own(r['player_id'],r['position'],target,r['kickoff'],floor);_,audit=prefix.defense(r['defense'],r['position'],target,r['kickoff'],floor)
   for g in maxima:
    consumed=[own,audit['latest_local_available']]+([audit['latest_league_available']]if g=='D2'else[]);v=max((x for x in consumed if x is not None),default=None)
    if v is not None:assert v<r['kickoff'];maxima[g]=max(v,maxima[g]if maxima[g]is not None else v)
   c['independent_training_row_prefix_checks']+=1
  result=dict(training_n=len(train),training_membership_sha256=member,latest_training_label_available=max((r['available']for r in train),default=None),prior_parameters=priors,prior_position_sample_counts={pos:sum(r['position']==pos for r in train)for pos in POSITIONS});training_cache[key]=(result,maxima);return result,maxima
 from threadpoolctl import threadpool_limits
 with threadpool_limits(limits=2):
  for ff in sorted(pub.glob('*-FIT.json')):
   fit=json.loads(ff.read_text());future=ff.name.startswith('FUTURE-');origin=epoch(fit.get('fit_cutoff_utc',fit.get('training_label_fit_cutoff_utc')));floor=fit['feature_floor'];target=fit['target'];group=fit['information_group'];policy=fit['policy_id'];expected,maxima=training(target,policy,origin,floor);compare(fit,expected,c);close(fit['latest_training_consumed_feature_available'],maxima[group]);c['exact_fit_membership_prior_and_chronology_receipts']+=1
   fd=fit['query_features'];fp=private/fd['bundle_name'];assert sha(fp)==fd['sha256'];entries=unzip(fp);c['query_feature_packet_hashes']+=1
   for e in entries:
    q=e['query'];blocked=q.get('blocked_reason')or q['position']not in POSITIONS
    if blocked:
     assert future and e['defense_audit']['state']=='BLOCKED_QUERY_NO_CONTEXT_LOOKUP';assert all(x is None for x in e['D2_features']);c['blocked_queries_kept_without_context_lookup']+=1;continue
    own,ownmax=prefix.own(q['player_id'],q['position'],target,q['cutoff'],floor);extra,audit=prefix.defense(q['defense'],q['position'],target,q['cutoff'],floor);compare(e['defense_audit'],audit,c);compare(e['own_features']if future else e['features'][:20],own,c);compare(e['D1_features']if future else e['features'],own+extra[:4]if future or group=='D1'else own+extra,c)
    if future:compare(e['D2_features'],own+extra,c)
    else:
     consumed=[ownmax,audit['latest_local_available']]+([audit['latest_league_available']]if group=='D2'else[]);close(e['latest_consumed_feature_available'],max((x for x in consumed if x is not None),default=None))
    c['full_query_prefixes']+=1
   model=None
   if fit['model']:
    md=fit['model'];mp=private/md['bundle_name'];assert sha(mp)==md['sha256'];c['retained_model_hashes']+=1
    # Hash is checked against the frozen self-produced receipt BEFORE decoding.
    model=pickle.loads(gzip.decompress(mp.read_bytes()));assert model.estimator.n_estimators==32 and model.estimator.max_depth==8 and model.estimator.min_samples_leaf==30 and model.estimator.random_state==1701;c['retained_model_parameter_contracts']+=1
   familykey=future,target,policy,group,'learned'if model is not None else'fallback'
   if familykey in sample_slots:continue
   usable=[e for e in entries if not e['query'].get('blocked_reason')and e['query']['position']in POSITIONS];usable=[e for e in usable if(e['own_features']if future else e['features'])[3]>0]or usable
   if not usable:continue
   sample_slots.add(familykey);e=usable[0];q=e['query'];features=e[group+'_features']if future else e['features'];pri=expected['prior_parameters'][q['position']]
   if model is None or features[3]<=0:law=pri
   else:
    x=np.asarray([[math.nan if v is None else v for v in features]]);raw=np.column_stack((np.where(np.isfinite(x),x,model.design.median),~np.isfinite(x))).astype(float);leaves=model.estimator.apply(raw)[0];weights=np.zeros(len(model.support))
    for j,h in enumerate(model.hist):weights+=h[leaves[j]].toarray().ravel()/32
    weights/=weights.sum();law=dict(kind='mixture',support=model.support,weights=weights,prior=pri)
   if future:
    # Allfuture outcomes stay unread; only lawforecastmoments are checked.
    continue
   forecast=json.loads((pub/(fit['slot']+'-FORECAST.json')).read_text());packet=forecast['packet'];path=private/packet['bundle_name'];assert sha(path)==packet['sha256'];records=unzip(path)['rows'];r=next(r for r in records if all(r[k]==q[k]for k in('game_id','player_id','target','population')));want=summaries(law,q['actual_grid']if target==CHART else q['actual']);saved=dict(r['distribution_summary'])
   if target==CHART:
    assert saved['grid_denominator']==50
    for k in('mean','lower_median','q05','q95','interval90_width','crps'):
     if saved[k]is not None:saved[k]*=50
   for k,v in want.items():
    if k in('lower_median','q05','q95'):close(saved[k],v)
    elif isinstance(v,(bool,type(None))):assert saved[k]==v
    else:
     delta=abs(saved[k]-v);maximum=max(maximum,delta);assert math.isclose(saved[k],v,rel_tol=2e-9,abs_tol=3e-7),(ff.name,k,saved[k],v)
    c['independent_PMF_moment_quantile_logmass_CRPS_fields']+=1
   lawcount+=1
 return dict(state='PASS_SOURCE_PREFIX_TRAINING_MEMBERSHIP_MODEL_HASH_AND_SAMPLED_PMF_REPLAY',protocol_sha256=sha(pub/'FROZEN_PROTOCOL.json'),checks=dict(c),sampled_historical_laws=lawcount,max_law_float_difference=maximum,window_contract='LastfourOBSERVEDqualified-positiongroups. Wholeabsentpositions notpadded; separately disclosed77historicalquerywindows. Thischeckreplaysactualcodecontract, doesnotauthenticatecalendar-padding wording.',resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
if __name__=='__main__':
 result=verify(source_root(),companion_root()/'qualified-defense-information-v1');(HERE/'DEFENSE_FEATURE_MODEL_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
