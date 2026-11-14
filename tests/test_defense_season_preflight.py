import unittest
from unittest.mock import patch
from nfl_v2 import defense_season_preflight as s
from nfl_v2.qualified_defense import QualifiedDefenseHistory,game_observation
from nfl_v2.scheduled_defense import ScheduledQualifiedDefenseHistory

DAY=86400

def fixtures():
    games=[];observations=[]
    for i in range(6):
        year=2024 if i==0 else 2025;ko=10*i*DAY
        games.append(dict(game_id='fixture-'+str(i),season=year,week=max(1,i),kickoff=ko,home='AAA',away='BBB',period='REG'))
        if i==2:continue
        row=dict(game_id='fixture-'+str(i),season=year,position='RB',player_id='fixture-player-'+str(i),defense='AAA',kickoff=ko,available=ko+7*DAY,played=True,values={'rush_yd':-100 if i==0 else i},workload={'carries':1})
        observations.append(game_observation([row],'rush_yd'))
    return observations,games

class DefenseSeasonReadinessTests(unittest.TestCase):
    def test_history_arms_are_season_relative_and_alias_without_extra_fits(self):
        self.assertEqual(s.policies(2025)['H-RECENT-COMMON'],('H-RECENT',2024,2022))
        self.assertEqual(s.policies(2022)['H-RECENT-COMMON'],('H-RECENT',2022,2022))
        grid=s.logical_grid(2022,['rush_yd'],weeks=[1],windows=['observed'])
        self.assertEqual(len(grid),8);self.assertEqual(sum(not r['alias_of_unrun_origin']for r in grid),2)
        self.assertTrue(all(r['state'].startswith('FIT_REQUIRED')for r in grid))

    def test_label_availability_is_strict_and_no_future_or_pre2022_hidden(self):
        rows=[dict(season=2024,available=99),dict(season=2025,available=100),dict(season=2025,available=101)]
        self.assertEqual(s.eligible_training(rows,2025,'H-RECENT-COMMON',100),rows[:1])
        self.assertEqual(s.eligible_training(rows,2025,'H-CURRENT-COMMON',100),[])
        for year in [2021,2026]:
            with self.assertRaises(ValueError):s.eligible_training([dict(season=year,available=0)],2025,'H-MULTI-COMMON',100)

    def test_observed_strict_adapter_equals_existing_floor_and_filters_league(self):
        obs,games=fixtures();cutoff=61*DAY
        actual,a=s.SeasonBoundDefenseHistory(obs,games,year=2025,feature_floor=2025,window='observed').at('AAA','RB','rush_yd',cutoff)
        expected,b=QualifiedDefenseHistory(obs).at('AAA','RB','rush_yd',cutoff,feature_floor=2025)
        self.assertEqual(actual,expected);self.assertEqual(a['local_game_ids'],b['local_game_ids']);self.assertEqual(a['league_rate'],b['league_rate'])
        common,_=s.SeasonBoundDefenseHistory(obs,games,year=2025,feature_floor=2022,window='observed').at('AAA','RB','rush_yd',cutoff)
        self.assertNotEqual(common['shrunk_allowed_per_opportunity4'],actual['shrunk_allowed_per_opportunity4'])

    def test_scheduled_strict_floor_missing_group_and_old_contract_preserved(self):
        obs,games=fixtures();cutoff=61*DAY
        with self.assertRaises(ValueError):ScheduledQualifiedDefenseHistory(obs,games).at('AAA','RB','rush_yd',cutoff,feature_floor=2025)
        actual,a=s.SeasonBoundDefenseHistory(obs,games,year=2025,feature_floor=2025,window='scheduled').at('AAA','RB','rush_yd',cutoff)
        expected,_=ScheduledQualifiedDefenseHistory([r for r in obs if r['season']>=2025],[g for g in games if g['season']>=2025]).at('AAA','RB','rush_yd',cutoff,feature_floor=2022)
        self.assertEqual(actual,expected);self.assertEqual(a['absent_group_game_ids'],['fixture-2']);self.assertEqual(actual['qualified_allowed_mean4'],4)
        self.assertEqual(actual['complete_target_games4'],3);self.assertEqual(a['local_game_slots'],4)

    def test_defense_exact_availability_boundary_excluded(self):
        obs,games=fixtures();clock=57*DAY
        for window in ['observed','scheduled']:
            _,a=s.SeasonBoundDefenseHistory(obs,games,year=2025,feature_floor=2025,window=window).at('AAA','RB','rush_yd',clock)
            self.assertNotIn('fixture-5',a['local_game_ids'])
            self.assertLess(a['latest_local_available'],clock)

    def test_parameterized_planning_never_calls_model_fit_or_predict(self):
        from nfl_v2 import distribution_wave_v2 as laws
        with patch.object(laws.FittedLawModel,'fit',side_effect=AssertionError('No model fit authorized')),patch.object(laws.FittedLawModel,'predict',side_effect=AssertionError('No model inference authorized')):
            for year in range(2022,2026):self.assertEqual(len(s.logical_grid(year,['anytime_td','rush_yd'])),576)

    def test_input_year_and_memory_floor_contract(self):
        obs,games=fixtures()
        for floor in [2021,2023,2026]:
            with self.assertRaises(ValueError):s.SeasonBoundDefenseHistory(obs,games,year=2025,feature_floor=floor,window='observed')
        with self.assertRaises(ValueError):s.SeasonBoundDefenseHistory(obs+[dict(obs[0],season=2026)],games,year=2025,feature_floor=2022,window='observed')
