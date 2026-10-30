import unittest
from tools.report_oct30c_checkpoint import feature_floor
class CheckpointLineageFixtures(unittest.TestCase):
 def test_empirical_memory_is_its_pool(self):
  for arm,expected in [('H-CURRENT',2025),('H-RECENT',2024),('H-MULTI',2022)]:
   self.assertEqual(feature_floor(dict(policy_id=arm+'-EMPIRICAL',history_regime=arm,procedure_id='empirical-player-history-control-v1'),2025),expected)
 def test_common_fitting_does_not_remove_older_memory(self):
  self.assertEqual(feature_floor(dict(policy_id='H-CURRENT-COMMON',history_regime='H-CURRENT',procedure_id='leaf'),2025),2022)
 def test_strict_memory_is_current_season_even_when_aliased(self):
  for year in (2022,2025):self.assertEqual(feature_floor(dict(policy_id='H-CURRENT-STRICT',history_regime='H-CURRENT',procedure_id='leaf'),year),year)
if __name__=='__main__':unittest.main()
