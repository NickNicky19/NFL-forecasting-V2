import unittest
import numpy as np
from nfl_v2 import qb_opportunity_increment as inc


class OpportunityIncrementTests(unittest.TestCase):
    def test_unknown_values_are_not_observed_zero(self):
        groups={k:{} for k in ('R1_support','R2_player_values','R3_defense_values')}
        groups['R1_support']['own_opportunities']=0
        x=inc.appended_features(groups,'R1')
        self.assertEqual(x[0:2].tolist(),[0.,0.])
        self.assertEqual(x[2:4].tolist(),[0.,1.])
        self.assertTrue(np.isfinite(x).all())

    def test_nested_arms_and_no_own_playcall_or_duplicate_completion_rate(self):
        r1=inc.extra_names('R1');r2=inc.extra_names('R2');r3=inc.extra_names('R3')
        self.assertEqual(r2[:len(r1)],r1)
        self.assertEqual(r3[:len(r2)],r2)
        self.assertFalse(any(n=='own_dropback_per_opportunity' for b,n in r3))
        self.assertFalse(any('completion_rate' in n or 'completion_per_attempt' in n for b,n in r3))
        self.assertEqual(len(inc.feature_order(['BASE'],'R3')),1+2*len(r3))
        self.assertEqual(inc.extra_names('R0'),[])

    def test_priority_is_earlier_workload_proxy_without_target_outcome(self):
        class H:
            def describe(self,q):return {'own_games':1}
            def exposure(self,q):return type('E',(),{'mean':10.})()
        a=inc.priority({'official_attempts':0,'actual':None},H())
        b=inc.priority({'official_attempts':100,'actual':100},H())
        self.assertEqual(a,b)
        self.assertTrue(a['member'])
        self.assertIn('NOT_AUTHENTICATED',a['status'])

if __name__=='__main__':unittest.main()
