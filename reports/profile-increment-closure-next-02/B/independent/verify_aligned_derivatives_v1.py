"""Independent fixed-clock derivative and eligible-window arithmetic, no fits."""
import gzip,hashlib,json
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;BASE=OUT.parent
def read(p):
 p=Path(p);b=p.read_bytes();return json.loads(gzip.decompress(b)if p.suffix=='.gz'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
old_inputs=read(ROOT/'reports/player-context-matchup-01/B/source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz')
old_source=read(ROOT/'reports/profile-increment-to-release-01/B/source-profiles/PASSING_OPPORTUNITY_GAME_INPUTS_V2.json.gz')
newpath=BASE/'source-policy/ALIGNED_48H_DERIVATIVES_V1.json.gz';new=read(newpath);checked=0
assert new['policy_id']=='DECLARED_KICKOFF_PLUS_48H_TIMING_SENSITIVITY'and new['delay_seconds']==172800
def identity(r):return(r['game_id'],r['player_id'])if'player_id'in r else(r['game_id'],r['team'])
for name,original in(('QB_inputs',old_inputs),('team_games',old_source['team_games']),('QB_games',old_source['QB_games'])):
 om={identity(r):r for r in original};nm={identity(r):r for r in new[name]};assert len(om)==len(original)and len(nm)==len(new[name])and om.keys()==nm.keys()
 for key,r in nm.items():
  o=om[key];assert o['available']==o['kickoff']+604800 and r['available']==o['kickoff']+172800
  extra=set(r)-set(o);assert extra=={'retained_declared_7day_available','information_policy_id','availability_evidence'}
  assert r['retained_declared_7day_available']==o['available']
  assert r['information_policy_id']==new['policy_id']
  assert {k:v for k,v in r.items()if k not in extra and k!='available'}=={k:v for k,v in o.items()if k!='available'}
  checked+=1
assert all(not x for x in new['unresolved'].values())
own=defaultdict(list);defenses=defaultdict(dict)
for r in old_inputs:
 if not r['physical_participation']or not r['target_parity']:continue
 own[r['player_id']].append(r);defenses[r['opponent']][r['game_id']]=r
for group in own.values():group.sort(key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
queries=[q for q in old_inputs if q['season']in(2025,2026)];own_changed=def_changed=0;age_changes=[]
for q in queries:
 def window(rr,delay,limit):return[r for r in sorted(rr,key=lambda r:(r['kickoff'],r['game_id']))if r['kickoff']+delay<q['kickoff']][-limit:]
 before=window(own[q['player_id']],604800,8);after=window(own[q['player_id']],172800,8)
 own_changed+=[r['game_id']for r in before]!=[r['game_id']for r in after]
 if before and after:age_changes.append((before[-1]['kickoff']-after[-1]['kickoff'])/86400)
 before_d=window(defenses[q['opponent']].values(),604800,16);after_d=window(defenses[q['opponent']].values(),172800,16)
 def_changed+=[r['game_id']for r in before_d]!=[r['game_id']for r in after_d]
payload=dict(id='B-ALIGNED-CLOCK-DERIVATIVES-INDEPENDENT-v1',status='PASS_IN_CHECKED_SCOPE',source_derivative_sha256=sha(newpath),rows_fieldwise_checked=checked,QB_input_rows=len(new['QB_inputs']),team_rows=len(new['team_games']),QB_opportunity_rows=len(new['QB_games']),explicit_unresolved_counts={k:len(v)for k,v in new['unresolved'].items()},historical_queries=len(queries),own_last8_history_changes=own_changed,existing_E3_defense_last16_changes=def_changed,old_and_new_values_equal_except_declared_clock_metadata=True,clock_treatment='Fixedkickoff+48h ratherthan7d, strict<, ineachreconstructedhistoricalorigin; no actualobservedclockqualification.',independence='Compareddecodedrawderivativefieldsandindependentlyselectedavailability/game-timehistorywindows; authorwrapper/sourcepreparationnotcalled.',new_fits=0,new_scores=0,limits=['Historycoveragechangesareindependentlycounted, notaccuracygains orcosts.','Currentrevisedsourcewith48hassumption; neitherkickoff norcurrentretrievalauthenticateshistoricalpublication.','Existingdefensehistorychangeswithclockpolicy; noadditionalrawR3defensearchitectureisintroduced.'])
dest=OUT/'ALIGNED_DERIVATIVES_INDEPENDENT_REVIEW_V1.json';assert not dest.exists();dest.write_text(json.dumps(payload,indent=2)+'\n');print(json.dumps(payload,indent=2))
