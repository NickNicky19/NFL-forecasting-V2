"""Independent J synthetic chronology/gate/storage audit; never NFL execution."""
import collections,copy,hashlib,json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];sys.path.insert(0,str(ROOT))
from nfl_v2 import defense_season_executor as r
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fixture():
    rows=[];games={};queries=[]
    for year in(2022,2023,2024):
        for week in range(1,19):
            gid=f'{year}-fixture-{week}';kick=1500000000+(year-2022)*366*86400+week*7*86400;games[gid]=dict(season=year,week=week,kickoff=kick,home='F',away='G');rows.append(dict(season=year,week=week,game_id=gid,player_id='fixture-qb',position='QB',kickoff=kick,available=kick+7*86400,played=True,values={'pass_att':float(week+10)},team='F',defense='G',workload=dict(attempts=week+10,carries=0,targets=0)))
            if year==2024:queries.append(dict(season=year,week=week,game_id=gid,player_id='fixture-qb',position='QB',target='pass_att',population='primary',query_id='fixture-'+str(week)))
    return rows,games,queries
def main():
    rows,games,queries=fixture();roles={'source_role_contract':{'primary':{'pass_att':['QB']},'extended':{}}};factory=lambda *_:(_ for _ in()).throw(AssertionError('No real or spy optimizer allowed'))
    with patch.object(r.laws,'FittedLawModel',side_effect=factory),patch.object(r.source,'make_estimator',side_effect=factory):
        features=r.Features(rows,2024,('pass_att',),roles);q=queries[8];origin=games[q['game_id']]['kickoff'];current=features.origin(2024,9,'pass_att','H-CURRENT-COMMON',origin,[q]);strict=features.origin(2024,9,'pass_att','H-CURRENT-STRICT',origin,[q]);multi=features.origin(2024,9,'pass_att','H-MULTI-COMMON',origin,[q]);assert len(current['train'])==7 and len(strict['train'])==7 and len(multi['train'])==43
        assert current['query_packets'][0][0][1]==3 and current['query_packets'][0][0][3]==8 and strict['query_packets'][0][0][3]==7;assert strict['query_packets'][0][0][0]==16 and strict['query_packets'][0][0][2]==14;assert strict['query_packets'][0][0][5]==14
        changed=copy.deepcopy(rows)
        for x in changed:
            if x['available']>=origin:x['values']['pass_att']=99999.
        modified=r.Features(changed,2024,('pass_att',),roles).origin(2024,9,'pass_att','H-MULTI-COMMON',origin,[q]);assert multi['binding']==modified['binding'];np.testing.assert_equal(multi['query_packets'][0][1],modified['query_packets'][0][1])
        baseline={}
        for week in range(1,19):
            qr=[queries[week-1]];at=games[qr[0]['game_id']]['kickoff']
            for policy in r.plan.policies(2024):baseline[r.slot(week,'pass_att',policy)]=features.origin(2024,week,'pass_att',policy,at,qr)['binding']
        events=list(r.observed_loop(rows=rows,games=games,queries=queries,year=2024,baseline=baseline,role_contract=roles,model_factory=factory,before_fit=lambda:(_ for _ in()).throw(AssertionError('Unexpected optimizer')),guard=lambda:None,targets=('pass_att',)));assert len([e for e in events if e['kind']=='FIT'])==144 and[e['week']for e in events if e['kind']=='WEEK_COMPLETE']==list(range(1,19));assert all(e['model']is None for e in events if e['kind']=='FIT')
        for binding in baseline.values():
            r.compare_retained_fit(binding,dict({k:binding[k]for k in('target','policy_id','training_n','training_membership_sha256','fit_cutoff','feature_floor','prior_parameters','prior_position_sample_counts')},method='leaf'))
        with tempfile.TemporaryDirectory()as tmp:
            tmp=Path(tmp);public=tmp/'public';public.mkdir();(public/'FROZEN_PROTOCOL.json').write_text('{}');fake=tmp/'fake.json';fake.write_text(json.dumps(dict(state=r.retention.GATE_STATE,all_required_archives_verified=True,all_required_members_verified=True,missing_required_parts=0,completed_at_utc='2026-10-30T00:00:00Z')))
            with patch.object(r.seasonal,'load_source',side_effect=AssertionError('NFL source read forbidden')):
                try:r.execute(public=public,private=tmp/'private',source_root=tmp,queries_path=fake,baseline_path=fake,source_protocol_path=fake,baseline_evidence_root=tmp,restoration_gate=fake,verifier_receipt=fake,software_receipt=fake,worker_release=fake)
                except ValueError:pass
                else:raise AssertionError('fabricated restoration admitted')
            assert not(public/'EXECUTION_REGISTRATION.json').exists()
        with tempfile.TemporaryDirectory()as tmp:
            tmp=Path(tmp);public=tmp/'public';public.mkdir();(public/'FROZEN_PROTOCOL.json').write_text('{}');query=queries[0];audit=dict(state='SYNTHETIC_NO_FIT',alias_of=None);eventfit=dict(kind='FIT',slot='fixture',audit=audit,train_features=np.zeros((1,24)),query_features=np.zeros((1,24)),training=[rows[0]],queries=[query],query_packets=[(None,None,None,{})],model=None);fore=dict(query,prediction=0.,actual=11.,fallback='none',procedure_id='synthetic',policy_id='H-CURRENT-COMMON',history_regime='H-CURRENT',product_id='mean',distribution_summary=None);events=iter([eventfit,dict(kind='FORECAST',slot='fixture',records=[fore])]);p=dict(evaluation_season=2024,source_vintage='SYNTHETIC_ONLY',budget=dict(wall_seconds=30,cpu_seconds=30,max_peak_memory_bytes=2**40,max_private_bytes=100000,max_forecast_rows=10,max_fit_calls=1));allbaseline={r.slot(w,t,pol):{}for w in r.WEEKS for t in r.TARGETS for pol in r.plan.policies(2024)};original_open=Path.open
            def fail_forecast(path,*args,**kwargs):
                if path.parent.name=='predictions':raise OSError('synthetic prediction persistence failure')
                return original_open(path,*args,**kwargs)
            with patch.object(r,'_verify_inputs',return_value=(p,{},allbaseline,dict(reconstruction_run_id='fixture'))),patch.object(r.seasonal,'load_source',return_value=(rows,games,{})),patch.object(r,'attach_context_through_year',return_value=rows),patch.object(r,'_read_json',return_value=queries),patch.object(r,'observed_loop',return_value=events),patch.object(r.seasonal.Meter,'add',side_effect=AssertionError('Unretained row scored')),patch.object(Path,'open',fail_forecast):
                receipt=r.execute(public=public,private=tmp/'private',source_root=tmp,queries_path=tmp/'q',baseline_path=tmp/'b',source_protocol_path=tmp/'s',baseline_evidence_root=tmp,restoration_gate=tmp/'g',verifier_receipt=tmp/'v',software_receipt=tmp/'sw',worker_release=Path(__file__))
            assert(public/'fixture-FIT.json').exists()and not(public/'fixture-FORECAST.json').exists();assert receipt['forecast_output_views']==receipt['score_views']==0 and receipt['state']=='PARTIAL_STOPPED';assert json.loads((public/'SCORES.json').read_text())==[]
    out=dict(state='PASS_J_CODE_REVIEW_AND_INDEPENDENT_SYNTHETIC_FIXTURES_NOT_REAL_PREFIT_ADMISSION',executor_sha256=sha(ROOT/'nfl_v2/defense_season_executor.py'),CLI_sha256=sha(ROOT/'tools/run_defense_seasons.py'),protocol_sha256=sha(HERE.parent/'FROZEN_PROTOCOL.json'),checker_sha256=sha(Path(__file__)),synthetic_full18week_origins_checked=144,synthetic_training_n_at_week9=dict(current=7,strict=7,multi=43),verified=['Strict label-availability equality exclusion; row-relative feature cutoff and mean/count/age values.','Current versus strict feature-memory distinction; future/target outcomes do not change earlier binding.','All18weeks preserve query membership; no optimizer/model construction occurs in this fixture.','Actual restoration gate rejects fabricated booleans before source decoding/registration.','Existing fit-schema facts match reconstructed binding without inventing original matrices.','FIT evidence persists, injected forecast persistence failure produces no FORECAST manifest, counter or score.','Source review confirms exact original own20/observedD1D2/role priors and per-year strict floors, independent real-input review and separate root release before actual execution.'],limitations=['This is code/synthetic review only and deliberately does not use PASS_J_SEASONAL_PREFIT_REVIEW required by execute.','No actual source/query/baseline map or complete restoration has been admitted. Exact2022RECENT and chart limitations persist.'],real_NFL_rows_loaded=0,real_NFL_fits=0,real_model_predict_calls=0,new_scientific_scores=0,new_forecasts=0)
    with(HERE/'INDEPENDENT_EXECUTOR_REVIEW.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(dict(state=out['state'],synthetic_origins=144,real_NFL_fits=0,new_scientific_scores=0)))
if __name__=='__main__':main()
