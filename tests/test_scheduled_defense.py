import unittest

from nfl_v2.qualified_defense import QualifiedDefenseHistory, game_observation
from nfl_v2.scheduled_defense import ScheduledQualifiedDefenseHistory


class ScheduledDefenseTests(unittest.TestCase):
    def games(self, n=5, season=2025):
        return [dict(game_id=f'fiction-{i}', season=season, week=i+1,
                     kickoff=i*864000., home='D', away='O') for i in range(n)]

    def observation(self, i, value=10., carries=2, season=2025):
        return game_observation([dict(game_id=f'fiction-{i}', defense='D', position='TE',
            season=season, kickoff=i*864000., available=i*864000.+604800.,
            player_id=f'fiction-p-{i}', played=True, values={'rush_yd':value},
            workload={'carries':carries})], 'rush_yd')

    def test_absent_group_consumes_slot_without_fabricated_zero(self):
        obs=[self.observation(0,100.), self.observation(1,2.), self.observation(2,4.),
             self.observation(3,6.)]
        h=ScheduledQualifiedDefenseHistory(obs,self.games())
        x,a=h.at('D','TE','rush_yd',5000000.)
        old,_=QualifiedDefenseHistory(obs).at('D','TE','rush_yd',5000000.)
        self.assertEqual(a['local_game_ids'],[f'fiction-{i}' for i in range(1,5)])
        self.assertEqual(a['absent_group_game_ids'],['fiction-4'])
        self.assertEqual(x['qualified_allowed_mean4'],4.)
        self.assertEqual(x['complete_target_games4'],3)
        self.assertNotEqual(x['qualified_allowed_mean4'],old['qualified_allowed_mean4'])
        self.assertEqual(a['league_rate'],112./8.)

    def test_all_absent_slots_are_unknown_but_coverage_is_zero(self):
        h=ScheduledQualifiedDefenseHistory([],self.games())
        x,a=h.at('D','TE','rush_yd',5000000.)
        self.assertIsNone(x['qualified_allowed_mean4'])
        self.assertIsNone(x['shrunk_allowed_per_opportunity4'])
        self.assertEqual(x['complete_target_games4'],0)
        self.assertEqual(x['qualified_rows4'],0)
        self.assertEqual(a['absent_group_slots'],4)

    def test_availability_is_strict_and_no_target_game(self):
        h=ScheduledQualifiedDefenseHistory([self.observation(0)],self.games(1))
        x,a=h.at('D','TE','rush_yd',604800.)
        self.assertEqual(a['local_game_slots'],0)
        x,a=h.at('D','TE','rush_yd',604800.01)
        self.assertEqual(x['qualified_allowed_mean4'],10.)

    def test_strict_floor_removes_scheduled_old_slots_and_league(self):
        h=ScheduledQualifiedDefenseHistory([self.observation(0)],self.games(1))
        x,a=h.at('D','TE','rush_yd',604801.,feature_floor=2026)
        self.assertEqual(a['local_game_slots'],0)
        self.assertEqual(a['league_rate_games'],0)
        self.assertIsNone(x['shrunk_allowed_per_opportunity4'])

    def test_observed_missing_target_consumes_slot_and_signed_yards_survive(self):
        obs=[self.observation(0,-2.),self.observation(1,None)]
        x,a=ScheduledQualifiedDefenseHistory(obs,self.games(2)).at('D','TE','rush_yd',2000000.)
        self.assertEqual(x['qualified_allowed_mean4'],-2.)
        self.assertEqual(x['complete_target_games4'],1)
        self.assertEqual(a['absent_group_slots'],0)

    def test_league_prior_identical_when_local_absent(self):
        obs=[self.observation(0,10.)]
        h=ScheduledQualifiedDefenseHistory(obs,self.games())
        x,a=h.at('D','TE','rush_yd',5000000.)
        self.assertEqual(x['complete_rate_games4'],0)
        self.assertEqual(x['shrunk_allowed_per_opportunity4'],5.)
        self.assertEqual(x['allowed_rate_minus_league'],0.)
        self.assertEqual(a['league_rate_games'],1)

    def test_schedule_binding_duplicates_and_week8_outcomes_are_rejected(self):
        with self.assertRaises(ValueError):ScheduledQualifiedDefenseHistory([],self.games()+self.games())
        g=self.games(1);g[0]['kickoff']=1.
        with self.assertRaises(ValueError):ScheduledQualifiedDefenseHistory([self.observation(0)],g)
        g=self.games(1,2026);g[0]['week']=8
        with self.assertRaises(ValueError):ScheduledQualifiedDefenseHistory([],g)

    def test_ordinary_complete_schedule_exact_feature_parity(self):
        obs=[self.observation(i,2.*i) for i in range(5)]
        x,a=ScheduledQualifiedDefenseHistory(obs,self.games()).at('D','TE','rush_yd',5000000.)
        y,b=QualifiedDefenseHistory(obs).at('D','TE','rush_yd',5000000.)
        self.assertEqual(x,y)
        self.assertEqual(a['local_game_ids'],b['local_game_ids'])


if __name__ == '__main__': unittest.main()
