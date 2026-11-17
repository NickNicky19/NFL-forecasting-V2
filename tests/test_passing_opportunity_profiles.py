import copy
import unittest

from nfl_v2.passing_opportunity_profiles import OpportunityHistory, blank_counts, blank_cells, coarse_bins, play_counts


def row(game,when,*,available=None,player='p',team='CHI',opponent='GB',attempts=20):
    c=blank_counts();c.update(opportunities=30,dropbacks=25,credited_attempts=attempts,completions=10,completion_known_attempts=attempts,sacks=3)
    return dict(game_id=game,player_id=player,team=team,opponent=opponent,season=2025,week=1,kickoff=when,
                available=when+604800 if available is None else available,counts=c,cells=blank_cells())


class ProfilesTest(unittest.TestCase):
    def test_null_completion_is_not_zero(self):
        p=dict(pass_attempt='1',sack='0',rush_attempt='0',qb_dropback='1',play_deleted='0',two_point_attempt='0',complete_pass='')
        c=play_counts(p)
        self.assertEqual(c['credited_attempts'],1)
        self.assertEqual(c['unknown_completion'],1)
        self.assertEqual(c['completion_known_attempts'],0)
        p['complete_pass']='0';c=play_counts(p)
        self.assertEqual(c['completion_known_attempts'],1)
        self.assertEqual(c['completions'],0)

    def test_unknown_safety_is_not_admitted(self):
        self.assertIsNone(play_counts(dict(pass_attempt='1',sack='0',play_deleted='',two_point_attempt='0')))

    def test_spike_outside_dropback_is_not_conditional_attempt(self):
        c=play_counts(dict(pass_attempt=1,sack=0,qb_dropback=0,qb_spike=1,play_deleted=0,two_point_attempt=0,complete_pass=0))
        self.assertEqual(c['credited_attempts'],1)
        self.assertEqual(c['attempts_on_dropbacks'],0)
        self.assertEqual(c['spike_known_attempts'],1)

    def test_boundary_and_credited_no_play(self):
        self.assertEqual(coarse_bins(dict(down=4,ydstogo=11,yardline_100=20)),(3,3,3))
        c=play_counts(dict(play_type='no_play',pass_attempt=1,sack=0,play_deleted=0,two_point_attempt=0,complete_pass=0))
        self.assertEqual(c['credited_attempts'],1)

    def test_admission_order_and_target_mutation(self):
        rr=[row('b',200),row('a',100),row('future',2000000)]
        h=OpportunityHistory(rr,rr,own_window=1)
        q=dict(game_id='q',player_id='p',team='CHI',opponent='GB',season=2026,week=1,kickoff=800000)
        self.assertEqual(h.build(q)['own']['game_ids'],['b'])
        baseline=h.feature_groups(q)
        q.update(attempts=999,completions=999,actual_down_mix=[99])
        self.assertEqual(h.feature_groups(q),baseline)
        # Equality is not admitted under the unchanged strict-< policy.
        self.assertEqual(h.rows(604900,player='p'),[])

    def test_unknown_clock_rejected(self):
        rr=[row('a',100)];rr[0]['available']=None
        with self.assertRaisesRegex(ValueError,'Unknown history clock'):
            OpportunityHistory(rr,rr)

    def test_all_teams_have_defined_empty_profiles(self):
        h=OpportunityHistory([],[])
        p=h.defense_profile('CHI',100,2026,1)
        self.assertEqual(p['summary']['games'],0)
        self.assertIsNone(p['summary']['rates']['completion_per_attempt']['shrunk'])

    def test_current_query_requires_membership_not_outcome(self):
        h=OpportunityHistory([],[])
        q=dict(game_id='q',player_id='p',team='CHI',opponent='GB',season=2026,week=1,kickoff=800000)
        self.assertEqual(h.build_current(q)['status'],'UNAVAILABLE_PROFILE')
        q['query_evidence']=dict(canonical_identity_verified=True,historical_team_verified=True,eligible_role_verified=True,
                                source_id='fixture',source_sha256='a'*64,recorded_at=799999)
        self.assertEqual(h.build_current(q)['query_population'],'SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE')


if __name__=='__main__':unittest.main()
