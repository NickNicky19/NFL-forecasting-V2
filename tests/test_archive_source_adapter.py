import json,unittest
from tools.qualify_w6_archive_sources import metadata_only
from nfl_v2 import full_provider_prop_replay as shared


class ArchiveSourceAdapterTests(unittest.TestCase):
    def test_old_schema_identity_and_threshold_without_point_or_outcome_decode(self):
        source=dict(season=2026,week=6,players=[dict(id='p1',pos='QB',team='A',game_id='g1',props=[dict(key='pass_td',line=1.5,line_from='dk',lean='over',proj=2.1,adj=2.2,actual=1)])])
        projected,skipped=metadata_only(json.dumps(source));player=projected['players'][0];prop=player['props'][0]
        self.assertEqual((player['id'],player['pos'],player['team'],prop['key'],prop['line'],prop['lean']),('p1','QB','A','pass_td',1.5,'over'))
        self.assertFalse({'actual','proj','adj'}&set(prop));self.assertEqual(skipped,3)

    def test_forbidden_stats_container_never_admits_identity_or_threshold_scalars(self):
        projected,_=metadata_only(json.dumps(dict(stats=dict(id='not-a-player-source',line=99),id='player-source')))
        self.assertEqual(projected['stats'],{});self.assertEqual(projected['id'],'player-source')

    def test_missing_point_abstains_only_for_that_rule(self):
        r=dict(side='over',original_side='over',prediction=None,raw_prediction=1.1,line=1.5,target='pass_td',participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL',actual=2)
        grades={v['strategy']:v for v in shared.grade([r])}
        self.assertEqual(grades['original']['statistical_state'],'WIN')
        self.assertEqual(grades[shared.ADJUSTED]['statistical_state'],'ABSTAIN')
        self.assertEqual(grades[shared.RAW]['statistical_state'],'LOSS')
        self.assertEqual(grades['original']['settlement_state'],'UNRESOLVED_CONTRACT')


if __name__=='__main__':unittest.main()
