"""Scoped independent PR88 encoder delta check; no private/NFL artifact load."""
import argparse
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def digest(body):
    return hashlib.sha256(body).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def metadata_functions(path):
    tree = ast.parse(path.read_bytes())
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef)
             and n.name in {'require', 'sha', 'canonical', 'strict', 'authenticate_fit'}]
    env = dict(json=json, hashlib=hashlib)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'reviewed-metadata-only-functions', 'exec'), env)
    return tree, env


def main(old_root, new_root, out):
    destination = out / 'ENCODER_DELTA_REVIEW_V1.json'
    if destination.exists():
        raise ValueError('Preserve frozen delta receipt')
    relative = 'nfl_lab/count_a_native_extension_v1.py'
    old, new = old_root / relative, new_root / relative
    before, after = old.read_bytes(), new.read_bytes()
    assert digest(before) == 'dec10328c7811d788c4b605a4098d01e8f95ab99dca3455b547cc699e7686008'
    assert digest(after) == '6bf0a6d432d7a0f77bab1d8d8a95c687cf91e350dde48e11a7e827184b469351'
    assert before.replace(b"sha(canonical(recipe)+b'\\n')", b'sha(canonical(recipe))', 1) == after
    old_tree, old_env = metadata_functions(old)
    new_tree, new_env = metadata_functions(new)
    bodies = lambda tree: {n.name: ast.dump(n, include_attributes=False) for n in tree.body
                            if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    old_bodies, new_bodies = bodies(old_tree), bodies(new_tree)
    changed = [name for name in old_bodies if old_bodies[name] != new_bodies[name]]
    assert changed == ['authenticate_fit']
    # A deliberately synthetic proof. Only this isolated function environment's
    # expected proof/parent constants are replaced; it is never native authority.
    recipe = dict(training_cutoff_utc='2026-09-01T00:00:00Z',
        source_pins=dict(mean_corrector=dict(sha256='aa7c002506b57d7c1ca643f4236e5fb8b5132bebb00ad86720ee11221b6d9fb6')),
        synthetic_only=True)
    canonical_recipe = encoded(recipe)
    expected = digest(canonical_recipe)
    fit_body = encoded(dict(recipe=recipe))
    fit_ref = dict(path='SYNTHETIC_ONLY_FIT_START', bytes=len(fit_body), sha256=digest(fit_body))
    proof = dict(artifacts={'pass_td__COUNT_A_MEAN/FIT_START.json': fit_ref}, synthetic_padding='')
    proof['synthetic_padding'] = 'x' * (26032 - len(encoded(proof)))
    proof_body = encoded(proof)
    assert len(proof_body) == 26032
    for env in (old_env, new_env):
        env.update(PROOF=digest(proof_body), PARENT=expected,
            CORRECTOR='aa7c002506b57d7c1ca643f4236e5fb8b5132bebb00ad86720ee11221b6d9fb6')
    registration = dict(fit_start=fit_ref)
    audit = dict(recipe_sha256=expected)
    checks = []

    def rejected(name, env, pb=proof_body, fb=fit_body, au=audit, error=None):
        try:
            env['authenticate_fit'](pb, fb, registration, au)
        except ValueError as exc:
            assert error is None or str(exc) == error
            checks.append(dict(check=name, state='PASS', expected_guard=str(exc)))
        else:
            raise AssertionError(name)

    rejected('Old encoder rejects a synthetically authenticated newline-free recipe', old_env, error='COUNT_A_ORIGINAL_RECIPE')
    assert new_env['authenticate_fit'](proof_body, fit_body, registration, audit) == recipe
    checks.append(dict(check='New encoder accepts the same decoded recipe without altering it', state='PASS'))
    rejected('Original proof-byte guard remains active', new_env,
        pb=proof_body[:-1] + b' ', error='COUNT_A_ORIGINAL_PRODUCER_PROOF')
    rejected('FIT_START byte/hash guard remains active', new_env,
        fb=fit_body + b'\n', error='COUNT_A_ORIGINAL_FIT_START')
    rejected('MODEL_AUDIT recipe mismatch remains rejected', new_env,
        au=dict(recipe_sha256='0' * 64), error='COUNT_A_ORIGINAL_RECIPE')
    assert digest(canonical_recipe + b'\n') != expected
    checks.append(dict(check='Trailing newline changes bytes and digest; no digest equality assumed', state='PASS'))
    checks.append(dict(check='Only authenticate_fit AST changed; other wire/capture/publication functions unchanged', state='PASS'))
    binding_path = next(new_root.rglob('COUNTA_CORRECTED_HELPER_ROOT_BINDING_V1.json'))
    binding = json.loads(binding_path.read_text())
    pins = binding['count_a_mean_shadow_helper_pins']
    assert pins[relative] == digest(after)
    for name in ['nfl_lab/count_a_mean_export_adapter_v1.py', 'tools/modern_count_a_mean_v3.py']:
        assert pins[name] == digest((old_root / name).read_bytes())
    checks.append(dict(check='Prepared new Root helper fragment binds new extension plus unchanged adapter/corrector bytes', state='PASS'))
    config = old_root / 'config/weekly-mae-display-core3-v1.json'
    assert binding['source_config_file_sha256'] == digest(config.read_bytes())
    checks.append(dict(check='Prepared helper fragment preserves actual reviewed source-profile file hash', state='PASS'))
    report_path = next(new_root.rglob('COUNTA_ENCODING_INDEPENDENT_REVIEW_V1.json'))
    owner = json.loads(report_path.read_text())
    real = owner['independent_metadata_reproduction']
    assert real['recipe_encoding']['without_newline_sha256'] == '9c48aab650f35a60631fd5d6af2cef4b8c513416fe0f9b2c61591d7f8af4b85f'
    assert real['recipe_encoding']['with_newline_sha256'] == '35b97d56ff4ddfd3460cd6c2d2223499f7390bab885c265550bc13d646a2810a'
    assert real['recipe_encoding']['canonical_without_newline_bytes'] == 5722
    assert real['recipe_encoding']['with_newline_bytes'] == 5723
    checks.append(dict(check='Owner-reported genuine metadata commitments agree with approved parent and exact one-byte encoding delta', state='PASS'))
    report = dict(id='B-COUNTA-PR88-RECIPE-ENCODER-DELTA-v1',
        checked_UTC=datetime.now(timezone.utc).isoformat(), source_before='af405c4604f6eac935e594f1acd3ab492eef412c',
        source_after='3156058b91c7d9f0bb0f2cdebc4831994214e5bd', before_sha256=digest(before), after_sha256=digest(after),
        check_count=len(checks), checks=checks, changed_function_ASTs=changed,
        verifier_sha256=digest(Path(__file__).read_bytes()),
        state='PASS_SCOPED_ENCODING_CORRECTION_AND_NEW_HELPER_BINDING',
        finding='Old recipe authentication appended an unregistered newline. New source removes only that byte before hashing; prediction/model/mean-corrector identity is unchanged.',
        genuine_metadata_verification=dict(owner_report_path='reports/abc-championship/final-mile-producer-delivery-01/review/COUNTA_ENCODING_INDEPENDENT_REVIEW_V1.json',
            owner_report_sha256=digest(report_path.read_bytes()), declared_original_metadata=real['original_metadata'],
            declared_recipe_encoding=real['recipe_encoding'], B_independently_loaded_private_FIT_START_or_recipe=False,
            scope='B independently verified public delta, unchanged ASTs, synthetic guard behavior and published commitments. Genuine5722recipe bytes remain owner-local; their digest was not independently recomputed by B.'),
        helper_binding_sha256=digest(binding_path.read_bytes()),
        new_full_Root_bytes='UNKNOWN_NOT_ISSUED', actual_CountA_feed_verified=False,
        old_34_checks='Remain an immutable af405-specific receipt. Unchanged function ASTs verified here; no claim they executed against315head.',
        no_contamination_claim='Owner reports old source was not bound to native producer. B observed no affected NFL forecast/grade and quantifies none.',
        NFL_fits=0, NFL_inference=0, model_deserializations=0, issued_NFL_rows=0, NFL_grades=0,
        native_API_calls=0, peer_writes=0, external_messages=0)
    destination.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(state=report['state'], checks=len(checks), genuine_private_recipe_read_by_B=False)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--old-source', type=Path, required=True)
    parser.add_argument('--new-source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    main(args.old_source, args.new_source, args.out)
