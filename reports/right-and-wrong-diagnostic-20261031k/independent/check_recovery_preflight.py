"""Independent read-only local part/plan/archive-header audit; no remote actions."""
import argparse,collections,datetime,hashlib,json,tarfile,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
def read(p):return json.loads(p.read_bytes())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('--private-root',type=Path,required=True);args=a.parse_args();start=time.monotonic()
 planpath=REPO/'reports/continuation-20261030d/ARTIFACT_RECOVERY_STATUS.json';receiptpath=HERE.parent/'recovery-preflight/RECOVERY_PREFLIGHT_RECEIPT_V2.json';queuepath=args.private_root/'right-wrong-20261031k-missing-only-preflight/REQUIRED_MISSING_PART_QUEUE.json';oldpath=args.private_root/'recovery-20261030d/RECOVERY_UPLOAD_QUEUE.json'
 plan=read(planpath);receipt=read(receiptpath);queue=read(queuepath);old=read(oldpath)
 assert sha(planpath)==receipt['accepted_plan_sha256']=='7ce075fc7b853a646f79795bb7133b597ee5dbeaa6cb7f5f21240e8cd8d516de'
 assert sha(queuepath)==receipt['private_queue_sha256']=='0afa92672d70b356219813941d32937a03e2e1e127dfd272a75e9facb303a289'
 assert {(r['artifact_id'],r['index']):{k:r[k]for k in old[0]}for r in queue}=={(r['artifact_id'],r['index']):r for r in old}
 assert len(queue)==plan['missing_upload_parts']==receipt['required_missing_parts']==53
 assert len({(r['artifact_id'],r['index'])for r in queue})==len({r['file_name']for r in queue})==53
 assert sum(r['bytes']for r in queue)==plan['minimum_additional_upload_bytes_for_frozen_plan']==receipt['required_missing_upload_bytes']==1093747658
 archiveplan={r['artifact_id']:r for r in plan['archives']};reported={r['artifact_id']:r for r in receipt['archives']};groups=collections.defaultdict(list)
 for r in queue:
  p=Path(r['local_path']);assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'];assert r['remote_presence']=='ROOT_CURRENT333_ITEM_RECHECK_REQUIRED_NOT_DONE_BY_SOURCE_AGENT';groups[r['artifact_id']].append(r)
 assert set(groups)==set(reported) and len(groups)==4
 proofs=[]
 for aid,parts in groups.items():
  p=archiveplan[aid];rep=reported[aid];assert sorted(r['index']for r in parts)==sorted(p['missing_part_indexes']);assert len(parts)==p['missing_parts']==rep['required_missing_parts'];assert sum(r['bytes']for r in parts)==p['missing_upload_bytes']==rep['required_missing_bytes']
  archive=Path(parts[0]['archive_local_path']);assert all(r['archive_local_path']==str(archive)for r in parts);digest=sha(archive);assert digest==p['archive_sha256']==rep['archive_sha256'] and all(r['archive_sha256']==digest for r in parts);assert archive.stat().st_size==p['archive_bytes']==rep['archive_bytes']
  count=total=0
  with tarfile.open(archive,'r:*')as t:
   for m in t:
    if m.isfile():count+=1;total+=m.size
  assert count==rep['regular_members'] and total==rep['all_regular_member_uncompressed_bytes']
  proofs.append(dict(artifact_id=aid,local_archive_sha256=digest,archive_bytes=archive.stat().st_size,required_missing_parts=len(parts),required_missing_bytes=sum(r['bytes']for r in parts),regular_header_count=count,declared_regular_payload_bytes=total))
 b=receipt['fresh_disk_budget'];full=sum(r['archive_bytes']for r in proofs);inner=sum(r['declared_regular_payload_bytes']for r in proofs)
 assert full==b['download_complete_four_archives_parts_bytes']==b['reassembled_complete_archives_bytes']==1306435930
 assert inner==b['tar_header_declared_regular_payload_bytes']==1372397644
 assert 2*full==b['minimum_parts_plus_archive_files_no_inner_extraction_bytes']==2612871860 and 2*full+inner==b['full_fresh_extraction_preserving_all_downloads_and_assemblies_bytes']==3985269504
 assert b['stream_buffer_separate_bytes']==1048576 and b['excludes_new_fit_output_reserve']is True
 assert min(queue,key=lambda r:r['bytes'])['bytes']==receipt['cheapest_required_part']['bytes']==11955439
 assert receipt['global_gate_cleared']is False and receipt['new_uploads']==receipt['new_downloads']==receipt['new_restorations']==receipt['new_fit_calls']==0
 out=dict(state='PASS_LOCAL_FROZEN_RECOVERY_PREFLIGHT_ONLY_NOT_REMOTE_RETENTION',at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_receipt_sha256=sha(receiptpath),accepted_plan_sha256=sha(planpath),private_queue_sha256=sha(queuepath),initial_frozen_missing_parts=53,initial_missing_upload_bytes=1093747658,all_53_local_parts_match_original_queue_and_frozen_plan=True,all_four_local_archive_whole_hashes_and_regular_headers_verified=True,archives=proofs,complete_remote_parts_download_bytes=full,parts_plus_assembled_archives_bytes=2*full,plus_declared_inner_extraction_bytes=2*full+inner,separate_stream_buffer_bytes=1048576,quota_or_remaining_capacity_authenticated=False,historical_disk_readings_scope='Historical observed local disk only, not reserved capacity or Drive quota.',current_remote_queue_scope='Frozen preflight before root subsequent successful part uploads; do not interpret 53 as a refreshed current remote missing count.',remote_transfers_or_extractions=0,inner_file_hash_recovery_verified=False,global_gate_cleared=False,new_model_calls=0,wall_seconds=time.monotonic()-start,checker_sha256=sha(Path(__file__)))
 with(HERE/'RECOVERY_PREFLIGHT_INDEPENDENT_REVIEW.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps({k:out[k]for k in('state','initial_frozen_missing_parts','initial_missing_upload_bytes','global_gate_cleared','wall_seconds')}))
if __name__=='__main__':main()
