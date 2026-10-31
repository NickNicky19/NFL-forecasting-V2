"""Independent synthetic feature/window algebra and unexecuted-plan accounting."""
import argparse,collections,csv,hashlib,json,math,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;PUB=HERE.parent/'d1d2-season-execution-readiness/metadata-preflight-v1'
sys.path.insert(0,str(ROOT))
from nfl_v2 import defense_season_preflight as adapter
from nfl_v2.qualified_defense import game_observation
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--receipt',type=Path,default=HERE/'DEFENSE_READINESS_INDEPENDENT_REVIEW.json');args=ap.parse_args();r=read(PUB/'PREFLIGHT_RECEIPT.json')
    for b in r['source_bindings']:assert sha(ROOT/b['path'])==b['sha256']
    for s in r['seasons']:assert sha(ROOT/s['original_season_protocol'])==s['original_season_protocol_sha256'];assert s['actual_new_fits']==s['actual_new_forecasts']==s['actual_closed_season_cells']==0
    with(PUB/'FINITE_FIT_ORIGIN_PLAN.csv').open()as f:rows=list(csv.DictReader(f))
    years={s['season']:s for s in r['seasons']};counts=collections.Counter();unique=collections.defaultdict(set);outputs=collections.Counter()
    for z in rows:
        year=int(z['season']);window=z['window'];assert z['state']=='FIT_REQUIRED_RUNNER_INTEGRATION_AND_RECOVERY_GATE';counts[window]+=1;unique[window].add((year,int(z['week']),z['target'],z['information_group'],z['fit_alias_policy']));outputs[window]+=1 if z['target']=='anytime_td'else 2
        policies=adapter.policies(year);arm,floor,memory=policies[z['policy_id']];assert arm==z['history_regime']and floor==int(z['fit_floor'])and memory==int(z['feature_floor']);assert floor>=2022 and memory in(2022,year)
        if year==2022 and arm=='H-RECENT':assert z['recent2022_status']=='SOURCE_LIMITED_EXPANDING_FROM2022_PROXY_NOT_PRIOR_YEAR'
    assert set(counts)=={'observed','scheduled'}and set(counts.values())=={6912};assert{len(v)for v in unique.values()}=={5184};assert set(outputs.values())=={13248}
    day=86400;base=datetime(2024,9,1,tzinfo=timezone.utc).timestamp();games=[];obs=[]
    for i,(year,offset,value,n)in enumerate([(2023,-365,9,10),(2024,10,10,20),(2024,20,None,None),(2024,30,20,40),(2024,40,30,60),(2024,50,40,80)]):
        ko=base+offset*day;game='independent-fixture-'+str(i);games.append(dict(game_id=game,season=year,week=max(1,i),kickoff=ko,home='AAA',away='BBB',period='REG'))
        if value is not None:obs.append(game_observation([dict(game_id=game,season=year,position='QB',player_id='fixture-QB-'+str(i),defense='AAA',kickoff=ko,available=ko+7*day,played=True,values={'pass_cmp':value},workload={'attempts':n})],'pass_cmp'))
    strict={};common={}
    for window in ['observed','scheduled']:
        strict[window],audit=adapter.SeasonBoundDefenseHistory(obs,games,year=2024,feature_floor=2024,window=window).at('AAA','QB','pass_cmp',base+57*day)
        common[window],_=adapter.SeasonBoundDefenseHistory(obs,games,year=2024,feature_floor=2022,window=window).at('AAA','QB','pass_cmp',base+57*day)
        assert strict[window]['qualified_allowed_mean4']==20 and strict[window]['complete_target_games4']==3
        assert math.isclose(strict[window]['shrunk_allowed_per_opportunity4'],.5,abs_tol=1e-12)
        assert 'independent-fixture-5'not in audit['local_game_ids'];assert audit['feature_floor']==audit['source_filter_floor']==2024 and audit['implementation_floor_token']==2022
        earlier,a=adapter.SeasonBoundDefenseHistory(obs,games,year=2024,feature_floor=2024,window=window).at('AAA','QB','pass_cmp',base+47*day);assert earlier['qualified_allowed_mean4']==15 and'independent-fixture-4'not in a['local_game_ids']
        if window=='scheduled':assert audit['absent_group_game_ids']==['independent-fixture-2']and audit['local_game_slots']==4
    assert common['observed']['qualified_allowed_mean4']==17.25
    assert math.isclose(common['scheduled']['shrunk_allowed_per_opportunity4'],(20*(69/130)+60)/140,abs_tol=1e-12)
    assert common['scheduled']['shrunk_allowed_per_opportunity4']!=strict['scheduled']['shrunk_allowed_per_opportunity4']
    receipt=dict(state='PASS_INDEPENDENT_D1_D2_SEASON_BOUND_FEATURE_ALGEBRA_AND_PLAN_COUNTS',preflight_receipt_sha256=sha(PUB/'PREFLIGHT_RECEIPT.json'),plan_sha256=sha(PUB/'FINITE_FIT_ORIGIN_PLAN.csv'),source_code_hash_bindings=len(r['source_bindings']),logical_origin_cells_per_window=dict(counts),unique_computational_origins_per_window={k:len(v)for k,v in unique.items()},output_views_per_window=dict(outputs),independent_fixture_target='pass_cmp',fixture_strict_mean=20,fixture_strict_conversion_rate=.5,fixture_missing_group_slots_preserved=True,fixture_exact_availability_excluded=True,fixture_older_league_prior_removed=True,new_NFL_observations=0,new_fits=0,new_model_inference=0,new_scores=0,readiness='SYNTHETIC_ADAPTER_AND_METADATA_PLAN_ONLY; NO_FULL_RUNNER_INTEGRATION_OR_ADMISSION',history2022='RECENT_PROXY_NOT_EXACT_PRIOR_YEAR',limits=['Computationaloriginsarenotactualfitcalls;startupmayabstain/usefallback.','Eachwindowhas13248plannedoutputviews;thetwoalternativewindowsmustnotbeconflated.','Recovery/admission,exactsourcequerypopulation,learnerintegrationandchartqualificationstillrequired.'])
    with args.receipt.open('x')as f:json.dump(receipt,f,indent=2);f.write('\n')
    print(json.dumps(receipt))
if __name__=='__main__':main()
