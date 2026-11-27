"""Bounded evidence match only: never rerank or rewrite a frozen selector."""
import argparse
import decimal
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(path.read_bytes())


def identity(row, native=False):
    return (row['week'], str(row['game_id']), str(row['player_id']),
            row.get('key', 'pass_int'), row['side'] if native else row['direction'],
            decimal.Decimal(str(row['line'])), row['line_from'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo-root', type=Path, required=True)
    ap.add_argument('--selected', type=Path, required=True)
    ap.add_argument('--labels', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    oldpath = a.repo_root / 'reports/category-decision-release-01/B/peer-live/selector-replay-review-v1/B_INDEPENDENT_SELECTOR_VERIFICATION_V1.json'
    contribution = a.repo_root / 'reports/follow-through-release-defensive-source-01/B/selector-review/SELECTOR_CONTRIBUTION_ACCOUNTING_V1.json'
    old, accounting = read(oldpath), read(contribution)
    commitment = 'c88fc8d3ccf3cab3f1b9919e7da5dafb02fa1cc78de651ee230cee223c9453c2'
    assert old['canonical_membership_sha256'] == accounting['canonical_decoded_rows_sha256'] == commitment
    native = [r for r in read(a.selected) if r['top_over'] or r['top_under']]
    assert len(native) == 3
    native_by_week = {w: sum(r['week'] == w for r in native) for w in (5, 6, 7, 8)}
    replay_unknown_by_week = {r['week']: r['states']['saved_control'].get('unresolved', 0) for r in old['weeks']}
    assert native_by_week == {5: 2, 6: 1, 7: 0, 8: 0}
    assert replay_unknown_by_week == {5: 0, 6: 1, 7: 0, 8: 2}
    example = old['deterministic_examples']['unknown']
    same = [r for r in native if identity(r, True) == identity(example)]
    assert len(same) == 1 and example['week'] == 6 and example['key'] == 'pass_int'
    assert example['result'] == 'unresolved' and example['policy'] == 'saved_control'
    label = next(r for r in read(a.labels) if (r['week'], str(r['source_game_id']), str(r['source_player_id']))
                 == (example['week'], example['game_id'], example['player_id']))
    assert label['corrected_pass_int'] == 0 and label['finality'] == 'STATUS_FINAL'
    assert label['label_support'] == 'EXPLICIT_NFLVERSE_PASSING_INTERCEPTIONS_AND_ESPN_PASSING_INTERCEPTIONS_AGREE'
    assert example['direction'] == 'over' and decimal.Decimal(str(example['line'])) > 0
    w6 = next(r for r in accounting['weeks'] if r['week'] == 6)
    assert w6['control_only_memberships']['unresolved'] == w6['candidate_only_memberships']['unresolved'] == 0
    assert w6['control_full_system']['unresolved'] == w6['candidate_full_system']['unresolved'] == 1
    assert w6['common_selected_point_changes'] == w6['common_selected_score_changes'] == w6['common_selected_opportunity_side_changes'] == 0
    # The prior published unknown example gives one exact identity. The complete
    # 192 rows are not recovered here; aggregate patterns cannot invent the rest.
    result = dict(
        state='PARTIAL_EXACT_IMPACT_CONFIRMED_WITHOUT_SELECTOR_REPLAY',
        frozen_policy='NFL-WEB-EXACT-SELECTOR-REC-P1-MEAN-WRTE-20261112-v1',
        frozen_canonical_membership_sha256=commitment,
        native_three_top_INT_flags_by_week=native_by_week,
        frozen_unknowns_per_policy_by_week=replay_unknown_by_week,
        native_three_equal_frozen_three_unknowns=False,
        exact_control_unknown_match=dict(
            public_source=str(oldpath.relative_to(a.repo_root)), public_field='deterministic_examples.unknown',
            week=example['week'], game_id=example['game_id'], player_id=example['player_id'],
            category=example['key'], side=example['direction'], line=example['line'], line_from=example['line_from'],
            previous_state='unresolved', supported_corrected_count=0, corrected_state='LOSS',
            source_qualified_label_sha256=hashlib.sha256(json.dumps(label, sort_keys=True, separators=(',', ':')).encode()).hexdigest()),
        candidate_common_membership_inference='Same one unknown is common: bothchangedmembershippartitionshave0unknown, bothfullpolicieshave1unknown, unchangedcommonscore/side. No newmapping or linechange.',
        matched_policy_records=2, matched_unique_player_games=1,
        directly_read_exact_control_examples=1,
        candidate_membership_inferred_from_prior_partition_counts=1,
        independent_full192_row_access_now=False,
        unresolved_impact_scope='The twoW8unknownrecordsperpolicy are notidentifiedbythe availablepublishedexample; one priorcategorytable haspass_int1,butids/line/statecannotbeinferredfromcounts.',
        exact_missing_artifact='Originalwebsiteowner complete192canonicalselectedrow manifest or immutablePICKS.local/B_CANONICAL_PICKS.local equivalent matchingc88fc8d3 commitment.',
        next_executor='Originalwebsiteowner appends source-supported gradingversion on frozenrecords; B verifies receivedrows, C recordsscope.',
        canonical_replay_rewritten=False, new_canonical_policy_totals_published=False,
        new_ranker_calls=0, new_selector_replays=0, new_NFL_weeks=0,
        native_flags_not_retroactively_substituted=True,
        source_bindings=[dict(path=str(path.relative_to(a.repo_root)), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                         for path in (oldpath, contribution)])
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(state=result['state'], matched_policy_records=2, native_equals_frozen_unknowns=False)))


if __name__ == '__main__':
    main()
