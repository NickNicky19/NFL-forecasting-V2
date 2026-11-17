"""Fictional signed-score/missingness/ranking fixtures; no NFL rows or fits."""
import unittest
from nfl_v2.chart_cohorts import ScoreHistory,memberships,band,TARGET,identity

class ChartCohortTests(unittest.TestCase):
    def test_missing_slots_consume_three_window_and_exact_cutoff_excludes(self):
        h=ScoreHistory([dict(player_id='p',game_id=str(i),available=t,points=v)for i,(t,v)in enumerate([(0,99.),(1,-.02),(2,None),(3,None),(4,44.)])])
        self.assertEqual(h.at('p',4),dict(mean=-.02,supported_slots=1,history_slots=3,latest_available=3))
        h=ScoreHistory([dict(player_id='p',game_id=str(i),available=i,points=v)for i,v in enumerate([12.,None,None,None])])
        self.assertIsNone(h.at('p',4)['mean']);self.assertEqual(h.at('p',4)['history_slots'],3)
    def test_signed_zero_and_inclusive_score_bands(self):
        self.assertEqual([band(x)for x in(None,-3.02,0.,5.,5.02,15.,15.02)],['unknown','low','zero','low','middle','middle','high'])
    def test_lexical_ties_nested_top_and_disjoint_bands(self):
        qs=[dict(player_id=f'p{i:02}',game_id='next',week=1,target=TARGET,population='fixture')for i in reversed(range(25))]
        h=ScoreHistory([dict(player_id=q['player_id'],game_id='old',available=1,points=1.)for q in qs]);m,_=memberships(qs,h,{1:2})
        self.assertEqual(m[identity(qs[-1])]['rank'],1)
        self.assertEqual([sum('top'+str(k)in x['cohorts']for x in m.values())for k in(10,15,20)],[10,15,20])
        self.assertEqual([sum(k in x['cohorts']for x in m.values())for k in('rank1_10','rank11_15','rank16_20','rank21plus')],[10,5,5,5])
    def test_blocked_identity_unranked_and_empty_future_cohort(self):
        q=dict(player_id=None,sleeper_id='raw-exact',game_id='next',week=8,target=TARGET,population='fixture',blocked_reason='UNKNOWN')
        m,_=memberships([q],ScoreHistory([]),{8:2});self.assertEqual(m[identity(q)]['cohorts'],['all','unranked','score_history_unknown'])
        self.assertIsNone(m[identity(q)]['mean']);self.assertEqual(memberships([],ScoreHistory([]),{8:2}),({},[]))
    def test_same_frozen_selector_has_no_competitor_or_targetgame_input(self):
        q=dict(player_id='p',game_id='next',week=1,target=TARGET,population='fixture')
        h=ScoreHistory([dict(player_id='p',game_id='old',available=1,points=-1.02),dict(player_id='p',game_id='next',available=3,points=999.)])
        m,_=memberships([q],h,{1:2});self.assertEqual(m[identity(q)]['mean'],-1.02)
        self.assertNotIn('workload',str(m));self.assertEqual(m[identity(q)]['supported_slots'],1)

if __name__=='__main__':unittest.main()
