"""Bounded independent raw-count/profile arithmetic; no author feature builder."""
import csv,gzip,hashlib,json,math,sys,time
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent
SOURCE=ROOT/'reports/profile-increment-to-release-01/B/source-profiles'
def read(p):
    p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def number(v):
    try:x=float(v);return x if math.isfinite(x)else None
    except(TypeError,ValueError):return None
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def plus(dst,src):
    for k in dst:dst[k]+=src.get(k,0)

data=read(SOURCE/'PASSING_OPPORTUNITY_GAME_INPUTS_V2.json.gz');teams=data['team_games'];qbs=data['QB_games']
names=list(teams[0]['counts']);by_t={(r['game_id'],r['team']):r for r in teams};by_q={(r['game_id'],r['player_id']):r for r in qbs}
# Chosen before new forecast scores: first and last chronological supported
# game of 2025 plus first and last 2026 game. These are source-count cases,
# not selected wins, gains or model examples.
selected=set()
for season in(2025,2026):
    rr=sorted({(r['kickoff'],r['game_id'])for r in teams if r['season']==season})
    selected.update((rr[0][1],rr[-1][1]))
scope=dict(id='B-OPPORTUNITY-INDEPENDENT-SCOPE-v1',source_version=data['version'],selected_raw_games=sorted(selected),source_sha256=sha(SOURCE/'PASSING_OPPORTUNITY_GAME_INPUTS_V2.json.gz'),profile_examples='first ordinary and first no-own-history in each declared2025/2026 season; feature checks additionally cover first2026W5 query',fresh_fit='No duplicate fit: unchanged forest family prior independently reproduced; this package verifies new derived inputs and new typed-model inference. Fresh-fit recreation of augmented model is not claimed.',protected_offers='Not involved in source-count fixtures; no raw PBP or restricted offered rows published.')
p=OUT/'VERIFICATION_SCOPE_BEFORE_NEW_SCORES_V1.json'
if p.exists():assert read(p)==scope
else:p.write_text(json.dumps(scope,indent=2)+'\n')
raw_t={k:{n:0 for n in names}for k in by_t if k[0]in selected};raw_q={k:{n:0 for n in names}for k in by_q if k[0]in selected}
cells_t={k:{x:[{n:0 for n in names}for j in range(5)]for x in('down','distance','field')}for k in raw_t}
cells_q={k:{x:[{n:0 for n in names}for j in range(5)]for x in('down','distance','field')}for k in raw_q}
bound=[];read_rows=0;fixtures=Counter()
source_root=Path(sys.argv[1])
for season in(2025,2026):
    path=source_root/f'play_by_play_{season}.csv.gz';bound.append(dict(source=path.name,sha256=sha(path)))
    seen=set()
    with gzip.open(path,'rt')as f:
        for r in csv.DictReader(f):
            read_rows+=1
            if r['game_id']not in selected or r['season_type']!='REG':continue
            identity=r['game_id'],r['play_id'];assert identity not in seen;seen.add(identity)
            if number(r['play_deleted'])!=0 or number(r['two_point_attempt'])!=0:continue
            v={k:number(r.get(k))for k in('pass_attempt','rush_attempt','qb_dropback','sack','qb_scramble','qb_spike','qb_kneel','complete_pass')}
            if not any(v[k]==1 for k in('pass_attempt','rush_attempt','qb_dropback')):continue
            att=v['pass_attempt']==1 and v['sack']==0;db=v['qb_dropback']==1
            c={n:0 for n in names}
            c.update(opportunities=1,dropbacks=int(db),credited_attempts=int(att),completions=int(att and v['complete_pass']==1),completion_known_attempts=int(att and v['complete_pass']in(0,1)),sacks=int(v['sack']==1),scrambles=int(v['qb_scramble']==1),spikes=int(att and v['qb_spike']==1),kneels=int(v['qb_kneel']==1),unknown_dropback=int(v['qb_dropback']not in(0,1)),unknown_sack=int(v['sack']not in(0,1)),unknown_scramble=int(v['qb_scramble']not in(0,1)),unknown_spike=int(v['qb_spike']not in(0,1)),unknown_completion=int(att and v['complete_pass']not in(0,1)),attempts_on_dropbacks=int(att and db),dropback_known_opportunities=int(v['qb_dropback']in(0,1)),sack_known_dropbacks=int(db and v['sack']in(0,1)),scramble_known_dropbacks=int(db and v['qb_scramble']in(0,1)),spike_known_attempts=int(att and v['qb_spike']in(0,1)))
            tid=r['game_id'],r['posteam'];assert tid in raw_t
            player=r['rusher_player_id']if v['qb_scramble']==1 else r['passer_player_id'];qid=r['game_id'],player
            assigned=bool(db or att or c['sacks'])and qid in raw_q
            c['unassigned_dropbacks']=int(db and not assigned);c['unassigned_attempts']=int(att and not assigned)
            down,dist,field=[number(r.get(k))for k in('down','ydstogo','yardline_100')]
            bins={'down':int(down)-1 if down in(1,2,3,4)else 4,'distance':4 if dist is None or dist<0 else 0 if dist<=3 else 1 if dist<=6 else 2 if dist<=10 else 3,'field':4 if field is None or not 0<=field<=100 else 0 if field>80 else 1 if field>=50 else 2 if field>20 else 3}
            plus(raw_t[tid],c)
            for name,j in bins.items():plus(cells_t[tid][name][j],c)
            if assigned:
                assert by_q[qid]['team']==r['posteam'];plus(raw_q[qid],c)
                for name,j in bins.items():plus(cells_q[qid][name][j],c)
            fixtures['qualified_sample_plays']+=1;fixtures['credited_no_play']+=int(att and r.get('play_type')=='no_play');fixtures['spike_outside_dropback']+=int(att and v['qb_spike']==1 and not db)
for qid,c in raw_q.items():
    t=raw_t[qid[0],by_q[qid]['team']];c['attributed_team_dropbacks']=t['dropbacks'];c['attributed_team_attempts']=t['credited_attempts']
for k,c in raw_t.items():assert c==by_t[k]['counts'],('TEAM_COUNTS',k)
for k,c in raw_q.items():assert c==by_q[k]['counts'],('QB_COUNTS',k)
for k,c in cells_t.items():assert c==by_t[k]['cells'],('TEAM_CONTEXT',k)
for k,c in cells_q.items():assert c==by_q[k]['cells'],('QB_CONTEXT',k)

# Independent arithmetic on as-of profiles: availability admission, game order,
# relevant8/16 windows, league-count-weighted shrinkage, and known/undefined zero.
profiles=read(SOURCE/'QB_OPPORTUNITY_ASOF_PROFILES_V2.json.gz');chosen=[]
for season in(2025,2026):
    pp=[p for p in profiles if p['identity']['season']==season]
    for predicate in(lambda p:p['own']['games']>=8,lambda p:p['own']['games']==0):
        match=next((p for p in pp if predicate(p)),None)
        if match is not None:chosen.append(match)
chosen.append(next(p for p in profiles if p['identity']['season']==2026 and p['identity']['week']==5))
checks=0;max_error=0.
definitions={'dropback_per_opportunity':('dropbacks','dropback_known_opportunities'),'attempt_per_dropback':('attempts_on_dropbacks','dropbacks'),'completion_per_attempt':('completions','completion_known_attempts'),'sack_per_dropback':('sacks','sack_known_dropbacks'),'scramble_per_dropback':('scrambles','scramble_known_dropbacks'),'spike_per_attempt':('spikes','spike_known_attempts'),'QB_dropback_share':('dropbacks','attributed_team_dropbacks'),'QB_attempt_share':('credited_attempts','attributed_team_attempts')}
def sums(rr):
    out={n:0 for n in names}
    for r in rr:plus(out,r['counts'])
    return out
def same(a,b):
    global max_error,checks
    checks+=1
    if a is None or b is None:assert a is b;return
    error=abs(float(a)-float(b));max_error=max(max_error,error);assert error<1e-12,(a,b,error)
for p in chosen:
    q=p['identity'];cut=p['cutoff'];eligible=[r for r in teams if r['available']<cut];qeligible=[r for r in qbs if r['available']<cut]
    for group in('own','offense','defense'):
        earlier=[r for r in(qeligible if group=='own'else eligible)if r['player_id']==q['player_id']]if group=='own'else[r for r in eligible if r['team'if group=='offense'else'opponent']==q['team'if group=='offense'else'opponent']]
        earlier=sorted(earlier,key=lambda r:(r['kickoff'],r['game_id'],r.get('player_id',r['team'])))[-(8 if group=='own'else 16):]
        assert [r['game_id']for r in earlier]==p[group]['game_ids'];counts=sums(earlier);prior_rows=qeligible if group=='own'else eligible;prior=sums(prior_rows);assert counts==p[group]['counts']
        for rate,(num,den)in definitions.items():
            expected=p[group]['rates'][rate];raw=counts[num]/counts[den]if counts[den]else None;prior_rate=prior[num]/prior[den]if prior[den]else None
            shrunk=(counts[num]+100*prior_rate)/(counts[den]+100)if prior_rate is not None else None
            same(raw,expected['raw']);same(prior_rate,expected['prior']);same(shrunk,expected['shrunk'])
        for name in('opportunities','dropbacks','credited_attempts','completions','sacks'):
            mu=prior[name]/len(prior_rows)if prior_rows else None;same((counts[name]+4*mu)/(len(earlier)+4)if mu is not None else None,p[group]['volume'][name]['shrunk_per_game'])
        for name in('down','distance','field'):
            for j in range(5):
                cell={n:sum(r['cells'][name][j][n]for r in earlier)for n in names};assert cell==p[group]['contexts'][name][j]['counts']
                same(cell['dropbacks']/counts['dropbacks']if counts['dropbacks']else None,p[group]['contexts'][name][j]['dropback_frequency']['raw'])
receipt=dict(id='B-OPPORTUNITY-SOURCE-INDEPENDENT-REVIEW-v1',status='PASS_IN_CHECKED_SCOPE',source_sha256=scope['source_sha256'],source_bindings=bound,selected_games=sorted(selected),raw_sample=dict(teams=len(raw_t),QB_game_rows=len(raw_q),counter_fields=len(names),**fixtures),profile_sample=dict(profiles=len(chosen),scalar_checks=checks,maximum_absolute_difference=max_error),independence='Raw PBP flags/attribution/context bins and count/rate/shrinkage arithmetic independently rebuilt; no author play_counts, OpportunityHistory, or scorer called.',limits=['Four deterministic games and five profiles, not every raw play/profile. Earlier full source acceptance reused.','Seven-day current-vintage policy is arithmetic-verified, not authenticated original source availability.','OwnQB opportunity denominator is attributed passing events; team opportunity is reported rush/pass/dropback proxy. Neither is authenticated active-QB snaps or designed passing calls.','Existing predictive comparisons and five-week product qualification are separate; source PASS alone demonstrates no forecasting gain.'])
dest=OUT/'SOURCE_INDEPENDENT_REVIEW_V1.json';assert not dest.exists();dest.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n');print(json.dumps(receipt,indent=2))
