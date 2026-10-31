"""Independent current-quota accounting and pointer audit; no transfers."""
import collections,datetime,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];PRIVATE=Path('/workspace/evidence-private')
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 pre=PRIVATE/'right-wrong-20261031k-missing-only-preflight';transfer=PRIVATE/'old-recovery-20261031k';queuepath=pre/'REQUIRED_MISSING_PART_QUEUE.json';queue=read(queuepath);q={(r['artifact_id'],r['index']):r for r in queue};full=read(pre/'ALL_COMPLETE_PARTS_FETCH_QUEUE_V2.json');assert len(full['parts'])==64 and len(q)==53
 folder=read(PRIVATE/'right-wrong-20261031k-recovery-metadata/folder.json');success={};bindings=[];errors=[]
 for pat in ('upload-receipts/*.json','upload-wave2-receipts/*.json','ISOLATED_RETRY_AFTER_INTERNAL_ERROR.json'):
  for path in sorted(transfer.glob(pat)):
   z=read(path);part=z['part'];key=part['artifact_id'],part['index'];assert key in q
   assert all(part[k]==q[key][k]for k in ('bytes','sha256','file_name','local_path','artifact_id','index'))
   v=z['provider_result']
   if z.get('isError')is False:
    assert v.get('success')is True and v['parent_id']==folder['id']and v['file_name']==part['file_name'];assert key not in success
    assert v['structuredContent']=={k:value for k,value in v.items()if k!='structuredContent'}
    success[key]=part;bindings.append(sha(path))
   else:errors.append((path,z))
 first=read(pre/'FIRST_OLD_PART_HASH_VERIFICATION.json');up=read(pre/'FIRST_OLD_PART_UPLOAD_RECEIPT.json');key=first['artifact_id'],first['part_index'];assert key in q and key not in success and up['success']is True and up['parent_id']==folder['id']and up['file_name']==q[key]['file_name'];assert first['state']=='FIRST_REQUIRED_OLD_PART_UPLOADED_AND_FRESH_DOWNLOAD_HASH_VERIFIED'and first['part_bytes']==q[key]['bytes']and first['part_sha256']==q[key]['sha256'];success[key]=q[key];bindings.append(sha(pre/'FIRST_OLD_PART_HASH_VERIFICATION.json'))
 assert len(success)==15 and sum(r['bytes']for r in success.values())==296829898
 rem={k:r for k,r in q.items()if k not in success};assert len(rem)==38 and sum(r['bytes']for r in rem.values())==796917760
 failurepath=transfer/'upload-wave2-receipts/attempt-010.json';failure=read(failurepath);e=failure['provider_result']['error_data']['error'];assert failure['isError']is True and e['code']==403 and any(r['reason']=='storageQuotaExceeded'for r in e['errors'])and(failure['part']['artifact_id'],failure['part']['index'])==('V2-PRIVATE-SEASON-2022-V2',0)
 reportpath=HERE.parent/'RECOVERY_PROGRESS_CHECKPOINT_K_V2_QUOTA_STOP.json';report=read(reportpath);assert report['state']=='STOPPED_CONFIRMED_DRIVE_QUOTA_GLOBAL_FIT_GATE_CLOSED'and report['successful_receipt_sha256s']==sorted(bindings)and report['provider_error_receipt_sha256']==sha(failurepath)and report['missing_part_plan_sha256']==sha(queuepath)
 assert report['provider_successful_missing_part_uploads']==len(success)and report['provider_successful_upload_bytes']==sum(r['bytes']for r in success.values())and report['remaining_missing_upload_parts']==len(rem)and report['remaining_missing_upload_bytes']==sum(r['bytes']for r in rem.values())
 by={r['artifact_id']:r for r in report['archives']};proof=[]
 for aid in sorted(by):
  universe=[r for r in full['parts']if r['artifact_id']==aid];missing=[r for(k,i),r in rem.items()if k==aid];available=[r for r in universe if(r['artifact_id'],r['index'])not in rem];r=by[aid]
  assert(r['total_parts'],r['archive_bytes'],r['remote_parts_available'],r['missing_parts'],r['missing_bytes'])==(len(universe),sum(x['bytes']for x in universe),len(available),len(missing),sum(x['bytes']for x in missing));assert r['full_restoration_verified']is False
  for part in available:
   ref=part['provider_reference'];assert ref
   z=read(ref['upload_receipt_local_path']);assert sha(ref['upload_receipt_local_path'])==ref['upload_receipt_sha256']
   if isinstance(z,list):
    zz=next(x for x in z if x.get('index')==part['index']and x.get('status')=='UPLOADED');v=zz['response']
   else:v=z.get('provider_result',z)
   assert v.get('success')is True and v['id']==ref['provider_object_id']and v['file_name']==part['expected_remote_file_name']
  proof.append(dict(artifact_id=aid,uploaded_parts=len(available),required_parts=len(universe),missing_parts=len(missing),missing_payload_bytes=sum(x['bytes']for x in missing)))
 assert report['large_fit_gate_cleared']is False and report['whole_four_archive_restoration_verified']is False and report['quota_available_bytes']is None and report['new_NFL_fits']==0
 pointerpath=ROOT/'registries/CURRENT_RESULTS_INDEX.json';pointer=read(pointerpath);checked=[]
 for label,ref in pointer.items():
  if isinstance(ref,dict)and'path'in ref and'sha256'in ref:assert sha(ROOT/ref['path'])==ref['sha256'];checked.append(label)
 assert pointer['recovery_status']['sha256']==sha(reportpath)
 current=HERE.parent/'RECOVERY_STATUS_CURRENT_V2.md';text=current.read_text();assert '796,917,760'in text and 'quota read is unsupported'in text and 'global large-fit gate remains closed'in text and 'no further upload retries'in text
 out={'state':'PASS_INDEPENDENT_QUOTA_V2_PART_IDENTITIES_COUNTS_REJECTION_AND_POINTER','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'public_quota_receipt_sha256':sha(reportpath),'current_status_md_sha256':sha(current),'reporting_helper_sha256':sha(ROOT/'tools/record_k_quota_stop.py'),'pointer_sha256':sha(pointerpath),'pointer_hash_bindings_verified':len(checked),'unique_new_successful_parts':15,'successful_upload_payload_bytes':296829898,'remaining_required_parts':38,'remaining_required_upload_payload_bytes':796917760,'archives':proof,'provider_rejection':{'HTTP_code':403,'reason':'storageQuotaExceeded','rejected_part_bytes':20971520},'quota_or_remaining_free_capacity_measured':False,'capacity_qualification':'760MiB is the remaining upload payload, not a measured quota increment or known available balance; separately reserve future-wave output. Approved Drive owner and connected profile remain distinct.','old_global_recovery_gate_cleared':False,'delta_complete_uploads_not_yet_independently_restoration_verified_by_this_receipt':True,'generator_review':'All current successes independently require isError=false AND provider success=true, exact frozen part identity and approved parent. A successful upload is not a complete-restoration claim.','new_transfers':0,'new_scientific_calculations':0,'checker_sha256':sha(Path(__file__))}
 with(HERE/'QUOTA_STOP_V2_INDEPENDENT_REVIEW.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps({k:out[k]for k in('state','unique_new_successful_parts','remaining_required_parts','remaining_required_upload_payload_bytes','pointer_hash_bindings_verified')}))
if __name__=='__main__':main()
