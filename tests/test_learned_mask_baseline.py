import unittest
from tools.learned_mask_baseline_portable import loss,membership_hash,key
class LearnedMaskFixtures(unittest.TestCase):
 def test_native_loss_and_binary_brier(self):
  self.assertEqual(loss(2,5,'rec'),3);self.assertAlmostEqual(loss(1,.2,'anytime_td'),.64)
 def test_membership_is_exact_and_order_invariant(self):
  baseline=[('b',2,1,'g','t','p'),('a',3,2,'g','t','p')]
  self.assertEqual(membership_hash([0,1],baseline),membership_hash([1,0],baseline));self.assertNotEqual(membership_hash([0],baseline),membership_hash([1],baseline))
 def test_policy_and_product_are_not_merged(self):
  r=dict(procedure_id='m',target='t',population='p',policy_id='h',product_id='mean');self.assertNotEqual(key(r),key(dict(r,product_id='lower_median')))
if __name__=='__main__':unittest.main()
