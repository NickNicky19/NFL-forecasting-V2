import unittest
import numpy as np
from nfl_v2 import availability_wave as wave
from nfl_v2 import hgb_control as src

class AvailabilityTests(unittest.TestCase):
    def row(self,week,kick,available,value=7):
        return dict(season=2026,week=week,kickoff=kick,available=available,player_id='fictional',game_id=str(week),position='QB',values={'pass_yd':value})
    def test_fresh_only_current_week7_and_does_not_mutate(self):
        old=[self.row(6,10,80),self.row(7,20,90)]
        new=wave.fresh_rows(old,40,50)
        self.assertEqual([r['available'] for r in new],[80,40]);self.assertEqual(old[1]['available'],90)
    def test_unknown_future_source_rejected(self):
        with self.assertRaises(ValueError):wave.fresh_rows([self.row(8,20,90)],40,50)
        with self.assertRaises(ValueError):wave.fresh_rows([self.row(7,45,90)],40,50)
    def test_exact_cutoff_is_not_available(self):
        row=self.row(7,20,90);fresh=wave.fresh_rows([row],40,50)
        self.assertEqual(src.FeatureHistory(fresh).get('fictional','QB','pass_yd',40)[0][3],0)
        self.assertEqual(src.FeatureHistory(fresh).get('fictional','QB','pass_yd',41)[0][3],1)
    def test_training_features_keep_seven_day_clocks(self):
        rows=[self.row(6,10,80),self.row(7,20,90)]
        self.assertEqual(src.FeatureHistory(rows).get('fictional','QB','pass_yd',20)[0][3],0)
        self.assertEqual(src.FeatureHistory(wave.fresh_rows(rows,40,100)).get('fictional','QB','pass_yd',100)[0][3],2)
    def test_none_position_blocked_before_hgb(self):
        class Model:
            def predict(self,x):
                self.n=len(x);return np.ones(len(x))*9
        model=Model();q=[dict(position=None,blocked_reason='NO_ID'),dict(position='QB',blocked_reason=None)]
        self.assertEqual(wave.infer_hgb(model,np.zeros((2,20)),q,'pass_yd'),[None,9.]);self.assertEqual(model.n,1)
    def test_deadline_exact_equality_closed(self):
        self.assertFalse(wave.open_query(dict(owner_input_cutoff_utc='2026-10-30T00:00:00Z'),1793318400.))

if __name__=='__main__':unittest.main()
