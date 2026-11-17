"""Independent retained-row calculations; no executor/scorer/model imports."""
import argparse,collections,csv,datetime,gzip,hashlib,json,math,re,sys,time
from decimal import Decimal
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canon(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def stamp(x):return datetime.datetime.fromisoformat(x.replace('Z','+00:00'))
def eq(a,b):
 if a is None or b is None:assert a is b,(a,b)
 elif isinstance(a,str)or isinstance(b,str):assert str(a)==str(b),(a,b)
 else:assert math.isclose(a,b,rel_tol=2e-12,abs_tol=3e-10),(a,b)
def stream(p):
 with gzip.open(p,'rt')as f:
  buf='';dec=json.JSONDecoder();started=False
  while True:
   chunk=f.read(65536);buf+=chunk
   if not started:
    pos=buf.find('[')
    if pos<0:continue
    buf=buf[pos+1:];started=True
   while True:
    buf=buf.lstrip(' \n\r\t,')
    if buf.startswith(']'):return
    try:r,n=dec.raw_decode(buf)
    except json.JSONDecodeError:break
    yield r;buf=buf[n:]
   if not chunk:raise AssertionError('truncated rows')
def key(r):return r['game_id'],r.get('player_id')or r.get('source_player_id'),r['target']
def gid(r):return tuple(r[k]for k in('capture_version','procedure_id','history_regime','product_id','information_policy','availability_arm','target'))
def mid(g):return hashlib.sha256(canon(g)).hexdigest()[:24]
def countside(rr,score):
 pool=rr;side=score['side'];picked=[r for r in pool if r['selected_side']and(side=='Combined'or r['selected_side']==side)]
 counts=collections.Counter(r['statistical_state']for r in picked);sm=score['selection_metrics'];n=counts['WIN']+counts['LOSS']
 assert score['n']==n and score['forecast_rows']==len(picked)
 for k,v in sm['status_counts'].items():assert counts[k]==v,(k,counts[k],v)
 eq(sm['hit_rate'],counts['WIN']/n if n else None);eq(sm['selection_coverage'],len(picked)/len(pool)if pool else None)
 assert sm['selection_pool_count']==len(pool) and sm['abstentions_outside_selected_partition']==sum(not r['selected_side']for r in pool)
 assert score['unique_games']==len({r['game_id']for r in picked})
 assert score['query_membership_sha256']==hashlib.sha256(canon(sorted(r['source_row_index']for r in picked))).hexdigest()
 assert sm['returns']['net']is None and sm['returns']['ROI']is None
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--private-root',type=Path,required=True);a=ap.parse_args();priv=a.private_root;pub=HERE.parent;start=time.monotonic()
 binding=read(priv/'LOCAL_INPUT_BINDINGS_V1.json');schedule=read(pub/'FROZEN_SOURCE_ASSIGNMENTS_V1.json')['assignments'];games={r['game_id']:r for r in schedule}
 stats={(r['game_id'],r['player_id']):r for r in csv.DictReader((priv/'source-labels/fresh-player-stats-2026.csv').open())if(r['season'],r['week'],r['season_type'])==('2026','8','REG')}
 ev={e['id']:e for e in read(priv/'source-labels/espn-week8-scoreboard-v2.json')['events']};rawgames={r['game_id']:r for r in csv.DictReader((priv/'source-labels/fresh-games.csv').open())if(r['season'],r['week'],r['game_type'])==('2026','8','REG')}
 final={g:ev[r['espn']]['status']['type']['completed']for g,r in rawgames.items()}
 fw=collections.defaultdict(set);rv=collections.defaultdict(set)
 with gzip.open(binding['identity_roster'],'rt')as f:
  for r in csv.DictReader(f):
   if r['season']=='2026'and int(r['week'])<=8 and r['sleeper_id']and r['gsis_id']:fw[r['sleeper_id']].add(r['gsis_id']);rv[r['gsis_id']].add(r['sleeper_id'])
 bridge={k:next(iter(v))for k,v in fw.items()if len(v)==1 and len(rv[next(iter(v))])==1}
 fields={'pass_yd':'passing_yards','pass_td':'passing_tds','pass_cmp':'completions','pass_att':'attempts','pass_int':'passing_interceptions','rush_yd':'rushing_yards','rush_att':'carries','rec':'receptions','rec_yd':'receiving_yards'}
 def number(v):
  try:return Decimal(str(v))if v not in('',None)else None
  except:return None
 cache={}
 def label(k):
  if k in cache:return cache[k]
  g,p,t=k
  if not final[g]:out=(None,'pending')
  else:
   r=stats.get((g,p));physical=r is not None and any((number(r.get(f))or 0)>0 for f in('attempts','carries','targets','receptions','punt_returns','kickoff_returns'))
   if not physical:out=(None,'final')
   else:
    def val(f):return number(r.get(f))
    if t in fields:v=val(fields[t])
    elif t in('rush_rec_yd','anytime_td'):
     ff=('rushing_yards','receiving_yards')if t=='rush_rec_yd'else('rushing_tds','receiving_tds');vv=[val(f)for f in ff];v=None if None in vv else sum(vv)
     if v is not None and t=='anytime_td':v=Decimal(int(v>=1))
    else:
     ww={'passing_yards':2,'passing_tds':200,'passing_interceptions':-50,'rushing_yards':5,'rushing_tds':300,'receptions':50,'receiving_yards':5,'receiving_tds':300,'fumbles_lost_total':-50,'passing_2pt_conversions':100,'rushing_2pt_conversions':100,'receiving_2pt_conversions':100}
     vv={f:val(f)for f in ww};v=None if any(z is None for z in vv.values())or val('fumble_recovery_tds')!=0 or val('special_teams_tds')!=0 else sum(ww[f]*z for f,z in vv.items())/50
    out=(float(v)if v is not None else None,'final')
  cache[k]=out;return out
 # Compact independent row representation: key,point,actual,error,issued,T90,pregame,pending,fallback.
 groups=collections.defaultdict(list);mapping={};total=0;labelchecks=0;zeros=0
 for r in stream(priv/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz'):
  total+=1;g=gid(r);m=mid(g);mapping[m]=g;k=key(r);assert r['player_id']is None or re.fullmatch(r'00-\d{7}',r['player_id']);expected=bridge.get(str(r['source_player_id']),str(r['source_player_id']))
  if not re.fullmatch(r'00-\d{7}',str(r['source_player_id'])) and r['player_id']is not None:assert expected==r['player_id']
  y,state=label(k);eq(r['actual'],y);assert state==r['outcome_state'];labelchecks+=1
  kick=stamp(games[k[0]]['kickoff_utc']);pre=stamp(r['issued_at_utc'])<kick and stamp(r['persistence_completed_at'])<kick;t90=pre and max(stamp(r['issued_at_utc']),stamp(r['persistence_completed_at']))<=kick-datetime.timedelta(minutes=90)
  assert r['pregame_retention_eligible']==pre and r['T90_eligible']==t90
  expected_error=r['prediction']-y if r['original_forecast_issued']and pre and r['label_state']=='SUPPORTED'else None;eq(r['error'],expected_error)
  if r['error']is not None:assert y is not None;zeros+=y==0
  groups[m].append((k,r['prediction'],y,r['error'],r['original_forecast_issued'],t90,pre,state=='pending',r['fallback']))
 assert total==277562
 for m,rr in groups.items():assert len({r[0]for r in rr})==len(rr)
 primary=set(read(pub/'captured-library-v2/COMMON_PANEL_DEFINITION.json')['primary_captures']);oldsets=collections.defaultdict(list);newsets=collections.defaultdict(list);excluded=[]
 for m,rr in groups.items():
  if mapping[m][0]not in primary:continue
  keys={r[0]for r in rr if r[3]is not None and r[5]};oldsets[mapping[m][-1]].append(keys)
  if any(r[4]and r[5]for r in rr):newsets[mapping[m][-1]].append(keys)
  else:excluded.append(m)
 common={t:set.intersection(*v)for t,v in newsets.items()};old={t:set.intersection(*v)for t,v in oldsets.items()}
 scope=read(pub/'comparable-products-v3/FROZEN_COMPARISON_SCOPE_V3.json');assert scope['common_final_rows']=={t:len(v)for t,v in common.items()};assert set(excluded)=={r['method_key']for r in scope['scope_exclusions']}
 nchecks=0
 for dirname in('captured-library-v2','comparable-products-v3'):
  for s in read(pub/dirname/'SCORES.json'):
   m=s['method_key'];rr=groups[m];g=mapping[m];panel=s['horizon_id']
   if panel=='OWN_CAPTURE_T90_SYSTEM':rr=[r for r in rr if r[5]or not r[4]]
   elif panel=='PRIMARY_ALL_METHOD_COMMON_FINAL_ROWS':rr=[r for r in rr if r[5]and r[0]in old[g[-1]]]
   elif panel=='ALL_ISSUED_COMPATIBLE_METHOD_COMMON_FINAL_ROWS_V3':rr=[r for r in rr if r[5]and r[0]in common[g[-1]]]
   else:assert panel=='OWN_CAPTURE_FULL_SYSTEM',panel
   good=[r for r in rr if r[3]is not None];e=[r[3]for r in good];ab=list(map(abs,e));n=len(good)
   assert s['n']==s['scored_forecast_rows']==n and s['forecast_rows']==len(rr)and s['issued_forecast_rows']==sum(r[4]for r in rr)
   assert s['pending_rows']==sum(r[7]for r in rr)and s['abstention_rows']==sum(not r[4]for r in rr)
   assert s['scored_key_sha256']==hashlib.sha256(canon(sorted(r[0]for r in good))).hexdigest()
   for field,calc in [('mae',sum(ab)/n if n else None),('mse',sum(z*z for z in e)/n if n else None),('bias',sum(e)/n if n else None),('rmse',math.sqrt(sum(z*z for z in e)/n)if n else None)]:eq(s[field],calc)
   if n:
    for f,v in [('p90_abs',np.quantile(ab,.9)),('p95_abs',np.quantile(ab,.95)),('max_abs',max(ab)),('exact_rate',sum(z==0 for z in ab)/n)]:eq(s[f],v)
    for name,c in s['precision_counts'].items():
     tol=int(name.rsplit('_',1)[1]);errors=[abs(Decimal(str(r[1]))*50-Decimal(str(r[2]))*50)/50 for r in good]if g[-1]=='nick-chart-ppr-v1'and g[3]=='lower_median'else ab
     num=sum(z<tol if '_lt_'in name else z<=tol for z in errors);assert(c['numerator'],c['denominator'])==(num,n),(name,c,num,n);eq(s[name],num/n)
    if g[-1]=='anytime_td':eq(s['brier'],sum(z*z for z in e)/n);loss=[-math.log(r[1]if r[2]else 1-r[1])if(r[1]if r[2]else 1-r[1])>0 else math.inf for r in good];eq(s['log_loss'],'Infinity'if math.inf in loss else sum(loss)/n)
   nchecks+=1
 offers={key(r):r for r in stream(priv/'ORIGINAL_JOINED_ROWS_V1.json.gz')if r['panel']=='ORIGINAL_PROVIDER_T90'}
 p1=collections.defaultdict(list);pchecks=0;example={}
 for r in stream(priv/'CAPTURED_LIBRARY_P1_ROWS_V1.json.gz'):
  m=r['method_key'];k=key(r);source=next(z for z in groups[m]if z[0]==k);offer=offers[k];assert source[4]and source[5];eq(r['prediction'],source[1]);eq(r['line'],offer['line']);eq(r['actual'],source[2]);assert r['source_head']==offer['source_head']
  side='over'if Decimal(str(source[1]))>Decimal(str(r['line']))else'under'if Decimal(str(source[1]))<Decimal(str(r['line']))else None
  assert r['selected_side']==side;state=verify_state(r,side);assert state==r['statistical_state'];p1[m].append(r);pchecks+=1
  if state in('WIN','LOSS')and state not in example:example[state]=r
 for dirname in('captured-library-v2','comparable-products-v3'):
  for s in read(pub/dirname/'SELECTION_SCORES.json'):
   rr=p1[s['method_key']]
   if dirname=='comparable-products-v3':rr=[r for r in rr if key(r)in common[r['target']]]
   countside(rr,s)
 pairs=read(pub/'checkpoint-summary-v1/LEADERS_VS_ADAPTIVE_ON_FIXED_COMMON_MASK_V2.json')
 for s in pairs:
  ca={r[0]:r for r in groups[s['candidate_method_key']]if r[0]in common[s['target']]};co={r[0]:r for r in groups[s['incumbent_method_key']]if r[0]in common[s['target']]};assert set(ca)==set(co)and len(ca)==s['n']
  f=(lambda r:r[3]**2)if s['metric']=='Brier'else(lambda r:abs(r[3]));a1=sum(map(f,ca.values()))/len(ca);b1=sum(map(f,co.values()))/len(co);eq(a1,s['candidate_error']);eq(b1,s['comparator_error']);eq(a1-b1,s['delta'])
 # Original complete laws: independently check all complements, chosen sides and proper losses.
 laws=collections.defaultdict(list);lawcount=0
 for r in stream(priv/'WEEK8_ORIGINAL_LAW_THRESHOLD_ROWS_V1.json.gz'):
  p=r['probabilities'];pr=r['prior_probabilities'];assert set(p)==set(pr)=={'over','under','push'}
  for vector in(p,pr):assert all(0<=x<=1 for x in vector.values());eq(sum(vector.values()),1.);assert vector['push']==0 if Decimal(str(r['line']))%1 else True
  side='over'if p['over']>p['under']else'under'if p['under']>p['over']else None;assert side==r['selected_side']and verify_state(r,side)==r['statistical_state'];offer=offers[key(r)];eq(r['line'],offer['line']);eq(r['actual'],offer['actual']);assert r['source_head']==offer['source_head'];laws[r['method_key']].append(r);lawcount+=1
 for s in read(pub/'saved-laws-v2/SCORES.json'):
  rr=laws[s['method_key']];good=[r for r in rr if r['outcome_state']=='final'and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'and r['actual']is not None]
  if s['evaluation_panel_id'].endswith(':HALF_POINT_NO_PUSH'):good=[r for r in good if Decimal(str(r['line']))%1]
  assert len(good)==s['n'];bs=[];ll=[]
  for r in good:
   y='over'if Decimal(str(r['actual']))>Decimal(str(r['line']))else'under'if Decimal(str(r['actual']))<Decimal(str(r['line']))else'push';p=r['probabilities']if s['reference']=='FOOTBALL_ORIGINAL_LAW'else r['prior_probabilities']if s['reference']=='EARLIER_FIT_ROLE_PRIOR'else{'over':.5,'under':.5,'push':0}
   bs.append(sum((v-int(k==y))**2 for k,v in p.items())/2);ll.append(-math.log(p[y])if p[y]>0 else math.inf)
  eq(s['brier'],sum(bs)/len(bs)if bs else None);eq(s['log_loss'],('Infinity'if math.inf in ll else sum(ll)/len(ll))if ll else None);assert s['infinite_log_losses']==sum(z==math.inf for z in ll)
 for s in read(pub/'saved-laws-v2/SELECTION_SCORES.json'):countside(laws[s['method_key']],s)
 # V2 law row change must be solely point metadata and equal the already-saved original mean.
 correction=read(pub/'saved-laws-v2/PRIVATE_ROW_METADATA_CORRECTION_V2.json');v2=priv/'WEEK8_ORIGINAL_LAW_THRESHOLD_ROWS_V2.json.gz';assert sha(v2)==correction['sha256']
 changed=0
 for oldr,newr in zip(stream(priv/'WEEK8_ORIGINAL_LAW_THRESHOLD_ROWS_V1.json.gz'),stream(v2)):
  oo=dict(oldr);nn=dict(newr);op=oo.pop('prediction');np1=nn.pop('prediction');oo.pop('raw_prediction');assert nn.pop('raw_prediction') is None;assert nn.pop('original_point_product')=='SAVED_ORIGINAL_MEAN_VIEW_OF_THIS_LAW';assert oo==nn
  source=[m for m,g in mapping.items()if g[0]==newr['capture_version']and g[1]==newr['procedure_id']and g[2]==newr['history_regime']and g[3]=='mean'and g[-1]==newr['target']];assert len(source)==1
  raw=next(z for z in groups[source[0]]if z[0]==key(newr));eq(np1,raw[1]);changed+=op!=np1
 def binding(path):return {'path':str(path.relative_to(pub.parent.parent)),'sha256':sha(path)}
 examples=priv/'independent-verification'/'LIBRARY_WIN_LOSS_WITNESSES_V1.json';examples.parent.mkdir(exist_ok=True);examples.write_text(json.dumps(example,indent=2)+'\n')
 out={'state':'PASS_INDEPENDENT_SAVED_LIBRARY_COMMON_MASK_AND_COMPLETE_LAW_CALCULATIONS','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checker_sha256':sha(__file__),'seconds':time.monotonic()-start,'numeric_rows_label_identity_clock_error_checks':labelchecks,'numeric_score_views_checked':nchecks,'P1_rows_checked':pchecks,'P1_side_views_checked':4428+4044,'law_offer_rows_checked':lawcount,'law_probability_views_checked':1400,'P2_side_views_checked':840,'fixed_common_incumbent_pairs_checked':len(pairs),'common_final_rows':{t:len(v)for t,v in common.items()},'outcome_blind_nonissued_product_exclusions':len(excluded),'played_zero_numeric_views_retained':zeros,'law_point_metadata_only_rows_changed':changed,'private_worked_examples_sha256':sha(examples),'private_example_retention':'LOCAL_ONLY_VERIFICATION_CACHE','scope':'Independent raw NFLverse/current-vintage label and identity joins, exact crossing, point metrics/precision, final/pending clocks, side partitions and probability losses from retained vectors. No fit, model inference or new forecast. Saved-law estimator-guard/model-summary provenance reviewed separately; this receipt does not independently execute model reconstruction. Statistical crossing only; no book settlement, prices, profitability or release admission.','bindings':[binding(pub/d/f)for d,f in [('captured-library-v2','SCORES.json'),('captured-library-v2','SELECTION_SCORES.json'),('comparable-products-v3','SCORES.json'),('comparable-products-v3','SELECTION_SCORES.json'),('saved-laws-v2','SCORES.json'),('saved-laws-v2','SELECTION_SCORES.json')]]}
 dest=HERE/'SAVED_LIBRARY_COMMON_AND_LAW_CALCULATION_REVIEW_V1.json';dest.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in('state','numeric_rows_label_identity_clock_error_checks','numeric_score_views_checked','P1_rows_checked','law_offer_rows_checked','seconds')}))
def verify_state(r,side):
 if side is None:return'ABSTAIN'
 if r['outcome_state']=='pending':return'PENDING'
 if r['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL':return'UNKNOWN_PARTICIPATION'
 if r['actual']is None:return'MISSING_ACTUAL'
 y,L=Decimal(str(r['actual'])),Decimal(str(r['line']))
 return'PUSH'if y==L else'WIN'if(y>L)==(side=='over')else'LOSS'
if __name__=='__main__':main()
