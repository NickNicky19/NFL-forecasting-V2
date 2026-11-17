"""Shared positive fresh-restoration gate for the frozen expanded content plan.

Public safe IDs/digests identify scientific bytes; no storage locators or uploads.
Capacity declarations and index digests never authenticate restoration.
"""
import json
from datetime import datetime,timezone
from pathlib import Path
from .hgb_control import sha
GATE_STATE='PASS_ALL_REQUIRED_FRESH_RESTORATION'
EXPECTED_PLAN_SHA256='7ce075fc7b853a646f79795bb7133b597ee5dbeaa6cb7f5f21240e8cd8d516de'
EXPECTED_CONTENT_REVIEW_SHA256='35d06f8c42287ab4783ec38799aa788bbb2e6b73e1cd4bd48e307f77c1877a67'
EXPECTED_MAP_REVIEW_SHA256='029a7fa1b6352c9b3916375399928600d059836970c6e20eec5ba4111adce36d'
EXPECTED_PRIOR_ALLOWLIST_SHA256='3ec50fe9832b4a68fabf75677e08e8125ebb3f2009071fa26b4b26cd93703d8b'
EXPECTED_PRIVATE_MAP_SHA256='e592881a6495ad097b31667daaa12229f0837b0bec6ff390386387df01f7a1ad'
EXPECTED_PENDING_IDS={'V2-PRIVATE-SEASON-2024-V2','V2-PRIVATE-SEASON-2023-COMPLETE-V1','V2-PRIVATE-SEASON-2022-V2','V2-PRIVATE-RECOVERY-DELTA-20261030D-0001'}
POSITIVE_PROOF_STATES={'FRESH_PRIVATE_RESTORE_ALL_PARTS_AND_INNER_FILES_VERIFIED','FRESH_OWNER_ONLY_RESTORE_ALL_MEMBERS_VERIFIED','RESTORED_AND_ALL_INNER_MEMBERS_VERIFIED','RESTORED_ALL_PARTS_AND_INNER_FILES_VERIFIED','FULL_ARCHIVE_FRESH_RESTORED_AND_ALL_INNER_MEMBERS_VERIFIED','FRESH_ALL_REQUIRED_ARCHIVES_RESTORED'}

def public_bound(reference,repository):
 name=reference.get('path','');relative=Path(name)
 if relative.is_absolute()or '..'in relative.parts or not name.startswith('reports/'):raise ValueError('PUBLIC_SAFE_PROOF_PATH_REQUIRED')
 file=Path(repository)/relative
 if sha(file)!=reference.get('sha256'):raise ValueError('PUBLIC_PROOF_HASH')
 return json.loads(file.read_text())

def _require_retention(path,repository):
 if path is None or not Path(path).is_file():raise ValueError('FRESH_RETENTION_GATE_MISSING')
 r=json.loads(Path(path).read_text())
 if r.get('state')!=GATE_STATE or r.get('all_required_archives_verified')is not True or r.get('all_required_members_verified')is not True or r.get('missing_required_parts')!=0:raise ValueError('FRESH_REQUIRED_RETENTION_NOT_VERIFIED')
 try:completed=datetime.fromisoformat(r['completed_at_utc'].replace('Z','+00:00'))
 except(KeyError,TypeError,ValueError)as exc:raise ValueError('AWARE_ACTUAL_RETENTION_COMPLETION_CLOCK_REQUIRED')from exc
 if completed.tzinfo is None or completed.utcoffset()is None or completed>datetime.now(timezone.utc):raise ValueError('AWARE_NONFUTURE_RETENTION_COMPLETION_CLOCK_REQUIRED')
 if r.get('recovery_plan',{}).get('sha256')!=EXPECTED_PLAN_SHA256 or r.get('content_plan_review',{}).get('sha256')!=EXPECTED_CONTENT_REVIEW_SHA256 or r.get('map_encoding_review',{}).get('sha256')!=EXPECTED_MAP_REVIEW_SHA256 or r.get('accepted_prior_proof_allowlist',{}).get('sha256')!=EXPECTED_PRIOR_ALLOWLIST_SHA256:raise ValueError('EXACT_QUALIFIED_RECOVERY_SNAPSHOT_REQUIRED')
 plan=public_bound(r['recovery_plan'],repository);review=public_bound(r['content_plan_review'],repository);encoding=public_bound(r['map_encoding_review'],repository);prior=public_bound(r['accepted_prior_proof_allowlist'],repository)
 if completed<datetime.fromisoformat(plan['cutoff_utc'].replace('Z','+00:00')):raise ValueError('RETENTION_COMPLETION_PRECEDES_FROZEN_SCOPE')
 if review.get('positive_allowlist_sha256')!=EXPECTED_PRIOR_ALLOWLIST_SHA256 or len(prior.get('entries',[]))!=20 or review.get('positive_used_object_proofs')!=20:raise ValueError('TWENTY_INDEPENDENTLY_QUALIFIED_PRIOR_OBJECTS_REQUIRED')
 if review.get('private_map_sha256')!=EXPECTED_PRIVATE_MAP_SHA256 or plan.get('required_file_paths')!=29527 or plan.get('required_unique_content_hashes')!=20217 or plan.get('new_delta_unique_files')!=1787 or review.get('delta_unique_file_blobs')!=1787:raise ValueError('FROZEN_EXPANDED_CONTENT_SCOPE_REQUIRED')
 if review.get('state')!='PASS_EXPANDED_CONTENT_RECOVERY_PLAN_WITH_POSITIVE_PROOF_SUPPLEMENT'or review.get('status_artifact_sha256')!=r['recovery_plan']['sha256']:raise ValueError('QUALIFIED_FROZEN_RECOVERY_PLAN_REQUIRED')
 if encoding.get('state')!='PASS_DISTINCT_EXTERNAL_AND_ARCHIVE_MAP_BYTE_BINDINGS'or encoding.get('semantic_objects_identical')is not True:raise ValueError('QUALIFIED_MAP_ENCODING_REQUIRED')
 if review.get('private_map_sha256')!=encoding.get('external_private_map_sha256')or r.get('covered_private_map_sha256')!=review.get('private_map_sha256'):raise ValueError('FROZEN_PRIVATE_FILE_MAP_BINDING')
 if r.get('covered_path_aliases')!=plan.get('required_file_paths')or r.get('covered_unique_content_hashes')!=plan.get('required_unique_content_hashes')or review.get('required_path_aliases')!=plan.get('required_file_paths')or review.get('unique_content_hashes')!=plan.get('required_unique_content_hashes'):raise ValueError('COMPLETE_FROZEN_SCIENTIFIC_FILE_COVERAGE_REQUIRED')
 pending={x['artifact_id']:x for x in plan.get('archives',[])if x.get('missing_parts',0)>0}
 if set(pending)!=EXPECTED_PENDING_IDS or sum(x['missing_parts']for x in pending.values())!=53:raise ValueError('FOUR_ARCHIVE_53_PART_SCIENTIFIC_PLAN_REQUIRED')
 delta=[x for x in pending.values()if x['archive_sha256']==review.get('delta_archive_sha256')]
 if len(delta)!=1 or encoding.get('delta_archive_sha256')!=delta[0]['archive_sha256']:raise ValueError('FROZEN_DELTA_ARCHIVE_BINDING')
 proofs=r.get('proof_receipts')
 if not isinstance(proofs,list):raise ValueError('POSITIVE_SOURCE_RESTORATION_PROOFS_REQUIRED')
 qualified={}
 for item in proofs:
  ident=item.get('artifact_id');proof=public_bound(item,repository);state=proof.get('status',proof.get('state'))
  if ident in qualified or proof.get('artifact_id')!=ident:raise ValueError('RESTORATION_ARTIFACT_IDENTITY')
  if state not in POSITIVE_PROOF_STATES:raise ValueError('POSITIVE_COMPLETE_RESTORATION_STATE_REQUIRED')
  if ident not in pending:continue
  expected=pending[ident]
  if proof.get('archive_sha256')!=expected['archive_sha256']or proof.get('archive_bytes')!=expected['archive_bytes']:raise ValueError('FRESH_ARCHIVE_CONTENT_DIGEST_MUST_MATCH_FROZEN_PLAN')
  count=proof.get('archive_member_count_verified',proof.get('inner_file_checks',0)+proof.get('manifest_file_extra',0))
  if not isinstance(count,int)or count<=0 or count!=expected.get('inner_files'):raise ValueError('ALL_ARCHIVE_MEMBERS_MUST_MATCH_FROZEN_PLAN')
  if proof.get('full_archive_fresh_restoration_verified')is False or proof.get('missing_parts',0)!=0:raise ValueError('PARTIAL_RESTORATION_REJECTED')
  qualified[ident]=proof
 if set(qualified)!=set(pending):raise ValueError('ALL_PENDING_SCIENTIFIC_RECOVERY_ARCHIVES_REQUIRED')
 return r


def require_retention(path,repository):
 """Return only the exact reviewed full-plan positive gate, fail closed."""
 try:return _require_retention(path,repository)
 except(KeyError,TypeError,AttributeError)as exc:raise ValueError('MALFORMED_RECOVERY_GATE_OR_PROOF')from exc
