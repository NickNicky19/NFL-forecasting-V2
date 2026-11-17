"""Materialize at most2 authenticated MCP raw-file references, never Drive IDs.

Source metadata/rawfetch chain stays PRIVATE. No inline base64, upload, sharing,
deletion, original-file overwrite, model work or scientific scoring.
"""
import argparse,concurrent.futures,hashlib,json,os,time,traceback,urllib.request
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def now():return datetime.now(timezone.utc).isoformat()


def materialize(reference,fresh_root):
 reference=Path(reference);record=json.loads(reference.read_text());p=record['part'];m=record['metadata'];r=record['response']
 fresh_root=Path(fresh_root).resolve()
 if fresh_root.is_relative_to(ROOT):raise ValueError('private fresh area outside Git required')
 if(m['id']!=p['provider_reference']['provider_object_id']or m['title']!=p['expected_remote_file_name']
     or int(m['size'])!=p['bytes']or m['shared']is not False or record['approved_parent']not in m['parent_ids']):
  raise ValueError('METADATA_IDENTITY_PRIVACY_OR_PARENT_MISMATCH')
 uri=r['file_uri']
 if not isinstance(uri,dict)or not uri.get('download_url')or uri.get('file_id')==m['id']:
  raise ValueError('AUTHENTICATED_TOP_LEVEL_FILE_SERVICE_REFERENCE_REQUIRED')
 if r.get('b64_string')is not None or int(r['file_size_bytes'])!=p['bytes']:
  raise ValueError('NO_INLINE_BYTES_AND_EXACT_FILE_SIZE_REQUIRED')
 name=p['expected_remote_file_name']
 if Path(name).name!=name:raise ValueError('SAFE_PART_BASENAME_REQUIRED')
 target=fresh_root/name
 if target.exists():raise ValueError('PRESERVE_EXISTING_PART_NO_OVERWRITE')
 fresh_root.mkdir(parents=True,exist_ok=True)
 receipt=reference.with_name(reference.name.removesuffix('-FETCH.json')+'-DOWNLOADED.json')
 if receipt.exists():raise ValueError('PRESERVE_EXISTING_RECEIPT_NO_OVERWRITE')
 begun=now();h=hashlib.sha256();n=0
 try:
  # URL comes only from the authenticated top-level MCP file_uri. No Google
  # API-key/cookie extraction, directDrive bypass or FileService/Drive-ID mix.
  with urllib.request.urlopen(uri['download_url'],timeout=120)as response:
   if response.status!=200:raise ValueError('COMPLETE_HTTP200_REQUIRED')
   if response.headers.get('Content-Length')and int(response.headers['Content-Length'])!=p['bytes']:
    raise ValueError('CONTENT_LENGTH_MISMATCH')
   with target.open('xb')as out:
    for chunk in iter(lambda:response.read(1048576),b''):
     if not chunk:continue
     if n+len(chunk)>p['bytes']:raise ValueError('EXPECTED_BYTES_LIMIT_BEFORE_WRITE')
     out.write(chunk);h.update(chunk);n+=len(chunk)
    out.flush();os.fsync(out.fileno())
  if(n,h.hexdigest())!=(p['bytes'],p['sha256'])or sha(target)!=p['sha256']:
   raise ValueError('FRESH_PART_SIZE_OR_SHA256_MISMATCH')
  result=dict(artifact_id=p['artifact_id'],index=p['index'],status='DOWNLOADED',unshared=True,
   provider_object_id=m['id'],expected_remote_file_name=name,workspace_path=str(target),
   bytes=n,sha256=h.hexdigest(),HTTP_status=200,started_at_utc=begun,completed_at_utc=now(),
   source_receipt=dict(path=str(reference),sha256=sha(reference)),
   file_service_id=uri['file_id'],no_inline_base64=True,original_sources_preserved=True)
  with receipt.open('x')as f:json.dump(result,f,indent=2);f.write('\n')
  return dict(status='DOWNLOADED_HASH_VERIFIED',artifact_id=p['artifact_id'],index=p['index'],bytes=n,sha256=h.hexdigest())
 except Exception as exc:
  failure=receipt.with_name(receipt.stem+'-FAILED.json')
  with failure.open('x')as f:json.dump(dict(state='STOP_ON_READBACK_FAILURE',type=type(exc).__name__,
    private_traceback=traceback.format_exc(),source_receipt_sha256=sha(reference),
    started_at_utc=begun,completed_at_utc=now(),received_bytes=n,
    partial_file_preserved=target.exists()),f,indent=2);f.write('\n')
  return dict(status='STOP_ON_READBACK_FAILURE',artifact_id=p['artifact_id'],index=p['index'],error_type=type(exc).__name__)


if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--reference',type=Path,action='append',required=True);parser.add_argument('--fresh-root',type=Path,required=True)
 args=parser.parse_args()
 if not 1<=len(args.reference)<=2:parser.error('one or two exact authenticated references per bounded batch')
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
  results=list(pool.map(lambda p:materialize(p,args.fresh_root),args.reference))
 print(json.dumps(results))
 if any(r['status']!='DOWNLOADED_HASH_VERIFIED'for r in results):raise SystemExit(2)
