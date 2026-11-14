import unittest
import numpy as np
from nfl_v2 import c02_future_shadow as wave,ordered_information_ablation as recipe,hgb_control as src
class FutureC02Tests(unittest.TestCase):
    def test_blocked_unknown_position_before_role_inference(self):
        self.assertEqual(wave.blocked_reason(dict(position=None,blocked_reason='NO_ID')),'NO_ID')
        self.assertEqual(wave.blocked_reason(dict(position=None,blocked_reason=None)),'UNQUALIFIED_POSITION')
    def test_projection_exact_and_lag_invariant(self):
        x=np.arange(40.).reshape(2,20);self.assertEqual(recipe.project(x).shape,(2,8));x[:,4:16]=-999
        np.testing.assert_array_equal(recipe.project(x),np.array([[0,1,2,3,16,17,18,19],[20,21,22,23,36,37,38,39]]))
    def test_exact_training_availability_and_strict_floor(self):
        rows=[dict(player_id='fixture',game_id=str(i),season=y,week=1,position='QB',available=a,kickoff=k,values={'pass_yd':v}) for i,(y,a,k,v) in enumerate([(2025,20,10,200),(2026,40,30,100)])]
        hist=src.FeatureHistory(rows);chosen,x,m=wave.training_binding(rows,'pass_yd','H-CURRENT',2026,40,hist);self.assertEqual(len(chosen),0)
        strict=src.FeatureHistory([r for r in rows if r['season']==2026]);chosen,x,m=wave.training_binding(rows,'pass_yd','H-CURRENT',2026,41,strict);self.assertEqual(len(chosen),1);self.assertEqual(x[0,3],0)
    def test_balanced_finite_counts(self):
        self.assertEqual(len(recipe.TARGETS)*len(recipe.POLICIES),48)
if __name__=='__main__':unittest.main()
