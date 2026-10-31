import unittest
from nfl_v2.strict_hgb_2026_design import current_rows,training_rows,fit_eligible,fallback,training_features,canonical_query
class Strict2026DesignFixtures(unittest.TestCase):
 def rows(self):
  return[dict(season=y,week=1,player_id='x',position='QB',game_id=str(y),available=a,kickoff=a-100,values={'pass_yd':v})for y,a,v in((2025,10,999),(2026,20,2),(2026,30,4))]
 def test_metadata_typed_without_ID_mutation(self):
  q=dict(season='2026',week='7',player_id='00-0000001');r=canonical_query(q);self.assertEqual((r['season'],r['week'],r['player_id']),(2026,7,'00-0000001'));self.assertEqual(q['season'],'2026')
 def test_current_only(self):self.assertEqual(len(current_rows(self.rows())),2)
 def test_strictavailability(self):self.assertEqual([r['values']['pass_yd']for r in training_rows(self.rows(),'pass_yd',30,{'QB'})],[2])
 def test_fallback_no_oldprior(self):self.assertEqual(fallback(self.rows(),'pass_yd','x','QB',20,'squared_error_mean')['value'],0)
 def test_binary_and_minimum(self):self.assertFalse(fit_eligible([0]*40,'anytime_td'));self.assertTrue(fit_eligible([0]*20+[1]*20,'anytime_td'));self.assertFalse(fit_eligible([1]*39,'pass_yd'))
if __name__=='__main__':unittest.main()
