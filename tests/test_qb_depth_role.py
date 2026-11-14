import copy

import unittest

from nfl_v2.qb_depth_role import DepthRoleHistory, feature_names, feature_values


def row(team='A', player='p', dt=10, rank=1):
    return dict(team=team, player_id=player, dt=dt, rank=rank)


def query(team='A', player='p', kickoff=40):
    return dict(team=team, player_id=player, kickoff=kickoff)


class DepthRoleHistoryTests(unittest.TestCase):
    def test_latest_empty_qb_team_snapshot_is_preserved(self):
        history = DepthRoleHistory([row(dt=10)],
                                   team_snapshots=[dict(team='A', dt=30)])
        d = history.describe(query())
        assert d['clocks']['current_snapshot_dt'] == 30
        assert d['current_status'] == 'ABSENT_LATEST_TEAM_SNAPSHOT'
        assert d['values']['current_depth_rank'] is None

    def test_latest_team_snapshot_does_not_resurrect_absent_player(self):
        history = DepthRoleHistory([row(dt=10), row(player='other', dt=30)])
        d = history.describe(query())
        assert d['current_status'] == 'ABSENT_LATEST_TEAM_SNAPSHOT'
        assert d['values']['current_depth_rank'] is None
        assert d['clocks']['current_snapshot_dt'] == 30
        assert d['support']['current_snapshot_available']
        assert not d['support']['current_player_in_snapshot']


    def test_strict_boundary_and_same_team_rank_change(self):
        history = DepthRoleHistory([row(dt=10, rank=3), row(dt=20, rank=2),
                                    row(dt=40, rank=1)])
        d = history.describe(query(), previous=query(kickoff=20))
        assert d['values']['current_depth_rank'] == 2
        assert d['values']['rank_change_since_eligible_own_game'] == -1
        assert d['clocks']['previous_snapshot_dt'] == 10
        assert history.describe(query(kickoff=10))['values']['current_depth_rank'] is None
        assert history.describe(query(), previous=query(team='B', kickoff=20))[
            'values']['rank_change_since_eligible_own_game'] is None


    def test_future_rows_and_target_outcomes_cannot_change_features(self):
        rows = [row(dt=10, rank=2), row(dt=30, rank=1)]
        q = query()
        before = DepthRoleHistory(rows).describe(q, previous=query(kickoff=20))
        future = rows + [row(dt=41, rank=3)]
        mutated = copy.deepcopy(q)
        mutated.update(attempts=1000, completions=999, started=True, participation=False)
        after = DepthRoleHistory(future).describe(mutated, previous=query(kickoff=20))
        assert before == after


    def test_unknown_clocks_and_rank_never_become_observed_zero(self):
        history = DepthRoleHistory([row(dt=None, rank=1), row(dt=float('nan')),
                                    row(dt=float('inf')), row(dt=30, rank=None)])
        d = history.describe(query())
        assert d['excluded_unknown_clock_rows'] == 3
        assert d['current_status'] == 'UNKNOWN_REPORTED_RANK'
        assert d['missing_flags']['current_depth_rank']
        x = dict(zip(feature_names('S2'), feature_values(d, 'S2')))
        assert x['current_depth_rank'] == 0
        assert x['current_depth_rank_missing'] == 1
        assert x['current_player_in_snapshot'] == 1
        assert feature_values(d, 'S0') == []


    def test_duplicate_identity_version_is_deterministic_or_rejected(self):
        history = DepthRoleHistory([row(), row()])
        assert history.identical_duplicate_rows == 1
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            DepthRoleHistory([row(), row(rank=2)])


    def test_invalid_rank_not_accepted(self):
        for invalid in [0, -1, 1.5, float('nan'), float('inf'), True]:
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, 'finite positive integer'):
                    DepthRoleHistory([row(rank=invalid)])


    def test_rank_one_is_source_label_without_participation_or_filtering(self):
        history = DepthRoleHistory([row(rank=1), row(player='backup', rank=2)])
        first = history.describe(query())
        backup = history.describe(query(player='backup'))
        assert first['values']['current_depth_rank'] == 1
        assert backup['values']['current_depth_rank'] == 2
        assert 'NOT_STARTER_HEALTH_OR_PARTICIPATION_PROBABILITY' in first['semantics']
        assert not any('probability' in key for key in first['values'])


    def test_change_requires_same_player_and_genuine_prior_origin(self):
        history = DepthRoleHistory([row(dt=10, rank=2), row(dt=30, rank=1)])
        for prior in [query(player='other', kickoff=20), query(kickoff=40),
                      query(kickoff=50), query(kickoff=float('nan'))]:
            assert history.describe(query(), previous=prior)['values'][
                'rank_change_since_eligible_own_game'] is None


if __name__ == '__main__':
    unittest.main()
