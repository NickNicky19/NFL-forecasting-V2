"""Finalize already prepared B forecasts against one bound native receipt.

No network, fitting, source refresh, scheduler, offers, or website writes.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from tools.capture_qb_forward_timing import ROOT, digest, event_reason, read, write_new


def main(directory, *, native_receipt='NATIVE_EVENT_RECEIPT.json', registration='FINALIZATION_REGISTRATION.json'):
    out = Path(directory).resolve()
    p = read(out / 'FROZEN_CAPTURE_PROTOCOL.json')
    reg = read(out / registration)
    prepared = read(out / 'PREPARED_FORECASTS.json.gz')
    event = read(out / native_receipt)
    now = datetime.now(timezone.utc)
    at = now.timestamp()
    if prepared['protocol_sha256'] != digest(out / 'FROZEN_CAPTURE_PROTOCOL.json'):
        raise ValueError('Prepared protocol changed')
    for b in p['bindings']:
        if digest(ROOT / b['path']) != b['sha256']:
            raise ValueError('Frozen input changed')
    if reg['finalizer_sha256'] != digest(__file__) or reg['prepared_sha256'] != digest(out / 'PREPARED_FORECASTS.json.gz'):
        raise ValueError('Finalization binding changed')
    rows = []
    for original in prepared['predictions']:
        q = original['identity']
        reason = event_reason(event, q, at)
        if reason:
            raise ValueError(reason)
        model = ROOT / original['model_path']
        if digest(model) != original['model_sha256'] or datetime.fromisoformat(read(model)['fit_completed_utc']).timestamp() > at:
            raise ValueError('Current model changed or not yet available')
        row = dict(original, actual_issued_UTC=now.isoformat(),
            original_pregame_forecast='mean' in original,
            basic_unavailable_record='mean' not in original, original_website_selection=False,
            issue_scope='B_OWNER_RESEARCH_SHADOW_CONDITIONAL_APPEARANCE;NO_OFFER_OR_PICK',
            prepared_record_sha256=hashlib.sha256(json.dumps(original, sort_keys=True, allow_nan=False).encode()).hexdigest())
        if 'mean' in row:
            row['status'] = 'ISSUED_FUTURE_FORECAST_ONLY_SHADOW'
        rows.append(row)
    packet = dict(id=reg['capture_id'], issue_UTC=now.isoformat(), feature_cutoff=p['feature_cutoff'],
        horizon=p['horizon'], event=event, protocol_sha256=digest(out / 'FROZEN_CAPTURE_PROTOCOL.json'),
        prepared_sha256=digest(out / 'PREPARED_FORECASTS.json.gz'), forecasts=rows,
        source_admission='EXISTING_PUBLIC_C_FACTUAL_PROJECTION;ONLY2RECENT_FINAL_GAMES;13HELD;CURRENT_KNOWN_BASIC_QB_ROLE',
        expected_starters='UNKNOWN_NOT_INFERRED', transaction_effective_clocks='UNKNOWN_NOT_FILLED',
        outcomes='FUTURE_UNKNOWN_NOT_GRADED', offers=0, actual_line_selections=0,
        original_website_consumer='NOT_DELIVERED_OR_ADMITTED', primary_switch=False,
        later_line_use='REQUIRES_SEPARATE_EXPLICIT_PREGAME_REPRICING_HORIZON_WITH_BOTH_CLOCKS;NOT_ORIGINAL_SELECTION',
        historical_information_policy='CURRENT_SOURCE_REVISED_HISTORICAL_FEATURE_RECONSTRUCTION;NO_AUTHENTICATED_HISTORICAL_VINTAGE_CLAIM')
    write_new(out / 'FORECASTS.json.gz', packet)
    write_new(out / 'LOCAL_CAPTURE_RECEIPT.json', dict(id=reg['capture_id'],
        state='ISSUED_AND_LOCALLY_PERSISTED;GITHUB_READBACK_PENDING',
        issued_UTC=now.isoformat(), local_persistence_completed_UTC=datetime.now(timezone.utc).isoformat(),
        packet_path=str((out / 'FORECASTS.json.gz').relative_to(ROOT)), packet_sha256=digest(out / 'FORECASTS.json.gz'),
        native_event_sha256=digest(out / native_receipt),
        forecast_count=sum('mean' in r for r in rows), basic_unavailable_records=sum('mean' not in r for r in rows),
        players=8, forecast_players=5, methods=2, actual_offers=0, actual_selections=0, new_graded_outcomes=0,
        resources=prepared['resources'], finalizer_sha256=digest(__file__),
        capture_owner='B owner-local research', production_owner='Original-site owner unchanged',
        source_expiry='Event receipt expiry governs new issuance, not erasure of this frozen earlier packet; later source/model/offer use requires revalidation',
        release='SHADOW_ONLY_NOT_PRIMARY_OR_TOP_PICKS'))
    print(json.dumps(dict(capture_id=reg['capture_id'], issued_UTC=now.isoformat(),
        forecasts=sum('mean' in r for r in rows), offers=0, selections=0, local_only_pending_publication=True)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('directory')
    ap.add_argument('--native-receipt', default='NATIVE_EVENT_RECEIPT.json')
    ap.add_argument('--registration', default='FINALIZATION_REGISTRATION.json')
    args = ap.parse_args()
    main(args.directory, native_receipt=args.native_receipt, registration=args.registration)
