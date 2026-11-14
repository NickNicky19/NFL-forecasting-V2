"""Bounded independent typed-model inference/use check; zero model fits.

FTN-derived counts, models and forecasts: FTN Data via nflverse, CC-BY-SA-4.0.
Uses existing public-safe source derivatives; does not reauthenticate raw plays,
historical publication clocks, private offers, grades, or production admission.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import resource
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from nfl_v2.player_context_matchup import restored_forest_law, ContextHistory
from nfl_v2.distribution_laws import Law
from nfl_v2 import qb_opportunity_increment as opportunity_increment
from nfl_v2.passing_opportunity_profiles import OpportunityHistory

BASE = ROOT / 'reports/information-first-20261112-01/B'
WAVE = BASE / 'completion-wave-v1'
OUT = Path(__file__).resolve().parent
FLAGS = ('is_throw_away', 'is_interception_worthy')
TOLERANCE = 1e-10


def read(path):
    b = path.read_bytes()
    return json.loads(gzip.decompress(b) if path.suffix == '.gz' else b)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(row):
    return row['game_id'], row['player_id']


def equal(a, b, *, tolerance=TOLERANCE):
    np.testing.assert_allclose(np.asarray(a, float), np.asarray(b, float), rtol=0, atol=tolerance, equal_nan=True)


def manual_batch(payload, x):
    """Independent vectorized tree traversal; never author fit/design/restore."""
    x = np.asarray(x, float)
    med = np.asarray(payload['design']['median'], float)
    assert x.ndim == 2 and x.shape[1] == len(med)
    z = np.concatenate([np.where(np.isfinite(x), x, med), ~np.isfinite(x)], axis=1).astype(np.float32)
    support = np.asarray(payload['support'], float)
    weights = np.zeros((len(x), len(support)))
    for tree in payload['trees']:
        left, right = np.asarray(tree['left']), np.asarray(tree['right'])
        feature, threshold = np.asarray(tree['feature']), np.asarray(tree['threshold'])
        node = np.zeros(len(x), int)
        for depth in range(9):
            live = np.flatnonzero(left[node] >= 0)
            if not len(live):
                break
            assert depth < 8
            f = feature[node[live]]
            assert np.all((f >= 0) & (f < z.shape[1]))
            node[live] = np.where(z[live, f] <= threshold[node[live]], left[node[live]], right[node[live]])
        assert np.all(left[node] == -1)
        hist = tree['leaf_histogram']
        dense = np.zeros((len(left), len(support)))
        np.add.at(dense, (hist['rows'], hist['columns']), hist['values'])
        weights += dense[node] / len(payload['trees'])
    equal(weights.sum(axis=1), 1.)
    assert np.isfinite(weights).all() and np.all(weights >= 0)
    return support, weights / weights.sum(axis=1)[:, None]


def prior_from_saved(row):
    p = row['law']['prior']
    assert p['kind'] == 'geometric' and 0 <= p['q'] < 1
    return Law('geometric', q=p['q'])


def manual_rate_trace(query, source_rows, quality, frozen):
    cutoff = query['kickoff']
    eligible = [r for r in source_rows if r['position'] == 'QB'
                and r['physical_participation'] is True and r['target_parity'] is True
                and isinstance(r.get('available'), (int, float)) and math.isfinite(r['available'])
                and r['available'] < cutoff]
    eligible.sort(key=lambda r: (r['kickoff'], r['game_id'], r['player_id']))
    own = [r for r in eligible if r['player_id'] == query['player_id']][-8:]
    details = {}
    for flag in FLAGS:
        own_counts = [quality[key(r)]['flags'][flag] for r in own]
        pool_counts = [quality[key(r)]['flags'][flag] for r in eligible]
        n = sum(v['known'] for v in own_counts)
        a = sum(v['positive'] for v in own_counts)
        pk = sum(v['known'] for v in pool_counts)
        pp = sum(v['positive'] for v in pool_counts)
        pool = (pp + 1) / (pk + 2)
        value = (a + 20 * pool) / (n + 20)
        expected = frozen['flags'][flag]
        for field, v in [('known', n), ('positive', a), ('prior_known', pk), ('prior_positive', pp)]:
            assert expected[field] == v
        equal(value, expected['shrunk'], tolerance=1e-14)
        assert sum(v['unknown'] for v in own_counts) == expected['unknown']
        details[flag] = dict(positive=a, known=n, unknown=expected['unknown'],
                             raw=a/n if n else None, prior_positive=pp, prior_known=pk,
                             pooled_beta11_mean=pool, strength=20, shrunk=value,
                             source_definition='Provider charted TRUE among explicitly known TRUE/FALSE on credited QB pass-attempt join; not completion/drop accounting identity.')
    assert frozen['trace']['own_window_game_ids'] == [r['game_id'] for r in own]
    assert all(r['available'] < cutoff and r['game_id'] != query['game_id'] for r in own)
    return dict(game_id=query['game_id'], player_id=query['player_id'], cutoff=cutoff,
                source_tier=frozen['source_tier'], own_window_games=[r['game_id'] for r in own],
                own_appearances=len(own), latest_own_available=max((r['available'] for r in own), default=None),
                own_eligible_throws=sum(r['attempts'] for r in own), flags=details,
                selected_without_B2_outcomes=True)


def main():
    started = datetime.now(timezone.utc).isoformat()
    t0, cpu0 = time.monotonic(), time.process_time()
    orders_path = WAVE/'FEATURE_ORDER_V1.json'
    orders = read(orders_path)['orders']
    assert orders['B0'] == orders['B1']
    assert orders['B2'] == orders['B0'] + [f + ':shrunk' for f in FLAGS]
    order_hash = sha(orders_path)
    source_path = WAVE/'QB_CONTEXT_W1_W9_INPUTS_V1.json.gz'
    source = read(source_path)
    source_map = {key(r): r for r in source}
    feature_path = WAVE/'FEATURE_INPUTS_V1.json.gz'
    feature_rows = read(feature_path)
    feature_map = {key(r): r for r in feature_rows}
    quality_path = BASE/'source-qualification/FTN_BALL_QUALITY_QB_GAME_INPUTS_V1.json.gz'
    quality = {key(r): r for r in read(quality_path)}
    base_width, width = len(orders['B0']), len(orders['B2'])
    models = sorted((WAVE/'fits').glob('*-B2.json.gz'))
    assert len(models) == 27
    counts = Counter()
    by_origin, bindings, all_predictions = [], [], []
    max_error = 0.
    for model_path in models:
        fit = read(model_path)
        p = fit['model']
        assert fit['feature_order_sha256'] == order_hash and fit['feature_count'] == width
        assert len(p['design']['median']) == width and len(p['trees']) == 32
        used = Counter(f for tree in p['trees'] for f in tree['feature'] if f >= 0)
        values_used = {name: int(used[base_width + i]) for i, name in enumerate(orders['B2'][-2:])}
        missing_used = {name: int(used[width + base_width + i]) for i, name in enumerate(orders['B2'][-2:])}
        pred_path = WAVE/'predictions'/(model_path.name.replace('-B2', ''))
        data = read(pred_path)
        rows = sorted((r for r in data['rows'] if r['method'] == 'B2'), key=key)
        all_predictions.extend(rows)
        x = np.asarray([r['features'] for r in rows], float)
        for r in rows:
            f = feature_map[key(r)]
            assert not f['fallback_to_B0'] and r['fallback'] == 'none'
            equal(r['features'], f['B0_features'] + f['B2_appended'])
            assert r['FTN_information'] == f['information']
        support, w = manual_batch(p, x)
        shuffled = np.random.default_rng(1701).permutation(len(x))
        _, ws = manual_batch(p, x[shuffled])
        equal(w[shuffled], ws, tolerance=0)
        roundtrip = json.loads(json.dumps(p, sort_keys=True, allow_nan=False))
        _, wr = manual_batch(roundtrip, x)
        equal(w, wr, tolerance=0)
        # Positional restoration checks every saved row, with independent batched masses.
        for i, r in enumerate(rows):
            prior = prior_from_saved(r)
            law = restored_forest_law(p, x[i], prior)
            equal(law.support, support, tolerance=0)
            equal(law.weights, w[i])
            equal(law.weights, r['law']['weights'])
            equal(support, r['law']['support'], tolerance=0)
            err = abs(law.mean - r['mean']); max_error = max(max_error, err)
            assert err <= TOLERANCE and law.quantile(.5) == r['lower_median']
            grid = list(range(-1, max(101, int(support[-1]) + 2)))
            cdf = np.asarray([law.cdf(g) for g in grid])
            pmf = np.asarray([law.pmf(g) for g in grid])
            assert np.all(np.diff(cdf) >= -1e-14) and np.all((cdf >= 0) & (cdf <= 1))
            assert np.isfinite(pmf).all() and np.all(pmf >= 0) and law.pmf(-1) == 0
            equal(np.cumsum(pmf), cdf)
            # Explicit integer push and half-integer orientation, independent of offer rows.
            for threshold in [0, 10, 20, 20.5, 40]:
                under = law.cdf(math.ceil(threshold)-1)
                push = law.pmf(threshold)
                over = 1-law.cdf(math.floor(threshold))
                equal(under+push+over, 1.)
            counts['saved_rows_restored'] += 1
        for bad in [x[0, :-1], np.r_[x[0], 0.]]:
            try:
                restored_forest_law(p, bad, prior_from_saved(rows[0]))
            except ValueError:
                counts['wrong_width_rejected'] += 1
            else:
                raise AssertionError('Wrong-width input admitted')
        # Same-width column reorder is intentionally recorded, not misreported as rejected.
        reordered = x[0].copy(); reordered[[-2, -1]] = reordered[[-1, -2]]
        restored_forest_law(p, reordered, prior_from_saved(rows[0]))
        counts['same_width_reorder_not_detected_by_lowlevel_API'] += 1
        by_origin.append(dict(slot=fit['slot'], rows=len(rows), input_columns=width,
            total_internal_splits=sum(used.values()), new_value_split_counts=values_used,
            new_missing_indicator_split_counts=missing_used,
            at_least_one_new_value_used=bool(sum(values_used.values())),
            feature_order_binding='PASS_FROZEN_ARRAYS_AND_MODEL_MANIFEST',
            named_order_runtime_enforcement='NOT_PROVIDED_BY_POSITIONAL_API'))
        for path in [model_path, pred_path]:
            bindings.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(path), bytes=path.stat().st_size))
    # Deterministic trace set is selected only by stable identity and source support.
    ordered = sorted(all_predictions, key=key)
    selected = {'first_stable_identity': ordered[0]}
    for name, predicate in [
        ('first_no_own_history', lambda r: r['FTN_information']['trace']['own_window_appearances'] == 0),
        ('first_zero_own_attempt_window', lambda r: r['FTN_information']['trace']['own_window_appearances'] > 0 and r['FTN_information']['trace']['eligible_throws'] == 0),
        ('first_known_zero_numerator', lambda r: any(v['known'] > 0 and v['positive'] == 0 for v in r['FTN_information']['flags'].values()))]:
        found = next((r for r in ordered if predicate(r)), None)
        if found is not None:
            selected[name] = found
    # Peer supplies only safe identities selected on B0 outcome, not offer rows.
    # These labels are selection provenance, not an independent regrade here.
    for reason, identity in [
        ('peer_first_B0_P1_MEAN_loss_native142', ('2026_05_BAL_ATL', '00-0035993')),
        ('peer_first_B0_P1_MEAN_win_native142', ('2026_05_BAL_ATL', '00-0039917'))]:
        selected[reason] = next(r for r in ordered if key(r) == identity)
    traces = []
    for reason, row in selected.items():
        traces.append(dict(selection_rule=reason, **manual_rate_trace(source_map[key(row)], source, quality, row['FTN_information'])))
    # Optional parent-captured current packet: offline restoration only, never a reissue.
    current_path = BASE/'current-conditional-shadow-v1/FORECAST_ONLY_PACKET.json.gz'
    current = dict(state='NOT_CHECKED_PACKET_ABSENT')
    if current_path.exists():
        packet = read(current_path)
        cdir = current_path.parent
        protocol = read(cdir/'FROZEN_PROTOCOL.json')
        assert packet['protocol_sha256'] == sha(cdir/'FROZEN_PROTOCOL.json')
        assert packet['historical_inputs_sha256'] == sha(source_path)
        assert packet['parent_historical_protocol_sha256'] == sha(WAVE/'FROZEN_PROTOCOL.json')
        assert packet['source'] == protocol['source']
        assert packet['forecast_issued_UTC'] < packet['target_kickoff_UTC']
        assert packet['original_actual_line_selection'] is False and packet['no_website_change'] is True
        opportunity_path = ROOT/'reports/profile-increment-to-release-01/B/source-profiles/PASSING_OPPORTUNITY_GAME_INPUTS_V2.json.gz'
        assert packet['opportunity_inputs_sha256'] == sha(opportunity_path)
        opportunity = read(opportunity_path)
        op_history = OpportunityHistory(opportunity['team_games'], opportunity['QB_games'])
        history = ContextHistory(source, 8, 20)
        qrows = {key(q): q for q in read(cdir/'CURRENT_QUERIES.json')['queries']}
        n, unavailable = 0, 0
        for row in packet['forecasts']:
            assert row['actual_offer'] is None and row['selected_side'] is None and row['per_pick_confidence'] is None
            mp = cdir/'fits'/(row['method']+'.json.gz')
            assert row['model_sha256'] == sha(mp)
            fitted = read(mp)
            admitted = qrows[key(row)]
            for field in ['game_id', 'player_id', 'team', 'opponent', 'source_status', 'position']:
                assert row[field] == admitted[field]
            if row['output_state'] != 'CONDITIONAL_FORECAST':
                assert row['output_state'] == 'UNAVAILABLE_EXPLICIT_SOURCE_IR'
                assert row['mean'] is None and row['law'] is None
                unavailable += 1
                continue
            assert len(row['features']) == len(orders[row['method']])
            p = fitted['model']
            prior = Law('geometric', q=row['law']['prior']['q'])
            law = restored_forest_law(p, row['features'], prior)
            support, weights = manual_batch(p, [row['features']])
            equal(law.weights, weights[0])
            equal(law.mean, row['mean'])
            assert law.quantile(.5) == row['lower_median']
            q = dict(row, kickoff=datetime.fromisoformat(row['feature_cutoff_UTC']).timestamp())
            base_features = np.concatenate([history.direct_features(q, 'E3'),
                opportunity_increment.appended_features(op_history.feature_groups(q), 'R3')])
            equal(row['features'][:base_width], base_features)
            trace = manual_rate_trace(q, source, quality, row['FTN_information'])
            if row['method'] == 'B2':
                equal(row['features'][-2:], [trace['flags'][f]['shrunk'] for f in FLAGS])
            assert fitted['latest_training_label'] < q['kickoff']
            train = [r for r in source if r['season'] >= 2025 and r['physical_participation'] is True
                     and r['target_parity'] is True and r['available'] < q['kickoff']]
            train.sort(key=lambda r: (r['kickoff'], r['game_id'], r['player_id']))
            train_hash = hashlib.sha256(json.dumps([key(r) for r in train]).encode()).hexdigest()
            assert fitted['training_membership_sha256'] == train_hash
            mu = max(.05, float(np.mean([r['official_completions'] for r in train])))
            equal(prior.q, mu/(1+mu))
            n += 1
        assert n == 8 and unavailable == 2
        current = dict(state='PASS_OFFLINE_RESTORATION', conditional_forecasts=n,
            explicit_IR_unavailable=unavailable, actual_lines=0, selected_sides=0,
            issued_UTC=packet['forecast_issued_UTC'], expiry_UTC=packet['expiry_UTC'],
            verification_is_reissue=False, model_hashes_verified=True,
            current_source_receipt='Bound_to_parent_packet_and_protocol_only; no_independent_feed_retrieval_or_role_authentication',
            standalone_law_field='Mixture_and_prior_parameters_only; empirical_mass_reconstructed_from_bound_model_and_features_not_standalone_law_field',
            scope=protocol['scope'])
        for path in [current_path, cdir/'FROZEN_PROTOCOL.json', cdir/'fits/B0.json.gz', cdir/'fits/B2.json.gz']:
            bindings.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(path), bytes=path.stat().st_size))
    for path in [source_path, feature_path, quality_path, orders_path,
                 BASE/'prior-use/PRESELECTED_FRESH_FIT_REPRODUCTION_V1.json',
                 BASE/'prior-use/VERIFICATION_EXECUTION_SCOPE_V1.json', Path(__file__)]:
        bindings.append(dict(path=str(path.relative_to(ROOT)), sha256=sha(path), bytes=path.stat().st_size))
    result = dict(id='B-FTN-SAVED-MODEL-INFERENCE-USE-VERIFICATION-v1', state='PASS_WITH_EXPLICIT_SCOPE_LIMITS',
        started_UTC=started, completed_UTC=datetime.now(timezone.utc).isoformat(),
        fits_executed=0, new_NFL_scores=0, checked_origins=len(models), counts=dict(counts),
        appended_value_names=orders['B2'][-2:], input_columns=width,
        origins_using_new_values=sum(r['at_least_one_new_value_used'] for r in by_origin),
        total_new_value_splits={f:sum(r['new_value_split_counts'][f] for r in by_origin) for f in orders['B2'][-2:]},
        new_support_columns_added=0, max_saved_mean_error=max_error,
        lower_median_match='All_saved_rows', single_batch_shuffle_serialization='PASS_ALL_SAVED_B2_ROWS',
        feature_order='PASS_fixed_positional_arrays_manifest_and_width; same_width_named_permutations_not_detected_by_lowlevel_API',
        distribution_scope='Standalone_completion_count_law; no_new_ATT_CMP_joint_law_or_role_probability; exact_integer_push_and_half_integer_partition_checked',
        reused_checks=dict(unit_tests=7, independent_fresh_fit='prior-use/PRESELECTED_FRESH_FIT_REPRODUCTION_V1.json; not_repeated'),
        origin_split_use=by_origin, deterministic_source_feature_traces=traces,
        current_packet=current, bindings=bindings,
        resources=dict(wall_seconds=time.monotonic()-t0, CPU_seconds=time.process_time()-cpu0,
                       peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024),
        limitations=['Public_safe_source_derivatives_not_raw_play_reacquisition',
            'No_private_offer_or_grade_verification_in_this_receipt',
            'Current_vintage_seven_day_proxy_not_authenticated_historical_publication',
            'Source_support_missing_and_unknown_boundary_fixtures_reused_not_NFL_samples',
            'Tree_feature_use_is_implementation_evidence_not_predictive_gain',
            'No_producer_consumer_or_original_website_admission_verified'],
        license='FTN_Data_via_nflverse_CC-BY-SA-4.0_for_FTN-dependent_derivatives; underlying_stats_separate_attribution')
    dest = OUT/'SAVED_INFERENCE_AND_USE_V1.json'
    dest.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in ['state','checked_origins','counts','origins_using_new_values','total_new_value_splits','max_saved_mean_error','resources']}))


if __name__ == '__main__':
    main()
