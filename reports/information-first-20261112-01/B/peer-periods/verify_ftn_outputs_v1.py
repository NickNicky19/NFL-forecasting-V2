"""Independent output arithmetic. No author scorer, fit, or inference imports.

Reads protected offer rows owner-locally; publishes aggregates and commitments only.
The old independently authored Decimal/tree helpers are reused by file binding.
"""
import argparse
import collections
import datetime
import decimal
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path

D = decimal.Decimal
decimal.getcontext().prec = 50


def read(path):
    b = Path(path).read_bytes()
    return json.loads(gzip.decompress(b) if str(path).endswith('.gz') else b)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def key(row):
    return row['game_id'], row['player_id'], row['target']


def equal(a, b, tol=2e-11):
    if a is None or b is None:
        assert a is b, (a, b)
    else:
        assert abs(float(a)-float(b)) <= tol, (a, b)


def state(actual, line, side):
    if side is None:
        return 'ABSTAIN'
    if actual is None:
        return 'UNKNOWN_PARTICIPATION'
    a, b = D(str(actual)), D(str(line))
    return 'PUSH' if a == b else 'WIN' if (a > b) == (side == 'over') else 'LOSS'


def pointside(point, line):
    if point is None:
        return None
    a, b = D(str(point)), D(str(line))
    return 'over' if a > b else 'under' if a < b else None


def probabilities(row, line, independent):
    law = row['law']
    if law['kind'] == 'leaf_mixture':
        cdf, mean, median = independent.decimal_law(row)
        under = cdf(math.ceil(D(str(line)))-1)
        over = D(1)-cdf(math.floor(D(str(line))))
        out = dict(over=float(over), under=float(under), push=float(D(1)-over-under))
        # Separate IEEE path verifies exact author probability commitments.
        fp = independent.float_probs(row, line)
        for event in out:
            equal(out[event], fp[event], 2e-12)
        return fp
    assert law['kind'] == 'gamma_poisson_count'
    mu, shape = D(str(law['mean'])), D(str(law['shape']))
    p = shape/(shape+mu)
    mass = p**shape
    cumulative = D(0)
    line = D(str(line))
    under = D(0)
    at = D(0)
    for count in range(math.floor(line)+1):
        if count:
            mass *= (D(count-1)+shape)/D(count)*(1-p)
        cumulative += mass
        if D(count) < line:
            under += mass
        elif D(count) == line:
            at = mass
    return dict(over=float(1-cumulative), under=float(under), push=float(at))


def probability_score(rows):
    rs = [r for r in rows if r['actual'] is not None and r['probs'] is not None]
    if not rs:
        return dict(n=0, brier=None, log_loss=None, infinite_log_losses=0)
    losses, logs = [], []
    for row in rs:
        actual, line = D(str(row['actual'])), D(str(row['line']))
        event = 'over' if actual > line else 'under' if actual < line else 'push'
        p = {k:D(str(v)) for k,v in row['probs'].items()}
        losses.append(sum((p[k]-int(k == event))**2 for k in ('over','under','push'))/2)
        logs.append(-math.log(float(p[event])) if p[event] > 0 else math.inf)
    infinite = sum(not math.isfinite(x) for x in logs)
    return dict(n=len(rs), brier=float(sum(losses)/len(rs)),
                log_loss=None if infinite else math.fsum(logs)/len(rs), infinite_log_losses=infinite)


def check_reliability(rows, reported):
    good = [r for r in rows if r['actual'] is not None and r['probs'] is not None]
    if not good:
        return
    points = []
    for row in good:
        p = row['probs']
        event = 'over' if D(str(row['actual'])) > D(str(row['line'])) else 'under' if D(str(row['actual'])) < D(str(row['line'])) else 'push'
        side = 'over' if p['over'] > p['under'] else 'under' if p['under'] > p['over'] else None
        points.append((max(p['over'],p['under']),None if side is None else int(side == event),p['over'],event == 'over'))
    assert reported['probability_direction_ties'] == sum(p[1] is None for p in points)
    for interval in reported['reliability']:
        hi = 1.0000001 if interval['upper'] == 1 else interval['upper']
        matches = [p for p in points if interval['lower'] <= p[0] < hi and p[1] is not None]
        assert interval['n'] == len(matches)
        equal(interval['mean_predicted'],math.fsum(p[0] for p in matches)/len(matches) if matches else None)
        equal(interval['correct_direction_rate'],sum(p[1] for p in matches)/len(matches) if matches else None)
    positive = [p[2] for p in points if p[3]]
    negative = [p[2] for p in points if not p[3]]
    auc = math.fsum(float(a > b)+.5*float(a == b) for a in positive for b in negative)/(len(positive)*len(negative)) if positive and negative and all(r['probs']['push'] == 0 for r in good) else None
    equal(auc,reported['over_event_AUC'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', type=Path, required=True)
    ap.add_argument('--wave', type=Path, required=True)
    ap.add_argument('--scores', type=Path, required=True)
    ap.add_argument('--sources', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    helper_path = args.repo/'reports/next-generation-information-research-01/B/peer-coordination/verify_depth_role_outputs_v1.py'
    spec = importlib.util.spec_from_file_location('prior_independent_decimal_verifier', helper_path)
    independent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(independent)
    rows = [r for p in sorted((args.wave/'predictions').glob('*.json.gz')) for r in read(p)['rows']]
    assert len(rows) == 979*3
    assert len({(r['method'],key(r)) for r in rows}) == len(rows)
    bindings, offers = [], []
    for week, path in sorted(read(args.sources).items(), key=lambda kv:int(kv[0])):
        week, path = int(week), Path(path)
        bindings.append(dict(week=week, SHA256=sha(path)))
        offers.extend(r for r in read(path)['rows'] if r['target'] == 'pass_cmp')
    assert len(offers) == 142 and len({key(r) for r in offers}) == 142
    controls = [r for p in sorted((args.repo/'reports/player-context-matchup-01/B/qb-wave-v1/predictions').glob('2026-*.gz'))
                for r in read(p)['rows'] if r['method'] in ('E1','P1','E3')]
    controls += [r for p in sorted((args.repo/'reports/player-context-matchup-01/B/qb-charting-wave-v1/predictions').glob('2026-*.gz'))
                 for r in read(p)['rows'] if r['method'] == 'F2']
    inputs = read(args.wave/'QB_CONTEXT_W1_W9_INPUTS_V1.json.gz')
    qmap = {(r['game_id'],r['player_id']):r for r in inputs}
    eligible = [r for r in inputs if r['physical_participation'] and r['target_parity']]
    own = collections.defaultdict(list)
    for r in eligible:
        own[r['player_id']].append(r)
    for rs in own.values():
        rs.sort(key=lambda r:(r['kickoff'],r['game_id']))
    for query in inputs:
        if query['season'] not in (2025,2026):
            continue
        history = [r for r in own[query['player_id']] if r['available'] < query['kickoff']][-8:]
        ys = sorted(D(str(r['official_completions'])) for r in history)
        controls.append(dict(method='OWN8',game_id=query['game_id'],player_id=query['player_id'],target='pass_cmp',
                             mean=float(sum(ys)/len(ys)) if ys else None,lower_median=float(ys[(len(ys)-1)//2]) if ys else None,
                             actual=query['official_completions'] if query['physical_participation'] else None))
    indexed = {(r['method'],key(r)):r for r in rows+controls}
    lawchecks = 0
    for row in rows:
        cdf, mean, median = independent.decimal_law(row)
        equal(mean,row['mean'])
        assert median == row['lower_median'] and cdf(-1) == 0
        assert 0 <= cdf(0) <= 1 and abs(float(cdf(100000))-1) < 1e-12
        assert all(float(v).is_integer() and v >= 0 for v in row['law']['support'])
        lawchecks += 1
    for row in rows:
        if row['method'] == 'B1':
            baseline = indexed['B0',key(row)]
            assert (row['mean'],row['lower_median'],row['law'],row['fallback']) == (baseline['mean'],baseline['lower_median'],baseline['law'],baseline['fallback'])
    tables = read(args.scores/'COMMON_CONTROL_TABLE.json')
    commitments = read(args.scores/'OWNER_LOCAL_COMMITMENTS.json')
    pairs = read(args.scores/'PAIRED_COMPARISONS.json')
    scores = read(args.scores/'SCORES.json')
    methods = ['B0','B1','B2','E1','P1','E3','F2','OWN8','SAVED_ADJUSTED','SAVED_RAW','SAVED_ORIGINAL_LEAN','ALWAYS_OVER','ALWAYS_UNDER','EARLIER_LINE_PREVALENCE','NEUTRAL_HALFPOINT']
    grades, summaries = {}, []
    exact_commitments, probability_vectors, aggregate_checks = 0, 0, 0
    for method in methods:
        policies = ('P1_MEAN','P1_LOWER_MEDIAN','P2_STATISTICAL_LAW','P90') if method in ('B0','B1','B2','E1','P1','E3','F2') else ('P1_MEAN','P1_LOWER_MEDIAN') if method == 'OWN8' else ('REGISTERED_DIRECTION',)
        proc = 'B-FTN-BALL-QUALITY-COMPLETION-v1:'+method if method in ('B0','B1','B2') else 'B-OWN-INFORMATION-EMPIRICAL8-v1' if method == 'OWN8' else method
        for policy in policies:
            gg = []
            for offer in offers:
                row = dict(offer)
                prediction = indexed.get((method,key(row)))
                p, side, unavailable, fallback = None, None, False, 'none'
                if prediction is not None:
                    assert prediction['actual'] == row['actual']
                    point = prediction['mean' if policy == 'P1_MEAN' else 'lower_median']
                    fallback = prediction.get('fallback','none')
                    unavailable = point is None
                    if prediction.get('law'):
                        p = probabilities(prediction,row['line'],independent)
                        assert min(p.values()) >= -1e-12 and abs(sum(p.values())-1) < 1e-12
                        probability_vectors += 1
                    side = pointside(point,row['line']) if policy.startswith('P1_') else 'over' if p['over'] > p['under'] else 'under' if p['under'] > p['over'] else None
                    if policy == 'P90' and (side is None or p[side] < .9):
                        side = None
                elif method in ('SAVED_ADJUSTED','SAVED_RAW'):
                    point = row.get('prediction' if method == 'SAVED_ADJUSTED' else 'raw_prediction')
                    side, unavailable = pointside(point,row['line']), point is None
                elif method == 'SAVED_ORIGINAL_LEAN':
                    side = row.get('original_side',row.get('side'))
                elif method in ('E1','P1','E3','F2','OWN8'):
                    unavailable = True
                elif method in ('ALWAYS_OVER','ALWAYS_UNDER'):
                    side = 'over' if method == 'ALWAYS_OVER' else 'under'
                elif method == 'NEUTRAL_HALFPOINT':
                    p = dict(over=.5,under=.5,push=0.) if D(str(row['line'])) % 1 == D('.5') else None
                else:
                    query = qmap[row['game_id'],row['player_id']]
                    ys = [r['official_completions'] for r in eligible if r['season'] >= 2025 and r['available'] < query['kickoff']]
                    line = D(str(row['line']))
                    whole = line % 1 == 0
                    den = len(ys)+(3 if whole else 2)
                    p = dict(over=(sum(D(str(y)) > line for y in ys)+1)/den,under=(sum(D(str(y)) < line for y in ys)+1)/den,push=(sum(D(str(y)) == line for y in ys)+1)/den if whole else 0.)
                    side = 'over' if p['over'] > p['under'] else 'under' if p['under'] > p['over'] else None
                row.update(selected_side=side,probs=p,statistical_state=state(row['actual'],row['line'],side),technical_unavailable=unavailable,fallback=fallback)
                gg.append(row)
            grades[method,policy] = gg
            checked = [{k:r.get(k) for k in ('game_id','player_id','target','line','selected_side','actual','statistical_state','probs')} for r in gg]
            expected = next(x for x in commitments if (x['method'],x['policy']) == (proc,policy))
            if method in ('B0','B1','B2'):
                assert independent.digest(checked) == expected['calculations_sha256'], ('new-arm exact commitment',method,policy)
                exact_commitments += 1
            for window in ('ALL',5,6,7,8,9):
                sub = [r for r in gg if window == 'ALL' or r['week'] == window]
                reported = next(t for t in tables if (t['method'],t['policy'],t['window']) == (proc,policy,window))
                result = {}
                for side_name in ('over','under','Combined'):
                    selected = [r for r in sub if r['selected_side'] and (side_name == 'Combined' or r['selected_side'] == side_name)]
                    counts = collections.Counter(r['statistical_state'] for r in selected)
                    rep = next(s['metrics'] for s in reported['sides'] if s['side'] == side_name)
                    for name in ('WIN','LOSS','PUSH'):
                        assert rep[name] == counts[name]
                    n = counts['WIN']+counts['LOSS']
                    assert rep['denominators']['decided'] == n and rep['selection_pool_count'] == len(sub)
                    equal(rep['hit_rate'],counts['WIN']/n if n else None)
                    equal(rep['selection_coverage'],len(selected)/len(sub) if sub else None)
                    unavailable_count = sum(r['technical_unavailable'] for r in sub)
                    if 'technical_unavailable' in rep:
                        assert rep['technical_unavailable'] == unavailable_count
                    ps = probability_score(selected)
                    for k in ('n','brier','log_loss','infinite_log_losses'):
                        equal(ps[k],rep['probability_scores'][k])
                    result[side_name] = dict(wins=counts['WIN'],losses=counts['LOSS'],decided=n,selected=len(selected),rate=counts['WIN']/n if n else None,unknown=counts['UNKNOWN_PARTICIPATION'])
                    aggregate_checks += 1
                ps = probability_score(sub)
                for k in ('n','brier','log_loss','infinite_log_losses'):
                    equal(ps[k],reported['probability'][k])
                check_reliability(sub,reported['probability'])
                if method in ('B0','B2') and (window == 'ALL' or policy == 'P1_MEAN'):
                    summaries.append(dict(method=method,policy=policy,window=window,sides=result,probability=ps,unavailable=sum(r['technical_unavailable'] for r in sub),fallback=sum(r['fallback'] != 'none' for r in sub)))
    rankchecks, rank_summaries = 0, []
    for method in ('B0','B2'):
        proc = 'B-FTN-BALL-QUALITY-COMPLETION-v1:'+method
        panel = [dict(r,source_row_index=i) for i,r in enumerate(grades[method,'P2_STATISTICAL_LAW'])]
        for pool in ('Combined','over','under'):
            for limit in (6,10,20):
                all_selected, weekly_counts, weekly_hashes = [], {}, {}
                for week in range(5,10):
                    weekly = [r for r in panel if r['week'] == week]
                    # Frozen rolling policy: earlier kickoff batches consume finite
                    # weekly capacity; only within-batch ranking uses confidence.
                    capacity, selected = limit, []
                    for kickoff in sorted({r['kickoff'] for r in weekly}):
                        batch = [r for r in weekly if r['kickoff'] == kickoff and r['selected_side'] is not None and (pool == 'Combined' or r['selected_side'] == pool)]
                        batch.sort(key=lambda r:(-r['probs'][r['selected_side']],r['game_id'],r['player_id'],str(r['line'])))
                        chosen = batch[:capacity]
                        selected.extend(chosen)
                        capacity -= len(chosen)
                    assert len(selected) <= limit
                    weekly_counts[str(week)] = len(selected)
                    weekly_hashes[str(week)] = independent.digest(sorted(r['source_row_index'] for r in selected))
                    all_selected.extend(selected)
                    for side in ('over','under','Combined'):
                        rs = [r for r in selected if side == 'Combined' or r['selected_side'] == side]
                        v = next(s for s in scores if s.get('product_id') == 'ROLLING_TOP_K_DIAGNOSTIC' and s['procedure_id'] == proc and s['week'] == week and s['rank_scope'] == pool and s['K'] == limit and s['side'] == side)
                        assert v['query_membership_sha256'] == independent.digest(sorted(r['source_row_index'] for r in rs))
                        c = collections.Counter(r['statistical_state'] for r in rs)
                        for name in ('WIN','LOSS','PUSH'):
                            assert v['selection_metrics'][name] == c[name]
                        assert v['forecast_rows'] == len(rs) and v['selection_metrics']['selection_pool_count'] == len(weekly)
                        equal(v['selection_metrics']['selection_coverage'],len(rs)/len(weekly))
                        ps = probability_score(rs)
                        for name in ('n','brier','log_loss','infinite_log_losses'):
                            equal(v['selection_metrics']['probability_scores'][name],ps[name])
                        check_reliability(rs,v['selection_metrics']['probability_scores'])
                        rankchecks += 1
                cumulative = next(t for t in tables if t['method'] == proc and t['policy'] == 'ROLLING_TOP_K_DIAGNOSTIC' and t['window'] == 'ALL' and t['rank_scope'] == pool and t['K'] == limit)
                assert cumulative['weekly_selected'] == weekly_counts
                assert cumulative['weeks_evaluated'] == 5 and cumulative['weeks_with_selections'] == sum(n > 0 for n in weekly_counts.values())
                for side in ('over','under','Combined'):
                    rs = [r for r in all_selected if side == 'Combined' or r['selected_side'] == side]
                    c = collections.Counter(r['statistical_state'] for r in rs)
                    v = next(s['metrics'] for s in cumulative['sides'] if s['side'] == side)
                    assert (v['WIN'],v['LOSS'],v['denominators']['decided']) == (c['WIN'],c['LOSS'],c['WIN']+c['LOSS'])
                    assert v['selection_pool_count'] == 142
                    equal(v['selection_coverage'],len(rs)/142)
                rank_summaries.append(dict(method=method,pool=pool,K=limit,weekly_selected=weekly_counts,weekly_membership_SHA256=weekly_hashes,
                                           wins=sum(r['statistical_state'] == 'WIN' for r in all_selected),losses=sum(r['statistical_state'] == 'LOSS' for r in all_selected),selected=len(all_selected)))
    pairchecks = 0
    for pair in pairs:
        if pair['kind'] != 'OFFER_DIRECTION_PAIRED_LOSS':
            continue
        a,b = grades[pair['candidate'],pair['policy']],grades[pair['control'],pair['control_policy']]
        matches = [(r,c) for r,c in zip(a,b) if (pair['window'] == 'ALL' or r['week'] == pair['window']) and r['statistical_state'] in ('WIN','LOSS') and c['statistical_state'] in ('WIN','LOSS')]
        cw = sum(r['statistical_state'] == 'WIN' for r,c in matches)
        bw = sum(c['statistical_state'] == 'WIN' for r,c in matches)
        assert (pair['candidate_wins'],pair['control_wins'],pair['n']) == (cw,bw,len(matches))
        equal(pair['delta'],(bw-cw)/len(matches) if matches else None)
        assert pair['candidate_only_wins'] == sum(r['statistical_state'] == 'WIN' and c['statistical_state'] == 'LOSS' for r,c in matches)
        assert pair['control_only_wins'] == sum(r['statistical_state'] == 'LOSS' and c['statistical_state'] == 'WIN' for r,c in matches)
        pairchecks += 1
    numerical_checks = 0
    offered_keys = {key(r) for r in offers}
    for method in ('B0','B2'):
        for season in (2025,2026):
            rs = [r for r in rows if r['method'] == method and r['season'] == season]
            windows = [('ALL',rs),('W1_4',[r for r in rs if r['week'] <= 4]),('W5_PLUS',[r for r in rs if r['week'] >= 5]),('W1_9',[r for r in rs if r['week'] <= 9])]
            windows += [(w,[r for r in rs if r['week'] == w]) for w in sorted({r['week'] for r in rs})]
            if season == 2026:
                windows += [('MATCHED_OFFERS_W5_W9',[r for r in rs if key(r) in offered_keys])]
            for window, sub in windows:
                for product in ('mean','lower_median'):
                    errors = [D(str(r[product]))-D(str(r['actual'])) for r in sub if r['actual'] is not None and r[product] is not None]
                    rep = next(s for s in scores if s.get('record_kind') == 'forecast_evaluation_view' and s['procedure_id'].endswith(':'+method) and s['season'] == season and s['week'] == window and s['product_id'] == product and s['fallback_view'] == 'FULL_SYSTEM')
                    assert rep['n'] == len(errors)
                    equal(rep['mae'],float(sum(abs(e) for e in errors)/len(errors)) if errors else None)
                    equal(rep['mse'],float(sum(e*e for e in errors)/len(errors)) if errors else None)
                    equal(rep['bias'],float(sum(errors)/len(errors)) if errors else None)
                    numerical_checks += 1
    receipt = dict(id='B_FTN_INDEPENDENT_OUTPUT_ARITHMETIC_v1',checked_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),verdict='PASS_CHECKED_SCOPE',code_SHA256=sha(__file__),prior_independent_helper_SHA256=sha(helper_path),sources=bindings,
                   bindings={p.name:sha(p) for p in (args.wave/'FROZEN_PROTOCOL.json',args.scores/'FROZEN_SCORING_PROTOCOL.json',args.scores/'COMMON_CONTROL_TABLE.json',args.scores/'SCORES.json',args.scores/'PAIRED_COMPARISONS.json',args.scores/'OWNER_LOCAL_COMMITMENTS.json')},
                   checked=dict(Decimal_laws=lawchecks,B1_exact_alias_rows=979,offered_rows=142,method_policy_variants=len(grades),probability_vectors=probability_vectors,weekly_side_aggregates=aggregate_checks,new_arm_exact_commitments=exact_commitments,paired_disagreement_views=pairchecks,numerical_views=numerical_checks,weekly_ranked_side_membership_views=rankchecks,complete_ranked_policies=len(rank_summaries)),results=summaries,ranked_policy_results=rank_summaries,
                   scope_limits=['No fit or fresh-fit reproduction here; distinct reviewer receipt required','No original source-vintage or upstream bookmaker clock authentication','No peer private-row parity','No uncertainty-bootstrap reproduction','No current query, forecast issue, production release or original-site consumer verification'],probability_confidence_checks='Allcheckedweekly/cumulativenew-arm/controltablesandselectedTopK: independentbinmembership,meanconfidence,observedcorrectnessandpairwise-tieAUC',new_fits=0,new_original_issues=0,new_NFL_games=0,new_scored_weeks_from_verification=0,restricted_rows_republished=False)
    args.out.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(verdict=receipt['verdict'],checked=receipt['checked'],all_results=[r for r in summaries if r['window'] == 'ALL']),indent=2))


if __name__ == '__main__':
    main()
