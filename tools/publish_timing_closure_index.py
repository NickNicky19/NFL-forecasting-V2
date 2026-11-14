"""Bind already retained B timing-closure members; no scoring or acquisition."""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('reports/profile-timing-closure-confirm-01/B')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def save(path, value):
    (ROOT / path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main():
    manifest_path = BASE / 'PUBLICATION_MANIFEST_V2.json'
    if (ROOT / manifest_path).exists():
        raise ValueError('Publication already frozen; append a version instead')
    head = git('rev-parse', 'HEAD')
    paths = git('ls-files', str(BASE)).splitlines()
    paths += ['tools/capture_qb_forward_timing.py', 'tools/finalize_qb_forward_timing.py',
              'tools/publish_timing_closure_index.py']
    records = []
    for path in sorted(set(paths)):
        body = (ROOT / path).read_bytes()
        committed = subprocess.check_output(['git', 'show', head + ':' + path], cwd=ROOT)
        if body != committed:
            raise ValueError('Member has uncommitted changes: ' + path)
        producer = git('log', '-1', '--format=%H', '--', path)
        records.append(dict(path=path, producer_commit=producer, sha256=sha(body), bytes=len(body),
            retrieval_url='https://raw.githubusercontent.com/NickNicky19/NFL-forecasting-V2/' + producer + '/' + path,
            readback_verified=False, state='COMMITTED_MEMBER_EXPECTING_EXACT_REMOTE_READBACK'))
    # The actual original finalizer is part of the immutable capture recipe;
    # its later metadata-only correction must not replace that runtime pin.
    original_path = 'tools/finalize_qb_forward_timing.py'
    original_commit = 'c3199e20149d018eda55eba6528ea27d0f859a5d'
    body = subprocess.check_output(['git', 'show', original_commit + ':' + original_path], cwd=ROOT)
    records.append(dict(path=original_path, producer_commit=original_commit, sha256=sha(body), bytes=len(body),
        retrieval_url='https://raw.githubusercontent.com/NickNicky19/NFL-forecasting-V2/' + original_commit + '/' + original_path,
        readback_verified=True, state='ORIGINAL_CAPTURE_RUNTIME_PRESERVED_AND_ALREADY_READ_BACK'))
    clock = datetime.now(timezone.utc).isoformat()
    manifest = dict(id='B-TIMING-CLOSURE-PUBLICATION-MEMBERS-v2', at_UTC=clock,
        binding_head=head, repository='NickNicky19/NFL-forecasting-V2', members=records,
        rights=dict(analysis='Existing approved factual-derivative/code/aggregate scope',
            export='Permitted B public artifacts; no restricted A/B board rows or locators',
            retention='GitHub immutable bytes; protected recovery obligations unchanged',
            publication='Own repository only; no original-site admission or activation'),
        artifact_count=len(records), bytes_with_versions=sum(r['bytes'] for r in records),
        current_origin_fits_already_recorded=2, repeated_historical_fits=0,
        original_forecasts_already_recorded=10, original_selections=0,
        new_scored_weeks=0, new_scientific_score_views=0,
        canonical_packet=dict(producer_commit='b046aab1877e5fb0412864d215a40df1c722a2df',
            path=str(BASE / 'forward-current-v1/FORECASTS_METADATA_V2.json'),
            sha256=sha((ROOT / BASE / 'forward-current-v1/FORECASTS_METADATA_V2.json').read_bytes())),
        admission='C admitted listed earlier timing-side arithmetic only; new capture and private joins remain separate',
        remote_readback='Separate append-only receipt must verify these exact members after publication')
    path = ROOT / 'reports/abc-championship/EXPORT_INDEX.json'
    old = json.loads(path.read_text())
    if old.get('profile_timing_closure_confirm_01'):
        raise ValueError('Existing timing-closure export version requires reconciliation')
    original_entries = list(old['exports'])
    entries = []
    for r in records:
        artifact_id = 'B-EXPORT-' + sha((r['producer_commit'] + '\0' + r['path'] + '\0' + r['sha256']).encode())[:16]
        if any(e.get('artifact_id') == artifact_id for e in old['exports']):
            continue
        kind = ('TRUSTED_TYPED_PUBLIC_CURRENT_SHADOW_MODEL' if '/models/' in r['path'] else
                'ORIGINAL_FORECAST_OR_OUTPUT_PRESERVING_METADATA_VERSION' if 'FORECASTS' in r['path'] else
                'PERMITTED_PUBLIC_FACTUAL_DERIVATIVE' if 'INPUTS' in r['path'] else
                'PUBLIC_CODE' if r['path'].endswith('.py') else 'PUBLIC_TECHNICAL_REPORT_OR_RECEIPT')
        entries.append(dict(artifact_id=artifact_id, **r, kind=kind,
            rights='Existing permitted public facts, own trusted JSON/code and aggregates; no restricted rows',
            retention='IMMUTABLE_GITHUB_MEMBERS;EXACT_READBACK_RECEIPT_SEPARATE',
            admission='OWNER_LOCAL_VALIDATED;C_ARTIFACT_SPECIFIC_ADMISSION_ONLY',
            periods='2026W10_FUTURE_UNGRADED' if '/forward-current-' in r['path'] else 'SEE_EXACT_BOUND_ARTIFACT',
            missing_dependencies='New exact A joins registered, not scored in inspected receipts; new capture not site-admitted.'))
    old['schema_version'] = 'B-ABC-EXPORT-INDEX-v15'
    old['at_utc'] = clock
    old['canonical_state'] = ('C_REMAINS_COORDINATOR;B_TIMING_LISTED_SIDE_ARITHMETIC_ADMITTED;'
        'A_EXACT_NEW_JOINS_REGISTERED_NOT_EXECUTION_VERIFIED;NEW_FORWARD_NOT_SITE_ADMITTED')
    old['exports'].extend(entries)
    assert old['exports'][:len(original_entries)] == original_entries
    old['profile_timing_closure_confirm_01'] = dict(
        report=str(BASE / 'RESUMPTION_CLOSURE_V1.md'),
        historical_checkpoint=str(BASE / 'TIMING_CLOSURE_CHECKPOINT_V1.md'),
        publication_manifest=str(manifest_path), binding_head=head,
        canonical_packet=manifest['canonical_packet'],
        exact_new_A_joins='ACKNOWLEDGED_REGISTERED_PREEXEC_CHECKED;NO_SCORING_RECEIPT_OBSERVED',
        C_admission='Earlier listed B timing own-side arithmetic only; new capture/receipts require exact intake',
        source_and_private_row_parity='UNKNOWN_OR_SCOPE_LIMITED;no public aggregate implies row transfer',
        capture=dict(id='B-F0-F2-20261110-W10-FIRST-01', issued_UTC='2026-11-10T23:01:29.145519+00:00',
            original_commit=original_commit, forecasts=10, basic_unavailable_records=6,
            offers=0, selections=0, graded_outcomes=0, reissued_after_outage=False),
        all_previous_exports_preserved=len(original_entries), added_exports=len(entries),
        production_changes=0, new_scored_weeks=0, no_new_lag_search=True)
    save(manifest_path, manifest)
    save(Path('reports/abc-championship/EXPORT_INDEX.json'), old)
    print(json.dumps(dict(bound_head=head, members=len(records),
        old_exports=len(original_entries), new_exports=len(entries), total_exports=len(old['exports']))))


if __name__ == '__main__':
    main()
