"""Independent safe JSON inference; no fitted estimator or author predictor used."""
import gzip
import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
B = ROOT / 'reports/category-decision-release-01/B/anytime-current-v1'
FEATURES = ['mean3', 'n3', 'mean8', 'n8'] + [
    f'lag{i}_{f}' for i in range(1, 5) for f in ('value', 'age_days', 'missing')
] + [f'position_{p}' for p in ('QB', 'RB', 'WR', 'TE')]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def features(rows, query):
    prior = sorted((r for r in rows if r['player_id'] == query['player_id']
                    and r['available'] < query['cutoff']),
                   key=lambda r: (r['kickoff'], r['game_id']))[-8:]
    values = []
    for window in (3, 8):
        known = [r['values']['anytime_td'] for r in prior[-window:]
                 if r['values']['anytime_td'] is not None]
        values.extend([sum(known) / len(known) if known else None, float(len(known))])
    for lag in range(1, 5):
        row = prior[-lag] if lag <= len(prior) else None
        value = row['values']['anytime_td'] if row else None
        values.extend([value, (query['cutoff'] - row['kickoff']) / 86400 if row else None,
                       float(value is None)])
    values.extend(float(query['position'] == role) for role in ('QB', 'RB', 'WR', 'TE'))
    return values, max((r['available'] for r in prior), default=None)


def restore(model, values):
    """Iteratively traverse each plain JSON tree; do not call production code."""
    assert len(values) == len(FEATURES)
    total = model['baseline_logit']
    assert math.isfinite(total)
    for tree in model['trees']:
        index, seen = 0, set()
        while True:
            assert index not in seen and 0 <= index < len(tree)
            seen.add(index)
            node = tree[index]
            if node['leaf']:
                assert math.isfinite(node['value'])
                total += node['value']
                break
            assert isinstance(node['feature'], int) and 0 <= node['feature'] < len(FEATURES)
            value = values[node['feature']]
            if value is None:
                left = node['missing_left']
            else:
                assert math.isfinite(value)
                kind = node['threshold_kind']
                assert kind in ('FINITE', 'POS_INF', 'NEG_INF')
                threshold = node['threshold'] if kind == 'FINITE' else math.inf if kind == 'POS_INF' else -math.inf
                assert kind != 'FINITE' or math.isfinite(threshold)
                assert kind == 'FINITE' or node['threshold'] is None
                left = value <= threshold
            index = node['left'] if left else node['right']
    expval = math.exp(-abs(total))
    return 1 / (1 + expval) if total >= 0 else expval / (1 + expval)


def main():
    protocol = read(B / 'FROZEN_PROTOCOL.json')
    rows = read(B / 'EVENT_HISTORY.json.gz')
    basic = read(B / 'CURRENT_QUERIES.json')['basic']
    packet = read(B / 'MODEL.json.gz')
    model = packet['model']
    prepared = read(B / 'PREPARED_FORECASTS.json')
    attempt = read(B / 'FIT_ATTEMPT.json')
    cutoff = protocol['fit_cutoff']
    bindings = {f: sha(B / f) for f in ('FROZEN_PROTOCOL.json', 'EVENT_HISTORY.json.gz',
                'CURRENT_QUERIES.json', 'MODEL.json.gz', 'PREPARED_FORECASTS.json', 'FIT_ATTEMPT.json')}
    assert bindings['EVENT_HISTORY.json.gz'] == protocol['inputs_sha256']
    assert bindings['CURRENT_QUERIES.json'] == protocol['queries_sha256']
    assert bindings['MODEL.json.gz'] == prepared['model_sha256']
    assert bindings['FROZEN_PROTOCOL.json'] == packet['protocol_sha256']
    assert model['feature_order'] == FEATURES == protocol['feature_order']
    assert model['parameters'] == protocol['params'] and len(model['trees']) == 64
    assert model['classes'] == [0, 1]
    assert model['recipe'] == protocol['recipe']
    assert model['output'] == 'RAW_BINARY_EVENT_PROBABILITY_NOT_CALIBRATED_CONFIDENCE'
    assert all(r['available'] == r['kickoff'] + 604800 for r in rows)
    train = [r for r in rows if r['available'] < cutoff and r['values']['anytime_td'] is not None]
    members = json.dumps([(r['game_id'], r['player_id']) for r in train], sort_keys=True,
                         separators=(',', ':'), allow_nan=False).encode()
    assert hashlib.sha256(members).hexdigest() == packet['training_membership_sha256']
    assert len(train) == packet['training_rows'] == attempt['training_rows'] == 25830
    assert set(r['values']['anytime_td'] for r in train) == {0., 1.}
    assert max(r['available'] for r in train) == packet['latest_training_label'] < cutoff
    assert packet['fit_cutoff'] == cutoff
    qs = [q for q in basic if q['eligible']]
    assert len(qs) == 25 and prepared['basic'] == basic
    assert all(q['position'] in ('RB', 'WR', 'TE') and q['cutoff'] == cutoff for q in qs)
    hgbid = protocol['recipe'] + ':H-MULTI'
    empiricalid = 'empirical-player-history-control-v1:H-MULTI'
    saved = {(r['identity']['game_id'], r['identity']['player_id'], r['procedure_id']): r
             for r in prepared['predictions']}
    assert len(saved) == len(prepared['predictions']) == 50
    expected_keys = {(q['game_id'], q['player_id'], procedure)
                     for q in qs for procedure in (hgbid, empiricalid)}
    assert set(saved) == expected_keys
    independent, errors, sparse, examples = {}, [], [], []
    for q in qs:
        vector, latest = features(rows, q)
        p = restore(model, vector)
        own = [r['values']['anytime_td'] for r in train
               if r['player_id'] == q['player_id'] and r['position'] == q['position']]
        positional = [r['values']['anytime_td'] for r in train if r['position'] == q['position']]
        labels = own or positional
        reference = sum(labels) / len(labels) if labels else 0.
        for procedure, value in ((hgbid, p), (empiricalid, reference)):
            key = q['game_id'], q['player_id'], procedure
            record = saved[key]
            assert record['identity'] == q and record['own_prior_n'] == len(own)
            assert record['latest_feature_available'] == latest
            assert latest is None or latest < cutoff
            fallback = 'none' if procedure == hgbid or own else 'position_empirical' if positional else 'constant_zero'
            assert record['fallback'] == fallback
            assert math.isfinite(value) and 0 <= value <= 1
            error = abs(value - record['probability']); errors.append(error)
            assert error <= 1e-12
            assert abs(record['probability'] + record['complement'] - 1) <= 1e-15
            assert record['actual'] is None and record['actual_state'] == 'FUTURE_NOT_GRADED'
            assert all(record[k] is None for k in ('offered_sides', 'line', 'selected_side'))
            assert record['product'] == 'RAW_EVENT_PROBABILITY'
            assert record['confidence_status'] == 'UNCALIBRATED_RESEARCH_NOT_PER_PICK_CONFIDENCE_OR_EV'
            independent[key] = value
        if not own:
            sparse.append(dict(player_id=q['player_id'], role=q['position'], own_prior_n=0,
                               empirical_position_n=len(positional), empirical_probability=reference,
                               hgb_missing_history_probability=p,
                               latest_feature_available=latest,
                               hgb_fallback='none', empirical_fallback='position_empirical'))
        if len(examples) < 3:
            examples.append(dict(player_id=q['player_id'], role=q['position'], own_prior_n=len(own),
                                 hgb_probability=p, empirical_probability=reference,
                                 latest_feature_available=latest))
    assert {r['player_id'] for r in sparse} == {'00-0041178', '00-0041376'}
    # Independent per-row traversal versus list traversal, reversed queries and reversed history.
    reversed_result = {(q['game_id'], q['player_id'], hgbid): restore(model, features(list(reversed(rows)), q)[0])
                       for q in reversed(qs)}
    assert all(value == independent[key] for key, value in reversed_result.items())
    batch = [restore(model, features(rows, q)[0]) for q in qs]
    assert batch == [independent[(q['game_id'], q['player_id'], hgbid)] for q in qs]
    # Future mutation cannot enter any earlier query's history.
    future = dict(player_id=qs[0]['player_id'], game_id='SYNTHETIC_FUTURE_ONLY',
                  available=cutoff + 1, kickoff=cutoff + 1, values={'anytime_td': 1.})
    assert features(rows + [future], qs[0]) == features(rows, qs[0])
    res = prepared['resources']; budget = protocol['budget']
    assert attempt['calls'] == res['new_current_fits'] == 1 and res['new_historical_fits'] == 0
    assert res['wall_seconds'] <= budget['wall_seconds'] and res['cpu_seconds'] <= budget['cpu_seconds']
    assert res['peak_RSS_bytes'] <= budget['RSS_bytes']
    registered = datetime.fromisoformat(protocol['registered_UTC']).timestamp()
    started = datetime.fromisoformat(attempt['actual_started_UTC']).timestamp()
    completed = datetime.fromisoformat(packet['actual_fit_completed_UTC']).timestamp()
    prepared_at = datetime.fromisoformat(prepared['prepared_UTC']).timestamp()
    expiry = protocol['current_roster']['source_expires_at']
    assert cutoff <= registered < started <= completed <= prepared_at < expiry < qs[0]['kickoff']
    assert not prepared['eligible_capture'] and all(prepared[k] == 0 for k in ('new_offers', 'new_selections', 'new_grades'))
    result = dict(id='B-ANYTIME-CURRENT-POSTFIT-INDEPENDENT-RESTORATION-v1',
        reviewed_UTC=datetime.now(timezone.utc).isoformat(), verdict='PASS_IN_CHECKED_RESTORATION_SCOPE',
        input_and_artifact_sha256=bindings, review_code_sha256=sha(Path(__file__)),
        procedure=hgbid, reference=empiricalid, feature_count=len(FEATURES), trees=len(model['trees']),
        tree_nodes=sum(len(tree) for tree in model['trees']), training_rows=len(train),
        training_roles=dict(Counter(r['position'] for r in train)),
        training_membership_sha256=packet['training_membership_sha256'],
        latest_training_label=packet['latest_training_label'], fit_cutoff=cutoff,
        model_fit_completed_UTC=packet['actual_fit_completed_UTC'],
        eligible_players=len(qs), basic_players=len(basic), checked_forecasts=len(saved),
        max_absolute_saved_probability_error=max(errors), native_parity_owner_report=prepared['parity_max_abs'],
        checks=['Independent plain-JSON numerical tree traversal; no author predictor or estimator imported',
                'Twenty independent own-history features with strict availability and unknown slots retained',
                'Training identity hash, class order, finite logistic probabilities and binary complement mass',
                'Own empirical mean and position fallback recomputed on full eligible training membership',
                'Single/list/reversed-query/reversed-history identity parity',
                'Synthetic future-row feature invariance without fitting',
                'Actual fit/prepared clocks precede roster expiry; reported fit resource budget satisfied'],
        examples=examples, no_own_cases=sparse, resources=res,
        raw_hgb_probability_range=[min(batch), max(batch)],
        source_expiry_UTC=datetime.fromtimestamp(expiry, timezone.utc).isoformat(),
        scope_limits=['No new model fits, no original estimator loading and no independent fresh-fit reproduction.',
                      'Owner native-estimator parity is separately reported; this review independently restores plain JSON against all saved current rows.',
                      'Historical raw-source/feature sample and seven-day reconstruction limitations remain in the separate prefit receipt.',
                      'Current event/status admission, actual issue/persistence, remote publication and consumer receipt are separately owned by root.',
                      'No offered line, O/U selection, calibration claim, EV, grade, new completed football week or primary release is created.'],
        reviewer_new_fits=0, reviewer_model_restoration_cases=25,
        reviewer_new_issued_forecasts=0, reviewer_new_grades=0)
    dest = OUT / 'POSTFIT_RESTORATION_REVIEW_V1.json'
    assert not dest.exists()
    dest.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(verdict=result['verdict'], checked_forecasts=len(saved),
                         error=max(errors), sparse=len(sparse), output_sha256=sha(dest))))


if __name__ == '__main__':
    main()
