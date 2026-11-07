import unittest
from tools.check_analysis_index_coverage import bound_comparison_histories


class CompletePolicyBindingTest(unittest.TestCase):
    def test_complete_policy_uses_actual_explicit_history_not_mechanism_label(self):
        r=dict(procedure_id='B::ranker',product_id='base_event_selection',
            comparator_procedure_id='B::raw_confidence',comparator_product_id='base_event_selection',
            history_regime='H-MULTI',comparator_history_regime='H-MULTI',
            history_limit='Complete earlier-only policies; common selected mask, not a pure history effect')
        self.assertEqual(bound_comparison_histories(r,'RANKER_MINUS_CONFIDENCE'),('H-MULTI','H-MULTI'))
        missing=dict(r);missing.pop('comparator_procedure_id')
        with self.assertRaises(ValueError):bound_comparison_histories(missing,'RANKER_MINUS_CONFIDENCE')
        for key,value in [('history_limit',' '),('comparator_procedure_id',7),('comparator_product_id',' '),('comparator_history_regime',' ')]:
            invalid=dict(r);invalid[key]=value
            with self.assertRaises(ValueError):bound_comparison_histories(invalid,'RANKER_MINUS_CONFIDENCE')

    def test_encoded_history_mismatch_still_rejects(self):
        r=dict(history_regime='H-CURRENT',comparator_history_regime='H-RECENT')
        self.assertEqual(tuple(bound_comparison_histories(r,'H-CURRENT_MINUS_H-RECENT')),('H-CURRENT','H-RECENT'))
        with self.assertRaises(ValueError):bound_comparison_histories(r,'H-MULTI_MINUS_H-RECENT')
        with self.assertRaises(ValueError):bound_comparison_histories(r,'ALGORITHM_MINUS_H-RECENT')

    def test_descriptive_label_cannot_disguise_same_unbound_procedure(self):
        r=dict(procedure_id='same',product_id='same',comparator_procedure_id='same',
            comparator_product_id='same',history_regime='H-CURRENT',
            comparator_history_regime='H-RECENT',history_limit='arbitrary prose')
        with self.assertRaises(ValueError):bound_comparison_histories(r,'METHOD_MINUS_OTHER')


if __name__=='__main__':unittest.main()
