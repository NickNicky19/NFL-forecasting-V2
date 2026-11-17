"""Partition an already verified frozen selector record; no ranking or grading.

The input is the exact 192-row decoded owner commitment previously checked by B.
Raw public source boards remain transient; only metadata/aggregates are emitted.
"""
import argparse
import ast
import collections
import hashlib
import json
import math
import platform
import time
from datetime import datetime, timezone
from pathlib import Path


EXPECTED = 'c88fc8d3ccf3cab3f1b9919e7da5dafb02fa1cc78de651ee230cee223c9453c2'
PROTOCOL_SHA = 'a69a34eb9f38592c27d01b596428cbba49c581baebc487d9e2f86f0993afd31d'
MODEL_SOURCE = 'C_P1_MEAN_RECONSTRUCTED'
FALLBACK_SOURCE = 'SAVED_WEBSITE_REFERENCE'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def key(row):
    return row['game_id'], row['player_id'], row['key'], row['direction']


def event_key(row):
    return row['game_id'], row['player_id'], row['key']


def summary(rows):
    states = collections.Counter(row['result'] for row in rows)
    decided = states['hit'] + states['miss']
    return dict(selected=len(rows), wins=states['hit'], losses=states['miss'],
        decided=decided, accuracy=states['hit'] / decided if decided else None,
        unresolved=states['unresolved'], push=states['push'], void=states['void'],
        other_states={k: v for k, v in sorted(states.items())
            if k not in {'hit', 'miss', 'unresolved', 'push', 'void'}},
        own_sides={side: summary_side([r for r in rows if r['direction'] == side])
            for side in ('over', 'under')})


def summary_side(rows):
    states = collections.Counter(row['result'] for row in rows)
    decided = states['hit'] + states['miss']
    return dict(selected=len(rows), wins=states['hit'], losses=states['miss'],
        decided=decided, accuracy=states['hit'] / decided if decided else None,
        unresolved=states['unresolved'], push=states['push'])


def source_policy(path):
    """Read the pinned constant as data; do not execute production code again."""
    tree = ast.parse(path.read_bytes())
    return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == 'POLICY' for t in n.targets))


def side_before_ranking(value, line, category, policy):
    if not all(type(x) in (int, float) and math.isfinite(x) for x in (value, line)):
        return None
    gap = value - line
    if line < category['minimum_line'] or not policy['projection_line_ratio'][0] <= value / line <= policy['projection_line_ratio'][1]:
        return None
    if abs(gap) <= category['lean'] or abs(gap / category['scale']) < policy['minimum_score']:
        return None
    return 'over' if gap > 0 else 'under'


def run(cache, previous, out):
    started = time.monotonic()
    out.mkdir(parents=True, exist_ok=True)
    destination = out / 'SELECTOR_CONTRIBUTION_ACCOUNTING_V1.json'
    if destination.exists():
        raise ValueError('Frozen accounting exists; preserve it')
    raw = (cache / 'B_CANONICAL_PICKS.local.json').read_bytes()
    rows = json.loads(raw)
    canonical = json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()
    assert len(rows) == 192 and sha(canonical) == EXPECTED
    prior = json.loads(previous.read_bytes())
    assert prior['canonical_membership_sha256'] == EXPECTED
    assert prior['canonical_membership_rows'] == len(rows)
    protocol_raw = (cache / 'block0.json').read_bytes()
    protocol = json.loads(protocol_raw)
    assert sha(protocol_raw) == PROTOCOL_SHA
    ranker = cache / 'website/tools/weekly_selected_rankings.py'
    assert sha(ranker.read_bytes()) == protocol['production_ranker_sha256']
    policy = source_policy(ranker)
    old_manifest = json.loads((cache / 'block4.json').read_bytes())
    source_bindings, weeks, numeric_changes = [], [], []
    for week in protocol['weeks']:
        old_week = next(r for r in prior['weeks'] if r['week'] == week)
        full_board = cache / f'selector-inputs/W{week}_FULL_ORIGINAL_BOARD.private.json'
        body = full_board.read_bytes()
        assert sha(body) == protocol['inputs'][f'W{week}']
        original = next(x for x in old_manifest['inputs']
            if x.get('local_name') == full_board.name)
        source_bindings.append({k: v for k, v in original.items() if k != 'local_name'} | dict(bytes=len(body)))
        board = json.loads(body)
        players = {(p['game_id'], p['id']): p for p in board['players']}
        control = [r for r in rows if r['week'] == week and r['policy'] == 'saved_control']
        candidate = [r for r in rows if r['week'] == week and r['policy'] == 'candidate']
        assert len(control) == len(candidate) == 24
        assert all(r['source'] == FALLBACK_SOURCE for r in control)
        assert {r['source'] for r in candidate} <= {MODEL_SOURCE, FALLBACK_SOURCE}
        models = [r for r in candidate if r['source'] == MODEL_SOURCE]
        fallback = [r for r in candidate if r['source'] == FALLBACK_SOURCE]
        cm, bm = {key(r): r for r in candidate}, {key(r): r for r in control}
        assert len(cm) == len(candidate) and len(bm) == len(control)
        common = cm.keys() & bm.keys()
        added, removed = cm.keys() - bm.keys(), bm.keys() - cm.keys()
        bm_event, cm_event = {event_key(r): r for r in control}, {event_key(r): r for r in candidate}
        common_events = bm_event.keys() & cm_event.keys()
        for r in fallback:
            pl = players[(r['game_id'], r['player_id'])]
            prop = next(p for p in pl['props'] if p['key'] == r['key'])
            assert (r['adj'], r['line'], r['line_from']) == (prop['adj'], prop['line'], prop['line_from'])
        changes = []
        for row in models:
            pl = players[(row['game_id'], row['player_id'])]
            prop = next(p for p in pl['props'] if p['key'] == row['key'])
            cat = policy['categories'][row['key']]
            assert (row['line'], row['line_from']) == (prop['line'], prop['line_from'])
            old_point, new_point, line = prop['adj'], row['adj'], row['line']
            assert row['candidate_model_sha256'] and math.isfinite(new_point)
            assert math.isclose((new_point - line) / cat['scale'], row['score'], rel_tol=1e-12, abs_tol=1e-12)
            old_side = side_before_ranking(old_point, line, cat, policy)
            new_side = side_before_ranking(new_point, line, cat, policy)
            assert new_side == row['direction']
            changes.append(dict(week=week, category=row['key'], selected_side=row['direction'],
                saved_margin_side='over' if old_point - line > cat['lean'] else 'under' if old_point - line < -cat['lean'] else None,
                previous_local_gate_side=old_side, new_local_gate_side=new_side,
                point_changed=new_point != old_point,
                score_changed=row['score'] != (old_point - line) / cat['scale'],
                local_gate_side_flipped=old_side is not None and old_side != new_side,
                saved_margin_side_flipped=abs(old_point - line) > cat['lean'] and ((old_point > line) != (new_point > line)),
                became_locally_eligible=old_side is None,
                selected_in_control=key(row) in common,
                new_membership=key(row) in added,
                result=row['result']))
        numeric_changes.extend(changes)
        # This reconstructs accounting only. It does not rank or grade again.
        model_result, fallback_result = summary(models), summary(fallback)
        new_rows = [cm[k] for k in sorted(added)]
        removed_rows = [bm[k] for k in sorted(removed)]
        assert model_result['selected'] == old_week['candidate_selected_model_rows']
        assert {x['result'] for x in candidate} <= {'hit', 'miss', 'unresolved'}
        assert model_result['wins'] + fallback_result['wins'] == old_week['states']['candidate'].get('hit', 0)
        assert model_result['losses'] + fallback_result['losses'] == old_week['states']['candidate'].get('miss', 0)
        weeks.append(dict(week=week, full_board_overrides_previously_verified=old_week['candidate_point_overrides'],
            candidate_generated_selected=model_result, fallback_generated_selected=fallback_result,
            control_full_system=summary(control), candidate_full_system=summary(candidate),
            common_same_side_selected=len(common), candidate_only_memberships=summary(new_rows),
            control_only_memberships=summary(removed_rows),
            candidate_model_selected_already_in_control=sum(key(r) in common for r in models),
            candidate_model_new_memberships=sum(key(r) in added for r in models),
            fallback_new_memberships=sum(key(r) in added for r in fallback),
            common_selected_point_changes=sum(cm[k]['adj'] != bm[k]['adj'] for k in common),
            common_selected_score_changes=sum(cm[k]['score'] != bm[k]['score'] for k in common),
            common_selected_opportunity_side_changes=sum(cm_event[k]['direction'] != bm_event[k]['direction'] for k in common_events),
            candidate_generated_selected_point_changes=sum(x['point_changed'] for x in changes),
            candidate_generated_selected_score_changes=sum(x['score_changed'] for x in changes),
            candidate_generated_selected_local_gate_side_flips=sum(x['local_gate_side_flipped'] for x in changes),
            candidate_generated_selected_saved_margin_side_flips=sum(x['saved_margin_side_flipped'] for x in changes),
            candidate_generated_selected_became_locally_eligible=sum(x['became_locally_eligible'] for x in changes)))
    candidate = [r for r in rows if r['policy'] == 'candidate']
    models = [r for r in candidate if r['source'] == MODEL_SOURCE]
    fallback = [r for r in candidate if r['source'] == FALLBACK_SOURCE]
    result = dict(id='B-SELECTOR-CONTRIBUTION-ACCOUNTING-v1', recorded_UTC=datetime.now(timezone.utc).isoformat(),
        parent='FOLLOW-THROUGH-RELEASE-AND-DEFENSIVE-SOURCE-01', owner_protocol=protocol['id'],
        owner_protocol_sha256=PROTOCOL_SHA, independent_previous_receipt_sha256=sha(previous.read_bytes()),
        canonical_decoded_rows_sha256=sha(canonical), transient_file_sha256=sha(raw),
        transient_file_note='Existing verified local JSON serialization; decoded commitment, not byte identity to another JSON formatting.',
        actual_ranker_sha256=sha(ranker.read_bytes()), input_bindings=source_bindings,
        execution='Accounting partition of frozen verified records; original inputs/points/selection/grading unchanged; no ranking, fitting or grading call',
        weeks=weeks,
        cumulative=dict(candidate_generated_selected=summary(models), fallback_generated_selected=summary(fallback),
            full_candidate=summary(candidate), full_control=summary([r for r in rows if r['policy'] == 'saved_control']),
            new_memberships=sum(w['candidate_only_memberships']['selected'] for w in weeks),
            removed_memberships=sum(w['control_only_memberships']['selected'] for w in weeks),
            candidate_model_rows_in_common=sum(w['candidate_model_selected_already_in_control'] for w in weeks),
            candidate_model_rows_new=sum(w['candidate_model_new_memberships'] for w in weeks),
            fallback_rows_new=sum(w['fallback_new_memberships'] for w in weeks),
            candidate_contributing_weeks=[w['week'] for w in weeks if w['candidate_generated_selected']['selected']],
            complete_system_scored_weeks=[w['week'] for w in weeks],
            candidate_generated_selected_point_changes=sum(w['candidate_generated_selected_point_changes'] for w in weeks),
            candidate_generated_selected_score_changes=sum(w['candidate_generated_selected_score_changes'] for w in weeks),
            candidate_generated_selected_local_gate_side_flips=sum(w['candidate_generated_selected_local_gate_side_flips'] for w in weeks),
            candidate_generated_selected_saved_margin_side_flips=sum(w['candidate_generated_selected_saved_margin_side_flips'] for w in weeks),
            candidate_generated_selected_became_locally_eligible=sum(w['candidate_generated_selected_became_locally_eligible'] for w in weeks),
            changed_side_on_opportunity_selected_both_policies=sum(w['common_selected_opportunity_side_changes'] for w in weeks)),
        selected_point_change_classes=numeric_changes,
        five_week_status='FOUR_SCORED_SYSTEM_WEEKS;NOT_PRIMARY_QUALIFIED. Candidate generated selected rows in three weeks; no new learned-only week-counting rule imposed.',
        interpretation='Eight added memberships equal eight candidate-generated selected rows in THIS frozen replay, proved by source/identity checks; those quantities are not generally interchangeable. Full-system improvement is two wins over 93decided; model-selected5/8 is a small exposed selected subset, not full-board skill or per-pick confidence.',
        latest_fifth_week_receipt='Peer refresh at2026-11-12 04:12UTC found no newer PR1 comments after6812397309; root binds its formal superseding receipt separately.',
        limits=['No new fifth week, original issuance, source-vintage authentication, quote clock, fitted-model review, deployment or better future accuracy is established.',
            'Four exposed complete-system week clusters, repeated selection and eight model-selected rows do not establish superiority. W8 is fallback-only.',
            'Reported outcomes are frozen statistical presence-aware grades, not verified venue settlement.',
            'Local-gate side changes compare points on the same offered opportunity before best-per-player and Top-K; they are not changed sides of already-selected control records.'],
        new_fits=0, new_model_inference=0, new_scoring_or_grading_calls=0,
        new_NFL_games=0, new_actual_offer_weeks=0, new_issued_picks=0, production_writes=0,
        environment=dict(python=platform.python_version(), stdlib_only=True),
        resources=dict(wall_seconds=time.monotonic() - started, output_budget_bytes=4 * 1024 * 1024),
        code_sha256=sha(Path(__file__).read_bytes()))
    data = (json.dumps(result, indent=2, allow_nan=False) + '\n').encode()
    assert len(data) < 4 * 1024 * 1024
    destination.write_bytes(data)
    print(json.dumps(dict(state='PASS_FROZEN_CONTRIBUTION_ACCOUNTING', weeks=[w['week'] for w in weeks],
        generated=summary(models), fallback=summary(fallback), output_sha256=sha(data))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--previous', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.cache, args.previous, args.out)
