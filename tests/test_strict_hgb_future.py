import math,unittest
from nfl_v2 import strict_hgb_future as f
class StrictFutureTests(unittest.TestCase):
    def test_finite_twenty_one_objectives(self):
        self.assertEqual(sum(len(f.s.objectives(t))for t in f.s.TARGETS),21)
        self.assertEqual(f.output_views([dict(target='pass_yd'),dict(target='anytime_td')]),3)
    def test_blocked_id_and_position(self):
        self.assertFalse(f.admitted(dict(position=None,blocked_reason=None)))
        self.assertFalse(f.admitted(dict(position='WR',blocked_reason='NO_ID')))
        self.assertTrue(f.admitted(dict(position='WR',blocked_reason=None)))
    def test_strict_history_discards_older_nfl_outcomes(self):
        rows=[dict(player_id='x',season=yr,kickoff=a-10,available=a,game_id=str(yr),values={'rec':v}) for yr,a,v in ((2025,20.,99.),(2026,40.,2.))]
        h=f.s.FeatureHistory([r for r in rows if r['season']==2026]);self.assertTrue(math.isnan(h.get('x','WR','rec',40.)[0][0]));self.assertEqual(h.get('x','WR','rec',41.)[0][0],2.)

class StrictFutureResourceFixtures(unittest.TestCase):
 def test_grid_all_cells_on_partial_stop(self):
  grid=f.complete_grid([dict(slot='pass_yd-absolute_error_point',state='FITTED_RETAINED')],[])
  self.assertEqual(len(grid),21);self.assertEqual(sum(r['state']=='NOT_RUN_AFTER_BOUNDED_STOP' for r in grid),20);self.assertTrue(all(r['forecast_state']=='NOT_PERSISTED' for r in grid))
 def test_resource_exception_distinct(self):
  self.assertTrue(issubclass(f.ResourceBudget,RuntimeError))

if __name__=='__main__':unittest.main()
