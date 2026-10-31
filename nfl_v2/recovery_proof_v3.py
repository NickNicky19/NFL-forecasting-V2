"""Strict restoration-object proof; unrelated software/source digests cannot qualify."""
import hashlib,json,re
from pathlib import Path
from .result_index import safe_artifact

SUCCESS_STATES={
 'FRESH_OWNER_ONLY_RESTORE_ALL_MEMBERS_VERIFIED',
 'RESTORED_AND_ALL_INNER_MEMBERS_VERIFIED',
 'RESTORED_ALL_PARTS_AND_INNER_FILES_VERIFIED',
 'RESTORED_ALL_INNER_FILES_VERIFIED',
 'OWNER_ONLY_UNSHARED_FRESH_DOWNLOAD_INNER_BYTES_VERIFIED',
 'OWNER_ONLY_UNSHARED_FRESH_DOWNLOAD_HASH_VERIFIED',
 'OWNER_ONLY_UNSHARED_ALL_PARTS_FRESH_DOWNLOAD_HASH_AND_INNER_BYTES_VERIFIED',
 'FRESH_PRIVATE_BYTE_RESTORATION_VERIFIED',
 'OWNER_ONLY_UNSHARED_ALL_PARTS_FRESHLY_DOWNLOADED_HASH_AND_INNER_BYTES_VERIFIED',
 'FULL_FORECAST_PACKET_FRESH_PRIVATE_RESTORE_VERIFIED',
 'UPLOADED_OWNER_ONLY_FRESH_DOWNLOAD_HASH_VERIFIED',
 'FRESH_PRIVATE_RESTORE_ALL_PARTS_AND_INNER_FILES_VERIFIED',
 'OWNER_ONLY_UNSHARED_FRESH_DOWNLOAD_BYTE_EQUAL',
}
RESTORED_DIGEST_FIELDS=('archive_sha256','sha256','compressed_sha256')
def load_allowlist(public_root,proof):
 root=Path(public_root).resolve();value=json.loads(Path(proof).read_text());out={}
 if value.get('schema')!='v2-positive-restoration-proof-allowlist-v1':raise ValueError('affirmative proof allowlist required')
 for row in value['entries']:
  path=root/safe_artifact(row['proof_receipt']);body=path.read_bytes()
  if hashlib.sha256(body).hexdigest()!=row['proof_receipt_sha256']:raise ValueError('restoration proof receipt changed')
  receipt=json.loads(body);digest=row['sha256'];state=receipt.get('status',receipt.get('state'))
  if not re.fullmatch('[a-f0-9]{64}',digest):raise ValueError('invalid proof digest')
  success=state in SUCCESS_STATES or(state is None and receipt.get('fresh_download_byte_equal')is True)
  if not success or not any(receipt.get(k)==digest for k in RESTORED_DIGEST_FIELDS):raise ValueError('matching restoration object not affirmatively verified')
  if receipt.get('shared')is True or receipt.get('unshared')is False:raise ValueError('restoration object is not private')
  if digest in out and out[digest]!=row['artifact_id']:raise ValueError('ambiguous restoration proof identity')
  out[digest]=row['artifact_id']
 return out
