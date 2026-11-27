"""Independent public wire/guard fixtures for PR88; zero NFL model execution.

Only the already-reviewed optional component is imported. Its import performs no
source/model/storage/native-context work. The output directory must be empty.
"""
import argparse
import ast
import copy
import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


def sha(body):
    return hashlib.sha256(body).hexdigest()


def main(source, out):
    out.mkdir(parents=True, exist_ok=True)
    destination = out / 'INDEPENDENT_GUARDED_WIRE_FIXTURES_V1.json'
    if destination.exists():
        raise ValueError('Preserve frozen verification receipt')
    module_path = source / 'nfl_lab/count_a_native_extension_v1.py'
    module_bytes = module_path.read_bytes()
    if sha(module_bytes) != 'dec10328c7811d788c4b605a4098d01e8f95ab99dca3455b547cc699e7686008':
        raise ValueError('Exact PR88 source changed')
    spec = importlib.util.spec_from_file_location('B_counta_wire_under_review', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    records = []

    def check(name, value):
        if not value:
            raise AssertionError(name)
        records.append(dict(check=name, state='PASS'))

    def rejects(name, operation):
        try:
            operation()
        except (ValueError, TypeError):
            check(name, True)
        else:
            raise AssertionError(name)

    # Deliberately independent expectation: this is the declared public contract,
    # not an expected value recomputed by the author's summary/scoring function.
    expected_fields = {
        'season', 'week', 'game_id', 'player_id', 'team', 'opponent', 'position',
        'kickoff_utc', 'cutoff_utc', 'expected_mean', 'selection_point',
        'fallback_reason', 'value_origin', 'prediction_functional',
        'procedure_version', 'model_sha256', 'issued_at_UTC', 'expiry_UTC',
        'probability', 'EV',
    }
    check('Exact 20-field public projection, no legacy_point/mean alias', set(module.ROW_FIELDS) == expected_fields)
    row = {key: None for key in expected_fields}
    row.update(season=2026, week=10, game_id='SYNTHETIC_ONLY_EVENT',
        player_id='SYNTHETIC_ONLY_QB', team='AAA', opponent='BBB', position='QB',
        kickoff_utc='2026-11-13T01:15:00+00:00', cutoff_utc='2026-11-12T23:45:00+00:00',
        issued_at_UTC='2026-11-12T22:00:00+00:00', expiry_UTC='2026-11-12T23:45:00+00:00',
        expected_mean=0.0, selection_point=0.0, fallback_reason='',
        value_origin='LEARNED_POISSON_OBJECTIVE_MEAN', prediction_functional='MEAN_OBJECTIVE_POINT',
        procedure_version=module.PROCEDURE, model_sha256=module.MODEL)
    zero = module.projection([row])
    check('Reported zero stays numerical zero and not null', zero['rows'][0]['expected_mean'] == 0.0)
    unknown = dict(row, expected_mean=None, selection_point=None,
        fallback_reason='unavailable', value_origin='INCUMBENT_FALLBACK_REQUIRED')
    null = module.projection([unknown])
    check('Unknown mean remains JSON null, not zero', json.loads(module.canonical(null))['rows'][0]['expected_mean'] is None)
    check('No point-derived probability or EV', zero['probability'] is zero['EV'] is None)
    check('Projection claims no primary or picks', zero['state'] == 'SHADOW_NOT_PRIMARY_NOT_PICKS' and zero['public_export_authorized'] is False)
    for field, value in [
        ('expected_mean', float('nan')), ('expected_mean', float('inf')),
        ('expected_mean', -0.1), ('expected_mean', True),
        ('selection_point', 1.0), ('model_sha256', '0' * 64),
        ('procedure_version', '0' * 64), ('position', 'RB'), ('probability', 0.9),
        ('EV', 1.0), ('issued_at_UTC', row['cutoff_utc']),
        ('expiry_UTC', '2026-11-12T23:46:00+00:00'),
        ('issued_at_UTC', '2026-11-12T22:00:00'),
    ]:
        altered = dict(row, **{field: value})
        rejects('Reject invalid public field ' + field + ':' + repr(value), lambda altered=altered: module.projection([altered]))
    extra = dict(row, legacy_point=0.0)
    rejects('Reject unregistered legacy output field', lambda: module.projection([extra]))
    rejects('Reject duplicate JSON key', lambda: module.strict(b'{"x":1,"x":2}'))
    rejects('Reject nonfinite JSON', lambda: module.strict(b'{"x":NaN}'))
    rejects('Reject nonmatching capsule before model deserialization', lambda: module.authenticate_capsule(b'not-model-bytes'))

    grant = dict(schema_version=module.VERSION + '-publication',
        authority_kind='ROOT_APPROVED_DERIVED_PUBLICATION', scope='DERIVED_QB_MEAN_SHADOW_ONLY',
        source_policy_sha256='e7f54213218031c978c766af7a1a3b22a57c2a424b51f62056742162154fe441',
        source_review_sha256='7' * 64, public_fields=list(module.ROW_FIELDS),
        public_prefix='public/count-a-mean-shadow-v1/', raw_or_weights_public=False,
        primary_activation=False, ranking_change=False)
    root = dict(publication=True, count_a_mean_shadow=dict(public_release=True, publication=grant))
    live_record = dict(accepted_at='2026-11-12T22:01:00+00:00')
    pair = module.public_pair(zero, live_record, root, '2026-11-12T22:02:00+00:00')
    feed = json.loads(next(body for name, body in pair.items() if name.endswith('.json')))
    check('Derived feed keeps exact corrected mean and null probability', feed['rows'][0]['expected_mean'] == feed['rows'][0]['selection_point'] == 0 and feed['probability'] is None)
    check('Frozen original issue is preserved at publication', feed['rows'][0]['issued_at_UTC'] == row['issued_at_UTC'])
    check('Current shadow is not a current recommendation', feed['current_use_status'] == 'CURRENT_SHADOW_FORECAST_ONLY' and feed['is_current_recommendation'] is False)
    late = module.public_pair(zero, live_record, root, '2026-11-14T00:00:00+00:00')
    expired = json.loads(next(body for name, body in late.items() if name.endswith('.json')))
    check('Late publication stays explicitly expired without backdating', expired['current_use_status'] == 'EXPIRED_OR_PARTIALLY_EXPIRED' and expired['rows'][0]['issued_at_UTC'] == row['issued_at_UTC'])
    rejects('Reject publication before native acceptance', lambda: module.public_pair(zero, live_record, root, '2026-11-12T22:00:30+00:00'))
    altered_root = copy.deepcopy(root)
    altered_root['count_a_mean_shadow']['publication']['primary_activation'] = True
    rejects('Reject public grant attempting primary activation', lambda: module.public_pair(zero, live_record, altered_root, '2026-11-12T22:02:00+00:00'))

    tree = ast.parse(module_bytes)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BoundShadow')
    capture = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'capture')
    calls = [n for n in ast.walk(capture) if isinstance(n, ast.Call)]
    adapter_calls = [n for n in calls if isinstance(n.func, ast.Name) and n.func.id == 'predict_verified_mean']
    check('New native capture calls unchanged mean adapter exactly once', len(adapter_calls) == 1)
    check('New adapter wiring explicitly supplies trained mean corrector', any(k.arg == 'mean_corrector' and isinstance(k.value, ast.Name) and k.value.id == 'correct_fallbacks' for k in adapter_calls[0].keywords))
    check('New native component does not directly reapply corrector', not any(isinstance(n.func, ast.Name) and n.func.id == 'correct_fallbacks' for n in calls))
    check('New capture has no bare-model predict substitution', not any(isinstance(n.func, ast.Attribute) and n.func.attr in ('predict', 'predict_proba') for n in calls))
    check('New component exports no legacy_point or synthetic side', 'legacy_point' not in expected_fields and not {'side', 'line', 'confidence'} & expected_fields)
    expected_procedure = sha(json.dumps(dict(recipe='count-a-prior-mean-fallback-v2-20261025', parent_procedure_version=module.PARENT, parent_model_sha256=module.MODEL), sort_keys=True, separators=(',', ':')).encode())
    check('Parent/model recipe independently hashes to approved f860 product', expected_procedure == module.PROCEDURE)

    report = dict(id='B-COUNTA-PR88-NEW-GUARDED-WIRE-CHECK-v1',
        checked_UTC=datetime.now(timezone.utc).isoformat(),
        source_ref='af405c4604f6eac935e594f1acd3ab492eef412c',
        module_path='nfl_lab/count_a_native_extension_v1.py', module_sha256=sha(module_bytes),
        verifier_sha256=sha(Path(__file__).read_bytes()), checks=records, check_count=len(records),
        state='PASS_IN_PUBLIC_SYNTHETIC_WIRE_AND_STATIC_ADAPTER_WIRING_SCOPE',
        original_model_or_corrector_math_repeated=False, model_deserializations=0,
        NFL_fits=0, NFL_inference=0, issued_NFL_rows=0, grades=0,
        real_native_Root_or_LiveAcceptance_claimed=False, actual_feed_verified=False,
        scope_limits=['No trusted private capsule/FIT_START/proof or genuine current Root was supplied here.',
            'Pure formatting fixtures do not establish live authority, current-source admissibility, durable output or consumer use.',
            'The previously completed retained-case model/corrector parity is reused rather than rerun.',
            'New native pipeline remains an optional shadow, not an original-site primary or selector switch.'])
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(state=report['state'], checks=len(records), NFL_fits=0, actual_feed_verified=False)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    main(args.source, args.out)
