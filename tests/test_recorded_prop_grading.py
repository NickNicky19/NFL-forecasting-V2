import unittest
from nfl_v2 import recorded_prop_grading as g

class RecordedPropTests(unittest.TestCase):
    def row(self,**kw):
        r=dict(side='over',prediction=1.5,line=1.,actual=2,target='rec',participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL');r.update(kw);return r
    def test_P1_equality_abstains_without_rounding(self):
        self.assertIsNone(g.choose_side(self.row(prediction=1.),'P1'));self.assertEqual(g.choose_side(self.row(prediction=1.000000000001),'P1'),'over')
    def test_push_is_separate_and_book_unresolved(self):
        r=g.grade_records([self.row(actual=1)])[0];self.assertEqual(r['statistical_state'],'PUSH');self.assertEqual(r['settlement_state'],'UNRESOLVED_CONTRACT')
    def test_unknown_participation_never_zero(self):
        r=g.grade_records([self.row(actual=None,participation='UNKNOWN')])[0];self.assertEqual(r['statistical_state'],'UNKNOWN_PARTICIPATION')
    def test_played_explicit_zero_is_valid(self):
        r=g.grade_records([self.row(actual=0)])[0];self.assertEqual(r['statistical_state'],'LOSS')
    def test_signed_yards_preserved(self):
        r=g.grade_records([self.row(target='rush_yd',actual=-2,line=-1.)])[0];self.assertEqual(r['statistical_state'],'LOSS')
    def test_DNP_is_not_refund_or_void(self):
        r=g.grade_records([self.row(actual=None,participation='DNP')])[0];self.assertEqual(r['statistical_state'],'DNP');self.assertIsNone(r['net_return'])
    def test_execution_release_required_before_file_access(self):
        with self.assertRaisesRegex(ValueError,'ROOT'):g.run(output=None,private_output=None)
    def test_fractional_official_count_rejected_by_ROOT_engine(self):
        with self.assertRaises(ValueError):g.grade_records([self.row(actual=.5)])

if __name__=='__main__':unittest.main()
