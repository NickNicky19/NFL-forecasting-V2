import unittest
from tools.project_served_board_identity_h import project

class ServedIdentityPrivacyTests(unittest.TestCase):
    def test_outcomes_and_forecast_scalars_are_skipped(self):
        raw='{"season":2026,"week":8,"games":[{"id":"g","kickoff":"2026-11-01T18:00:00Z","score":1e9999}],"players":[{"id":"p","game_id":"g","props":[{"key":"rec","actual":999,"proj":1e9999}],"stats":{"rec":999,"id":"hidden"}}]}'
        result,skipped=project(raw)
        self.assertEqual(result,dict(season=2026,week=8,games=[dict(id='g',kickoff='2026-11-01T18:00:00Z')],players=[dict(id='p',game_id='g',props=[dict(key='rec')])]))
        self.assertEqual(skipped,5)

    def test_no_player_game_is_manufactured(self):
        result,_=project('{"season":2026,"week":8,"games":[],"players":[{"id":"p","props":[]}]}')
        self.assertIsNone(result['players'][0]['game_id'])
