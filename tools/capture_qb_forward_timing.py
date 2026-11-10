"""One manually registered future-origin QB shadow; no collection or scheduler.

This is not a rerun of the closed historical timing experiment. It fits the
two unchanged unaugmented recipes at a new real origin, with held source games
explicitly excluded. It never invents an offer, participation, or starter.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import platform
import resource
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import numpy as np
import sklearn
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nfl_v2 import player_context_matchup as ctx
from nfl_v2.distribution_laws import prior
from nfl_v2.distribution_wave_v2 import FittedLawModel, FOREST
from nfl_v2.qb_aligned_freshness import CONTROL, ALTERNATIVE, reconstruct_rows
from nfl_v2.qb_context_profiles import query_validation

VERSION = 'B-QB-FORWARD-TIMING-SHADOW-v1'


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    data = Path(path).read_bytes()
    return json.loads(gzip.decompress(data) if str(path).endswith('.gz') else data)


def write_new(path, value):
    path = Path(path)
    if path.exists():
        raise ValueError('Frozen artifact exists; preserve it')
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    path.write_bytes(gzip.compress(data, mtime=0) if str(path).endswith('.gz') else data)


def feature_query(query, cutoff):
    # ContextHistory names its cutoff kickoff. Actual event time is retained
    # separately in the immutable query and output; no target outcome is read.
    if not math.isfinite(cutoff) or cutoff > query['kickoff']:
        raise ValueError('Invalid feature cutoff')
    return dict(query, kickoff=cutoff)


def event_reason(event, query, request_at):
    expected = dict(game_id=query['game_id'], native_event_id=query['native_event_id'],
        season=query['season'], week=query['week'], kickoff=query['kickoff'],
        state='pre', status_name='STATUS_SCHEDULED', completed=False, season_type=2)
    if any(event.get(k) != v for k, v in expected.items()) or event.get('completed') is not False:
        return 'EVENT_STATUS_OR_IDENTITY_MISMATCH'
    for key in ('observed_at', 'retained_at', 'expires_at'):
        if isinstance(event.get(key), bool) or not isinstance(event.get(key), (float, int)) or not math.isfinite(event[key]):
            return 'UNKNOWN_EVENT_CLOCK'
    if not event['observed_at'] <= event['retained_at'] <= request_at < min(event['expires_at'], query['kickoff'] - 300):
        return 'EXPIRED_OR_FUTURE_EVENT_RECEIPT'
    if (event.get('competition_id') != event.get('native_event_id') or
        {event.get('home_team'), event.get('away_team')} != {query['team'], query['opponent']}):
        return 'EVENT_COMPETITION_OR_TEAMS_MISMATCH'
    if event['expires_at'] > event['observed_at'] + 1800:
        return 'UNBOUND_EVENT_EXPIRY'
    try:
        expiry = http_expiry(event['observed_at'], event.get('HTTP_Age'), event.get('HTTP_Date'))
    except ValueError:
        return 'UNQUALIFIED_NATIVE_HTTP_CLOCK'
    if event['expires_at'] != expiry or not request_at < expiry:
        return 'NATIVE_HTTP_RESPONSE_EXPIRED'
    return None


def http_expiry(observed, raw_age, raw_date):
    """Same C1800s/5s-skew guard, independently calculated; missing != zero."""
    candidates = [observed + 1800]
    known = False
    if raw_age not in (None, ''):
        try:
            age = float(raw_age)
        except (ValueError, TypeError):
            raise ValueError('Malformed HTTP Age') from None
        if not math.isfinite(age) or not 0 <= age <= 1800:
            raise ValueError('Stale/nonfinite HTTP Age')
        known = True
        candidates.append(observed + 1800 - age)
    if raw_date not in (None, ''):
        try:
            parsed = parsedate_to_datetime(raw_date)
            if parsed.tzinfo is None:
                raise ValueError('Naive HTTP Date')
            date = parsed.timestamp()
        except (TypeError, ValueError, OverflowError):
            raise ValueError('Malformed HTTP Date') from None
        if not -5 <= observed - date <= 1800:
            raise ValueError('Stale/future HTTP Date')
        known = True
        candidates.append(date + 1800)
    if not known:
        raise ValueError('HTTP Date and Age unknown')
    return min(candidates)


def run(protocol_path):
    started_wall, started_cpu = time.monotonic(), time.process_time()
    protocol_path = Path(protocol_path).resolve()
    p = read(protocol_path)
    out = protocol_path.parent
    if p['id'] != VERSION or p['max_new_fits'] != 2:
        raise ValueError('Unregistered capture')
    for binding in p['bindings']:
        if digest(ROOT / binding['path']) != binding['sha256']:
            raise ValueError('Bound input/code changed')
    cutoff = p['feature_cutoff']
    if datetime.fromisoformat(p['registered_utc']).timestamp() > cutoff:
        raise ValueError('Origin precedes real registration')
    rows = ctx.load_inputs(ROOT / p['inputs'])
    queries = read(ROOT / p['queries'])['queries']
    orders = read(ROOT / p['feature_order'])['orders']
    predictions, resources = [], []
    with threadpool_limits(limits=2):
        for arm, policy in [('F0', CONTROL), ('F2', ALTERNATIVE)]:
            model_path = out / 'models' / (arm + '.json.gz')
            if model_path.exists():
                raise ValueError('Current model already fitted; restore, do not refit')
            derived, unresolved = reconstruct_rows(rows, policy)
            if unresolved:
                raise ValueError('Unresolved history clock')
            history = ctx.ContextHistory(derived, 8, 20)
            train = [r for r in derived if r['physical_participation'] and r['target_parity']
                     and r['season'] >= p['season'] - 1 and r['available'] < cutoff]
            membership = [(r['game_id'], r['player_id']) for r in train]
            x = np.asarray([history.direct_features(r, 'E3') for r in train])
            if x.shape[1] != len(orders[arm]):
                raise ValueError('Named feature width')
            y = np.asarray([r['official_completions'] for r in train])
            pr = prior(y, 'pass_cmp')
            fit_started = now()
            attempt = dict(arm=arm, actual_started_utc=fit_started, training_rows=len(train))
            write_new(out / 'fit-attempts' / (arm + '.json'), attempt)
            model = FittedLawModel('ordered_leaf_cdf', 'pass_cmp').fit(x, y, ['QB'] * len(y))
            payload = ctx.export_forest(model)
            record = dict(id=VERSION + ':' + arm, model=payload, policy=policy, fit_started_utc=fit_started,
                fit_completed_utc=now(), actual_new_fit_calls=1, fit_cutoff=cutoff,
                training_rows=len(train), membership_sha256=hashlib.sha256(json.dumps(membership).encode()).hexdigest(),
                training_membership=membership, latest_training_label=max(r['available'] for r in train),
                feature_count=x.shape[1], named_feature_order=orders[arm], fixed_forest=FOREST,
                input_sha256=digest(ROOT / p['inputs']), protocol_sha256=digest(protocol_path))
            write_new(model_path, record)
            for q in queries:
                reason = query_validation(q, 'SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE')
                identity = {k: q[k] for k in ('game_id', 'native_event_id', 'player_id', 'name', 'team', 'opponent', 'position', 'season', 'week', 'kickoff', 'provider_status')}
                base = dict(identity=identity, arm=arm, recipe='B-QB-ALIGNED-FRESHNESS-v1:' + arm,
                    current_shadow_id=VERSION + ':' + arm, feature_cutoff=cutoff,
                    model_path=str(model_path.relative_to(ROOT)), model_sha256=digest(model_path),
                    actual_inferred_utc=now(), actual=None, actual_status='FUTURE_NOT_GRADED',
                    exact_offer=None, side=None, selection=False, original_website_selection=False,
                    role_contract='CURRENT_KNOWN_BASIC_QB_CONDITIONAL_APPEARANCE_NOT_STARTER_OR_APPEARANCE_PROBABILITY',
                    information_policy=policy)
                if reason or q['provider_status'] != 'ACT':
                    predictions.append(dict(base, status='BASIC_ONLY_UNAVAILABLE_FORECAST', reason=reason or 'NON_ACT_PROVIDER_STATUS_NOT_A_HEALTH_OR_STARTER_INFERENCE'))
                    continue
                work = feature_query(q, cutoff)
                features = history.direct_features(work, 'E3')
                law = ctx.restored_forest_law(payload, features, pr)
                original = model.predict(features[None, :], ['QB'], {'QB': pr})[0][0]
                if abs(law.mean - original.mean) > 1e-10 or law.quantile(.5) != original.quantile(.5):
                    raise ValueError('Retained-model inference parity')
                d = history.describe(work)
                own = history.player_rows(q['player_id'], cutoff)
                predictions.append(dict(base, status='PREPARED_FUTURE_FORECAST_EVENT_RECONFIRMATION_REQUIRED',
                    mean=law.mean, mean_type='EXPECTED_MEAN', lower_median=law.quantile(.5), median_type='LOWER_MEDIAN',
                    law=dict(kind='leaf_mixture', support=law.support.tolist(), weights=law.weights.tolist(),
                        prior=law.prior.parameters(), mixture=law.b),
                    own_prior_games=len(own), own_game_ids=[r['game_id'] for r in own],
                    latest_own_game=None if not own else own[-1]['game_id'],
                    latest_own_game_time=None if not own else own[-1]['kickoff'],
                    latest_own_reconstructed_available=None if not own else max(r['available'] for r in own),
                    last_source_age_days=d['latest_own_source_age_days'],
                    fallback=dict(learned_model=True, earlier_label_prior_mixture=.05,
                        own_history_missing=not bool(own), incumbent=False),
                    probability_status='EXPERIMENTAL_COUNT_LAW_NOT_CALIBRATED_CONFIDENCE_OR_EV',
                    target_outcome_not_accessed=True))
            resources.append(dict(arm=arm, fits=1, training_rows=len(train), feature_count=x.shape[1]))
    elapsed = time.monotonic() - started_wall
    if elapsed > p['budget']['wall_seconds'] or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 > p['budget']['RSS_bytes']:
        raise ValueError('Registered resource allocation exceeded; retain fitted evidence')
    write_new(out / 'PREPARED_FORECASTS.json.gz', dict(id=VERSION, prepared_utc=now(),
        protocol_sha256=digest(protocol_path), predictions=predictions,
        eligible_capture=False, reason='FRESH_INDEPENDENT_EVENT_RECONFIRMATION_AND_DURABLE_PUBLICATION_NOT_YET_VERIFIED',
        resources=dict(new_current_origin_fits=2, repeated_historical_fits=0, wall_seconds=elapsed,
            cpu_seconds=time.process_time()-started_cpu, peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            by_arm=resources), environment=dict(python=platform.python_version(), numpy=np.__version__, sklearn=sklearn.__version__)))
    print(json.dumps(dict(state='PREPARED_NOT_CAPTURED', predictions=len(predictions), learned=sum('mean' in r for r in predictions), new_current_origin_fits=2, wall_seconds=elapsed)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('protocol')
    run(ap.parse_args().protocol)
