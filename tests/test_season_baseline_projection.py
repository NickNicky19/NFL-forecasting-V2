import unittest
from tools.annotate_season_baseline import key,weekly_aggregate_bootstrap_supported
class SeasonalBaselineProjectionFixtures(unittest.TestCase):
 def test_missing_position_week_is_explicit(self):
  self.assertFalse(weekly_aggregate_bootstrap_supported(dict(evaluation_weeks=list(range(1,19)),position='QB')))
  self.assertTrue(weekly_aggregate_bootstrap_supported(dict(evaluation_weeks=list(range(1,19)),position='ALL')))
 def test_single_week_no_cluster_bootstrap(self):
  self.assertFalse(weekly_aggregate_bootstrap_supported(dict(evaluation_weeks=[7],position='ALL')))
 def test_learned_and_fullsystem_lookup_distinct(self):
  r=dict(target='rec',population='primary',week=1,position='ALL',procedure_id='f',policy_id='h',product_id='mean',fallback_view='ALL')
  self.assertNotEqual(key(r),key(dict(r,fallback_view='LEARNED_ONLY')))
if __name__=='__main__':unittest.main()
