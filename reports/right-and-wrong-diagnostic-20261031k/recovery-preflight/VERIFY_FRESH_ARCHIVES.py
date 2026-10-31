"""Verify root-materialized fresh private parts; no transfer, extraction or fit.

Default action only validates the existing20 positive prior proof objects.
The verify action reuses private_bundle.verify for three canonical archives;
the differently encoded delta gets an explicit source-bound stream adapter.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,os,sys,tarfile,time
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from tools import private_bundle
from nfl_v2 import expanded_retention_gate as gate
from nfl_v2.recovery_proof_v3 import load_allowlist

BASE=ROOT/'reports/continuation-20261030d'
DELTA='V2-PRIVATE-RECOVERY-DELTA-20261030D-0001'
def read(path):return json.loads(Path(path).read_text())
def sha(path):return private_bundle.digest(path)
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def now():return datetime.now(timezone.utc).isoformat()


def fixed_inputs():
 refs={'ARTIFACT_RECOVERY_STATUS.json':gate.EXPECTED_PLAN_SHA256,
       'RECOVERY_DELTA_INDEPENDENT_REVIEW.json':gate.EXPECTED_CONTENT_REVIEW_SHA256,
       'RECOVERY_MAP_ENCODING_INDEPENDENT_READBACK.json':gate.EXPECTED_MAP_REVIEW_SHA256,
       'RESTORATION_PROOF_ALLOWLIST.json':gate.EXPECTED_PRIOR_ALLOWLIST_SHA256}
 for name,digest in refs.items():
  if sha(BASE/name)!=digest:raise ValueError('frozen public recovery binding changed')
 prior=load_allowlist(ROOT,BASE/'RESTORATION_PROOF_ALLOWLIST.json')
 if len(prior)!=20:raise ValueError('exact20positivepriorproofs required')
 return read(BASE/'ARTIFACT_RECOVERY_STATUS.json'),prior


def fresh_downloads(aid,meta,queue,downloads,fresh_root):
 expected={r['index']:r for r in queue['parts']if r['artifact_id']==aid}
 if set(expected)!=set(range(len(meta['parts'])))or len(downloads)!=len(expected):
  raise ValueError('complete ordered part census required')
 ordered=sorted(downloads,key=lambda r:r['index'])
 for i,(part,actual)in enumerate(zip(meta['parts'],ordered)):
  q=expected[i];path=Path(actual['workspace_path']).resolve()
  if actual['index']!=i or actual.get('status')!='DOWNLOADED'or actual.get('unshared')is not True:
   raise ValueError('positive fresh private download record required')
  if not path.is_relative_to(Path(fresh_root).resolve()):
   raise ValueError('only current fresh-part area accepted, never originalpart paths')
  ref=q.get('provider_reference')
  if not ref or actual.get('provider_object_id')!=ref['provider_object_id']:
   raise ValueError('download must bind actual approved upload object')
  evidence=actual.get('source_receipt')
  if not evidence or sha(evidence['path'])!=evidence['sha256']:
   raise ValueError('retained root rawfetch/source-receipt hash required')
  if(q['sha256'],q['bytes'])!=(part['sha256'],part['bytes']):
   raise ValueError('part metadata differs from frozen queue')
  if path.stat().st_size!=part['bytes']or sha(path)!=part['sha256']:
   raise ValueError('fresh part byte/hash mismatch')
 return ordered


def assemble_delta(meta,downloads,joined):
 """Same completepart byte rules as private_bundle.verify; custom delta format."""
 if joined.exists()or joined.resolve().is_relative_to(ROOT):raise ValueError('fresh private joined path required')
 whole=hashlib.sha256();total=0
 with joined.open('xb')as out:
  for part,actual in zip(meta['parts'],downloads):
   ph=hashlib.sha256();size=0
   with Path(actual['workspace_path']).open('rb')as src:
    for chunk in iter(lambda:src.read(1048576),b''):
     out.write(chunk);whole.update(chunk);ph.update(chunk);total+=len(chunk);size+=len(chunk)
   if(size,ph.hexdigest())!=(part['bytes'],part['sha256']):raise ValueError('delta part bytes changed')
  out.flush();os.fsync(out.fileno())
 if(total,whole.hexdigest())!=(meta['archive_bytes'],meta['archive_sha256']):
  raise ValueError('complete delta archive mismatch')


def catalog(joined,delta=False):
 """Hash every fresh recovered regular member, including its exact manifest.

    extractfile reads bytes from the fresh archive stream; it does not create
    any inner filesystem path. Old local source files are never substituted.
 """
 result={};manifest=None;manifest_blob=None
 marker='REQUIRED_FILES_PRIVATE.json'if delta else'__V2_PRIVATE_MEMBERS__.json'
 with tarfile.open(joined,mode='r|gz')as tar:
  for member in tar:
   p=PurePosixPath(member.name)
   if not member.isfile()or p.is_absolute()or'..'in p.parts or member.name in result:
    raise ValueError('unexpected duplicate/unsafe/nonregular archive member')
   h=hashlib.sha256();size=0;parts=[];stream=tar.extractfile(member)
   for chunk in iter(lambda:stream.read(1048576),b''):
    h.update(chunk);size+=len(chunk)
    if member.name==marker:parts.append(chunk)
   if size!=member.size:raise ValueError('member size mismatch')
   result[member.name]=(h.hexdigest(),size)
   if member.name==marker:
    manifest_blob=b''.join(parts);manifest=json.loads(manifest_blob)
 if manifest is None:raise ValueError('exact archive manifest missing')
 if not delta:
  expected={r['name']:(r['sha256'],r['bytes'])for r in manifest['members']}
  if len(expected)!=len(manifest['members'])or set(result)!=(set(expected)|{marker}):
   raise ValueError('allmanifestmembers and onlymanifestmembers required')
  if any(result[name]!=value for name,value in expected.items()):raise ValueError('canonical member hash mismatch')
 else:
  for name,(digest,n)in result.items():
   if name!=marker and name!='blobs/'+digest:raise ValueError('delta contentaddressedmember mismatch')
 return result,manifest,manifest_blob


def validate_map(mapping,pending_catalogs,prior,external_map):
 if sha(external_map)!=gate.EXPECTED_PRIVATE_MAP_SHA256:raise ValueError('external frozen map changed')
 if mapping!=read(external_map):raise ValueError('freshembedded/privateexternal map semantics differ')
 rows=mapping['required_files']
 if len(rows)!=29527 or len({r['sha256']for r in rows})!=20217:
  raise ValueError('complete frozen scope required')
 if len({(r['namespace'],r['relative_path'])for r in rows})!=29527:raise ValueError('duplicate source path alias')
 kinds=collections.Counter();fresh=prior_rows=public_rows=0;novel=set()
 for row in rows:
  b=row['restoration_binding'];kind=b['kind'];aid=b['artifact_id'];value=(row['sha256'],row['bytes']);kinds[kind]+=1
  if kind=='DELTA_BLOB':
   if pending_catalogs[DELTA].get(b['member'])!=value:raise ValueError('freshdelta binding mismatch')
   novel.add(row['sha256']);fresh+=1
  elif kind=='ARCHIVE_MEMBER'and aid in pending_catalogs:
   if pending_catalogs[aid].get(b['member'])!=value:raise ValueError('freshpendingarchive binding mismatch')
   fresh+=1
  elif kind in('ARCHIVE_MEMBER','FULL_ARCHIVE','FULL_STANDALONE_OBJECT'):
   if aid not in set(prior.values()):raise ValueError('positive prior proof object required')
   if kind in('FULL_ARCHIVE','FULL_STANDALONE_OBJECT')and row['sha256']not in prior:
    raise ValueError('prior wholeobject digest required')
   prior_rows+=1
  elif kind in('PUBLIC_SAFE_ALREADY_PUBLISHED','PUBLIC_SAFE_LOSSLESS_ENCODING'):
   # Exact frozen map + pinned independent content review already verified
   # these immutable published bindings; do not relabel current files as old.
   public_rows+=1
  else:raise ValueError('unknown restoration binding')
 if len(novel)!=1787:raise ValueError('exact1787newdelta contentblobs required')
 return dict(covered_path_aliases=len(rows),covered_unique_content_hashes=20217,
  fresh_pending_archive_or_delta_aliases=fresh,accepted_prior_object_aliases=prior_rows,
  inherited_frozen_public_bindings=public_rows,binding_kinds=dict(kinds),
  prior_binding_authority='Exactacceptedcontentreview+fixedmap+20revalidatedpositivepriorproofs; no claimtheseold20objectswerefreshdownloadedinthiswave')


def verify(*,queue_path,downloads_path,fresh_root,joined_root,external_map,public_output):
 plan,prior=fixed_inputs();queue=read(queue_path);downloads=read(downloads_path)['archives']
 pending={r['artifact_id']:r for r in plan['archives']if r.get('missing_parts',0)}
 if set(downloads)!=gate.EXPECTED_PENDING_IDS:raise ValueError('allfourfreshcompletearchives required')
 if queue.get('accepted_plan_sha256')!=gate.EXPECTED_PLAN_SHA256 or len(queue['parts'])!=64:
  raise ValueError('exact64part sourceboundfetchqueue required')
 joined_root=Path(joined_root);public_output=Path(public_output)
 if joined_root.exists()or joined_root.resolve().is_relative_to(ROOT)or public_output.exists():
  raise ValueError('fresh immutable joined/report directories required')
 joined_root.mkdir(parents=True);public_output.mkdir(parents=True)
 catalogs={};proofs=[];embedded=None;embedded_blob=None
 for aid in sorted(pending):
  binding=queue['metadata'][aid];meta_path=Path(binding['metadata_local_path'])
  if sha(meta_path)!=binding['metadata_sha256']:raise ValueError('archive metadata changed')
  meta=read(meta_path);expected=pending[aid]
  if(meta['artifact_id'],meta['archive_bytes'],meta['archive_sha256'])!=(aid,expected['archive_bytes'],expected['archive_sha256']):
   raise ValueError('frozen canonical archive metadata required')
  materialized=fresh_downloads(aid,meta,queue,downloads[aid],fresh_root)
  joined=joined_root/(aid+'.tar.gz')
  if aid==DELTA:
   assemble_delta(meta,materialized,joined)
   proof=dict(artifact_id=aid,status='FRESH_PRIVATE_RESTORE_ALL_PARTS_AND_INNER_FILES_VERIFIED',
     archive_bytes=meta['archive_bytes'],archive_sha256=meta['archive_sha256'],parts=len(materialized))
  else:
   # Reuse the existing completepart+inner-byte verifier unchanged. Its
   # downloadmanifest is private and is preserved alongside the joined file.
   manifest=joined_root/(aid+'-DOWNLOADS.json')
   with manifest.open('x')as f:json.dump(materialized,f,indent=2);f.write('\n')
   proof=private_bundle.verify(meta_path,manifest,joined)
  cat,manifest,blob=catalog(joined,delta=aid==DELTA);catalogs[aid]=cat
  if len(cat)!=expected['inner_files']:raise ValueError('exactALLmembercensus required')
  if aid==DELTA:embedded,embedded_blob=manifest,blob
  proof.update(archive_member_count_verified=len(cat),inner_file_checks=len(cat)-1,
    manifest_file_extra=1,full_archive_fresh_restoration_verified=True,missing_parts=0,
    all_regular_member_bytes_verified=True,regular_payload_bytes=sum(v[1]for v in cat.values()),
    private_inner_member_catalog_sha256=hashlib.sha256(canonical(sorted(cat.items()))).hexdigest(),
    completed_at_utc=now(),visibility='allpartsmetadataunshared',inner_files_extracted_to_filesystem=0)
  file=public_output/(aid+'-FRESH_RESTORATION.json')
  with file.open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
  proofs.append(dict(artifact_id=aid,path=file.relative_to(ROOT).as_posix(),sha256=sha(file)))
 encoding=read(BASE/'RECOVERY_MAP_ENCODING_INDEPENDENT_READBACK.json')
 pretty=(json.dumps(embedded,indent=2)+'\n').encode()
 if(hashlib.sha256(embedded_blob).hexdigest(),len(embedded_blob))!=(encoding['archive_map_member_sha256'],encoding['archive_map_member_bytes']):
  raise ValueError('exactfreshcompactmap encoding required')
 if hashlib.sha256(pretty).hexdigest()!=gate.EXPECTED_PRIVATE_MAP_SHA256 or len(pretty)!=encoding['external_private_map_bytes']:
  raise ValueError('exactexternalpretty map encoding required')
 coverage=validate_map(embedded,catalogs,prior,external_map)
 result=dict(state='PASS_FRESH_FOUR_ARCHIVES_AND_REVALIDATED_PRIOR_SCOPE_NOT_FIT_RELEASE',
   completed_at_utc=now(),proof_receipts=proofs,all_required_archives_verified=True,
   all_required_members_verified=True,missing_required_parts=0,covered_private_map_sha256=gate.EXPECTED_PRIVATE_MAP_SHA256,
   accepted_prior_objects=20,inner_files_extracted_to_filesystem=0,**coverage,
   archive_manifest_map_encodings_verified=True,new_uploads=0,new_downloads=0,new_NFL_fits=0,
   note='Rootmustindependentlyreviewactualdownloadprovenance andcomposeexactexpanded_retention_gate receipt. Thisisnotaworkerrelease.')
 with(public_output/'FULL_SCOPE_RESTORATION_VALIDATION.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
 return result


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['preflight','verify'],nargs='?',default='preflight')
 for n in('queue-path','downloads-path','fresh-root','joined-root','external-map','public-output'):p.add_argument('--'+n,type=Path)
 a=p.parse_args()
 if a.action=='preflight':
  _,prior=fixed_inputs();print(json.dumps(dict(state='PRIOR_PROOF_PREFLIGHT_ONLY',positive_prior_objects=len(prior),new_restorations=0,new_fits=0)))
 else:
  values=vars(a);values.pop('action')
  if any(v is None for v in values.values()):p.error('all exact source/provenance/fresharea/report inputs required')
  print(json.dumps(verify(**values)))
