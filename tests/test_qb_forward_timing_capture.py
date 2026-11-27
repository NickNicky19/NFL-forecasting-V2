import unittest

from tools.capture_qb_forward_timing import event_reason, feature_query, http_expiry


class ForwardTimingCapture(unittest.TestCase):
    def test_future_event_time_is_not_feature_cutoff(self):
        q = dict(kickoff=2000., official_completions=999)
        self.assertEqual(feature_query(q, 1000.)['kickoff'], 1000.)
        self.assertEqual(q['kickoff'], 2000.)
        with self.assertRaises(ValueError):
            feature_query(q, 2001.)

    def test_unknown_or_stale_http_clock_is_not_fresh(self):
        for age, date in [(None, None), ('nan', None), ('1801', None),
                          ('0', 'Thu, 01 Jan 1970 00:00:00 GMT')]:
            with self.assertRaises(ValueError):
                http_expiry(2000., age, date)
        self.assertEqual(http_expiry(2000., '600', None), 3200.)

    def test_cached_response_expiry_is_not_reset_by_local_receipt(self):
        q = dict(game_id='2026_10_WAS_NYG', native_event_id='401873052',
                 season=2026, week=10, kickoff=10000., team='WAS', opponent='NYG')
        event = dict(q, state='pre', status_name='STATUS_SCHEDULED', completed=False,
            season_type=2, home_team='NYG', away_team='WAS', competition_id='401873052',
            observed_at=2000., retained_at=2001., HTTP_Age='600', HTTP_Date=None,
            expires_at=3200.)
        self.assertIsNone(event_reason(event, q, 2100.))
        self.assertIsNotNone(event_reason(event, q, 3201.))
        self.assertIsNotNone(event_reason(dict(event, expires_at=3800.), q, 2100.))
        self.assertIsNotNone(event_reason(dict(event, completed=True), q, 2100.))
        self.assertIsNotNone(event_reason(dict(event, completed=0), q, 2100.))
        self.assertIsNotNone(event_reason(dict(event, home_team='DAL'), q, 2100.))


if __name__ == '__main__':
    unittest.main()
