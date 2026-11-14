"""B-owned independent A public arithmetic and source-contract fixtures.

No author scorer, fit, model deserialize, raw/private transfer or NFL regrade.
Synthetic play fixtures verify meaning of the public feature code only.
"""
import argparse,collections,gzip,hashlib,importlib.util,json,math
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd

def read(p):
 b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--cache',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();base=a.cache/'reports/abc-championship/player-context-matchup-01'
 manifest=read(base/'PUBLIC_AGGREGATE_MANIFEST_V1.json');restored=[]
 for r in manifest['artifacts']:
  b=(base/r['path']).read_bytes();expanded=gzip.decompress(b)
  assert len(b)==r['bytes']and hashlib.sha256(b).hexdigest()==r['sha256']
  assert len(expanded)==r['uncompressed_bytes']and hashlib.sha256(expanded).hexdigest()==r['uncompressed_sha256']
  restored.append(dict(path=r['path'],stored_bytes=len(b),expanded_bytes=len(expanded),sha256=r['sha256']))
 actual=read(base/'completion-v4/ACTUAL_LINE_RESULTS_V1.json.gz');num=read(base/'completion-v4/NUMERICAL_RESULTS_V1.json.gz')['scores'];source=read(base/'SOURCE_PANEL_RESULTS_V1.json.gz')['scores']
 sidechecks=0
 def check(r):
  nonlocal sidechecks
  sides=[r[x]for x in('OVER','UNDER','COMBINED')]
  for s in sides:
   w,l=(s[k]or 0 for k in('wins','losses'));assert s['decided']==w+l
   assert s['rate']is None if not w+l else math.isclose(s['rate'],w/(w+l),abs_tol=1e-14)
   sidechecks+=1
  for key in('wins','losses','decided','selected'):
   assert(sides[2][key]or 0)==sum(s[key]or 0 for s in sides[:2])
  assert sum(r['states'].values())==r['eligible']
  assert r['COMBINED']['selected']+r['abstentions']+r['unavailable']==r['eligible']
  return True
 for r in actual['scores']+source:check(r)
 weekly=collections.defaultdict(dict)
 for r in actual['scores']:weekly[r['arm'],r['policy']][r['week']]=r
 for rr in weekly.values():
  allr=rr['ALL'];wk=[rr[w]for w in range(1,8)]
  for side in('OVER','UNDER','COMBINED'):
   for k in('selected','wins','losses','decided'):assert(allr[side][k]or 0)==sum(r[side][k]or 0 for r in wk)
 for r in num:
  if r['unsupported_product_rows']:
   assert r['unsupported_product_rows']==r['expected'] and r['scored']==0
  else:assert r['scored']+r['unknown_or_missing']==r['expected']
  if r['scored']:
   assert abs(r['RMSE']**2-r['MSE'])<1e-10
   assert r['MAE']+1e-12>=abs(r['bias'])
 population=[r for r in num if r['week']=='ALL'and r['product']=='mean'and r['arm']=='E1_OWN_CONTEXT'][0]
 partial=weekly['P2_PARTIAL_PLAYER_TEAM_RIDGE','P1_OTHER_POINT']['ALL'];over=weekly['ALWAYS_OVER','CONSTANT']['ALL'];assert partial['COMBINED']['wins']==119 and over['COMBINED']['wins']==122
 assert partial['COMBINED']['decided']==231
 # Independent source decomposition, not a paired-membership reproduction.
 p2=[r for r in source if r['arm']=='P2_PARTIAL_PLAYER_TEAM_RIDGE'and r['policy']=='P1_OTHER_POINT']
 assert next(r for r in p2 if r['panel']=='ANNUAL_NJ_W1_5')['COMBINED']['wins']==85
 assert next(r for r in p2 if r['panel']=='SITE_RECORDED_DK_W6_7')['COMBINED']['wins']==34
 # Use the exact public source-feature implementation on fictional eligible plays.
 modpath=a.cache/'nfl_lab/abc_player_rushing_context_v1.py';spec=importlib.util.spec_from_file_location('public_A_context',modpath);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
 frames=[];hist=[]
 for gi in range(3):
  kick=pd.Timestamp('2024-01-01T18:00:00Z')+pd.Timedelta(days=14*gi);gid='FICTIONAL_'+str(gi);raw=[]
  plays=[('R',1,-2,'left','end',1,'run',0,0,-.2),('R',1,0,None,None,2,'run',0,0,.05),('Q',1,5,'right','tackle',3,'run',0,1,.1),('Q',1,-1,'middle',None,4,'qb_kneel',1,0,-.1),(None,0,0,None,None,1,'pass',0,0,0),(None,0,0,None,None,2,'pass',0,0,0),(None,0,0,None,None,1,'no_play',0,0,0)]
  for pi,(player,attempt,y,loc,gap,down,ptype,kneel,scramble,epa)in enumerate(plays):
   raw.append(dict(season=2024,season_type='REG',week=gi+1,game_id=gid,play_id=pi,posteam='AA',defteam='BB',rusher_player_id=player,rush_attempt=attempt,rushing_yards=y,run_location=loc,run_gap=gap,down=down,ydstogo=3,yardline_100=50,qb_kneel=kneel,qb_scramble=scramble,qb_spike=0,two_point_attempt=0,penalty=0,play_type=ptype,first_down_rush=int(y>=3),epa=epa,success=int(epa>0),pass_attempt=int(ptype in('pass','no_play'))))
  frames.append(pd.DataFrame(raw))
  for player,pos,n,state in [('R','RB',2,'played'),('Q','QB',2,'played'),('Z','RB',0,'played'),('U','RB',np.nan,'unknown')]:
   hist.append(dict(game_id=gid,player_id=player,team='AA',opponent='BB',position=pos,kickoff_utc=kick,outcome_available_utc=kick+pd.Timedelta(days=7),participation_state=state,rush_att=n))
 h=pd.DataFrame(hist);context=mod.Context(frames,h);cut=pd.Timestamp('2024-03-15T18:00:00Z');f,clock=context.features('R','AA','BB',cut,window=4)
 assert f['f_pcm_team_run_rate']==4/6
 assert f['f_pcm_down_1']!=f['f_pcm_team_run_down1']
 assert f['f_pcm_team_run_down1']==.5 and f['f_pcm_player_given_run_down1']==1.
 assert f['f_pcm_nonpositive']==1. and f['f_pcm_firstdown']==0. and f['f_pcm_epapos']==.5
 assert f['f_pcm_location_UNKNOWN']>0
 assert len(context.players['Z'])==3 and all(r['attempts']==0 for r in context.players['Z'])
 assert not context.players.get('U')
 # Query needs no target outcome or availability field; target/future plays cannot revise it.
 q=pd.DataFrame([dict(game_id='UPCOMING',player_id='R',team='AA',opponent='BB',cutoff_utc=cut,feature_max_source_available_utc=cut-pd.Timedelta(days=1))])
 aug=context.augment(q,window=4);assert len(aug)==1
 future=frames[-1].copy();future['game_id']='FUTURE';future['play_id']+=100;future['rushing_yards']=999;hf=h[h.game_id.eq('FICTIONAL_2')].copy();hf['game_id']='FUTURE';hf['kickoff_utc']=cut+pd.Timedelta(days=1);hf['outcome_available_utc']=cut+pd.Timedelta(days=8)
 changed=mod.Context(frames+[future],pd.concat([h,hf],ignore_index=True));changed_f,_=changed.features('R','AA','BB',cut,window=4)
 for key in f:assert f[key]==changed_f[key]or np.isnan(f[key])and np.isnan(changed_f[key])
 # Code-equation example uses historical context-specific residuals, not one scalar.
 drecords=context.defenses['BB'];nd=sum(r['attempts']for r in drecords);down_den=sum((r['down_opps']for r in drecords),np.zeros(4))+30
 down_res=sum((r['down_residual']for r in drecords),np.zeros(4))/down_den;loc_res=sum((r['location_residual']for r in drecords),np.zeros(4))/(nd+40)
 manual_down=[f['f_pcm_down_'+str(i+1)]*down_res[i]for i in range(4)];manual_location=[f['f_pcm_location_'+name]*loc_res[i]for i,name in enumerate(mod.GROUPS['location'])]
 for k,v in zip(mod.INTER,manual_down+manual_location):assert abs(f[k]-v)<1e-15
 assert len(set(np.round(down_res,12)))>1 and len(set(np.round(loc_res,12)))>1
 result=dict(state='PASS_CHECKED_PUBLIC_ARITHMETIC_AND_SYNTHETIC_SOURCE_CONTRACT',at_utc=datetime.now(timezone.utc).isoformat(),A_ref='846b90ee032812306034f90e397e38dec7cebe99',new_fits=0,new_NFL_grades=0,new_raw_feed_downloads=0,author_scorer_invocations=0,unsafe_model_loads=0,
  aggregate_files_restored=restored,selection_views_checked=len(actual['scores']),source_panel_views_checked=len(source),side_partitions_checked=sidechecks,native_metric_views_checked=len(num),weekly_policy_groups=len(weekly),
  population=dict(numerical_query=population['expected'],numerical_scored=population['scored'],numerical_unknown=population['unknown_or_missing'],offer_eligible=partial['eligible'],offer_decided=partial['COMBINED']['decided'],offer_unknown=partial['states']['UNKNOWN_PARTICIPATION']),
  strong_control=dict(partial_pool_wins=119,always_Over_wins=122,decided=231,delta_wins=-3,delta_pp=100*(119-122)/231),
  synthetic_source_contract=dict(raw_plays=21,source_games=3,credited_carries=12,recognized_offensive_opportunities=18,known_zero_appearances=3,unknown_appearances_added_as_zero=0,team_run_probability=4/6,team_run_down1=.5,player_given_run_down1=1.,future_mutation='UNCHANGED',upcoming_query_without_outcome='PASS',no_play_pass_contract='An official-stat-credited no_play pass is outside A explicit convenience denominator; not demonstrated on actual A NFL rows.'),
  interaction_worked_example=dict(kind='SYNTHETIC_CODE_PATH_NOT_NFL_OBSERVATION',down_residual=down_res.tolist(),location_residual=loc_res.tolist(),player_mix={k:f[k]for k in f if k.startswith('f_pcm_down_')or k.startswith('f_pcm_location_')},down_interactions=manual_down,location_interactions=manual_location,collapse='NO: distinct context-specific residual vectors kept as separate regressors; no identical-scalar weighted-sum claim.'),
  raw_NFL_feature_reproduction='UNKNOWN_EXACT_A_RAW_BYTES_NOT_ACCESSIBLE; Bcachedcurrentversions differ, not substituted.',inference_and_fresh_fit='UNKNOWN_A_MODELS_AND_QUERY_ROWS_NOT_TRANSFERRED; priorAownerlocal arithmetic receipt reused only for its stated scope.')
 a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({k:result[k]for k in('state','selection_views_checked','source_panel_views_checked','side_partitions_checked','native_metric_views_checked','population','strong_control')}))
if __name__=='__main__':main()
