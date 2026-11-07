"""Root-only, idempotent registration of retained H execution evidence.

This does not run models, grade NFL rows, or regenerate scientific results.
"""
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "reports/baselines-coverage-20261031h"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    now = datetime.now(timezone.utc).isoformat()
    event_path = ROOT / "registries/EXECUTIONS.jsonl"
    known = {json.loads(line)["run_id"] for line in event_path.read_text().splitlines() if line.strip()}
    manifest_path = ROOT / "registries/RUN_RESULT_ARTIFACT_MANIFEST.json"
    artifacts = json.loads(manifest_path.read_text())
    known_artifacts = {row["artifact_id"] for row in artifacts}
    receipts = {
        path for path in H.rglob("*.json")
        if path.name.endswith(("RECEIPT.json", "REVIEW.json"))
    }
    receipts.update(H / name for name in (
        "FROZEN_PROTOCOL.json", "RECOVERY_STATUS_REFRESH.json",
        "PUBLICATION_ENVIRONMENT.json", "CONSOLIDATED_REPORT_BINDINGS.json",
        "SOFTWARE_VERIFICATION_MANIFEST.json", "NEW_CANONICAL_SCORE_MANIFEST_V2.json",
        "owner/CURRENT_OWNER_POLICY_AND_ACTIONS.json",
        "owner-status-20261031-late-v2/OBSERVED_CAPTURE_AND_SERVED_STATUS.json",
    ))
    events, added = [], []
    for path in sorted(receipts):
        relative = path.relative_to(ROOT).as_posix()
        rid = "V2-20261031H-" + hashlib.sha256(relative.encode()).hexdigest()[:16]
        obj = json.loads(path.read_text())
        state = obj.get("state", obj.get("status", "BOUND_METADATA_SNAPSHOT"))
        if rid not in known:
            events.append(dict(
                run_id=rid, state=state, recorded_at_utc=now,
                accepted_parent="d1aa4cead94472cf5706ee91f4faf7a7ecfee6e9",
                receipt=relative, receipt_sha256=sha(path),
                actual_new_fit_calls=0, new_inference_calls=0,
                new_issued_forecasts=0, new_current2026_Week8_player_outcomes_read=0,
                production_changed_by_V2=False,
                scope="Saved-row/law lookup, temporal qualification, source-bound analysis, metadata, software or read-only owner status. Registration time is not historical execution/forecast issuance; original receipt retains its own clocks.",
            ))
        aid = rid + "-ARTIFACT"
        if aid not in known_artifacts:
            added.append(dict(
                artifact_id=aid, run_id=rid, file=relative, sha256=sha(path),
                bytes=path.stat().st_size,
                kind="bounded_execution_or_independent_or_notification_receipt",
                status=state, original=False,
                evidence_availability="PUBLIC_SAFE_SOURCE_BOUND_RECEIPT", private_locator=None,
            ))
    for source in json.loads((H / "NEW_CANONICAL_SCORE_MANIFEST_V2.json").read_text())["sources"]:
        path = ROOT / source["path"]
        assert sha(path) == source["sha256"]
        aid = "V2-H-SCORE-" + hashlib.sha256(source["path"].encode()).hexdigest()[:16]
        if aid not in known_artifacts:
            added.append(dict(
                artifact_id=aid, run_id=None, file=source["path"], sha256=source["sha256"],
                bytes=path.stat().st_size, kind="immutable_canonical_aggregate_score_source",
                status="SCORED", original=False,
                evidence_availability="PUBLIC_SAFE_AGGREGATES_PRIVATE_ROWS_SOURCE_BOUND", private_locator=None,
            ))
    with event_path.open("a") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")
    if added:
        manifest_path.write_text(json.dumps(artifacts + added, indent=2) + "\n")
        csv_path = ROOT / "registries/RUN_RESULT_ARTIFACT_MANIFEST.csv"
        with csv_path.open(newline="") as handle:
            fields = csv.DictReader(handle).fieldnames
        with csv_path.open("a", newline="") as handle:
            csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore").writerows(added)
    receipt = H / "EXECUTION_REGISTRATION_RECEIPT.json"
    if not receipt.exists():
        receipt.write_text(json.dumps(dict(
            state="ROOT_APPENDED_RETAINED_H_EVENTS",
            recorded_at_utc=now, new_events=len(events), new_manifest_rows=len(added),
            new_fits=0, new_model_inference=0, new_original_forecasts=0,
            canonical_sources=28, canonical_evaluation_views=104238,
            rolling_W5_W7_outer_thresholds=1936,
            rolling_W5_W7_qualified_threshold_actuals=1881,
            rolling_W5_W7_unknown_threshold_appearances=55,
            source_games=42, source_weeks=[5, 6, 7],
            unit_note="Overlapping methods, policies, cohorts and thresholds do not add independent NFL observations. These games are already in the fixed W1–7 numerical population.",
            resource_scope="Actual execution wall/RSS/CPU and derivative sizes remain in per-run receipts. No invented cumulative resource total for unmetered discovery/failed runs.",
            restricted_rows_published=False,
        ), indent=2) + "\n")
    print(json.dumps(dict(new_events=len(events), new_manifest_rows=len(added))))


if __name__ == "__main__":
    main()
