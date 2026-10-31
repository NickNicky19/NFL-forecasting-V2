import unittest
from nfl_v2.full_provider_prop_replay import metadata_panel,grade,ADJUSTED,RAW,score_row,check_triplet


class FullProviderReplayTests(unittest.TestCase):
    def base(self):
        return dict(source_row_index=1,game_id='g',player_id='p',target='rec',population='primary',position='WR',
            line=4.5,line_from='dk',side=None,original_side=None,top_over=False,top_under=False,
            actual=0,prediction=5,raw_prediction=4,participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL',source_cohorts=[],week=7)

    def test_unselected_provider_threshold_is_admitted_but_generated_is_not(self):
        r=dict(category='rec',metadata_panel_status='NO_ORIGINAL_SAVED_SIDE',line_from='dk',line=4.5,lean=None)
        self.assertEqual(metadata_panel([r,dict(r,line_from='ours')]),[r])

    def test_original_abstention_is_preserved(self):
        rows=grade([self.base()]);original=next(r for r in rows if r['strategy']=='original')
        self.assertIsNone(original['selected_side']);self.assertEqual(original['statistical_state'],'ABSTAIN')
        self.assertEqual(original['settlement_state'],'NOT_SELECTED')

    def test_raw_and_adjusted_points_remain_distinct_without_invented_precision(self):
        rows=grade([self.base()]);lookup={r['strategy']:r for r in rows}
        self.assertEqual(lookup[RAW]['selected_side'],'under');self.assertEqual(lookup[RAW]['statistical_state'],'WIN')
        self.assertEqual(lookup[ADJUSTED]['selected_side'],'over');self.assertEqual(lookup[ADJUSTED]['statistical_state'],'LOSS')

    def test_played_zero_is_graded_unknown_is_not(self):
        rows=grade([self.base(),dict(self.base(),source_row_index=2,actual=None,participation='UNKNOWN')])
        rr=[r for r in rows if r['strategy']==RAW]
        self.assertEqual(rr[0]['statistical_state'],'WIN');self.assertEqual(rr[1]['statistical_state'],'UNKNOWN_PARTICIPATION')
        self.assertEqual(rr[1]['settlement_state'],'UNRESOLVED_CONTRACT')

    def test_zero_decided_bucket_is_null_and_partition_is_exact(self):
        pool=grade([self.base()]);rr=[r for r in pool if r['strategy']==RAW]
        views=[]
        for side in('over','under','Combined'):
            selected=[r for r in rr if side=='Combined'or r['selected_side']==side]
            views.append(score_row(selected,rr,strategy=RAW,target='rec',cohort='ALL',side=side))
        self.assertIsNone(views[0]['selection_metrics']['hit_rate']);self.assertIsNone(views[0]['selection_loss_rate'])
        check_triplet(views)


if __name__=='__main__':unittest.main()
