import unittest
from nfl_v2.seasonal_continuity_repair import repair_row
class RepairTests(unittest.TestCase):
    def row(self,pos,fb,p):return dict(procedure_id='v2-hgb-rush-att-qb-rb-specialization-v1:common-feature-memory',position=pos,fallback=fb,prediction=p,product_id='absolute_error_point')
    def test_unsupported_fallback_repaired_even_when_error_worsens(self):
        r,reason=repair_row(self.row('WR','own_empirical',1.));self.assertEqual(r['prediction'],0);self.assertEqual(r['fallback'],'constant_zero');self.assertTrue(reason);self.assertEqual(r['product_id'],'absolute_loss_point')
    def test_primary_and_modelled_values_unchanged(self):
        for pos,fb in [('RB','own_empirical'),('WR','none')]:
            r,reason=repair_row(self.row(pos,fb,3.));self.assertEqual(r['prediction'],3);self.assertFalse(reason)
if __name__=='__main__':unittest.main()
