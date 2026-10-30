import unittest
from tools.build_current_valid_view_v2 import recipe,admissible_lineage

class CurrentLineageTests(unittest.TestCase):
 def test_chart_empirical_alias_is_same_control_not_new_family(self):
  self.assertEqual(recipe({'procedure_id':'v2-qualified-partial-chart-direct-wave-v1:empirical'}),recipe({'procedure_id':'empirical-player-history-control-v1'}))
 def test_only_qualified_chart_correction_lineage_is_admitted(self):
  r=dict(evidence='REPRODUCED_FROM_DATA',category='nick-chart-ppr-v1',source_artifact='reports/continuation-20261030/chart-grid-precision-correction-v1/SCORES.json',source_aggregate_fields={'supersedes_score_artifact':'reports/continuation-20261030/chart-wave-v1/SCORES.json'})
  self.assertTrue(admissible_lineage(r));self.assertFalse(admissible_lineage(dict(r,source_artifact='provider.json')));self.assertFalse(admissible_lineage(dict(r,category='pass_yd')))
 def test_distinct_information_procedures_share_family(self):
  a=recipe({'procedure_id':'v2-qualified-position-defense-information-wave-v1:D1:common-feature-memory'});b=recipe({'procedure_id':'v2-qualified-position-defense-information-wave-v1:D2:common-feature-memory'});self.assertEqual(a[0],b[0]);self.assertNotEqual(a[1],b[1])
