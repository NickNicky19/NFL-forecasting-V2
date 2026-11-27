"""Independent support census, not parent feature builder or scorer."""
import argparse,datetime,gzip,hashlib,json,resource,time
from pathlib import Path
import pandas as pd
import numpy as np
FLAGS=('is_catchable_ball','is_drop','is_contested_ball')
DEPTHS=('BEHIND_LOS','YARDS_0_9','YARDS_10_19','YARDS_20_PLUS','UNKNOWN')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def depth(v):return 4 if not np.isfinite(v) else 0 if v<0 else 1 if v<10 else 2 if v<20 else 3

def run(source,inputs,out):
 started=time.monotonic();cpu=time.process_time()
 qb=json.loads(gzip.decompress(inputs.read_bytes()));keys={(r['game_id'],r['player_id'])for r in qb}
 rows=[];years=[]
 for season in range(2022,2027):
  pp=source/f'play_by_play_{season}.csv.gz';fp=source/f'ftn_charting_{season}.csv'
  use=['game_id','play_id','season_type','week','passer_player_id','pass_attempt','sack','two_point_attempt','play_deleted','air_yards','down','complete_pass']
  p=pd.read_csv(pp,usecols=use,dtype={'game_id':'string','passer_player_id':'string'},low_memory=False)
  p=p[(p.season_type=='REG')&(p.pass_attempt==1)&(p.sack==0)&(p.two_point_attempt==0)&(p.play_deleted!=1)].copy()
  p=p[[ (g,q)in keys for g,q in zip(p.game_id,p.passer_player_id) ]].copy()
  p['play_key']=p.play_id.astype('Int64').astype('string');p['depth_index']=[depth(v)for v in p.air_yards]
  f=pd.read_csv(fp,usecols=['nflverse_game_id','nflverse_play_id',*FLAGS],dtype='string')
  assert not f.duplicated(['nflverse_game_id','nflverse_play_id']).any()
  for flag in FLAGS:assert set(f[flag].dropna())<={'TRUE','FALSE'}
  j=p.merge(f,left_on=['game_id','play_key'],right_on=['nflverse_game_id','nflverse_play_id'],how='left',validate='one_to_one')
  y=dict(season=season,eligible_throws=len(j),unique_QB_games=j[['game_id','passer_player_id']].drop_duplicates().shape[0],actual_weeks=sorted(j.week.astype(int).unique().tolist()),pbp_sha256=digest(pp),FTN_sha256=digest(fp),annotation_counts={})
  for flag in FLAGS:
   known=j[flag].notna();positive=j[flag].eq('TRUE').fillna(False)
   y['annotation_counts'][flag]={'known':int(known.sum()),'positive':int(positive.sum()),'unknown':int((~known).sum()),'complete_with_FALSE':int(((j.complete_pass==1)&j[flag].eq('FALSE').fillna(False)).sum()),'incomplete_with_TRUE':int(((j.complete_pass==0)&positive).sum())}
  years.append(y)
  for (week,d),g in j.groupby(['week','depth_index']):
   for flag in FLAGS:
    kn=g[flag].notna();po=g[flag].eq('TRUE').fillna(False)
    rows.append({'season':season,'week':int(week),'depth':DEPTHS[int(d)],'flag':flag,'eligible_official_throws':len(g),'known':int(kn.sum()),'positive':int(po.sum()),'unknown':int((~kn).sum()),'rate':float(po.sum()/kn.sum())if kn.sum()else None,'source_unavailable':not bool(kn.sum())})
 result={'id':'B-DEPTH-ANNOTATION-SUPPORT-INDEPENDENT-v1','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'state':'SUPPORTED_PROVIDER_ANNOTATION_CONTEXT_PROXY','method':'Independent pandas raw key join plus finite disjoint depth counts; no parent feature builder/scorer. Reuses accepted official-throw contract and exact QB source-identity universe.','input_sha256':digest(inputs),'source_vintage':'CURRENT_REVISED_SOURCE_WITH_RETAINED_7DAY_AVAILABILITY_RECONSTRUCTION;NOT_AUTHENTICATED_HISTORICAL_RELEASE','definition':'FTN provider binary is_catchable_ball / is_drop / is_contested_ball annotation, TRUE/FALSE counted as known and missing as unknown. These are separate from observed complete_pass; no completion/catchability/drop identity assumed.','denominator':'Each flag positive / explicitly known flag among eligible official credited non-sack/non-two-point throws, including incompletions; support coverage known / all eligible throws. All25down-depthcontexts remain in original contract; this review summarizes five depth bins.','depths':DEPTHS,'seasons':years,'week_depth_flag_support':rows,'difference_from_F1_F2':'PriorF1/F2 appended eight-game aggregate chart support/age/three rates across all throws. New mechanism conditions annotation counts/rates on down/depth and integrates with pregame predicted context. It is not a repeated intercept or confidence gate.','five_week_rule':'New exact law/direction/probability/policy must earn its own distinct scored season-weeks; four retained offered weeks do not inherit prior base or seven-week C point-replay history.','claim_limits':['Provider charted catchable annotation is not pure QB accuracy, CP/CPOE or target-game predictor.','Current download/FTN date_pulled does not authenticate historical first availability.','Existing physical/stat-row universe remains retrospective participant membership, not a pregame roster.','New context fields must receive own later test against strongest same-mask retained controls; no positive gain presumed.'],'resources':{'wall_seconds':time.monotonic()-started,'cpu_seconds':time.process_time()-cpu,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,'fits':0,'downloads':0},'license':'FTN Data via nflverse CC-BY-SA4.0; PBP nflverse/nflfastR CC-BY4.0; mixed derivative CC-BY-SA4.0'}
 out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({'state':result['state'],'seasons':len(years),'cells':len(rows),'resources':result['resources']}))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--source',type=Path,required=True);a.add_argument('--inputs',type=Path,required=True);a.add_argument('--out',type=Path,required=True);v=a.parse_args();run(v.source,v.inputs,v.out)
