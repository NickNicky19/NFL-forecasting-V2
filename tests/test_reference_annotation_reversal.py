import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tools import register_additive_checkpoint as module

class ReferenceReversalTests(unittest.TestCase):
 def test_reference_error_change_uses_candidate_denominator_and_preserves_v1(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);base=dict(target='pass_att',history_regime='H-MULTI',strict_current_information=False,evaluation_weeks=[5],fallback_view='FULL',n=4,membership_sha256='m',matched_candidate_procedure_id='law')
   rows=[dict(base,reference_id=ref,procedure_id=proc,brier=value)for ref,proc,value in [('candidate','law:known-target-time-v1',.3),('B0','B0:matched-to:law',.25),('B1','B1:matched-to:law',.27)]]
   p=root/'SCORES.json';p.write_text(json.dumps(rows));old=root/'INDEX_REFERENCE_COMPARISON_ANNOTATIONS_V1.json';old.write_text('preserved')
   pairs=[dict(base,procedure_id='law',comparator=ref,metric='brier',candidate_error=.3,comparator_error=error,delta=.3-error,relative_error_change=(.3-error)/error,comparison_id=ref,game_normal95_sensitivity=[-.1,.2],week_interval=None,weekly_paired_sums_counts={'5':dict(n=4,loss_difference_sum=4*(.3-error))})for ref,error in [('B0',.25),('B1',.27)]]
   (root/'PAIRED_REFERENCE_COMPARISONS.json').write_text(json.dumps(pairs))
   with patch.object(module,'ROOT',root):out=module.baseline_comparisons(p)
   a=json.loads(out.read_text())['rows'];c=a[1]['comparison'];self.assertAlmostEqual(c['uncertainty']['relative_error_change'],(.25-.3)/.3);self.assertEqual(c['uncertainty']['comparator'],'law:known-target-time-v1');self.assertEqual(c['uncertainty']['game_normal95_sensitivity'],[-.2,.1]);self.assertEqual(old.read_text(),'preserved')
