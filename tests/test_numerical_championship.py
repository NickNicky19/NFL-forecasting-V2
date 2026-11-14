import unittest
from tools.numerical_championship import normalize,proc_id,product_id,choose_representatives,key

class NumericalChampionshipContracts(unittest.TestCase):
    def test_common_alias_preserves_strict_information_identity(self):
        self.assertEqual(proc_id('recipe:common-feature-memory'),'recipe')
        self.assertEqual(proc_id('recipe:strict-current-information'),'recipe:strict-current-information')
        self.assertEqual(product_id('empirical_mean'),'mean')
        self.assertEqual(product_id('lower_median'),'lower_median')

    def test_future_week_filtered_before_outcome_conversion(self):
        self.assertIsNone(normalize({'season':2026,'population':'primary','week':8,'actual':'not eligible'},'laws',2026))
        self.assertIsNone(normalize({'season':2026,'population':'extended','week':1},'laws',2026))

    def test_hgb_missing_procedure_uses_registered_objective(self):
        norm=normalize({'season':2026,'population':'primary','week':7,'target':'pass_yd','history_regime':'H-MULTI','objective':'absolute_error_point'},'hgb',2026)
        self.assertEqual(norm,(('pass_yd','hgb-direct-history-controls-v1:absolute_error_point','H-MULTI','absolute_error_point'),7))

    def test_representation_keeps_distinct_mechanisms(self):
        common=dict(target='rec',ranking_product='display_point',procedure_id='x',history_regime='H-MULTI',product_id='lower_median')
        a=dict(common,mechanism_id='base',ranking_loss=2)
        b=dict(common,mechanism_id='base',ranking_loss=1,history_regime='H-RECENT')
        c=dict(common,mechanism_id='changed_information',ranking_loss=1)
        chosen=choose_representatives([a,b,c])
        self.assertEqual(len(chosen),2)
        self.assertEqual({r['mechanism_id']for r in chosen},{'base','changed_information'})
        self.assertIn(b,chosen)
        self.assertNotEqual(key(a),key(b))

if __name__=='__main__':unittest.main()
