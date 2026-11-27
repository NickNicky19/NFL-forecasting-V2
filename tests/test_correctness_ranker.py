import copy
import unittest
from nfl_v2 import correctness_ranker as r

class CorrectnessRankerTests(unittest.TestCase):
 def rows(self):
  return [dict(offer_id=str(i),game_id=str(i//2),label_available=10+i,probabilities=dict(over=.55+.01*(i%3),under=.45-.01*(i%3),push=0.),actual=(i%3),line=1.5,position=['RB','WR','TE'][i%3],participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL')for i in range(30)]
 def test_future_labels_and_probabilities_cannot_change_earlier_fit(self):
  rows=self.rows();future=dict(rows[0],offer_id='future',game_id='later',label_available=200)
  a=r.fit(rows+[future],100);future.update(actual=99,probabilities=dict(over=.99,under=.01,push=0.));b=r.fit(rows+[future],100)
  self.assertEqual(a,b);self.assertTrue(a['fit_performed']);self.assertLess(a['latest_label_available'],100)
 def test_unavailable_baseline_is_not_a_confidence_abstention_or_zero(self):
  row=self.rows()[0];row['probabilities']=None
  self.assertIsNone(r.rank_score(row,dict(fit_performed=False)))
  row['probabilities']=dict(over=float('nan'),under=.4,push=.6)
  with self.assertRaises(ValueError):r.features(row)
 def test_ranker_does_not_change_baseline_side_or_probabilities(self):
  rows=self.rows();row=rows[0];before=copy.deepcopy(row);score=r.rank_score(row,r.fit(rows,100))
  self.assertTrue(0<=score<=1);self.assertEqual(row,before)
  self.assertEqual(r.rank_score(row,dict(fit_performed=False)),max(row['probabilities']['over'],row['probabilities']['under']))
