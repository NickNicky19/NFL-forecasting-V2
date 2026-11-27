"""Bound original recovery-map encodings without changing the archive."""
import argparse,hashlib,json,resource,tarfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def digest(body):return hashlib.sha256(body).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--recovery-root',type=Path,required=True);a=p.parse_args();start,cpu=time.monotonic(),time.process_time()
 external=(a.recovery_root/'REQUIRED_FILES_PRIVATE.json').read_bytes();meta=json.loads((a.recovery_root/'DELTA_ARCHIVE_METADATA.json').read_bytes())
 with tarfile.open(a.recovery_root/'RECOVERY_DELTA_20261030D_V1.tar.gz',mode='r|gz')as archive:
  for member in archive:
   if member.name=='REQUIRED_FILES_PRIVATE.json':internal=archive.extractfile(member).read();break
  else:raise AssertionError('required private map member absent')
 obj=json.loads(internal);assert obj==json.loads(external);assert digest(external)==meta['private_file_map_sha256']
 reconstructed=(json.dumps(obj,indent=2)+'\n').encode();assert reconstructed==external
 result=dict(state='PASS_DISTINCT_EXTERNAL_AND_ARCHIVE_MAP_BYTE_BINDINGS',delta_archive_sha256=meta['archive_sha256'],
  external_private_map_sha256=digest(external),external_private_map_bytes=len(external),archive_map_member='REQUIRED_FILES_PRIVATE.json',
  archive_map_member_sha256=digest(internal),archive_map_member_bytes=len(internal),semantic_objects_identical=True,
  deterministic_external_reconstruction='UTF8 json.dumps(decoded_archive_map,indent=2) + newline; preserve insertion order; equality verified byteforbyte',
  original_delta_metadata_sha256=digest((a.recovery_root/'DELTA_ARCHIVE_METADATA.json').read_bytes()),
  interpretation='The existing metadata binds the external prettyJSON bytes, not the compact map member. Keep both hashes in an additive recovery qualification; do not pretend the two encodings are byte-identical or overwrite original delta.',
  new_fits=0,uploads=0,deletions=0,current2026_week8_outcomes_read=0,
  resource=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024))
 (HERE/'RECOVERY_MAP_ENCODING_INDEPENDENT_READBACK.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
