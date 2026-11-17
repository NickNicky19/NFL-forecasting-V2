import copy
import unittest
from types import SimpleNamespace

from nfl_v2.qb_ftn_information import QBFTNInformation, feature_order, feature_values, FLAGS

DAY=86400


def game(index,attempts=10,player='p',position='QB'):
    return dict(game_id='g'+str(index),player_id=player,season=2025,week=index+1,
                team='AAA',opponent='BBB',kickoff=index*8*DAY,available=(index*8+7)*DAY,
                attempts=attempts,official_completions=5,position=position,
                physical_participation=True,target_parity=True)


def quality(row,positive=0):
    return dict(**{k:row[k]for k in('game_id','player_id','season','week','team','opponent','kickoff','available')},
                eligible_throws=row['attempts'],charted_throws=row['attempts'],
                flags={name:dict(known=row['attempts'],positive=positive,unknown=0)for name in FLAGS},
                date_pulled_min='2030-01-01',date_pulled_max='2030-01-01')


class QBFTNInformationTests(unittest.TestCase):
    def test_future_target_and_input_order_invariance(self):
        rows=[game(0),game(1)];source=[quality(r,2)for r in rows];q=dict(player_id='p',kickoff=20*DAY)
        base=QBFTNInformation(SimpleNamespace(all_rows=rows),source).describe(q)
        future=game(4);future['official_completions']=999
        changed=QBFTNInformation(SimpleNamespace(all_rows=list(reversed(rows+[future]))),list(reversed(source+[quality(future,9)]))).describe(dict(q,official_completions=999,attempts=999))
        self.assertEqual(base,changed)
        self.assertEqual(feature_order('B1'),[])
        self.assertEqual(len(feature_values(base,'B2')),2)

    def test_last_eight_appearances_before_source_join(self):
        rows=[game(0,30)]+[game(i,0)for i in range(1,9)]
        d=QBFTNInformation(SimpleNamespace(all_rows=rows),[quality(rows[0],3)]).describe(dict(player_id='p',kickoff=100*DAY))
        self.assertEqual(d['trace']['own_window_game_ids'],['g'+str(i)for i in range(1,9)])
        self.assertEqual(d['flags'][FLAGS[0]]['known'],0)
        self.assertEqual(d['flags'][FLAGS[0]]['prior_known'],30)
        self.assertIsNone(d['flags'][FLAGS[0]]['raw'])

    def test_missing_annotation_does_not_become_false(self):
        row=game(0);known=quality(row);unknown=quality(row)
        unknown['flags'][FLAGS[0]]=dict(known=0,positive=0,unknown=10)
        q=dict(player_id='p',kickoff=9*DAY)
        a=QBFTNInformation(SimpleNamespace(all_rows=[row]),[known]).describe(q)
        b=QBFTNInformation(SimpleNamespace(all_rows=[row]),[unknown]).describe(q)
        self.assertEqual(a['flags'][FLAGS[0]]['raw'],0.)
        self.assertIsNone(b['flags'][FLAGS[0]]['raw'])
        self.assertTrue(a['complete_required_charting']);self.assertFalse(b['complete_required_charting'])
        with self.assertRaises(ValueError):feature_values(b,'B2')

    def test_global_prior_excludes_non_qb_and_future_labels(self):
        row=game(0);other=game(0,1000,'r','RB');q=dict(player_id='p',kickoff=9*DAY)
        a=QBFTNInformation(SimpleNamespace(all_rows=[row]),[quality(row,2)]).describe(q)
        b=QBFTNInformation(SimpleNamespace(all_rows=[row,other]),[quality(row,2),quality(other,1000)]).describe(q)
        self.assertEqual(a,b)

    def test_explicit_unknown_clock_not_reconstructed(self):
        row=game(0);a=quality(row);a['available']=None
        q=dict(player_id='p',kickoff=9*DAY)
        d=QBFTNInformation(SimpleNamespace(all_rows=[row]),[a]).describe(q)
        self.assertEqual(d['flags'][FLAGS[0]]['known'],0)
        self.assertFalse(d['complete_required_charting'])
        del a['available']
        reconstructed=QBFTNInformation(SimpleNamespace(all_rows=[row]),[a]).describe(q)
        self.assertEqual(reconstructed['flags'][FLAGS[0]]['known'],10)

    def test_strict_boundary_and_date_pulled_is_not_availability(self):
        row=game(0);h=QBFTNInformation(SimpleNamespace(all_rows=[row]),[quality(row,2)])
        a=h.describe(dict(player_id='p',kickoff=7*DAY))
        b=h.describe(dict(player_id='p',kickoff=7*DAY+1))
        self.assertEqual(a['flags'][FLAGS[0]]['known'],0)
        self.assertEqual(b['flags'][FLAGS[0]]['known'],10)
        self.assertEqual(b['flags'][FLAGS[0]]['positive'],2)

    def test_denominator_and_duplicate_contracts(self):
        row=game(0);a=quality(row);a['eligible_throws']=11
        with self.assertRaises(ValueError):QBFTNInformation(SimpleNamespace(all_rows=[row]),[a])
        with self.assertRaises(ValueError):QBFTNInformation(SimpleNamespace(all_rows=[row]),[quality(row),quality(row)])


if __name__=='__main__':unittest.main()
