import hashlib,json,tempfile,unittest
from pathlib import Path
from nfl_v2.recovery_proof_v3 import load_allowlist
from tests import test_recovery_proof as proof_fixtures

class StrictRecoveryProofTests(unittest.TestCase):
 def check(self,body,expected):
  with tempfile.TemporaryDirectory()as d:
   root=Path(d);p,row=proof_fixtures.RecoveryProofTests().setup_case(root,body)
   if expected:self.assertEqual(load_allowlist(root,p),{'a'*64:'V2-FICTIONAL'})
   else:
    with self.assertRaises(ValueError):load_allowlist(root,p)
 def test_unrelated_nested_software_pass_does_not_restore_a_file(self):self.check(dict(state='LOCAL_ONLY',sha256='a'*64,software={'status':'PASS'}),False)
 def test_source_prediction_digest_is_not_the_restored_archive(self):self.check(dict(status='FRESH_PRIVATE_RESTORE_ALL_PARTS_AND_INNER_FILES_VERIFIED',archive_sha256='b'*64,source_prediction_sha256='a'*64),False)
 def test_specific_archive_and_boolean_legacy_receipts(self):
  self.check(dict(status='FRESH_PRIVATE_RESTORE_ALL_PARTS_AND_INNER_FILES_VERIFIED',archive_sha256='a'*64),True)
  self.check(dict(fresh_download_byte_equal=True,sha256='a'*64),True)
 def test_generic_verified_and_contradictory_status_are_rejected(self):
  self.check(dict(status='VERIFIED',sha256='a'*64),False)
  self.check(dict(state='LOCAL_ONLY',fresh_download_byte_equal=True,sha256='a'*64),False)
