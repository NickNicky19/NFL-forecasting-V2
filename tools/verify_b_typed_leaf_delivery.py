#!/usr/bin/env python3
"""Bounded parity verification, not new forecasts or NFL accuracy evaluation.

Only authenticate and restore B's own previously recovered, hash-bound models.
No generic pickle/input route, source collection, fits or selector replay.
"""
from __future__ import annotations
import argparse
import collections
import gzip
import hashlib
import json
import math
import pickle
import platform
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from threadpoolctl import threadpool_limits
from nfl_v2 import hgb_control as source, qualified_defense_inputs as defense
from nfl_v2.distribution_laws import Law
from nfl_v2.typed_leaf_adapter import point_outputs

REPO = Path(__file__).resolve().parents[1]
PUB = REPO / 'reports/continuation-20261030c/qualified-defense-information-v1'
BASE = 'v2-qualified-position-defense-information-wave-v1'
TARGETS = ('pass_td', 'pass_cmp', 'rec_yd')


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.loads(Path(p).read_bytes())


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def bind(root, spec):
    p = root / spec['bundle_name']
    if p.stat().st_size != spec['bytes'] or digest(p) != spec['sha256']:
        raise ValueError('retained artifact bytes mismatch')
    return p


def stamp():
    return datetime.now(timezone.utc).isoformat()


def run(protocol_path, private_root, source_root, out):
    start, cpu = time.monotonic(), time.process_time()
    p = load(protocol_path)
    if out.exists():
        raise ValueError('immutable output exists')
    for b in p['code_bindings']:
        if digest(REPO / b['path']) != b['sha256']:
            raise ValueError('frozen verification code mismatch')
    original = load(PUB / 'FROZEN_PROTOCOL.json')
    if digest(PUB / 'FROZEN_PROTOCOL.json') != p['original_protocol_sha256']:
        raise ValueError('original protocol changed')
    for name, sha in original['helpers'].items():
        if digest(REPO / 'nfl_v2' / name) != sha:
            raise ValueError('origin helper changed')
    for s in original['source_ids']:
        if digest(source_root / s['name']) != s['sha256']:
            raise ValueError('origin source changed')
    rows, _, counts = source.load_source(source_root, original)
    games = source.schedules(source_root / 'games.csv')
    defense.attach_context(rows, games, source_root)
    lookup = {(r['game_id'], r['player_id']): r for r in rows}
    history = source.FeatureHistory(rows)
    dh = defense.build_history(rows, TARGETS)
    results, failures = [], []
    queries_checked = point_values_checked = single_rows = models = 0
    def guard():
        if time.monotonic() - start > p['budget']['wall_seconds']:
            raise ValueError('wall budget')
        if time.process_time() - cpu > p['budget']['cpu_seconds']:
            raise ValueError('CPU budget')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > p['budget']['peak_memory_bytes']:
            raise ValueError('RSS budget')
    with threadpool_limits(limits=2):
        for cell in p['cells']:
            guard()
            fit = load(REPO / cell['fit_path'])
            forecast = load(REPO / cell['forecast_path'])
            if digest(REPO / cell['fit_path']) != cell['fit_sha256'] or digest(REPO / cell['forecast_path']) != cell['forecast_sha256']:
                raise ValueError('origin receipt changed')
            qp = bind(private_root, fit['query_features'])
            fp = bind(private_root, forecast['packet'])
            qrows = json.loads(gzip.decompress(qp.read_bytes()))
            saved = json.loads(gzip.decompress(fp.read_bytes()))['rows']
            keyed = {(r['game_id'], r['player_id'], r['product_id']): r for r in saved}
            if len(keyed) != len(saved):
                raise ValueError('duplicate origin output')
            x, qs, age, target_age, features_checked = [], [], [], [], 0
            for packet in qrows:
                q = packet['query']
                native = lookup[q['game_id'], q['player_id']]
                if (native['season'], native['week'], native['team'], native['defense'], native['position']) != (q['season'], q['week'], q['team'], q['defense'], q['position']):
                    raise ValueError('source/query identity mismatch')
                if native['values'][q['target']] != q['actual']:
                    raise ValueError('origin label differs from bound source')
                own, clock = history.get(q['player_id'], q['position'], q['target'], q['cutoff'])
                full, audit = defense.augment(own, dh, q, fit['feature_floor'], fit['information_group'])
                clocks = [clock, audit.get('latest_local_available')]
                if fit['information_group'] == 'D2':
                    clocks.append(audit.get('latest_league_available'))
                maximum = max((c for c in clocks if c is not None), default=None)
                oldx = np.asarray(packet['features'], dtype=float)
                if not np.array_equal(full, oldx, equal_nan=True):
                    raise ValueError('source rebuilt feature vector differs')
                if audit != packet['defense_audit'] or maximum != packet['latest_consumed_feature_available']:
                    raise ValueError('context/consumed availability differs')
                if maximum is not None and maximum >= q['cutoff']:
                    raise ValueError('non-earlier source dependency')
                if maximum is not None:
                    age.append((q['cutoff'] - maximum) / 86400)
                valid = [r for r in history.rows.get(q['player_id'], []) if r['available'] < q['cutoff'] and r['values'][q['target']] is not None]
                if valid:
                    target_age.append((q['cutoff'] - valid[-1]['kickoff']) / 86400)
                x.append(oldx)
                qs.append(dict(q, latest_consumed_feature_available=maximum))
                features_checked += len(oldx)
            # These are our authenticated restored origin models, never arbitrary
            # transferred or untrusted pickle files. No current model substitutes.
            model = None
            if fit['model'] is not None:
                mp = bind(private_root, fit['model'])
                if fit['model']['sha256'] != cell['model_sha256']:
                    raise ValueError('frozen model binding differs')
                model = pickle.loads(gzip.decompress(mp.read_bytes()))
                if type(model).__module__ != 'nfl_v2.distribution_wave_v2' or type(model).__name__ != 'FittedLawModel':
                    raise ValueError('unexpected restored model type')
                models += 1
            priors = {k: Law(**v) for k, v in fit['prior_parameters'].items()}
            x = np.asarray(x)
            got = point_outputs(model=model, raw_features=x, feature_columns=fit['feature_columns'], fit=fit, queries=qs, priors=priors)
            matched, fallback, leaf_rows = [], collections.Counter(), 0
            for q, v in zip(qs, got):
                for product in ('mean', 'lower_median'):
                    r = keyed[q['game_id'], q['player_id'], product]
                    if r['procedure_id'] != cell['procedure_id'] or r['policy_id'] != 'H-MULTI-COMMON':
                        raise ValueError('exact procedure/policy differs')
                    if v[product] != r['prediction']:
                        raise ValueError('typed point differs from original saved output')
                    if v['fallback'] != r['fallback']:
                        raise ValueError('fallback route differs')
                    matched.append([q['game_id'], q['player_id'], product, v[product], v['fallback']])
                fallback[v['fallback']] += 1
                if v['law_reference'] != keyed[q['game_id'], q['player_id'], 'mean']['law_reference']:
                    raise ValueError('origin leaf/prior reference differs')
                leaf_rows += v['fallback'] == 'none'
            # Deterministic information-only sample, not selected by outcomes.
            order = sorted(range(len(qs)), key=lambda i: (qs[i]['cutoff'], qs[i]['game_id'], qs[i]['player_id']))
            chosen = {order[0], order[-1]}
            cold = [i for i in order if got[i]['fallback'] != 'none']
            if cold:
                chosen.add(cold[0])
            for i in sorted(chosen):
                single = point_outputs(model=model, raw_features=x[[i]], feature_columns=fit['feature_columns'], fit=fit,
                    queries=[dict(qs[i], actual=999999)], priors=priors)[0]
                if single != got[i]:
                    raise ValueError('batch/single or target-outcome mutation changed output')
                single_rows += 1
            queries_checked += len(qs)
            point_values_checked += 2 * len(qs)
            if queries_checked > p['budget']['max_query_rows']:
                raise ValueError('query row budget')
            results.append(dict(slot=fit['slot'], procedure_id=cell['procedure_id'], target=fit['target'],
                week=fit['week'], history='H-MULTI', feature_memory='COMMON-2022-MEMORY',
                output_products=['mean', 'lower_median'], query_rows=len(qs), point_values_checked=2*len(qs),
                feature_values_checked=features_checked, matched_output_digest=hashlib.sha256(canonical(matched)).hexdigest(),
                fallback_query_counts=dict(fallback), learned_leaf_reference_rows=leaf_rows,
                source_availability_age_days_min=min(age) if age else None,
                source_availability_age_days_max=max(age) if age else None,
                last_known_target_game_age_days_max=max(target_age) if target_age else None,
                fit_receipt_sha256=cell['fit_sha256'], model_sha256=cell['model_sha256'],
                query_features_sha256=fit['query_features']['sha256'], original_forecast_sha256=forecast['packet']['sha256'],
                source_feature_and_typed_output_parity='EXACT', batch_single_actual_mutation='EXACT',
                disposition='NO_DEFECT_FOUND_IN_CHECKED_SCOPE'))
            del model
    guard()
    receipt = dict(schema='B-typed-leaf-delivery-verification-v1', state='PASS',
        actual_completed_at_utc=stamp(), frozen_protocol_sha256=digest(protocol_path),
        models_restored=models, query_rows_checked=queries_checked, point_values_checked=point_values_checked,
        single_row_checks=single_rows, results=results, failures=failures,
        new_fit_calls=0, newly_issued_forecasts=0, new_NFL_accuracy_observations=0,
        new_test_weeks=0, original_predictions_replaced=0, private_new_row_bytes=0,
        software_verification_not_accuracy_tournament=True,
        limits=['Current/revised source reconstruction, not authenticated historical source vintages',
                'Representative batch/single checks; full row source/point equality for21bound origins',
                'No fresh current-query source, origin, offer, publication, consumer or served verification',
                'No Top Picks replay; remaining exact selector owned by website session',
                'No new five-week qualification or promotion from these checks'],
        environment=dict(python=platform.python_version(), numpy=np.__version__),
        resources=dict(wall_seconds=time.monotonic()-start, cpu_seconds=time.process_time()-cpu,
                       peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024, threads=2),
        source_counts=counts)
    out.write_text(json.dumps(receipt, sort_keys=True, indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ('results','source_counts')}))


if __name__ == '__main__':
    a = argparse.ArgumentParser()
    for x in ('protocol', 'private-root', 'source-root', 'out'):
        a.add_argument('--'+x, required=True, type=Path)
    args = a.parse_args()
    run(args.protocol, args.private_root, args.source_root, args.out)
