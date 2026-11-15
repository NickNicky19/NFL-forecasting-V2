"""SKILL forecast adapter into the pinned M2/C evaluator, not a new grader.

Restricted offers and row joins remain in memory. Only aggregates, commitments,
and source hashes are written. This command performs no fitting or collection.
The unchanged M2 reporting-table function is loaded from its authenticated AST;
all direction grading, uncertainty, selection, and calibration functions are
reused. Numerical W1--9 origins do not fill missing actual-offer weeks W1--4.
"""
from __future__ import annotations

import argparse
import ast
import collections
import copy
import math
import pathlib
import resource
import sys
import time
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BASE = ROOT / 'reports/information-skill-01/B'
M2_PATH = ROOT / 'reports/targeted-accuracy-w1w9-01/B/evaluation/score_m2_v1.py'
METHODS = ('SKILL_C0', 'SKILL_C1', 'SKILL_R0', 'SKILL_R1')
RETAINED = ('M2_P2_BIN', 'M2_C1_BIN', 'M2_C2_BIN', 'D_M2')
CONTRASTS = (('SKILL_C1', 'SKILL_C0'), ('SKILL_R1', 'SKILL_C1'),
             ('SKILL_R1', 'SKILL_R0'), ('SKILL_R0', 'SKILL_C0'))
TIER = ('TIER_B_CURRENT_VINTAGE_CHRONOLOGICAL_RETAINED_ACTUAL_SOURCE_LINES;'
        'QUOTE_CLOCK_UNKNOWN;MAIN_ALT_UNCLASSIFIED')


def load_evaluator():
    """Import trusted local code; require the frozen design's exact hashes."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('SKILL_PINNED_M2_EVAL', M2_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    design = module.read(BASE / 'FROZEN_DESIGN_V1.json')
    for name, digest in design['source_bindings'].items():
        if module.sha(ROOT / name) != digest:
            raise ValueError('Frozen SKILL source/code binding mismatch: ' + name)
    return module, design


def inherited_table(evaluator, summary, raw):
    """Reuse the exact existing report function, including empty-mask semantics."""
    tree = ast.parse(M2_PATH.read_text())
    main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    table = next(n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == 'table')
    namespace = dict(evaluator.__dict__, summary=summary, raw=raw)
    exec(compile(ast.Module(body=[table], type_ignores=[]), str(M2_PATH), 'exec'), namespace)
    original = namespace['table']

    def report(method, policy, window, rows, *, mode='RAW'):
        result = original(method, policy, window, rows, mode=mode)
        result.update(record_id='B-SKILL-EVAL-' + evaluator.digest(
            [method, policy, window, mode])[:24],
            evaluation_panel_id='B-SKILL-2026-NATIVE-QB142-pass_cmp',
            canonical_source_view=True, reused_forecasts=method not in METHODS,
            original_issuance=False)
        return result
    return report


def windows(rows):
    return [('ALL', rows)] + [(str(w), [r for r in rows if r['week'] == w])
                             for w in range(5, 10)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sources', 'scorer-source', 'interval-source'):
        parser.add_argument('--' + name, type=pathlib.Path, required=True)
    parser.add_argument('--predictions', type=pathlib.Path,
                        default=BASE / 'wave-v1/predictions')
    parser.add_argument('--retained-predictions', type=pathlib.Path,
                        default=ROOT / 'reports/targeted-accuracy-w1w9-01/B/wave-v1/predictions')
    parser.add_argument('--existing-cmp-grades', type=pathlib.Path,
                        help='Optional existing permitted B row grades; never published.')
    parser.add_argument('--out', type=pathlib.Path, default=BASE / 'evaluation-v1')
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError('Use a new versioned output directory; do not overwrite scores.')
    if not args.out.resolve().is_relative_to(BASE.resolve()):
        raise ValueError('Only the owned SKILL report subtree may receive outputs.')
    ev, design = load_evaluator()
    from nfl_v2 import player_context_matchup as ctx
    from nfl_v2.targeted_qb_m2 import restore_law
    from nfl_v2.paired_uncertainty import paired_losses
    started, cpu = time.monotonic(), time.process_time()
    adapter = ev.module(ROOT / 'reports/w1w9-comparison-closure-01/B/common-intake/'
                       'COMMON_SCORER_PARITY_ADAPTER_V1.py', 'SKILL_PINNED_C_ADAPTER')
    status, summary, _ = adapter.load_common_functions(args.scorer_source, args.interval_source)
    fixtures = adapter.boundary_fixtures(status)
    inventory = ev.module(ROOT / 'reports/player-context-matchup-01/B/independent/'
                          'inventory_retained_qb_offers_v1.py', 'SKILL_EXISTING_OFFER_ITERATOR')
    sources = {int(w): pathlib.Path(p) for w, p in ev.read(args.sources).items()}
    if set(sources) != set(range(5, 10)):
        raise ValueError('Exactly the frozen native W5--9 sources are required.')
    prior_bindings = ev.read(M2_PATH.parent / 'EXECUTION_INPUT_BINDINGS_V1.json')
    for binding in prior_bindings['source_files']:
        if ev.sha(sources[binding['week']]) != binding['sha256']:
            raise ValueError('Native offer source differs from the frozen M2 panel.')
    offers = [r for w, p in sorted(sources.items())
              for r in inventory.iter_offers(p, w) if r['target'] == 'pass_cmp']
    if len(offers) != 142 or len({ev.key(r) for r in offers}) != 142:
        raise ValueError('Expected the identical native142 completion board.')
    if collections.Counter(r['week'] for r in offers) != {5: 28, 6: 28, 7: 28, 8: 28, 9: 30}:
        raise ValueError('Frozen weekly opportunity counts changed.')
    if any(r['actual'] is None or r['label_state'] != 'SUPPORTED' or
           r['participation'] != 'VERIFIED_PLAYED_POSITIVE_PHYSICAL' or
           float(r['line']) % 1 != .5 for r in offers):
        raise ValueError('Native panel requires explicit qualified counts and half-point lines.')
    predictions, prediction_bindings = [], []
    retained_hashes = {r['file']: r['sha256'] for r in prior_bindings['prediction_files']}
    for directory, allowed in ((args.predictions, METHODS), (args.retained_predictions, RETAINED)):
        paths = sorted(directory.glob('2026-W*.json.gz'))
        if len(paths) != 9:
            raise ValueError('All nine saved numerical origins are required.')
        for path in paths:
            if allowed == RETAINED and ev.sha(path) != retained_hashes.get(path.name):
                raise ValueError('Retained M2 prediction hash differs from its scored binding.')
            body = ev.read(path)
            predictions.extend(r for r in body['rows'] if r['method'] in allowed)
            prediction_bindings.append(dict(file=path.name, role='new' if allowed == METHODS else 'retained',
                                            sha256=ev.sha(path)))
    predmap = {(r['method'], ev.key(r)): r for r in predictions}
    if len(predmap) != len(predictions):
        raise ValueError('Repeated saved forecast identity.')
    queries = ctx.load_inputs(ROOT / 'reports/information-first-20261112-01/B/'
                              'completion-wave-v1/QB_CONTEXT_W1_W9_INPUTS_V1.json.gz')
    querymap = {(r['game_id'], r['player_id']): r for r in queries}
    expected = {(r['game_id'], r['player_id'], 'pass_cmp') for r in queries if r['season'] == 2026}
    for method in METHODS + RETAINED:
        if {ev.key(r) for r in predictions if r['method'] == method} != expected:
            raise ValueError('Saved numerical query population differs: ' + method)
    origins = {w: min(ev.dt(r['fit_cutoff']) for r in predictions
                      if r['method'] == 'SKILL_C0' and r['week'] == w) for w in range(1, 10)}
    for r in predictions:
        if r['method'] not in METHODS:
            continue
        if r['target'] != 'pass_cmp' or ev.dt(r['fit_cutoff']) > ev.dt(r['kickoff']):
            raise ValueError('Wrong target or invalid forecast fit clock.')
        if ev.dt(r['feature_cutoff']) != ev.dt(r['kickoff']):
            raise ValueError('Changed query feature horizon.')
        parent = predmap['M2_C2_BIN', ev.key(r)]
        if r['components']['attempt_law'] != parent['components']['attempt_law']:
            raise ValueError('The fixed attempt law changed.')
        attempt = r['components']['attempt_law']
        mixture = r['components']['predicted_context_mix']
        conversion = r['components']['conditional_completion_probability']
        if (len(mixture) != 25 or len(conversion) != 25 or
                any(not math.isfinite(v) or v < 0 or v > 1 for v in mixture + conversion) or
                abs(math.fsum(mixture) - 1) > 1e-10):
            raise ValueError('Invalid future context mixture or conversion support.')
        expected_mean = attempt['mean'] * math.fsum(w * p for w, p in zip(mixture, conversion))
        if (r['law'].get('kind') != 'gamma_poisson_count' or
                r['law']['shape'] != attempt['shape'] or abs(expected_mean - r['mean']) > 1e-8):
            raise ValueError('Count law does not match the fixed-exposure thinning contract.')
        if r['method'] == 'SKILL_C0' and (r['law'] != parent['law'] or
                r['mean'] != parent['mean'] or r['lower_median'] != parent['lower_median']):
            raise ValueError('C0 must preserve the exact retained C2 output.')
    law_cache = {}

    def law_for(r):
        identity = r['method'], ev.key(r)
        if identity not in law_cache:
            law_cache[identity] = restore_law(r['law'])
        return law_cache[identity]

    def forecast_row(offer, method, policy, prediction):
        row = adapter.common_row(offer, None, appearance='PLAYED', status='UNAVAILABLE_FORECAST')
        row.update(target='pass_cmp', kickoff=offer['kickoff'], line_from=offer['line_from'],
                   method=method, component_policy=policy, procedure_id=method,
                   point=None, probs=None, available=prediction is not None,
                   unavailable_reason=None if prediction else 'MISSING_EXACT_SAVED_FORECAST',
                   fallback=None, parent_fallback=False, attribution='unavailable', original_issuance=False)
        if prediction is not None:
            if prediction.get('actual') is not None and prediction['actual'] != offer['actual']:
                raise ValueError('Frozen forecast and qualified outcome differ.')
            law = law_for(prediction)
            probs = ctx.exact_probabilities(law, offer['line'])
            if any(not math.isfinite(p) or p < 0 or p > 1 for p in probs.values()) or abs(sum(probs.values()) - 1) > 1e-9:
                raise ValueError('Invalid exact-line law masses.')
            if abs(law.mean - prediction['mean']) > 1e-7:
                raise ValueError('Wrong typed expected count.')
            point = prediction['mean' if policy == 'MEAN' else 'lower_median'] if policy != 'LAW' else None
            if point is not None and not math.isfinite(point):
                raise ValueError('Nonfinite typed point.')
            side = ev.lawside(probs) if policy == 'LAW' else ('OVER' if point > offer['line'] else 'UNDER' if point < offer['line'] else 'ABSTAIN')
            fallback = prediction.get('fallback')
            row.update(procedure_id=prediction['procedure_id'], point=point, probs=probs,
                       selected_side=side, status='ABSTAIN' if side == 'ABSTAIN' else 'READY',
                       fallback=fallback, parent_fallback=ev.fallback(fallback),
                       attribution='fallback' if ev.fallback(fallback) else 'learned')
        row['status'] = status(row)
        return row

    raw = {(method, policy): [forecast_row(o, method, policy, predmap.get((method, ev.key(o)))) for o in offers]
           for method in METHODS + RETAINED for policy in ('MEAN', 'MEDIAN', 'LAW')}
    for method, side in (('ALWAYS_OVER', 'OVER'), ('ALWAYS_UNDER', 'UNDER')):
        rows = []
        for offer in offers:
            row = forecast_row(offer, method, 'REGISTERED_DIRECTION', None)
            row.update(available=True, unavailable_reason=None, selected_side=side, status='READY',
                       attribution='reference')
            row['status'] = status(row)
            rows.append(row)
        raw[method, 'REGISTERED_DIRECTION'] = rows
    imported_controls = []
    if args.existing_cmp_grades:
        existing = ev.read(args.existing_cmp_grades)['rows']
        policy_map = {'P1_MEAN': 'MEAN', 'P1_LOWER_MEDIAN': 'MEDIAN', 'P2_STATISTICAL_LAW': 'LAW',
                      'REGISTERED_DIRECTION': 'REGISTERED_DIRECTION'}
        for key in ('B0', 'B2', 'SAVED_ADJUSTED', 'SAVED_RAW', 'EARLIER_LINE_PREVALENCE'):
            for original_policy, policy in policy_map.items():
                rows = [r for r in existing if r['model_key'] == key and r['policy'] == original_policy]
                if not rows:
                    continue
                lookup = {ev.key(r): r for r in rows}
                if len(lookup) != len(rows):
                    raise ValueError('Duplicate retained control opportunity.')
                result = []
                for offer in offers:
                    previous = lookup.get(ev.key(offer))
                    current = forecast_row(offer, 'RETAINED_' + key, policy, None)
                    if previous is not None:
                        if previous['actual'] != offer['actual'] or previous['line'] != offer['line']:
                            raise ValueError('Retained control line/outcome contract mismatch.')
                        current.update({k: previous.get(k) for k in ('point', 'probs', 'fallback', 'procedure_id')})
                        current.update(selected_side=previous['selected_side'], available=previous['available'],
                                       unavailable_reason=previous.get('unavailable_reason'),
                                       attribution=previous.get('attribution', 'reference'), status=previous['status'])
                        current['parent_fallback'] = ev.fallback(current['fallback'])
                        current['status'] = status(current)
                    result.append(current)
                raw['RETAINED_' + key, policy] = result
                imported_controls.append(['RETAINED_' + key, policy])
    table = inherited_table(ev, summary, raw)
    tables, selective, proper, broad, pairs, selected_frames, calibration_trace = [], [], [], [], [], {}, []
    for (method, policy), rows in raw.items():
        tables.extend(table(method, policy, window, subset) for window, subset in windows(rows))
        if method in METHODS:
            for window, subset in [('DK_ONLY', [r for r in rows if r['line_from'] == 'dk']),
                                   ('SLEEPER_ONLY', [r for r in rows if r['line_from'] == 'sleeper']),
                                   ('LEARNED_ONLY', [r for r in rows if r['attribution'] == 'learned']),
                                   ('FALLBACK_ONLY', [r for r in rows if r['attribution'] == 'fallback'])]:
                tables.append(table(method, policy, window, subset))
    selective_methods = list(METHODS + RETAINED)
    selective_methods += [m for m in ('RETAINED_B0', 'RETAINED_B2') if (m, 'LAW') in raw]
    for method in selective_methods:
        rows = raw[method, 'LAW']
        cal = []
        for w in range(5, 10):
            subset = [r for r in ev.calibrated(rows, origins[w]) if r['week'] == w]
            cal.extend(subset)
            calibration_trace.append(dict(method=method, week=w, origin=origins[w].isoformat(),
                                          n_min=min(r['calibration_n'] for r in subset),
                                          n_max=max(r['calibration_n'] for r in subset),
                                          identity_startups=sum(r['calibration_n'] == 0 for r in subset)))
        for num, den, name in ((1, 1, 'COVERAGE_100'), (1, 2, 'COVERAGE_50'),
                               (1, 4, 'COVERAGE_25'), (1, 10, 'COVERAGE_10')):
            chosen = set().union(*(ev.choose_fraction([r for r in rows if r['week'] == w], num, den) for w in range(5, 10)))
            selected_frames[method, name] = ev.apply_selection(rows, chosen)
        for k in (6, 10, 20):
            for pool in ('Combined', 'OVER', 'UNDER'):
                chosen = set().union(*(ev.choose_top([r for r in rows if r['week'] == w], k, pool) for w in range(5, 10)))
                selected_frames[method, f'TOP_{k}_{pool}'] = ev.apply_selection(rows, chosen)
        for threshold in (.75, .8, .9):
            for mode, frame in (('RAW', rows), ('CALIBRATED_RELIABILITY', cal)):
                chosen = {ev.key(r) for r in frame if r['available'] and r['selected_side'] in ('OVER', 'UNDER') and
                          (r['calibrated_selected_confidence'] if mode != 'RAW' else r['probs'][r['selected_side'].lower()]) >= threshold}
                selected_frames[method, f'THRESHOLD_{int(threshold * 100)}_{mode}'] = ev.apply_selection(frame, chosen)
        for (m, policy), frame in selected_frames.items():
            if m == method:
                mode = 'CALIBRATED_RELIABILITY' if policy.endswith('CALIBRATED_RELIABILITY') else 'RAW'
                selective.extend(table(method, policy, w, rr, mode=mode) for w, rr in windows(frame))
        for mode, frame in (('RAW', rows), ('CALIBRATED_RELIABILITY', cal)):
            for window, subset in windows(frame):
                stats = ev.probstats(subset, 'probs' if mode == 'RAW' else 'calibrated_probs')
                proper.append(dict(record_id='B-SKILL-PROB-' + ev.digest([method, mode, window])[:24],
                    record_kind='prop_threshold_probability_evaluation', method=method, procedure_id=rows[0]['procedure_id'],
                    category='pass_cmp', target='pass_cmp', season=2026, actual_weeks=sorted({r['week'] for r in subset}),
                    window=window, week_view=window, policy='RAW_EXACT_LINE_LAW' if mode == 'RAW' else 'CALIBRATED_RAW_SIDE_CORRECTNESS_BERNOULLI',
                    n=stats['events'], probability_events=stats['events'], brier=stats['half_three_state_Brier'],
                    strict_binary_Over_Brier=stats['strict_binary_Over_Brier'], log_loss=stats['log_loss'],
                    reliability=stats, eligible=len(subset), available=sum(r['available'] for r in subset),
                    unavailable=sum(not r['available'] for r in subset), points=None,
                    games=len({r['game_id'] for r in subset}), evidence_tier=TIER, primary_admission='LOCAL_NOT_C_ADMITTED',
                    probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',
                    probability_conditioning='MODELED_APPEARANCE', history_regime='H-RECENT',
                    population='FULL_DECLARED_NATIVE_QB_OFFER_BOARD;CONDITIONAL_QUALIFIED_PLAYED_LABELS',
                    evaluation_panel_id='B-SKILL-2026-NATIVE-QB142-pass_cmp',
                    membership_SHA256=ev.digest(sorted(ev.key(r) for r in subset)),
                    calibration_mode=mode, joint_scope='SELECTED_SIDE_BERNOULLI_NOT_COUNT_CDF' if mode != 'RAW' else 'RAW_COUNT_LAW'))

    def paired(candidate, policy, left, control, control_policy, right, scope, metric='SELECTION_LOSS_RATE'):
        lookup = {ev.key(r): r for r in right}
        same = [(r, lookup[ev.key(r)]) for r in left if ev.key(r) in lookup and
                r['status'] in ('WIN', 'LOSS') and lookup[ev.key(r)]['status'] in ('WIN', 'LOSS')]
        def loss(r):
            if metric == 'SELECTION_LOSS_RATE':
                return int(r['status'] == 'LOSS')
            if metric == 'ABSOLUTE_NUMERICAL_ERROR':
                return abs(r['point'] - r['actual'])
            if metric == 'STRICT_BINARY_OVER_BRIER':
                return (r['probs']['over'] - int(r['actual'] > r['line'])) ** 2
            event = 'over' if r['actual'] > r['line'] else 'under' if r['actual'] < r['line'] else 'push'
            return -math.log(r['probs'][event]) if r['probs'][event] > 0 else math.inf
        if metric == 'ABSOLUTE_NUMERICAL_ERROR':
            same = [(r, s) for r, s in same if r['point'] is not None and s['point'] is not None]
        elif metric != 'SELECTION_LOSS_RATE':
            same = [(r, s) for r, s in same if r['probs'] is not None and s['probs'] is not None]
        return dict(candidate=candidate, policy=policy, control=control, control_policy=control_policy,
                    target='pass_cmp', scope=scope, metric=metric, history_regime='H-RECENT',
                    candidate_selected=sum(r['selected_side'] in ('OVER', 'UNDER') for r in left),
                    common_decided=len(same), candidate_wins=sum(r['status'] == 'WIN' for r, _ in same),
                    control_wins=sum(s['status'] == 'WIN' for _, s in same),
                    side_disagreements=sum(r['selected_side'] != s['selected_side'] for r, s in same),
                    membership_SHA256=ev.digest(sorted(ev.key(r) for r, _ in same)),
                    **paired_losses([loss(r) for r, _ in same], [loss(s) for _, s in same],
                                    [(2026, r['week']) for r, _ in same], [r['game_id'] for r, _ in same]))
    for candidate, control in CONTRASTS:
        for policy in ('MEAN', 'MEDIAN', 'LAW'):
            pairs.append(paired(candidate, policy, raw[candidate, policy], control, policy,
                                raw[control, policy], 'MATCHED_COMPLETE_PIPELINE'))
        for metric in ('STRICT_BINARY_OVER_BRIER', 'EXACT_LINE_LOG_LOSS'):
            pairs.append(paired(candidate, 'LAW', raw[candidate, 'LAW'], control, 'LAW',
                                raw[control, 'LAW'], 'MATCHED_COMPLETE_PIPELINE_PROBABILITY', metric))
        for policy in ('MEAN', 'MEDIAN'):
            pairs.append(paired(candidate, policy, raw[candidate, policy], control, policy,
                                raw[control, policy], 'MATCHED_OFFERED_NUMERICAL', 'ABSOLUTE_NUMERICAL_ERROR'))
    controls = [(m, p) for m, p in raw if m in RETAINED or m.startswith('RETAINED_') or m.startswith('ALWAYS_')]
    for method in METHODS:
        for policy in ('MEAN', 'MEDIAN', 'LAW'):
            for control, cp in controls:
                pairs.append(paired(method, policy, raw[method, policy], control, cp, raw[control, cp], 'MATCHED_FULL_BOARD'))
        for (m, policy), frame in selected_frames.items():
            if m == method:
                for control, cp in controls:
                    pairs.append(paired(method, policy, frame, control, cp, raw[control, cp],
                                        'CANDIDATE_OWN_SELECTED_CASES_CONTROL_BROAD_SIDES'))
    for method in METHODS + RETAINED:
        group = [r for r in predictions if r['method'] == method]
        for output in ('mean', 'lower_median'):
            for window, subset in [('ALL', group)] + [(str(w), [r for r in group if r['week'] == w]) for w in range(1, 10)]:
                numeric_rows, unknown, count_losses, infinite = [], 0, [], 0
                for r in subset:
                    q = querymap.get((r['game_id'], r['player_id']))
                    if q is None or not q.get('physical_participation') or not q.get('target_parity') or q['official_completions'] is None:
                        unknown += 1
                        continue
                    actual = q['official_completions']
                    numeric_rows.append(dict(point=r[output], actual=actual))
                    law = law_for(r)
                    value = law.logpmf(actual) if hasattr(law, 'logpmf') else math.log(law.pmf(actual)) if law.pmf(actual) > 0 else -math.inf
                    if math.isfinite(value):
                        count_losses.append(-value)
                    else:
                        infinite += 1
                broad.append(dict(record_id='B-SKILL-NUMERIC-' + ev.digest([method, output, window])[:24],
                    record_kind='forecast_evaluation_view', method=method, procedure_id=group[0]['procedure_id'],
                    target='pass_cmp', category='pass_cmp', season=2026, window=window, week_view=window,
                    actual_weeks=sorted({r['week'] for r in subset}), output=output, eligible=len(subset),
                    available=len(subset), unknown=unknown, games=len({r['game_id'] for r in subset}),
                    numerical=ev.numeric(numeric_rows), count_log_loss='Infinity' if infinite else sum(count_losses) / len(count_losses) if count_losses else None,
                    law_events=len(count_losses) + infinite, infinite_count_logloss_cases=infinite,
                    fallback_states=dict(collections.Counter(str(r.get('fallback')) for r in subset)),
                    evidence_tier='CURRENT_VINTAGE_7DAY_CHRONOLOGICAL_RECONSTRUCTION;STAT_ROW_CONDITIONAL_QUERY_UNIVERSE;NO_OFFER_REQUIRED',
                    primary_admission='LOCAL_NOT_C_ADMITTED', history_regime='H-RECENT',
                    evaluation_panel_id='B-SKILL-2026-QB-STAT-ROW-NUMERICAL'))
    fixture = raw['SKILL_C0', 'LAW']
    changed = copy.deepcopy(fixture)
    for row in changed:
        if row['week'] == 9:
            row['actual'] += 1000
            row['status'] = 'LOSS' if row['status'] == 'WIN' else 'WIN'
    before, after = ev.calibrated(fixture, origins[7]), ev.calibrated(changed, origins[7])
    if [r.get('calibrated_probs') for r in before if r['week'] <= 7] != [r.get('calibrated_probs') for r in after if r['week'] <= 7]:
        raise AssertionError('Future outcomes changed earlier reliability calibration.')
    for denominator in (1, 2, 4, 10):
        for week in range(5, 10):
            rows = [r for r in fixture if r['week'] == week]
            chosen = ev.choose_fraction(rows, 1, denominator)
            for kickoff in sorted({r['kickoff'] for r in rows}, key=ev.dt):
                prefix = [r for r in rows if ev.dt(r['kickoff']) <= ev.dt(kickoff)]
                if ev.choose_fraction(prefix, 1, denominator) != {ev.key(r) for r in prefix if ev.key(r) in chosen}:
                    raise AssertionError('Fixed-coverage selection changed an earlier decision batch.')
    old_tables = ev.read(M2_PATH.parent / 'MAIN_TABLES_V1.json.gz')
    membership = ev.digest(sorted(ev.key(r) for r in offers))
    references = [r for r in old_tables if r['method'] in ('RETAINED_B0', 'RETAINED_B2', 'RETAINED_EARLIER_LINE_PREVALENCE') and r['window'] == 'ALL']
    if any(r['membership_SHA256'] != membership for r in references):
        raise ValueError('Public aggregate controls are on a different opportunity mask.')
    canonical = tables + selective + broad + proper
    if len({r['record_id'] for r in canonical}) != len(canonical):
        raise ValueError('Duplicate canonical record identity.')
    bindings = dict(design_sha256=ev.sha(BASE / 'FROZEN_DESIGN_V1.json'), code_sha256=ev.sha(__file__),
                    inherited_evaluator_sha256=ev.sha(M2_PATH), prediction_files=prediction_bindings,
                    C_scorer_sha256=ev.sha(args.scorer_source), C_interval_sha256=ev.sha(args.interval_source),
                    existing_CMP_grades_sha256=ev.sha(args.existing_cmp_grades) if args.existing_cmp_grades else None,
                    source_files=[dict(week=w, sha256=ev.sha(p)) for w, p in sorted(sources.items())])
    outputs = {'EXECUTION_INPUT_BINDINGS_V1.json': bindings, 'MAIN_TABLES_V1.json.gz': tables,
               'SELECTIVE_TABLES_V1.json.gz': selective, 'PROBABILITY_TABLES_V1.json.gz': proper,
               'BROAD_NUMERICAL_TABLES_V1.json.gz': broad, 'PAIRED_COMPARISONS_V1.json': pairs,
               'CALIBRATION_SUPPORT_TRACE_V1.json': calibration_trace, 'SCORES.json': canonical,
               'PUBLIC_RETAINED_CONTROL_REFERENCES_V1.json': dict(source_sha256=ev.sha(M2_PATH.parent / 'MAIN_TABLES_V1.json.gz'),
                   records=references, imported_row_controls=imported_controls,
                   limitation='Aggregate-only controls establish no new paired row parity or selection membership. B0/B2 paired and own-list views exist only when exact permitted row inputs were supplied.'),
               'MEMBERSHIP_COMMITMENTS_V1.json': [dict(method=m, policy=p,
                   selected=sum(r['selected_side'] in ('OVER', 'UNDER') for r in rows),
                   selected_keys_sha256=ev.digest(sorted(ev.key(r) for r in rows if r['selected_side'] in ('OVER', 'UNDER'))))
                   for (m, p), rows in selected_frames.items()]}
    if time.process_time() - cpu > 600 or time.monotonic() - started > 900:
        raise RuntimeError('Inherited evaluation compute cap exceeded before publication.')
    # No source locators, raw offers, grade rows, or player-level predictions are emitted.
    for filename, body in outputs.items():
        ev.write(args.out / filename, body)
    public_bytes = sum(p.stat().st_size for p in args.out.iterdir() if p.is_file())
    if public_bytes > 8388608:
        raise RuntimeError('Inherited8MiB aggregate evaluation cap exceeded; preserve version, no automatic retry.')
    receipt = dict(state='EXECUTED_SKILL_LOCAL_NOT_C_ADMITTED', at_UTC=datetime.now(timezone.utc).isoformat(),
        models=list(METHODS), native_CMP_offers=142, actual_offer_weeks=list(range(5, 10)),
        missing_offer_weeks=[1, 2, 3, 4], numeric_weeks=list(range(1, 10)), native_games=71,
        main_views=len(tables), selective_views=len(selective), broad_numeric_views=len(broad),
        proper_probability_views=len(proper), canonical_views=len(canonical), paired_views=len(pairs),
        boundary_fixtures=fixtures, frozen_policy_count_per_method=19,
        future_outcome_mutation='PASS_EARLIER_CALIBRATION_UNCHANGED', batch_prefix_invariance='PASS',
        source_reads_by_execution=0, new_fits=0, new_NFL_observations=0, original_pregame_selections=0,
        private_restricted_rows_written=0, public_bytes=public_bytes,
        CPU_seconds=time.process_time() - cpu, wall_seconds=time.monotonic() - started,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        C_or_website_admission=False, code_sha256=ev.sha(__file__), design_id=design['id'])
    ev.write(args.out / 'RUN_RECEIPT_V1.json', receipt)
    print(ev.json.dumps({k: receipt[k] for k in ('state', 'native_CMP_offers', 'canonical_views', 'paired_views', 'CPU_seconds')}))


if __name__ == '__main__':
    from threadpoolctl import threadpool_limits
    with threadpool_limits(limits=2):
        main()
