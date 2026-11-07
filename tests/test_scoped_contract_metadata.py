import unittest
from tools.build_test_index_v3 import apply_scoped_contract_metadata

class ScopedContractMetadataTest(unittest.TestCase):
    def test_source_binding_and_metrics_preserved(self):
        row=dict(time_panel_id='STALE_W7',history_regime='H-RECENT',n=112,mae=5.2)
        annotation=dict(contract_metadata=dict(kind='SCOPE_METADATA_ONLY_NO_PREDICTION_OR_GRADE_CHANGE',fields={
            'time_panel_id':dict(original='STALE_W7',current='QB_W5_W8'),
            'history_regime':dict(original='H-RECENT',current='UNKNOWN_ARCHIVED_PROCEDURE')}))
        current=apply_scoped_contract_metadata(row,annotation)
        self.assertEqual(current['n'],112);self.assertEqual(current['mae'],5.2)
        self.assertEqual(row['time_panel_id'],'STALE_W7');self.assertEqual(current['time_panel_id'],'QB_W5_W8')
        with self.assertRaises(ValueError):apply_scoped_contract_metadata(dict(row,time_panel_id='OTHER'),annotation)

    def test_metric_or_denominator_change_rejected(self):
        for field in('n','mae','selection_metrics','procedure_id'):
            with self.assertRaises(ValueError):
                apply_scoped_contract_metadata({field:1},dict(contract_metadata=dict(kind='SCOPE_METADATA_ONLY_NO_PREDICTION_OR_GRADE_CHANGE',fields={field:dict(original=1,current='2')})))

if __name__=='__main__':unittest.main()
