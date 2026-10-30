"""Fictional-law arithmetic/leakage fixtures; no NFL rows."""
import math,unittest
import numpy as np
from scipy import stats
from threadpoolctl import threadpool_limits
from nfl_v2.distribution_laws import Law,prior
from nfl_v2.distribution_wave import Design,FittedLawModel,feature_history,output_count

class DistributionWaveTests(unittest.TestCase):
 def test_signed_and_count_normalization_and_cdf(self):
  for law,lo,hi in [(Law('signed',center=-4,q=.6),-120,120),(Law('geometric',q=.6),0,120),(Law('poisson',mean=3.2),0,120),(Law('bernoulli',p=.3),0,1)]:
   support=np.arange(lo,hi+1);mass=np.asarray([law.pmf(float(x)) for x in support]);self.assertAlmostEqual(float(mass.sum()),1.,places=12)
   for x in range(-7,9):self.assertAlmostEqual(law.cdf(x),float(mass[support<=x].sum()),places=11)
 def test_crps_matches_independent_finite_double_sum(self):
  laws=[Law('signed',center=-2,q=.4),Law('geometric',q=.4),Law('poisson',mean=3.2),Law('bernoulli',p=.3)]
  laws.append(Law('mixture',support=[-4,0,3],weights=[.2,.5,.3],prior=laws[0]))
  for law in laws:
   values=np.arange(-100,101);p=np.asarray([law.pmf(float(x)) for x in values]);pair=float(np.sum(abs(values[:,None]-values[None,:])*p[:,None]*p[None,:]))
   for actual in [-4,0,7]:
    expected=float(np.dot(p,np.abs(values-actual))-.5*pair);self.assertAlmostEqual(law.crps(actual),expected,places=10)
 def test_log_mass_survives_underflow_and_true_infinite(self):
  law=Law('poisson',mean=.01);self.assertEqual(law.pmf(400),0.);self.assertTrue(math.isfinite(law.logpmf(400)));self.assertFalse(law.summary(400)['infinite_nll']);self.assertTrue(Law('zero').summary(2)['infinite_nll'])
 def test_exact_quantile_push_and_complements(self):
  law=Law('mixture',support=[-4,0,3],weights=[.2,.5,.3],prior=Law('signed',center=0,q=.5))
  for p in [.05,.5,.95]:
   q=law.quantile(p);self.assertGreaterEqual(law.cdf(q),p);self.assertLess(law.cdf(q-1),p)
  over=1-law.cdf(0);under=law.cdf(-1);push=law.pmf(0);self.assertAlmostEqual(over+under+push,1.);self.assertAlmostEqual((1-law.cdf(.5))+law.cdf(.5),1.)
 def test_strict_history_excludes_old_and_exact_availability(self):
  rows=[dict(player_id='p',position='RB',season=s,kickoff=k,available=a,game_id=str(s),values={'rush_att':v}) for s,k,a,v in [(2025,10.,20.,99.),(2026,30.,40.,2.)]]
  strict=feature_history(rows,2026);common=feature_history(rows,2022)
  f,m=strict.get('p','RB','rush_att',40.);self.assertTrue(math.isnan(f[0]));self.assertIsNone(m)
  f,m=strict.get('p','RB','rush_att',41.);self.assertEqual(f[0],2.);self.assertEqual(m,40.)
  self.assertEqual(common.get('p','RB','rush_att',41.)[0][0],50.5)
 def test_training_only_design_and_output_budget_count(self):
  d=Design().fit(np.asarray([[1.,math.nan],[3.,2.]]));before=d.median.copy();d.transform(np.asarray([[999.,99.]]),True);np.testing.assert_array_equal(before,d.median)
  self.assertEqual(output_count([{'target':'rec'},{'target':'anytime_td'}]),24)
 def test_no_old_NFL_startup_and_support(self):
  self.assertEqual(prior([], 'rush_yd').mean,0.);self.assertEqual(prior([], 'anytime_td').mean,.5);self.assertEqual(prior([-9,-2,5],'rush_yd').center,-2)
  self.assertEqual(prior([0,0,0],'rec').q,.05/1.05)
 def test_both_models_produce_supported_laws_on_fictional_data(self):
  rng=np.random.default_rng(1701);x=rng.normal(size=(120,20));x[0,0]=math.nan;y=rng.poisson(3,size=120).astype(float);pos=['RB']*120;priors={'RB':prior(y,'rush_att')}
  with threadpool_limits(limits=2):
   for family in ['ordered_leaf_cdf','regularized_glm_law']:
    model=FittedLawModel(family,'rush_att').fit(x,y,pos);laws=model.predict(x[:4],pos[:4],priors)
    for law,_ in laws:self.assertGreaterEqual(law.mean,0.);self.assertGreaterEqual(law.quantile(.05),0);self.assertGreaterEqual(law.summary(3)['crps'],0.)

if __name__=='__main__':unittest.main()
