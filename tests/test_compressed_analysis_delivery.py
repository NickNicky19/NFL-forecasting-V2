import gzip
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools import check_analysis_index_coverage as validator


class CompressedAnalysisDeliveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.raw=b'[{"n":111,"delta":-0.018018018018018} ]\n'
        self.body=gzip.compress(self.raw,mtime=0);(self.root/'rows.json.gz').write_bytes(self.body)
        self.binding=dict(path='rows.json.gz',sha256=hashlib.sha256(self.body).hexdigest(),compression='gzip',
            uncompressed_bytes=len(self.raw),uncompressed_sha256=hashlib.sha256(self.raw).hexdigest())

    def test_exact_roundtrip_and_plain_compatibility(self):
        with patch.object(validator,'ROOT',self.root):
            self.assertEqual(validator.read_bound(self.binding),self.raw)
            (self.root/'plain.json').write_bytes(self.raw)
            self.assertEqual(validator.read_bound(dict(path='plain.json',sha256=hashlib.sha256(self.raw).hexdigest())),self.raw)

    def test_bad_compressed_or_uncompressed_binding_rejects(self):
        with patch.object(validator,'ROOT',self.root):
            for key,value in [('sha256','wrong'),('uncompressed_sha256','wrong'),('uncompressed_bytes',0),('compression','zip')]:
                bad=dict(self.binding);bad[key]=value
                with self.assertRaises(ValueError):validator.read_bound(bad)
            bad=dict(self.binding);bad.pop('uncompressed_sha256')
            with self.assertRaises(ValueError):validator.read_bound(bad)


if __name__=='__main__':unittest.main()
