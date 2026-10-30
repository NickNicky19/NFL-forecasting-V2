"""Independent streaming seasonal native/proper-score and repair replay.

No fits, model inference, source acquisition or current2026Week8 outcomes.
"""
from array import array
from collections import Counter,defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
import argparse,csv,gzip,hashlib,json,math,resource,sys,time
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'reports/continuation-20261030c'
sys.path.insert(0,str(ROOT/'reports/verification'))
from check_empirical_diagnostic import ACTION_COUNTS,ACTION_YARDS,count,num,value
TARGETS=('pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd','anytime_td','nick-chart-ppr-v1')
COUNTS={'pass_td','pass_cmp','pass_att','pass_int','rush_att','rec'}
WEIGHTS={'passing_yards':2,'passing_tds':200,'passing_interceptions':-50,'rushing_yards':5,'rushing_tds':300,'receptions':50,'receiving_yards':5,'receiving_tds':300,'fumbles_lost_total':-50,'passing_2pt_conversions':100,'rushing_2pt_conversions':100,'receiving_2pt_conversions':100}
def sha(path):
 h=hashlib.sha256()
 with path.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def close(a,b):
 if b==math.inf:assert a in('Infinity',math.inf);return
 assert(a is None and b is None)or(a is not None and b is not None and math.isclose(float(a),float(b),rel_tol=5e-10,abs_tol=5e-9)),(a,b)
def number(x):return None if x in('',None)else float(x)
def grid(x):
 y=Decimal(str(x))*50;assert y==y.to_integral_value();return int(y)
def load_truth(source,protocol,year):
 for d in protocol['source_ids']:assert sha(source/d['name'])==d['sha256']
 games={}
 with(source/'games.csv').open()as f:
  for r in csv.DictReader(f):
   if r['game_type']!='REG'or not 2022<=int(r['season'])<=year or(int(r['season'])==2026 and int(r['week'])>7):continue
   clock=datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp();hs,aws,result,total=(num(r[k])for k in('home_score','away_score','result','total'));games[r['game_id']]=dict(year=int(r['season']),week=int(r['week']),kickoff=clock,home=r['home_team'],away=r['away_team'],final=count(hs)and count(aws)and result==hs-aws and total==hs+aws)
 rows=[];lookup={}
 for season in range(2022,year+1):
  with(source/f'stats_player_week_{season}.csv').open()as f:
   for r in csv.DictReader(f):
    if r['season_type']!='REG'or int(r['season'])!=season or(season==2026 and int(r['week'])>7)or r['position']not in('QB','RB','WR','TE')or not(r['player_id'].startswith('00-')and len(r['player_id'])==10 and r['player_id'][3:].isdigit()):continue
    g=games[r['game_id']];assert(g['year'],g['week'])==(season,int(r['week']));assert(r['team'],r['opponent_team'])in((g['home'],g['away']),(g['away'],g['home']));played=any(count(num(r[k]))and num(r[k])>0 for k in ACTION_COUNTS)or any(num(r[k])not in(None,0)for k in ACTION_YARDS)
    values={t:float(v)if(v:=value(t,r))is not None else None for t in TARGETS if t!='nick-chart-ppr-v1'}if played else {t:None for t in TARGETS if t!='nick-chart-ppr-v1'}
    components={k:num(r[k])for k in WEIGHTS};chart=None
    if played and g['final']and num(r['fumble_recovery_tds'])==num(r['special_teams_tds'])==0 and all(v is not None for v in components.values())and all(count(v)for k,v in components.items()if k not in('passing_yards','rushing_yards','receiving_yards')):
     coordinate=sum(components[k]*weight for k,weight in WEIGHTS.items());assert coordinate==int(coordinate);chart=int(coordinate)
    values['nick-chart-ppr-v1']=chart
    row=dict(player_id=r['player_id'],game_id=r['game_id'],position=r['position'],season=season,week=int(r['week']),kickoff=g['kickoff'],available=g['kickoff']+7*86400,values=values);k=r['game_id'],r['player_id'];assert k not in lookup;lookup[k]=row;rows.append(row)
 return rows,lookup,games
class Stats:
 def __init__(self):
  self.errors=array('d');self.forecasts=0;self.fallbacks=Counter();self.games=set();self.qgames=set();self.weeks=set();self.precision=Counter();self.events=0.;self.logs=array('d');self.loginfinite=0;self.crps=array('d');self.nll=array('d');self.inf=0;self.width=array('d');self.covered=0;self.zero=array('d')
 def add(self,r):
  self.forecasts+=1;self.fallbacks[r['fallback']]+=1;self.qgames.add(r['game_id']);y=r['actual'];p=r['prediction']
  if y is None:return
  assert p is not None and math.isfinite(p);e=p-y;self.errors.append(e);self.games.add(r['game_id']);self.weeks.add(r['week']);a=abs(e);unit=1
  if r['target']=='nick-chart-ppr-v1'and r['product_id']=='lower_median':a=abs(grid(p)-int(r['actual_grid']));unit=50
  self.precision['exact_rate']+=a==0
  for t in(1,5,10):self.precision['abs_lt_'+str(t)]+=a<t*unit;self.precision['abs_le_'+str(t)]+=a<=t*unit
  if r['target']=='anytime_td':
   assert y in(0,1)and 0<=p<=1;self.events+=y;mass=p if y else 1-p
   if mass==0:self.loginfinite+=1
   else:self.logs.append(-math.log(mass))
  d=r['distribution_summary']
  if d:
   self.crps.append(d['crps']);self.width.append(d['interval90_width']);self.covered+=d['interval90_covered'];self.zero.append(d['zero_mass']);self.inf+=d['infinite_nll']
   if not d['infinite_nll']:self.nll.append(d['nll'])
 def result(self,target):
  n=len(self.errors);out=dict(n=n,scored_n=n,forecast_rows=self.forecasts,missing_actual_n=self.forecasts-n,fallback_rows=self.forecasts-self.fallbacks['none'],fallback_source_counts=dict(self.fallbacks),unique_games=len(self.games),forecast_games=len(self.qgames),evaluation_weeks=sorted(self.weeks),mae=None,mse=None,rmse=None,bias=None)
  if n:
   a=sorted(map(abs,self.errors));mse=math.fsum(e*e for e in self.errors)/n;q=lambda p:(lambda x:a[math.floor(x)]+(a[math.ceil(x)]-a[math.floor(x)])*(x-math.floor(x)))((n-1)*p);out.update(mae=math.fsum(a)/n,mse=mse,rmse=math.sqrt(mse),bias=math.fsum(self.errors)/n,p90_abs=q(.9),p95_abs=q(.95),max_abs=a[-1],**{k:v/n for k,v in self.precision.items()})
   if target=='anytime_td':out.update(brier=mse,prevalence=self.events/n,log_loss=math.inf if self.loginfinite else math.fsum(self.logs)/n,infinite_log_losses=self.loginfinite)
  if self.crps:
   k=len(self.crps);out.update(CRPS=math.fsum(self.crps)/k,NLL=math.inf if self.inf else math.fsum(self.nll)/k,infinite_NLL=self.inf,interval90_width=math.fsum(self.width)/k,interval90_coverage=self.covered/k,mean_zero_mass=math.fsum(self.zero)/k)
  return out
def groups_add(groups,r):
 base=tuple(r[k]for k in('procedure_id','family','target','policy_id','history_regime','product_id','population'))
 for suffix in [('ALL','ALL','ALL'),(str(r['week']),'ALL','ALL'),('ALL',r['position'],'ALL')]+([('ALL','ALL','LEARNED_ONLY')]if r['fallback']=='none'else[]):groups[base+suffix].add(r)
def score_key(s):return tuple(s[k]for k in('procedure_id','procedure_family_id','target','policy_id','history_regime','product_id','population'))+(str(s['week']),s['position'],s['fallback_view'])
def read_row(r):
 r=dict(r)
 for k in('prediction','actual','actual_grid'):r[k]=number(r[k])
 r['week']=int(r['week']);r['season']=int(r['season']);r['distribution_summary']=json.loads(r['distribution_summary'])if r['distribution_summary']else None
 return r
def verify(public,private,source,repair_public=None,repair_private=None):
 start,cpu=time.monotonic(),time.process_time();p=json.loads((public/'FROZEN_PROTOCOL.json').read_text());run=json.loads((public/'RUN_RECEIPT.json').read_text());year=p['evaluation_season'];assert sha(public/'FROZEN_PROTOCOL.json')==run['protocol_sha256'];file=private/run['private_flat']['bundle_name'];assert sha(file)==run['private_flat']['sha256'];raw,labels,games=load_truth(source,p,year);groups=defaultdict(Stats);checks=Counter();total=0;original_ra={};learner_counts=Counter()
 with gzip.open(file,'rt',newline='')as f:
  for source_index,text in enumerate(csv.DictReader(f)):
   assert int(text['season'])==year and 1<=int(text['week'])<=18;r=read_row(text);truth=labels[r['game_id'],r['player_id']];expected=truth['values'][r['target']];expected=expected/50 if expected is not None and r['target']=='nick-chart-ppr-v1'else expected;close(r['actual'],expected);assert r['position']==truth['position'];checks['raw_source_label_and_position_joins']+=2
   if r['actual']is not None and r['target']in COUNTS:assert r['actual']>=0 and int(r['actual'])==r['actual']
   if text['feature_cutoff']:assert float(text['feature_cutoff'])==truth['kickoff']
   for key in('latest_training_label_available','latest_training_feature_available','latest_feature_available'):
    if text[key]:assert float(text[key])<float(text['fit_cutoff']if key=='latest_training_label_available'else text['feature_cutoff']);checks['retained_row_chronology_checks']+=1
   if 'qb-rb-specialization'in r['procedure_id']:original_ra[r['fit_slot'],r['query_id'],r['product_id']]=(source_index,text)
   groups_add(groups,r);total+=1;learner_counts[r['family']]+=1
 scores=json.loads((public/'SCORES.json').read_text());assert len(scores)==len(groups)==run['score_views'];assert total==run['forecast_output_views'];maximum=0.
 for s in scores:
  stat=groups[score_key(s)];expected=stat.result(s['target'])
  for field,value in expected.items():
   if isinstance(value,(dict,list)):assert s[field]==value
   else:
    close(s[field],value)
    if isinstance(value,(int,float))and math.isfinite(value):maximum=max(maximum,abs(float(s[field])-value))
   checks['independent_score_fields']+=1
  for field,v in s.get('precision_counts',{}).items():assert v['numerator']==stat.precision[field]and v['denominator']==len(stat.errors);close(v['rate'],stat.precision[field]/len(stat.errors));checks['exact_precision_numerators']+=1
 repair_report=None
 if repair_public:
  rp=json.loads((repair_public/'FROZEN_PROTOCOL.json').read_text());rr=json.loads((repair_public/'RUN_RECEIPT.json').read_text());assert rp['source_prediction_sha256']==sha(file);rf=repair_private/rr['private_flat']['bundle_name'];assert sha(rf)==rr['private_flat']['sha256'];rg=defaultdict(Stats);n=changes=nonzero=0
  with gzip.open(rf,'rt',newline='')as f:
   for text in csv.DictReader(f):
    if 'qb-rb-specialization'not in text['procedure_id']:assert rr['GLM_all_zero_affected_cells']>0;continue
    old_index,old=original_ra[text['fit_slot'],text['query_id'],'absolute_error_point'];oldp=float(old['prediction']);expected=0. if old['fallback']!='none'and old['position']not in('QB','RB')else oldp;close(text['prediction'],expected);assert text['product_id']=='absolute_loss_point';assert text['source_run_id']==old['run_id']and text['source_actual_generated_at']==old['actual_generated_at']and text['source_model_artifact_id']==old['model_artifact_id'];assert text['corrected_at']==text['actual_generated_at']and datetime.fromisoformat(text['corrected_at'])>=datetime.fromisoformat(old['actual_generated_at']);assert text['prediction_version']==rr['version']and text['run_id'].startswith(rr['version']);n+=1;changes+=old['fallback']!='none'and old['position']not in('QB','RB');nonzero+=oldp!=expected;groups_add(rg,read_row(text))
  rs=json.loads((repair_public/'SCORES.json').read_text());assert len(rs)==rr['score_views']==len(rg)
  for s in rs:
   expected=rg[score_key(s)].result(s['target'])
   for field,value in expected.items():
    if isinstance(value,(dict,list)):assert s[field]==value
    else:close(s[field],value)
    checks['repaired_score_fields']+=1
  assert n==rr['forecast_rows_replayed']==rr['product_alias_rows'];assert changes==rr['changed_fallback_rows'];assert nonzero==rr['numerically_changed_predictions'];assert rr['new_fit_calls']==rr['old_models_refitted']==0
  repair_report=dict(score_views=len(rs),rows=n,changed_fallback_rows=changes,numerically_changed_predictions=nonzero,GLM_all_zero_audited_cells=rr['GLM_all_zero_audited_cells'],GLM_affected_cells=rr['GLM_all_zero_affected_cells'],new_generation_identity_and_time_checked=True,corrected_prediction_sha256=sha(rf),score_sha256=sha(repair_public/'SCORES.json'))
 return dict(status='PASS_FULL_SEASON_STREAMING_SOURCE_NATIVE_PROPER_SCORE_AND_REPAIR_REPLAY',season=year,forecast_rows=total,score_views=len(scores),unique_games=run['query_games'],unique_player_games=run['unique_player_games'],checks=dict(checks),max_float_difference=maximum,source_variant_rows=dict(learner_counts),repair=repair_report,source_score_sha256=sha(public/'SCORES.json'),source_prediction_sha256=sha(file),protocol_sha256=sha(public/'FROZEN_PROTOCOL.json'),verification_resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),scope='Everyretainedpointrow joinedrawseasonfilteredsource; everypublishednative/properaggregate andprecisionnumerator replayed. Savedlawsummaryaggregation isnotyet independentmodel/PMFreconstruction; separatecheckrequired.',evidence='Current-vintageparticipantdiagnostic; originalv1RAcontinuitygap preserved, repairedversionpreferred; no historicalpregameclaims',new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__)
 for name in('public','private','source'):a.add_argument('--'+name,type=Path,required=True)
 for name in('repair-public','repair-private'):a.add_argument('--'+name,type=Path)
 args=a.parse_args();r=verify(args.public,args.private,args.source,args.repair_public,args.repair_private);OUT.joinpath('SEASON_'+str(r['season'])+'_INDEPENDENT_SCORE_REVIEW.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
