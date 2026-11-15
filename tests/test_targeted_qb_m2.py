import copy
import math
import unittest
import numpy as np
from scipy import stats
from nfl_v2.targeted_qb_m2 import (DispersionModel,IntegratedBetaBinomial,
    dispersion_features,restore_law,prior_beta)
from nfl_v2.player_context_matchup import exact_probabilities


class TargetedQBTests(unittest.TestCase):
    def test_joint_support_and_attempt_marginal(self):
        law=IntegratedBetaBinomial(30,12,.64,120)
        for a in (0,1,4,12,35):
            mass=sum(math.exp(law.joint_logpmf(a,c))for c in range(a+1))
            self.assertAlmostEqual(mass,stats.nbinom.pmf(a,12,12/42),places=11)
            self.assertEqual(law.joint_logpmf(a,a+1),-math.inf)

    def test_marginal_mass_push_and_moments(self):
        law=IntegratedBetaBinomial(30,12,.64,120)
        self.assertEqual(law.mean,19.2)
        self.assertGreater(law.variance,19.2)
        self.assertEqual(law.cdf(-1),0)
        self.assertEqual(law.cdf(math.inf),1)
        masses=[law.pmf(i)for i in range(200)]
        self.assertTrue(all(v>=0 for v in masses))
        self.assertAlmostEqual(sum(masses),1,places=8)
        p=exact_probabilities(law,20)
        self.assertAlmostEqual(sum(p.values()),1,places=12)
        self.assertAlmostEqual(p['push'],law.pmf(20),places=10)
        self.assertEqual(exact_probabilities(law,20.5)['push'],0)

    def test_zero_and_all_success_limits(self):
        for M,p in [(0,.6),(30,0)]:
            law=IntegratedBetaBinomial(M,4,p,20)
            self.assertEqual(law.mean,0);self.assertEqual(law.pmf(0),1)
            self.assertEqual(law.cdf(100),1);self.assertEqual(law.pmf(1),0)
        law=IntegratedBetaBinomial(30,4,1,20)
        self.assertAlmostEqual(law.cdf(50),stats.nbinom.cdf(50,4,4/34),places=12)

    def test_typed_restore_and_order(self):
        model=DispersionModel();payload=model.payload()
        restored=DispersionModel.restore(payload)
        z=np.asarray([[1,.5,.5,.4,.9,0,0],[1,.4,.6,.3,.8,0,0]])
        np.testing.assert_allclose(restored.precision(z),[restored.precision(v)for v in z],atol=1e-10,rtol=0)
        wrong=copy.deepcopy(payload);wrong['version']='OTHER'
        with self.assertRaises(ValueError):DispersionModel.restore(wrong)
        wrong=copy.deepcopy(payload);wrong['feature_order'].reverse()
        with self.assertRaises(ValueError):DispersionModel.restore(wrong)
        spec=IntegratedBetaBinomial(30,12,.64,120).parameters();spec['version']='OTHER'
        with self.assertRaises(ValueError):restore_law(spec)

    def test_invalid_training_rejected_before_fallback_or_optimizer(self):
        for n,c,m in [([10.5],[6],[.6]),([10],[6.1],[.6]),([10],[6],[float('nan')]),([float('inf')],[6],[.6])]:
            with self.assertRaises(ValueError):DispersionModel().fit(np.zeros((1,7)),n,c,m)

    def test_gradient_without_optimizer(self):
        z=np.asarray([[1,.2,.3,.4,.5,0,0],[1,.6,.5,.8,.1,0,1],[1,.7,.2,.1,.8,1,0]])
        n=np.asarray([30,35,25]);c=np.asarray([20,19,22]);m=np.asarray([.64,.63,.67]);b=prior_beta()
        _,gradient=DispersionModel.objective(b,z,n,c,m)
        finite=[]
        for i in range(7):
            plus=b.copy();minus=b.copy();plus[i]+=1e-5;minus[i]-=1e-5
            finite.append((DispersionModel.objective(plus,z,n,c,m)[0]-DispersionModel.objective(minus,z,n,c,m)[0])/2e-5)
        np.testing.assert_allclose(gradient,finite,atol=1e-6,rtol=1e-5)

    def test_known_zero_is_distinct_from_unknown_summary(self):
        class History:
            def __init__(self,row):self.row=row
            def describe(self,q):return dict(mix=np.full(25,1/25),own_attempts=10)
            def player_rows(self,p,t):return [self.row]
        row=dict(pass_destination_counts={'left':10,'middle':0,'right':0},field_context={'ydstogo':{'mean':0.,'n':10}},available=1,kickoff=0)
        q=dict(player_id='SYNTHETIC',kickoff=2)
        z,_=dispersion_features(q,History(row));self.assertEqual(z[2],0);self.assertEqual(z[3],0);self.assertEqual(z[5],0);self.assertEqual(z[6],0)
        row['pass_destination_counts']={};row['field_context']['ydstogo']={'mean':None,'n':0}
        z,_=dispersion_features(q,History(row));self.assertEqual(z[5],1);self.assertEqual(z[6],1)


if __name__=='__main__':unittest.main()
