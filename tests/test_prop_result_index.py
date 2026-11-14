import unittest
from nfl_v2.result_index import evaluation,validate_index


class PropIndexTests(unittest.TestCase):
    def row(self):
        return dict(record_id='direction-fixture',record_kind='prop_selection_evaluation',
            procedure_id='recorded-lean',target='rec',product_id='recorded_threshold_direction',
            evaluation_panel_id='fictional-source-panel',population='recorded-selections',
            history_regime='ORIGINAL_UNKNOWN',season=2026,week=7,n=2,forecast_rows=3,
            selection_metrics=dict(wins=1,losses=1,unknown_participation=1),selection_loss_rate=.5,
            settlement_verified=False)

    def test_selection_counts_do_not_become_numeric_MAE(self):
        r=evaluation(self.row(),'reports/fictional/SCORES.json');validate_index([r])
        self.assertEqual(r['primary_metric'],'selection_loss_rate')
        self.assertEqual(r['primary_error'],.5);self.assertIsNone(r['metrics']['mae'])
        self.assertEqual(r['precision_metrics']['decided_pick_hit_rate']['numerator'],1)
        self.assertEqual(r['precision_metrics']['decided_pick_hit_rate']['denominator'],2)

    def test_invalid_counts_and_empty_results(self):
        row=self.row();row['n']=3
        with self.assertRaises(ValueError):evaluation(row,'reports/fictional/SCORES.json')
        row=self.row();row.update(n=0,selection_metrics=dict(wins=0,losses=0),selection_loss_rate=None)
        r=evaluation(row,'reports/fictional/SCORES.json');validate_index([r])
        self.assertIsNone(r['primary_error'])
        self.assertIsNone(r['precision_metrics']['decided_pick_hit_rate']['numerator'])

    def test_side_selection_retains_parent_eligible_pool(self):
        row=self.row();row['selection_metrics'].update(selection_pool_count=9,
            status_counts={'WIN':1,'LOSS':1,'UNKNOWN_PARTICIPATION':1},abstentions_outside_selected_partition=0)
        r=evaluation(row,'reports/fictional/SCORES.json')
        self.assertEqual(r['selection_metrics']['eligible_opportunities'],9)
        self.assertEqual(r['selection_metrics']['selected_opportunities'],3)
        self.assertEqual(r['selection_metrics']['selection_coverage'],1/3)
