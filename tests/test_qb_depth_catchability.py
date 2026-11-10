import copy
import unittest
from nfl_v2.qb_depth_catchability import DepthHistory


class DepthCatchabilityTest(unittest.TestCase):
    def setUp(self):
        self.past = dict(game_id='past', player_id='QB', kickoff=0, available=10,
                         physical_participation=True)
        self.chart = dict(game_id='past', player_id='QB', eligible_throws=[10,0,0,0,0],
                          flags={'is_catchable_ball':dict(known=[10,0,0,0,0], positive=[0,0,0,0,0])})
        self.query = dict(game_id='next', player_id='QB', kickoff=20)

    def test_known_false_is_zero_not_unknown(self):
        d=DepthHistory([self.past],[self.chart]).describe(self.query)
        self.assertEqual(d['raw'][0],0.)
        self.assertIsNone(d['raw'][1])
        self.assertAlmostEqual(d['shrunk'][0],(20/12)/30)
        self.assertEqual(d['baseline'][1],.5)
        self.assertEqual(d['support'][1][-2:],[1.,1.])

    def test_future_source_and_target_labels_cannot_change_profile(self):
        a=DepthHistory([self.past],[self.chart]).describe(self.query)
        future=dict(self.past,game_id='future',available=30,kickoff=21)
        chart=dict(self.chart,game_id='future')
        changed=dict(self.query,actual=999,realized_attempts=999,realized_depth=[999]*5)
        b=DepthHistory([self.past,future],[self.chart,chart]).describe(changed)
        self.assertEqual(a,b)
        # Strict availability boundary, distinct from the prior game's kickoff.
        c=DepthHistory([self.past],[self.chart]).describe(dict(self.query,kickoff=10))
        self.assertEqual(c['own_games'],0)

if __name__=='__main__':unittest.main()
