"""Frozen COMMON_EXPOSURE saved-output adapter to the pinned C grader."""
import argparse
import collections
import gzip
import hashlib
import importlib.util
import json
import math
import resource
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = HERE.parent
OUT = HERE / 'native-attempts'


def read(p):
    p = Path(p)
    return json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def write(path, value):
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    path.write_bytes(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def count_cdf(mean, shape, threshold):
    # Exact gamma-Poisson finite CDF recurrence, mathematically the same NB law.
    k = math.floor(threshold)
    if k < 0:
        return 0.
    if mean == 0:
        return 1.
    probability = shape / (shape + mean)
    mass = probability ** shape
    terms = [mass]
    for j in range(k):
        mass *= (j + shape) / (j + 1) * (1 - probability)
        terms.append(mass)
    return math.fsum(terms)


def exact_probs(law, line):
    mean, shape = law['mean'], law['shape']
    assert law['kind'] == 'gamma_poisson_count'
    assert math.isfinite(mean) and mean >= 0 and math.isfinite(shape) and shape > 0
    k = math.floor(line)
    under = count_cdf(mean, shape, k - 1 if line == k else k)
    below = count_cdf(mean, shape, k)
    result = dict(over=1 - below, under=under, push=below - under)
    assert all(math.isfinite(v) and v >= -1e-14 for v in result.values())
    assert abs(sum(result.values()) - 1) < 1e-12
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('action', choices=['prepare', 'score'])
    for name in ['sources', 'scorer-source', 'interval-source', 'private-output']:
        ap.add_argument('--' + name, type=Path, required=True)
    args = ap.parse_args()
    sources = {int(w): Path(p) for w, p in read(args.sources).items()}
    prediction_paths = [ROOT / f'reports/player-context-matchup-01/B/qb-wave-v1/predictions/2026-W{w:02}.json.gz'
                        for w in range(5, 9)] + [BASE / 'modern-completion-extension/PREDICTIONS_2026_W09.json.gz']
    inputs = ROOT / 'reports/information-first-20261112-01/B/completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz'
    adapter_path = BASE / 'common-intake/COMMON_SCORER_PARITY_ADAPTER_V1.py'
    iterator_path = ROOT / 'reports/player-context-matchup-01/B/independent/inventory_retained_qb_offers_v1.py'
    roster = BASE / 'roster/FROZEN_B_CONTRIBUTION_ROSTER_V1.json'
    protocol_path = OUT / 'FROZEN_PROTOCOL_V1.json'
    if args.action == 'prepare':
        write(protocol_path, dict(
            id='B_NATIVE_ATT_COMMON_EXPOSURE_FIXED_SAVED_OUTPUTS_v1',
            state='FROZEN_BEFORE_NEW_ATT_COMPARATIVE_SCORES',
            at_UTC=datetime.now(timezone.utc).isoformat(), owner='B', coordinator='C',
            procedure='B-player-context-matchup-01-v1:COMMON_EXPOSURE',
            category='pass_att', role='QB', weeks=[5, 6, 7, 8, 9], expected_offers=142,
            history='Original strict seven-day availability; own 8 eligible games, shared QB prior; original analytical gamma-Poisson exposure and fallback.',
            policies=['P1_MEAN', 'P1_LOWER_MEDIAN', 'P2_STATISTICAL_LAW', 'P90_EXISTING_0.90_THRESHOLD'],
            controls=['ALWAYS_OVER', 'ALWAYS_UNDER', 'SAVED_ADJUSTED', 'SAVED_RAW', 'EARLIER_LINE_PREVALENCE'],
            decision='Strict unrounded point vs exact line; P2 Over/Under mass argmax; ties abstain; P90 unchanged selected-side mass >= .90.',
            panel='Retained native W5-9 actual-source-labelled attempts; 141 DraftKings + one W6 Sleeper Picks source-labelled market; quote clocks and main/alternate unverified.',
            source_owner_receipt='Root inspected exact W6 build/books code at 5bffd5c332b8cf8fa625089047013b4da2176377; DK-first then Sleeper Picks market, separate provider projection. Raw API flags and quote clocks not preserved.',
            numerical='Only typed mean/median and saved point controls; no point error assigned to P2/P90.',
            probability='Strict-binary Over and half-multiclass Brier; exact three-state logloss; reliability; physical-participation conditioning, not guaranteed venue nonvoid.',
            population='Native exact offers only; no annual87 union, original issuance, full W1-9 or league-complete claim.',
            tuning='None; no new mechanisms, fit or threshold search.',
            source_bindings=[dict(week=w, sha256=sha(p), bytes=p.stat().st_size) for w, p in sorted(sources.items())],
            input_bindings={str(p.relative_to(ROOT)): sha(p) for p in prediction_paths + [inputs, adapter_path, iterator_path, roster]},
            C_scorer_sha256=sha(args.scorer_source), C_interval_sha256=sha(args.interval_source),
            budgets=dict(cpu_seconds=180, peak_extra_memory_bytes=134217728, public_bytes=2097152, HTTP=0, fits=0),
            source_code_sha256=sha(__file__)))
        print(json.dumps(dict(state='FROZEN', protocol_sha256=sha(protocol_path))))
        return
    start = time.monotonic()
    cpu = time.process_time()
    protocol = read(protocol_path)
    assert protocol['source_code_sha256'] == sha(__file__)
    for name, expected in protocol['input_bindings'].items():
        assert sha(ROOT / name) == expected
    for b in protocol['source_bindings']:
        assert sha(sources[b['week']]) == b['sha256']
    adapter = module(adapter_path, 'existing_C_adapter')
    status, summary, _ = adapter.load_common_functions(args.scorer_source, args.interval_source)
    adapter.boundary_fixtures(status)
    iterator = module(iterator_path, 'existing_offer_iterator')
    offers = [r for w, path in sorted(sources.items()) for r in iterator.iter_offers(path, w) if r['target'] == 'pass_att']
    assert len(offers) == len({(r['game_id'], r['player_id'], r['line']) for r in offers}) == 142
    assert all(r['participation'] == 'VERIFIED_PLAYED_POSITIVE_PHYSICAL' and r['label_state'] == 'SUPPORTED' and r['actual'] is not None for r in offers)
    queries = read(inputs)
    qindex = {(r['game_id'], r['player_id']): r for r in queries}
    qualified_history = [r for r in queries if r.get('physical_participation') and r['target_parity']]
    predictions = {}
    source_hashes = {}
    for path in prediction_paths:
        for r in read(path)['rows']:
            if r['method'] == 'COMMON_EXPOSURE' and r['target'] == 'pass_att':
                key = (r['game_id'], r['player_id'])
                assert key not in predictions
                predictions[key] = r
                source_hashes[key] = sha(path)
    allrows = {}
    for name in ['P1_MEAN', 'P1_LOWER_MEDIAN', 'P2_STATISTICAL_LAW', 'P90'] + protocol['controls']:
        rows = []
        for offer in offers:
            key = (offer['game_id'], offer['player_id'])
            q = qindex[key]
            assert q['official_attempts'] == offer['actual'] and q['physical_participation']
            assert q['team'] and q['opponent']
            pred = predictions.get(key)
            point = probs = side = None
            reason = fallback = None
            if name.startswith('P'):
                if pred is None:
                    reason = 'SAVED_ORIGIN_OUTPUT_UNAVAILABLE'
                else:
                    assert pred['procedure_id'] == protocol['procedure']
                    assert pred['actual'] == offer['actual']
                    assert pred['feature_cutoff'] == q['kickoff']
                    assert pred['fit_cutoff'] <= q['kickoff']
                    assert pred['law']['mean'] == pred['mean']
                    probs = exact_probs(pred['law'], offer['line'])
                    fallback = pred.get('fallback')
                    if name.startswith('P1_'):
                        point = pred['mean' if name == 'P1_MEAN' else 'lower_median']
                        side = 'OVER' if point > offer['line'] else 'UNDER' if point < offer['line'] else None
                    else:
                        side = 'OVER' if probs['over'] > probs['under'] else 'UNDER' if probs['under'] > probs['over'] else None
                        if name == 'P90' and side and probs[side.lower()] < .90:
                            side = None
            elif name in ['SAVED_ADJUSTED', 'SAVED_RAW']:
                point = offer.get('prediction' if name == 'SAVED_ADJUSTED' else 'raw_prediction')
                if point is None or not math.isfinite(point):
                    reason = 'RETAINED_POINT_UNAVAILABLE'
                    point = None
                else:
                    side = 'OVER' if point > offer['line'] else 'UNDER' if point < offer['line'] else None
            elif name in ['ALWAYS_OVER', 'ALWAYS_UNDER']:
                side = 'OVER' if name == 'ALWAYS_OVER' else 'UNDER'
            else:
                history = [r['official_attempts'] for r in qualified_history if r['available'] < q['kickoff'] and r['season'] >= q['season'] - 1]
                assert all(y is not None for y in history)
                integer = float(offer['line']).is_integer()
                denominator = len(history) + (3 if integer else 2)
                probs = dict(over=(sum(y > offer['line'] for y in history) + 1) / denominator,
                             under=(sum(y < offer['line'] for y in history) + 1) / denominator,
                             push=(sum(y == offer['line'] for y in history) + 1) / denominator if integer else 0.)
                side = 'OVER' if probs['over'] > probs['under'] else 'UNDER' if probs['under'] > probs['over'] else None
            row = dict(game_id=offer['game_id'], player_id=offer['player_id'], category='pass_att', position='QB',
                       season=2026, week=offer['week'], actual=offer['actual'], line=offer['line'],
                       selected_side=side if side else None if reason else 'ABSTAIN', appearance='PLAYED',
                       status='UNAVAILABLE_FORECAST' if reason else 'ABSTAIN' if side is None else 'READY',
                       comparator='STRICT_OVER_UNDER', period='FULL_GAME_INCLUDING_OT',
                       scoring_contract_id='OFFICIAL_FULL_GAME_QB_CREDITED_PASS_ATTEMPTS_EXCLUDES_SACKS',
                       model_key='COMMON_EXPOSURE' if name.startswith('P') else name, policy=name,
                       procedure_id=protocol['procedure'] if name.startswith('P') else 'B_EXISTING_CONTROL:' + name,
                       point=point, probs=probs, available=reason is None, unavailable_reason=reason,
                       fallback=fallback, line_from=offer['line_from'], kickoff=offer['kickoff'],
                       source_forecast_sha256=source_hashes.get(key) if name.startswith('P') else None,
                       original_issuance=False)
            row['status'] = status(row)
            rows.append(row)
        allrows[name] = rows

    def table(name, rows, view):
        result = summary(rows)
        errors = [r['point'] - r['actual'] for r in rows if r['point'] is not None]
        probabilistic = [r for r in rows if r['probs'] is not None]
        bins = []
        for i in range(10):
            included = [r for r in probabilistic if i / 10 <= r['probs']['over'] < (i + 1) / 10 or i == 9 and r['probs']['over'] == 1]
            if included:
                bins.append(dict(lower=i / 10, upper=(i + 1) / 10, n=len(included),
                                 predicted=sum(r['probs']['over'] for r in included) / len(included),
                                 observed=sum(r['actual'] > r['line'] for r in included) / len(included)))
        binary = [(r['probs']['over'] - int(r['actual'] > r['line'])) ** 2 for r in probabilistic]
        multiclass = [.5 * sum((r['probs'][event] - int(event == ('over' if r['actual'] > r['line'] else 'under' if r['actual'] < r['line'] else 'push'))) ** 2 for event in ['over', 'under', 'push']) for r in probabilistic]
        logs = [-math.log(r['probs']['over' if r['actual'] > r['line'] else 'under' if r['actual'] < r['line'] else 'push']) for r in probabilistic]
        result.update(model_key='COMMON_EXPOSURE' if name.startswith('P') else name,
                      procedure_id=protocol['procedure'] if name.startswith('P') else 'B_EXISTING_CONTROL:' + name,
                      category='pass_att', role='QB', policy=name, week_view=view,
                      available=sum(r['available'] for r in rows), selected=result['COMBINED']['selected'],
                      decided=result['COMBINED']['decided'], unknown=0,
                      fallback_states=dict(collections.Counter(str(r['fallback']) for r in rows if r['available'])),
                      missing_reasons=dict(collections.Counter(r['unavailable_reason'] for r in rows if not r['available'])),
                      source_labels=dict(collections.Counter(r['line_from'] for r in rows)),
                      numerical=dict(scored=len(errors), **{k: (sum(abs(e) if k == 'MAE' else e * e if k == 'MSE' else e for e in errors) / len(errors) if errors else None) for k in ['MAE', 'MSE', 'bias']}),
                      probability=dict(events=len(probabilistic), binary_Over_Brier=sum(binary) / len(binary) if binary else None,
                                       half_multiclass_Brier=sum(multiclass) / len(multiclass) if multiclass else None,
                                       three_state_log_loss=sum(logs) / len(logs) if logs else None,
                                       binary_Over_reliability=bins, conditioning='MODELED_PHYSICAL_PARTICIPATION_NOT_VENUE_NONVOID'),
                      membership_sha256=digest(sorted((r['game_id'], r['player_id'], r['line']) for r in rows)),
                      evidence_tier='TIMING_UNVERIFIED_ACTUAL_SOURCE_LABELLED_CURRENT_VINTAGE_DIAGNOSTIC',
                      main_alternate_status='UNCLASSIFIED', original_issuance=False)
        return result

    tables = []
    for name, rows in allrows.items():
        for view, chosen in [('ALL', rows)] + [(str(w), [r for r in rows if r['week'] == w]) for w in range(5, 10)] + [('DK_ONLY', [r for r in rows if r['line_from'] == 'dk'])]:
            tables.append(table(name, chosen, view))
    sys.path.insert(0, str(ROOT))
    from nfl_v2.paired_uncertainty import paired_losses
    paired = []
    for policy in ['P1_MEAN', 'P1_LOWER_MEDIAN', 'P2_STATISTICAL_LAW']:
        for control in protocol['controls']:
            left = allrows[policy]
            right = allrows[control]
            matches = [(a, b) for a, b in zip(left, right) if a['status'] in ['WIN', 'LOSS'] and b['status'] in ['WIN', 'LOSS']]
            outcome = paired_losses([int(a['status'] == 'LOSS') for a, b in matches], [int(b['status'] == 'LOSS') for a, b in matches],
                                    [(a['season'], a['week']) for a, b in matches], [a['game_id'] for a, b in matches])
            outcome.update(left=policy, right=control, side_disagreements=sum(a['selected_side'] != b['selected_side'] for a, b in matches))
            paired.append(outcome)
    write(args.private_output / 'NATIVE_ATT_ROWS_V1.json.gz', dict(rows=[r for rows in allrows.values() for r in rows]))
    write(OUT / 'TABLES_V1.json', tables)
    write(OUT / 'PAIRED_V1.json', paired)
    primary = [r for r in tables if r['week_view'] == 'ALL']
    candidate = [r for r in primary if r['policy'] in ['P1_MEAN', 'P1_LOWER_MEDIAN', 'P2_STATISTICAL_LAW']]
    highest = max(r['COMBINED']['rate'] for r in candidate)
    leaders = [dict(policy=r['policy'], record=r['COMBINED']) for r in candidate if r['COMBINED']['rate'] == highest]
    write(OUT / 'DECISION_V1.json', dict(highest_observed_COMMON_EXPOSURE_products=leaders,
          controls=[dict(name=r['model_key'], record=r['COMBINED']) for r in primary if r['model_key'] != 'COMMON_EXPOSURE'],
          recommendation='SHADOW_NO_AUTOMATIC_PRIMARY_REPLACEMENT',
          coverage='PARTIAL_W5_W9; W1-W4 not supplied to this native panel. Annual87 W1-W5 retained separately.',
          status_90='TARGET_NOT_ESTABLISHED', duration='Five diagnostic season-week blocks; not authentic quote-time qualification or full W1-W9.',
          limits='Not a complete ABC attempt championship. Unprovided other-model outputs remain unevaluated, not losers.'))
    resources = dict(wall_seconds=time.monotonic() - start, cpu_seconds=time.process_time() - cpu,
                     peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                     public_bytes=sum(p.stat().st_size for p in OUT.iterdir() if p.is_file()))
    assert resources['cpu_seconds'] < 180 and resources['peak_RSS_bytes'] < 134217728
    assert resources['public_bytes'] < 2097152
    write(OUT / 'RUN_V1.json', dict(state='EXECUTED_SAVED_OUTPUT_NATIVE_ATT', resources=resources,
          new_HTTP=0, new_fits=0, new_forecasts=0, new_NFL_games=0,
          protocol_sha256=sha(protocol_path), code_sha256=sha(__file__),
          private_rows_sha256=sha(args.private_output / 'NATIVE_ATT_ROWS_V1.json.gz'),
          C_scorer_sha256=sha(args.scorer_source), C_interval_sha256=sha(args.interval_source)))
    print(json.dumps(dict(state='EXECUTED', resources=resources, leaders=leaders)))


if __name__ == '__main__':
    main()
