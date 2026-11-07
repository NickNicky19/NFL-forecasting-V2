import unittest

from nfl_v2.qualified_defense import QualifiedDefenseHistory, game_observation


class QualifiedDefenseTests(unittest.TestCase):
    def row(self, **kw):
        row=dict(game_id='fictional',defense='D',position='RB',season=2025,kickoff=0.,
                 available=10.,player_id='fictional-p',played=True,
                 values={'rush_yd':-2.,'nick-chart-ppr-v1':-10},workload={'carries':2})
        row.update(kw);return row

    def test_signed_rate_shrinkage_uses_compatible_units_and_strict_cutoff(self):
        obs=game_observation([self.row()], 'rush_yd')
        history=QualifiedDefenseHistory([obs])
        x,_=history.at('D','RB','rush_yd',10.)
        self.assertIsNone(x['qualified_allowed_mean4'])
        x,a=history.at('D','RB','rush_yd',11.)
        self.assertEqual(x['shrunk_allowed_per_opportunity4'],-1.)
        self.assertEqual(x['allowed_rate_minus_league'],0.)
        self.assertEqual(a['local_game_ids'],['fictional'])

    def test_unknown_target_or_incompatible_exposure_never_becomes_zero_rate(self):
        missing=game_observation([self.row(values={'rush_yd':None})], 'rush_yd')
        self.assertIsNone(missing['target_sum'])
        exceptional=game_observation([self.row(values={'rush_yd':3},workload={'carries':0})], 'rush_yd')
        self.assertEqual(exceptional['target_sum'],3)
        self.assertIsNone(exceptional['opportunities'])

    def test_strict_season_memory_excludes_old_observations_and_priors(self):
        history=QualifiedDefenseHistory([game_observation([self.row()], 'rush_yd')])
        x,a=history.at('D','RB','rush_yd',100.,feature_floor=2026)
        self.assertIsNone(x['shrunk_allowed_per_opportunity4'])
        self.assertEqual(a['league_rate_games'],0)

    def test_chart_uses_signed_points_per_qualified_appearance(self):
        obs=game_observation([self.row()], 'nick-chart-ppr-v1')
        self.assertEqual(obs['target_sum'],-.2)
        self.assertEqual(obs['opportunities'],1.)

    def test_missing_game_slots_consume_the_four_game_window(self):
        obs=[]
        for i in range(5):
            r=self.row(game_id='fixture'+str(i),kickoff=float(i),available=10.+i,
                       values={'rush_yd':10. if i==0 else None})
            obs.append(game_observation([r],'rush_yd'))
        x,a=QualifiedDefenseHistory(obs).at('D','RB','rush_yd',20.)
        self.assertEqual(a['local_game_slots'],4)
        self.assertIsNone(x['qualified_allowed_mean4'])

    def test_duplicate_players_and_observations_are_rejected(self):
        with self.assertRaises(ValueError):game_observation([self.row(),self.row()], 'rush_yd')
        obs=game_observation([self.row()], 'rush_yd')
        with self.assertRaises(ValueError):QualifiedDefenseHistory([obs,obs])
