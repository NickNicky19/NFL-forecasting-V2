import hashlib,json,tempfile,unittest
from pathlib import Path
from nfl_v2.recovery_proof import load_allowlist

class RecoveryProofTests(unittest.TestCase):
 def setup_case(self,root,receipt):
  b=json.dumps(receipt).encode();(root/'receipt.json').write_bytes(b);row=dict(artifact_id='V2-FICTIONAL',sha256='a'*64,proof_receipt='receipt.json',proof_receipt_sha256=hashlib.sha256(b).hexdigest());p=root/'allow.json';p.write_text(json.dumps(dict(schema='v2-positive-restoration-proof-allowlist-v1',entries=[row])));return p,row
 def test_no_locator_can_create_restoration_without_positive_proof(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);p,row=self.setup_case(root,dict(state='LOCAL_ONLY',sha256='a'*64))
   with self.assertRaisesRegex(ValueError,'positive matching'):load_allowlist(root,p)
 def test_accepted_matching_fresh_receipt_is_admitted(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);p,row=self.setup_case(root,dict(status='FRESH_PRIVATE_RESTORE_VERIFIED',archive_sha256='a'*64));self.assertEqual(load_allowlist(root,p),{'a'*64:'V2-FICTIONAL'})
 def test_tampered_receipt_and_wrong_digest_are_rejected(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);p,row=self.setup_case(root,dict(fresh_download_byte_equal=True,sha256='b'*64))
   with self.assertRaisesRegex(ValueError,'positive matching'):load_allowlist(root,p)
   (root/'receipt.json').write_text('{}')
   with self.assertRaisesRegex(ValueError,'receipt changed'):load_allowlist(root,p)
 def test_proof_cannot_read_outside_public_root(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);p,row=self.setup_case(root,dict(status='PASS',sha256='a'*64));row['proof_receipt']='../private.json';p.write_text(json.dumps(dict(schema='v2-positive-restoration-proof-allowlist-v1',entries=[row])))
   with self.assertRaisesRegex(ValueError,'repository-relative'):load_allowlist(root,p)
 def test_fresh_download_byte_equal_receipt_is_positive(self):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);p,row=self.setup_case(root,dict(state='OWNER_ONLY_UNSHARED_FRESH_DOWNLOAD_BYTE_EQUAL',sha256='a'*64));self.assertEqual(len(load_allowlist(root,p)),1)
