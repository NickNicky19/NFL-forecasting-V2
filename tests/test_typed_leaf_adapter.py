import unittest
import numpy as np

from nfl_v2.distribution_laws import Law
from nfl_v2.typed_leaf_adapter import point_outputs


class TypedLeafAdapterTests(unittest.TestCase):
    def setUp(self):
        self.fit = dict(target='pass_td', training_n=10,
                        feature_columns=['a', 'b', 'c', 'n8'],
                        latest_training_label_available=1,
                        latest_training_consumed_feature_available=1)
        self.q = dict(target='pass_td', position='QB', cutoff=3,
                      latest_consumed_feature_available=2)
        self.priors = dict(QB=Law('geometric', q=.6))

    def call(self, **kw):
        opts = dict(model=None, raw_features=[[0, 0, 0, 0]],
                    feature_columns=self.fit['feature_columns'], fit=self.fit,
                    queries=[self.q], priors=self.priors)
        opts.update(kw)
        return point_outputs(**opts)

    def test_mean_median_and_actual_independence(self):
        a = self.call()[0]
        self.assertAlmostEqual(a['mean'], 1.5)
        self.assertEqual(a['lower_median'], 1)
        self.assertEqual(a['fallback'], 'cold_start_role_prior')
        self.assertEqual(self.call(queries=[dict(self.q, actual=999999)]), [a])

    def test_rejects_reordered_features_and_future_dependency(self):
        with self.assertRaisesRegex(ValueError, 'ordered feature'):
            self.call(feature_columns=list(reversed(self.fit['feature_columns'])))
        with self.assertRaisesRegex(ValueError, 'feature dependency'):
            self.call(queries=[dict(self.q, latest_consumed_feature_available=3)])

    def test_blocked_query_has_no_fallback_point(self):
        r = self.call(queries=[dict(self.q, blocked_reason='identity')])[0]
        self.assertIsNone(r['mean'])
        self.assertIsNone(r['fallback'])
        self.assertEqual(r['status'], 'UNAVAILABLE_BLOCKED_QUERY')

    def test_no_model_and_no_training_fallbacks_remain_distinct(self):
        self.assertEqual(self.call(raw_features=[[0, 0, 0, 1]])[0]['fallback'], 'no_model_role_prior')
        self.assertEqual(self.call(fit=dict(self.fit, training_n=0))[0]['fallback'], 'fixed_no_NFL_startup')


if __name__ == '__main__':
    unittest.main()
