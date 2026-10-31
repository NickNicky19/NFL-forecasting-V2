"""Result-reporting behavior, using fictional aggregates only."""
import unittest
from nfl_v2.result_index import DIAGNOSTIC_KIND,canonical,diagnostic_row,evaluation,hgb_row,software_receipt,validate_index
import hashlib


def row(**changes):
    r=dict(procedure_id='fixture-control',target='rush_yd',product_id='empirical_mean',
        evaluation_panel_id='fixture-same-rows',population='primary_roles',season=2026,week=7,
        n=4,unique_games=2,forecast_rows=5,mae=7.5,rmse=9.,bias=-2.,exact_rate=.25,
        abs_le_10=.75,evidence='FICTIONAL_TEST_ONLY')
    r.update(changes);return r


class ResultIndexTests(unittest.TestCase):
    def test_nested_only_precision_is_searchable_without_top_level_rates(self):
        source=row(n=335,exact_rate=None,abs_le_10=None,
                   precision_counts={'abs_le_1':dict(numerator=33,denominator=335,rate=33/335)})
        r=evaluation(source,'reports/fixture-nested.json')
        validate_index([r])
        value=r['precision_metrics']['abs_le_1']
        self.assertEqual((value['numerator'],value['denominator']),(33,335))
        self.assertEqual(value['rate'],33/335)
        self.assertNotEqual(r['accuracy_status'],'not_reported_no_accuracy_inferred_from_error')
        with self.assertRaisesRegex(ValueError,'rate/count mismatch'):
            evaluation(dict(source,precision_counts={'abs_le_1':dict(numerator=33,denominator=335,rate=1.)}), 'reports/fixture-nested.json')

    def test_nested_zero_sample_precision_is_na_and_not_zero_percent(self):
        source=row(n=0,mae=None,exact_rate=None,abs_le_10=None,
                   precision_counts={'abs_le_1':dict(numerator=0,denominator=0,rate=None)})
        r=evaluation(source,'reports/fixture-empty.json')
        validate_index([r])
        value=r['precision_metrics']['abs_le_1']
        self.assertIsNone(value['rate'])
        self.assertEqual(value['numerator'],0)
        self.assertEqual(value['missing_reason'],'no_eligible_scored_rows_zero_denominator')

    def test_offered_threshold_probability_is_separate_from_native_point_error(self):
        source=row(record_kind='prop_threshold_probability_evaluation',
            product_id='actual_line_categorical_law',target='pass_att',mae=None,mse=None,
            brier=.18,log_loss=.6,probability_conditioning='MODELED_APPEARANCE',
            probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1')
        r=evaluation(source,'reports/fixture-threshold.json')
        validate_index([r])
        self.assertEqual(r['primary_metric'],'brier')
        self.assertEqual(r['primary_error'],.18)
        self.assertEqual(r['native_units'],'probability')
        self.assertIsNone(r['metrics']['mae'])
        self.assertEqual(r['bookmaker_nonvoid_conditioning'],'UNESTABLISHED')
        self.assertEqual(r['probability_conditioning'],'MODELED_APPEARANCE')
        with self.assertRaisesRegex(ValueError,'conditioning'):
            evaluation(dict(source,probability_conditioning='nonvoid'),'reports/fixture.json')
        with self.assertRaisesRegex(ValueError,'point errors'):
            evaluation(dict(source,mae=3),'reports/fixture.json')

    def test_native_errors_are_not_percent_accuracy(self):
        r=evaluation(row(),'reports/fixture.json')
        self.assertEqual(r['primary_error'],7.5)
        self.assertEqual(r['native_units'],'yards')
        self.assertNotIn('accuracy_percent',r)
        self.assertEqual(r['precision_metrics']['exact_rate']['numerator'],1)
        self.assertEqual(r['precision_metrics']['abs_le_10']['numerator'],3)
        self.assertEqual(r['precision_metrics']['exact_rate']['denominator'],4)
        self.assertIn('derived_from_source_rate',r['precision_metrics']['exact_rate']['numerator_provenance'])

    def test_missing_precision_and_error_remain_unknown(self):
        source=row();del source['exact_rate'];del source['abs_le_10'];del source['mae']
        r=evaluation(source,'reports/fixture.json')
        self.assertIsNone(r['primary_error']);self.assertIsNone(r['precision_metrics'])
        self.assertIn('no exact-match',r['accuracy_missing_reason'])
        self.assertIsNotNone(r['metric_missing_reasons']['mae'])

    def test_unknown_or_inconsistent_accuracy_denominator_not_invented(self):
        source=row();del source['n']
        r=evaluation(source,'reports/fixture.json')
        self.assertIsNone(r['precision_metrics']['exact_rate']['numerator'])
        self.assertIsNone(r['precision_metrics']['exact_rate']['denominator'])
        r=evaluation(row(exact_rate=.26),'reports/fixture.json')
        self.assertIsNone(r['precision_metrics']['exact_rate']['numerator'])
        self.assertIn('integer_numerator',r['precision_metrics']['exact_rate']['missing_reason'])

    def test_ids_stable_on_key_order_and_change_with_panel(self):
        a=row();b=dict(reversed(list(a.items())))
        self.assertEqual(evaluation(a,'reports/fixture.json')['test_id'],evaluation(b,'reports/fixture.json')['test_id'])
        self.assertNotEqual(evaluation(a,'reports/fixture.json')['test_id'],
            evaluation(row(evaluation_panel_id='different-outcomes'),'reports/fixture.json')['test_id'])

    def test_probability_residual_is_not_pick_or_classifier_accuracy(self):
        r=evaluation(row(target='anytime_td',brier=.16,log_loss=.5),'reports/fixture.json')
        self.assertEqual(r['primary_metric'],'brier')
        self.assertIn('without_registered_binary',r['accuracy_status'])
        self.assertIn('not_binary_accuracy',r['precision_metrics']['exact_rate']['kind'])

    def test_software_has_check_counts_and_no_nfl_accuracy(self):
        r=software_receipt('reports/fixture-software.json',dict(tests_run=8,status='PASS'))
        self.assertEqual(r['software_checks'],8)
        self.assertIsNone(r['metrics']);self.assertIsNone(r['n']);validate_index([r])
        r['n']=8
        with self.assertRaises(ValueError):validate_index([r])

    def test_bad_values_unsafe_paths_and_duplicate_views_rejected(self):
        for changes in [dict(exact_rate=1.1),dict(n=-1),dict(mae=-1),dict(mae=float('nan'))]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):evaluation(row(**changes),'reports/fixture.json')
        for path in ['/workspace/private.json','../private.json','s3://bucket/row.json']:
            with self.subTest(path=path),self.assertRaises(ValueError):evaluation(row(),path)
        r=evaluation(row(),'reports/fixture.json')
        with self.assertRaises(ValueError):validate_index([r,r])

    def test_signed_bias_and_source_distribution_nll_preserved(self):
        r=evaluation(row(NLL=-.2),'reports/fixture.json')
        self.assertEqual(r['metrics']['bias'],-2.)
        self.assertEqual(r['metrics']['nll'],-.2)
        self.assertEqual(r['metrics']['mae'],7.5)

    def test_infinite_probability_losses_remain_explicit(self):
        r=evaluation(row(target='anytime_td',log_loss=float('inf'),infinite_NLL=2),'reports/fixture.json')
        self.assertIsNone(r['metrics']['log_loss'])
        self.assertEqual(r['metric_status']['log_loss'],'positive_infinite_loss')
        self.assertIn('infinite_loss',r['metric_missing_reasons']['log_loss'])
        self.assertEqual(r['source_infinite_nll_rows'],2)

    def test_added_diagnostic_dimensions_preserve_legacy_stable_ids(self):
        source=row();r=evaluation(source,'reports/fixture.json')
        old_identity=dict(source_record_id=None,source_pointer=None,procedure_id='fixture-control',category='rush_yd',
            product_id='empirical_mean',evaluation_panel_id='fixture-same-rows',population='primary_roles',
            period=None,season=2026,week=7,history_regime='UNKNOWN_NOT_H_CLASSIFIED')
        expected='TEST-'+hashlib.sha256(canonical(['reports/fixture.json',old_identity]).encode()).hexdigest()[:20]
        self.assertEqual(r['test_id'],expected)

    def test_diagnostic_views_keep_roles_dates_and_infinite_failures(self):
        raw=dict(target='anytime_td',population='primary',history_regime='H-CURRENT',product='event_probability',
            season='2026',week='ALL',position='ALL',fallback_view='ALL',scored_n='10',forecast_queries='12',
            fallback_n='3',mae='.2',brier='.1',log_loss='',infinite_log_losses='2',exact_rate='.8')
        source,dates=diagnostic_row(raw,{'2026':[1,2,3,4,5,6,7]})
        r=evaluation(source,'reports/diagnostic.csv',year_record=dates)
        self.assertEqual(r['kind'],DIAGNOSTIC_KIND);self.assertEqual(r['n'],10)
        self.assertEqual(r['weeks'],[1,2,3,4,5,6,7]);self.assertEqual(r['source_infinite_nll_rows'],2)
        self.assertEqual(r['metric_status']['log_loss'],'positive_infinite_loss')
        self.assertIn('QB+RB',r['cohort_limit']);validate_index([r])

    def test_hgb_adapter_retains_objective_history_memory_and_unknown_games(self):
        raw=dict(target='rush_att',population='primary',history_regime='H-CURRENT',objective='absolute_error_point',
            week='ALL',position='ALL',scored_n=4,forecast_queries=5,fallback_n=2,constant_zero_n=1,
            mae=2.,mse=5.,exact_rate=.25)
        source,dates=hgb_row(raw);r=evaluation(source,'reports/hgb/SCORES.json',year_record=dates)
        self.assertEqual(r['kind'],DIAGNOSTIC_KIND);self.assertEqual(r['n'],4)
        self.assertEqual(r['product_id'],'absolute_error_point');self.assertEqual(r['fallback_rows'],2)
        self.assertEqual(r['coverage_source']['constant_zero_n'],1)
        self.assertIn('not pure',r['feature_memory_policy'])
        self.assertEqual(r['weeks'],list(range(1,8)))
        self.assertIsNone(r['games']);self.assertIsNotNone(r['games_missing_reason'])
        validate_index([r])

    def test_hgb_adapter_rejects_probability_point_contract_mix(self):
        raw=dict(target='anytime_td',population='primary',history_regime='H-MULTI',objective='absolute_error_point',
            week='7',position='ALL',scored_n=4,forecast_queries=4,fallback_n=0)
        with self.assertRaises(ValueError):hgb_row(raw)


if __name__=='__main__':unittest.main()
