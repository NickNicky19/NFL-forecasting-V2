"""Conservative global constant-lag boundary check; no fitting or scoring."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from zoneinfo import ZoneInfo
import csv,json,hashlib,collections
D=Path(__file__).parent;C=D/'C';W=Path('/tmp/NFL-CATEGORY-RELEASE-20261112/website');N=0

def ck(v,m):
 global N
 assert v,m;N+=1

def utc(s):
 x=datetime.fromisoformat(s.replace('Z','+00:00'));ck(x.utcoffset()is not None,'awaretimestamp');return x

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=[C/'prospective/runs/C-FWD-v4-20261101-0009-P2-pass_yd/sources/schedule.csv',C/'prospective/runs/C-FWD-v4-20261105-W09-JAXBAL-remainder/sources/schedule.csv']
def schedule(p):
 rows=list(csv.DictReader(p.open()));out={}
 for r in rows:
  if not r['gametime']or not r['gameday']:continue
  k=datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).astimezone(timezone.utc)
  ck(r['game_id']not in out,'uniquegame');out[r['game_id']]=dict(game_id=r['game_id'],season=int(r['season']),week=int(r['week']),home=r['home_team'],away=r['away_team'],kickoff=k)
 return out
ss=[schedule(p)for p in paths];a,b=ss
relevant={k for k,r in a.items()if r['season']==2026 and 1<=r['week']<=8};ck(relevant=={k for k,r in b.items()if r['season']==2026 and 1<=r['week']<=8},'samesupported2026gameuniverse');ck(all(a[k]['kickoff']==b[k]['kickoff']for k in relevant),'samekickoffsretainedversions')
# Crosscheck every prior-week league game against independently retained site finals.
canon=lambda t:'LAR'if t=='LA'else t
site_sources=[]
for week in [4,5,6,7]:
 p=W/f'output/data/weeks/2026_w{week:02d}.json';j=json.loads(p.read_bytes());native={(canon(g['home']),canon(g['away'])):g for g in j['games']};research=[r for r in a.values()if r['season']==2026 and r['week']==week];ck(len(research)==len(native),'completeleagueweekcount')
 for r in research:
  g=native[(canon(r['home']),canon(r['away']))];ck(utc(g['kickoff'])==r['kickoff'],'siteandCresearchkickoffagree')
 site_sources.append(dict(path=str(p),sha256=sha(p),games=len(native)))
boundaries=[(r['kickoff']+timedelta(days=7),r['game_id'])for r in a.values()]
projection=json.loads((D/'P1_TYPED_POINTS_W1_W8.json').read_bytes());bygame=collections.defaultdict(list)
for r in projection['rows']:
 ck(r['game_id']in a,'queryscheduled');ck(utc(r['kickoff_UTC'])==a[r['game_id']]['kickoff'],'exactquerykickoff');bygame[r['game_id']].append(r)
results=[]
for week in [5,6,7,8]:
 board=json.loads((D/f'W{week}_FULL_ORIGINAL_BOARD.private.json').read_bytes());start=utc(board['generated_at']);games=[]
 for g in board['games']:
  end=utc(g['kickoff']);cg=[r for r in a.values()if r['season']==2026 and r['week']==week and (canon(r['home']),canon(r['away']))==(canon(g['home']),canon(g['away']))];ck(len(cg)==1 and cg[0]['kickoff']==end,'boardgamebinding');research_id=cg[0]['game_id'];eligible=g['state']=='pre'and start<end
  # Strict History.before uses available<cutoff: at target cutoff is excluded;
  # at board cutoff is also excluded there but could be added before target.
  hit=sorted((t.isoformat(),k)for t,k in boundaries if start<=t<end) if eligible else []
  rows=bygame[research_id];fitready=all(utc(r['fit_cutoff_UTC'])<=start for r in rows)
  status='STARTED_EXCLUDED'if not eligible else 'POTENTIAL_INFORMATION_BOUNDARY'if hit else 'CONDITIONAL_NO_GLOBAL_7D_BOUNDARY'if fitready else 'MODEL_ORIGIN_AFTER_BOARD'
  games.append(dict(native_game_id=g['id'],canonical_game_id=research_id,kickoff=end.isoformat(),state=status,global_boundaries_between_board_and_kickoff=hit,saved_P1_rows=len(rows),WRTE_rows=sum(r['position']in ['WR','TE']for r in rows),fit_before_board=fitready))
 results.append(dict(week=week,board_UTC=start.isoformat(),games=games))
# These sourcefiles are same-period consistent but NOT exact original sourcehash.
original=json.loads((C/'reports/player-context-matchup-01/v1.1/FOOTBALL_INPUT_BINDINGS.json').read_bytes())['original_schedule_SHA256']
result={'state':'CONDITIONAL_PREFIX_INVARIANCE_CHECK_NOT_ORIGINAL_SOURCE_ADMISSION','checked_at_UTC':datetime.now(timezone.utc).isoformat(),'assertions':N,'source_code':{p:sha(C/p)for p in ['src/context_experiment_c01.py','src/context_features_c01.py','src/data_v2.py']},'source_schedule_original_SHA256':original,'source_schedule_exact_original_restored':any(sha(p)==original for p in paths),'retained_schedule_sources':[{'path':str(p),'sha256':sha(p)}for p in paths],'complete2026W1_W8games_agree_across_retained_schedules':len(relevant),'independent_site_previousweek_sources':site_sources,'criterion':'NO global C game kickoff+7days in [savedboard_clock,targetkickoff); History.before is strictly available<cutoff. Trained state/modelorigin must be fixed before board. Targetkickoff/role/week known context held unchanged.','dependency_scope':'Every query dynamic historyprefix in E2baseplayer/team/Contextplayer/opponentdefense/earlierleague residuals uses fixed7days. Precomputed older residuals and fittedpriors frozen; no additional query externalcontext source appears in inspected code.','limits':['The exact original5ac3 schedule bytes were not restored; two retainedsourceversions and sitefinals agree on relevantgameclocks, but this conditionalcertificate is not exactoriginalsourceclosure.','Historical source/vintage remains revised+7dreconstruction, not observedavailability.','Targetqueryuniverse remains stat-row-conditioned and explicitunknown source states retained; this check doesnotauthenticatepregamepopulation.','No actual featurevector reproduction or model fit/inference performed; this is a sufficient no-boundary condition under declaredsourceclockassumption.','Rows crossing any globalboundary remain unqualifiedbythiscriterion; absenceofnewrelevantteamhistory alone was not assumed.'],'weeks':results,'new_fit_inference_grade_replay':0}
(D/'TEMPORAL_BOUNDARY_RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'assertions':N,'exact_original_schedule':result['source_schedule_exact_original_restored'],'counts':[{ 'week':x['week'],'statuses':dict(collections.Counter(g['state']for g in x['games'])),'conditional_WRTE_rows':sum(g['WRTE_rows']for g in x['games']if g['state']=='CONDITIONAL_NO_GLOBAL_7D_BOUNDARY')}for x in results]},indent=2))
