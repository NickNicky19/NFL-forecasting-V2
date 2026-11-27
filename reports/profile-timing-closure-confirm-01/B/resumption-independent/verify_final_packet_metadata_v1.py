"""Verify a frozen packet's metadata amendment; no fit/inference/grading."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
BASE = OUT.parent
FORWARD = BASE / 'forward-current-v1'
ORIGINAL_COMMIT = 'c3199e20149d018eda55eba6528ea27d0f859a5d'
PUBLICATION_COMMIT = 'b046aab1877e5fb0412864d215a40df1c722a2df'


def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clock(text):
    value = datetime.fromisoformat(text.replace('Z', '+00:00'))
    assert value.tzinfo is not None
    return value.timestamp()


def save_new(path, value):
    assert not path.exists(), 'Preserve existing receipt'
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def main(prior_receipts):
    original_path = FORWARD / 'FORECASTS.json.gz'
    corrected_path = FORWARD / 'FORECASTS_METADATA_V2.json'
    prepared_path = FORWARD / 'PREPARED_FORECASTS.json.gz'
    correction_path = FORWARD / 'PACKET_METADATA_CORRECTION_V2.json'
    original, corrected, prepared, correction = map(read,
        (original_path, corrected_path, prepared_path, correction_path))
    original_relative = original_path.relative_to(ROOT).as_posix()
    committed_original = subprocess.check_output(
        ['git', 'show', ORIGINAL_COMMIT + ':' + original_relative], cwd=ROOT)
    assert committed_original == original_path.read_bytes()
    assert sha(original_path) == correction['original_sha256'] == '618a260be4bec1082592a2dea7c53a4c1eabe42121e09b0412e652f52c196d2e'
    assert sha(corrected_path) == correction['corrected_sha256']
    assert sha(prepared_path) == corrected['prepared_sha256']
    assert original['protocol_sha256'] == corrected['protocol_sha256'] == prepared['protocol_sha256'] == sha(FORWARD / 'FROZEN_CAPTURE_PROTOCOL.json')
    assert len(original['forecasts']) == len(corrected['forecasts']) == len(prepared['predictions']) == 16
    old_top = {k: v for k, v in original.items() if k != 'forecasts'}
    new_top = {k: v for k, v in corrected.items() if k not in ('forecasts', 'metadata_correction')}
    assert old_top == new_top
    source_rows = prepared['predictions']
    forecast_count = basic_count = changed_flags = 0
    keys = set()
    issued = clock(original['issue_UTC'])
    ignored_finalization_fields = {'actual_issued_UTC', 'original_pregame_forecast',
        'original_website_selection', 'issue_scope', 'prepared_record_sha256', 'status'}
    checked_models = {}
    for before, after, source in zip(original['forecasts'], corrected['forecasts'], source_rows):
        ident = before['identity']
        key = before['arm'], ident['game_id'], ident['player_id']
        assert key not in keys
        keys.add(key)
        has_forecast = isinstance(before.get('mean'), (int, float)) and not isinstance(before.get('mean'), bool)
        assert after['original_pregame_forecast'] is has_forecast
        assert after['basic_unavailable_record'] is (not has_forecast)
        assert before['original_pregame_forecast'] is True
        changed_flags += before['original_pregame_forecast'] != after['original_pregame_forecast']
        stripped_before = {k: v for k, v in before.items() if k not in ('original_pregame_forecast', 'basic_unavailable_record')}
        stripped_after = {k: v for k, v in after.items() if k not in ('original_pregame_forecast', 'basic_unavailable_record')}
        assert stripped_before == stripped_after
        assert {k: v for k, v in before.items() if k not in ignored_finalization_fields} == {
            k: v for k, v in source.items() if k not in ignored_finalization_fields}
        expected_prepared_commitment = hashlib.sha256(json.dumps(source, sort_keys=True, allow_nan=False).encode()).hexdigest()
        assert before['prepared_record_sha256'] == expected_prepared_commitment
        assert before['actual_issued_UTC'] == after['actual_issued_UTC'] == original['issue_UTC']
        assert before['actual'] is None and before['actual_status'] == 'FUTURE_NOT_GRADED'
        assert before['exact_offer'] is None and before['side'] is None
        assert before['selection'] is False and before['original_website_selection'] is False
        model_path = ROOT / before['model_path']
        assert sha(model_path) == before['model_sha256']
        if before['arm'] not in checked_models:
            model = read(model_path)
            assert model['training_rows'] == (941 if before['arm'] == 'F0' else 945)
            assert model['actual_new_fit_calls'] == 1
            assert model['latest_training_label'] < model['fit_cutoff'] <= clock(model['fit_started_utc']) <= clock(model['fit_completed_utc']) <= issued
            checked_models[before['arm']] = dict(path=before['model_path'], sha256=sha(model_path),
                training_rows=model['training_rows'], actual_original_fit_calls=1)
        if has_forecast:
            forecast_count += 1
            assert ident['provider_status'] == 'ACT'
            assert math.isfinite(before['mean']) and before['mean_type'] == 'EXPECTED_MEAN'
            assert before['median_type'] == 'LOWER_MEDIAN' and before['law'] == after['law']
            assert before['status'] == 'ISSUED_FUTURE_FORECAST_ONLY_SHADOW'
        else:
            basic_count += 1
            assert ident['provider_status'] in ('DEV', 'RES')
            assert 'mean' not in before and 'law' not in before
            assert before['status'] == 'BASIC_ONLY_UNAVAILABLE_FORECAST'
    assert (forecast_count, basic_count, changed_flags) == (10, 6, 6)
    assert corrected['offers'] == corrected['actual_line_selections'] == 0
    assert corrected['primary_switch'] is False
    assert len({r['identity']['player_id'] for r in corrected['forecasts']}) == 8
    assert len({r['identity']['player_id'] for r in corrected['forecasts'] if r['original_pregame_forecast']}) == 5
    now = datetime.now(timezone.utc)
    event = corrected['event']
    assert event['completed'] is False and event['state'] == 'pre'
    assert event['observed_at'] <= event['retained_at'] <= issued < event['expires_at'] < now.timestamp() < event['kickoff']
    assert event['expires_at'] == clock('2026-11-10T23:30:18Z')
    derivation_path = BASE / 'forward-receipts/current-inputs/CURRENT_INPUT_DERIVATION_RECEIPT_V1.json'
    derivation = read(derivation_path)
    assert len(derivation['held_game_ids']) == 13 and len(derivation['held_QB_rows']) == 34
    assert len(derivation['recent_native_final_game_ids']) == 2

    # Retain prior completed verification bytes. Do not rerun its model checks.
    copied = []
    prior_out = OUT / 'prior-receipts'
    prior_out.mkdir(exist_ok=True)
    names = ['CURRENT_PREPARED_PACKET_INDEPENDENT_REVIEW_V1.json',
        'CURRENT_PREPARED_PACKET_INDEPENDENT_REVIEW_V2.json',
        'FORWARD_PREPARATION_INDEPENDENT_REVIEW_V1.json', 'CHECKER_DEVELOPMENT_NOTES_V1.json']
    for name in names:
        source = prior_receipts / name
        content = source.read_text()
        assert not any(token in content for token in ('/workspace/', '/tmp/', 's3://', 'sk-proj-'))
        destination = prior_out / name
        assert not destination.exists()
        shutil.copyfile(source, destination)
        assert sha(source) == sha(destination)
        copied.append(dict(path=destination.relative_to(ROOT).as_posix(), sha256=sha(destination),
            bytes=destination.stat().st_size, origin='Preserved pre-outage owner-local B verifier bytes; not a new execution'))
    source_script = prior_receipts / 'verify_prepared_forward_packet_v1.py'
    assert not any(t in source_script.read_text() for t in ('/workspace/', 's3://', 'sk-proj-'))
    script_destination = prior_out / 'verify_prepared_forward_packet_v1.py.source.txt'
    assert not script_destination.exists()
    shutil.copyfile(source_script, script_destination)
    copied.append(dict(path=script_destination.relative_to(ROOT).as_posix(), sha256=sha(script_destination),
        bytes=script_destination.stat().st_size, origin='Exact prior completed verifier source retained as evidence; not re-executed'))
    reused = read(prior_out / 'CURRENT_PREPARED_PACKET_INDEPENDENT_REVIEW_V2.json')
    assert reused['prepared_sha256'] == sha(prepared_path)
    assert reused['source_derivation_receipt_sha256'] == sha(derivation_path)
    assert reused['held_recent_games'] == 13 and reused['held_QB_rows'] == 34
    assert reused['new_fits_by_verifier'] == 0
    for model in reused['models']:
        assert model['model_sha256'] == checked_models[model['arm']]['sha256']
        assert model['training_rows'] == checked_models[model['arm']]['training_rows']
    receipt = dict(id='B-FINAL-FROZEN-PACKET-METADATA-INDEPENDENT-REVIEW-v1',
        reviewed_UTC=now.isoformat(), status='PASS_WITHIN_CHECKED_SCOPE',
        repository='NickNicky19/NFL-forecasting-V2', original_commit=ORIGINAL_COMMIT,
        materialized_metadata_publication_commit=PUBLICATION_COMMIT,
        originals_immutable=True, original_sha256=sha(original_path), corrected_sha256=sha(corrected_path),
        prepared_sha256=sha(prepared_path), protocol_sha256=corrected['protocol_sha256'],
        records_checked=16, unchanged_forecast_values=10, explicit_basic_records=6,
        changed_original_forecast_flags=6, all_other_existing_record_fields_exactly_unchanged=True,
        top_level_changes=['metadata_correction annotation only'], final_to_prepared_parity='PASS_ALL16',
        prepared_record_commitments_verified=16, issue_UTC_unchanged=original['issue_UTC'],
        players_basic=8, players_forecast=5, actual_offers=0, actual_selections=0,
        graded_outcomes=0, models=list(checked_models.values()),
        source_summary=dict(qualified_recent_games=2, new_qualified_QB_rows=4,
            held_recent_games=13, held_QB_rows=34, checked_via_bound_prior_receipt=True,
            current_raw_PBP_reconstruction_repeated=False),
        native_clock_at_original_issue='VALID_IN_RETAINED_RECEIPT',
        native_clock_for_new_issuance='EXPIRED;NO_NEW_FRESH_PACKET_CLAIM',
        native_expiry_UTC='2026-11-10T23:30:18Z', future_event_kickoff_UTC='2026-11-13T01:15:00Z',
        current_event_status_requeried=False, prior_completed_receipts_reused=copied,
        verifier_code_sha256=sha(Path(__file__)), environment=dict(python=platform.python_version()),
        new_fits=0, new_model_inference=0, new_original_forecasts=0, new_score_views=0,
        independence='Separate metadata/identity/clock/hash/JSON comparison and prior receipt binding; author finalization helper not called.',
        limits=['No fresh fit or repeated 10-model inference; completed prior verification reused.',
            'No new raw play reconstruction or private A-board/source-clock verification.',
            'No new independent remote download by this task; local immutable Git objects and parent GitHub byte readback remain separately identified.',
            'No current producer, consumer, DOM, activation, Top Picks or primary release established by this check.'])
    save_new(OUT / 'INDEPENDENT_FINAL_PACKET_PARITY_V1.json', receipt)
    print(json.dumps({k: receipt[k] for k in ('status', 'records_checked', 'unchanged_forecast_values',
        'explicit_basic_records', 'issue_UTC_unchanged', 'native_clock_for_new_issuance', 'new_fits')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prior-receipts', type=Path, required=True)
    main(parser.parse_args().prior_receipts)
