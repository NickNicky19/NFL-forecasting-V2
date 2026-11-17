import unittest
from tools.compare_retained_availability_final_offers import key


class RetainedAvailabilityOfferKeyTests(unittest.TestCase):
    def test_forecast_ordinals_do_not_change_same_offer_identity(self):
        a = dict(game_id='fixture-game', player_id='fixture-player', target='pass_att', line=29.5,
                 source_head='fixture-immutable-source', source_server_clock='2026-01-01T00:00:00Z',
                 decision_time='2026-01-01T00:00:00Z', line_from='fixture', source_row_index=10)
        self.assertEqual(key(a), key(dict(a, source_row_index=11)))
        for changes in (dict(player_id='another'), dict(line=30.5),
                        dict(source_head='different-version'), dict(decision_time='2026-01-01T00:01:00Z')):
            self.assertNotEqual(key(a), key(dict(a, **changes)))
