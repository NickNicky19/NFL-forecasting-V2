import unittest
from tools.build_test_index_v3 import separate_ancillary_point_metrics,qualify_registered_rolling_rank,qualify_bound_source_horizon,apply_source_vintage_annotation

class AncillaryAttribution(unittest.TestCase):
 def test_event_metrics_not_promoted_to_constant_numeric_ranking(self):
  r=dict(record_kind='prop_selection_evaluation',product_id='constant_side_or_original_prior',mae=1.1,bias=-.2,selection_metrics=dict(WIN=6,LOSS=7))
  metrics={key:r.get(key)for key in ['mae','mse','rmse','bias','p90_abs','p95_abs','max_abs']};a=dict(ancillary_point_attribution=dict(kind='ORIGINAL_B0_MEAN_REFERENCE_NOT_THIS_EVENT_PRODUCT',original_metrics=metrics));q=separate_ancillary_point_metrics(r,a)
  self.assertEqual(r['mae'],1.1);self.assertIsNone(q['mae']);self.assertEqual(q['ancillary_point_reference_metrics']['mae'],1.1);self.assertEqual(q['selection_metrics'],r['selection_metrics'])
  a['ancillary_point_attribution']['original_metrics']['mae']=0
  with self.assertRaises(ValueError):separate_ancillary_point_metrics(r,a)
 def test_rolling_rank_cannot_be_relabelled_as_another_K_or_fixed_weekly(self):
  r=dict(record_kind='prop_selection_evaluation',strategy='ROLLING_K6_over',K=None)
  a=dict(registered_rolling_rank=dict(K=6,side_pool='over',rank_scope='PER_CATEGORY_PER_WEEK_ROLLING_DECISION_BATCHES'))
  self.assertEqual(qualify_registered_rolling_rank(r,a)['K'],6)
  a['registered_rolling_rank']['K']=10
  with self.assertRaises(ValueError):qualify_registered_rolling_rank(r,a)
 def test_probability_source_clock_correction_requires_original_binding(self):
  r=dict(record_kind='prop_threshold_probability_evaluation',horizon_id='INHERITED_C_PANEL',source_vintage='INHERITED')
  a=dict(source_vintage='B_ORIGINAL_CAPTURE_PLUS_RETROSPECTIVE_RULE',original_source_vintage='INHERITED',correction_kind='SOURCE_VINTAGE_METADATA_ONLY',source_horizon_qualification=dict(kind='TARGET_SPECIFIC_BOUND_SOURCE_CLOCKS',original_horizon_id='INHERITED_C_PANEL',horizon_id='B_EARLY_FORECAST_LATER_THRESHOLD',source_binding='SOURCE_AND_CLOCK_BINDINGS.json'))
  q=qualify_bound_source_horizon(apply_source_vintage_annotation(r,a),a)
  self.assertEqual(q['horizon_id'],'B_EARLY_FORECAST_LATER_THRESHOLD');self.assertEqual(r['horizon_id'],'INHERITED_C_PANEL')
  a['source_horizon_qualification']['original_horizon_id']='DIFFERENT_SOURCE'
  with self.assertRaises(ValueError):qualify_bound_source_horizon(r,a)
