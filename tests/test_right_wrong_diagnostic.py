import unittest
from nfl_v2.right_wrong_diagnostic import diagnose,aggregate,representatives,gap_band

def row(point=300,line=249.5,actual=250,side='over',state='WIN',idx=1,target='pass_yd'):
 return dict(point=point,line=line,actual=actual,selected_side=side,statistical_state=state,source_row_index=idx,target=target,admitted=True,participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL',decision_time='2026-10-23T10:00:00Z',kickoff='2026-10-25T18:00:00Z',week=7,game_id='fixture-game',player_id='fixture-player',fallback='none')

class RightWrongDiagnostic(unittest.TestCase):
 def test_large_numeric_error_can_be_correct_and_small_wrong(self):
  right=diagnose(row(),tolerance=10);wrong=diagnose(row(point=240,side='under',state='LOSS'),tolerance=10)
  self.assertEqual(right['bucket'],'OVER_WIN');self.assertTrue(right['large_error_right']);self.assertEqual(wrong['bucket'],'UNDER_LOSS');self.assertTrue(wrong['close_wrong'])
 def test_halfpoint_fractional_prediction_is_not_rounded(self):
  r=diagnose(row(point=19.6,line=19.5,actual=20,target='pass_cmp'),tolerance=1)
  self.assertEqual(r['bucket'],'OVER_WIN');self.assertAlmostEqual(r['absolute_error'],.4)
 def test_signed_yards_and_whole_point_push_are_preserved(self):
  r=diagnose(row(point=-2,line=-.5,actual=-1,side='under',target='rush_yd'),tolerance=5);self.assertEqual(r['bucket'],'UNDER_WIN')
  r=diagnose(row(point=20,line=19,actual=19,state='PUSH',target='pass_cmp'),tolerance=1);self.assertIsNone(r['bucket']);self.assertEqual(r['diagnostic_exclusion_reason'],'NONDECIDED_PUSH')
 def test_played_zero_is_valid_missing_is_not_zero(self):
  r=diagnose(row(point=.1,line=.5,actual=0,side='under',target='pass_int'),tolerance=1);self.assertEqual(r['bucket'],'UNDER_WIN')
  r=diagnose(row(actual=None),tolerance=10);self.assertIsNone(r['absolute_error']);self.assertEqual(r['diagnostic_exclusion_reason'],'MISSING_ACTUAL')
 def test_selected_side_bucket_never_follows_outcome_side(self):
  r=diagnose(row(point=1.6,line=1.5,actual=1,state='LOSS',target='pass_td'),tolerance=1);self.assertEqual(r['bucket'],'OVER_LOSS')
 def test_incompatible_frozen_selection_or_grade_raises(self):
  with self.assertRaises(ValueError):diagnose(row(side='under'),tolerance=10)
  with self.assertRaises(ValueError):diagnose(row(state='LOSS'),tolerance=10)
 def test_no_direct_components_or_unretained_role_invented(self):
  r=diagnose(row(),tolerance=10);self.assertIsNone(r['components']);self.assertIn('DIRECT_PROCEDURE',r['component_null_reason']);self.assertIsNone(r['pregame_role'])
 def test_deterministic_earliest_and_largest_error_are_separate(self):
  a=row(point=260,idx=2);a['decision_time']='2026-10-22T10:00:00Z';b=row(point=300,idx=1)
  rr=[diagnose(x,tolerance=10)for x in[b,a]];examples=representatives(rr)
  self.assertEqual(examples[0]['row']['source_row_index'],2);self.assertEqual(examples[-2]['row']['source_row_index'],1)
 def test_signed_gap_band_edges_follow_frozen_intervals(self):
  self.assertEqual([gap_band(x,10)for x in [-21,-20,-10,-.1,0,.1,10,20,21]],['LT_NEG_2T','GE_NEG_2T_LT_NEG_T','GE_NEG_T_LT_0','GE_NEG_T_LT_0','EQ_0','GT_0_LE_T','GT_0_LE_T','GT_T_LE_2T','GT_2T'])
 def test_void_and_pending_are_not_turned_into_threshold_grades(self):
  for state in ['VOID','PENDING']:
   r=diagnose(row(state=state),tolerance=10);self.assertIsNone(r['bucket']);self.assertIsNone(r['absolute_error'])
 def test_empty_buckets_have_null_metrics_and_counts_reconcile(self):
  rr=[diagnose(row(),tolerance=10),diagnose(row(point=240,side='under',state='LOSS'),tolerance=10)];b=[r for r in aggregate(rr,tolerance=10)if r['dimension']=='BUCKET']
  self.assertEqual(sum(r['n']for r in b),2);self.assertIsNone(next(r for r in b if r['bucket']=='OVER_LOSS')['mae'])

if __name__=='__main__':unittest.main()
