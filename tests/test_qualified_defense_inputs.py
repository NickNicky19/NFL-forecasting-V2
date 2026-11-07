import unittest
import numpy as np
from nfl_v2.qualified_defense_inputs import augment,attach_future_context,GROUPS
from nfl_v2.qualified_defense import QualifiedDefenseHistory,game_observation

class QualifiedDefenseInputTests(unittest.TestCase):
 def history(self):
  r=dict(game_id='fictional',player_id='p',defense='D',position='RB',season=2025,kickoff=0.,available=10.,played=True,values={'rush_yd':-2.},workload={'carries':2.})
  return QualifiedDefenseHistory([game_observation([r],'rush_yd')])
 def q(self):return dict(defense='D',position='RB',target='rush_yd',cutoff=11.,blocked_reason=None)
 def test_own_block_unchanged_and_nested_groups(self):
  own=np.arange(20.);a,_=augment(own,self.history(),self.q(),2022,'D1');b,_=augment(own,self.history(),self.q(),2022,'D2');np.testing.assert_array_equal(a[:20],own);np.testing.assert_array_equal(a,b[:24]);self.assertEqual(b.shape,(29,))
 def test_strict_floor_removes_older_context(self):
  a,audit=augment(np.zeros(20),self.history(),self.q(),2026,'D2');self.assertTrue(np.isnan(a[20]));self.assertEqual(audit['league_rate_games'],0)
 def test_none_position_abstains_before_lookup(self):
  q=dict(self.q(),position=None,blocked_reason='UNQUALIFIED');a,audit=augment(np.zeros(20),None,q,2026,'D2');self.assertTrue(np.all(np.isnan(a[20:])));self.assertEqual(audit['state'],'BLOCKED_QUERY_NO_CONTEXT_LOOKUP')
 def test_exact_cutoff_is_excluded(self):
  a,_=augment(np.zeros(20),self.history(),dict(self.q(),cutoff=10.),2022,'D1');self.assertTrue(np.isnan(a[20]))
 def test_no_opponent_substitution(self):
  with self.assertRaises(ValueError):augment(np.zeros(20),self.history(),dict(self.q(),defense=None),2022,'D1')
 def test_future_board_requires_same_sleeper_game_direction_and_position(self):
  q=dict(game_id='fictional',sleeper_id='1',position='RB',blocked_reason=None);games={'fictional':dict(season=2026,week=8,home='H',away='A',espn='2')};board=dict(season=2026,week=8,players=[dict(id='1',game_id='2',pos='RB',team='H',opp='A')]);r=attach_future_context([q],games,board)[0];self.assertEqual(r['defense'],'A');board['players'][0]['opp']='Z'
  with self.assertRaises(ValueError):attach_future_context([q],games,board)
 def test_blocked_future_identity_remains_blocked(self):
  q=dict(game_id='fictional',sleeper_id='1',position=None,blocked_reason='NO_ID');g={'fictional':dict(season=2026,week=8,home='H',away='A',espn='2')};b=dict(season=2026,week=8,players=[]);r=attach_future_context([q],g,b)[0];self.assertIsNone(r['defense']);self.assertEqual(r['blocked_reason'],'NO_ID')
if __name__=='__main__':unittest.main()
