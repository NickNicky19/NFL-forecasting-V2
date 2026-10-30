"""Fictional source/clock/software fixtures; no model optimization or NFL data."""
import math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from nfl_v2.count_ablations import (RA,POISSON,POLICIES,COUNT_TARGETS,Budget,Metrics,
    eligible_indices,feature_history,fit_state,make_estimator,output_count,predict_admitted,
    procedure_id,training_roles,prepare)
from nfl_v2.hgb_control import canonical,sha
from nfl_v2.result_index import evaluation,validate_index


class CountAblationTests(unittest.TestCase):
    def test_specialization_changes_training_roles_without_dropping_queries(self):
        p={'source_role_contract':{'primary':{'rush_att':['RB']},'extended':{'rush_att':['QB','WR','TE']}}}
        self.assertEqual(training_roles(p,'rush_att',RA),{'QB','RB'})
        self.assertEqual(training_roles(p,'rush_att',POISSON),{'QB','RB','WR','TE'})
        self.assertEqual(output_count([{'target':'rush_att','position':'TE'},{'target':'rec'}]),12)
        with self.assertRaises(ValueError):training_roles(p,'rec',RA)

    def test_fixed_fit_windows_and_strict_left_availability(self):
        rows=[dict(season=y,available=a)for y,a in [(2022,1),(2025,2),(2026,3),(2026,4),(2027,1)]]
        self.assertEqual(eligible_indices(rows,4,2026).tolist(),[2])
        self.assertEqual(eligible_indices(rows,4,2025).tolist(),[1,2])
        self.assertEqual(eligible_indices(rows,4,2022).tolist(),[0,1,2])

    def test_strict_feature_memory_never_reads_old_outcome(self):
        rows=[dict(player_id='fictional',season=y,available=a,kickoff=k,game_id=str(y),values={'rush_att':v})
            for y,a,k,v in [(2025,20.,10.,99.),(2026,40.,30.,2.)]]
        common=feature_history(rows,2022);strict=feature_history(rows,2026)
        self.assertEqual(common.get('fictional','RB','rush_att',41.)[0][0],50.5)
        f,m=strict.get('fictional','RB','rush_att',40.);self.assertTrue(math.isnan(f[0]));self.assertIsNone(m)
        self.assertEqual(strict.get('fictional','RB','rush_att',41.)[0][0],2.)

    def test_estimator_objectives_and_fixed_params_without_fitting(self):
        l1,poisson=make_estimator(RA),make_estimator(POISSON)
        self.assertEqual(l1.loss,'absolute_error');self.assertEqual(poisson.loss,'poisson')
        for m in (l1,poisson):
            self.assertEqual(m.max_iter,64);self.assertEqual(m.max_depth,3)
            self.assertEqual(m.min_samples_leaf,10);self.assertEqual(m.l2_regularization,10)
            self.assertFalse(hasattr(m,'_predictors'))
        self.assertEqual(fit_state(np.zeros(40),POISSON),'NO_FIT_ALL_ZERO_COUNT')
        self.assertEqual(fit_state(np.zeros(40),RA),'FIT_ELIGIBLE')
        self.assertEqual(fit_state(np.ones(39),RA),'NO_FIT_INSUFFICIENT_TRAINING')

    def test_blocked_missing_position_excluded_before_estimator_inference(self):
        class Spy:
            def __init__(self):self.seen=[]
            def predict(self,x):self.seen.append(x.copy());return np.arange(len(x))+2.
        spy=Spy();x=np.asarray([[1.,2.],[math.nan,math.nan],[3.,4.]])
        queries=[{'blocked_reason':None},{'blocked_reason':'UNKNOWN_IDENTITY','position':None},{'blocked_reason':None}]
        self.assertEqual(predict_admitted(spy,x,queries),[2.,None,3.])
        np.testing.assert_array_equal(spy.seen[0],x[[0,2]])
        spy=Spy();self.assertEqual(predict_admitted(spy,x[1:2],queries[1:2]),[None]);self.assertEqual(spy.seen,[])

    def test_preflight_counts_exact224_cells_and_no_mean_median_inflation(self):
        queries=[{'target':t}for t in COUNT_TARGETS]
        self.assertEqual(output_count(queries),28)
        self.assertEqual(8*output_count(queries),224)
        self.assertEqual(len(POLICIES),4)
        self.assertNotEqual(procedure_id(RA,2022),procedure_id(RA,2026))

    def test_fit_private_and_output_guards_fail_before_budget_overrun(self):
        limits=dict(max_forecast_rows=2,max_fit_calls=1,max_private_bytes=10,wall_seconds=100,cpu_seconds=100,max_peak_memory_bytes=1<<60)
        b=Budget(limits);b.charge_fit()
        with self.assertRaises(RuntimeError):b.charge_fit()
        self.assertEqual(b.fits,1);b.charge_private(10)
        with self.assertRaises(RuntimeError):b.charge_private(1)
        self.assertEqual(b.private_bytes,10);b.outputs.reserve(2)
        with self.assertRaises(RuntimeError):b.outputs.reserve(1)
        self.assertEqual(b.outputs.reserved,2)

    def test_native_point_metrics_keep_zero_missing_coverage_and_unique_games(self):
        m=Metrics()
        for y,p,fb,g in [(0.,2.,'none','g1'),(None,4.,'none','g2'),(3.,1.,'constant_zero','g1')]:
            m.add(dict(actual=y,prediction=p,fallback=fb,game_id=g))
        r=m.result('rush_att');self.assertEqual(r['n'],2);self.assertEqual(r['mae'],2.)
        self.assertEqual(r['unique_games'],1);self.assertEqual(r['coverage']['forecast_games'],2)
        self.assertEqual(r['coverage']['played_missing_rows'],1);self.assertEqual(r['fallback_rows'],1)
        row=dict(procedure_id=procedure_id(RA,2026),target='rush_att',product_id='absolute_loss_point',evaluation_panel_id='fictional',population='fictional',season=2026,week=1,history_regime='H-CURRENT',**r)
        validate_index([evaluation(row,'reports/fictional/SCORES.json')])

    def test_preparation_binds_shared_origin_before_any_source_values_or_fits(self):
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);old=root/'old';old.mkdir();shared=root/'shared';shared.mkdir();cache=root/'source';cache.mkdir()
            roles={'primary':{t:['QB']if t.startswith('pass_')else['RB']for t in COUNT_TARGETS},'extended':{t:[]for t in COUNT_TARGETS}}
            base=dict(source_ids=[],source_role_contract=roles)
            (old/'FROZEN_PROTOCOL.json').write_bytes(canonical(base))
            (old/'WEEK8_CAPTURE_RECEIPT.json').write_bytes(canonical(dict(cutoff_utc='2020-10-29T23:16:00Z')))
            q=dict(query_id='fictional',target='rush_att',owner_input_cutoff_utc='2020-11-01T16:30:00Z',game_id='fictional-game')
            (shared/'queries.json').write_bytes(canonical(dict(historical=[],week8=[q])))
            (shared/'protocol.json').write_bytes(canonical(dict(frozen_queries_sha256=sha(shared/'queries.json'),source_ids=[])))
            (shared/'execution.json').write_bytes(canonical(dict(protocol_sha256=sha(shared/'protocol.json'),actual_week8_feature_origin='2020-10-30T00:27:00Z')))
            with patch('nfl_v2.count_ablations.source.schedules',return_value={}):
                p=prepare(source_root=cache,old_protocol=old/'FROZEN_PROTOCOL.json',shared_queries=shared/'queries.json',shared_protocol=shared/'protocol.json',shared_execution=shared/'execution.json',public_root=root/'public',private_root=root/'private',source_artifact_id='FICTIONAL')
            self.assertEqual(p['new_fits_before_registration'],0);self.assertEqual(len(p['grid']),224)
            self.assertEqual(p['shared_week8_feature_origin_utc'],'2020-10-30T00:27:00Z')
            self.assertEqual(p['expected_output_rows'],8);self.assertFalse(p['official_capture'])


if __name__=='__main__':unittest.main()
