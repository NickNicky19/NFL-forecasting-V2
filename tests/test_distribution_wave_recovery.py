"""Focused blocked-query and recovery counter fixtures; no NFL fits."""
import unittest
import numpy as np
from nfl_v2.distribution_wave_v2 import predict_admitted
class Spy:
 def __init__(self):self.calls=[]
 def predict(self,x,positions,priors):
  self.calls.append((len(x),positions));assert all(p in priors for p in positions)
  return [('law',{}) for p in positions]
class RecoveryTests(unittest.TestCase):
 def test_six_original_shape_missing_positions_abstain_before_lookup(self):
  q=[{'position':None,'blocked_reason':'MISSING_BOARD_CONTEXT'} for _ in range(6)]+[{'position':'RB','blocked_reason':None}]
  model=Spy();out=predict_admitted(model,np.zeros((7,20)),q,{'RB':'prior'})
  self.assertEqual(model.calls,[(1,['RB'])]);self.assertEqual(out[:6],[(None,None)]*6);self.assertEqual(out[-1],('law',{}))
 def test_all_blocked_no_estimator_call_and_unknown_position(self):
  q=[{'position':None,'blocked_reason':None},{'position':'WR','blocked_reason':'UNQUALIFIED_ID'}];m=Spy();self.assertEqual(predict_admitted(m,np.zeros((2,20)),q,{'WR':'prior'}),[(None,None)]*2);self.assertEqual(m.calls,[])
 def test_absent_model_uses_no_estimator_or_role_lookup(self):
  self.assertEqual(predict_admitted(None,np.zeros((1,20)),[{'position':'RB','blocked_reason':None}],{}),[(None,None)])
if __name__=='__main__':unittest.main()
