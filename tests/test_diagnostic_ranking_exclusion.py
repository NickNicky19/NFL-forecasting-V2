"""Outcome-conditioned error patterns remain searchable without entering ranks."""
import unittest
from nfl_v2.result_index import RIGHT_WRONG_KIND,evaluation,validate_index,is_championship_eligible
from tests.test_result_index import row
from tools.build_test_index_v2 import current_flat
from tools.build_current_valid_view_v2 import admissible_lineage
from tools.build_test_index_v3 import diagnostic_control_mask_annotation


class DiagnosticExclusionTests(unittest.TestCase):
    def sample(self,**changes):
        return row(record_kind=RIGHT_WRONG_KIND,diagnostic_only=True,default_rank_eligible=False,
                   conditioning='SELECTED_SIDE_AND_REALIZED_OUTCOME',diagnostic_bucket='OVER_WIN',
                   diagnostic_dimension='BUCKET',diagnostic_band='ALL',**changes)

    def test_searchable_distinct_identity_and_rank_exclusion(self):
        a=evaluation(self.sample(max_abs_error=12.5),'reports/fixture-diagnostic.json')
        b=evaluation(dict(self.sample(),diagnostic_bucket='OVER_LOSS'),'reports/fixture-diagnostic.json')
        validate_index([a,b])
        self.assertEqual(a['metrics']['max_abs'],12.5)
        self.assertNotEqual(a['test_id'],b['test_id'])
        for value in(a,current_flat(a),dict(a,source_aggregate_fields=self.sample())):
            self.assertIs(value['diagnostic_only'],True)
            self.assertIs(value['default_rank_eligible'],False)
            self.assertFalse(is_championship_eligible(value))
            self.assertFalse(admissible_lineage(dict(value,evidence='NEW_EXPERIMENT')))
        self.assertTrue(admissible_lineage(dict(evidence='NEW_EXPERIMENT')))

    def test_missing_exclusion_cannot_silently_create_a_champion(self):
        for changes in({'diagnostic_only':False},{'default_rank_eligible':True},{'conditioning':'PREGAME'}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                evaluation(dict(self.sample(),**changes),'reports/fixture-diagnostic.json')
        a=evaluation(self.sample(),'reports/fixture-diagnostic.json')
        with self.assertRaises(ValueError):validate_index([dict(a,default_rank_eligible=True)])
        self.assertFalse(is_championship_eligible({'source_aggregate_fields':self.sample()}))

    def test_masked_control_is_not_reported_as_missing_forecasts(self):
        record=evaluation(self.sample(procedure_id='SAVED_FIXTURE',outer_opportunities=5,
                          source_admitted_forecasts=4,full_source_coverage=.8),'reports/fixture-diagnostic.json')
        addition=dict(correction_kind='COVERAGE_SCOPE_METADATA_ONLY_NO_NUMERIC_OR_PREDICTION_CHANGE',
            default_rank_eligible=False,coverage_scope='INHERITED_FOCAL_COMPARISON_MASK',
            comparison_mask_outer_offer_rows=5,comparison_mask_admitted_forecasts=4,
            comparison_mask_fraction=.8,original_full_source_coverage=.8,masked_out_or_missing_control_rows=1,
            full_source_coverage_semantics='inherited mask fraction only',standalone_forecast_availability=None,
            standalone_forecast_unavailable_count=None,standalone_availability_null_reason='not established')
        fixed=diagnostic_control_mask_annotation(record,addition)
        self.assertEqual(fixed['metrics'],record['metrics'])
        self.assertIsNone(fixed['standalone_forecast_unavailable_count'])
        self.assertNotIn('coverage_scope',record)
        self.assertEqual(current_flat(fixed)['coverage_scope'],'INHERITED_FOCAL_COMPARISON_MASK')
        with self.assertRaises(ValueError):
            diagnostic_control_mask_annotation(record,dict(addition,comparison_mask_fraction=1.))
        with self.assertRaises(ValueError):
            diagnostic_control_mask_annotation(record,dict(addition,standalone_forecast_unavailable_count=1))
