import unittest
from nfl_v2.carry_older_pairs import candidate_spec,original_spec,validate_pair,point_summary,strongest,number

class CarryOlderPairsTests(unittest.TestCase):
    def row(self,**kw):
        r=dict(game_id='fiction',player_id='p',target='rush_att',population='primary',position='RB',week=1,season=2025,prediction=0.,actual=0.,fallback='none');r.update(kw);return r
    def test_zero_is_scored_and_missing_is_not_zero(self):
        out=point_summary([self.row(),self.row(actual=None,prediction=3.)]);self.assertEqual(out['n'],1);self.assertEqual(out['mae'],0.);self.assertEqual(out['missing_actual_rows'],1)
    def test_label_or_position_mismatch_rejected(self):
        with self.assertRaises(ValueError):validate_pair(self.row(),self.row(position='QB'))
        with self.assertRaises(ValueError):validate_pair(self.row(),self.row(actual=1.))
    def test_candidate_and_original_product_contracts_remain_distinct(self):
        self.assertEqual(candidate_spec('H-MULTI-COMMON')[2],'absolute_loss_point');self.assertEqual(original_spec('H-MULTI-COMMON')[2],'absolute_error_point')
        self.assertIn('strict-current-feature-memory',candidate_spec('H-CURRENT-STRICT')[0])
    def test_fallback_contribution_adds_to_total_error(self):
        o=point_summary([self.row(prediction=3.,actual=1.,fallback='prior'),self.row(prediction=2.,actual=1.)]);self.assertEqual(o['mae'],1.5);self.assertEqual(o['fallback_full_error_contribution'],1.);self.assertEqual(o['learned_loss_sum'],1.)
    def test_no_supported_rows_have_null_error(self):
        o=point_summary([self.row(actual=None)]);self.assertIsNone(o['mae']);self.assertEqual(o['n'],0)
    def test_nonfinite_is_rejected_not_silently_missing(self):
        with self.assertRaises(ValueError):number('nan')
        self.assertIsNone(number(''))
    def test_strongest_excludes_candidate_and_requires_full_support(self):
        def r(proc,n,error):return dict(target='rush_att',week='ALL',position='ALL',fallback_view='ALL',population='primary',procedure_id=proc,history_regime='H-MULTI',product_id='point',mae=error,n=n)
        got=strongest([r('v2-hgb-rush-att-qb-rb-specialization-v1:common',10,0.),r('weak',10,2.),r('selected',10,1.),r('partial',2,.1)])
        self.assertEqual(got['procedure_id'],'selected')

if __name__=='__main__':unittest.main()
