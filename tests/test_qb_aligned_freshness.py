import copy
import math
import unittest

import numpy as np

from nfl_v2 import player_context_matchup as ctx
from nfl_v2 import qb_opportunity_increment as inc
from nfl_v2.passing_opportunity_profiles import OpportunityHistory,blank_counts,blank_cells
from nfl_v2.qb_aligned_freshness import (CONTROL,ALTERNATIVE,AlignedFreshnessBundle,
    PolicyOpportunityHistory,reconstruct_rows,eligible_recent)


def qb_row(game,kickoff,attempts=20):
    a=[0]*25;c=[0]*25;a[1]=attempts;c[1]=attempts//2
    return dict(game_id=game,player_id='p',team='CHI',opponent='GB',season=2025,week=1,
        kickoff=kickoff,available=kickoff+604800,physical_participation=True,target_parity=True,
        official_attempts=attempts,official_completions=attempts//2,attempts=attempts,completions=attempts//2,
        context_attempts=a,context_completions=c,
        field_context={k:dict(mean=10.,n=attempts) for k in ctx.FIELD_NAMES})


def source(rows):
    team=[];qb=[]
    for r in rows:
        c=blank_counts();c.update(opportunities=30,dropbacks=25,credited_attempts=r['attempts'],
            attempts_on_dropbacks=r['attempts'],completions=r['completions'],completion_known_attempts=r['attempts'],
            dropback_known_opportunities=30,sack_known_dropbacks=25,scramble_known_dropbacks=25,
            spike_known_attempts=r['attempts'],sacks=3,attributed_team_dropbacks=25,attributed_team_attempts=r['attempts'])
        row={k:r[k] for k in ('game_id','player_id','team','opponent','season','week','kickoff','available')}
        row.update(counts=c,cells=blank_cells());qb.append(row)
        row=copy.deepcopy(row);del row['player_id'];team.append(row)
    return dict(team_games=team,QB_games=qb)


class FreshnessTest(unittest.TestCase):
    def setUp(self):
        self.rows=[qb_row('g1',1000000),qb_row('g2',1500000),qb_row('g3',2000000)]
        self.source=source(self.rows)
        self.q=dict(game_id='future',player_id='p',team='CHI',opponent='GB',season=2025,week=2,kickoff=2250000)

    def test_control_exact_features_and_prior_membership(self):
        b=AlignedFreshnessBundle(self.rows,self.source,policy_id=CONTROL)
        history=ctx.ContextHistory(self.rows,8,20)
        opportunity=OpportunityHistory(self.source['team_games'],self.source['QB_games'])
        for f,r in (('F0','R0'),('F1','R2')):
            np.testing.assert_allclose(b.direct_features(self.q,f),inc.direct_features(self.q,history,opportunity,r),equal_nan=True)
        self.assertEqual([r['game_id'] for r in b.training_rows(2025,self.q['kickoff'])],['g1','g2'])

    def test_aligned_alternative_changes_all_existing_histories(self):
        old=AlignedFreshnessBundle(self.rows,self.source,policy_id=CONTROL)
        new=AlignedFreshnessBundle(self.rows,self.source,policy_id=ALTERNATIVE)
        self.assertEqual([r['game_id'] for r in new.training_rows(2025,self.q['kickoff'])],['g1','g2','g3'])
        self.assertEqual(new.history.player_rows('p',self.q['kickoff'])[-1]['game_id'],'g3')
        self.assertEqual(new.history.group_rows('GB',self.q['kickoff'],True)[-1]['game_id'],'g3')
        self.assertEqual(new.opportunity.rows(self.q['kickoff'],team='CHI')[-1]['game_id'],'g3')
        self.assertEqual(old.history.group_rows('GB',self.q['kickoff'],True)[-1]['game_id'],'g2')
        self.assertEqual(len(new.direct_features(self.q,'F3')),len(old.direct_features(self.q,'F1')))

    def test_future_and_target_mutations_do_not_change_earlier_features(self):
        baseline=AlignedFreshnessBundle(self.rows,self.source,policy_id=ALTERNATIVE)
        rows=copy.deepcopy(self.rows);rows.append(qb_row('target',self.q['kickoff'],1000))
        rows.append(qb_row('later',self.q['kickoff']+1000000,1000))
        changed=AlignedFreshnessBundle(rows,source(rows),policy_id=ALTERNATIVE)
        for arm in ('F2','F3'):
            np.testing.assert_allclose(baseline.direct_features(self.q,arm),changed.direct_features(self.q,arm),equal_nan=True)
        q=dict(self.q,official_attempts=999,official_completions=999,available=None)
        np.testing.assert_allclose(baseline.direct_features(self.q,'F3'),baseline.direct_features(q,'F3'),equal_nan=True)

    def test_explicit_unknown_is_never_reconstructed(self):
        for value in (None,float('nan'),float('inf'),True):
            rows=copy.deepcopy(self.rows);rows[0]['available']=value
            valid,u=reconstruct_rows(rows,ALTERNATIVE)
            self.assertEqual(len(valid),2)
            self.assertEqual(u[0]['reason'],'EXPLICIT_UNKNOWN_AVAILABILITY')
        rows=copy.deepcopy(self.rows);rows[0]['observed_available_at']=None
        valid,u=reconstruct_rows(rows,ALTERNATIVE)
        self.assertEqual(u[0]['reason'],'EXPLICIT_UNKNOWN_OBSERVATION_CLOCK')

    def test_absent_column_requires_distinct_declared_policy(self):
        rows=copy.deepcopy(self.rows)
        for r in rows:del r['available']
        self.assertEqual(len(reconstruct_rows(rows,ALTERNATIVE)[1]),3)
        valid,u=reconstruct_rows(rows,ALTERNATIVE,allow_absent_column=True)
        self.assertFalse(u)
        self.assertEqual(valid[0]['available'],valid[0]['kickoff']+172800)
        mixed=copy.deepcopy(self.rows);del mixed[0]['available']
        self.assertEqual(len(reconstruct_rows(mixed,ALTERNATIVE,allow_absent_column=True)[1]),1)

    def test_admission_then_game_time_not_publication_order(self):
        rows=[dict(game_id='g'+str(i),player_id='p',team='CHI',opponent='GB',kickoff=i,
                   available=available,value=value) for i,available,value in ((1,100,100),(2,20,10),(3,30,20),(4,40,30))]
        chosen=eligible_recent(rows,101,3,player_id='p')
        self.assertEqual(sum(r['value'] for r in chosen)/3,20)
        self.assertEqual([r['game_id'] for r in chosen],['g2','g3','g4'])
        self.assertEqual(eligible_recent(rows,20,3,player_id='p'),[])

    def test_mixed_wrong_clock_duplicate_and_old_guard(self):
        rows=copy.deepcopy(self.rows);rows[0]['available']=rows[0]['kickoff']+172800
        valid,u=reconstruct_rows(rows,ALTERNATIVE)
        self.assertEqual(u[0]['reason'],'INPUT_NOT_DECLARED_SEVEN_DAY_RECONSTRUCTION')
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            reconstruct_rows(self.rows+[self.rows[0]],ALTERNATIVE)
        conflicting=copy.deepcopy(self.rows[0]);conflicting.update(team='GB',opponent='CHI')
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            reconstruct_rows(self.rows+[conflicting],ALTERNATIVE)
        team_conflict=copy.deepcopy(self.source['team_games'][0]);team_conflict['opponent']='MIN'
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            reconstruct_rows(self.source['team_games']+[team_conflict],ALTERNATIVE)
        converted,_=reconstruct_rows(self.source['team_games'],ALTERNATIVE)
        with self.assertRaisesRegex(ValueError,'Changed seven-day'):
            OpportunityHistory(converted,[])
        with self.assertRaisesRegex(ValueError,'mismatched'):
            PolicyOpportunityHistory(converted,[],policy_id=CONTROL)

    def test_query_without_own_outcome_and_arm_policy_guard(self):
        b=AlignedFreshnessBundle(self.rows,self.source,policy_id=ALTERNATIVE)
        result=b.direct_features(self.q,'F2')
        self.assertTrue(np.isfinite(result[~np.isnan(result)]).all())
        with self.assertRaisesRegex(ValueError,'policy mismatch'):
            b.direct_features(self.q,'F0')


if __name__=='__main__':unittest.main()
