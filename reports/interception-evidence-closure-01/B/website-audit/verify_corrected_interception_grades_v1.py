"""Independent Decimal grading of frozen website rows; no author scorer imports."""
import argparse
import collections
import decimal
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def key(row, label=False):
    return (int(row['season']), int(row['week']),
            str(row['source_game_id'] if label else row['game_id']),
            str(row['source_player_id'] if label else row['player_id']))


def finite_positive(value):
    return type(value) in (int, float) and decimal.Decimal(str(value)).is_finite() and value > 0


def count(value):
    if type(value) not in (int, float):
        return None
    number = decimal.Decimal(str(value))
    if not number.is_finite() or number < 0 or number != number.to_integral_value():
        return None
    return int(number)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-cache', type=Path, required=True)
    ap.add_argument('--labels', type=Path, required=True)
    ap.add_argument('--regrade', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    full = read(a.source_cache / 'FULL_REAL_LINE_INTERCEPTION_BOARD_W5_W9_PRIVATE.json')
    selected = read(a.source_cache / 'ALL_RECORDED_INTERCEPTION_LEANS_W5_W9_PRIVATE.json')
    sm = {key(row): row for row in selected}
    labels = {key(row, True): row for row in read(a.labels)}
    assert len(full) == len(labels) == 144 and len(sm) == 86
    protocols = read(a.regrade / 'FROZEN_SCORING_PROTOCOL.json')
    commitments = {r['strategy']: r for r in read(a.regrade / 'OWNER_LOCAL_COMMITMENTS.json')}
    scored = {(r['strategy'], r['week'], r['side']): r for r in read(a.regrade / 'SCORES.json')}
    expected = ('CURRENT_PUBLISHED_PRESENCE_V5', 'CORRECTED_CURRENT_FINAL_LABELS',
                'CONSTANT_OVER_ON_SAME86', 'CONSTANT_UNDER_ON_SAME86',
                'CONSTANT_OVER_FULL144', 'CONSTANT_UNDER_FULL144',
                'RECORDED_TOP_FLAGS_ORIGINAL', 'RECORDED_TOP_FLAGS_CORRECTED')
    assert tuple(protocols['products']) == expected
    allgrades, summaries, hashes = {}, [], []
    identity_checks = side_line_checks = aggregate_checks = 0
    for strategy in expected:
        grades = []
        for raw in full:
            identity = key(raw)
            label, saved = labels[identity], sm.get(identity)
            assert label['team'] == raw['team'] and label['opponent'] == raw['opponent']
            assert label['player_id'] and label['game_id']
            identity_checks += 1
            prop, stats = raw['prop'], raw['stats_entry']['stats']
            side = prop.get('lean') if prop.get('lean') in ('over', 'under') else None
            if saved:
                assert saved['side'] == side
                assert decimal.Decimal(str(saved['line'])) == decimal.Decimal(str(prop['line']))
                assert saved['line_from'] == prop['line_from']
                side_line_checks += 1
            top = bool(saved and ((saved['top_over'] and side == 'over') or (saved['top_under'] and side == 'under')))
            if strategy.startswith('CONSTANT_'):
                side = 'over' if strategy.startswith('CONSTANT_OVER_') else 'under'
                if strategy.endswith('SAME86') and saved is None:
                    side = None
            elif strategy.startswith('RECORDED_TOP_FLAGS'):
                side = side if top else None
            played = any(finite_positive(stats.get(name)) for name in ('gp', 'off_snp', 'pass_att'))
            original = strategy in ('CURRENT_PUBLISHED_PRESENCE_V5', 'RECORDED_TOP_FLAGS_ORIGINAL')
            if original:
                value = count(stats['pass_int']) if played and 'pass_int' in stats else None
            else:
                supported = (label['label_support'] == 'EXPLICIT_NFLVERSE_PASSING_INTERCEPTIONS_AND_ESPN_PASSING_INTERCEPTIONS_AGREE'
                             and label['finality'] == 'STATUS_FINAL'
                             and all(isinstance(label.get(name), str) and len(label[name]) == 64
                                     and all(c in '0123456789abcdef' for c in label[name])
                                     for name in ('weekly_source_sha256', 'espn_source_sha256', 'finality_source_sha256')))
                value = count(label.get('corrected_pass_int')) if supported and played else None
            if side is None:
                state = 'ABSTAIN'
            elif not played:
                state = 'UNKNOWN_PARTICIPATION'
            elif value is None:
                state = 'MISSING_ACTUAL'
            else:
                actual, line = decimal.Decimal(value), decimal.Decimal(str(prop['line']))
                state = 'PUSH' if actual == line else 'WIN' if ((actual > line) == (side == 'over')) else 'LOSS'
            grades.append(dict(game_id=raw['game_id'], player_id=raw['player_id'], week=raw['week'],
                               line=prop['line'], selected_side=side, actual=value, statistical_state=state))
        sha = digest(grades)
        assert commitments[strategy]['rows'] == 144 and commitments[strategy]['calculation_sha256'] == sha
        hashes.append(dict(strategy=strategy, calculation_sha256=sha, exact_match=True))
        allgrades[strategy] = grades
        for window in ['ALL', 5, 6, 7, 8, 9]:
            outer = [r for r in grades if window == 'ALL' or r['week'] == window]
            for side in ('over', 'under', 'Combined'):
                group = [r for r in outer if r['selected_side'] and (side == 'Combined' or r['selected_side'] == side)]
                c = collections.Counter(r['statistical_state'] for r in group)
                wins, losses = c['WIN'], c['LOSS']
                decided = wins + losses
                unknown = sum(c[name] for name in ('MISSING_ACTUAL', 'UNKNOWN_PARTICIPATION', 'PENDING', 'UNRESOLVED_CONTRACT'))
                recorded = scored[strategy, window, side]['selection_metrics']
                assert (recorded['WIN'], recorded['LOSS'], recorded['PUSH']) == (wins, losses, c['PUSH'])
                assert recorded['denominators']['decided'] == decided and recorded['denominators']['unresolved'] == unknown
                assert recorded['denominators']['outer_rows'] == len(group)
                assert recorded['selection_pool_count'] == len(outer)
                assert recorded['abstentions_outside_selected_partition'] == sum(r['selected_side'] is None for r in outer)
                rate = wins / decided if decided else None
                assert recorded['hit_rate'] == rate
                aggregate_checks += 1
                summaries.append(dict(strategy=strategy, window=window, side=side, selected=len(group),
                                      wins=wins, losses=losses, push=c['PUSH'], decided=decided, unknown=unknown, rate=rate))
    before = allgrades['CURRENT_PUBLISHED_PRESENCE_V5']
    after = allgrades['CORRECTED_CURRENT_FINAL_LABELS']
    transitions = collections.Counter()
    for original, corrected in zip(before, after):
        assert all(original[k] == corrected[k] for k in ('game_id', 'player_id', 'week', 'line', 'selected_side'))
        if original['selected_side']:
            transitions[original['statistical_state'] + ' -> ' + corrected['statistical_state']] += 1
    assert dict(transitions) == read(a.regrade / 'MEASUREMENT_TRANSITIONS_V1.json')['transitions']
    for pair in read(a.regrade / 'PAIRED_CONTROLS.json'):
        other = allgrades[pair['control']]
        same = [(r, c) for r, c in zip(after, other) if r['selected_side']
                and r['statistical_state'] in ('WIN', 'LOSS') and c['statistical_state'] in ('WIN', 'LOSS')]
        assert pair['n'] == len(same) == 86
        assert pair['candidate_only_wins'] == sum(r['statistical_state'] == 'WIN' and c['statistical_state'] == 'LOSS' for r, c in same)
        assert pair['control_only_wins'] == sum(r['statistical_state'] == 'LOSS' and c['statistical_state'] == 'WIN' for r, c in same)
    result = dict(state='PASS_INDEPENDENT_DECIMAL_CORRECTED_GRADE_REPRODUCTION',
                  imports='Pythonstdlibonly; noauthorgrader/scorerimports',
                  scope='Samefrozen144board/86sides/lines; explicitdual-sourcefinal-labelcorrection,8strategies,6windows,3sidegroups. Notrecheckingrawsourceclockauthenticity,bootstraporvenuecontracts.',
                  exact_commitments=hashes, aggregate_checks=aggregate_checks,
                  identity_checks=identity_checks, unchanged_selected_side_line_checks=side_line_checks,
                  transitions=dict(transitions), results=summaries, side_or_line_changes=0,
                  new_fits=0, new_forecasts=0, new_NFL_observations=0, production_changes=0,
                  private_inputs=dict(selected_sha256=hashlib.sha256((a.source_cache / 'ALL_RECORDED_INTERCEPTION_LEANS_W5_W9_PRIVATE.json').read_bytes()).hexdigest(),
                      board_sha256=hashlib.sha256((a.source_cache / 'FULL_REAL_LINE_INTERCEPTION_BOARD_W5_W9_PRIVATE.json').read_bytes()).hexdigest(),
                      labels_sha256=hashlib.sha256(a.labels.read_bytes()).hexdigest()),
                  root_score_artifact_sha256=hashlib.sha256((a.regrade / 'SCORES.json').read_bytes()).hexdigest())
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(state=result['state'], aggregates=aggregate_checks, commitments=len(hashes), transitions=dict(transitions))))


if __name__ == '__main__':
    main()
