import unittest
from tools.history_adjacent_replay import view_names,membership,procedure
class AdjacentHistoryFixtures(unittest.TestCase):
 def test_common_all_three_learned(self):
  self.assertIn('COMMON_CORE_LEARNED',view_names(['none']*3,2));self.assertNotIn('COMMON_CORE_LEARNED',view_names(['none','prior','none'],2))
 def test_fallback_partition_and_startup(self):
  v=view_names(['prior']*3,1);self.assertIn('ALL_ARM_FALLBACK',v);self.assertIn('ANY_ARM_FALLBACK',v);self.assertIn('WEEK1_STARTUP',v)
  self.assertIn('MIXED_FALLBACK',view_names(['none','prior','none'],4))
 def test_exact_order_invariant_membership(self):self.assertEqual(membership(['b','a']),membership(['a','b']))
 def test_common_and_strict_not_aliased(self):
  self.assertEqual(procedure(dict(procedure_id='f:common-feature-memory'),'law'),'f');self.assertIn('strict',procedure(dict(procedure_id='f:strict-current-inputs'),'law'))
if __name__=='__main__':unittest.main()
