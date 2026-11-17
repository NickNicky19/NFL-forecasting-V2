import unittest
from decimal import Decimal
from nfl_v2.scoring import (CHART_WEIGHTS,chart_points,chart_points_exact,
    threshold_crossing,grade_settlement,event_probabilities,expected_value)
from nfl_v2.prop_selection import choose_side,timing_violations,fixed_top_k,rolling_top_k


class ExactPropTests(unittest.TestCase):
    def contract(self,target='rec'):
        return dict(verified=True,contract_id='fictional-refund',version='v1',book='fictional',
            jurisdiction='fixture',rule_source_id='fictional-rule',stat_correction_policy='official_final',
            injury_protection_rule='none',statistic=target,period='full_game',overtime=True,
            scoring_contract=target,event_scope='ordinary_official_statistic',payout_kind='cash_refund',
            tie_rule='cash_refund',dnp_rule='cash_refund',void_rule='cash_refund')

    def grade(self,actual=0,**kw):
        c=self.contract();args=dict(target='rec',participation='PLAYED',outcome_state='final',
            contract=c,outcome_contract=c,decimal_odds=None);args.update(kw)
        return grade_settlement(actual,'4.5','over',**args)

    def test_half_point_inequalities_far_beyond_line(self):
        for target,line,below,above in [('pass_td','1.5',1,4),('pass_cmp','19.5',19,35),
            ('rec','4.5',4,10),('rush_yd','49.5',49,130)]:
            self.assertEqual(threshold_crossing(above,line,'over',target=target),'WIN')
            self.assertEqual(threshold_crossing(below,line,'under',target=target),'WIN')
            self.assertEqual(threshold_crossing(above,line,'under',target=target),'LOSS')

    def test_integer_push_signed_and_fractional_grid(self):
        self.assertEqual(threshold_crossing(5,5,'over',target='rec'),'PUSH')
        self.assertEqual(threshold_crossing(-7,'-5.5','under',target='rush_yd'),'WIN')
        self.assertEqual(threshold_crossing('15.10','15.1','under',target='nick-chart-ppr-v1'),'PUSH')
        for y,t in [('.5','rec'),('-1','rec'),('15.05','nick-chart-ppr-v1'),('1','website-fantasy')]:
            with self.assertRaises(ValueError):threshold_crossing(y,1,'over',target=t)

    def test_exact_components_fix_float_tie_without_rounding(self):
        c=dict.fromkeys(CHART_WEIGHTS,0);c.update(rushing_yards=-5,receiving_yards=3)
        self.assertNotEqual(chart_points(c),-.2)
        self.assertEqual(chart_points_exact(c),Decimal('-.20'))
        self.assertEqual(threshold_crossing(chart_points_exact(c),'-.20','over',target='nick-chart-ppr-v1'),'PUSH')
        with self.assertRaises(ValueError):threshold_crossing(chart_points(c),'-.20','over',target='nick-chart-ppr-v1')

    def test_states_price_absence_and_played_zero(self):
        self.assertEqual(self.grade()['state'],'LOSS')
        self.assertIsNone(self.grade()['net'])
        self.assertEqual(self.grade(None,participation='DNP')['state'],'VOID')
        self.assertEqual(self.grade(None,participation='UNKNOWN')['state'],'UNKNOWN_PARTICIPATION')
        self.assertEqual(self.grade(None)['state'],'MISSING_ACTUAL')
        self.assertEqual(self.grade(None,outcome_state='pending')['state'],'PENDING')
        self.assertEqual(self.grade(10,contract=None)['state'],'UNRESOLVED_CONTRACT')
        c=self.contract();o=dict(c,period='first_half')
        self.assertEqual(self.grade(10,outcome_contract=o)['state'],'UNRESOLVED_CONTRACT')
        self.assertEqual(self.grade(10,decimal_odds='2.10')['net'],Decimal('1.10'))

    def test_probability_support_push_complements_and_mirror(self):
        laws=[event_probabilities([0,1,2],[.2,.5,.3],L)for L in ('.5','1','1.5')]
        self.assertEqual(laws[1],{'over':.3,'under':.2,'push':.5})
        self.assertEqual(laws[0]['push'],0)
        self.assertTrue(all(abs(sum(p.values())-1)<1e-12 for p in laws))
        self.assertGreaterEqual(laws[0]['over'],laws[1]['over']);self.assertGreaterEqual(laws[1]['over'],laws[2]['over'])
        self.assertAlmostEqual((.7-1)**2,(.3-0)**2)

    def test_EV_conditioning_and_likely_side_vs_value(self):
        a=expected_value('.3','.2',2,conditioning='conditional_nonvoid',p_nonvoid='.8')
        self.assertEqual(a,{'EV_nonvoid':Decimal('.1'),'EV_placed':Decimal('.08')})
        self.assertIsNone(expected_value('.3','.2',2,conditioning='conditional_nonvoid')['EV_placed'])
        p=dict(over='.4',under='.6',push=0,conditioning='conditional_nonvoid')
        self.assertEqual(choose_side('P2',probabilities=p),'under')
        self.assertEqual(choose_side('P3',probabilities=p,prices={'over':3,'under':'1.5'}),'over')
        self.assertIsNone(choose_side('P3',probabilities=p,prices={}))
        self.assertIsNone(choose_side('P1',point='4.5',line='4.5'))
        self.assertEqual(choose_side('P1',point='4.50001',line='4.5'),'over')

    def test_cutoff_and_identity_violations(self):
        ident=dict(event_id='g',player_id='p',target='rec',period='full_game',scoring_contract='rec')
        f=dict(ident,feature_cutoff='2026-10-20T10:00:00Z',training_label_cutoff='2026-10-19T10:00:00Z',
            fallback_cutoff='2026-10-20T10:00:00Z',calibration_cutoff='2026-10-19T10:00:00Z',
            issued_at='2026-10-20T10:00:00Z',persisted_at='2026-10-20T10:00:01Z')
        o=dict(ident,source_update='2026-10-20T10:00:00Z',received_at='2026-10-20T10:00:02Z',status='OPEN',kickoff='2026-10-20T15:00:00Z')
        self.assertEqual(timing_violations(f,o,'2026-10-20T10:01:00Z'),[])
        self.assertIn('FUTURE_feature_cutoff',timing_violations(dict(f,feature_cutoff='2026-10-20T10:02:00Z'),o,'2026-10-20T10:01:00Z'))
        self.assertIn('IDENTITY_player_id',timing_violations(f,dict(o,player_id='collision'),'2026-10-20T10:01:00Z'))
        self.assertIn('STALE_QUOTE',timing_violations(f,o,'2026-10-20T11:00:00Z'))
        self.assertIn('DECISION_NOT_PREGAME',timing_violations(f,o,'2026-10-20T16:00:00Z'))
        self.assertIn('INFORMATION_AFTER_ISSUANCE',timing_violations(dict(f,feature_cutoff='2026-10-20T10:00:30Z'),o,'2026-10-20T10:01:00Z'))

    def test_fixed_weekly_vs_rolling_and_duplicate(self):
        def row(i,available,kickoff):return dict(selection_unit_id=str(i),season=2026,week=7,target='rec',side='over',
            rank_score=i,available_at=available,decision_time=available,kickoff=kickoff)
        a=row(1,'2026-10-20T10:00:00Z','2026-10-20T12:00:00Z')
        b=row(2,'2026-10-20T13:00:00Z','2026-10-20T15:00:00Z')
        with self.assertRaises(ValueError):fixed_top_k([a,b],6,freeze_time='2026-10-20T11:00:00Z')
        self.assertEqual(len(rolling_top_k([{'decision_time':a['decision_time'],'candidates':[a]},
            {'decision_time':b['decision_time'],'candidates':[b]}],6)),2)
        with self.assertRaises(ValueError):fixed_top_k([a,a],6,freeze_time='2026-10-20T11:00:00Z')
        with self.assertRaises(ValueError):fixed_top_k([a,dict(a,selection_unit_id='x',target='rush_yd')],6,
            freeze_time='2026-10-20T11:00:00Z',ranking_kind='point_gap')
