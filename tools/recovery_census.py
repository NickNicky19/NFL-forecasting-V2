#!/usr/bin/env python3
"""Hash retained evidence and prepare a deduplicated, missing-only private bundle.

This command never uploads, deletes, changes sharing or fits a model. Every
location is a CLI argument. Public output contains safe IDs, sizes and hashes;
the file-level restoration map stays inside the private companion bundle.
"""
import argparse,collections,datetime,gzip,hashlib,io,json,re,tarfile,time
from pathlib import Path

PART=20*1024*1024
PENDING={'SEASON_2024_V2_ARCHIVE_METADATA.json':'v2-private-season-2024-v2.tar.gz','SEASON_2023_COMPLETE_ARCHIVE_METADATA.json':'v2-private-season-2023-complete-v1.tar.gz','SEASON_2022_V2_ARCHIVE_METADATA.json':'v2-private-season-2022-v2.tar.gz'}

def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def write(path,value):
 with Path(path).open('x')as f:json.dump(value,f,indent=2);f.write('\n')
def restored_digests(index,public_root):
 result={}
 for key,value in index.items():
  if not isinstance(value,dict):continue
  status=str(value.get('state',''))
  if any(x in status for x in('LOCAL_ARCHIVE','PARTIAL','QUOTA_BLOCKED')):continue
  digest=value.get('archive_sha256',value.get('sha256',value.get('compressed_sha256')))
  if digest:result[digest]=key
 # These later restoration receipts intentionally do not rewrite the older
 # private locator index. They bind separately preserved successful uploads.
 for name in ('PRIVATE_ORIGINAL_CODE_RESTORATION.json','PRIVATE_INDEX_RESTORATION.json'):
  p=public_root/'reports/continuation-20261030c'/name
  if p.exists():
   value=json.loads(p.read_text());result[value.get('archive_sha256',value.get('sha256'))]=value['artifact_id']
 return result

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in('private-root','source-root','archive-root','public-root','output','private-output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--cutoff-utc',required=True);a=p.parse_args();start=time.monotonic();a.output.mkdir(parents=True,exist_ok=True);a.private_output.mkdir(parents=True,exist_ok=True)
 cutoff=datetime.datetime.fromisoformat(a.cutoff_utc.replace('Z','+00:00')).timestamp();admin=a.private_root/'continuation-20261030c';index=json.loads((a.private_root/'v2-companion-private-locations.json').read_text());approved=restored_digests(index,a.public_root);known={};future={};archive_rows=[];pending={}
 for metadata,name in PENDING.items():
  m=json.loads((admin/metadata).read_text());pending[m['archive_sha256']]=m
 # Staged public file hashes cover only bytes already legitimately published.
 public_manifest=json.loads((a.public_root/'reports/continuation-20261030c/PUBLIC_FILE_MANIFEST.json').read_text())
 for r in public_manifest['files']:known.setdefault(r['sha256'],dict(kind='PUBLIC_SAFE_ALREADY_PUBLISHED',artifact_id='V2-PUBLIC-2EE4751',member=r['path']))
 for path in sorted(a.archive_root.glob('*.tar.gz')):
  digest=sha(path)
  if digest not in approved and digest not in pending:continue
  m=pending.get(digest);safe=approved.get(digest)or m['artifact_id'];target=known if digest in approved else future;target[digest]=dict(kind='FULL_ARCHIVE',artifact_id=safe,member=None)
  files=0;logical=0
  with tarfile.open(path,mode='r|gz')as tar:
   for info in tar:
    if not info.isfile():continue
    f=tar.extractfile(info);h=hashlib.sha256();size=0
    for b in iter(lambda:f.read(1048576),b''):h.update(b);size+=len(b)
    if size!=info.size:raise ValueError('archive member size mismatch')
    target.setdefault(h.hexdigest(),dict(kind='ARCHIVE_MEMBER',artifact_id=safe,member=info.name));files+=1;logical+=size
  if m:
   if path.stat().st_size!=m['archive_bytes']:raise ValueError('pending archive size mismatch')
   if '2024' in safe:
    uploads=json.loads((admin/'SEASON_2024_V2_PRIVATE_UPLOADS.json').read_text());done={r['index']for r in uploads if r['status']=='UPLOADED'}
   else:done=set()
   missing=[i for i in range(len(m['parts']))if i not in done];missing_bytes=sum(m['parts'][i]['bytes']for i in missing)
  else:missing=[];missing_bytes=0
  archive_rows.append(dict(artifact_id=safe,state='FULLY_RESTORED_ACCEPTED'if digest in approved else'PARTIALLY_RESTORED'if done else'LOCAL_ONLY',archive_sha256=digest,archive_bytes=path.stat().st_size,inner_files=files,inner_bytes=logical,missing_part_indexes=missing,missing_parts=len(missing),missing_upload_bytes=missing_bytes))
  if time.monotonic()-start>300:raise RuntimeError('bounded archive census stop')
 # A standalone full forecast packet is already privately retained.
 for digest,safe in approved.items():known.setdefault(digest,dict(kind='FULL_STANDALONE_OBJECT',artifact_id=safe,member=None))
 # A public compressed aggregate can restore its original uncompressed bytes.
 for receipt in (a.public_root/'reports/continuation-20261030c').rglob('*ENCODING*.json'):
  r=json.loads(receipt.read_text());digest=r.get('uncompressed_sha256',r.get('decompressed_sha256'))
  if digest:known.setdefault(digest,dict(kind='PUBLIC_SAFE_LOSSLESS_ENCODING',artifact_id='V2-PUBLIC-2EE4751',member=receipt.relative_to(a.public_root).as_posix()))
 required=[];novel={};groups=collections.defaultdict(lambda:collections.Counter());cache={}
 sources=[('EVIDENCE',a.private_root,p)for p in a.private_root.rglob('*')if p.is_file()and p.stat().st_mtime<=cutoff and not p.is_relative_to(a.private_output)]
 sources += [('SOURCE',a.source_root,p)for p in a.source_root.iterdir()if p.is_file()and p.stat().st_mtime<=cutoff]
 for namespace,root,path in sources:
  if path.is_symlink():raise ValueError('evidence symlink requires separate review')
  before=path.stat();key=(before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)
  digest=cache.get(key)
  if digest is None:digest=sha(path);cache[key]=digest
  if key!=(path.stat().st_dev,path.stat().st_ino,path.stat().st_size,path.stat().st_mtime_ns):raise ValueError('source changed during census')
  relative=path.relative_to(root).as_posix();scope=namespace+'-'+(relative.split('/')[0]if '/'in relative else'ROOT')
  if digest in known:state='FULLY_RESTORED_BYTES';binding=known[digest]
  elif digest in future:state='COVERED_AFTER_PENDING_ARCHIVE_COMPLETION';binding=future[digest]
  else:state='NEW_DELTA_REQUIRED';binding=dict(kind='DELTA_BLOB',artifact_id='V2-PRIVATE-RECOVERY-DELTA-20261030D-0001',member='blobs/'+digest);novel.setdefault(digest,path)
  required.append(dict(namespace=namespace,relative_path=relative,bytes=before.st_size,sha256=digest,state=state,restoration_binding=binding));groups[scope]['files']+=1;groups[scope]['bytes']+=before.st_size;groups[scope][state+'_files']+=1;groups[scope][state+'_bytes']+=before.st_size
  if time.monotonic()-start>300:raise RuntimeError('bounded source census stop')
 private_map=dict(schema='v2-private-recovery-file-map-v1',cutoff_utc=a.cutoff_utc,required_files=required,novel_unique_files=len(novel),known_full_file_hashes=len(known),pending_file_hashes=len(future))
 write(a.private_output/'REQUIRED_FILES_PRIVATE.json',private_map)
 archive=a.private_output/'RECOVERY_DELTA_20261030D_V1.tar.gz'
 with archive.open('xb')as output:
  with tarfile.open(fileobj=output,mode='w:gz',compresslevel=1)as tar:
   for digest,path in sorted(novel.items()):
    info=tarfile.TarInfo('blobs/'+digest);info.size=path.stat().st_size
    with path.open('rb')as f:tar.addfile(info,f)
   body=json.dumps(private_map,separators=(',',':')).encode();info=tarfile.TarInfo('REQUIRED_FILES_PRIVATE.json');info.size=len(body);tar.addfile(info,io.BytesIO(body))
 parts=[]
 with archive.open('rb')as f:
  for i,b in enumerate(iter(lambda:f.read(PART),b'')):
   name='RECOVERY_DELTA_20261030D_V1.part'+str(i).zfill(3)
   with(archive.parent/name).open('xb')as target:target.write(b)
   parts.append(dict(name=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
 meta=dict(artifact_id='V2-PRIVATE-RECOVERY-DELTA-20261030D-0001',archive_bytes=archive.stat().st_size,archive_sha256=sha(archive),parts=parts,novel_unique_files=len(novel),novel_unique_bytes=sum(p.stat().st_size for p in novel.values()),private_file_map_sha256=sha(a.private_output/'REQUIRED_FILES_PRIVATE.json'))
 write(a.private_output/'DELTA_ARCHIVE_METADATA.json',meta);archive_rows.append(dict(artifact_id=meta['artifact_id'],state='LOCAL_ONLY_PREPARED_NO_UPLOAD',archive_sha256=meta['archive_sha256'],archive_bytes=meta['archive_bytes'],missing_part_indexes=list(range(len(parts))),missing_parts=len(parts),missing_upload_bytes=meta['archive_bytes'],inner_files=len(novel)+1))
 summary=dict(protocol='v2-recoverability-census-20261030d-v1',accepted_parent='2ee4751c0c1ffce1900d6743b947a9330675056b',cutoff_utc=a.cutoff_utc,archives=archive_rows,minimum_additional_upload_bytes_for_frozen_plan=sum(r['missing_upload_bytes']for r in archive_rows),missing_upload_parts=sum(r['missing_parts']for r in archive_rows),required_file_paths=len(required),required_unique_content_hashes=len({r['sha256']for r in required}),new_delta_unique_files=len(novel),new_delta_unique_file_bytes=meta['novel_unique_bytes'],all_original_local_files_preserved=True,uploads_or_deletions=0,new_fit_calls=0,wall_seconds=time.monotonic()-start,capacity_scope='Finish3fixedcanonicalarchivesusingonlymissingparts,then1deduplicateddelta. Coversallscientificandmetadatafilepathsatcutoff;previousunuploadedtransportencodingsremainlocalunchanged. Notanentropyminimumorproviderfreespacemeasurement.')
 write(a.output/'ARTIFACT_RECOVERY_STATUS.json',summary);write(a.private_output/'SCIENTIFIC_SCOPE_COUNTS_PRIVATE.json',dict(groups));print(json.dumps({k:summary[k]for k in('minimum_additional_upload_bytes_for_frozen_plan','missing_upload_parts','required_file_paths','new_delta_unique_files','wall_seconds')}))

if __name__=='__main__':main()
