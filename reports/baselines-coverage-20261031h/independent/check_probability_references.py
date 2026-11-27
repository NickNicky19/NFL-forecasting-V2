"""Independent source-prefix, proper-score, calibration and AUC checks; no forecasts."""
import argparse,bisect,collections,csv,gzip,hashlib,json,math,re,resource,time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

def read(p):return json.loads(p.read_bytes())
def gz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def close(a,b):
 if a is None or b is None or isinstance(a,str)or isinstance(b,str):assert a==b,(a,b)
 else:assert math.isclose(a,b,abs_tol=2e-10,rel_tol=2e-10),(a,b)
def num(x):
 try:v=float(x)
 except(TypeError,ValueError):return None
 return v if math.isfinite(v)else None
def valid(v):return v is not None and v>=0 and v==int(v)
def epoch(x):return datetime.fromisoformat(x.replace('Z','+00:00')).timestamp()
REGIONS=('over','under','push')
MAP={'pass_yd':'passing_yards','pass_td':'passing_tds','pass_cmp':'completions','pass_att':'attempts','pass_int':'passing_interceptions','rush_yd':'rushing_yards','rush_att':'carries','rec':'receptions','rec_yd':'receiving_yards'}
COUNTS={'pass_td','pass_cmp','pass_att','pass_int','rush_att','rec'}
PC=('attempts','completions','carries','targets','receptions','sacks_suffered','passing_tds','rushing_tds','receiving_tds','passing_2pt_conversions','rushing_2pt_conversions','receiving_2pt_conversions','punt_returns','kickoff_returns','def_tackles_solo','def_tackles_with_assist','def_tackle_assists','def_sacks','def_interceptions','fumble_recovery_own','fumble_recovery_opp','fg_att','pt_att')
PY=('passing_yards','rushing_yards','receiving_yards','sack_yards_lost','punt_return_yards','kickoff_return_yards','def_interception_yards','fumble_recovery_yards_own','fumble_recovery_yards_opp','misc_yards')
def losses(pp,cls):return(.5*math.fsum((pp[s]-int(s==cls))**2 for s in REGIONS),-math.log(pp[cls])if pp[cls]>0 else'Infinity')
def auc(rr,ref):
 d=collections.defaultdict(lambda:[0,0])
 for r in rr:
  pp=r[ref+'_probabilities'];mass=pp['over']+pp['under']
  if r['actual_region']!='push'and mass>0:d[pp['over']/mass][int(r['actual_region']=='over')]+=1
 pos=sum(v[1]for v in d.values());neg=sum(v[0]for v in d.values());seen=0;u=0.
 for p,(n,y)in sorted(d.items()):u+=y*(seen+n/2);seen+=n
 return(u/(pos*neg)if pos and neg else None,pos+neg)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--source',type=Path,required=True);ap.add_argument('--private',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();start=time.monotonic();pub=a.root/'reports/baselines-coverage-20261031h/probability/reference-v2';p=read(pub/'FROZEN_PROTOCOL.json');run=read(pub/'RUN_RECEIPT.json');assert sha(pub/'FROZEN_PROTOCOL.json')==run['protocol_sha256'];assert sha(pub/'SOURCE_SNAPSHOT.py')==p['code_sha256'];assert sha(pub/'SCORES.json')==run['score_sha256'];file=a.private/'baselines-coverage-20261031h-probability-reference-v2/BASELINE_AND_CACHED_LAW_ROWS.json.gz';assert sha(file)==run['private_rows_sha256'];rows=gz(file)
 for b in p['prior_source_ids']:assert sha(a.source/b['name'])==b['sha256']
 for b in p['source_members']:
  path=a.root/b['source_id']/b['member']if b['source_id'].startswith('reports/')else a.private/b['source_id']/b['member'];assert sha(path)==b['sha256']
 schedule={}
 with(a.source/'games.csv').open()as f:
  for r in csv.DictReader(f):
   if r['game_type']=='REG'and 2022<=int(r['season'])<=2026 and r['gametime']:schedule[r['game_id']]=(int(r['season']),int(r['week']),datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp(),r['home_team'],r['away_team'],r['home_score'],r['away_score'])
 history=collections.defaultdict(list);counts=collections.Counter();seen=set()
 for year in range(2022,2027):
  with(a.source/f'stats_player_week_{year}.csv').open()as f:
   for r in csv.DictReader(f):
    if r['season_type']!='REG'or(year==2026 and int(r['week'])>7)or r['position']not in('QB','RB','WR','TE')or re.fullmatch(r'00-\d{7}',r['player_id'])is None:continue
    g=schedule[r['game_id']];assert g[:2]==(year,int(r['week']))and(r['team'],r['opponent_team'])in((g[3],g[4]),(g[4],g[3]));identity=(r['game_id'],r['player_id']);assert identity not in seen;seen.add(identity);v={k:num(r[k])for k in set(PC+PY+tuple(MAP.values()))};played=any(valid(v[k])and v[k]>0 for k in PC)or any(v[k]is not None and v[k]!=0 for k in PY);counts['verified_played'if played else'participation_unknown']+=1
    if not played:continue
    assert g[5]not in('',None)and g[6]not in('',None),'prior physical record from nonfinal/cancelled schedule'
    for target in list(MAP)+['rush_rec_yd']:
     if target.startswith('pass_')and r['position']!='QB':continue
     y=(v['rushing_yards']+v['receiving_yards'])if target=='rush_rec_yd'and v['rushing_yards']is not None and v['receiving_yards']is not None else None if target=='rush_rec_yd'else v[MAP[target]]
     if y is None or(target in COUNTS and not valid(y)):continue
     assert y==int(y),'NFL native target expected integer support';history[target,r['position']].append((year,g[2]+604800,y,identity))
 assert dict(counts)==run['prior_source_qualification']
 original={}
 for week in(6,7):
  for leaf in(False,True):
   name=f'completion-20261031g-w{week}-'+('complete-leaf-law-v1'if leaf else'rolling-method-comparison-v1');path=a.private/name;f=gz(path/('FROZEN_LAW_DIRECTIONS_K.json.gz'if leaf else'FROZEN_SELECTIONS_AND_K.json.gz'));g=gz(path/('GRADED_COMPLETE_LEAF_LAWS.json.gz'if leaf else'GRADED_METHOD_ROWS.json.gz'));specs={x['method_id']:x for x in p['roster']if x['week']==week and x['source_type']==('complete_leaf'if leaf else'full_parametric')}
   for tag,s in specs.items():
    for r in g['graded'][tag]:
     if r['admitted']and r['actual']is not None and r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL':original[week,s['target'],s['procedure_id'],s['history_regime'],r['source_row_index']]=(r,leaf)
 prefix={};by=collections.defaultdict(list);constant_pushes=0
 for r in rows:
  key=(r['week'],r['target'],r['procedure_id'],r['history_regime'],r['source_row_index']);o,leaf=original.pop(key);assert(r['game'],r['player'],r['position'],r['actual'],r['line'])==(o['game_id'],o['player_id'],o['position'],o['actual'],float(o['line']));assert r['decision_time']==o.get('source_server_clock',o.get('server_retained_by'));assert r['strict_current_information']==('strict'in r['procedure_id']);origin=('PRIOR'if o['source']=='REUSED_ELIGIBLE_FALLBACK_LAW'else'LEARNED')if leaf else('PRIOR'if o.get('fallback')not in(None,'none')else'LEARNED');assert r['origin']==origin;cls='over'if r['actual']>r['line']else'under'if r['actual']<r['line']else'push';assert r['actual_region']==cls;floor=2026 if r['strict_current_information']or r['history_regime']=='H-CURRENT'else 2025 if r['history_regime']=='H-RECENT'else 2022;pk=(r['target'],r['position'],r['decision_time'],floor)
  if pk not in prefix:
   pp=[x for x in history[r['target'],r['position']]if x[0]>=floor and x[1]<epoch(r['decision_time'])];freq=collections.Counter(x[2]for x in pp);membership=hashlib.sha256(canon(sorted(x[3]for x in pp))).hexdigest();prefix[pk]=(pp,freq,membership)
  pp,freq,membership=prefix[pk];n=len(pp);assert n==r['baseline_prior_n']and membership==r['baseline_prior_membership_sha256'];assert r['baseline_prior_earliest']==min((x[1]for x in pp),default=None)and r['baseline_prior_latest']==max((x[1]for x in pp),default=None);assert all(x[3]!=(r['game'],r['player'])for x in pp);b1=dict(over=sum(c for y,c in freq.items()if y>r['line'])/n,under=sum(c for y,c in freq.items()if y<r['line'])/n,push=freq.get(r['line'],0)/n)if n else dict(over=.5,under=.5,push=0.);assert r['baseline_origin']==('EARLIER_EMPIRICAL'if n else'EMPTY_PREFIX_CONSTANT_HALF')
  for ref,expected in[('candidate',o['probabilities']),('B0',dict(over=.5,under=.5,push=0.)),('B1',b1)]:
   for s in REGIONS:close(r[ref+'_probabilities'][s],expected[s])
   close(sum(expected.values()),1.);b,ll=losses(expected,cls);close(r[ref+'_brier'],b);close(r[ref+'_log_loss'],ll)
  close(r['B0_brier'],.75 if cls=='push'else.25);constant_pushes+=cls=='push';by[r['target'],r['procedure_id'],r['history_regime']].append(r)
 assert not original and len(rows)==run['cached_recipe_offer_rows']==14280
 masks={};scores=read(pub/'SCORES.json');scoreby={}
 for s in scores:
  rr=[r for r in by[s['target'],s['matched_candidate_procedure_id'],s['history_regime']]if r['week']in s['evaluation_weeks']];rr=sorted(rr,key=lambda r:(r['week'],r['source_row_index']));full=len(rr);rr=[r for r in rr if s['fallback_view']=='FULL'or r['origin']==s['fallback_view']];n=len(rr);ref=s['reference_id'];mask=hashlib.sha256(canon([[r['week'],r['source_row_index'],r['game'],r['player'],r['target'],r['line'],r['actual']]for r in rr])).hexdigest();assert s['n']==n and s['forecast_rows']==full and s['membership_sha256']==mask;ll=[r[ref+'_log_loss']for r in rr];inf=ll.count('Infinity');close(s['brier'],math.fsum(r[ref+'_brier']for r in rr)/n if n else None);close(s['log_loss'],'Infinity'if inf else math.fsum(ll)/n if n else None);assert s['infinite_log_losses']==inf and s['candidate_prior_rows']==sum(r['origin']=='PRIOR'for r in rr);assert s['baseline_empty_prefix_rows']==sum(r['baseline_origin']=='EMPTY_PREFIX_CONSTANT_HALF'for r in rr);assert s['null_reason']==(None if n else'NO_ROWS_IN_FROZEN_CANDIDATE_ORIGIN_PARTITION');masks[s['record_id']]=rr;scoreby[s['record_id']]=s
 diagnostics=read(pub/'CALIBRATION_AND_DISCRIMINATION.json')
 for d in diagnostics:
  s=scoreby[d['record_id']];rr=masks[d['record_id']];ref=s['reference_id'];bins=collections.defaultdict(list)
  for r in rr:
   for region in REGIONS:prob=r[ref+'_probabilities'][region];bins[region,min(9,math.floor(prob*10))].append((prob,int(r['actual_region']==region)))
  assert len(d['calibration_bins'])==len(bins)
  for b in d['calibration_bins']:
   vals=bins[b['region'],b['bin']];assert b['n']==len(vals);close(b['mean_probability'],math.fsum(v[0]for v in vals)/len(vals));close(b['actual_frequency'],math.fsum(v[1]for v in vals)/len(vals));close(b['signed_calibration_error'],b['mean_probability']-b['actual_frequency'])
  ac,an=auc(rr,ref);close(d['decisive_over_auc'],ac);assert d['decisive_auc_n']==an
 contrasts=read(pub/'PAIRED_REFERENCE_COMPARISONS.json');nonfinite=empty=0
 for c in contrasts:
  rr=sorted([r for r in by[c['target'],c['procedure_id'],c['history_regime']]if r['week']in c['evaluation_weeks']and(c['fallback_view']=='FULL'or r['origin']==c['fallback_view'])],key=lambda r:(r['week'],r['source_row_index']));n=len(rr);assert c['n']==n;ref='B0'if c['comparator'].startswith('B0')else'B1';metric=c['metric'];x=[r['candidate_'+metric]for r in rr];y=[r[ref+'_'+metric]for r in rr]
  if not n:assert c['status']=='NO_SUPPORTED_PAIRED_ROWS'and c['delta']is None;empty+=1;continue
  ci=x.count('Infinity');bi=y.count('Infinity');assert c['candidate_infinite_rows']==ci and c['comparator_infinite_rows']==bi;close(c['candidate_error'],'Infinity'if ci else math.fsum(x)/n);close(c['comparator_error'],'Infinity'if bi else math.fsum(y)/n)
  if ci or bi:assert c['status']=='NONFINITE_LOSS_DIFFERENCE_UNDEFINED'and c['delta']is None;nonfinite+=1;continue
  dif=[u-v for u,v in zip(x,y)];delta=math.fsum(dif)/n;close(c['delta'],delta);close(c['relative_error_change'],delta/(math.fsum(y)/n)if math.fsum(y)else None);gg=collections.defaultdict(list)
  for r,v in zip(rr,dif):gg[r['game']].append(v)
  G=len(gg);se=math.sqrt(G/(G-1)*math.fsum((math.fsum(v)-delta*len(v))**2 for v in gg.values()))/n if G>=8 else None;close(c['game_cluster_sensitivity_se'],se)
  if se is None:assert c['game_normal95_sensitivity']is None
  else:
   for aa,bb in zip(c['game_normal95_sensitivity'],[delta-1.96*se,delta+1.96*se]):close(aa,bb)
  assert c['week_interval']is None and c['week_interval_status']=='INSUFFICIENT_WEEK_CLUSTERS'
 assert len(scores)==3726 and len(contrasts)==4968 and len(diagnostics)==len(scores)
 examples=[]
 for s in scores:
  if s['target']=='pass_att'and s['reference_id']=='candidate'and s['fallback_view']=='FULL'and s['evaluation_weeks']==[6,7]and'ordered_leaf_cdf'in s['procedure_id']and(s['history_regime']=='H-MULTI'or s['strict_current_information']):examples.append(dict(procedure_id=s['procedure_id'],history_regime=s['history_regime'],strict=s['strict_current_information'],n=s['n'],brier=s['brier'],neutral=.25,delta_from_neutral=s['brier']-.25))
 out=dict(state='PASS_INDEPENDENT_EARLIER_PREFIX_PROBABILITY_REFERENCES_SCORES_AND_DIAGNOSTICS',protocol_sha256=run['protocol_sha256'],scores_sha256=run['score_sha256'],cached_recipe_offer_rows=len(rows),unique_prefix_memberships=len(prefix),source_prior_participation_counts=dict(counts),score_views=len(scores),paired_contrasts=len(contrasts),calibration_AUC_views=len(diagnostics),retained_nonfinite_comparisons=nonfinite,empty_comparisons=empty,actual_push_rows=constant_pushes,passing_attempt_examples=examples,new_fits=0,new_inference=0,new_forecasts=0,new_grades=0,resources=dict(wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),limits=['FULL is the complete qualified candidate lossmask, not entire sourceoffercoverage; outercoverage supplement separate.','Earlier sourceavailability uses inherited7day/currentvintage policy, not authenticated historicalpublication.','Diagnostics use exposed outcomes descriptively; no calibrationparameters or selectedstrategy fitted.'])
 with a.output.open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps(out))
if __name__=='__main__':main()
