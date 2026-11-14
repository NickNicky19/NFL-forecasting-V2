"""Invented component contracts only; no NFL label reads or fits."""
import unittest
from nfl_v2.chart_sources import (CSV_SHA256_BY_SEASON,FIELDS,RARE,WEIGHTS_TIMES_50,chart_label)
from nfl_v2.scoring import CHART_WEIGHTS


class ChartSourceTests(unittest.TestCase):
    def row(self):
        return dict(season='2026',week='7',season_type='REG',
            **{v:'0'for v in FIELDS.values()},fumble_recovery_tds='0',special_teams_tds='0')
    def label(self,row,**kwargs):
        return chart_label(row,source_sha256=CSV_SHA256_BY_SEASON[2026],appearance_verified=True,game_completed_verified=True,**kwargs)
    def test_all_exact_sixteen_weights_match_independent_original_scorer(self):
        self.assertEqual(len(WEIGHTS_TIMES_50),16);self.assertEqual(len(FIELDS),12);self.assertEqual(len(RARE),4)
        self.assertEqual(set(WEIGHTS_TIMES_50),set(CHART_WEIGHTS))
        for k,w in WEIGHTS_TIMES_50.items():self.assertAlmostEqual(w/50,CHART_WEIGHTS[k])
    def test_ordinary_signed_example_exact_grid_and_unique_fumble(self):
        r=self.row();r.update(passing_yards='250',passing_tds='2',passing_interceptions='1',rushing_yards='-4',receptions='3',receiving_yards='27',receiving_tds='1',fumbles_lost_total='1',passing_2pt_conversions='1',receiving_2pt_conversions='1',sack_fumbles_lost='1',rushing_fumbles_lost='1')
        out=self.label(r);self.assertEqual(out['points_times_50'],1565);self.assertEqual(out['points'],31.3)
        self.assertEqual(out['components']['fumbles_lost'],1)
    def test_credited_two_point_catch_does_not_add_reception(self):
        r=self.row();r['receiving_2pt_conversions']='1';out=self.label(r)
        self.assertEqual(out['points'],2);self.assertEqual(out['components']['receptions'],0)
        r=self.row();r['passing_2pt_conversions']='1';self.assertEqual(self.label(r)['points'],2)
    def test_positive_or_missing_rare_totals_stay_missing(self):
        for field,value in [('fumble_recovery_tds','1'),('special_teams_tds','1'),('special_teams_tds',''),('fumble_recovery_tds',None)]:
            r=self.row();r[field]=value;out=self.label(r)
            self.assertIsNone(out['points']);self.assertEqual(out['status'],'EXCEPTIONAL_TD_ATTRIBUTION_UNRESOLVED')
            self.assertTrue(all(out['components'][k]is None for k in RARE))
    def test_missing_invalid_counts_never_fill_zero(self):
        for value in [None,'','NaN','Infinity','-1','.5',True]:
            r=self.row();r['fumbles_lost_total']=value;self.assertIsNone(self.label(r)['points'])
    def test_complete_zero_source_needs_appearance_and_finality(self):
        for appearance,completed in [(False,True),(True,False),(False,False)]:
            out=chart_label(self.row(),source_sha256=CSV_SHA256_BY_SEASON[2026],appearance_verified=appearance,game_completed_verified=completed)
            self.assertIsNone(out['points'])
        self.assertEqual(self.label(self.row())['points'],0.)
    def test_outside_panel_or_wrong_source_fails_before_components(self):
        r=self.row();r['week']='8'
        with self.assertRaises(ValueError):self.label(r)
        with self.assertRaises(ValueError):chart_label(self.row(),source_sha256='0'*64,appearance_verified=True,game_completed_verified=True)
    def test_signed_total_retained_without_unlisted_bonuses(self):
        r=self.row();r.update(rushing_yards='-3',def_fumbles_forced='10',def_fg_blocks='2',fumble_recovery_own='1')
        out=self.label(r);self.assertEqual(out['points_times_50'],-15);self.assertEqual(out['points'],-.3)


if __name__=='__main__':unittest.main()
