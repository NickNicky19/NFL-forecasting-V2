import unittest
from tools.build_five_week_B_contribution import explicit_scored_week,identity,primary_fullsystem

class FiveWeekQualificationTests(unittest.TestCase):
 def test_declared_training_or_aggregate_weeks_are_not_scored_week_proof(self):
  r=dict(kind='prop_selection_evaluation',season=2026,week='ALL',weeks=[1,2,3,4,5,6,7],n=100,selection_metrics=dict(WIN=60,LOSS=40))
  self.assertEqual(explicit_scored_week(r),(None,'NO_EXPLICIT_SINGLE_SCORED_WEEK'))
 def test_zero_selection_unresolved_week_not_counted(self):
  r=dict(kind='prop_selection_evaluation',season=2026,week=3,n=0,selection_metrics=dict(WIN=0,LOSS=0,PUSH=0))
  self.assertEqual(explicit_scored_week(r),((2026,3),'NO_RESOLVED_SCORED_OUTCOME'));r['n']=1
  self.assertEqual(explicit_scored_week(r)[1],'EXPLICIT_WEEK_WITH_RESOLVED_SCORED_SUPPORT')
 def test_point_probability_and_policy_identities_cannot_borrow_weeks(self):
  a=dict(procedure_id='same-v1',category='rec',product_id='mean',strategy='P1',history_regime='H-MULTI')
  b=dict(a,product_id='exact_line_probability',strategy='P2')
  self.assertNotEqual(identity(a),identity(b));self.assertNotEqual(identity(a),identity(dict(a,strategy='TOP6',K=6)))
 def test_fullsystem_case_spelling_does_not_discard_completed_week_evidence(self):
  for value in [None,'ALL','all','full_system','FULL_SYSTEM']:
   self.assertTrue(primary_fullsystem(dict(fallback_view=value)))
  self.assertFalse(primary_fullsystem(dict(fallback_view='own_learned_only')))
