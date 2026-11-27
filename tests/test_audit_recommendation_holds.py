import unittest
import math
from nfl_v2.result_index import is_championship_eligible
from nfl_v2.recommendation_holds import recommendation_hold, HGB_CARRY_HOLD
from nfl_v2.hgb_output_diagnostics import point_output_profile


class AuditRecommendationHoldTests(unittest.TestCase):
    def test_original_exact_carry_versions_and_views_are_held(self):
        for procedure in ('hgb-direct-history-controls-v1:absolute_error_point',
                          'v2-hgb-direct-history-controls-v1:absolute_error_point',
                          'B:hgb-direct-history-controls-v1:absolute_error_point:retained-method-key',
                          'B::hgb-direct-history-controls-v1:absolute_error_point:known-target-time-v1'):
            row = dict(procedure_id=procedure, target='rush_att')
            self.assertEqual(recommendation_hold(row), HGB_CARRY_HOLD)
            self.assertFalse(is_championship_eligible(row))
            self.assertFalse(is_championship_eligible(dict(category='rush_att', source_aggregate_fields=row)))

    def test_other_targets_repairs_and_controls_are_not_blanket_excluded(self):
        for procedure, target in (
            ('hgb-direct-history-controls-v1:absolute_error_point', 'pass_yd'),
            ('hgb-direct-history-controls-v1:squared_error_mean', 'rush_att'),
            ('v2-hgb-rush-att-qb-rb-specialization-v1:absolute_error_point', 'rush_att'),
            ('v2-hgb-poisson-count-point-reconstruction-v1:point', 'rush_att'),
            ('empirical-player-history-control-v1', 'rush_att')):
            row = dict(procedure_id=procedure, target=target,
                       control_procedure_id='hgb-direct-history-controls-v1:absolute_error_point')
            self.assertIsNone(recommendation_hold(row))
            self.assertTrue(is_championship_eligible(row))

    def test_raw_original_score_provenance_is_required_for_short_objective(self):
        raw = dict(target='rush_att', objective='absolute_error_point')
        self.assertIsNone(recommendation_hold(raw))
        self.assertEqual(recommendation_hold(dict(raw, source_artifact=
            'reports/continuation-20261029/hgb-history-v1/SCORES.json')), HGB_CARRY_HOLD)

    def test_known_failed_fixed_model_dependency_is_not_cured_by_new_alias(self):
        row = dict(target='rush_att', procedure_id='v2-availability-abc-shadow-v1:hgb_direct:absolute_error_point',
                   model_artifact_id='MODEL-b9e7ec24ce3fd672bed9bed7d2d80ea00a303ba39dd8211004cb596f2e30dc9a')
        self.assertEqual(recommendation_hold(row), HGB_CARRY_HOLD)
        self.assertIsNone(recommendation_hold(dict(row, model_artifact_id='MODEL-different-registered-refit')))

    def test_output_diagnostic_preserves_legitimate_zeros_and_missingness(self):
        r = point_output_profile([0, 0, math.nan], [0, 0, 15])
        self.assertEqual(r['zero_outputs'], 2)
        self.assertEqual(r['unavailable_or_nonfinite_outputs'], 1)
        self.assertEqual(r['mae'], 0)
        self.assertTrue(r['diagnostic_not_automatic_defect'])
        with self.assertRaises(ValueError):
            point_output_profile([0], [0, 1])

    def test_bound_availability_arms_survive_lost_projection_metadata(self):
        proc = 'v2-availability-abc-shadow-v1:hgb_direct:absolute_error_point'
        for arm in ('A', 'B'):
            row = dict(target='rush_att', procedure_id='B:' + proc + ':method',
                       availability_arm=arm)
            self.assertEqual(recommendation_hold(row), HGB_CARRY_HOLD)
            projected = dict(category='rush_att', procedure_id='B::' + proc + ':method',
                             source_aggregate_fields=dict(information_policy='AVAILABILITY-' + arm))
            self.assertEqual(recommendation_hold(projected), HGB_CARRY_HOLD)
        self.assertIsNone(recommendation_hold(dict(target='rush_att', procedure_id=proc,
                                                  availability_arm='C')))
        self.assertIsNone(recommendation_hold(dict(target='pass_yd', procedure_id=proc,
                                                  availability_arm='A')))
        self.assertEqual(recommendation_hold(dict(target='rush_att', procedure_id='alias',
            fixed_model_artifact_id='MODEL-4333f846a06ff945536379969920ce16ae00086df0e9922a0a9dc58290c29b53')),
            HGB_CARRY_HOLD)
