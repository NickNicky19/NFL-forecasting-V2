"""Independent narrow V2 fault replay; no real model/NFL source calls."""
import ast,hashlib,importlib.util,json,tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
s=importlib.util.spec_from_file_location('independent_J_fixture',HERE/'check_executor.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);r=m.r
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    oldpath=HERE.parent/'correction-v2/source-v1/defense_season_executor.py.txt';newpath=ROOT/'nfl_v2/defense_season_executor.py';old=ast.parse(oldpath.read_text());new=ast.parse(newpath.read_text());nodes=lambda tree:{n.name:ast.dump(n,include_attributes=False)for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))};a,b=nodes(old),nodes(new);unchanged=['Features','attach_context_through_year','prepare','check_baseline','compare_retained_fit','reconstruct_baseline_metadata','_verify_inputs','code_bindings'];assert all(a[k]==b[k]for k in unchanged);assert r.VERSION.endswith('v2');assert sha(oldpath)=='07b821211cd1649342a2b615120d85f165880437e2447fc1b847b64666a5f2e6'
    rows,games,queries=m.fixture();results=[]
    for fault in('FIRST_FIT_EVIDENCE_SAVE','POST_FIT_GUARD'):
        cell=r.slot(1,'pass_att','H-MULTI-COMMON')+('-D1'if fault=='FIRST_FIT_EVIDENCE_SAVE'else'-D2')
        with tempfile.TemporaryDirectory()as tmp:
            d=Path(tmp);pub=d/'pub';pub.mkdir();(pub/'FROZEN_PROTOCOL.json').write_text('{}');p=dict(evaluation_season=2024,source_vintage='SYNTHETIC_ONLY',budget=dict(wall_seconds=20,cpu_seconds=20,max_peak_memory_bytes=2**40,max_private_bytes=1,max_forecast_rows=10,max_fit_calls=1));bas={r.slot(w,t,pol):{}for w in r.WEEKS for t in r.TARGETS for pol in r.plan.policies(2024)}
            def events(**kw):
                yield dict(kind='FIT_REGISTERED',slot=cell)
                kw['before_fit']()
                yield dict(kind='FIT_STARTED',slot=cell)
                if fault=='POST_FIT_GUARD':raise RuntimeError('TIME_BUDGET')
                yield dict(kind='FIT',slot=cell,audit=dict(state='FITTED_RETAINED',alias_of=None),train_features=np.zeros((1,24)),query_features=np.zeros((1,24)),training=[rows[0]],queries=[queries[0]],query_packets=[(None,None,None,{})],model=None)
            with patch.object(r,'_verify_inputs',return_value=(p,{},bas,dict(reconstruction_run_id='synthetic-retention-v2'))),patch.object(r.seasonal,'load_source',return_value=(rows,games,{})),patch.object(r,'attach_context_through_year',return_value=rows),patch.object(r,'_read_json',return_value=queries),patch.object(r,'observed_loop',side_effect=events),patch.object(r.laws,'FittedLawModel',side_effect=AssertionError('Real model forbidden')):
                z=r.execute(public=pub,private=d/'priv',source_root=d,queries_path=d/'q',baseline_path=d/'b',source_protocol_path=d/'s',baseline_evidence_root=d,restoration_gate=d/'g',verifier_receipt=d/'v',software_receipt=d/'sw',worker_release=newpath)
            grid=json.loads((pub/'GRID_STATUS.json').read_text());g=next(x for x in grid if x['slot']==cell);assert g['state']=='FIT_ATTEMPTED_UNRETAINED'and g['fit_attempted']is True and g['evidence_state']=='UNRETAINED_OR_INCOMPLETE';assert z['actual_fit_calls']==z['fit_attempted_cells']==z['unretained_fit_attempt_cells']==1 and z['forecast_output_views']==z['score_views']==0;assert all(x['state']=='NOT_RUN_AFTER_BOUNDED_STOP'for x in grid if x['slot']!=cell);results.append(dict(fault=fault,state=g['state'],algorithm_state=g['algorithm_state'],attempts=1,scores=0))
    out=dict(state='PASS_INDEPENDENT_J_V2_ATTEMPT_STATE_REPAIR_NOT_REAL_PREFIT_ADMISSION',executor_v1_sha256=sha(oldpath),executor_v2_sha256=sha(newpath),correction_protocol_sha256=sha(HERE.parent/'correction-v2/FROZEN_PROTOCOL_V2.json'),checker_sha256=sha(Path(__file__)),prior_failure_witness_sha256=sha(HERE/'FIT_RETENTION_ATTEMPT_STATE_LIMITATION.json'),unchanged_mathematical_gate_and_metadata_units=unchanged,faults=results,scope='Confirms the observed V1 bookkeeping loss is repaired for first FIT-evidence persistence and post-fit guard failure; attempted identities remain distinct from unrun cells. Existing mathematical feature/prior/source/gate code ASTs unchanged. Original V1 sources and reviews remain retained.',new_NFL_fits=0,new_real_model_calls=0,new_forecasts=0,new_scientific_scores=0,actual_worker_admitted=False)
    with(HERE/'ATTEMPT_STATE_V2_INDEPENDENT_REVIEW.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(dict(state=out['state'],faults_repaired=2,executor_v2_sha256=out['executor_v2_sha256'])))
if __name__=='__main__':main()
