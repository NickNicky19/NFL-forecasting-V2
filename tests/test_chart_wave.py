"""Invented chart-grid and current-only fixtures, never NFL skill evidence."""
import unittest
import numpy as np
from threadpoolctl import threadpool_limits
from nfl_v2.chart_wave import chart_prior,chart_summary,ChartModel,chart_future,TARGET
from nfl_v2.distribution_laws import Law
from nfl_v2.distribution_wave_v2 import predict_admitted
class ChartWaveTests(unittest.TestCase):
 def test_signed_point_grid_and_proper_score_scaling(self):
  law=Law('signed',center=-37,q=.7);d=chart_summary(law,-9)
  self.assertEqual(d['mean'],-.74);self.assertEqual(d['lower_median'],-.74);self.assertAlmostEqual(d['crps'],law.crps(-9)/50);self.assertEqual(d['nll'],law.summary(-9)['nll']);self.assertAlmostEqual(d['q05']*50,law.quantile(.05))
 def test_prior_floor_one_native_point_no_old_startup(self):
  self.assertEqual(chart_prior([]).mean,0.);p=chart_prior([123,123]);self.assertEqual(p.q,50/51);self.assertEqual(p.center,123)
 def test_dedupe_future_without_inventing_unknown_identity(self):
  def q(player,sleeper,pos,reason):return dict(game_id='g',player_id=player,sleeper_id=sleeper,position=pos,blocked_reason=reason,kickoff_utc='2030-01-01T18:00:00+00:00',owner_input_cutoff_utc='2030-01-01T16:30:00+00:00')
  rows=[q('00-1234567','s','RB',None),q('00-1234567','s','RB',None),q(None,'x',None,'MISSING_BOARD'),q(None,'y',None,'MISSING_BOARD')];a,b=chart_future(rows,0);self.assertEqual(len(a),3);self.assertEqual(len(b),0);self.assertIsNone(a[1]['player_id']);self.assertIsNone(a[2]['position'])
 def test_fictional_chart_models_preserve_negative_support_and_missing_context(self):
  rng=np.random.default_rng(1701);x=rng.normal(size=(120,20));y=np.rint(rng.normal(0,300,size=120));positions=['QB']*120
  with threadpool_limits(limits=2):
   for family in ['ordered_leaf_cdf','regularized_glm_law']:
    m=ChartModel(family,TARGET).fit(x,y,positions);q=[{'position':'QB','blocked_reason':None},{'position':None,'blocked_reason':'MISSING_BOARD'}];pred=predict_admitted(m,x[:2],q,{'QB':chart_prior(y)});self.assertIsNone(pred[1][0]);law,_=pred[0];self.assertGreater(law.pmf(-1),0.);self.assertEqual(chart_summary(law,0)['grid_denominator'],50)
if __name__=='__main__':unittest.main()
