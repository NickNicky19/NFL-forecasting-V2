"""Root-only append of bounded J software and owner-observation receipts.

This does not fit, forecast, grade, restore or admit a production procedure.
"""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = (
    'reports/defense-season-executor-20261031j-code',
    'reports/owner-runtime-refresh-20261031j',
)


def main():
    ledger = ROOT / 'registries/EXECUTIONS.jsonl'
    known = {json.loads(line)['run_id'] for line in ledger.read_text().splitlines() if line.strip()}
    manifest = ROOT / 'registries/RUN_RESULT_ARTIFACT_MANIFEST.json'
    old = json.loads(manifest.read_text())
    known_artifacts = {row['artifact_id'] for row in old}
    stamp = datetime.now(timezone.utc).isoformat()
    events, artifacts = [], []
    for folder in FOLDERS:
        base = ROOT / folder
        if not base.exists():
            continue
        for path in sorted(base.rglob('*.json')):
            if any(part.startswith('results-index') for part in path.parts) or path.name.startswith('new-records-'):
                continue
            relative = path.relative_to(ROOT).as_posix()
            raw = path.read_bytes()
            value = json.loads(raw)
            state = (value.get('state', value.get('status', 'BOUND_CODE_OR_OBSERVATION_METADATA'))
                     if isinstance(value, dict) else 'BOUND_CODE_OR_OBSERVATION_METADATA')
            digest = hashlib.sha256(raw).hexdigest()
            rid = 'V2-20261031J-' + hashlib.sha256(relative.encode()).hexdigest()[:16]
            if rid not in known:
                events.append(dict(
                    run_id=rid, recorded_at_utc=stamp, state=state,
                    receipt=relative, receipt_sha256=digest,
                    actual_new_V2_NFL_fit_calls=0, new_V2_model_inference_calls=0,
                    new_V2_original_forecast_captures=0, new_V2_NFL_outcome_scores=0,
                    production_changed_by_V2=False,
                    scope='J software checks and permitted owner-state observations. Owner capture is separately attributed in its evidence; zero V2 calls does not assert zero owner calls. No new historical fit, original selection, source restoration or release admission.'))
            aid = rid + '-ARTIFACT'
            if aid not in known_artifacts:
                artifacts.append(dict(
                    artifact_id=aid, run_id=rid, file=relative, sha256=digest,
                    bytes=len(raw), kind='bounded_J_code_or_owner_state_receipt',
                    status=state, original=False,
                    evidence_availability='PUBLIC_SAFE_CODE_TEST_OR_OBSERVATION_METADATA',
                    private_locator=None))
    with ledger.open('a') as handle:
        for event in events:
            handle.write(json.dumps(event) + '\n')
    if artifacts:
        manifest.write_text(json.dumps(old + artifacts, indent=2) + '\n')
        target = ROOT / 'registries/RUN_RESULT_ARTIFACT_MANIFEST.csv'
        with target.open(newline='') as handle:
            fields = csv.DictReader(handle).fieldnames
        with target.open('a', newline='') as handle:
            csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore').writerows(artifacts)
    print(json.dumps(dict(new_receipt_events=len(events), new_artifact_rows=len(artifacts),
                          new_V2_NFL_fits=0, new_NFL_grades=0)))


if __name__ == '__main__':
    main()
