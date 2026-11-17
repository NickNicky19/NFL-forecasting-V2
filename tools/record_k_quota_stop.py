"""Publish safe, receipt-derived K recovery progress; no provider mutations."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'reports/right-and-wrong-diagnostic-20261031k'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(private_root):
    preflight = private_root / 'right-wrong-20261031k-missing-only-preflight'
    transfer = private_root / 'old-recovery-20261031k'
    queue_path = preflight / 'REQUIRED_MISSING_PART_QUEUE.json'
    queue = json.loads(queue_path.read_text())
    complete = json.loads((preflight / 'ALL_COMPLETE_PARTS_FETCH_QUEUE_V1.json').read_text())['parts']
    successes = {}
    bindings = []
    for pattern in ('upload-receipts/*.json', 'upload-wave2-receipts/*.json',
                    'ISOLATED_RETRY_AFTER_INTERNAL_ERROR.json'):
        for path in sorted(transfer.glob(pattern)):
            receipt = json.loads(path.read_text())
            if receipt.get('isError') is False:
                part = receipt['part']
                successes[part['artifact_id'], part['index']] = part
                bindings.append(sha(path))
    first_path = preflight / 'FIRST_OLD_PART_HASH_VERIFICATION.json'
    first = json.loads(first_path.read_text())
    assert first['state'] == 'FIRST_REQUIRED_OLD_PART_UPLOADED_AND_FRESH_DOWNLOAD_HASH_VERIFIED'
    first_part = next(p for p in queue if p['artifact_id'] == first['artifact_id'] and p['index'] == 12)
    successes[first_part['artifact_id'], first_part['index']] = first_part
    bindings.append(sha(first_path))
    failure_path = transfer / 'upload-wave2-receipts/attempt-010.json'
    failure = json.loads(failure_path.read_text())
    assert failure['isError'] is True and 'storageQuotaExceeded' in json.dumps(failure)
    assert len(successes) == 15 and sum(p['bytes'] for p in successes.values()) == 296829898
    remaining = [p for p in queue if (p['artifact_id'], p['index']) not in successes]
    assert len(remaining) == 38 and sum(p['bytes'] for p in remaining) == 796917760
    archives = []
    for artifact in sorted({p['artifact_id'] for p in complete}):
        parts = [p for p in complete if p['artifact_id'] == artifact]
        missing = [p for p in remaining if p['artifact_id'] == artifact]
        archives.append(dict(artifact_id=artifact, total_parts=len(parts),
            archive_bytes=sum(p['bytes'] for p in parts),
            remote_parts_available=len(parts)-len(missing),
            missing_parts=len(missing), missing_bytes=sum(p['bytes'] for p in missing),
            restoration_state='FRESH_FULL_DOWNLOAD_AND_MEMBER_VERIFICATION_IN_PROGRESS' if not missing
                else 'PARTIAL_REMOTE_LOCAL_ORIGINALS_PRESERVED',
            full_restoration_verified=False))
    receipt = dict(state='STOPPED_CONFIRMED_DRIVE_QUOTA_GLOBAL_FIT_GATE_CLOSED',
        checked_at_utc=datetime.now(timezone.utc).isoformat(),
        supersedes_progress_snapshot='RECOVERY_PROGRESS_CHECKPOINT_K_V1.json',
        original_missing_parts=len(queue), original_missing_bytes=sum(p['bytes'] for p in queue),
        provider_successful_missing_part_uploads=len(successes),
        provider_successful_upload_bytes=sum(p['bytes'] for p in successes.values()),
        remaining_missing_upload_parts=len(remaining), remaining_missing_upload_bytes=sum(p['bytes'] for p in remaining),
        minimum_additional_capacity_bytes=796917760,
        additional_new_wave_retention_reservation_bytes=None,
        provider_error=dict(code=403, reason='storageQuotaExceeded', rejected_part_bytes=failure['part']['bytes']),
        provider_error_receipt_sha256=sha(failure_path),
        successful_receipt_sha256s=sorted(bindings), missing_part_plan_sha256=sha(queue_path),
        archives=archives, new_K_bundle_restoration_verified=True,
        whole_four_archive_restoration_verified=False, large_fit_gate_cleared=False,
        quota_available_bytes=None,
        quota_identity_qualification='Connected profile and Drive owner differ; uploaded owner matches approved folder owner. No supported quantitative quota reading. Explicit write rejection establishes exhaustion for that upload.',
        next_owner_action='Make at least 796917760 additional bytes available to the actual uploading Drive owner in the approved destination, plus a separately reserved new-wave budget; or provide an owner-approved capacity solution. No purchase, deletion, sharing or destination change authorized.',
        retry_policy='No more uploads without meaningful capacity/account/provider-state change. Preserve every successful part and local original. Finish readback only for the now-complete delta archive.',
        privacy_or_sharing_changes=0, new_NFL_fits=0,
        scope='Transfer status is not restoration. The delta verification result will be a separate immutable receipt; the other three archives remain incomplete.')
    path = BASE / 'RECOVERY_PROGRESS_CHECKPOINT_K_V2_QUOTA_STOP.json'
    assert not path.exists()
    path.write_text(json.dumps(receipt, indent=2)+'\n')
    pointer = ROOT / 'registries/CURRENT_RESULTS_INDEX.json'
    current = json.loads(pointer.read_text())
    current['recovery_status'] = dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path))
    pointer.write_text(json.dumps(current, indent=2)+'\n')
    print(json.dumps(dict(state=receipt['state'], successful_parts=len(successes),
        remaining_parts=len(remaining), remaining_bytes=receipt['remaining_missing_upload_bytes'],
        public_receipt=path.relative_to(ROOT).as_posix())))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--private-root', type=Path, required=True)
    main(parser.parse_args().private_root)
