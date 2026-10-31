import unittest
from nfl_v2 import seasonal_rolling_v2 as v2,count_ablations as old
class ContinuityTests(unittest.TestCase):
    def test_role_restricted_fallback_and_original_product(self):
        rows=[dict(season=2025,position=p,values={'rush_att':1}) for p in ('QB','RB','WR','TE')]
        self.assertEqual([r['position'] for r in v2.fallback_sample_rows(rows,'rush_att',2025,'hgb_carry_primary')],['QB','RB'])
        self.assertEqual(len(v2.fallback_sample_rows(rows,'rush_att',2025,'hgb_poisson')),4)
        self.assertEqual(v2.products('hgb_carry_primary','rush_att'),('absolute_loss_point',))
    def test_glm_all_zero_uses_same_original_law_skip(self):
        self.assertTrue(v2.all_zero_count_skip('glm_law','pass_int',[0]*40))
        self.assertFalse(v2.all_zero_count_skip('glm_law','pass_int',[0]*39+[1]))
        self.assertFalse(v2.all_zero_count_skip('hgb_L1','pass_int',[0]*40))
    def test_zero_count_poisson_original_skip(self):
        self.assertEqual(old.fit_state([0]*40,old.POISSON),'NO_FIT_ALL_ZERO_COUNT')
        self.assertTrue(v2.all_zero_count_skip('hgb_poisson','pass_td',[0]*40))
if __name__=='__main__':unittest.main()
