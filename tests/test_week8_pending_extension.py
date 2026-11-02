import unittest
from nfl_v2.full_provider_prop_replay import grade


class PendingExtensionTests(unittest.TestCase):
    def row(self, **changes):
        return dict(side='over', raw_prediction=22., prediction=22., participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL',
                    actual=20, line=19.5, target='pass_cmp', **changes)

    def test_existing_final_default_unchanged(self):
        self.assertEqual(grade([self.row()])[0]['statistical_state'], 'WIN')

    def test_pending_live_credit_cannot_be_a_final_win(self):
        rows = grade([self.row(outcome_state='pending')])
        self.assertTrue(all(r['statistical_state'] == 'PENDING' for r in rows))
        self.assertTrue(all(r['net_return'] is None for r in rows))

    def test_pending_missing_participation_is_pending_and_equality_abstains(self):
        row = self.row(outcome_state='pending')
        row.update(actual=None, participation='UNKNOWN', prediction=19.5)
        rows = grade([row])
        self.assertEqual(rows[0]['statistical_state'], 'PENDING')
        self.assertEqual(rows[1]['statistical_state'], 'ABSTAIN')
