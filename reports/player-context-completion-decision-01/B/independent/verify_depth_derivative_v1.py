"""Separate arithmetic checks of the new depth derivative and feature semantics."""
import argparse,copy,csv,datetime,gzip,hashlib,json,math,resource,sys,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from nfl_v2.qb_depth_catchability import DepthHistory
FLAGS=('is_catchable_ball','is_drop','is_contested_ball')
def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def finite(s):
 try:v=float(s);return v if math.isfinite(v)else None
 except (ValueError,TypeError):return None
def depth(v):return 4 if v is None else 0 if v<0 else 1 if v<10 else 2 if v<20 else 3

def run(source,base,chartfile,census,out):
 started=time.monotonic();rows=read(base);chart=read(chartfile);by={(r['game_id'],r['player_id']):r for r in chart};assert len(by)==len(rows)==2901
 for r in chart:
  n=r['eligible_throws'];assert len(n)==5 and all(int(v)==v and v>=0 for v in n)
  for f in FLAGS:
   k=r['flags'][f]['known'];p=r['flags'][f]['positive'];assert len(k)==len(p)==5
   assert all(int(a)==a and int(b)==b and 0<=b<=a<=e for e,a,b in zip(n,k,p))
 expected={ (r['season'],r['week'],r['depth'],r['flag']):(r['eligible_official_throws'],r['known'],r['positive'])for r in read(census)['week_depth_flag_support'] }
 names=('BEHIND_LOS','YARDS_0_9','YARDS_10_19','YARDS_20_PLUS','UNKNOWN');tot={}
 for r in chart:
  for j,d in enumerate(names):
   for f in FLAGS:
    key=r['season'],r['week'],d,f;v=tot.setdefault(key,[0,0,0]);v[0]+=r['eligible_throws'][j];v[1]+=r['flags'][f]['known'][j];v[2]+=r['flags'][f]['positive'][j]
 for key,v in expected.items():assert tuple(tot[key])==v
 assert all(not any(v)for k,v in tot.items()if k not in expected)
 # Outcome-blind fixed sample: lexicalfirst physical QB-game per source year.
 sample=[]
 for season in range(2022,2027):
  q=min((r for r in rows if r['season']==season and r['physical_participation'] and r['attempts']>0),key=lambda r:(r['game_id'],r['player_id']))
  wanted=(q['game_id'],q['player_id']);throws={}
  with gzip.open(source/f'play_by_play_{season}.csv.gz','rt')as h:
   for r in csv.DictReader(h):
    if(r['game_id'],r['passer_player_id'])!=wanted or r['season_type']!='REG':continue
    if finite(r['pass_attempt'])==1 and finite(r['sack'])==0 and finite(r['two_point_attempt'])==0 and finite(r['play_deleted'])!=1:
     throws[str(int(float(r['play_id'])))]=depth(finite(r['air_yards']))
  n=[0]*5;counts={f:{'known':[0]*5,'positive':[0]*5}for f in FLAGS}
  for j in throws.values():n[j]+=1
  with(source/f'ftn_charting_{season}.csv').open()as h:
   for r in csv.DictReader(h):
    if r['nflverse_game_id']!=wanted[0]or r['nflverse_play_id']not in throws:continue
    j=throws[r['nflverse_play_id']]
    for f in FLAGS:
     if r[f]in('TRUE','FALSE'):counts[f]['known'][j]+=1;counts[f]['positive'][j]+=int(r[f]=='TRUE')
  derived=by[wanted];assert derived['eligible_throws']==n and derived['flags']==counts
  sample.append({'game_id':wanted[0],'player_id':wanted[1],'season':season,'eligible_throws':n,'flags':counts,'raw_key_check':'PASS'})
 # Feature-layer fixture: knownzero, missing and nohistory remain distinct.
 def rr(g,k,a):return dict(game_id=g,player_id='P',kickoff=k,available=a,physical_participation=True)
 ar=[rr('past-knownzero',10,20),rr('past-unknown',30,40)]
 cc=[dict(game_id='past-knownzero',player_id='P',eligible_throws=[5,0,0,0,0],flags={'is_catchable_ball':{'known':[4,0,0,0,0],'positive':[0,0,0,0,0]}}),dict(game_id='past-unknown',player_id='P',eligible_throws=[5,0,0,0,0],flags={'is_catchable_ball':{'known':[0,0,0,0,0],'positive':[0,0,0,0,0]}})]
 q=dict(game_id='future-no-outcomes',player_id='P',kickoff=50)
 d=DepthHistory(ar,cc).describe(q);assert d['eligible_throws'][0]==10 and d['known'][0]==4 and d['positive'][0]==0 and d['raw'][0]==0
 assert math.isclose(d['baseline'][0],1/6)and math.isclose(d['shrunk'][0],20/6/24)
 assert d['raw'][1]is None and d['baseline'][1]==.5 and d['shrunk'][1]==.5 and d['support'][1][-2:]==[1.,1.]
 unseen=DepthHistory(ar,cc).describe(dict(q,player_id='UNSEEN'));assert unseen['known']==[0.]*5 and unseen['fallback']=='earlier_depth_prior_no_own_chart_annotations'
 future=rr('target-mutated',50,60);newchart=dict(game_id=future['game_id'],player_id='P',eligible_throws=[999]*5,flags={'is_catchable_ball':{'known':[999]*5,'positive':[999]*5}})
 assert DepthHistory(ar+[future],cc+[newchart]).describe(q)==d
 # Real query future/target mutation: source arrays for elapsedlabel stay excluded.
 qreal=min((r for r in rows if r['season']==2026),key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
 before=DepthHistory(rows,chart).describe(qreal);mr=copy.deepcopy(rows);mc=copy.deepcopy(chart)
 for r in mr:
  if r['available']>=qreal['kickoff']:r['attempts']=999999;r['completions']=999999
 for r in mc:
  if r['available']>=qreal['kickoff']:
   r['eligible_throws']=[999999]*5
   for f in FLAGS:r['flags'][f]={'known':[999999]*5,'positive':[999999]*5}
 assert DepthHistory(mr,mc).describe(qreal)==before
 result={'id':'B-DEPTH-DERIVATIVE-FEATURE-INDEPENDENT-v1','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','chart_sha256':sha(chartfile),'source_census_sha256':sha(census),'base_inputs_sha256':sha(base),'module_sha256':sha(ROOT/'nfl_v2/qb_depth_catchability.py'),'checked':{'derivative_rows':len(chart),'independent_aggregate_cells':len(expected),'source_year_sample_cases':sample,'knownzero_missing_unseen_fixture':'PASS','future_target_mutation':'PASS_SYNTHETIC_AND_REAL_2026W1_QUERY','upcoming_query_requires_final_outcome':False},'scope':'New five-depth annotation derivative and new DepthHistory only. No rerun of old2901sourcefeatureacceptance, no freshfit/scoring. Rawsampletables are licensedPBP/FTN derivatives, not privateoffers.','resources':{'wall_seconds':time.monotonic()-started,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'fits':0,'downloads':0}}
 out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({'status':'PASS','rows':len(chart),'aggregatecells':len(expected),'samplecases':len(sample),'resources':result['resources']}))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--source',type=Path,required=True);a.add_argument('--base',type=Path,required=True);a.add_argument('--chart',type=Path,required=True);a.add_argument('--census',type=Path,required=True);a.add_argument('--out',type=Path,required=True);z=a.parse_args();run(z.source,z.base,z.chart,z.census,z.out)
