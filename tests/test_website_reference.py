import unittest

from tools.replay_website_reference import select_packets


class WebsiteReferenceTests(unittest.TestCase):
    def packet(self,capture):
        return dict(captured_at=capture,forecast_generated_at=capture,
                    rows=[dict(season=2026,week=7,game_id='fixture',kickoff='2026-10-25T17:00:00Z',player_id='fictional',category='rec')])

    def test_selection_uses_capture_and_deadline_without_outcome(self):
        from tools.replay_website_reference import epoch
        games={'fixture':{'kickoff':epoch('2026-10-25T17:00:00Z')}}
        packets=[('early',self.packet('2026-10-25T14:00:00Z')),('later',self.packet('2026-10-25T15:30:00Z')),
                 ('late',self.packet('2026-10-25T15:31:00Z'))]
        self.assertEqual(select_packets(packets,games)['fixture'][1],'later')

    def test_wrong_week_and_duplicate_capture_are_rejected(self):
        from tools.replay_website_reference import epoch
        games={'fixture':{'kickoff':epoch('2026-10-25T17:00:00Z')}}
        packet=self.packet('2026-10-25T15:30:00Z');packet['rows'][0]['week']=8
        with self.assertRaises(ValueError): select_packets([('wrong',packet)],games)
        packet=self.packet('2026-10-25T15:30:00Z');packet['rows'].append(dict(packet['rows'][0]))
        with self.assertRaises(ValueError): select_packets([('duplicate',packet)],games)
