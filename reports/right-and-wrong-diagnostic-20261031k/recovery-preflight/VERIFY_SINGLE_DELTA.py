"""Verify ONLY the complete fresh delta; explicitly never a global fit gate.

Reuses the independently reviewed fresh_downloads/assemble_delta/catalog code.
Does not transfer, extract inner files, fabricate missing archives or fit models.
"""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('reviewed_fresh_restore',HERE/'VERIFY_FRESH_ARCHIVES.py')
restore=importlib.util.module_from_spec(spec);spec.loader.exec_module(restore)


def verify(queue_path,downloads_path,fresh_root,joined_root,external_map,public_output):
 plan,prior=restore.fixed_inputs();queue=restore.read(queue_path)
 if queue.get('accepted_plan_sha256')!=restore.gate.EXPECTED_PLAN_SHA256:
  raise ValueError('exact accepted fetchqueue required')
 aid=restore.DELTA;expected=next(r for r in plan['archives']if r['artifact_id']==aid)
 binding=queue['metadata'][aid];meta_path=Path(binding['metadata_local_path'])
 if restore.sha(meta_path)!=binding['metadata_sha256']:raise ValueError('source delta metadata changed')
 meta=restore.read(meta_path)
 if(meta['archive_sha256'],meta['archive_bytes'])!=(expected['archive_sha256'],expected['archive_bytes']):
  raise ValueError('exact frozen canonicaldelta required')
 downloads=restore.read(downloads_path)['archives']
 if set(downloads)!={aid}:raise ValueError('single-delta scope only')
 materialized=restore.fresh_downloads(aid,meta,queue,downloads[aid],fresh_root)
 joined_root,public_output=Path(joined_root),Path(public_output)
 if joined_root.exists()or joined_root.resolve().is_relative_to(restore.ROOT)or public_output.exists():
  raise ValueError('fresh immutable restoration/report areas required')
 joined_root.mkdir(parents=True);public_output.mkdir(parents=True)
 joined=joined_root/(aid+'.tar.gz')
 restore.assemble_delta(meta,materialized,joined)
 catalog,mapping,blob=restore.catalog(joined,delta=True)
 if len(catalog)!=1788 or len(catalog)!=expected['inner_files']:raise ValueError('exact1788regularmembers required')
 encoding=restore.read(restore.BASE/'RECOVERY_MAP_ENCODING_INDEPENDENT_READBACK.json')
 pretty=(json.dumps(mapping,indent=2)+'\n').encode()
 if(hashlib.sha256(blob).hexdigest(),len(blob))!=(encoding['archive_map_member_sha256'],encoding['archive_map_member_bytes']):
  raise ValueError('compact fresh map encoding mismatch')
 if(hashlib.sha256(pretty).hexdigest(),len(pretty))!=(restore.gate.EXPECTED_PRIVATE_MAP_SHA256,encoding['external_private_map_bytes']):
  raise ValueError('external pretty map encoding mismatch')
 if restore.sha(external_map)!=restore.gate.EXPECTED_PRIVATE_MAP_SHA256 or mapping!=restore.read(external_map):
  raise ValueError('frozen externalmap semantic mismatch')
 rows=mapping['required_files']
 if len(rows)!=29527 or len({r['sha256']for r in rows})!=20217:
  raise ValueError('fixed complete map scope mismatch')
 aliases=[r for r in rows if r['restoration_binding']['kind']=='DELTA_BLOB'];novel=set()
 for row in aliases:
  member=row['restoration_binding']['member'];digest=row['sha256']
  if member!='blobs/'+digest or catalog.get(member)!=(digest,row['bytes']):raise ValueError('fresh delta source binding mismatch')
  novel.add(digest)
 actual={name.removeprefix('blobs/')for name in catalog if name.startswith('blobs/')}
 if novel!=actual or len(novel)!=1787:raise ValueError('all1787unique sourceblobs required')
 proof=dict(artifact_id=aid,status='FRESH_PRIVATE_RESTORE_ALL_PARTS_AND_INNER_FILES_VERIFIED',
  archive_bytes=meta['archive_bytes'],archive_sha256=meta['archive_sha256'],parts=len(materialized),
  archive_member_count_verified=1788,inner_file_checks=1787,manifest_file_extra=1,
  full_archive_fresh_restoration_verified=True,all_regular_member_bytes_verified=True,missing_parts=0,
  covered_delta_path_aliases=len(aliases),covered_delta_unique_content_hashes=len(novel),
  embedded_compact_map_sha256=hashlib.sha256(blob).hexdigest(),external_map_sha256=hashlib.sha256(pretty).hexdigest(),
  map_encodings_semantically_identical=True,completed_at_utc=restore.now(),visibility='allpartsmetadataunshared',
  inner_files_extracted_to_filesystem=0,global_old_recovery_gate_cleared=False,
  other_three_required_archives='INCOMPLETE_NOT_SUBSTITUTED_BY_LOCAL_ORIGINALS',accepted_prior_proof_objects_revalidated=len(prior),
  new_uploads=0,new_downloads=0,new_NFL_fits=0,worker_release=False,
  source_queue_sha256=restore.sha(queue_path),source_download_manifest_sha256=restore.sha(downloads_path),
  reviewed_core_verifier_sha256=restore.sha(HERE/'VERIFY_FRESH_ARCHIVES.py'),single_delta_adapter_sha256=restore.sha(__file__))
 with(public_output/'DELTA_FRESH_RESTORATION_RECEIPT.json').open('x')as f:json.dump(proof,f,indent=2);f.write('\n')
 return proof


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in('queue-path','downloads-path','fresh-root','joined-root','external-map','public-output'):p.add_argument('--'+n,type=Path,required=True)
 print(json.dumps(verify(**vars(p.parse_args()))))
