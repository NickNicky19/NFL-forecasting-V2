"""Independent arithmetic and safe JSON-tree inference; no author scorer imports.

Private offers are read owner-locally and never written to the public receipt.
The decimal calculation establishes meaning; IEEE arithmetic reproduces bindings.
"""
import argparse,collections,datetime,decimal,gzip,hashlib,json,math,platform
from pathlib import Path
import numpy as np
D=decimal.Decimal;decimal.getcontext().prec=50

def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b)if str(p).endswith('.gz')else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def key(r):return r['game_id'],r['player_id'],r['target']
def dec(x):return D(str(x))
def same(a,b,tol=2e-11):
 if a is None or b is None:assert a is b,(a,b)
 else:assert abs(float(a)-float(b))<=tol,(a,b)
def side(point,line):
 if point is None:return None
 a,b=dec(point),dec(line);return 'over'if a>b else'under'if a<b else None
def state(actual,line,sd):
 if sd is None:return'ABSTAIN'
 if actual is None:return'UNKNOWN_PARTICIPATION'
 a,b=dec(actual),dec(line)
 return'PUSH'if a==b else'WIN'if(a>b)==(sd=='over')else'LOSS'

def decimal_law(r):
 p=r['law'];assert p['kind']=='leaf_mixture' and p['prior']['kind']=='geometric'
 support=list(map(dec,p['support']));w=list(map(dec,p['weights']));total=sum(w);w=[z/total for z in w];mix=dec(p['mixture']);q=dec(p['prior']['q'])
 assert all(z>=0 for z in w)and 0<=q<1 and all(a<b for a,b in zip(support,support[1:]))
 def cdf(x):
  n=math.floor(x);prior=D(0)if n<0 else D(1)-q**(n+1)
  return(D(1)-mix)*sum(z for y,z in zip(support,w)if y<=n)+mix*prior
 mu=(D(1)-mix)*sum(y*z for y,z in zip(support,w))+mix*q/(1-q)
 median=0
 while cdf(median)<D('.5'):median+=1;assert median<10000
 return cdf,mu,median

def float_probs(r,line):
 p=r['law'];a=np.array(p['support'],float);w=np.array(p['weights'],float);w=w/float(w.sum());q=float(p['prior']['q']);b=float(p['mixture'])
 def cdf(n):return(1-b)*float(w[a<=n].sum())+b*(0. if n<0 else 1-q**(n+1))
 k=math.floor(float(line));below=cdf(k-1)if float(line)==k else cdf(k);at=cdf(k)
 return dict(over=1-at,under=below,push=at-below)
def probability(rows):
 good=[r for r in rows if r['actual']is not None and r['probs']is not None]
 if not good:return dict(n=0,brier=None,log_loss=None,infinite_log_losses=0)
 losses=[];logs=[]
 for r in good:
  a,b=dec(r['actual']),dec(r['line']);event='over'if a>b else'under'if a<b else'push';p={k:dec(v)for k,v in r['probs'].items()}
  losses.append(sum((p[k]-int(k==event))**2 for k in('over','under','push'))/2);logs.append(-math.log(float(p[event]))if p[event]>0 else math.inf)
 return dict(n=len(good),brier=float(sum(losses)/len(losses)),log_loss=None if any(not math.isfinite(x)for x in logs)else math.fsum(logs)/len(logs),infinite_log_losses=sum(not math.isfinite(x)for x in logs))

def safe_forest(payload,features):
 assert payload['kind']=='typed_ordered_leaf_cdf'and len(payload['trees'])==32
 med=payload['design']['median'];assert len(med)==len(features)
 missing=[x is None or not math.isfinite(float(x))for x in features]
 design=np.array([m if absent else x for x,m,absent in zip(features,med,missing)]+[float(x)for x in missing],dtype=np.float32)
 mass=[0.]*len(payload['support']);leaves=[]
 for tree in payload['trees']:
  node=0;depth=0
  while tree['left'][node]!=-1:
   i=tree['feature'][node];assert 0<=i<len(design)
   node=tree['left'][node]if float(design[i])<=tree['threshold'][node]else tree['right'][node];depth+=1;assert depth<=8
  leaves.append(node);h=tree['leaf_histogram']
  for ri,ci,value in zip(h['rows'],h['columns'],h['values']):
   if ri==node:mass[ci]+=value/len(payload['trees'])
 total=math.fsum(mass);assert abs(total-1)<1e-10
 return[m/total for m in mass],leaves

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--wave',type=Path,required=True);ap.add_argument('--scores',type=Path,required=True);ap.add_argument('--offers-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 rows=[r for p in sorted((a.wave/'predictions').glob('*.json.gz'))for r in read(p)['rows']];assert len(rows)==831
 sources=[];offers=[]
 for w in range(5,9):
  p=a.offers_root/f'RESTORED_W{w}_QB_OFFERS.json.gz';sources.append(dict(week=w,SHA256=sha(p)));offers += [r for r in read(p)['rows']if r['target']=='pass_cmp']
 assert len(offers)==112 and len({key(r)for r in offers})==112
 controls=[r for p in sorted((a.repo_root/'reports/player-context-matchup-01/B/qb-wave-v1/predictions').glob('2026-*.json.gz'))for r in read(p)['rows']if r['method']=='E3']
 indexed={(r['method'],key(r)):r for r in rows+controls}
 tables=read(a.scores/'COMMON_CONTROL_TABLE.json');nums=read(a.scores/'NUMERICAL_TABLE.json');pairs=read(a.scores/'PAIRED_COMPARISONS.json');commitments=read(a.scores/'OWNER_LOCAL_COMMITMENTS.json')
 with gzip.open(a.repo_root/'reports/player-context-matchup-01/B/source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz','rt')as f:inputs=json.load(f)
 qmap={(q['game_id'],q['player_id']):q for q in inputs};eligible=[q for q in inputs if q.get('physical_participation')and q['target_parity']]
 full_law_checks=0;probability_checks=0;grades={};summaries=[];commitment_checks=[]
 for r in rows:
  cdf,mu,median=decimal_law(r);same(mu,r['mean']);assert median==r['lower_median'];assert cdf(-1)==0 and abs(float(cdf(100000))-1)<1e-12;full_law_checks+=1
 methods=['S0','S1','S2','E3','SAVED_ADJUSTED','SAVED_RAW','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE','NEUTRAL_HALFPOINT']
 for method in methods:
  policies=['P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','P90']if method in('S0','S1','S2','E3')else['REGISTERED_DIRECTION']
  for policy in policies:
   gg=[]
   for offer in offers:
    r=dict(offer);p=indexed.get((method,key(r)));probs=None;sd=None
    if p:
     assert p['actual']==r['actual'];cdf,mu,median=decimal_law(p);fp=float_probs(p,r['line']);line=dec(r['line']);under=cdf(math.ceil(line)-1);over=D(1)-cdf(math.floor(line));push=D(1)-over-under
     for name,v in zip(('over','under','push'),(over,under,push)):same(v,fp[name],2e-12)
     assert min(fp.values())>=-1e-12 and abs(sum(fp.values())-1)<1e-12;probability_checks+=1;probs=fp
     point=p['mean'if policy=='P1_MEAN'else'lower_median']
     sd=side(point,r['line'])if policy.startswith('P1_')else'over'if over>under else'under'if under>over else None
     if policy=='P90'and(sd is None or dec(probs[sd])<D('.9')):sd=None
    elif method in('SAVED_ADJUSTED','SAVED_RAW'):sd=side(r.get('prediction'if method=='SAVED_ADJUSTED'else'raw_prediction'),r['line'])
    elif method in('ALWAYS_OVER','ALWAYS_UNDER'):sd='over'if method=='ALWAYS_OVER'else'under'
    elif method=='NEUTRAL_HALFPOINT':probs=dict(over=.5,under=.5,push=0.)if dec(r['line'])%1==D('.5')else None
    else:
     q=qmap[r['game_id'],r['player_id']];ys=[x['official_completions']for x in eligible if x['season']>=2025 and x['available']<q['kickoff']];whole=dec(r['line'])%1==0;den=len(ys)+(3 if whole else 2)
     probs=dict(over=(sum(dec(y)>dec(r['line'])for y in ys)+1)/den,under=(sum(dec(y)<dec(r['line'])for y in ys)+1)/den,push=(sum(dec(y)==dec(r['line'])for y in ys)+1)/den if whole else 0.);sd='over'if probs['over']>probs['under']else'under'if probs['under']>probs['over']else None
    r.update(selected_side=sd,statistical_state=state(r['actual'],r['line'],sd),probs=probs);gg.append(r)
   grades[method,policy]=gg
   # IEEE binding uses independent arithmetic over the same committed schema.
   checked=[{k:r.get(k)for k in('game_id','player_id','target','line','selected_side','actual','statistical_state','probs')}for r in gg];h=digest(checked);old=next(c for c in commitments if(c['method'],c['policy'])==(method,policy));commitment_checks.append(dict(method=method,policy=policy,match=h==old['calculations_sha256'],computed_SHA256=h,expected_SHA256=old['calculations_sha256']))
   assert h==old['calculations_sha256'],('commitment',method,policy,h,old['calculations_sha256'])
   for window in['ALL',5,6,7,8]:
    sub=[r for r in gg if window=='ALL'or r['week']==window];reported=next(t for t in tables if(t['method'],t['policy'],t['window'])==(method,policy,window));computed={}
    for ss in('over','under','Combined'):
     selected=[r for r in sub if r['selected_side']and(ss=='Combined'or r['selected_side']==ss)];counts=collections.Counter(r['statistical_state']for r in selected);rep=next(s['metrics']for s in reported['sides']if s['side']==ss)
     for state_key in('WIN','LOSS','PUSH'):assert rep[state_key]==counts[state_key]
     n=counts['WIN']+counts['LOSS'];assert rep['denominators']['decided']==n;same(rep['hit_rate'],counts['WIN']/n if n else None)
     assert rep['selection_pool_count']==len(sub);same(rep['selection_coverage'],len(selected)/len(sub))
     assert rep['admitted_rule_abstentions']==sum(r['selected_side']is None for r in sub)
     ps=probability(selected)
     for k in('n','brier','log_loss','infinite_log_losses'):same(ps[k],rep['probability_scores'][k])
     computed[ss]=dict(wins=counts['WIN'],losses=counts['LOSS'],decided=n,selected=len(selected),rate=counts['WIN']/n if n else None)
    ps=probability(sub)
    for k in('n','brier','log_loss','infinite_log_losses'):same(ps[k],reported['probability'][k])
    if method in('S0','S1','S2')and(window=='ALL'or policy=='P2_STATISTICAL_LAW'):summaries.append(dict(method=method,policy=policy,window=window,sides=computed,probability=ps))
 # Independent numerical checks cover all full-system windows, not rescore old fit.
 numchecks=0
 for v in nums:
  if v['fallback_view']!='FULL_SYSTEM':continue
  method=v['procedure_id'].rsplit(':',1)[-1];rr=[r for r in rows if r['method']==method];window=v['week']
  if isinstance(window,int):rr=[r for r in rr if r['week']==window]
  elif window=='W1_4':rr=[r for r in rr if r['week']<=4]
  elif window=='W5_8':rr=[r for r in rr if r['week']>=5]
  elif window=='MATCHED_OFFERS_W5_W8':rr=[r for r in rr if any(key(r)==key(o)for o in offers)]
  elif window!='ALL':raise ValueError(window)
  errors=[dec(r[v['product_id']])-dec(r['actual'])for r in rr if r['actual']is not None and r[v['product_id']]is not None];assert v['n']==len(errors)
  same(sum(abs(e)for e in errors)/len(errors),v['mae']);same(sum(e*e for e in errors)/len(errors),v['mse']);same(sum(errors)/len(errors),v['bias']);numchecks+=1
 pairchecks=0
 for p in pairs:
  if p['kind']!='OFFER_DIRECTION_PAIRED_LOSS':continue
  policy=p['policy'];control_policy=policy if(p['control'],policy)in grades else'REGISTERED_DIRECTION';g=grades[p['candidate'],policy];c=grades[p['control'],control_policy];matches=[(r,b)for r,b in zip(g,c)if(p['window']=='ALL'or r['week']==p['window'])and r['statistical_state']in('WIN','LOSS')and b['statistical_state']in('WIN','LOSS')]
  cw=sum(r['statistical_state']=='WIN'for r,b in matches);bw=sum(b['statistical_state']=='WIN'for r,b in matches);assert(p['candidate_wins'],p['control_wins'],p['n'])==(cw,bw,len(matches));same(p['delta'],(bw-cw)/len(matches))
  assert p['candidate_only_wins']==sum(r['statistical_state']=='WIN'and b['statistical_state']=='LOSS'for r,b in matches);assert p['control_only_wins']==sum(r['statistical_state']=='LOSS'and b['statistical_state']=='WIN'for r,b in matches);pairchecks+=1
 # Deterministic first W1 query per arm, selected without regard to gain.
 forest=[]
 for arm in('S0','S1','S2'):
  r=next(z for z in rows if z['week']==1 and z['method']==arm);fp=(a.repo_root/'reports/profile-increment-to-release-01/B/opportunity-wave-v1/fits/2026-W01-R3.json.gz')if arm=='S0'else a.wave/'fits'/f'2026-W01-{arm}.json.gz';fit=read(fp);model=fit['model'];weights,leaves=safe_forest(model,r['features']);same(max(abs(x-y)for x,y in zip(weights,r['law']['weights'])),0,1e-12)
  ys=[q['official_completions']for q in eligible if q['season']>=2025 and q['available']<fit['fit_cutoff']];mu=max(.05,math.fsum(ys)/len(ys));q=mu/(1+mu);same(q,r['law']['prior']['q'],1e-15)
  restored=dict(r,law=dict(r['law'],weights=weights,support=model['support']));cdf,mean,median=decimal_law(restored);same(mean,r['mean']);assert median==r['lower_median'];forest.append(dict(arm=arm,model_SHA256=sha(fp),feature_count=len(r['features']),trees=len(leaves),training_prior_rows=len(ys),query_identity_commitment=digest([r['game_id'],r['player_id']]),mean_error=abs(float(mean)-r['mean']),median_match=True,complete_leaf_mass_match=True))
 assert next(t for t in summaries if(t['method'],t['policy'],t['window'])==('S0','P2_STATISTICAL_LAW','ALL'))['sides']['Combined']['wins']==59
 receipt=dict(id='B_NEXTGEN_INDEPENDENT_OUTPUT_ARITHMETIC_v1',checked_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),verdict='PASS_CHECKED_SCOPE',code_SHA256=sha(__file__),environment=dict(python=platform.python_version(),numpy=np.__version__,decimal_precision=decimal.getcontext().prec),input_bindings=dict(wave_protocol=sha(a.wave/'FROZEN_PROTOCOL.json'),score_protocol=sha(a.scores/'FROZEN_SCORING_PROTOCOL.json'),source_files=sources,score_files=[dict(path=p.name,SHA256=sha(p))for p in(a.scores/'COMMON_CONTROL_TABLE.json',a.scores/'NUMERICAL_TABLE.json',a.scores/'PAIRED_COMPARISONS.json',a.scores/'OWNER_LOCAL_COMMITMENTS.json')]),checked=dict(independent_decimal_law_means_medians=full_law_checks,offered_rows=112,method_policy_variants=len(grades),float_probability_vectors_checked_against_decimal=probability_checks,aggregate_weekly_method_policy_tables=len(tables),full_system_numerical_views=numchecks,paired_side_disagreement_views=pairchecks,exact_reproduced_commitments=len(commitment_checks)),commitments=commitment_checks,representative_safe_forest=forest,new_arm_results=summaries,scope_limits=['No new fits or independent refit verification','Only deterministic W1 savedmodel inference perarm, not allorigin restoration','No privatepeer-row parity or originalquote/sourceHTTPvintage authentication','No uncertaintybootstrap reimplementation','Numerical MAE/MSE/bias checked; not everytail/reliability/AUC figure independently reconstructed','No probability/injury/confirmedstarter/productionpromotion inferred from this arithmetic'],new_fits=0,new_NFL_games=0,new_scores_added=0,private_rows_republished=False)
 a.out.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(verdict=receipt['verdict'],checked=receipt['checked'],forests=forest,all_results=[r for r in summaries if r['window']=='ALL']),indent=2))
if __name__=='__main__':main()
