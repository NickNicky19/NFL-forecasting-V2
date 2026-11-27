import unittest
from nfl_v2 import compact_subgroups as s

class CompactSubgroupTests(unittest.TestCase):
 def row(self,p='p',prediction=0,actual=0,fallback='none',target='rush_att'):
  return dict(game_id='2025_18_A_B',player_id=p,target=target,population='primary',position='RB',history_regime='H-MULTI',fallback=fallback,season=2025,week=18,procedure_id='CANDIDATE',product_id='lower_median',policy_id='H-MULTI-COMMON',prediction=prediction,actual=actual,distribution_summary=None)
 def setup(self,row,other=None):
  other=other or dict(row,procedure_id='REFERENCE');members={s.identity(row):dict(cohorts=['all','top10','workload_zero'])};refs={('group',row['target'],'fixed_2026_control'):{s.identity(other):other},('group',row['target'],'same_season_strongest_control'):{s.identity(other):other}};p=dict(evaluation_season=2025,mode='season',cohort_limit='fictionalfixture',protocol_sha256='fixture');return refs,members,p
 def test_empirical_alias_is_explicit_and_preserves_functional(self):
  a=s.alias(dict(procedure_id='empirical-player-history-control-v1',product_id='empirical_mean'));self.assertEqual(a['product_id'],'mean');b=s.alias(dict(procedure_id='empirical-player-history-control-v1',product_id='empirical_lower_median'));self.assertEqual(b['product_id'],'lower_median')
 def test_full_and_common_learned_reference_use_same_queries(self):
  r=self.row(prediction=1);refs,m,p=self.setup(r);out,pairs,_=s.evaluate([('group',r)],refs,m,p);self.assertTrue(any(x['fallback_view']=='selected_candidate_and_controls_common_learned_overlap'for x in out));self.assertTrue(all(x['paired_n']==1 for x in pairs));self.assertEqual(out[0]['season'],2025)
 def test_reference_fallback_excludes_only_common_mask(self):
  r=self.row();refs,m,p=self.setup(r,dict(r,fallback='position_prior'));out,_,_=s.evaluate([('group',r)],refs,m,p);self.assertFalse(any(x['fallback_view']=='selected_candidate_and_controls_common_learned_overlap'for x in out));self.assertTrue(any(x['fallback_view']=='own_learned_only'for x in out))
 def test_missing_actual_stays_coverage(self):
  r=self.row(actual=None);refs,m,p=self.setup(r);out,_,_=s.evaluate([('group',r)],refs,m,p);self.assertEqual(out[0]['forecast_rows'],1);self.assertEqual(out[0]['n'],0);self.assertIsNone(out[0]['mae'])
 def test_reference_label_mismatch_rejected(self):
  r=self.row();refs,m,p=self.setup(r,dict(r,actual=1))
  with self.assertRaisesRegex(ValueError,'mismatch'):s.evaluate([('group',r)],refs,m,p)
 def test_duplicate_candidate_rejected(self):
  r=self.row();refs,m,p=self.setup(r)
  with self.assertRaisesRegex(ValueError,'duplicate'):s.evaluate([('group',r),('group',r)],refs,m,p)
 def test_signed_chart_exact_grid_precision(self):
  r=self.row(prediction=-.02,actual=-1.02,target=s.CHART);refs,m,p=self.setup(r);out,_,_=s.evaluate([('group',r)],refs,m,p);self.assertEqual(out[0]['abs_le_1'],1);self.assertEqual(out[0]['abs_lt_1'],0)
 def test_current_week8_filtered_before_numeric_decode(self):
  self.assertIsNone(s.normal(dict(season=2026,week=8,prediction='INVALID'),2026))
if __name__=='__main__':unittest.main()
