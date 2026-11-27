"""Independent streaming raw->QB context verifier; no author qualifier/model fit.

Restricted offers are optional owner-local reads. Only aggregate/hash diagnostics
are emitted. Public PBP/stat derivatives CC BY4; FTN fields CC BY-SA4, FTN Data via
nflverse. These are current/revised bytes, not authentic as-of publication.
"""
import argparse,collections,csv,datetime,gzip,hashlib,json,math,resource,time
from pathlib import Path
from zoneinfo import ZoneInfo

FIELDS=('ydstogo','yardline_100','game_seconds_remaining','score_differential')
FLAGS=('is_catchable_ball','is_contested_ball','is_drop','is_throw_away','is_motion','is_screen_pass','is_play_action','is_rpo')

def number(v):
 try:x=float(v)
 except(TypeError,ValueError):return None
 return x if math.isfinite(x)else None

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):
 p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def context(d,a):
 d=number(d);a=number(a)
 return (int(d)-1 if d in(1,2,3,4)else 4)*5+(4 if a is None else 0 if a<0 else 1 if a<10 else 2 if a<20 else 3)
def base(q):return dict(context_attempts=[0]*25,context_completions=[0]*25,field_context={f:dict(sum=0.,n=0)for f in FIELDS},destinations=collections.Counter(),known_receiver_throws=0,unknown_receiver_throws=0,teams=set(),opponents=set(),play_keys=[],flags={f:dict(known=0,positive=0)for f in FLAGS},matched_chart_rows=0)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,required=True);ap.add_argument('--weekly-root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--week5',type=Path)
 a=ap.parse_args();started=time.monotonic();cpu=time.process_time();b=a.repo/'reports/player-context-matchup-01/B';expected={r['name']:r for r in read(b/'source-qualification-v1/SOURCE_RECEIPTS.json')['sources']};bindings=[]
 def guard():
  if time.monotonic()-started>600 or time.process_time()-cpu>300 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>536870912:raise RuntimeError('BOUNDED_RAW_REVIEW_RESOURCE_LIMIT')
 for y in range(2022,2027):
  for name in(f'play_by_play_{y}.csv.gz',f'ftn_charting_{y}.csv'):
   path=a.source_root/name;h=sha(path);assert h==expected[name]['sha256'];assert path.stat().st_size==expected[name]['bytes'];bindings.append(dict(source_id=name,sha256=h,bytes=path.stat().st_size,state='EXISTING_RAW_BYTES_HASH_MATCH'))
 games={}
 with(a.weekly_root/'games.csv').open()as f:
  for r in csv.DictReader(f):
   if r['game_type']=='REG':games[r['game_id']]=datetime.datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp()
 official={};physical={};sample=[]
 for y in range(2022,2027):
  path=a.weekly_root/f'stats_player_week_{y}.csv';bindings.append(dict(source_id='WEEKLY_'+str(y),sha256=sha(path),bytes=path.stat().st_size))
  with path.open()as f:
   for r in csv.DictReader(f):
    if r['position']!='QB'or r['season_type']!='REG'or y==2026 and int(r['week'])>8 or r['game_id']not in games:continue
    key=r['game_id'],r['player_id'];assert key not in official
    official[key]=dict(season=y,week=int(r['week']),team=r['team'],opponent=r['opponent_team'],kickoff=games[r['game_id']],attempts=number(r['attempts']),completions=number(r['completions']))
    physical[key]=any(number(r.get(k))is not None and number(r[k])>0 for k in('attempts','carries','targets','receptions','sacks_suffered','passing_2pt_conversions','rushing_2pt_conversions'))
 for y in range(2022,2027):sample.append(min((k for k,v in official.items()if v['season']==y),key=lambda k:(official[k]['kickoff'],k)))
 ordered=sorted(official,key=lambda k:(official[k]['kickoff'],k));sample+=[next(k for k in ordered if physical[k]and official[k]['attempts']==0),next(k for k in ordered if not physical[k])]
 allcounts={};yearstats=[];no_play_key=None
 for y in range(2022,2027):
  guard();seen=set();throws={};stats=collections.Counter();pid_groups={}
  with gzip.open(a.source_root/f'play_by_play_{y}.csv.gz','rt')as f:
   reader=csv.reader(f);head=next(reader);ix={v:i for i,v in enumerate(head)}
   for rr in reader:
    if rr[ix['season_type']]!='REG':continue
    gid=rr[ix['game_id']];play=rr[ix['play_id']];pkey=gid,str(int(float(play)));assert pkey not in seen;seen.add(pkey);stats['REG_plays']+=1
    stats['dropback']+=number(rr[ix['qb_dropback']])==1;stats['sack']+=number(rr[ix['sack']])==1;stats['scramble']+=number(rr[ix['qb_scramble']])==1
    pa,sack,two,deleted=(number(rr[ix[v]])for v in('pass_attempt','sack','two_point_attempt','play_deleted'))
    if pa!=1 or sack!=0 or two!=0 or deleted==1:continue
    stats['credited_throw_candidates']+=1;stats['missing_deleted_flag_on_admitted']+=deleted is None
    pid=rr[ix['passer_player_id']];key=gid,pid
    if key not in official:continue
    q=allcounts.setdefault(key,base(key));state=context(rr[ix['down']],rr[ix['air_yards']]);q['context_attempts'][state]+=1;q['context_completions'][state]+=number(rr[ix['complete_pass']])==1
    q['teams'].add(rr[ix['posteam']]);q['opponents'].add(rr[ix['defteam']]);q['play_keys'].append(pkey)
    for field in FIELDS:
     value=number(rr[ix[field]])
     if value is not None:q['field_context'][field]['sum']+=value;q['field_context'][field]['n']+=1
    destination=rr[ix['pass_location']]or'UNKNOWN';q['destinations'][destination]+=1
    q['known_receiver_throws']+=bool(rr[ix['receiver_player_id']]);q['unknown_receiver_throws']+=not bool(rr[ix['receiver_player_id']]);throws[pkey]=key
    if y==2025 and int(float(rr[ix['week']]))==2 and rr[ix['play_type']]=='no_play'and no_play_key is None:no_play_key=key
  # Independent exact-key left join, missing chart fields never mapped to FALSE.
  chart_seen=set();valid_values={f:set()for f in FLAGS}
  with(a.source_root/f'ftn_charting_{y}.csv').open()as f:
   for row in csv.DictReader(f):
    pk=row['nflverse_game_id'],row['nflverse_play_id'];assert pk not in chart_seen;chart_seen.add(pk)
    for field in FLAGS:
     if row[field]:valid_values[field].add(row[field])
    key=throws.get(pk)
    if key is None:continue
    q=allcounts[key];q['matched_chart_rows']+=bool(row['ftn_play_id'])
    for field in FLAGS:
     value=row[field];assert value in('','TRUE','FALSE')
     q['flags'][field]['known']+=bool(value);q['flags'][field]['positive']+=value=='TRUE'
  assert all(v<={'TRUE','FALSE'}for v in valid_values.values());stats['raw_play_unique_keys']=len(seen);stats['FTN_unique_keys']=len(chart_seen);yearstats.append(dict(season=y,**stats));guard()
 assert no_play_key is not None;sample.append(no_play_key)
 saved={(r['game_id'],r['player_id']):r for r in read(b/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz')};savedchart={(r['game_id'],r['player_id']):r for r in read(b/'source-fields-v3/FTN_DERIVED_QB_GAME_INPUTS.json.gz')}
 checks=[];full_parity=collections.Counter();normalized=[]
 for key,v in official.items():
  q=allcounts.get(key,base(key));att=sum(q['context_attempts']);cmp=sum(q['context_completions']);assert (att,cmp)==(v['attempts'],v['completions'])
  if att:assert q['teams']=={v['team']}and q['opponents']=={v['opponent']}
  r=saved[key];assert r['context_attempts']==q['context_attempts']and r['context_completions']==q['context_completions'];assert r['physical_participation']==physical[key];assert r['available']==v['kickoff']+7*86400
  assert r['pass_destination_counts']==dict(q['destinations']);assert r['known_receiver_throws']==q['known_receiver_throws']and r['unknown_receiver_throws']==q['unknown_receiver_throws']
  for field in FIELDS:
   raw=q['field_context'][field];got=r['field_context'][field];assert raw['n']==got['n'];mean=raw['sum']/raw['n']if raw['n']else None
   assert got['mean']is None if mean is None else math.isclose(mean,got['mean'],abs_tol=1e-10)
  if att:
   c=savedchart[key];assert c['eligible_throws']==att and c['matched_chart_rows']==q['matched_chart_rows'];assert c['flags']==q['flags']
  full_parity[str(v['season'])]+=1
  normalized.append(dict(v,game_id=key[0],player_id=key[1],available=v['kickoff']+7*86400,physical_participation=physical[key],A=q['context_attempts'],C=q['context_completions']))
  if key in sample:
   checks.append(dict(game_id=key[0],player_id=key[1],season=v['season'],week=v['week'],official_ATT=v['attempts'],official_CMP=v['completions'],physical_participation=physical[key],context_ATT=q['context_attempts'],context_CMP=q['context_completions'],field_mean_counts={f:q['field_context'][f]['n']for f in FIELDS},FTN_flag_counts=q['flags'],raw_pbp_play_key_count=len(q['play_keys']),source_clock_tier='CURRENT_REVISED_SEVEN_DAY_RECONSTRUCTION_NOT_AUTHENTICATED'))
 # One independently rebuilt pregame interaction; no model method invoked.
 query=min((r for r in normalized if r['season']==2025 and r['week']==1),key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
 history=sorted([r for r in normalized if r['physical_participation']],key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
 def past(t):return[r for r in history if r['available']<t]
 def sumvec(rr,field):return[sum(r[field][j]for r in rr)for j in range(25)]
 def counts_at(t):
  pp=past(t);return sumvec(pp,'A'),sumvec(pp,'C')
 pp=past(query['kickoff']);A,C=counts_at(query['kickoff']);own=[r for r in pp if r['player_id']==query['player_id']][-8:];oa,oc=sumvec(own,'A'),sumvec(own,'C');league_mix=[(x+1)/(sum(A)+25)for x in A];mix=[(x+20*m)/(sum(oa)+20)for x,m in zip(oa,league_mix)]
 defense=collections.defaultdict(list)
 for r in pp:
  if r['opponent']==query['opponent']:defense[r['game_id']].append(r)
 last=sorted(defense,key=lambda gid:(defense[gid][0]['kickoff'],gid))[-16:];da=[0]*25;dc=[0]*25;expected=[0.]*25;historical_example=None
 for gid in last:
  for r in defense[gid]:
   ga,gc=counts_at(r['kickoff']);prior=[(c+1)/(n+2)for n,c in zip(ga,gc)];o=[p for p in past(r['kickoff'])if p['player_id']==r['player_id']][-8:];pa,pc=sumvec(o,'A'),sumvec(o,'C');rate=[(c+20*p)/(n+20)for n,c,p in zip(pa,pc,prior)]
   for j in range(25):da[j]+=r['A'][j];dc[j]+=r['C'][j];expected[j]+=r['A'][j]*rate[j]
   if historical_example is None:historical_example=dict(game_id=r['game_id'],player_id=r['player_id'],kickoff=r['kickoff'],eligible_prior_rows=len(past(r['kickoff'])),latest_prior_availability=max(p['available']for p in past(r['kickoff'])))
 residual=[(c-e)/(n+100)for n,c,e in zip(da,dc,expected)];interaction=[m*r for m,r in zip(mix,residual)];main=(sum(dc)-sum(expected))/(sum(da)+100)
 # Compare only after independent source arithmetic was complete.
 import sys
 sys.path.insert(0,str(a.repo));from nfl_v2.player_context_matchup import ContextHistory,load_inputs
 model_history=ContextHistory(load_inputs(b/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz'),8,20);qr=saved[query['game_id'],query['player_id']];d=model_history.describe(qr)
 for actual,truth in [(mix,d['mix']),(residual,d['opponent_residual']),(interaction,model_history.direct_features(qr,'E3')[-25:])]:assert max(abs(float(a)-float(c))for a,c in zip(actual,truth))<1e-12
 scalar_collapse=sum(m*main for m in mix);assert math.isclose(scalar_collapse,main,abs_tol=1e-12);assert len({round(x,12)for x in residual})>1
 # Mutation is synthetic checking only: changed target/future labels/exposure must
 # not affect earlier features; no additional NFL fit or prediction is claimed.
 mutated=[dict(r)for r in load_inputs(b/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz')]
 for r in mutated:
  if r['kickoff']>=qr['kickoff']:
   r.update(context_attempts=[900]*25,context_completions=[400]*25,official_attempts=22500,official_completions=10000)
 altered=ContextHistory(mutated,8,20).direct_features(qr,'E3');original=model_history.direct_features(qr,'E3');assert all((math.isnan(float(x))and math.isnan(float(y)))or x==y for x,y in zip(original,altered))
 # Optional protected win/loss checked separately; publish hashes/counts only.
 offer_check=dict(state='NOT_REQUESTED',new_scored_NFL_rows=0)
 if a.week5:
  board=[r for r in read(a.week5)['rows']if r.get('target')=='pass_cmp'];pred=[r for r in read(b/'qb-wave-v1/predictions/2026-W05.json.gz')['rows']if r['method']=='E3'];pmap={(r['game_id'],r['player_id']):r for r in pred};cases=[]
  from scipy.stats import geom
  for o in board:
   p=pmap[o['game_id'],o['player_id']];l=p['law'];k=math.floor(o['line']);support=l['support'];weights=l['weights'];prior=l['prior'];f=sum(w for x,w in zip(support,weights)if x<=k);kind=prior['kind'];assert kind=='geometric';pf=0 if k<0 else 1-prior['q']**(k+1);under=(1-l['mixture'])*f+l['mixture']*pf;side='over'if 1-under>under else'under'if under>1-under else None
   state='PUSH'if o['actual']==o['line']else'WIN'if(side=='over'and o['actual']>o['line'])or(side=='under'and o['actual']<o['line'])else'LOSS'
   cases.append((o,p,side,state))
  chosen=[]
  for state in('WIN','LOSS'):
   o,p,side,s=sorted((r for r in cases if r[3]==state),key=lambda r:(r[0]['game_id'],r[0]['player_id']))[0];raw=allcounts[o['game_id'],o['player_id']];assert sum(raw['context_completions'])==o['actual'];assert p['actual']==o['actual'];assert p['feature_cutoff']==saved[o['game_id'],o['player_id']]['kickoff']
   chosen.append(dict(state=state,selected_side=side,contract_and_values_sha256=digest({k:o[k]for k in('game_id','player_id','target','line','actual')}),raw_label_parity=True,quote_time_status='TIMING_UNVERIFIED_ACTUAL_LINE_DIAGNOSTIC',forecast_cutoff_after_quote=bool(p['feature_cutoff']>datetime.datetime.fromisoformat(o['source_server_clock'].replace('Z','+00:00')).timestamp())))
  offer_check=dict(state='DETERMINISTIC_ONE_WIN_ONE_LOSS_RAW_LABEL_AND_SIDE_CHECKED',cases=chosen,protected_rows_exported=0,board_input_sha256=sha(a.week5),new_NFL_observations=0)
 result=dict(state='PASS_INDEPENDENT_RAW_TO_FEATURE_RECONSTRUCTION_WITH_SCOPE_LIMITS',at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),producer_commit='2fa855fc4dd7e9e495126dea93ba90a33fee4be3',reviewer='B_independent_raw_source_checker',source_bindings=bindings,
  complete_raw_stat_context_parity_by_season=dict(full_parity),sample_rules='SAMPLE_AND_RESOURCE_REGISTRATION_V1.json',sample_cases=checks,source_year_diagnostics=yearstats,
  interaction=dict(query_game=query['game_id'],query_player=query['player_id'],formula='mix_j=(ownA_j+20*(globalA_j+1)/(sumGlobalA+25))/(sumOwnA+20); expectedPastC_j=sumPastQBA_j*(ownPastC_j+20*(globalPastC_j+1)/(globalPastA_j+2))/(ownPastA_j+20); r_j=(defC_j-expectedPastC_j)/(defA_j+100); E3_j=mix_j*r_j',
   opponent_game_count=len(last),predicted_mix=mix,defense_attempts=da,defense_completions=dc,offense_expected_completions=expected,context_residual=residual,E3_interaction=interaction,
   unique_context_residuals=len({round(x,12)for x in residual}),same_scalar_main=main,weighted_identical_scalar_would_collapse=scalar_collapse,actual_context_weighted_sum=sum(interaction),historical_offense_example=historical_example,
   conclusion='Actual per-context residual vector, not repeated one-scalar interaction. Earlier offense-quality reference recomputed at each past origin. QB-throw-only context; not all dropbacks or full defensive talent.'),
  future_target_exposure_mutation='PASS_EARLIER_E3_FEATURES_IDENTICAL_WITHOUT_REFIT',offer_win_loss_check=offer_check,
  semantics=dict(completion_not_catchability=True,FTN_known_false_not_missing=True,explicit_weekly_zero_not_unknown=True,unknown_physical_state_retained=True,pass_destination_not_alignment=True,
   team_history='QB passers collapsed once perteam/game;16observedqualifiedgames, excludesnonQBthrowers,notdesigneddropbackforecast.',clock='kickoff+7days strict< consistentlyreconstructed; current/reviseddata, noauthenticated as-of claim.',offense_adjustment='Perpastgame shrunk QB completion context history, not iterative schedule-adjusted latenttalent or randomizedcausal defenseeffect.'),
  resources=dict(wall_seconds=time.monotonic()-started,CPU_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,new_fits=0,new_source_collections=0),
  verdicts=dict(A='PASS_checked_declared_source/feature_paths',B='PASS_current-vintage_7day_reconstruction_not_authentic_asof',C='PASS_raw_feature_and_representative_side_arithmetic;freshfit_not_this_scope',D='PASS_fixed-information-ablation_scope_not_all_contextmodels',E='PARTIAL_actualdropback/gamecontext_andentirely-owninfo_notcompleted',F='NO_positive_gain_orreleasecertification_fromthisreview'))
 a.out.mkdir(parents=True,exist_ok=True);target=a.out/'RAW_TO_FEATURE_ACCEPTANCE_RECEIPT_V1.json';assert not target.exists();target.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(state=result['state'],raw_parity=dict(full_parity),sample_cases=len(checks),context_residuals=result['interaction']['unique_context_residuals'],resources=result['resources'])))
if __name__=='__main__':main()
