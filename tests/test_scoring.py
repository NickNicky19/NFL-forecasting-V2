import math
import unittest
from nfl_v2.scoring import (chart_points, CHART_WEIGHTS, anytime_td,
                            point_metrics, event_probabilities, expected_net, settle)

class ScoringTests(unittest.TestCase):
    def test_chart_ordinary_and_rare(self):
        c=dict.fromkeys(CHART_WEIGHTS,0)
        c.update(passing_yards=250,passing_TD=2,interceptions_thrown=1,
                 rushing_yards=-5,receptions=3,receiving_yards=20,fumbles_lost=1)
        self.assertEqual(chart_points(c),20.5)
        c.update(passing_2pt=1,rushing_2pt=1,receiving_2pt=1,
                 offensive_fumble_recovery_TD=1,kick_return_TD=1,punt_return_TD=1,
                 field_goal_return_TD=1)
        self.assertEqual(chart_points(c),50.5)
        del c['field_goal_return_TD'];self.assertIsNone(chart_points(c))

    def test_missing_and_signed(self):
        self.assertIsNone(chart_points({}))
        self.assertEqual(point_metrics([-4],[-7],'rush_yd')['mae'],3)
        with self.assertRaises(ValueError):point_metrics([0],[None],'rec')
        with self.assertRaises(ValueError):point_metrics([0],[-1],'rec')
        with self.assertRaises(ValueError):point_metrics([0],[.5],'rec')

    def test_precision_boundary(self):
        r=point_metrics([0,1,10],[0,0,0],'pass_yd')
        self.assertEqual(r['abs_lt_1'],1/3);self.assertEqual(r['abs_le_1'],2/3)
        self.assertEqual(r['abs_lt_10'],2/3);self.assertEqual(r['abs_le_10'],1)

    def test_td_event_support(self):
        self.assertEqual(anytime_td(2,0),1);self.assertEqual(anytime_td(None,1),1)
        self.assertIsNone(anytime_td(None,0));self.assertEqual(anytime_td(0,0),0)
        for a,b in [(.5,0),(1,-1),(float('nan'),1),(True,1)]:
            self.assertIsNone(anytime_td(a,b))

    def test_coherent_offers_and_refunds(self):
        p=event_probabilities([0,1,2],[.2,.5,.3],1)
        self.assertEqual(p,{'over':.3,'under':.2,'push':.5})
        self.assertAlmostEqual(expected_net(p['over'],p['under'],2),.1)
        half=event_probabilities([0,1,2],[.2,.5,.3],.5)
        self.assertEqual(half['push'],0);self.assertEqual(half['over']+half['under'],1)
        self.assertEqual(settle(1,1,'over',2),('push',0))
        self.assertEqual(settle(None,1,'over',2,'void'),('void',0))
        self.assertEqual(settle(None,1,'over',2),('unresolved',None))
        self.assertEqual(settle(2,1,'over',2),('win',1))
        self.assertEqual(settle(2,1,'under',2),('loss',-1))

    def test_probability_proper_score(self):
        self.assertEqual(point_metrics([.7],[1],'anytime_td')['brier'],(.7-1)**2)
        self.assertTrue(math.isinf(point_metrics([0],[1],'anytime_td')['log_loss']))
        self.assertAlmostEqual(point_metrics([.7],[1],'anytime_td')['brier'],point_metrics([.3],[0],'anytime_td')['brier'])
        with self.assertRaises(ValueError):event_probabilities([0,1],[.5,.6],.5)
        with self.assertRaises(ValueError):event_probabilities([0,0],[.5,.5],.5)

if __name__=='__main__':unittest.main()
