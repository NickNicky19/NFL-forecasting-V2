"""Read-only reconstructed selector replay; never a live overlay/admission artifact."""
from pathlib import Path
from datetime import datetime,timezone
import json,gzip,hashlib,sys,math,collections,time,resource
D=Path(__file__).parent;BASE=D.parent;W=BASE/'website';S=BASE/'selector-inputs';sys.path[:0]=[str(W/'tools'),str(W/'pull')]
import weekly_selected_rankings as rank,weekly_adaptive_overlay as overlay,grade
resource.setrlimit(resource.RLIMIT_CPU,(120,120));resource.setrlimit(resource.RLIMIT_AS,(512*1024**2,512*1024**2));started=time.monotonic();cpu=time.process_time()
def load(p):return json.loads(Path(p).read_bytes())
def h(b):return hashlib.sha256(b).hexdigest()
def utc(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def number(x):return type(x)in (int,float)and math.isfinite(x)
def team(t):return {'LA':'LAR'}.get(t,t)
protocol=load(D/'PROTOCOL.json');assert h((W/'tools/weekly_selected_rankings.py').read_bytes())==protocol['production_ranker_sha256'];points=load(S/'P1_TYPED_POINTS_W1_W8.json')['rows'];proof=load(S/'P1_BOARD_TIMING_PROOF.json')
bridges=collections.defaultdict(set)
for path in ['C/sources/propline-v7/historical_identity_crosswalk.json.gz','C/artifacts/reliability-v8/IDENTITY_CROSSWALK.json.gz']:
 for r in json.loads(gzip.decompress((S/path).read_bytes())):
  p=str(r.get('native_player_id',''))
  if r.get('player_id') and p.startswith('espn:') and p[5:].isdigit():bridges[p[5:]].add(r['player_id'])
point_index={(r['origin'],r['game_id'],r['player_id']):r for r in points};assert len(point_index)==len(points)
def select(board, overrides):
 # Pure equivalent of production's fresh-candidate loops; default preserves all original points.
 P=rank.POLICY;games={g['id']:g for g in board['games']};now=utc(board['generated_at']);allp={'over':[],'under':[]}
 for pl in board['players']:
  if not rank.eligible(pl) or games[pl['game_id']]['state']!='pre' or utc(games[pl['game_id']]['kickoff'])<=now:continue
  best={}
  for pr in pl.get('props',[]):
   c=P['categories'].get(pr['key']);line=pr.get('line');key=(pl['game_id'],pl['id'],pr['key']);value=overrides.get(key,{}).get('mean',pr.get('adj'))
   if c is None or pr.get('line_from')not in ['dk','sleeper'] or not number(line)or not number(value):continue
   if type(pr.get('over'))is not int or type(pr.get('n'))is not int or not 0<=pr['over']<=pr['n']:continue
   if line<c['minimum_line']or not P['projection_line_ratio'][0]<=value/line<=P['projection_line_ratio'][1]:continue
   gap=value-line;score=gap/c['scale']
   if abs(gap)<=c['lean']or abs(score)<P['minimum_score']:continue
   side='over'if gap>0 else'under';item=dict(player_id=pl['id'],game_id=pl['game_id'],key=pr['key'],direction=side,line=line,line_from=pr['line_from'],adj=value,score=score,source='C_P1_MEAN_RECONSTRUCTED'if key in overrides else'SAVED_WEBSITE_REFERENCE',candidate_model_sha256=overrides.get(key,{}).get('model_sha256'))
   if side not in best or rank.order(item)<rank.order(best[side]):best[side]=item
  for side,item in best.items():allp[side].append(item)
 return {s:sorted(a,key=rank.order)[:P['top_n']]for s,a in allp.items()}
fields=['player_id','game_id','key','direction','line','line_from','adj','score'];reports=[];parity_checks=0;allrows=[]
for week in protocol['weeks']:
 p=S/f'W{week}_FULL_ORIGINAL_BOARD.private.json';raw=p.read_bytes();assert h(raw)==protocol['inputs'][f'W{week}'];board=json.loads(raw);now=board['generated_at'];games={g['id']:g for g in board['games']}
 doc=overlay.prepare_overlay(board,overlay.digest(board),{},{},website_source_sha=protocol['main'],prepared_at=now)
 actual=rank.prepare(board,overlay.digest(board),doc,overlay.digest(doc),now=now,website_source_sha=protocol['main'])
 control=select(board,{})
 for side in ['over','under']:
  assert [[a[k]for k in fields]for a in actual['picks'][side]]==[[a[k]for k in fields]for a in control[side]];parity_checks+=len(control[side])*len(fields)
 overrides={};coverage=collections.Counter();covrows=[]
 for pl in board['players']:
  g=games[pl['game_id']]
  if g['state']!='pre'or utc(g['kickoff'])<=utc(now)or not rank.eligible(pl):continue
  for pr in pl['props']:
   if pr['key']!='rec'or pr.get('line_from')not in ['dk','sleeper']or not number(pr.get('line')):continue
   reason=None;r=None
   if pl['pos']not in ['WR','TE']:reason='UNSUPPORTED_ROLE_REFERENCE'
   elif len(bridges.get(str(pl.get('espn_id')),set()))!=1:reason='MISSING_OR_CONFLICTING_ID_REFERENCE'
   else:
    gsis=next(iter(bridges[str(pl['espn_id'])]));gid=f"2026_{week:02d}_{'LA'if g['away']=='LAR'else g['away']}_{'LA'if g['home']=='LAR'else g['home']}";r=point_index.get((f'2026-W{week:02d}',gid,gsis))
    if r is None:reason='MISSING_EXACT_PLAYER_GAME_POINT_REFERENCE'
    elif team(r['team'])!=team(pl['team'])or team(r['opponent'])!=team(pl['opp'])or r['position']!=pl['pos']or utc(r['kickoff_UTC'])!=utc(g['kickoff']):reason='IDENTITY_ROLE_EVENT_MISMATCH_REFERENCE'
    elif not number(r['mean'])or utc(r['fit_cutoff_UTC'])>utc(now):reason='MODEL_POINT_OR_FIT_CLOCK_REFERENCE'
    else:
     t=proof['games'].get(f'{week}:{g["id"]}')
     if t is None or t['status']!='RECONSTRUCTED_PREFIX_INVARIANT':reason='QUERY_HORIZON_UNQUALIFIED_REFERENCE'
     else:overrides[(pl['game_id'],pl['id'],'rec')]=r;reason='C_P1_MEAN_RECONSTRUCTED_PREFIX_INVARIANT'
   coverage[reason]+=1;covrows.append({'player_id':pl['id'],'game_id':pl['game_id'],'category':'rec','state':reason})
 candidate=select(board,overrides);stats=load(W/f'data/cache/stat-keys-presence-strict-v3/stats_2026_{week:02d}.json');final=load(W/f'output/data/weeks/2026_w{week:02d}.json');finals={g['id']for g in final['games']if g['state']=='post'and g.get('completed')is True and g.get('home_score')is not None and g.get('away_score')is not None};byid={p['id']:p for p in board['players']};rows={}
 for name,picks in [('saved_control',control),('candidate',candidate)]:
  rr=[]
  for side,items in picks.items():
   for item in items:
    pl=byid[item['player_id']];entry=grade._bound_stats(board,pl,stats.get(pl['id']),game_id=item['game_id']);v,status=grade._prop_result(item,side,entry)if item['game_id']in finals else(None,'pending');rr.append(dict(item,result=status,actual=v,as_of_board_clock=now,actual_execution_clock=datetime.now(timezone.utc).isoformat(),original_issuance=False))
  rows[name]=rr;allrows.extend(dict(x,week=week,policy=name)for x in rr)
 tallies={name:{side:dict(collections.Counter(r['result']for r in rr if r['direction']==side))for side in ['over','under']}for name,rr in rows.items()}
 ids=lambda rr:{(r['game_id'],r['player_id'],r['key'],r['direction'])for r in rr};both=ids(rows['saved_control'])&ids(rows['candidate'])
 reports.append({'week':week,'board_sha256':h(raw),'as_of_board_clock':now,'production_policy':actual['policy']['version'],'selected_counts':{n:len(rr)for n,rr in rows.items()},'tallies':tallies,'rec_opportunity_coverage':dict(coverage),'candidate_point_overrides':len(overrides),'candidate_selected_model_rows':sum(r['source']=='C_P1_MEAN_RECONSTRUCTED'for r in rows['candidate']),'membership_common_same_side':len(both),'control_only':len(ids(rows['saved_control'])-both),'candidate_only':len(ids(rows['candidate'])-both),'frozen_started_origins_invented':0});(D/f'W{week}_COVERAGE.local.json').write_text(json.dumps(covrows,indent=2)+'\n');assert p.read_bytes()==raw
assert time.monotonic()-started<180
(D/'PICKS.local.json').write_text(json.dumps(allrows,indent=2)+'\n');total={}
for name in ['saved_control','candidate']:
 rr=[r for r in allrows if r['policy']==name];counts=collections.Counter(r['result']for r in rr);dec=counts['hit']+counts['miss'];total[name]={'states':dict(counts),'decided':dec,'rate':counts['hit']/dec if dec else None,'selected':len(rr)}
res={'state':'EXECUTED_PARTIAL_RECONSTRUCTED_SELECTOR_REPLAY','protocol_sha256':h((D/'PROTOCOL.json').read_bytes()),'production_equivalence_assertions':parity_checks,'weeks':reports,'cumulative':total,'actual_source_changed':False,'live_validator_bypassed':False,'live_admission_claimed':False,'new_model_inference_or_fits':0,'completed_scored_weeks':4,'five_week_floor':False,'current_v2_incumbent_historical_claim':False,'timing_proof_scope':proof['scope'],'uncertainty':'4exposedweeklyclusters only; no supported replacement superiority claim or calibrated confidence. Preserve per-week results/unknowns; no original issued policy claim.','resources':{'wall_seconds':time.monotonic()-started,'cpu_seconds':time.process_time()-cpu,'peak_process_RSS_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'max_RSS_MiB':512},'missing_to_complete':'Fifth fullboard with original eligibility/source/clock and compatible source-bound model/query-prefix closure. Complete source-vintage authentication remains separate.'}
(D/'RESULT.json').write_text(json.dumps(res,indent=2)+'\n');assert sum(p.stat().st_size for p in D.glob('*.json'))<4*1024**2;print(json.dumps(res,indent=2))
