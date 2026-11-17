"""Independent arithmetic; never invoke the producer's scorer or fit models."""
import argparse,collections,csv,gzip,hashlib,json,math
from decimal import Decimal
from pathlib import Path
import numpy as np
from scipy import stats
BASE='B-player-context-matchup-01-v1:'
def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dig(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def eq(a,b,tol=2e-10):
 if a is None or b is None:assert a is b,(a,b)
 else:assert math.isclose(a,b,rel_tol=tol,abs_tol=tol),(a,b)
def k(r):return r['game_id'],r['player_id'],r['target']
def fall(r):return r.get('fallback')not in(None,'none','NONE','learned','NOT_APPLICABLE')
def direction(point,line):
 if point is None:return None
 a,b=Decimal(str(point)),Decimal(str(line));return 'over'if a>b else'under'if a<b else None
def crossing(actual,line,side):
 if side is None:return 'ABSTAIN'
 a,b=Decimal(str(actual)),Decimal(str(line))
 return 'PUSH'if a==b else'WIN'if(a>b if side=='over'else a<b)else'LOSS'
def cdf(law,n):
 if law['kind']=='gamma_poisson_count':
  mu,z=law['mean'],law['shape'];return float(n>=0)if not mu else float(stats.nbinom.cdf(n,z,z/(z+mu)))
 support=np.asarray(law['support']);w=np.asarray(law['weights']);w=w/w.sum();p=law['prior'];q=p['q']
 pc=0. if n<0 else 1-q**(n+1)
 return (1-law['mixture'])*float(w[support<=n].sum())+law['mixture']*pc
def probs(law,line):
 f=math.floor(line);u=cdf(law,f-1)if line==f else cdf(law,f);v=cdf(law,f)
 return dict(over=1-v,under=u,push=v-u)
def logmass(law,y):
 if law['kind']=='gamma_poisson_count':
  mu,z=law['mean'],law['shape'];return 0. if not mu and y==0 else -math.inf if not mu else math.lgamma(y+z)-math.lgamma(z)-math.lgamma(y+1)+z*math.log(z/(z+mu))+y*math.log(mu/(z+mu))
 w=np.asarray(law['weights']);w/=w.sum();support=np.asarray(law['support']);v=float(w[support==y].sum());q=law['prior']['q'];pp=(1-q)*q**y if y>=0 else 0
 mass=(1-law['mixture'])*v+law['mixture']*pp;return math.log(mass)if mass else -math.inf
def probability_metrics(rows):
 good=[r for r in rows if r['probs']is not None];n=len(good)
 if not n:return dict(n=0,brier=None,log_loss=None,infinite_log_losses=0)
 losses=[];ll=[]
 for r in good:
  event='over'if r['actual']>r['line']else'under'if r['actual']<r['line']else'push';p=r['probs']
  losses.append(.5*math.fsum((p[s]-float(s==event))**2 for s in('over','under','push')));ll.append(-math.log(p[event])if p[event]else math.inf)
 inf=sum(not math.isfinite(v)for v in ll)
 return dict(n=n,brier=math.fsum(losses)/n,log_loss=math.fsum(ll)/n if not inf else None,infinite_log_losses=inf)
def quantile(x,p):
 x=sorted(x);v=(len(x)-1)*p;i=math.floor(v);return x[i]+(v-i)*(x[min(i+1,len(x)-1)]-x[i])
def main():
 ap=argparse.ArgumentParser()
 for x in('repo','wave','scores','inputs','output'):ap.add_argument('--'+x,type=Path,required=True)
 for w in range(5,9):ap.add_argument('--week'+str(w),type=Path,required=True)
 ap.add_argument('--old-predictions',type=Path,action='append',required=True);a=ap.parse_args()
 frozen=read(a.scores/'FROZEN_SCORING_PROTOCOL.json');sc=read(a.scores/'SCORES.json');pairs=read(a.scores/'PAIRED_COMPARISONS.json');commit=read(a.scores/'OWNER_LOCAL_CALCULATION_COMMITMENTS.json')
 offers=[]
 for w in range(5,9):
  path=getattr(a,'week'+str(w));assert sha(path)==next(r['sha256']for r in frozen['offers']if r['week']==w)
  for r in read(path)['rows']:
   if r.get('target')not in('pass_cmp','pass_att'):continue
   if w==8 and not(r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original'and not r.get('method_key')):continue
   assert r['label_state']=='SUPPORTED'and r['actual']is not None;offers.append(r)
 assert len(offers)==224 and len({(k(r),str(r['line']))for r in offers})==224
 pred=[r for p in sorted((a.wave/'predictions').glob('*.json.gz'))for r in read(p)['rows']];assert len(pred)==7528
 indexed={(r['procedure_id'],k(r)):r for r in pred};assert len(indexed)==len(pred)
 source=read(a.inputs);good=[r for r in source if r['physical_participation']and r['target_parity']];qmap={(r['game_id'],r['player_id']):r for r in source}
 # Stream the existing old source files once. Retain exact distinct recipe IDs.
 wanted={k(r)for r in offers};old=collections.defaultdict(dict);oldbindings=[]
 for path in a.old_predictions:
  oldbindings.append(dict(source_id='OLD_POINT_SOURCE_'+str(len(oldbindings)+1),sha256=sha(path),bytes=path.stat().st_size))
  with gzip.open(path,'rt')as h:
   for r in csv.DictReader(h):
    if r['target']not in('pass_cmp','pass_att')or r['position']!='QB'or r['history_regime']!='H-RECENT'or r['family']!='ordered_leaf_cdf'or r['product_id']not in('mean','lower_median'):continue
    if k(r)not in wanted:continue
    if r.get('information_policy')not in(None,'','COMMON_FEATURE_MEMORY','COMMON','common-feature-memory')and'strict-current'in r.get('procedure_id',''):continue
    try:value=float(r['prediction']);actual=float(r['actual'])
    except(ValueError,TypeError):continue
    key=k(r),r['product_id'];v=(value,actual,r.get('fallback'))
    if key in old[r['procedure_id']]:assert old[r['procedure_id']][key]==v
    old[r['procedure_id']][key]=v
 oldmap={proc+'::SAVED_'+product:(proc,product)for proc,entries in old.items()for product in('mean','lower_median')if any(key[1]==product for key in entries)}
 procedures=sorted({r['procedure_id']for r in pred})+['SAVED_ADJUSTED','SAVED_RAW','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE','NEUTRAL_HALFPOINT']+list(oldmap)
 policyrows={};commitchecks=[]
 for target in('pass_cmp','pass_att'):
  board=[r for r in offers if r['target']==target];assert len(board)==112
  for method in procedures:
   if method.startswith(BASE)and not any((method,k(r))in indexed for r in board):continue
   policies=['P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','P90']if method.startswith(BASE)else['REGISTERED_DIRECTION']
   for policy in policies:
    rows=[]
    for ordinal,r in enumerate(board):
     prediction=indexed.get((method,k(r)));point=None;p=None;side=None;fb='none';band='CONTROL_SCOPE'
     if prediction:
      assert prediction['actual']==r['actual'];p=probs(prediction['law'],r['line']);fb=prediction['fallback'];band=prediction['pregame_role_band'];point=prediction['mean'if policy=='P1_MEAN'else'lower_median']
      side=direction(point,r['line'])if policy.startswith('P1_')else'over'if p['over']>p['under']else'under'if p['under']>p['over']else None
      if policy=='P90'and(side is None or p[side]<.9):side=None
     elif method in oldmap:
      proc,product=oldmap[method];saved=old[proc].get((k(r),product))
      if saved:point,actual,fb=saved;assert actual==r['actual'];side=direction(point,r['line'])
     elif method in('SAVED_ADJUSTED','SAVED_RAW'):point=r.get('prediction'if method=='SAVED_ADJUSTED'else'raw_prediction');side=direction(point,r['line'])
     elif method in('ALWAYS_OVER','ALWAYS_UNDER'):side='over'if method=='ALWAYS_OVER'else'under'
     elif method=='NEUTRAL_HALFPOINT':
      if r['line']%1==.5:p=dict(over=.5,under=.5,push=0.)
     elif method=='EARLIER_LINE_PREVALENCE':
      q=qmap[r['game_id'],r['player_id']];past=[z for z in good if z['season']>=q['season']-1 and z['available']<q['kickoff']];field='official_completions'if target=='pass_cmp'else'official_attempts';values=[z[field]for z in past];whole=r['line'].is_integer()if isinstance(r['line'],float)else int(r['line'])==r['line'];den=len(values)+(3 if whole else 2)
      p=dict(over=(sum(v>r['line']for v in values)+1)/den,under=(sum(v<r['line']for v in values)+1)/den,push=(sum(v==r['line']for v in values)+1)/den if whole else 0.)
      side='over'if p['over']>p['under']else'under'if p['under']>p['over']else None
     if p:assert min(p.values())>=-1e-12 and math.isclose(sum(p.values()),1,abs_tol=1e-10)
     available=prediction is not None or point is not None or side is not None or p is not None
     rows.append(dict(r,ordinal=ordinal,selected_side=side,statistical_state=crossing(r['actual'],r['line'],side),probs=p,fallback=fb,technical_unavailable=not available,pregame_role_band=band))
    policyrows[target,method,policy]=rows
    expected=next(c for c in commit if(c['target'],c['procedure_id'],c['policy'])==(target,method,policy));assert expected['rows']==len(rows)
    calculated=dig([{k:r.get(k)for k in('game_id','player_id','target','line','selected_side','actual','statistical_state','probs','fallback')}for r in rows])
    commitchecks.append(dict(target=target,procedure_id=method,policy=policy,exact_row_commitment_match=calculated==expected['row_calculations_sha256']))
 # Rebuild only registered membership, not a new selection/scoring pipeline.
 # No outcome field enters any rank or tie break.
 def choose(weekly,poolside,K):
  remaining=K;chosen=set()
  for batch in sorted({r['kickoff']for r in weekly}):
   candidates=[r for r in weekly if r['kickoff']==batch and r['selected_side']and(poolside=='Combined'or r['selected_side']==poolside)]
   candidates.sort(key=lambda r:(-r['probs'][r['selected_side']],r['game_id'],r['player_id'],str(r['line'])))
   add=candidates[:remaining];chosen.update(r['ordinal']for r in add);remaining-=len(add)
  return chosen
 sidechecks=probchecks=topchecks=0;metadata=collections.Counter();numericchecks=0
 for s in sc:
  kind=s['record_kind'];method=s['procedure_id'];target=s['target'];window=s['week']
  if kind=='forecast_evaluation_view':
   outer=[r for r in pred if r['procedure_id']==method and r['season']==s['season']]
   if window=='W1_4':outer=[r for r in outer if r['week']<=4]
   elif window=='W5_PLUS':outer=[r for r in outer if r['week']>=5]
   elif window!='ALL':outer=[r for r in outer if r['week']==window]
   rr=[r for r in outer if s['fallback_view']=='FULL_SYSTEM'or(s['fallback_view']=='FALLBACK')==fall(r)];vals=[r for r in rr if r['actual']is not None];product=s['product_id'];errors=[r[product]-r['actual']for r in vals];abses=[abs(v)for v in errors];n=len(errors)
   assert s['n']==n and s['forecast_rows']==len(rr)and s['outer_query_rows']==len(outer)and s['fallback_rows']==sum(fall(r)for r in rr)
   for name,value in [('mae',sum(abses)/n if n else None),('mse',sum(v*v for v in errors)/n if n else None),('bias',sum(errors)/n if n else None),('rmse',math.sqrt(sum(v*v for v in errors)/n)if n else None),('max_abs',max(abses)if n else None),('p90_abs',quantile(abses,.9)if n else None),('p95_abs',quantile(abses,.95)if n else None)]:eq(s[name],value)
   for name,z in s['precision_counts'].items():
    if name=='exact_rate':hits=sum(v==0 for v in errors)
    else:_,op,distance=name.split('_');hits=sum(v<int(distance)if op=='lt'else v<=int(distance)for v in abses)
    assert z['numerator']==hits and z['denominator']==n;eq(z['rate'],hits/n if n else None)
   if n:
    ll=[-logmass(r['law'],r['actual'])for r in vals];inf=sum(not math.isfinite(v)for v in ll);assert s['infinite_NLL']==inf;eq(s['NLL'],sum(ll)/n if not inf else None,tol=1e-9)
   numericchecks+=1;continue
  if kind=='prop_threshold_probability_evaluation':
   rr=policyrows[target,method,'P2_STATISTICAL_LAW'if method.startswith(BASE)else'REGISTERED_DIRECTION'];rr=[r for r in rr if window=='ALL'or r['week']==window];z=probability_metrics(rr)
   for field in('n','brier','log_loss','infinite_log_losses'):eq(s[field],z[field])
   if method=='NEUTRAL_HALFPOINT':assert s['brier']==.25
   probchecks+=1;continue
  assert kind=='prop_selection_evaluation';policy=s['product_id'];basepolicy='P2_STATISTICAL_LAW'if policy=='ROLLING_TOP_K_DIAGNOSTIC'else policy
  rr=policyrows[target,method,basepolicy];rr=[r for r in rr if window=='ALL'or r['week']==window]
  if policy=='ROLLING_TOP_K_DIAGNOSTIC':
   chosen=choose(rr,s['rank_scope'],s['K']);mutated=[dict(r,actual=-999,statistical_state='LOSS')for r in rr];assert choose(mutated,s['rank_scope'],s['K'])==chosen
   rr=[dict(r,selected_side=r['selected_side']if r['ordinal']in chosen else None,statistical_state=r['statistical_state']if r['ordinal']in chosen else'ABSTAIN')for r in rr];topchecks+=1
  cohort=s['cohort_id']
  if cohort=='LEARNED':rr=[r for r in rr if not fall(r)]
  elif cohort=='FALLBACK':rr=[r for r in rr if fall(r)]
  elif cohort.startswith('ROLE:'):rr=[r for r in rr if r['pregame_role_band']==cohort[5:]]
  chosen=[r for r in rr if r['selected_side']and(s['side']=='Combined'or r['selected_side']==s['side'])];counts=collections.Counter(r['statistical_state']for r in chosen);m=s['selection_metrics'];n=counts['WIN']+counts['LOSS']
  assert s['forecast_rows']==len(chosen)and s['n']==n and m['selection_pool_count']==len(rr)
  for st in('WIN','LOSS','PUSH'):assert m[st]==counts[st]
  eq(m['hit_rate'],counts['WIN']/n if n else None);assert s['technical_unavailable']==sum(r['technical_unavailable']for r in rr)and s['fallback_rows']==sum(fall(r)for r in chosen)
  assert m['admitted_rule_abstentions']==sum(r['selected_side']is None and not r['technical_unavailable']for r in rr)
  eq(m['selection_coverage'],len(chosen)/len(rr)if rr else None)
  z=probability_metrics(chosen)
  for f in('n','brier','log_loss','infinite_log_losses'):eq(m['probability_scores'][f],z[f])
  if s.get('time_panel_id')=='2026_W7_FULL_PROVIDER_LABELLED_462_13_GAMES':metadata['STALE_HELPER_W7_PANEL_LABEL']+=1
  if not method.startswith(BASE)and s.get('history_regime')=='H-RECENT':metadata['ARCHIVED_OR_CONSTANT_HISTORY_OVERRIDE_NEEDED']+=1
  sidechecks+=1
 # Pairwise native/offer point estimates and game-cluster sensitivity; do not
 # rerun the parent helper or reinterpret exposed maxima as routing policies.
 pairchecks=0
 for q in pairs:
  if q['kind']=='NUMERICAL_PAIRED_MAE':
   aa=[r for r in pred if r['season']==q['season']and r['method']==q['candidate']];bb={k(r):r for r in pred if r['season']==q['season']and r['method']==q['control']};same=[(r,bb[k(r)])for r in aa if r['actual']is not None and(q['scope']=='FULL_SYSTEM'or not fall(r)and not fall(bb[k(r)]))];av=[abs(r[q['product']]-r['actual'])for r,b in same];bv=[abs(b[q['product']]-b['actual'])for r,b in same]
  else:
   aa=policyrows[q['target'],q['candidate'],q['policy']];bb={k(r):r for r in policyrows[q['target'],q['control'],q['control_policy']]};same=[(r,bb[k(r)])for r in aa if(q['window']=='ALL'or r['week']==q['window'])and r['statistical_state']in('WIN','LOSS')and bb[k(r)]['statistical_state']in('WIN','LOSS')];av=[float(r['statistical_state']=='LOSS')for r,b in same];bv=[float(b['statistical_state']=='LOSS')for r,b in same]
   assert q['candidate_wins']==sum(r['statistical_state']=='WIN'for r,b in same)and q['control_wins']==sum(b['statistical_state']=='WIN'for r,b in same)
   assert dig(sorted([r['game_id'],r['player_id'],r['target']]for r,b in same))==q['membership_sha256']
  n=len(same);assert n==q['n'];delta=math.fsum(x-y for x,y in zip(av,bv))/n
  eq(q['candidate_error'],sum(av)/n);eq(q['comparator_error'],sum(bv)/n);eq(q['delta'],delta)
  bygame=collections.defaultdict(list)
  for (r,b),x,y in zip(same,av,bv):bygame[r['game_id']].append(x-y)
  G=len(bygame);se=math.sqrt(G/(G-1)*math.fsum((math.fsum(v)-delta*len(v))**2 for v in bygame.values()))/n if G>=8 else None;eq(q['game_cluster_sensitivity_se'],se);pairchecks+=1
 # Frozen no-selection and matched full-mask headline witnesses.
 assert all(not any(r['selected_side']for r in rows)for key,rows in policyrows.items()if key[2]=='P90')
 headlines=[]
 for target,method,policy in [('pass_cmp',BASE+'E0','P2_STATISTICAL_LAW'),('pass_cmp',BASE+'E3','P2_STATISTICAL_LAW'),('pass_cmp','SAVED_ADJUSTED','REGISTERED_DIRECTION'),('pass_cmp','ALWAYS_OVER','REGISTERED_DIRECTION'),('pass_cmp','EARLIER_LINE_PREVALENCE','REGISTERED_DIRECTION')]:
  rows=policyrows[target,method,policy];assert len(rows)==112;headlines.append(dict(target=target,procedure=method,policy=policy,over_wins=sum(r['selected_side']=='over'and r['statistical_state']=='WIN'for r in rows),over_losses=sum(r['selected_side']=='over'and r['statistical_state']=='LOSS'for r in rows),under_wins=sum(r['selected_side']=='under'and r['statistical_state']=='WIN'for r in rows),under_losses=sum(r['selected_side']=='under'and r['statistical_state']=='LOSS'for r in rows),wins=sum(r['statistical_state']=='WIN'for r in rows),decided=sum(r['statistical_state']in('WIN','LOSS')for r in rows)))
 assert [r['wins']for r in headlines]==[49,58,58,58,59]
 result=dict(state='PASS_INDEPENDENT_ARITHMETIC_WITH_METADATA_QUALIFICATION_REQUIRED',source_scores_sha256=sha(a.scores/'SCORES.json'),source_pair_sha256=sha(a.scores/'PAIRED_COMPARISONS.json'),
   source_commitments_sha256=sha(a.scores/'OWNER_LOCAL_CALCULATION_COMMITMENTS.json'),offer_rows=224,complete_CMP_rows=112,complete_ATT_rows=112,
   prediction_records=7528,numeric_views_checked=numericchecks,selection_side_views_checked=sidechecks,proper_score_views_checked=probchecks,paired_views_checked=pairchecks,
   rolling_topK_side_views_checked=topchecks,calculation_commitments=commitchecks,exact_commitment_matches=sum(x['exact_row_commitment_match']for x in commitchecks),
   parent_metadata_findings=dict(metadata),headline_same_mask_witnesses=headlines,old_source_bindings=oldbindings,
   methodology='Primitive Decimal inequalities, independently reconstructed CDF events and categorical losses, direct native errors/precision, chronological game-batch membership and independent pair residual sums. SciPy NB primitives used without invoking root scorer, law classes, grader or fit functions.',
   scope='New/current 2026actual-offer W5-W8only, four exposedweeks; numerical2025fullREG+2026W1-W8separate. OldLeaf/C02partial masks and recipes retained separately. No calibration on evaluated outcomes or future originalissuance claim.',
   caveats=['Original raw score metadata contains inherited W7panel labels and archived-control history/horizon overrides; parent preparing source-bound corrections without metric changes','Neutral0.25 is halfpoint no-push reference only','NoP90selections; emptyrateN/A and0selectedweeks','P3own-onlycoefficienttraininguses sharedinputs/exposure/P1fallback','No price/settlement/ROI or productionadmission established'],
   scorer_invocations=0,NFL_fits=0,model_loads=0,new_private_row_exports=0)
 if a.output.exists():raise FileExistsError(a.output)
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(state=result['state'],views=numericchecks+sidechecks+probchecks,pairs=pairchecks,exact_commitments=result['exact_commitment_matches'],sha256=sha(a.output))))
if __name__=='__main__':main()
