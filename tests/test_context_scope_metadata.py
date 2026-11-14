import hashlib,json,tempfile,unittest
from pathlib import Path
from nfl_v2.context_scope_metadata import qualified_rows

class ContextScopeMetadataTest(unittest.TestCase):
    def test_outside_bucket_is_not_unavailable_forecast(self):
        with tempfile.TemporaryDirectory()as tmp:
            p=Path(tmp)/'scores.json';row=dict(record_id='r',forecast_rows=2,n=2,mae=4.5,technical_unavailable=110)
            body=json.dumps([row]).encode();p.write_bytes(body)
            correction=dict(source_row_index=0,record_id='r',original_technical_unavailable=110,full_system_query_rows=112,reported_scope_rows=2,outside_reported_scope=110)
            overlay=dict(sources=[dict(source_sha256=hashlib.sha256(body).hexdigest(),rows=[correction])])
            current=list(qualified_rows(p,overlay))[0]
            self.assertEqual(current['technical_unavailable'],0);self.assertEqual(current['outside_reported_scope'],110)
            self.assertEqual(current['n'],2);self.assertEqual(current['mae'],4.5);self.assertEqual(json.loads(p.read_bytes()),[row])
            correction['reported_scope_rows']=3
            with self.assertRaises(ValueError):list(qualified_rows(p,overlay))
if __name__=='__main__':unittest.main()
