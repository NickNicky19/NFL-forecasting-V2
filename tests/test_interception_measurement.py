"""Source-presence and exact-identity boundaries for versioned regrading."""
import copy
import math
import unittest

from tools.audit_website_interceptions import original_actual, qualified_actual, SUPPORT
from nfl_v2.scoring import threshold_crossing


class InterceptionMeasurementTests(unittest.TestCase):
    def setUp(self):
        self.row=dict(season=2026,week=5,game_id='event-a',player_id='sleeper-a',
                      team='AAA',opponent='BBB',played_evidence=dict(gp=1,off_snp=50,pass_att=30),
                      pass_int_field_present=False,reported_pass_int=None)
        self.label=dict(season=2026,week=5,source_game_id='event-a',source_player_id='sleeper-a',
                        team='AAA',opponent='BBB',player_id='gsis-a',game_id='2026_05_AAA_BBB',
                        label_support=SUPPORT,finality='STATUS_FINAL',corrected_pass_int=0,
                        weekly_source_sha256='a'*64,espn_source_sha256='b'*64,finality_source_sha256='c'*64)

    def test_participation_does_not_supply_missing_or_null_stat(self):
        self.assertIsNone(original_actual(self.row))
        self.assertIsNone(original_actual(dict(self.row,pass_int_field_present=True)))
        self.assertIsNone(qualified_actual(self.row,None))

    def test_explicit_reported_zero_is_valid(self):
        self.assertEqual(original_actual(dict(self.row,pass_int_field_present=True,reported_pass_int=0)),0)
        self.assertEqual(qualified_actual(self.row,self.label),0)
        self.assertEqual(threshold_crossing(qualified_actual(self.row,self.label),.5,'under',target='pass_int'),'WIN')

    def test_new_source_version_does_not_overwrite_original(self):
        before=copy.deepcopy(self.row)
        self.assertEqual(qualified_actual(self.row,self.label),0)
        self.assertEqual(self.row,before)
        self.assertIsNone(original_actual(self.row))

    def test_exact_identity_and_historical_team_required(self):
        for field,value in [('source_game_id','event-b'),('source_player_id','other'),('week',6),('team','CCC'),('opponent','CCC')]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                qualified_actual(self.row,dict(self.label,**{field:value}))

    def test_unqualified_or_unfinished_source_cannot_supply_zero(self):
        for field,value in [('label_support','PARTICIPATION_ONLY'),('finality','STATUS_IN_PROGRESS'),('weekly_source_sha256',None)]:
            with self.subTest(field=field):
                self.assertIsNone(qualified_actual(self.row,dict(self.label,**{field:value})))

    def test_invalid_counts_are_not_zero(self):
        for value in (True,-1,.5,math.nan,math.inf,None):
            with self.subTest(value=value):
                self.assertIsNone(qualified_actual(self.row,dict(self.label,corrected_pass_int=value)))
                self.assertIsNone(original_actual(dict(self.row,pass_int_field_present=True,reported_pass_int=value)))


if __name__=='__main__':unittest.main()
