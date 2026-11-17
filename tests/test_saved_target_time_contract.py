import unittest
import numpy as np
from nfl_v2.hgb_control import FeatureHistory
from nfl_v2.ordered_information_ablation import project

class SavedTargetTimeContractTests(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(player_id='fixture',position='QB',season=2026,game_id='old',kickoff=1.,available=10.,values={'pass_att':20.})]

    def test_foreknown_target_time_preserves_full_saved_vector_without_new_arrival(self):
        history=FeatureHistory(self.rows)
        saved,latest=history.get('fixture','QB','pass_att',18.)
        earlier_asof=FeatureHistory([r for r in self.rows if r['available']<15.])
        reconstructed,_=earlier_asof.get('fixture','QB','pass_att',18.)
        np.testing.assert_equal(saved,reconstructed)
        self.assertLess(latest,15.)
        current_clock,_=history.get('fixture','QB','pass_att',15.)
        self.assertNotEqual(saved[5],current_clock[5])

    def test_arrival_after_decision_invalidates_saved_vector_reuse(self):
        rows=self.rows+[dict(self.rows[0],game_id='new',kickoff=7.,available=16.,values={'pass_att':40.})]
        saved,latest=FeatureHistory(rows).get('fixture','QB','pass_att',18.)
        earlier,_=FeatureHistory([r for r in rows if r['available']<15.]).get('fixture','QB','pass_att',18.)
        self.assertGreaterEqual(latest,15.)
        self.assertNotEqual(saved[0],earlier[0])

    def test_c02_is_clock_invariant_between_source_arrivals(self):
        history=FeatureHistory(self.rows)
        at_decision,_=history.get('fixture','QB','pass_att',15.)
        at_target,_=history.get('fixture','QB','pass_att',18.)
        np.testing.assert_equal(project(np.array([at_decision])),project(np.array([at_target])))

if __name__=='__main__':unittest.main()
