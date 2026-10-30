import json
import unittest
from nfl_v2 import prop_evidence_metadata_v2 as m
class MetadataIsolationFixtures(unittest.TestCase):
 def test_forbidden_nested_allowed_names_stay_undecoded(self):
  data,skipped=m.project_metadata('{"actual":{"over":NaN},"statistics":{"line":Infinity},"line":3.5}')
  self.assertEqual(data,{"actual":{},"statistics":{},"line":3.5});self.assertEqual(skipped,2)
 def test_unknown_scalar_is_not_json_decoded(self):
  data,_=m.project_metadata('{"actual":undefined,"category":"rec","lean":"over"}')
  self.assertEqual(data,{"category":"rec","lean":"over"})
 def test_object_span_iterator_does_not_decode_target_numbers(self):
  self.assertEqual(len(list(m.object_spans_in_array('{"rows":[{"actual":NaN},{"actual":Infinity}]}','rows'))),2)
if __name__=='__main__':unittest.main()
