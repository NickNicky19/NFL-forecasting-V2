import unittest
from nfl_v2 import prop_side_projection as p

class SideProjectionTests(unittest.TestCase):
    def row(self,i,**kw):
        r=dict(source_row_index=i,selected_side='over',prediction=3.,line=1.,game_id='fiction-game',player_id='p'+str(i),target='rec',statistical_state='UNKNOWN_PARTICIPATION',top_over=False,top_under=False,position='WR');r.update(kw);return r
    def test_ranking_keeps_unknown_outcomes_and_does_not_use_wins(self):
        rows=[self.row(1,prediction=10.),self.row(2,prediction=4.,statistical_state='WIN')]
        got,n=p.select_k(rows,'Combined',1);self.assertEqual(got[0]['source_row_index'],1);self.assertEqual(n,2)
    def test_actual_side_pool_differs_from_original_side(self):
        rows=[self.row(1,original_side='under'),self.row(2,selected_side='under',original_side='over')]
        got,n=p.select_k(rows,'over',20);self.assertEqual([r['source_row_index']for r in got],[1]);self.assertEqual(n,1)
    def test_empty_side_is_empty_not_padded(self):
        got,n=p.select_k([self.row(1)],'under',20);self.assertEqual(got,[]);self.assertEqual(n,0)
    def test_ties_use_canonical_id_not_outcome(self):
        a=self.row(1,player_id='a',statistical_state='LOSS');b=self.row(2,player_id='b',statistical_state='WIN');got,_=p.select_k([b,a],'Combined',1);self.assertEqual(got[0]['player_id'],'a')
    def test_point_precision_not_rounded_again(self):
        got,_=p.select_k([self.row(1,prediction=3.),self.row(2,prediction=3.000000000001)],'Combined',1);self.assertEqual(got[0]['source_row_index'],2)
    def test_abstention_outside_selected_partition(self):
        got,n=p.select_k([self.row(1,selected_side=None)],'Combined',20);self.assertEqual(got,[]);self.assertEqual(n,0)
    def test_unsupported_empty_target_has_null_error(self):
        r=p.summarize([],source_pool=[],universe_n=None,strategy='original',target='anytime_td',side='Combined',cohort='ALL',time_panel=p.PERIODS[0]);self.assertEqual(r['n'],0);self.assertIsNone(r['selection_loss_rate']);self.assertEqual(r['null_reason'],'UNSUPPORTED_SOURCE_TARGET_CONTRACT')
    def test_projection_requires_root_release(self):
        with self.assertRaises(ValueError):p.run(output=None,private_output=None)

if __name__=='__main__':unittest.main()
