import unittest

from nfl_v2.scheduled_defense_audit import _aggregate, _change, require_fit_permission
from nfl_v2.qualified_defense import RATE_COLUMNS, RAW_COLUMNS


class ScheduledDefenseAuditTests(unittest.TestCase):
    def test_fit_capacity_block_is_unconditional(self):
        with self.assertRaisesRegex(RuntimeError, 'BLOCKED_DURABLE_RETENTION_CAPACITY'):
            require_fit_permission()

    def test_window_and_feature_changes_are_separate(self):
        f={c:None for c in RATE_COLUMNS}
        diff=_change(f,dict(f),dict(local_game_ids=['a']),
                     dict(local_game_ids=['b'],absent_group_slots=1))
        self.assertTrue(diff['window_changed'])
        self.assertEqual(diff['changed_columns'],[])
        self.assertEqual(_aggregate([diff],RAW_COLUMNS)['any_raw_feature_changed'],0)

    def test_rate_only_change_does_not_count_as_d1_change(self):
        f={c:0. for c in RATE_COLUMNS};g=dict(f,shrunk_allowed_per_opportunity4=1.)
        diff=_change(f,g,dict(local_game_ids=['a']),
                     dict(local_game_ids=['a'],absent_group_slots=0))
        self.assertEqual(_aggregate([diff],RAW_COLUMNS)['any_raw_feature_changed'],0)
        self.assertEqual(_aggregate([diff],RATE_COLUMNS)['any_raw_feature_changed'],1)

    def test_missing_zero_change_is_retained(self):
        f={c:None for c in RATE_COLUMNS};g=dict(f,qualified_allowed_mean4=0.)
        diff=_change(f,g,dict(local_game_ids=[]),dict(local_game_ids=[],absent_group_slots=0))
        self.assertEqual(diff['changed_columns'],['qualified_allowed_mean4'])


if __name__ == '__main__': unittest.main()
