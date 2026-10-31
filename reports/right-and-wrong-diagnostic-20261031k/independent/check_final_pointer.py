"""Final K pointer/retention readback only; no scientific recalculation."""
import hashlib,json
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 pointerpath=ROOT/'registries/CURRENT_RESULTS_INDEX.json';pointer=read(pointerpath);bindings=[]
 for label,ref in pointer.items():
  if isinstance(ref,dict)and'path'in ref and'sha256'in ref:
   path=Path(ref['path']);assert not path.is_absolute()and'..'not in path.parts;assert sha(ROOT/path)==ref['sha256'];bindings.append(dict(label=label,path=path.as_posix(),sha256=ref['sha256']))
 assert len(bindings)==25
 own=read(HERE/'FINAL_K_INDEX_AND_METADATA_REVIEW.json');indexpath=ROOT/pointer['manifest'];index=read(indexpath);assert sha(indexpath)==own['index_manifest_sha256']=='29a4f9a2698eccfa84dbfff8a6f278ec4c5509aa68623b5a15075405ca263b2e';assert index['record_count']==565871
 parentpath=ROOT/pointer['previous_checkpoint'];parent=read(parentpath);assert sha(parentpath)==own['prior_J_manifest_sha256'] and parent['record_count']==557818
 assert index['shards'][:len(parent['shards'])]==parent['shards']and index['csv_parts'][:len(parent['csv_parts'])]==parent['csv_parts'];assert len(parent['shards'])==409 and len(parent['csv_parts'])==60 and len(index['shards'])==414 and len(index['csv_parts'])==61
 assert pointer['right_wrong_readable']['sha256']==own['final_readable_sha256']=='a591f3ddfeef0f44e839896ce1f99c6aa958f8c8b6a73fcf0b00f62bc1b5ba49'
 assert pointer['right_wrong_artifact_bindings']['sha256']==own['final_binding_sha256']=='1ce37b5dc28a05fda015e7723b10de5b6580f0d4289391d4f076c0517364eca4'
 retention=read(ROOT/pointer['right_wrong_private_retention']['path']);independent=read(HERE/'K_BUNDLE_RESTORATION_REVIEW.json');assert retention['state']=='VERIFIED_FRESH_DOWNLOAD_WHOLE_AND_ALL_INNER_BYTES'and retention['all_inner_bytes_equal_to_original']is True and retention['download_sha256']==independent['archive_sha256']and retention['download_bytes']==5362879 and retention['global_old_recovery_gate_cleared']is False
 progress=read(ROOT/pointer['recovery_status']['path']);assert progress['state']=='OLD_MISSING_ONLY_TRANSFER_ACTIVE_GATE_CLOSED'and progress['large_fit_gate_cleared']is False and progress['whole_four_archive_restoration_verified']is False
 assert progress['original_missing_parts']==progress['provider_successful_missing_part_uploads']+progress['remaining_missing_upload_parts']==53
 assert progress['original_missing_bytes']==progress['provider_successful_upload_bytes']+progress['remaining_missing_upload_bytes']==1093747658
 assert progress['checked_at_utc']=='2026-10-31T20:43:27.082423+00:00'and progress['quota_available_bytes']is None and progress['new_NFL_fits']==0
 addendum=HERE.parent/'RETENTION_UPDATE_20261031.md';text=addendum.read_text();assert 'assembly time'in text and 'do not clear the older global recovery gate'in text and 'no newfitworker'in text
 out={'state':'PASS_FINAL_K_POINTER_REPORT_INDEX_AND_NEW_K_RETENTION_BINDINGS','at_utc':datetime.now(timezone.utc).isoformat(),'pointer_sha256':sha(pointerpath),'hash_bound_pointer_targets':bindings,'hash_bound_pointer_target_count':25,'index_manifest_sha256':sha(indexpath),'index_records':565871,'prior_records':557818,'unchanged_prior_JSON_shards':409,'unchanged_prior_CSV_parts':60,'new_diagnostic_views':8052,'new_software_records':1,'scientific_rows_or_metrics_replayed':0,'earlier_independent_index_math_receipt_sha256':sha(HERE/'FINAL_K_INDEX_AND_METADATA_REVIEW.json'),'new_K_bundle_restoration_independent_receipt_sha256':sha(HERE/'K_BUNDLE_RESTORATION_REVIEW.json'),'retention_addendum_sha256':sha(addendum),'old_recovery_progress_snapshot_at_utc':progress['checked_at_utc'],'old_recovery_snapshot_arithmetic_verified':True,'old_upload_provenance_scope':'Counts are the root reported time-qualified progress snapshot; actual64-part provider chains and complete four-archive/all-member restoration remain a separately pending review. This is not a current-count refresh or full gate pass.','whole_old_global_gate_cleared':False,'new_K_only_restored':True,'quota_or_remaining_capacity_verified':False,'rankings_and_release_status':'Existing numerical/probability/selection champions remain unchanged.8052 new outcome-conditioned diagnostic views are not championship candidates; no production admission or worker release follows.','new_external_transfers':0,'new_model_calls':0,'checker_sha256':sha(Path(__file__))}
 with(HERE/'FINAL_POINTER_REPORT_AND_K_RETENTION_REVIEW.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print(json.dumps({k:out[k]for k in('state','pointer_sha256','hash_bound_pointer_target_count','index_records','whole_old_global_gate_cleared')}))
if __name__=='__main__':main()
