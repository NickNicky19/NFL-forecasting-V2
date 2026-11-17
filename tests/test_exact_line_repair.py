import unittest
from nfl_v2.exact_line_repair import repair,cdf_shift,fit,gate_threshold

class ExactLineRepair(unittest.TestCase):
 def test_cdf_order_push_complements_and_endpoints(self):
  for alpha in [-1.5,0,1.5]:
   values=[cdf_shift(x,alpha)for x in [0,.1,.4,.8,1]];self.assertEqual(values,sorted(values));self.assertEqual(values[0],0);self.assertEqual(values[-1],1)
   for p in [dict(over=.4,under=.6,push=0),dict(over=.3,under=.5,push=.2)]:
    q=repair(p,alpha);self.assertAlmostEqual(sum(q.values()),1);self.assertGreaterEqual(min(q.values()),0)
    if p['push']==0:self.assertEqual(q['push'],0)
 def test_future_labels_cannot_change_earlier_fit_or_gate(self):
  rows=[dict(offer_id=str(i),game_id=str(i//4),label_available=10,probabilities=dict(over=.35,under=.65,push=0),actual=1 if i%3 else 0,line=.5,participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL')for i in range(40)]
  future=dict(rows[0],offer_id='future',label_available=101,actual=100)
  a=fit(rows+[future],100);future['actual']=-100;b=fit(rows+[future],100)
  self.assertTrue(a['fit_performed']);self.assertEqual(a,b)
  old=[dict(decision_epoch=10,probabilities=r['probabilities'])for r in rows];new=dict(decision_epoch=101,probabilities=dict(over=.99,under=.01,push=0));self.assertEqual(gate_threshold(old,100),gate_threshold(old+[new],100))
 def test_sparse_startup_stays_identity_and_infinite_mass_not_clipped(self):
  self.assertFalse(fit([],100)['fit_performed']);self.assertEqual(repair(dict(over=0.,under=1.,push=0.),1.5)['over'],0.)
