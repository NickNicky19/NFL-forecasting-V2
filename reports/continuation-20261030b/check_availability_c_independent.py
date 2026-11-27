"""Independent C refit-frame/model replay and A/B/C prediction-change math.

This inspects retained estimators only; no estimator.fit and no future outcomes.
"""
import argparse
from collections import defaultdict, Counter
from functools import lru_cache
import gzip
import hashlib
import json
import math
from pathlib import Path
import pickle
import sys
import warnings

import numpy as np
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'reports/continuation-20261030'))
from check_new_wave_prefixes import load, clock, canonical
from check_retained_distribution_math import summaries
PUBLIC = ROOT / 'reports/continuation-20261030b/availability-wave-v1'
POSITIONS = ('QB', 'RB', 'WR', 'TE')
COUNTS = ('pass_td', 'pass_cmp', 'pass_att', 'pass_int', 'rush_att', 'rec')


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def decode(path): return json.loads(gzip.decompress(path.read_bytes()))
def close(a, b):
    assert (a is None and b is None) or (a is not None and b is not None and math.isclose(float(a), float(b), rel_tol=3e-11, abs_tol=4e-10)), (a, b)
def prior(values, target):
    if not values: return {'kind': 'bernoulli', 'p': .5} if target == 'anytime_td' else {'kind': 'zero'}
    if target == 'anytime_td': return {'kind': 'bernoulli', 'p': (sum(values)+1)/(len(values)+2)}
    if target in COUNTS:
        mean = max(.05, sum(values)/len(values)); return {'kind': 'geometric', 'q': mean/(1+mean)}
    center = sorted(values)[(len(values)-1)//2]
    scale = max(50. if target == 'nick-chart-ppr-v1' else 1., sum(abs(v-center) for v in values)/len(values))
    return {'kind': 'signed', 'center': center, 'q': scale/(1+scale)}


def verify(private, source):
    protocol = json.loads((PUBLIC/'FROZEN_PROTOCOL.json').read_text())
    receipt = json.loads((PUBLIC/'C-RUN_RECEIPT.json').read_text())
    assert receipt['protocol_sha256'] == sha(PUBLIC/'FROZEN_PROTOCOL.json')
    packet = private/receipt['packet']['bundle_name']; assert sha(packet) == receipt['packet']['sha256']
    records = decode(packet)['rows']
    queries = json.loads((private/'frozen-queries.json').read_text()); byquery = {q['query_id']: q for q in queries}
    bindings = {r['key']: r for r in json.loads((PUBLIC/'FIXED_MODEL_BINDINGS.json').read_text())}
    features = {r['query_id']: r['B_features'] for r in decode(private/'features/QUERY_FEATURE_CHANGES.json.gz')}
    oldrows, history, games = load(source, protocol)
    asof, captured = clock(protocol['fixed_feature_origin_utc']), clock(protocol['qualified_2026_source_available_by'])
    persisted = clock(receipt['actual_persistence_completed_at'])
    available = {(r['game_id'], r['player_id']): min(r['available'], captured) if r['season'] == 2026 and games[r['game_id']]['week'] == 7 else r['available'] for r in oldrows}
    counts = Counter()

    @lru_cache(None)
    def oldfeature(player, position, target, cutoff):
        rs = [r for r in history.get(player, []) if r['available'] < cutoff][-8:]; values=[]
        for window in (3, 8):
            ys = [float(r['values'][target]) for r in rs[-window:] if r['values'][target] is not None]
            values.extend((sum(ys)/len(ys) if ys else math.nan, float(len(ys))))
        for lag in range(1, 5):
            r = rs[-lag] if len(rs) >= lag else None; value = r['values'][target] if r else None
            values.extend((float(value) if value is not None else math.nan, (cutoff-r['kickoff'])/86400 if r else math.nan, float(value is None)))
        values.extend(float(position == p) for p in POSITIONS)
        return values, rs[-1]['available'] if rs else None
    byfit = defaultdict(list)
    for r in records:
        assert r['availability_arm'] == 'C' and r['actual'] is None and r['actual_status'] == 'PENDING_FUTURE'
        assert r['week'] == 8 and r['season'] == 2026
        q = byquery[r['query_id']]
        assert r['feature_cutoff_utc'] == protocol['fixed_feature_origin_utc']
        if r['prediction'] is not None:
            assert clock(r['actual_generated_at']) <= persisted < clock(q['owner_input_cutoff_utc']) < clock(q['kickoff_utc'])
        else: assert r['status'] == 'ABSTAIN' and r['abstention_reason']
        counts['issued' if r['prediction'] is not None else 'abstained'] += 1
        if r.get('fit_binding'): byfit[r['fit_binding']].append(r)
    assert counts['issued'] == receipt['issued'] and counts['abstained'] == receipt['abstained']
    assert len(records) == receipt['output_views'] == 33927
    fits = list(PUBLIC.glob('C-FIT-*.json')); assert len(fits) == receipt['actual_fit_calls'] == receipt['retained_models'] == 99
    with threadpool_limits(limits=2):
        for path in fits:
            fit = json.loads(path.read_text()); binding = bindings[fit['key']]
            target, arm = binding['target'], binding['history_regime']
            roles = set(POSITIONS) if target == 'nick-chart-ppr-v1' else set(protocol['source_role_contract']['primary'][target] + protocol['source_role_contract']['extended'].get(target, []))
            floor = {'H-CURRENT': 2026, 'H-RECENT': 2025, 'H-MULTI': 2022}[arm]
            train = [r for r in oldrows if r['position'] in roles and r['values'][target] is not None and r['season'] >= floor and available[(r['game_id'], r['player_id'])] < asof]
            assert len(train) == fit['training_n']
            assert hashlib.sha256(canonical([(r['game_id'], r['player_id']) for r in train])).hexdigest() == fit['training_membership_sha256']
            assert all(r['kickoff'] < asof and not (r['season'] == 2026 and games[r['game_id']]['week'] > 7) for r in train)
            frames = [oldfeature(r['player_id'], r['position'], target, r['kickoff']) for r in train]
            assert all(maximum is None or maximum < r['kickoff'] for r, (_, maximum) in zip(train, frames))
            assert max((m for _, m in frames if m is not None), default=None) == fit['latest_training_feature_available']
            assert fit['historical_feature_rule'] == 'UNCHANGED_CONSERVATIVE_7DAY'
            assert fit['fit_cutoff_utc'] == protocol['fixed_feature_origin_utc']
            assert asof <= clock(fit['actual_fit_started_at']) <= clock(fit['actual_fit_completed_at']) <= persisted
            counts['training_membership_and_chronology_checks'] += 7
            modelpath = private/fit['model']['bundle_name']; assert sha(modelpath) == fit['model']['sha256']
            model = pickle.loads(gzip.decompress(modelpath.read_bytes())); counts['C_model_hashes_verified'] += 1
            if binding['family'] == 'ordered_leaf_cdf':
                x = np.asarray([f for f, _ in frames], dtype=float)
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore', RuntimeWarning); med = np.nanmedian(x, axis=0)
                med = np.where(np.isfinite(med), med, 0.)
                raw = np.column_stack((np.where(np.isfinite(x), x, med), ~np.isfinite(x))).astype(float)
                np.testing.assert_allclose(med, model.design.median, rtol=1e-12, atol=1e-10)
                np.testing.assert_allclose(raw.mean(axis=0), model.design.mean, rtol=1e-12, atol=1e-10)
                std = raw.std(axis=0); std = np.where(std > 1e-12, std, 1.)
                np.testing.assert_allclose(std, model.design.scale, rtol=1e-12, atol=1e-10)
                counts['training_only_transform_values'] += len(med) + len(std)*2
                saved = byfit[fit['key']]
                unique = {}; [unique.setdefault(r['query_id'], r) for r in saved if r['prediction'] is not None]
                chosen = []
                for want_fallback in (False, True):
                    candidate = next((r for r in unique.values() if (features[r['query_id']][3] <= 0) == want_fallback), None)
                    if candidate: chosen.append(candidate)
                for r in chosen:
                    q = byquery[r['query_id']]; f = features[r['query_id']]
                    rolevalues = [float(v['values'][target]) for v in train if v['position'] == q['position']]
                    law = prior(rolevalues or [float(v['values'][target]) for v in train], target)
                    if f[3] > 0:
                        x = np.asarray([[math.nan if v is None else v for v in f]])
                        design = np.column_stack((np.where(np.isfinite(x), x, model.design.median), ~np.isfinite(x))).astype(float)
                        leaf = model.estimator.apply(design)[0]
                        weights = sum((h[leaf[j]].toarray().ravel()/len(model.hist) for j,h in enumerate(model.hist)), start=np.zeros(len(model.support))); weights /= weights.sum()
                        law = dict(kind='mixture', support=model.support, weights=weights, prior=law)
                    d = summaries(law, None); scale = 50 if target == 'nick-chart-ppr-v1' else 1
                    for field in ('mean','lower_median','q05','q95','interval90_width'): close(r['distribution_summary'][field], d[field]/scale); counts['C_independent_law_summary_fields'] += 1
                    close(r['distribution_summary']['zero_mass'], d['zero_mass'])
                    assert r['distribution_summary']['crps'] is None and r['distribution_summary']['nll'] is None
                    counts['C_representative_leaf_laws'] += 1
            else:
                params=model.get_params()
                for k, v in protocol['models']['hgb'].items(): assert params[k] == v
                assert model.n_iter_ == 64
                saved=[r for r in byfit[fit['key']] if r['prediction'] is not None]
                x=np.asarray([[math.nan if v is None else v for v in features[r['query_id']]] for r in saved])
                preds=model.predict_proba(x)[:,list(model.classes_).index(1.)] if target=='anytime_td' else model.predict(x)
                for r,p in zip(saved,preds): close(r['prediction'], max(0.,p) if target in COUNTS else p); counts['C_HGB_predictions_replayed'] += 1
    # Independent prediction-change aggregates; these are not forecast errors.
    ab=json.loads((PUBLIC/'AB-RUN_RECEIPT.json').read_text());original=decode(private/ab['packet']['bundle_name'])['rows'];lookup={}
    for r in original+records:
        ident=(r['availability_arm'],r['target'],r['family'],r['history_regime'],r['product_id'],r['query_id']);assert ident not in lookup;lookup[ident]=r
    reports=json.loads((PUBLIC/'FORECAST_CHANGE_SUMMARY.json').read_text())
    for summary in reports:
        later,earlier=summary['contrast'].split('-');suffix=(summary['target'],summary['family'],summary['history_regime'],summary['product_id'])
        pairs=[(r,lookup[(earlier,)+k[1:]]) for k,r in lookup.items() if k[0]==later and k[1:5]==suffix]
        issued=[(a,b) for a,b in pairs if a['prediction'] is not None and b['prediction'] is not None]
        changes=[a['prediction']-b['prediction'] for a,b in issued]
        assert summary['query_cells']==len(pairs) and summary['paired_issued']==len(issued)
        assert summary['prediction_changed_n']==sum(d!=0 for d in changes)
        assert summary['later_fallback_changed_n']==sum(a['fallback']!=b['fallback'] for a,b in issued)
        close(summary['mean_signed_prediction_change'],math.fsum(changes)/len(changes) if changes else None)
        close(summary['mean_absolute_prediction_change'],math.fsum(map(abs,changes))/len(changes) if changes else None)
        close(summary['max_absolute_prediction_change'],max(map(abs,changes)) if changes else None)
        assert summary['forecast_skill_established'] is False and summary['score_state']=='PENDING_WEEK8_OUTCOMES'
        counts['ABC_prediction_change_aggregate_checks'] += 9
    amendment=json.loads((PUBLIC/'C-RESOURCE-AMENDMENT.json').read_text());cumulative=json.loads((PUBLIC/'CUMULATIVE_RESOURCE_RECEIPT.json').read_text())
    assert clock(amendment['registered_at_utc']) < min(clock(json.loads(f.read_text())['actual_fit_started_at']) for f in fits)
    assert cumulative['actual_cumulative_forecast_views']==len(original)+len(records)<=amendment['max_cumulative_forecast_rows']
    assert cumulative['actual_cumulative_fit_calls']==99 and cumulative['actual_cumulative_active_wall_seconds']<=900 and cumulative['actual_cumulative_active_cpu_seconds']<=1200
    return dict(status='PASS_C_RAW_TRAINING_CHRONOLOGY_TRANSFORMS_RETAINED_MODELS_AND_CHANGE_MATH',counts=dict(counts),all_AB_C_views=len(original)+len(records),forecast_change_views=len(reports),source_known_by_utc=protocol['qualified_2026_source_available_by'],C_persisted_at_utc=receipt['actual_persistence_completed_at'],C_packet_sha256=sha(packet),protocol_sha256=sha(PUBLIC/'FROZEN_PROTOCOL.json'),evidence='ACTUALLY_RETAINED_CURRENT_AVAILABILITY_SHADOW; C train-row features remain seven-day historical reconstruction',limits='No Week8 outcomes, grades, skill, offer or website claims. C changes refitting/label pool and priors; H-CURRENT fitting retains older feature memory.',new_fits=0,new_forecasts=0,week8_outcomes_read=0)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--private-root',type=Path,required=True);parser.add_argument('--source-root',type=Path,required=True);args=parser.parse_args();report=verify(args.private_root,args.source_root)
    Path(__file__).with_name('AVAILABILITY_C_INDEPENDENT_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
