"""Affirmative source-bound restoration proof; locator presence is insufficient."""
import hashlib,json,re
from pathlib import Path
from .result_index import safe_artifact

def walk(value):
 yield value
 if isinstance(value,dict):
  for item in value.values():yield from walk(item)
 elif isinstance(value,list):
  for item in value:yield from walk(item)

def positive_receipt(value):
 for item in walk(value):
  if not isinstance(item,dict):continue
  if item.get('fresh_download_byte_equal')is True:return True
  for key in('status','state'):
   state=str(item.get(key,'')).upper()
   if any(x in state for x in('FAIL','PENDING','BLOCKED','PARTIAL','UNVERIFIED','NOT_VERIFIED')):continue
   if 'VERIFIED'in state or state=='PASS'or all(x in state for x in('FRESH','DOWNLOAD','BYTE_EQUAL')):return True
 return False

def load_allowlist(public_root,proof):
 root=Path(public_root).resolve();value=json.loads(Path(proof).read_text());out={}
 if value.get('schema')!='v2-positive-restoration-proof-allowlist-v1':raise ValueError('affirmative proof allowlist required')
 for row in value['entries']:
  path=root/safe_artifact(row['proof_receipt']);body=path.read_bytes()
  if hashlib.sha256(body).hexdigest()!=row['proof_receipt_sha256']:raise ValueError('restoration proof receipt changed')
  receipt=json.loads(body);digest=row['sha256']
  if not re.fullmatch('[a-f0-9]{64}',digest):raise ValueError('invalid proof digest')
  if not positive_receipt(receipt)or digest not in set(x for x in walk(receipt)if isinstance(x,str)):raise ValueError('positive matching restoration proof absent')
  if digest in out and out[digest]!=row['artifact_id']:raise ValueError('ambiguous restoration proof identity')
  out[digest]=row['artifact_id']
 return out
