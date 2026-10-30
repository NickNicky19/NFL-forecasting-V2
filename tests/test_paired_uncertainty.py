import unittest
import numpy as np
from nfl_v2.paired_uncertainty import paired_losses


class PairedUncertaintyTests(unittest.TestCase):
    def test_cluster_weighting_is_row_weighted_not_mean_week_mae(self):
        weeks=[1]*10+list(range(2,9));a=[10.]*10+[0.]*7;b=[0.]*17
        out=paired_losses(a,b,weeks,list(range(17)))
        self.assertAlmostEqual(out['delta'],100/17)
        sampled=np.random.default_rng(1703).integers(0,8,size=(500,8))
        sums=np.array([100.]+[0.]*7);ns=np.array([10]+[1]*7)
        expected=np.quantile(sums[sampled].sum(axis=1)/ns[sampled].sum(axis=1),[.025,.975],method='linear')
        np.testing.assert_allclose(out['week_interval'],expected)
        self.assertIsNone(out['relative_error_change'])

    def test_insufficient_week_clusters_not_replaced_by_game_count(self):
        out=paired_losses([1.]*20,[2.]*20,[1]*20,list(range(20)))
        self.assertIsNone(out['week_interval'])
        self.assertEqual(out['game_cluster_sensitivity_se'],0.)

    def test_infinite_law_losses_remain_explicit(self):
        out=paired_losses([float('inf')],[0.],[1],['fictional'])
        self.assertEqual(out['candidate_error'],'Infinity')
        self.assertIsNone(out['delta'])

    def test_complement_and_seed_are_deterministic(self):
        a=[.1,.5,.2,.6,.2,.7,.3,.8];b=[.2]*8
        first=paired_losses(a,b,list(range(8)),list(range(8)))
        self.assertEqual(first,paired_losses(a,b,list(range(8)),list(range(8))))
        inverse=paired_losses(b,a,list(range(8)),list(range(8)))
        self.assertAlmostEqual(first['delta'],-inverse['delta'])
        np.testing.assert_allclose(first['week_interval'],[-inverse['week_interval'][1],-inverse['week_interval'][0]])
