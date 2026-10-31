"""Read-only content census, approved-proof and deduplicated delta audit."""
import argparse,collections,datetime,gzip,hashlib,json,os,resource,subprocess,tarfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
ACCEPTED='2ee4751c0c1ffce1900d6743b947a9330675056b'
GOOD={'UPLOADED_OWNER_ONLY_FRESH_DOWNLOAD_HASH_VERIFIED','OWNER_ONLY_UNSHARED_FRESH_DOWNLOAD_HASH_VERIFIED',
 'OWNER_ONLY_UNSHARED_FRESH_DOWNLOAD_BYTE_EQUAL','OWNER_ONLY_UNSHARED_FRESH_DOWNLOAD_INNER_BYTES_VERIFIED',
 'OWNER_ONLY_UNSHARED_ALL_PARTS_FRESH_DOWNLOAD_HASH_AND_INNER_BYTES_VERIFIED',
 'OWNER_ONLY_UNSHARED_ALL_PARTS_FRESHLY_DOWNLOADED_HASH_AND_INNER_BYTES_VERIFIED',
 'FRESH_PRIVATE_RESTORE_ALL_PARTS_AND_INNER_FILES_VERIFIED','FRESH_PRIVATE_BYTE_RESTORATION_VERIFIED',
 'FULL_FORECAST_PACKET_FRESH_PRIVATE_RESTORE_VERIFIED','RESTORED_AND_ALL_INNER_MEMBERS_VERIFIED',
 'RESTORED_ALL_INNER_FILES_VERIFIED','RESTORED_ALL_PARTS_AND_INNER_FILES_VERIFIED','FRESH_OWNER_ONLY_RESTORE_ALL_MEMBERS_VERIFIED'}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 parser=argparse.ArgumentParser()
 for x in('private-root','source-root','archive-root','recovery-root'):parser.add_argument('--'+x,type=Path,required=True)
 a=parser.parse_args();start,cpu=time.monotonic(),time.process_time();checks=collections.Counter()
 status=json.loads((HERE/'ARTIFACT_RECOVERY_STATUS.json').read_bytes());mapping=json.loads((a.recovery_root/'REQUIRED_FILES_PRIVATE.json').read_bytes());meta=json.loads((a.recovery_root/'DELTA_ARCHIVE_METADATA.json').read_bytes());cut=datetime.datetime.fromisoformat(status['cutoff_utc'].replace('Z','+00:00')).timestamp()
 tree=subprocess.run(['git','ls-tree','-r',ACCEPTED],cwd=ROOT,check=True,capture_output=True,text=True).stdout
 gitfiles={line.split('\t',1)[1]:line.split('\t',1)[0].split()[2]for line in tree.splitlines()}
 checked_public={}
 def public(path):
  rel=path.relative_to(ROOT).as_posix()
  if rel not in checked_public:
   body=path.read_bytes();assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==gitfiles[rel],rel
   checked_public[rel]=hashlib.sha256(body).hexdigest();checks['accepted_git_public_blob_hashes']+=1
  return checked_public[rel]
 manifest_path=ROOT/'reports/continuation-20261030c/PUBLIC_FILE_MANIFEST.json';public(manifest_path);pubmanifest=json.loads(manifest_path.read_bytes());published={};published_paths={}
 for r in pubmanifest['files']:
  assert public(ROOT/r['path'])==r['sha256'];published[r['sha256']]=r['path'];published_paths[r['path']]=r['sha256']
 proof={}
 candidates=set((ROOT/'reports').rglob('*RESTOR*.json'))
 candidates.add(ROOT/'reports/continuation-20261029/week8-shadow-v2/PRIVATE_REVIEW_CSV.json')
 for path in sorted(candidates):
  rel=path.relative_to(ROOT).as_posix()
  if rel not in gitfiles:continue
  value=json.loads(path.read_bytes())
  if not isinstance(value,dict):continue
  digest=value.get('archive_sha256',value.get('sha256',value.get('compressed_sha256')))
  positive=(value.get('state')in GOOD or value.get('status')in GOOD or value.get('fresh_download_byte_equal')is True)
  if not digest or not positive:continue
  proof[digest]=dict(artifact_id=value['artifact_id'],sha256=digest,proof_receipt=rel,proof_receipt_sha256=public(path),
      proof_kind='ACCEPTED_FRESH_RESTORATION_RECEIPT_WITH_POSITIVE_SUCCESS_STATE',receipt_state=value.get('state',value.get('status','fresh_download_byte_equal=True')))
 approved_ids={r['archive_sha256']:r['artifact_id']for r in status['archives']if r['state']=='FULLY_RESTORED_ACCEPTED'}
 for digest in approved_ids:assert digest in proof,('missing positive proof',approved_ids[digest])
 pending_ids={r['archive_sha256']:r['artifact_id']for r in status['archives']if r['state']in('LOCAL_ONLY','PARTIALLY_RESTORED')}
 archives={};members={};allroots={**approved_ids,**pending_ids}
 for path in sorted(a.archive_root.glob('*.tar.gz')):
  digest=sha(path)
  if digest not in allroots:continue
  ident=allroots[digest];assert ident not in archives;archives[ident]=dict(sha256=digest,bytes=path.stat().st_size,restored=digest in approved_ids);n=0;logical=0
  with tarfile.open(path,mode='r|gz')as t:
   for member in t:
    if not member.isfile():continue
    h=hashlib.sha256();size=0;stream=t.extractfile(member)
    for b in iter(lambda:stream.read(1048576),b''):h.update(b);size+=len(b)
    assert size==member.size;members[ident,member.name]=(h.hexdigest(),size);n+=1;logical+=size;checks['archive_member_blob_hashes']+=1
  expected=next(x for x in status['archives']if x['artifact_id']==ident);assert n==expected['inner_files']and logical==expected['inner_bytes']and path.stat().st_size==expected['archive_bytes'];checks['approved_or_pending_complete_archives']+=1
 assert len(archives)==len(allroots)
 # Independently validate only the public lossless encoding actually used.
 encoding={}
 for path in(ROOT/'reports/continuation-20261030c').rglob('*ENCODING*.json'):
  value=json.loads(path.read_bytes());digest=value.get('uncompressed_sha256',value.get('decompressed_sha256'))
  if not digest:continue
  if value.get('compressed_artifact'):
   blob=path.parent/value['compressed_artifact'];assert public(blob)==value['compressed_sha256'];h=hashlib.sha256();n=0
   with gzip.open(blob,'rb')as f:
    for b in iter(lambda:f.read(1048576),b''):h.update(b);n+=len(b)
   assert h.hexdigest()==digest and n==value['uncompressed_bytes'];encoding[path.relative_to(ROOT).as_posix()]=digest;public(path)
 required=mapping['required_files'];actual={};cache={}
 for namespace,base in(('EVIDENCE',a.private_root),('SOURCE',a.source_root)):
  candidates=(Path(folder)/name for folder,_,names in os.walk(base)for name in names)if namespace=='EVIDENCE'else(x for x in base.iterdir()if x.is_file())
  for path in candidates:
   if path.is_relative_to(a.recovery_root)or path.stat().st_mtime>cut:continue
   assert not path.is_symlink();st=path.stat();k=(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)
   if k not in cache:cache[k]=sha(path);checks['local_required_unique_inode_hashes']+=1
   assert k==(path.stat().st_dev,path.stat().st_ino,path.stat().st_size,path.stat().st_mtime_ns)
   actual[namespace,path.relative_to(base).as_posix()]=(cache[k],st.st_size)
 assert len(actual)==len(required)==status['required_file_paths']==29527
 assert {(x['namespace'],x['relative_path'])for x in required}==set(actual)
 delta_members={};inside_map=None;archive=a.recovery_root/'RECOVERY_DELTA_20261030D_V1.tar.gz';assert sha(archive)==meta['archive_sha256']
 with tarfile.open(archive,mode='r|gz')as t:
  for member in t:
   assert member.isfile()
   if member.name=='REQUIRED_FILES_PRIVATE.json':inside_map=json.load(t.extractfile(member));continue
   assert member.name.startswith('blobs/');h=hashlib.sha256();size=0;f=t.extractfile(member)
   for b in iter(lambda:f.read(1048576),b''):h.update(b);size+=len(b)
   digest=h.hexdigest();assert member.name=='blobs/'+digest and digest not in delta_members;delta_members[digest]=size;checks['deduplicated_delta_blob_hashes']+=1
 assert inside_map==mapping and sha(a.recovery_root/'REQUIRED_FILES_PRIVATE.json')==meta['private_file_map_sha256']
 states=collections.Counter();used_proof=set();novel=set()
 for row in required:
  digest,n=actual[row['namespace'],row['relative_path']];assert digest==row['sha256']and n==row['bytes'];binding=row['restoration_binding'];kind=binding['kind'];ident=binding['artifact_id'];states[row['state']]+=1
  if kind=='ARCHIVE_MEMBER':
   assert members[ident,binding['member']]==(digest,n);expected='FULLY_RESTORED_BYTES'if archives[ident]['restored']else'COVERED_AFTER_PENDING_ARCHIVE_COMPLETION';assert row['state']==expected
   if archives[ident]['restored']:used_proof.add(archives[ident]['sha256'])
  elif kind=='FULL_ARCHIVE':
   assert archives[ident]['sha256']==digest and archives[ident]['bytes']==n and archives[ident]['restored'];used_proof.add(digest)
  elif kind=='FULL_STANDALONE_OBJECT':assert digest in proof;used_proof.add(digest)
  elif kind=='PUBLIC_SAFE_ALREADY_PUBLISHED':assert published_paths[binding['member']]==digest
  elif kind=='PUBLIC_SAFE_LOSSLESS_ENCODING':assert encoding[binding['member']]==digest
  elif kind=='DELTA_BLOB':assert binding['member']=='blobs/'+digest and delta_members[digest]==n;novel.add(digest);assert row['state']=='NEW_DELTA_REQUIRED'
  else:raise AssertionError(kind)
  checks['required_path_alias_restoration_bindings']+=1
 assert novel==set(delta_members)and len(novel)==meta['novel_unique_files']==1787;assert sum(delta_members.values())==meta['novel_unique_bytes']==278519991
 assert len({x['sha256']for x in required})==status['required_unique_content_hashes']==20217
 full=hashlib.sha256();total=0
 for part in meta['parts']:
  path=a.recovery_root/part['name'];assert sha(path)==part['sha256']and path.stat().st_size==part['bytes'];total+=part['bytes']
  with path.open('rb')as f:
   for b in iter(lambda:f.read(1048576),b''):full.update(b)
 assert full.hexdigest()==meta['archive_sha256']and total==meta['archive_bytes']==263613679 and len(meta['parts'])==13
 prior=json.loads((HERE/'ARCHIVE_CAPACITY_INDEPENDENT_REVIEW.json').read_bytes());pmap={r['artifact_id']:r for r in prior['rows']}
 pending_bytes=pending_parts=0
 for digest,ident in pending_ids.items():
  row=next(x for x in status['archives']if x['artifact_id']==ident);old=pmap[ident];assert row['missing_part_indexes']==old['missing_part_indices']and row['missing_upload_bytes']==old['missing_part_bytes'];pending_bytes+=row['missing_upload_bytes'];pending_parts+=row['missing_parts']
 assert pending_bytes+total==status['minimum_additional_upload_bytes_for_frozen_plan']==1093747658 and pending_parts+13==status['missing_upload_parts']==53
 # Add the separately proved index object, even if its old bytes are not a used
 # alias in the current census. The allowlist is affirmative and source-bound.
 used_proof.add(json.loads((ROOT/'reports/continuation-20261030c/PRIVATE_INDEX_RESTORATION.json').read_bytes())['sha256'])
 allowlist=dict(schema='v2-positive-restoration-proof-allowlist-v1',accepted_parent=ACCEPTED,
  artifact_semantics='Positive accepted fresh-restoration receipts. A locator or digest in a private index is not itself proof; published file/member and encoding hashes are separately checked.',
  entries=sorted((proof[d]for d in used_proof),key=lambda x:(x['artifact_id'],x['sha256'])))
 output=HERE/'RESTORATION_PROOF_ALLOWLIST.json';output.write_text(json.dumps(allowlist,indent=2)+'\n')
 result=dict(state='PASS_EXPANDED_CONTENT_RECOVERY_PLAN_WITH_POSITIVE_PROOF_SUPPLEMENT',status_artifact_sha256=sha(HERE/'ARTIFACT_RECOVERY_STATUS.json'),delta_archive_sha256=meta['archive_sha256'],private_map_sha256=meta['private_file_map_sha256'],positive_allowlist_sha256=sha(output),fully_restored_archive_proofs=len(approved_ids),approved_or_pending_archives_checked=len(archives),positive_used_object_proofs=len(used_proof),required_path_aliases=len(required),unique_content_hashes=20217,state_counts=dict(states),delta_unique_file_blobs=len(delta_members),delta_raw_file_bytes=sum(delta_members.values()),delta_archive_bytes=total,delta_parts=13,missing_upload_bytes=1093747658,missing_upload_parts=53,checks=dict(checks),scope='All local evidence files and top-level admitted source files withmtime at/before frozen cutoff19:17:17Z, excluding the new recovery directory. No source subdirectories exist. Content blobs restore all path aliases through private map. Postcutoff30d artifacts and unshared/unretained old private sessions are outside this finite census. Old defense/small transportarchive encodings remain local; their underlying scientific files are covered by delta where needed. This is a plan before upload, not completed durability or an entropy minimum.',tool_finding='Original recovery_census.py v1 accepted index digests by absence of negative state. Actual coverage is now positively proved; reusable tool must require this source-bound allowlist in a separately versioned qualification, not infer restoration from index presence.',new_fits=0,new_forecasts=0,uploads=0,deletions=0,current2026_week8_outcomes_read=0,resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
 (HERE/'RECOVERY_DELTA_INDEPENDENT_REVIEW.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
