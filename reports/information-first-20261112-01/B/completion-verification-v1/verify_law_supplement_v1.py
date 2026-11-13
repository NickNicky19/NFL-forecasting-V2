"""Independently check an output-preserving complete-law serialization.

FTN Data via nflverse, CC-BY-SA-4.0 for FTN-dependent derivatives.
No fit, reissue, offer grading, source refresh or website operation.
"""
import gzip
import hashlib
import importlib.util
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
CURRENT = ROOT/'reports/information-first-20261112-01/B/current-conditional-shadow-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    b = path.read_bytes()
    return json.loads(gzip.decompress(b) if path.suffix == '.gz' else b)


def main():
    helper = HERE/'verify_saved_inference_v1.py'
    spec = importlib.util.spec_from_file_location('independent_batch_verifier', helper)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    packet_path = CURRENT/'FORECAST_ONLY_PACKET.json.gz'
    capsule_path = CURRENT/'COMPLETE_LAW_CAPSULE_V1.json.gz'
    prior_receipt_path = HERE/'SAVED_INFERENCE_AND_USE_V1.json'
    packet, capsule, previous = read(packet_path), read(capsule_path), read(prior_receipt_path)
    old_binding = next(b for b in previous['bindings'] if b['path'] == str(packet_path.relative_to(ROOT)))
    assert sha(packet_path) == old_binding['sha256'] == capsule['original_packet_sha256']
    assert capsule['original_forecast_issued_UTC'] == packet['forecast_issued_UTC']
    assert capsule['actual_packaged_UTC'] > capsule['original_forecast_issued_UTC']
    assert capsule['original_packet_preserved'] is True and capsule['prediction_time_not_backdated'] is True
    for k in ['new_fits', 'new_forecasts', 'new_sides', 'changed_points', 'changed_distributions']:
        assert capsule[k] == 0
    identity = lambda r: (r['game_id'], r['player_id'], r['method'])
    old_rows = {identity(r): r for r in packet['forecasts']}
    rows = capsule['forecasts']
    assert len(rows) == len(old_rows) == 10 and len({identity(r) for r in rows}) == 10
    checked, unavailable, masses = 0, 0, 0
    max_mean_error = max_mass_error = 0.
    model_paths = set()
    for row in rows:
        old = old_rows[identity(row)]
        for k in ['output_state', 'mean', 'lower_median']:
            assert row[k] == old[k]
        if row['output_state'] != 'CONDITIONAL_FORECAST':
            assert row['output_state'] == 'UNAVAILABLE_EXPLICIT_SOURCE_IR'
            assert row['mean'] is None and row['lower_median'] is None and row['law'] is None
            unavailable += 1
            continue
        law = row['law']
        assert law['kind'] == 'leaf_mixture'
        support, weights = np.asarray(law['support'], float), np.asarray(law['weights'], float)
        assert len(support) == len(weights) and np.all(np.diff(support) > 0)
        assert np.isfinite(support).all() and np.all(support >= 0) and np.all(support == np.floor(support))
        assert np.isfinite(weights).all() and np.all(weights >= 0)
        assert abs(float(weights.sum())-1) <= 1e-12
        assert law['prior'] == old['law']['prior'] and law['mixture'] == old['law']['mixture'] == .05
        assert law['prior']['kind'] == 'geometric'
        q, b = law['prior']['q'], law['mixture']
        assert 0 <= q < 1
        mp = CURRENT/'fits'/(row['method']+'.json.gz')
        model_paths.add(mp)
        assert sha(mp) == old['model_sha256']
        # Independent typed traversal from the previous verifier, no author restore.
        expected_support, expected_weights = mod.manual_batch(read(mp)['model'], [old['features']])
        np.testing.assert_array_equal(support, expected_support)
        error = float(np.max(np.abs(weights-expected_weights[0])))
        assert error <= 1e-12
        max_mass_error = max(max_mass_error, error)
        mean = (1-b)*float(weights@support)+b*q/(1-q)
        max_mean_error = max(max_mean_error, abs(mean-old['mean']))
        assert abs(mean-old['mean']) <= 1e-12
        def cdf(value):
            x = math.floor(value)
            prior_cdf = 0. if x < 0 else 1-q**(x+1)
            return (1-b)*float(weights[support <= x].sum())+b*prior_cdf
        def pmf(value):
            if value != math.floor(value) or value < 0:
                return 0.
            return (1-b)*float(weights[support == value].sum())+b*(1-q)*q**int(value)
        median = next(k for k in range(10000) if cdf(k) >= .5)
        assert median == old['lower_median']
        # Exact total-mass identity includes the unbounded geometric tail.
        assert abs((1-b)*float(weights.sum())+b-1) <= 1e-12
        grid = np.asarray([cdf(k) for k in range(-1, 101)])
        assert np.all(np.diff(grid) >= -1e-14) and np.all((grid >= -1e-14) & (grid <= 1+1e-14))
        for threshold in [0, 10, 20, 20.5, 40]:
            under, push, over = cdf(math.ceil(threshold)-1), pmf(threshold), 1-cdf(math.floor(threshold))
            assert abs(under+push+over-1) <= 1e-12
        checked += 1
        masses += len(support)
    assert checked == 8 and unavailable == 2
    paths = [packet_path, capsule_path, prior_receipt_path, helper, Path(__file__)] + sorted(model_paths)
    result = dict(id='B-FTN-CURRENT-COMPLETE-LAW-SUPPLEMENT-CHECK-v1', state='PASS',
        verified_UTC=datetime.now(timezone.utc).isoformat(),
        complete_conditional_laws=checked, empirical_support_mass_pairs=masses,
        explicit_IR_unavailable=unavailable, max_empirical_mass_difference=max_mass_error,
        max_mean_difference=max_mean_error, lower_medians='8_of_8_match_original',
        normalization='Independent_empirical_plus_infinite_geometric_tail_identity',
        inference='Independent_vectorized_typed_traversal_from_same_bound_models_and_vectors; no_author_fit_or_restore',
        original_packet_unchanged_since_prior_verification=True,
        original_forecast_issued_UTC=packet['forecast_issued_UTC'],
        actual_packaged_UTC=capsule['actual_packaged_UTC'],
        fits_executed=0, new_forecasts=0, reissues=0, new_sides=0, new_NFL_grades=0,
        limitation_resolution='Original_packet_law_field_remains_incomplete_alone; append_only_capsule_now_serializes_same_empirical_support_and_weights_without_changed_predictions_or_distributions',
        source_and_admission_limits='Prior_current_packet_limits_preserved; no_independent_source_retrieval, active_role_authentication, actual_offer, consumer_or_website_admission',
        bindings=[dict(path=str(p.relative_to(ROOT)),sha256=sha(p),bytes=p.stat().st_size) for p in paths],
        license='FTN_Data_via_nflverse_CC-BY-SA-4.0_for_FTN-dependent_derivatives')
    (HERE/'SUPPLEMENT_CHECK_V1.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['state','complete_conditional_laws','empirical_support_mass_pairs','max_empirical_mass_difference','max_mean_difference']}))


if __name__ == '__main__':
    main()
