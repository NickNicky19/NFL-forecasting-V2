"""Independent raw offer grading/counts and saved forecast metrics. No parent scorer."""
import collections,datetime,gzip,hashlib,json,math,resource,sys,time
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from nfl_v2.paired_uncertainty import paired_losses
NEW=('D1','D2','C1','C2');POL=('P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','P90')
def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dig(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def eq(a,b,tol=3e-10):
 if a is None or b is None:assert a is b,(a,b)
 else:assert math.isclose(a,b,rel_tol=tol,abs_tol=tol),(a,b)
def key(r):return r['game_id'],r['player_id'],'pass_cmp'
def fallback(r):return r.get('fallback')not in(None,'none','NONE','learned','NOT_APPLICABLE')
def direction(x,line):
 if x is None:return None
 a,b=Decimal(str(x)),Decimal(str(line));return'over'if a>b else'under'if a<b else None
def grade(actual,line,side):
 if side is None:return'ABSTAIN'
 a,b=Decimal(str(actual)),Decimal(str(line));return'PUSH'if a==b else'WIN'if(a>b if side=='over'else a<b)else'LOSS'
def cdf(law,k):
 if k<0:return 0.
 k=int(math.floor(k))
 if law['kind']=='gamma_poisson_count':
  m,r=law['mean'],law['shape']
  if m==0:return 1.
  p=r/(r+m);t=math.exp(r*math.log(p));terms=[t]
  for i in range(1,k+1):t*=((r+i-1)/i)*(1-p);terms.append(t)
  return math.fsum(terms)
 w=law['weights'];z=math.fsum(w);q=law['prior']['q'];return(1-law['mixture'])*math.fsum(v/z for a,v in zip(law['support'],w)if a<=k)+law['mixture']*(1-q**(k+1))
def probs(law,line):
 k=math.floor(line);v=cdf(law,k);u=cdf(law,k-1)if line==k else v;return{'over':1-v,'under':u,'push':v-u}
def logmass(law,y):
 if law['kind']=='gamma_poisson_count':
  m,r=law['mean'],law['shape']
  if m==0:return 0.if y==0 else-math.inf
  return math.lgamma(y+r)-math.lgamma(r)-math.lgamma(y+1)+r*math.log(r/(r+m))+y*math.log(m/(r+m))
 z=math.fsum(law['weights']);emp=math.fsum(v/z for a,v in zip(law['support'],law['weights'])if a==y);q=law['prior']['q'];p=(1-law['mixture'])*emp+law['mixture']*(1-q)*q**y;return math.log(p)if p else-math.inf
def quantile(values,p):
 a=sorted(values);i=(len(a)-1)*p;j=math.floor(i);return a[j]+(i-j)*(a[min(j+1,len(a)-1)]-a[j])
def probmetrics(rr):
 good=[r for r in rr if r['probs']is not None];n=len(good)
 if not n:return{'n':0,'brier':None,'log_loss':None,'infinite_log_losses':0}
 bs=[];ll=[]
 for r in good:
  ev='over'if r['actual']>r['line']else'under'if r['actual']<r['line']else'push';p=r['probs'];bs.append(.5*math.fsum((p[k]-int(ev==k))**2 for k in('over','under','push')));ll.append(-math.log(p[ev])if p[ev]>0 else math.inf)
 inf=sum(not math.isfinite(x)for x in ll);return{'n':n,'brier':math.fsum(bs)/n,'log_loss':math.fsum(ll)/n if not inf else None,'infinite_log_losses':inf}
def native_rows(rr,window,keys,games):
 if window=='ALL':return rr
 if window=='W1_4':return[r for r in rr if r['week']<=4]
 if window=='W5_PLUS':return[r for r in rr if r['week']>=5]
 if window=='W1_8':return[r for r in rr if r['week']<=8]
 if window=='MATCHED_OFFERS_W5_W8':return[r for r in rr if key(r)in keys]
 if window=='COVERED_GAMES_W5_W8':return[r for r in rr if r['game_id']in games]
 return[r for r in rr if r['week']==window]
def numcheck(s,rr):
 p=s['product_id'];good=[r for r in rr if r['actual']is not None and r.get(p)is not None];n=len(good);assert s['n']==n
 if not n:assert s['mae']is None;return
 errors=[r[p]-r['actual']for r in good];ae=list(map(abs,errors));mse=math.fsum(e*e for e in errors)/n
 for k,v in [('mae',math.fsum(ae)/n),('mse',mse),('rmse',math.sqrt(mse)),('bias',math.fsum(errors)/n),('p90_abs',quantile(ae,.9)),('p95_abs',quantile(ae,.95)),('max_abs',max(ae))]:eq(s[k],v)
 for k in('exact_rate','abs_lt_1','abs_le_1','abs_lt_5','abs_le_5','abs_lt_10','abs_le_10'):
  if k=='exact_rate':hits=sum(x==0 for x in ae)
  else:_,op,z=k.split('_');hits=sum(x<int(z)if op=='lt'else x<=int(z)for x in ae)
  eq(s[k],hits/n);assert s['precision_counts'][k]['numerator']==hits and s['precision_counts'][k]['denominator']==n
 assert s['unique_games']==len({r['game_id']for r in good});assert s['query_membership_sha256']==dig(sorted([r['game_id'],r['player_id'],'pass_cmp']for r in good))
 if 'NLL'in s:
  ls=[-logmass(r['law'],r['actual'])for r in good];inf=sum(not math.isfinite(x)for x in ls);assert s['infinite_NLL']==inf;eq(s['NLL'],None if inf else math.fsum(ls)/n)
def selected_check(s,rows):
 selected=[r for r in rows if r['selected_side']is not None and(s['side']=='Combined'or r['selected_side']==s['side'])];st=collections.Counter(r['statistical_state']for r in selected);m=s['selection_metrics'];n=st['WIN']+st['LOSS'];assert s['n']==n
 assert m['WIN']==st['WIN']and m['LOSS']==st['LOSS']and m['PUSH']==st['PUSH'];assert m['denominators']['outer_rows']==len(selected)and m['denominators']['decided']==n
 eq(m['hit_rate'],st['WIN']/n if n else None);assert m['selection_pool_count']==len(rows)
 assert s['technical_unavailable']==sum(r['unavailable']for r in rows)
 assert m['admitted_rule_abstentions']==sum(r['selected_side']is None and not r['unavailable']for r in rows)
 assert m['fallback_issued']==sum(fallback(r)for r in selected)
 pp=probmetrics(selected)
 for k,v in pp.items():eq(m['probability_scores'][k],v)
 assert s['unique_games']==len({r['game_id']for r in selected})
def main():
 start=time.monotonic();b=ROOT/'reports/player-context-completion-decision-01/B';old=ROOT/'reports/player-context-matchup-01/B';scores=read(b/'depth-scores-v2/SCORES.json');tables=read(b/'depth-scores-v2/COMMON_CONTROL_TABLE.json');sourcepaths=read(Path('/tmp/b-context-offer-sources.json'));offers=[];bindings=[]
 for w in range(5,9):
  p=Path(sourcepaths[str(w)]);bindings.append({'week':w,'sha256':sha(p),'bytes':p.stat().st_size})
  for r in read(p)['rows']:
   if r.get('target')!='pass_cmp':continue
   if w==8 and not(r.get('panel')=='ORIGINAL_PROVIDER_T90'and r.get('strategy')=='original'and not r.get('method_key')):continue
   assert r['season']==2026 and r['week']==w and r['position']=='QB'and r['label_state']=='SUPPORTED'and r['actual']is not None;offers.append(r)
 assert len(offers)==112 and len({key(r)for r in offers})==112 and all(float(r['line'])%1==.5 for r in offers)
 base=read(old/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz');good=[r for r in base if r['physical_participation']and r['target_parity']];qmap={(r['game_id'],r['player_id']):r for r in base};newrows=[r for p in sorted((b/'depth-wave-v2/predictions').glob('*.json.gz'))for r in read(p)['rows']];assert len(newrows)==3764
 controls=[r for p in sorted((old/'qb-wave-v1/predictions').glob('*.json.gz'))for r in read(p)['rows']if r['method']in('E1','P1','E3')]
 controls +=[r for p in sorted((old/'qb-charting-wave-v1/predictions').glob('*.json.gz'))for r in read(p)['rows']if r['method']=='F2']
 own=[]
 for q in base:
  if q['season']not in(2025,2026):continue
  earlier=sorted([r for r in good if r['player_id']==q['player_id']and r['available']<q['kickoff']],key=lambda r:(r['kickoff'],r['game_id']))[-8:];y=sorted(r['official_completions']for r in earlier);mean=math.fsum(y)/len(y)if y else None;med=y[(len(y)-1)//2]if y else None
  own.append(dict(q,method='OWN8',procedure_id='B-OWN-INFORMATION-EMPIRICAL8-v1',mean=mean,lower_median=med,actual=q['official_completions']if q['physical_participation']else None,target='pass_cmp',fallback='none'))
 indexed={(r['method'],key(r)):r for r in newrows+controls+own};assert len(indexed)==len(newrows+controls+own)
 policyrows={};newids={r['method']:r['procedure_id']for r in newrows};ids={**newids,'OWN8':'B-OWN-INFORMATION-EMPIRICAL8-v1'};reverse={v:k for k,v in ids.items()}
 for method in(*NEW,'E1','P1','E3','F2','OWN8','SAVED_ADJUSTED','SAVED_RAW','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE','NEUTRAL_HALFPOINT'):
  policies=POL if method in(*NEW,'E1','P1','E3','F2')else('P1_MEAN','P1_LOWER_MEDIAN')if method=='OWN8'else('REGISTERED_DIRECTION',)
  for policy in policies:
   rr=[]
   for ordinal,r in enumerate(offers):
    pred=indexed.get((method,key(r)));point=None;pr=None;side=None;unavail=False;fb='none'
    if pred:
     assert pred['actual']==r['actual'];fb=pred.get('fallback','none');point=pred['mean'if policy=='P1_MEAN'else'lower_median'];unavail=point is None
     if pred.get('law'):pr=probs(pred['law'],r['line'])
     side=direction(point,r['line'])if policy.startswith('P1_')else'over'if pr['over']>pr['under']else'under'if pr['under']>pr['over']else None
     if policy=='P90'and(side is None or pr[side]<.9):side=None
    elif method in('SAVED_ADJUSTED','SAVED_RAW'):point=r.get('prediction'if method=='SAVED_ADJUSTED'else'raw_prediction');side=direction(point,r['line']);unavail=point is None
    elif method in('ALWAYS_OVER','ALWAYS_UNDER'):side='over'if method=='ALWAYS_OVER'else'under'
    elif method=='NEUTRAL_HALFPOINT':pr={'over':.5,'under':.5,'push':0.}
    else:
     q=qmap[r['game_id'],r['player_id']];values=[x['official_completions']for x in good if x['season']>=2025 and x['available']<q['kickoff']];den=len(values)+2;pr={'over':(sum(y>r['line']for y in values)+1)/den,'under':(sum(y<r['line']for y in values)+1)/den,'push':0.};side='over'if pr['over']>pr['under']else'under'if pr['under']>pr['over']else None
    if pr:assert min(pr.values())>=-2e-12;eq(sum(pr.values()),1.)
    rr.append(dict(r,ordinal=ordinal,selected_side=side,statistical_state=grade(r['actual'],r['line'],side),probs=pr,unavailable=unavail,fallback=fb))
   policyrows[method,policy]=rr
 keys={key(r)for r in offers};games={r['game_id']for r in offers};num=sel=prob=top=0;top_memberships=[]
 by=collections.defaultdict(list)
 for r in newrows+own:by[r['season'],r['method']].append(r)
 for s in scores:
  method=reverse[s['procedure_id']]
  if s['record_kind']=='forecast_evaluation_view':
   rr=native_rows(by[s['season'],method],s['week'],keys,games);scope=s['fallback_view'];rs=[r for r in rr if scope=='FULL_SYSTEM'or (not fallback(r)if scope=='LEARNED'else fallback(r))];numcheck(s,rs);num+=1
  elif s['record_kind']=='prop_threshold_probability_evaluation':
   rr=policyrows[method,'P2_STATISTICAL_LAW'];rr=rr if s['week']=='ALL'else[r for r in rr if r['week']==s['week']];pp=probmetrics(rr)
   for k,v in pp.items():eq(s[k],v)
   prob+=1
  else:
   if s['strategy']=='ROLLING_TOP_K_DIAGNOSTIC':
    weekly=[r for r in policyrows[method,'P2_STATISTICAL_LAW']if r['week']==s['week']];slots=s['K'];chosen=[]
    for batch in sorted({r['kickoff']for r in weekly}):
     ee=[r for r in weekly if r['kickoff']==batch and r['selected_side']and(s['rank_scope']=='Combined'or r['selected_side']==s['rank_scope'])];ee.sort(key=lambda r:(-r['probs'][r['selected_side']],r['game_id'],r['player_id'],str(r['line'])));chosen+=ee[:slots];slots-=min(slots,len(ee))
    ids_chosen={r['ordinal']for r in chosen};rr=[dict(r,selected_side=r['selected_side']if r['ordinal']in ids_chosen else None,statistical_state=r['statistical_state']if r['ordinal']in ids_chosen else'ABSTAIN')for r in weekly];top+=1
    if s['side']=='Combined':top_memberships.append({'method':method,'week':s['week'],'pool':s['rank_scope'],'K':s['K'],'selected':len(chosen),'membership_sha256':dig(sorted([r['game_id'],r['player_id'],'pass_cmp',str(r['line'])]for r in chosen))})
   else:rr=policyrows[method,s['strategy']];rr=rr if s['week']=='ALL'else[r for r in rr if r['week']==s['week']]
   selected_check(s,rr);sel+=1
 # Everycontrol summary regraded on its ownpool; no unsupportedprobabilities onOWN8.
 ct=0
 for t in tables:
  method=reverse.get(t['method'],t['method']);rr=policyrows[method,t['policy']];rr=rr if t['window']=='ALL'else[r for r in rr if r['week']==t['window']]
  for z in t['sides']:
   side=z['side'];ss=[r for r in rr if r['selected_side']and(side=='Combined'or r['selected_side']==side)];c=collections.Counter(r['statistical_state']for r in ss);met=z['metrics'];assert met['WIN']==c['WIN']and met['LOSS']==c['LOSS']and met['denominators']['decided']==c['WIN']+c['LOSS'];eq(met['hit_rate'],c['WIN']/(c['WIN']+c['LOSS'])if c['WIN']+c['LOSS']else None)
  for k,v in probmetrics(rr).items():eq(t['probability'][k],v)
  ct+=1
 # New necessary matched-ownpoint contrasts: author scorer doesnot containthese.
 contrasts=[]
 for method in NEW:
  for ownproduct,opolicy in [('mean','P1_MEAN'),('lower_median','P1_LOWER_MEDIAN')]:
   aa=policyrows[method,'P2_STATISTICAL_LAW'];bb=policyrows['OWN8',opolicy]
   for window in('ALL',5,6,7,8):
    same=[(a,z)for a,z in zip(aa,bb)if(window=='ALL'or a['week']==window)and a['statistical_state']in('WIN','LOSS')and z['statistical_state']in('WIN','LOSS')];ca=sum(a['statistical_state']=='WIN'for a,z in same);co=sum(z['statistical_state']=='WIN'for a,z in same)
    zz=paired_losses([float(a['statistical_state']=='LOSS')for a,z in same],[float(z['statistical_state']=='LOSS')for a,z in same],[(2026,a['week'])for a,z in same],[a['game_id']for a,z in same]);eq(zz['delta'],(co-ca)/len(same)if same else None)
    contrasts.append(dict(kind='OFFER_DIRECTION_PAIRED_LOSS',season=2026,window=window,target='pass_cmp',candidate=newids[method],control='B-OWN-INFORMATION-EMPIRICAL8-v1::'+ownproduct,policy='P2_STATISTICAL_LAW',control_policy=opolicy,scope='COMMON_SELECTED_POINT_CONTROL',candidate_wins=ca,control_wins=co,eligible_offers=len([r for r in aa if window=='ALL'or r['week']==window]),membership_sha256=dig(sorted([a['game_id'],a['player_id'],'pass_cmp',str(a['line'])]for a,z in same)),**zz))
 assert len(contrasts)==40
 out=b/'independent';(out/'OWN8_PAIRED_PROP_COMPARISONS_V1.json').write_text(json.dumps(contrasts,indent=2,allow_nan=False)+'\n')
 result={'id':'B-DEPTH-FULL-SCORES-INDEPENDENT-v1','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','source_scores_sha256':sha(b/'depth-scores-v2/SCORES.json'),'source_control_table_sha256':sha(b/'depth-scores-v2/COMMON_CONTROL_TABLE.json'),'source_forecast_records':len(newrows),'verified_views':{'numerical':num,'selection':sel,'probability':prob,'topK_selection_rows_within_selection':top,'all':num+sel+prob},'control_policy_windows_checked':ct,'source_offer_bindings':bindings,'source_qualified_offers':112,'actual_weeks':[5,6,7,8],'games':56,'all_lines_halfpoint':True,'own_information_scope':'Ownlast8 historicaloutcome pointmean/lowermedian; no laws/probabilities. Frozen8lookback fromsharedpriorstudy is disclosed; thisisnotanindependentlytunedperplayerprocedure.','own_offer_status':{p:dict(selected=sum(r['selected_side']is not None for r in policyrows['OWN8',p]),wins=sum(r['statistical_state']=='WIN'for r in policyrows['OWN8',p]),losses=sum(r['statistical_state']=='LOSS'for r in policyrows['OWN8',p]),abstained=sum(r['selected_side']is None and not r['unavailable']for r in policyrows['OWN8',p]),unavailable=sum(r['unavailable']for r in policyrows['OWN8',p]))for p in('P1_MEAN','P1_LOWER_MEDIAN')},'new_law_P2':{m:dict(wins=sum(r['statistical_state']=='WIN'for r in policyrows[m,'P2_STATISTICAL_LAW']),losses=sum(r['statistical_state']=='LOSS'for r in policyrows[m,'P2_STATISTICAL_LAW']),**probmetrics(policyrows[m,'P2_STATISTICAL_LAW']))for m in NEW},'topK_membership_commitments':top_memberships,'OWN8_new_scientific_paired_views':40,'new_scientific_paired_artifact_sha256':sha(out/'OWN8_PAIRED_PROP_COMPARISONS_V1.json'),'metadata_limit':'Inheritedtime_panel_idW7 label must be corrected bysource-bound metadataoverlay; evaluationweeks/grades areactualW5-8. No metric correction needed.','new_fits':0,'new_forecasts':0,'new_original_selections':0,'private_row_exports':0,'author_summary_scorer_calls':0,'uncertainty':'Existingdeclaredpaired_uncertaintyhelperusedonlyfor40newscientificcontrasts; primitivecountsindependent. Fewweek/multiplicity/exposurelimits retained.','resources':{'wall_seconds':time.monotonic()-start,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}}
 assert result['verified_views']['all']==1802
 (out/'FULL_SCORE_ARITHMETIC_REVIEW_V1.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({'status':'PASS','views':result['verified_views'],'own':result['own_offer_status'],'newpaired':40,'resources':result['resources']}))
if __name__=='__main__':main()
