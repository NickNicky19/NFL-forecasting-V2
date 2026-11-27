import json
import unittest

import numpy as np
from threadpoolctl import threadpool_limits

from nfl_v2.anytime_current_shadow import export_model, restore_probability
from nfl_v2.hgb_control import FEATURES, FeatureHistory, make_estimator
from nfl_v2.empirical_benchmark import target_value


class AnytimeCurrentShadow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Deliberately strong synthetic signal, never included in NFL evidence.
        rng = np.random.default_rng(1701)
        cls.x = rng.normal(size=(300, len(FEATURES)))
        cls.y = (cls.x[:, 0] > 0).astype(float)
        cls.x[::9, 4] = np.nan
        with threadpool_limits(limits=2):
            cls.model = make_estimator('anytime_td', 'log_loss_probability').fit(cls.x, cls.y)
        cls.payload = json.loads(json.dumps(export_model(cls.model), allow_nan=False))

    def test_json_restoration_single_batch_shuffled(self):
        with threadpool_limits(limits=2):
            expected = self.model.predict_proba(self.x)[:, 1]
        restored = np.array([restore_probability(self.payload, x, FEATURES) for x in self.x])
        np.testing.assert_allclose(restored, expected, atol=1e-12, rtol=0)
        order = np.random.default_rng(91).permutation(len(self.x))
        shuffled = [restore_probability(self.payload, self.x[i], FEATURES) for i in order]
        np.testing.assert_allclose(shuffled, restored[order], atol=1e-12, rtol=0)
        self.assertGreater(np.std(expected), .1)

    def test_named_feature_order_enforced(self):
        with self.assertRaises(ValueError):
            restore_probability(self.payload, self.x[0], tuple(reversed(FEATURES)))

    def test_unknown_component_is_not_zero(self):
        self.assertIsNone(target_value('anytime_td', dict(rushing_tds=0, receiving_tds=None)))
        self.assertEqual(target_value('anytime_td', dict(rushing_tds=0, receiving_tds=0)), 0)
        self.assertEqual(target_value('anytime_td', dict(rushing_tds=1, receiving_tds=None)), 1)

    def test_future_label_cannot_change_earlier_feature(self):
        row = dict(player_id='fixed', game_id='past', kickoff=0., available=604800., values={'anytime_td': 0.})
        future = dict(player_id='fixed', game_id='future', kickoff=700000., available=1304800., values={'anytime_td': 1.})
        before = FeatureHistory([row]).get('fixed', 'RB', 'anytime_td', 800000.)[0]
        after = FeatureHistory([row, future]).get('fixed', 'RB', 'anytime_td', 800000.)[0]
        np.testing.assert_allclose(before, after, equal_nan=True)


if __name__ == '__main__':
    unittest.main()
