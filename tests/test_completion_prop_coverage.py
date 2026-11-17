import copy
import unittest
from tools.check_completion_prop_coverage import check_rows

def fixture():
    rows=[]
    for side,w,l in [('over',1,3),('under',8,0),('Combined',9,3)]:
        n=w+l
        rows.append(dict(record_kind='prop_selection_evaluation',side=side,forecast_rows=n,n=n,
            selection_loss_rate=l/n,settlement_status='UNRESOLVED_CONTRACT',selection_metrics=dict(
            WIN=w,LOSS=l,PUSH=0,status_counts=dict(WIN=w,LOSS=l,PUSH=0),
            denominators=dict(outer_rows=n,decided=n,supported_threshold_outcomes=n,unresolved=0),
            hit_rate=w/n,bookmaker_settlement_status_counts=dict(UNRESOLVED_CONTRACT=n),
            returns=dict(ROI=None,net=None,drawdown=None))))
    return rows

class CompletionPartitionTests(unittest.TestCase):
    def test_unequal_sides_require_underlying_counts(self):
        rows=fixture();self.assertEqual(check_rows(rows)['groups'],1)
        rows[-1]['selection_metrics']['hit_rate']=(.25+1)/2
        with self.assertRaisesRegex(ValueError,'weighted rate'):check_rows(rows)
    def test_missing_side_and_unknown_settlement_return_rejected(self):
        with self.assertRaisesRegex(ValueError,'Missing selected'):check_rows(fixture()[:-1])
        rows=fixture();rows[0]['selection_metrics']['returns']['ROI']=.2
        with self.assertRaisesRegex(ValueError,'Unknown settlement'):check_rows(rows)
