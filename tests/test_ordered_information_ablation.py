"""Fictional feature and scoring checks; no model optimization or NFL rows."""
import unittest,math
import numpy as np
from nfl_v2.ordered_information_ablation import project,KEEP,KEEP_NAMES,TARGETS,POLICIES,Metrics,CHART,laws_prior
from nfl_v2.distribution_wave_v2 import feature_history

class OrderedInformationAblationTests(unittest.TestCase):
    def test_removes_entire_lag_block_preserving_means_and_roles(self):
        x=np.arange(40.).reshape(2,20);want=x[:,[0,1,2,3,16,17,18,19]];np.testing.assert_array_equal(project(x),want)
        changed=x.copy();changed[:,4:16]=999999.;np.testing.assert_array_equal(project(changed),want)
        self.assertEqual(len(KEEP_NAMES),8);self.assertEqual(len(KEEP),8)
        with self.assertRaises(ValueError):project(np.zeros((2,19)))
    def test_missing_values_remain_missing_not_zero_features(self):
        x=np.zeros((1,20));x[0,0]=math.nan;self.assertTrue(math.isnan(project(x)[0,0]))
    def test_strict_memory_excludes_older_target_and_cutoff_equality(self):
        rows=[dict(player_id='p',season=y,available=a,kickoff=k,game_id=str(y),values={'rush_att':v})for y,a,k,v in[(2025,20.,10.,99.),(2026,40.,30.,2.)]]
        strict=feature_history(rows,2026);self.assertTrue(math.isnan(strict.get('p','RB','rush_att',40.)[0][0]));self.assertEqual(strict.get('p','RB','rush_att',41.)[0][0],2.)
    def test_all_twelve_balanced_grid_without_future_or_extra_families(self):
        self.assertEqual(len(TARGETS),12);self.assertEqual(len(set(TARGETS)),12);self.assertEqual(7*len(TARGETS)*len(POLICIES),336)
    def test_chart_median_precision_is_exact_but_mean_not_rounded(self):
        summary=dict(crps=1.,nll=2.,infinite_nll=False,interval90_width=3.,interval90_covered=True,zero_mass=.1)
        m=Metrics();m.add(dict(prediction=5.02,actual=4.02,fallback='none',game_id='fixture',distribution_summary=summary))
        r=m.result(CHART,'lower_median');self.assertEqual(r['abs_lt_1'],0.);self.assertEqual(r['abs_le_1'],1.);self.assertEqual(r['precision_counts_exact_grid']['abs_lt_1']['numerator'],0)
        mean=m.result(CHART,'mean');self.assertNotIn('precision_counts_exact_grid',mean)
    def test_signed_chart_prior_scale_and_actual_law_support(self):
        law=laws_prior(np.asarray([-151.,-50.,0.,100.]),CHART);self.assertEqual(law.center,-50);self.assertGreaterEqual(law.q,50/51);self.assertGreater(law.pmf(-200),0)
    def test_missing_label_remains_coverage(self):
        m=Metrics();m.add(dict(prediction=0.,actual=None,fallback='constant_zero',game_id='fixture',distribution_summary={}))
        r=m.result('rush_att','lower_median');self.assertEqual(r['n'],0);self.assertEqual(r['forecast_rows'],1);self.assertIsNone(r['mae'])

if __name__=='__main__':unittest.main()
