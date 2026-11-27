import copy
import json
import unittest

from nfl_v2.qb_context_profiles import QBProfileAdapter, HISTORICAL_UNIVERSE


def source_row(game='past', kickoff=0., attempts=1, completions=0):
    return dict(game_id=game, player_id='QB1', season=2025, week=1,
        team='T1', opponent='D1', kickoff=kickoff, available=kickoff+604800,
        physical_participation=True, target_parity=True,
        official_attempts=attempts, official_completions=completions,
        context_attempts=[attempts]+[0]*24, context_completions=[completions]+[0]*24,
        field_context={x:dict(mean=None,n=0) for x in ('ydstogo','yardline_100','game_seconds_remaining','score_differential')},
        pass_destination_counts={'left':attempts})


def query():
    return dict(game_id='future',player_id='QB1',season=2025,week=3,
        team='T1',opponent='D1',position='QB',kickoff=1500000.,cutoff=1500000.)


class QBContextProfilesTest(unittest.TestCase):
    def test_known_zero_and_unknown_denominator_and_current_evidence(self):
        adapter=QBProfileAdapter([source_row()])
        result=adapter.build(query(),universe=HISTORICAL_UNIVERSE)
        self.assertEqual(result['contexts'][0]['completion_per_attempt']['state'],'KNOWN_ZERO')
        self.assertEqual(result['contexts'][1]['completion_per_attempt']['state'],'UNDEFINED_ZERO_DENOMINATOR')
        self.assertEqual(result['contexts'][1]['attempt_frequency']['state'],'KNOWN_ZERO')
        current=adapter.build(query(),universe='SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE')
        self.assertEqual(current['status'],'UNAVAILABLE_PROFILE')
        self.assertEqual(adapter.build(dict(query(),query_evidence=None),universe='SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE')['reason'],'QUERY_EVIDENCE_UNAVAILABLE')
        malformed=adapter.build(dict(query(),cutoff=float('nan')),universe='SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE')
        self.assertEqual(malformed['status'],'UNAVAILABLE_PROFILE')
        self.assertIsNone(malformed['identity']['cutoff'])
        json.dumps(malformed,allow_nan=False)
        q=query();q['query_evidence']=dict(source_id='SYNTHETIC_TEST_ONLY',source_sha256='0'*64,
            recorded_at=1499000.,canonical_identity_verified=True,historical_team_verified=True,eligible_role_verified=True)
        self.assertEqual(adapter.build(q,universe='SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE')['status'],'AVAILABLE_PROFILE')
        q['query_evidence']['recorded_at']=1500001.
        self.assertEqual(adapter.build(q,universe='SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE')['reason'],'QUERY_MEMBERSHIP_NOT_RETAINED_BEFORE_CUTOFF')
        q['query_evidence']['recorded_at']=True
        self.assertEqual(adapter.build(q,universe='SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE')['reason'],'QUERY_MEMBERSHIP_NOT_RETAINED_BEFORE_CUTOFF')

    def test_future_rows_and_target_outcomes_do_not_change_profile(self):
        q=query();first=QBProfileAdapter([source_row()]).build(q,universe=HISTORICAL_UNIVERSE)
        future=source_row('later',2000000.,50,45)
        q2=copy.deepcopy(q);q2.update(actual=999,official_attempts=999,official_completions=999,physical_participation=False)
        second=QBProfileAdapter([source_row(),future]).build(q2,universe=HISTORICAL_UNIVERSE)
        self.assertEqual(first,second)
        sparse=dict(q,player_id='UNSEEN')
        p=QBProfileAdapter([source_row()]).build(sparse,universe=HISTORICAL_UNIVERSE)
        self.assertEqual(p['history']['own']['eligible_games'],0)
        self.assertEqual(p['fallback'],'no_player_history_role_prior')

    def test_depth_known_false_and_absent_denominator_stay_distinct(self):
        past=source_row()
        chart=dict(game_id='past',player_id='QB1',available=past['available'],
            eligible_throws=[1,0,0,0,0],flags={
                flag:dict(known=[1,0,0,0,0],positive=[0,0,0,0,0])
                for flag in ('is_catchable_ball','is_drop','is_contested_ball')})
        p=QBProfileAdapter([past],depth_annotations={('past','QB1'):chart}).build(query(),universe=HISTORICAL_UNIVERSE)
        d=p['charted_depth_annotations']['frozen_depth_describer']
        self.assertEqual(d['raw_state'][0],'KNOWN_ZERO')
        self.assertEqual(d['raw_state'][1],'UNDEFINED_ZERO_DENOMINATOR')
        self.assertFalse(d['pooled_known_zero'][0])
        self.assertTrue(d['pooled_known_zero'][1])
        self.assertEqual(len(d['support'][0]),5)


if __name__=='__main__':
    unittest.main()
