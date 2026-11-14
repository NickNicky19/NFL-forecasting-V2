"""Targeted additions:16numericpools and profileguard/metadata; reuse earlierchecks."""
import datetime,gzip,hashlib,importlib.util,json,math,sys,time,resource
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT));b=ROOT/'reports/player-context-completion-decision-01/B';ind=b/'independent'
spec=importlib.util.spec_from_file_location('independent_full_math',ind/'verify_full_scores_v1.py');v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
started=time.monotonic();scores=v.read(b/'numerical-pools-v1/SCORES.json');balanced=v.read(b/'numerical-pools-v1/SEASON_BALANCED_SUMMARY_V1.json');raw=[r for p in sorted((b/'depth-wave-v2/predictions').glob('*.json.gz'))for r in v.read(p)['rows']];summaries=[]
for s in scores:
 rr=[r for r in raw if r['procedure_id']==s['procedure_id']and(s['week']=='FULL_2025_PLUS_2026_W1_W8'or r['week']<=8)];assert s['n']in(573,941);assert set(r['season']for r in rr)=={2025,2026};v.numcheck(s,rr)
 p=s['product_id'];season_values=[];ns=[]
 for season in(2025,2026):
  ee=[abs(r[p]-r['actual'])for r in rr if r['season']==season and r['actual']is not None];season_values.append(math.fsum(ee)/len(ee));ns.append(len(ee))
 z=next(z for z in balanced if z['procedure_id']==s['procedure_id']and z['panel']==s['week']and z['product']==p);assert z['seasons']==[2025,2026]and z['weights']==[.5,.5]and z['season_n']==ns;v.eq(z['micro_MAE'],s['mae']);v.eq(z['equal_season_MAE'],math.fsum(season_values)/2);v.eq(z['micro_MAE'],math.fsum(a*n for a,n in zip(season_values,ns))/sum(ns));assert z['micro_n']==sum(ns)
 summaries.append({'procedure':s['procedure_id'],'panel':s['week'],'product':p,'n':s['n'],'season_n':ns,'micro_MAE':s['mae'],'equal_season_MAE':z['equal_season_MAE']})
assert len(summaries)==16
from nfl_v2.qb_context_profiles import QBProfileAdapter
rows=v.read(ROOT/'reports/player-context-matchup-01/B/source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz');chart=v.read(b/'source-depth-v1/FTN_DEPTH_QB_GAME_INPUTS.json.gz');cb={(r['game_id'],r['player_id']):r for r in chart};adapter=QBProfileAdapter(rows,depth_annotations=cb);q=min((r for r in rows if r['season']==2026),key=lambda r:(r['kickoff'],r['game_id'],r['player_id']));clean={k:q[k]for k in('game_id','player_id','season','week','team','opponent','kickoff')};clean['position']='QB';clean['query_evidence']={'canonical_identity_verified':True,'historical_team_verified':True,'eligible_role_verified':True,'source_id':'SYNTHETIC_TEST_MEMBERSHIP_NOT_CAPTURE','source_sha256':'0'*64,'recorded_at':q['kickoff']-3600};U='SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE';ordinary=adapter.build(clean,universe=U);assert ordinary['status']=='AVAILABLE_PROFILE'
clockchecks=[]
for x in(True,None,float('nan'),float('inf'),q['kickoff']+1):
 bad=dict(clean,query_evidence=dict(clean['query_evidence'],recorded_at=x));z=adapter.build(bad,universe=U);assert z['status']=='UNAVAILABLE_PROFILE';clockchecks.append({'clock_case':'BOOL'if x is True else'NULL'if x is None else'NONFINITE'if not math.isfinite(x)else'AFTER_CUTOFF','status':z['status'],'reason':z['reason']})
overlay=v.read(b/'profiles/PROFILE_CONSUMPTION_QUALIFICATION_V2.json');assert v.sha(ROOT/overlay['source_profile_index']['path'])==overlay['source_profile_index']['sha256'];allids=[]
for entry in overlay['source_chunks']:
 pp=ROOT/entry['path'];assert v.sha(pp)==entry['sha256'];ss=v.read(pp);ss=ss['profiles']if isinstance(ss,dict)else ss;assert len(ss)==entry['profiles']
 for x in ss:assert x['consumed_by_frozen_forecasts']['charting_limits']==overlay['original'];allids.append(x['profile_id'])
assert len(allids)==len(set(allids))==overlay['profile_count']==941
assert 'no-pooled-known indicator is consumed'in overlay['qualified_current']and'five-field support'in overlay['qualified_current'];assert ordinary['consumed_by_frozen_forecasts']['charting_limits']==overlay['qualified_current']
result={'id':'B-POOL-AND-PROFILE-GUARD-INDEPENDENT-v1','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'PASS','numeric_pool_scores_sha256':v.sha(b/'numerical-pools-v1/SCORES.json'),'balanced_summary_sha256':v.sha(b/'numerical-pools-v1/SEASON_BALANCED_SUMMARY_V1.json'),'pooled_views_checked':16,'rows':summaries,'profile_current_module_sha256':v.sha(ROOT/'nfl_v2/qb_context_profiles.py'),'profile_metadata_overlay_sha256':v.sha(b/'profiles/PROFILE_CONSUMPTION_QUALIFICATION_V2.json'),'profile_guard_checks':clockchecks,'unchanged_profile_chunks':26,'unchanged_profile_ids':941,'prior_profile_arithmetic_receipt':'PROFILE_ARITHMETIC_REVIEW_V1.json reused; no941profile regeneration/recheck','scope':'Poolednumericalviews are notactual-offerpooledperformance. Both declaredyears kept; currentW1-8 remainsvisible separately. Boolguard andconsumptionprose repair changes nofrozenprofiles/features/forecasts/grades.','fits':0,'new_NFL_observations':0,'new_original_forecasts':0,'resources':{'wall_seconds':time.monotonic()-started,'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}}
(ind/'POOL_AND_PROFILE_GUARD_REVIEW_V1.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps({'state':'PASS','numericpools':16,'profile_guard':len(clockchecks),'profilechunks':26,'resources':result['resources']}))
