import gzip,json,tempfile,unittest
from pathlib import Path
from tools.abc_b_c_bound_replay import gzsave

class PrivateWriteBound(unittest.TestCase):
 def test_rejected_payload_creates_no_file_and_preserves_existing_evidence(self):
  with tempfile.TemporaryDirectory()as directory:
   target=Path(directory)/'new.gz';old=Path(directory)/'retained.gz';old.write_bytes(b'original evidence')
   with self.assertRaisesRegex(ValueError,'BEFORE_WRITE'):gzsave(target,{'data':'x'*1000},max_bytes=1)
   self.assertFalse(target.exists())
   with self.assertRaisesRegex(ValueError,'BEFORE_WRITE'):gzsave(old,{'data':'x'*1000},max_bytes=1)
   self.assertEqual(old.read_bytes(),b'original evidence')
 def test_exact_limit_roundtrips_without_overwriting(self):
  value={'data':[1,2,3]};size=len(gzip.compress(json.dumps(value,separators=(',',':'),allow_nan=False).encode(),mtime=0))
  with tempfile.TemporaryDirectory()as directory:
   target=Path(directory)/'valid.gz';gzsave(target,value,max_bytes=size)
   self.assertEqual(target.stat().st_size,size);self.assertEqual(json.loads(gzip.decompress(target.read_bytes())),value)
   with self.assertRaises(FileExistsError):gzsave(target,value,max_bytes=size)
