"""Qualify reference attribution: other categories are retained, not model failures."""
import argparse
import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from account_contribution_v1 import EXPECTED, sha, summary


def run(cache, accounting, out):
    rows = json.loads((cache / 'B_CANONICAL_PICKS.local.json').read_bytes())
    assert sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()) == EXPECTED
    prior = json.loads(accounting.read_bytes())
    weeks = []
    for week in [5, 6, 7, 8]:
        board_raw = (cache / f'selector-inputs/W{week}_FULL_ORIGINAL_BOARD.private.json').read_bytes()
        assert sha(board_raw) == next(r['sha256'] for r in prior['input_bindings'] if r['ref'] ==
            {5: '9f3ddad8a382a033fe6205ef115ad8c541748358', 6: '63e687e1918205b20a1188580d6cf2b6264a5aca',
             7: '453e7e6e843b0cb1ae611b0925063e0f96c70196', 8: '0f615dd95fb6684ffe84ccd978a49e620ed6ba6c'}[week])
        board = json.loads(board_raw)
        players = {(p['game_id'], p['id']): p for p in board['players']}
        reference = [r for r in rows if r['week'] == week and r['policy'] == 'candidate'
            and r['source'] == 'SAVED_WEBSITE_REFERENCE']
        inside = [r for r in reference if r['key'] == 'rec'
            and players[(r['game_id'], r['player_id'])]['pos'] in ('WR', 'TE')]
        outside = [r for r in reference if r not in inside]
        old = next(w for w in prior['weeks'] if w['week'] == week)
        assert len(inside) + len(outside) == old['fallback_generated_selected']['selected']
        weeks.append(dict(week=week, reference_within_candidate_category_role=summary(inside),
            unchanged_reference_outside_candidate_mapping=summary(outside),
            category_counts=dict(sorted(collections.Counter(r['key'] for r in reference).items())),
            candidate_board_overrides_not_selected=old['full_board_overrides_previously_verified'] - old['candidate_generated_selected']['selected']))
    dest = out / 'REFERENCE_SCOPE_ADDENDUM_V1.json'
    if dest.exists():
        raise ValueError('Frozen addendum exists')
    result = dict(id='B-SELECTOR-REFERENCE-SCOPE-ADDENDUM-v1', recorded_UTC=datetime.now(timezone.utc).isoformat(),
        accounting_sha256=sha(accounting.read_bytes()), canonical_decoded_rows_sha256=EXPECTED,
        code_sha256=sha(Path(__file__).read_bytes()), weeks=weeks,
        interpretation='The88 reference-selected rows include83 unchanged category/role outputs outside the bounded WR/TE reception mapping and5 references within it. They are not88 failures of the C reception model. Seventy-five admitted candidate board overrides did not enter the final candidate list; no zero-effect claim is inferred from nonselection.',
        new_fits=0, new_inference=0, new_grading=0, new_NFL_games=0, new_scored_weeks=0)
    dest.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(state='PASS_REFERENCE_SCOPE_ACCOUNTING', within_mapping=sum(x['reference_within_candidate_category_role']['selected'] for x in weeks), outside_mapping=sum(x['unchanged_reference_outside_candidate_mapping']['selected'] for x in weeks), nonselected_overrides=sum(x['candidate_board_overrides_not_selected'] for x in weeks))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--accounting', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.cache, args.accounting, args.out)
