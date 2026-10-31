"""Independent source/prefix, fixed A/B model and future capture replay.

Only preexisting through-W7 source bytes and new future predictions are read.
No fits, target-game outcomes, producer run functions or law scorer are called.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import math
import pickle
from pathlib import Path
import sys

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'reports/continuation-20261030'))
from check_new_wave_prefixes import load, clock, canonical
from check_retained_distribution_math import summaries

PUBLIC = ROOT / 'reports/continuation-20261030b/availability-wave-v1'
POSITIONS = ('QB', 'RB', 'WR', 'TE')
FEATURES = ('mean3', 'n3', 'mean8', 'n8') + tuple(f'lag{i}_{f}' for i in range(1, 5) for f in ('value', 'age_days', 'missing')) + tuple('position_' + p for p in POSITIONS)


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def decode(path): return json.loads(gzip.decompress(path.read_bytes()))
def close(a, b):
    assert (a is None and b is None) or (a is not None and b is not None and math.isclose(float(a), float(b), rel_tol=3e-11, abs_tol=3e-10)), (a, b)


def verify(private, source):
    protocol = json.loads((PUBLIC / 'FROZEN_PROTOCOL.json').read_text())
    receipt = json.loads((PUBLIC / 'AB-RUN_RECEIPT.json').read_text())
    assert sha(ROOT / 'nfl_v2/availability_wave.py') == protocol['code_sha256']
    assert sha(PUBLIC / 'FROZEN_PROTOCOL.json') == receipt['protocol_sha256']
    for name, digest in protocol['helper_code_sha256'].items(): assert sha(ROOT / 'nfl_v2' / name) == digest
    queries_path = private / 'frozen-queries.json'
    assert sha(queries_path) == protocol['frozen_queries_sha256']
    queries = json.loads(queries_path.read_text())
    assert len(queries) == protocol['query_cells'] == 2229
    bindings = json.loads((PUBLIC / 'FIXED_MODEL_BINDINGS.json').read_text())
    assert sha(PUBLIC / 'FIXED_MODEL_BINDINGS.json') == protocol['fixed_model_manifest_sha256']
    paths = json.loads((private / 'FIXED_MODEL_BINDINGS_PRIVATE.json').read_text())
    packet = private / receipt['packet']['bundle_name']
    assert sha(packet) == receipt['packet']['sha256']
    records = decode(packet)['rows']
    by_key = {}
    counts = Counter()
    asof = clock(protocol['fixed_feature_origin_utc'])
    captured = clock(protocol['qualified_2026_source_available_by'])
    persisted = clock(receipt['actual_persistence_completed_at'])
    assert captured < asof < persisted
    rows, history, games = load(source, protocol)
    fresh = defaultdict(list)
    for r in rows:
        g = games[r['game_id']]
        assert not (r['season'] == 2026 and g['week'] > 7)
        n = dict(r)
        if r['season'] == 2026 and g['week'] == 7:
            assert r['kickoff'] < captured
            n['available'] = min(r['available'], captured)
        fresh[r['player_id']].append(n)
    for rs in fresh.values(): rs.sort(key=lambda r: (r['available'], r['kickoff'], r['game_id']))

    def features(hist, q):
        rs = [r for r in hist.get(q['player_id'], []) if r['available'] < asof][-8:]
        out = []
        for size in (3, 8):
            ys = [float(r['values'][q['target']]) for r in rs[-size:] if r['values'][q['target']] is not None]
            out += [sum(ys) / len(ys) if ys else None, float(len(ys))]
        for i in range(1, 5):
            r = rs[-i] if len(rs) >= i else None
            value = r['values'][q['target']] if r else None
            out += [float(value) if value is not None else None, (asof-r['kickoff']) / 86400 if r else None, float(value is None)]
        out += [float(q['position'] == p) for p in POSITIONS]
        return out, rs[-1]['available'] if rs else None

    expected_features = {}
    changes = decode(private / 'features/QUERY_FEATURE_CHANGES.json.gz')
    assert len(changes) == len(queries)
    queries_by_id = {q['query_id']: q for q in queries}
    assert len(queries_by_id) == len(queries)
    for item in changes:
        q = queries_by_id[item['query_id']]
        a, ma = features(history, q)
        b, mb = features(fresh, q)
        for arm, expected, maximum in [('A', a, ma), ('B', b, mb)]:
            saved = item[arm + '_features']
            for x, y in zip(expected, saved): close(x, y); counts['independent_raw_feature_values'] += 1
            assert item[arm + '_max_available'] == maximum
            assert maximum is None or maximum < asof
            expected_features[(arm, q['query_id'])] = expected
        assert item['changed_columns'] == [name for name, a, b in zip(FEATURES, a, b) if a != b]
        counts['feature_changed_queries'] += bool(item['changed_columns'])
    for r in records:
        assert r['actual'] is None and r['actual_status'] == 'PENDING_FUTURE'
        assert r['season'] == 2026 and r['week'] == 8
        assert r['feature_cutoff_utc'] == protocol['fixed_feature_origin_utc']
        q = queries_by_id[r['query_id']]
        for field in ('game_id', 'player_id', 'target', 'position', 'kickoff_utc', 'owner_input_cutoff_utc'):
            assert r[field] == q[field]
        if r['prediction'] is not None:
            assert clock(r['actual_generated_at']) <= persisted < clock(r['owner_input_cutoff_utc']) < clock(r['kickoff_utc'])
            assert r['status'] == 'STAGED_RESEARCH_SHADOW'
            assert r['abstention_reason'] is None
        else:
            assert r['status'] == 'ABSTAIN' and r['abstention_reason']
        ident = (r['availability_arm'], r['family'], r['history_regime'], r['product_id'], r['query_id'])
        assert ident not in by_key
        by_key[ident] = r
        counts['issued' if r['prediction'] is not None else 'abstained'] += 1
    assert len(records) == receipt['output_views']
    assert counts['issued'] == receipt['issued'] and counts['abstained'] == receipt['abstained']
    for ident, a in list(by_key.items()):
        if ident[0] != 'A': continue
        b = by_key[('B',) + ident[1:]]
        assert a['fallback'] == b['fallback'] and a.get('fixed_model_artifact_id') == b.get('fixed_model_artifact_id')
        assert a['status'] == b['status'] and a['abstention_reason'] == b['abstention_reason']
        if a['family'] == 'ordered_leaf_cdf' and a['fallback'] != 'none':
            assert a['prediction'] == b['prediction']
            assert a['distribution_summary'] == b['distribution_summary']
        counts['AB_same_model_route_pairs'] += 1
        counts['AB_changed_predictions'] += a['prediction'] != b['prediction']

    def empirical(hist, target, arm, q, cutoff=asof):
        floor = {'H-CURRENT': 2026, 'H-RECENT': 2025, 'H-MULTI': 2022}[arm]
        eligible = [r for rs in hist.values() for r in rs if r['season'] >= floor and r['available'] < cutoff and r['position'] == q['position'] and r['values'][target] is not None]
        own = [r for r in eligible if r['player_id'] == q['player_id']]
        ys = sorted(float(r['values'][target]) for r in (own or eligible))
        return dict(own_n=len(own), n=len(ys), mean=math.fsum(ys)/len(ys) if ys else 0., lower_median=ys[(len(ys)-1)//2] if ys else 0., fallback='none' if own else 'same_arm_position_empirical' if ys else 'constant_zero')
    # Exact arithmetic-control replay for every output; cache repeated products.
    sample_cache = {}
    for r in records:
        if r['family'] != 'empirical_history_control' or r['prediction'] is None: continue
        q = queries_by_id[r['query_id']]
        k = (r['query_id'], r['history_regime'])
        if k not in sample_cache:
            a = empirical(history, r['target'], r['history_regime'], q)
            b = empirical(fresh, r['target'], r['history_regime'], q) if a['own_n'] else a
            sample_cache[k] = {'A': a, 'B': b}
        expected = sample_cache[k][r['availability_arm']]
        field = 'mean' if r['product_id'] == 'event_probability' else r['product_id']
        close(r['prediction'], expected[field] / (50 if r['target'] == 'nick-chart-ppr-v1' else 1))
        assert r['fallback'] == expected['fallback'] and r['fallback_n'] == expected['n']
        counts['arithmetic_predictions_replayed'] += 1
    with threadpool_limits(limits=2):
        for binding in bindings:
            local = paths[binding['key']]
            receiptfile = Path(local['receipt_path'])
            assert sha(receiptfile) == binding['receipt_sha256']
            old = json.loads(receiptfile.read_text())
            assert old['training_membership_sha256'] == binding['original_training_membership_sha256']
            model = None
            if local['model_path']:
                path = Path(local['model_path'])
                assert sha(path) == binding['model_sha256']
                model = pickle.loads(gzip.decompress(path.read_bytes()))
                counts['original_models_hash_verified'] += 1
            qrows = [q for q in queries if q['target'] == binding['target'] and not q.get('blocked_reason') and q.get('position') in POSITIONS]
            for mode in ('A', 'B'):
                if binding['family'] == 'hgb_direct':
                    x = np.asarray([[math.nan if v is None else v for v in expected_features[(mode, q['query_id'])]] for q in qrows])
                    values = model.predict_proba(x)[:, list(model.classes_).index(1.)] if model is not None and binding['target'] == 'anytime_td' else model.predict(x) if model is not None else [None] * len(qrows)
                    for q, value in zip(qrows, values):
                        product = 'event_probability' if binding['target'] == 'anytime_td' else 'mean' if binding['objective'] == 'squared_error_mean' else 'absolute_error_point'
                        saved = by_key[(mode, binding['family'], binding['history_regime'], product, q['query_id'])]
                        if value is None:
                            s = empirical(history, binding['target'], binding['history_regime'], q, clock(binding['original_fit_cutoff_utc']))
                            value = s['lower_median' if product == 'absolute_error_point' else 'mean']
                        if binding['target'] in ('pass_td', 'pass_cmp', 'pass_att', 'pass_int', 'rush_att', 'rec'): value = max(0., value)
                        close(saved['prediction'], value)
                        counts['original_HGB_inferences_replayed'] += 1
                else:
                    # Independent PMF reconstruction at representative learned and fallback queries.
                    selected = []
                    for want_fallback in (False, True):
                        for q in qrows:
                            x = expected_features[('A', q['query_id'])]
                            if bool(model is None or x[3] <= 0) == want_fallback:
                                selected.append(q); break
                    if qrows and qrows[-1] not in selected: selected.append(qrows[-1])
                    for q in selected:
                        f = expected_features[(mode, q['query_id'])]
                        law = old['prior_parameters'][q['position']]
                        if model is not None and expected_features[('A', q['query_id'])][3] > 0:
                            x = np.asarray([[math.nan if v is None else v for v in f]])
                            design = np.column_stack((np.where(np.isfinite(x), x, model.design.median), ~np.isfinite(x))).astype(float)
                            leaf = model.estimator.apply(design)[0]
                            weights = sum((h[leaf[j]].toarray().ravel() / len(model.hist) for j, h in enumerate(model.hist)), start=np.zeros(len(model.support)))
                            weights /= weights.sum()
                            law = dict(kind='mixture', support=model.support, weights=weights, prior=law)
                        summary = summaries(law, None)
                        scale = 50 if binding['target'] == 'nick-chart-ppr-v1' else 1
                        for product in ('event_probability',) if binding['target'] == 'anytime_td' else ('mean', 'lower_median'):
                            saved = by_key[(mode, binding['family'], binding['history_regime'], product, q['query_id'])]
                            d = saved['distribution_summary']
                            for field in ('mean', 'lower_median', 'q05', 'q95', 'interval90_width'):
                                close(d[field], summary[field] / scale)
                                counts['independent_law_summary_fields'] += 1
                            close(d['zero_mass'], summary['zero_mass'])
                            close(saved['prediction'], summary['mean' if product == 'event_probability' else product] / scale)
                            assert d['crps'] is None and d['nll'] is None
                        counts['representative_fixed_leaf_laws'] += 1
    assert receipt['actual_fit_calls'] == receipt['retained_models'] == receipt['failed_fits'] == receipt['score_views'] == 0
    return dict(status='PASS_INDEPENDENT_RAW_PREFIX_FIXED_MODEL_AND_CAPTURE_REPLAY', counts=dict(counts), games=13, query_cells=len(queries), source_W7_rows=303,
                source_W7_rows_excluded_A=receipt['W7_rows_excluded_A'], source_W7_rows_excluded_B=receipt['W7_rows_excluded_B'],
                source_known_by_utc=protocol['qualified_2026_source_available_by'], feature_origin_utc=protocol['fixed_feature_origin_utc'], persisted_at_utc=receipt['actual_persistence_completed_at'],
                protocol_sha256=sha(PUBLIC/'FROZEN_PROTOCOL.json'), packet_sha256=sha(packet), code_sha256=sha(Path(__file__)),
                evidence='ACTUALLY_RETAINED_CURRENT_SOURCE_AVAILABILITY_SHADOW; historical training features remain current-vintage seven-day reconstructions',
                caution='No outcomes or skill result; owner admission pending. A/B source/fit/prior/fallback routing fixed. C requires a separate verification.', new_fits=0, new_forecasts=0, week8_outcomes_read=0)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-root', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.private_root, args.source_root)
    Path(__file__).with_name('AVAILABILITY_AB_INDEPENDENT_REVIEW.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report))
