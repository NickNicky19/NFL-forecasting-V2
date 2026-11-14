import copy
import unittest

from tools.register_point_offer_diagnostic import oriented


class PointOfferComparisonOrientationTests(unittest.TestCase):
    def pair(self, candidate=8.0, comparator=10.0):
        return dict(candidate_error=candidate, comparator_error=comparator,
                    candidate_recipe=['saved-raw', 'ARCHIVED', 'point'],
                    comparator_recipe=['focal', 'H-MULTI', 'point'],
                    candidate_infinite_rows=0, comparator_infinite_rows=0,
                    delta=candidate-comparator,
                    relative_error_change=(candidate-comparator)/comparator,
                    game_normal95_sensitivity=[-3.0, -1.0], week_interval=None,
                    weekly_paired_sums_counts={'5': {'n': 3, 'loss_difference_sum': -6.0}})

    def test_reverse_relative_change_uses_new_comparator_and_preserves_source(self):
        source = self.pair()
        before = copy.deepcopy(source)
        reverse = oriented(source, True)
        self.assertEqual(source, before)
        self.assertEqual(reverse['candidate_error'], 10.0)
        self.assertEqual(reverse['comparator_error'], 8.0)
        self.assertEqual(reverse['delta'], 2.0)
        self.assertEqual(reverse['relative_error_change'], .25)
        self.assertEqual(reverse['game_normal95_sensitivity'], [1.0, 3.0])
        self.assertEqual(reverse['weekly_paired_sums_counts']['5']['loss_difference_sum'], 6.0)

    def test_reverse_zero_comparator_is_missing_relative_change(self):
        reverse = oriented(self.pair(0.0, 10.0), True)
        self.assertIsNone(reverse['relative_error_change'])
        self.assertEqual(reverse['relative_error_missing_reason'], 'zero_comparator_error_denominator')


if __name__ == '__main__':
    unittest.main()
