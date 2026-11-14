"""No-fit software checks for the original-label/member defense ablation."""
import unittest
import numpy as np
from nfl_v2 import qualified_defense_wave as w

class QualifiedDefenseWaveTests(unittest.TestCase):
 def test_procedure_ids_separate_information_groups_not_meanmedian_learners(self):
  self.assertNotEqual(w.proc('D1','H-MULTI-COMMON'),w.proc('D2','H-MULTI-COMMON'));self.assertEqual(w.FAMILY,'ordered_leaf_cdf');self.assertIn('strict-current-inputs',w.proc('D1','H-CURRENT-STRICT'))
 def test_exact_predeclared_cells_and_raw_dimensions(self):
  self.assertEqual(7*len(w.TARGETS)*len(w.POLICIES)*len(w.GROUPS),672);self.assertEqual(len(w.TARGETS)*len(w.POLICIES)*len(w.GROUPS),96);self.assertEqual(len(w.src.FEATURES)+len(w.GROUPS['D1']),24);self.assertEqual(len(w.src.FEATURES)+len(w.GROUPS['D2']),29)
 def test_d1_consumed_clock_excludes_unused_league_values(self):
  audit=dict(latest_local_available=10,latest_league_available=20);self.assertEqual(w.latest(5,audit,'D1'),10);self.assertEqual(w.latest(5,audit,'D2'),20)
 def test_missing_clocks_preserved(self):self.assertIsNone(w.latest(None,{},'D1'))
 def test_execution_requires_explicit_worker_slot_before_access(self):
  with self.assertRaisesRegex(ValueError,'worker'):w.run_historical(source_root=None,control_public=None,control_private=None,chart_public=None,chart_private=None,public_root=None,private_root=None,verifier_receipt=None)
  with self.assertRaisesRegex(ValueError,'worker'):w.run_future(source_root=None,public_root=None,private_root=None,verifier_receipt=None)
 def test_point_and_event_views_remain_original_contracts(self):
  self.assertEqual(w.old_recipe.products('rush_att'),('mean','lower_median'));self.assertEqual(w.old_recipe.products('anytime_td'),('event_probability',));self.assertEqual(w.POLICIES['H-CURRENT-STRICT'][1:],(2026,2026))
if __name__=='__main__':unittest.main()
