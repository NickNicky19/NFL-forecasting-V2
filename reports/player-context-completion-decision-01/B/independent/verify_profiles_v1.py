"""Independent profile arithmetic from retained input contracts, no profile regeneration."""
import datetime,gzip,hashlib,json,math,sys,time,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
def read(p):
 b=Path(p).read_bytes();return json.loads(gzip.decompress(b)if b[:2]==b'\x1f\x8b'else b)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def close(a,b):assert abs(float(a)-float(b))<2e-10,(a,b)
def svec(rr,key):return [math.fsum(r[key][j]for r in rr)for j in range(25)]

def main():
 started=time.monotonic();b=ROOT/'reports/player-context-completion-decision-01/B';base=ROOT/'reports/player-context-matchup-01/B/source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz';rows=read(base);chart=read(b/'source-depth-v1/FTN_DEPTH_QB_GAME_INPUTS.json.gz');by={(r['game_id'],r['player_id']):r for r in rows};cb={(r['game_id'],r['player_id']):r for r in chart};index=read(b/'profiles/PROFILE_INDEX_V1.json');profiles=[]
 for a in index['artifacts']:
  p=ROOT/a['path'];assert sha(p)==a['sha256'];z=read(p);pp=z['profiles']if isinstance(z,dict)else z;assert len(pp)==a['profiles'];profiles+=pp
 wanted={(r['game_id'],r['player_id'])for r in rows if r['season']in(2025,2026)};assert len(profiles)==len(wanted)==941
 seen=set();zeros=0;undefined=0;fallbacks={};chartprior=0
 eligible_rows=[r for r in rows if r['physical_participation']and r['target_parity']]
 for p in profiles:
  ident=p['identity'];key=ident['game_id'],ident['player_id'];q=by[key];assert key not in seen;seen.add(key);assert p['query_universe']=='RETROSPECTIVE_OFFICIAL_QB_STAT_ROWS_NOT_EXANTE_ROSTER'
  assert ident['team']==q['team']and ident['opponent']==q['opponent']and ident['cutoff']==q['kickoff']
  cutoff=ident['cutoff'];el=[r for r in eligible_rows if r['available']<cutoff];own=sorted([r for r in el if r['player_id']==q['player_id']],key=lambda r:(r['kickoff'],r['game_id']))[-8:]
  assert p['history']['own']['game_ids']==[r['game_id']for r in own];assert p['history']['global_eligible_QB_games']==len(el)
  oa=svec(own,'context_attempts');oc=svec(own,'context_completions');a=svec(el,'context_attempts');c=svec(el,'context_completions');nt=math.fsum(oa);gt=math.fsum(a)
  for j,x in enumerate(p['contexts']):
   f=x['attempt_frequency'];cr=x['completion_per_attempt'];assert f['numerator']==oa[j]and f['denominator']==nt;assert cr['numerator']==oc[j]and cr['denominator']==oa[j]
   if nt:close(f['estimate'],oa[j]/nt);assert f['state']==('KNOWN_ZERO'if oa[j]==0 else'OBSERVED_POSITIVE')
   else:assert f['estimate']is None and f['state']=='UNDEFINED_ZERO_DENOMINATOR'
   if oa[j]:close(cr['estimate'],oc[j]/oa[j]);zeros+=int(oc[j]==0);assert cr['state']==('KNOWN_ZERO'if oc[j]==0 else'OBSERVED_POSITIVE')
   else:assert cr['estimate']is None;undefined+=1
   close(x['shrunk_attempt_frequency'],(oa[j]+20*(a[j]+1)/(gt+25))/(nt+20));close(x['shrunk_completion_per_attempt'],(oc[j]+20*(c[j]+1)/(a[j]+2))/(oa[j]+20))
  cd=p['charted_depth_annotations']['frozen_depth_describer'];prior=not any(cd['known']);chartprior+=int(prior)
  for j in range(5):
   kn=math.fsum(cb[r['game_id'],r['player_id']]['flags']['is_catchable_ball']['known'][j]for r in own);po=math.fsum(cb[r['game_id'],r['player_id']]['flags']['is_catchable_ball']['positive'][j]for r in own)
   gk=math.fsum(cb[r['game_id'],r['player_id']]['flags']['is_catchable_ball']['known'][j]for r in el);gp=math.fsum(cb[r['game_id'],r['player_id']]['flags']['is_catchable_ball']['positive'][j]for r in el)
   assert cd['known'][j]==kn and cd['positive'][j]==po and cd['pooled_known'][j]==gk and cd['pooled_positive'][j]==gp;close(cd['baseline'][j],(gp+1)/(gk+2));close(cd['shrunk'][j],(po+20*(gp+1)/(gk+2))/(kn+20))
   assert cd['raw'][j]==(po/kn if kn else None)
  assert p['attempts']['past_sum']==math.fsum(r['official_attempts']for r in own)
  assert p['dropbacks']['state']=='UNAVAILABLE_SOURCE_FOR_THIS_PROFILE';assert p['not_supplied']['future_game_script']=='NOT_MODELED'
  assert p['not_supplied']['receiver_alignment']=='SOURCE_BLOCKED'and p['not_supplied']['all_routes']=='SOURCE_BLOCKED'
  f=p['fallback'];fallbacks[f]=fallbacks.get(f,0)+1
 assert seen==wanted
 # New supplied-query adapter checks exercise input guard; source authentication is external.
 from nfl_v2.qb_context_profiles import QBProfileAdapter
 adapter=QBProfileAdapter(rows,depth_annotations=cb);q=min((r for r in rows if r['season']==2026),key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
 clean={k:q[k]for k in('game_id','player_id','season','week','team','opponent','kickoff')};clean['position']='QB';clean['query_evidence']={'canonical_identity_verified':True,'historical_team_verified':True,'eligible_role_verified':True,'source_id':'SYNTHETIC_TEST_MEMBERSHIP_NOT_CAPTURE','source_sha256':'0'*64,'recorded_at':q['kickoff']-3600}
 U='SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE';normal=adapter.build(clean,universe=U);assert normal['status']=='AVAILABLE_PROFILE'
 changed=dict(clean,actual=99999,official_attempts=99999,official_completions=99999,physical_participation=False,context_attempts=[99999]*25,context_completions=[99999]*25);assert adapter.build(changed,universe=U)==normal
 noev=dict(clean);noev.pop('query_evidence');assert adapter.build(noev,universe=U)['status']=='UNAVAILABLE_PROFILE'
 boolq=dict(clean,query_evidence=dict(clean['query_evidence'],recorded_at=True));boolguard=adapter.build(boolq,universe=U)['status']=='UNAVAILABLE_PROFILE'
 r={'id':'B-ASOF-QB-PROFILE-INDEPENDENT-REVIEW-v1','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS_HISTORICAL_PROFILE_ARITHMETIC_WITH_GUARD_DISPOSITION','profiles':len(profiles),'same_universe_ids':True,'source_index_sha256':sha(b/'profiles/PROFILE_INDEX_V1.json'),'base_source_sha256':sha(base),'module_sha256':sha(ROOT/'nfl_v2/qb_context_profiles.py'),'knownzero_completion_contexts':zeros,'undefined_completion_contexts':undefined,'fallback_counts':fallbacks,'no_own_chart_profiles':chartprior,'target_outcome_mutation':'PASS_CURRENT_SUPPLIED_QUERY_NO_TARGET_STAT_REQUIRED','missing_membership':'UNAVAILABLE_PROFILE_AS_REQUIRED','boolean_membership_clock_rejected':boolguard,'remaining_semantic_limits':['Current query source flags/hash are structurally validated but actual roster/source authentication is capture owner responsibility.','Historical941membership remains officialstat-row-conditioned, not authenticatedpregameuniverse.','Dropbacks, role/stint uncertainty, alignment/routes and futuregame-script are not completed by theseprofiles.','EmpiricalBayesintervals are declaredpseudo-count summaries; no predictive/exchangeabilityguarantee.'],'new_NFL_fits':0,'new_forecasts':0,'new_grades':0,'resources':{'wall_seconds':time.monotonic()-started,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}}
 (b/'independent/PROFILE_ARITHMETIC_REVIEW_V1.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'profiles':len(profiles),'status':r['status'],'boolguard':boolguard,'resources':r['resources']}))
if __name__=='__main__':main()
