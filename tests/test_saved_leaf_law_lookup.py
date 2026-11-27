import unittest
import numpy as np
from scipy import sparse
from nfl_v2.saved_leaf_law_lookup import lookup,from_payload


class SavedLeafLawLookupTests(unittest.TestCase):
    def test_exact_tree_mixture_and_infinite_prior_tail(self):
        h=[sparse.csr_matrix([[.5,.5],[0.,1.]]),sparse.csr_matrix([[1.,0.],[.25,.75]])]
        law,payload=lookup([0,2],h,[0,1],dict(kind='geometric',q=.5),expected_trees=2)
        self.assertAlmostEqual(law.pmf(0),.95*.375+.05*.5)
        self.assertAlmostEqual(law.pmf(2),.95*.625+.05*.125)
        self.assertAlmostEqual(law.pmf(5),.05*.5**6)
        self.assertAlmostEqual(law.mean,.95*1.25+.05)
        self.assertAlmostEqual(from_payload(payload).cdf(2),law.cdf(2))

    def test_signed_support_and_push_mass_are_preserved(self):
        h=[sparse.csr_matrix([[.2,.3,.5]])]
        law,_=lookup([-3,0,4],h,[0],dict(kind='signed',center=0,q=.5),expected_trees=1)
        self.assertLess(law.cdf(-4),law.cdf(-3));self.assertGreater(law.pmf(-3),0)
        self.assertAlmostEqual(law.cdf(0)-law.cdf(-1),law.pmf(0))
        self.assertAlmostEqual((1-law.cdf(0))+law.cdf(-1)+law.pmf(0),1)

    def test_missing_tree_or_nonleaf_histogram_is_rejected(self):
        h=[sparse.csr_matrix([[0.,0.],[.5,.5]])]
        with self.assertRaises(ValueError):lookup([0,1],h,[1],dict(kind='zero'))
        with self.assertRaises(ValueError):lookup([0,1],h,[0],dict(kind='zero'),expected_trees=1)


if __name__=='__main__':unittest.main()
