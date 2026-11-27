"""Root-only append of source-bound I execution and correction receipts."""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'reports/point-prop-diagnostic-20261031i'


def main():
    ledger = ROOT / 'registries/EXECUTIONS.jsonl'
    known = {json.loads(line)['run_id'] for line in ledger.read_text().splitlines() if line.strip()}
    path = ROOT / 'registries/RUN_RESULT_ARTIFACT_MANIFEST.json'
    artifacts = json.loads(path.read_text())
    known_artifacts = {row['artifact_id'] for row in artifacts}
    receipts = {item for item in FOLDER.rglob('*.json')
                if item.name.endswith(('RECEIPT.json', 'REVIEW.json')) or 'FAILED_ATTEMPT' in item.name}
    receipts.update(FOLDER / name for name in (
        'FROZEN_PROTOCOL.json', 'ENVIRONMENT_AND_SCOPE.json', 'RECOVERY_AND_EXPORT_ACCESS_REFRESH.json',
        'FRESH_SERVED_BYTE_STATUS.json', 'FUTURE_CAPTURE_AND_RELEASE_STATUS.json',
        'NEW_CANONICAL_SCORE_MANIFEST_I_V2.json', 'SOFTWARE_VERIFICATION_MANIFEST_V2.json',
        'INDEX_STAGING_V1_INVALIDATION.json', 'INDEX_STAGING_V2_SCOPE_NOTE.json',
        'METADATA_SCHEMA_FAILURES_V1.json', 'REPORT_SOURCE_BINDINGS_I_V1.json',
    ))
    now = datetime.now(timezone.utc).isoformat()
    events, added = [], []
    for item in sorted(receipts):
        relative = item.relative_to(ROOT).as_posix()
        rid = 'V2-20261031I-' + hashlib.sha256(relative.encode()).hexdigest()[:16]
        obj = json.loads(item.read_text())
        state = obj.get('state', obj.get('status', 'BOUND_EXECUTION_OR_METADATA_RECEIPT'))
        digest = hashlib.sha256(item.read_bytes()).hexdigest()
        if rid not in known:
            events.append(dict(run_id=rid, recorded_at_utc=now, state=state,
                               receipt=relative, receipt_sha256=digest,
                               actual_new_NFL_fit_calls=0, new_model_inference_calls=0,
                               new_original_forecast_captures=0, new_NFL_observations=0,
                               production_changed_by_V2=False,
                               scope='Per-receipt original execution clocks/resources retained; registration is not forecast issuance. Numerical startup and point diagnostics reuse old forecasts. Precision versions and failed metadata stages are separate.'))
        aid = rid + '-ARTIFACT'
        if aid not in known_artifacts:
            added.append(dict(artifact_id=aid, run_id=rid, file=relative, sha256=digest,
                              bytes=item.stat().st_size, kind='bounded_I_execution_independent_or_metadata_receipt',
                              status=state, original=False, evidence_availability='PUBLIC_SAFE_SOURCE_BOUND_RECEIPT', private_locator=None))
    for source in json.loads((FOLDER / 'NEW_CANONICAL_SCORE_MANIFEST_I_V2.json').read_text())['sources']:
        item = ROOT / source['path']
        assert hashlib.sha256(item.read_bytes()).hexdigest() == source['sha256']
        aid = 'V2-I-SCORE-' + hashlib.sha256(source['path'].encode()).hexdigest()[:16]
        if aid not in known_artifacts:
            added.append(dict(artifact_id=aid, run_id=None, file=source['path'], sha256=source['sha256'],
                              bytes=item.stat().st_size, kind='immutable_I_canonical_aggregate_scores_or_scoring_replacement',
                              status='SCORED_WITH_EXPLICIT_PRECISION_SUPERSESSION_WHERE_APPLICABLE', original=False,
                              evidence_availability='PUBLIC_SAFE_AGGREGATES_RETAINED_PRIVATE_INPUTS', private_locator=None))
    with ledger.open('a') as handle:
        for event in events:
            handle.write(json.dumps(event) + '\n')
    if added:
        path.write_text(json.dumps(artifacts + added, indent=2) + '\n')
        target = ROOT / 'registries/RUN_RESULT_ARTIFACT_MANIFEST.csv'
        with target.open(newline='') as handle:
            fields = csv.DictReader(handle).fieldnames
        with target.open('a', newline='') as handle:
            csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore').writerows(added)
    print(json.dumps(dict(new_execution_events=len(events), new_artifact_rows=len(added), new_NFL_fits=0)))


if __name__ == '__main__':
    main()
