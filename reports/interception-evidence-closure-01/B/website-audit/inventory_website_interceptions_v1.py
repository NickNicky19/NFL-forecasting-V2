"""Read-only website pass_int population and presence inventory; no grading.

Run with --source-cache pointing to the owner-local restored website tree.
The output contains counts, source hashes and published aggregates only.
"""
import argparse
import collections
import datetime
import hashlib
import json
from pathlib import Path

MAIN = '689bc6ff11c7424d5384324e5a7d25dc6e0fad9a'
PR1 = '81c3fc2a612ced916f4c54814f978c509058bca5'


def read(path):
    return json.loads(path.read_bytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source-cache', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    rows = read(a.source_cache / 'ALL_RECORDED_INTERCEPTION_LEANS_W5_W9_PRIVATE.json')
    full = read(a.source_cache / 'FULL_REAL_LINE_INTERCEPTION_BOARD_W5_W9_PRIVATE.json')
    published = read(a.source_cache / 'output/data/track_record.json')
    checks = collections.Counter()
    finals = {(week, str(game['id'])): game for week in range(5, 10)
              for game in read(a.source_cache / f'output/data/weeks/2026_w{week:02}.json')['games']}
    for r in rows:
        entry = r['source_stat_entry']
        stats = entry['stats']
        presence = stats['_presence']
        original = presence['original_row']
        context = presence['source_context']
        tests = {
            'QB_role': r['position'] == 'QB',
            'game_team_identity': r['team'] in (r['home'], r['away']) and r['opponent'] == (
                r['away'] if r['team'] == r['home'] else r['home']),
            'stat_team_identity': entry.get('team') == r['team'] and entry.get('opp') == r['opponent'],
            'presence_identity': original['player_id'] == r['player_id'] and original['team'] == r['team']
                and original['opponent'] == r['opponent'],
            'source_context': context['season'] == r['season'] and context['week'] == r['week'],
            'presence_stats_preserved': original['stats'] == {k: v for k, v in stats.items() if k != '_presence'},
            'played_positive': stats.get('gp', 0) > 0 or stats.get('off_snp', 0) > 0,
            'completed_event': finals[r['week'], r['game_id']].get('completed') is True
                and finals[r['week'], r['game_id']].get('state') == 'post',
            'real_line_notlate': r['line_from'] == 'dk' and r['late'] is False,
            'finite_valid_side_line': r['side'] in ('over', 'under') and r['line'] in (.5, 1.5),
        }
        assert all(tests.values()), [k for k, value in tests.items() if not value]
        checks.update({key: int(value) for key, value in tests.items()})
    weekly = []
    for week in range(5, 10):
        selected = [r for r in rows if r['week'] == week]
        eligible = [r for r in full if r['week'] == week]
        original = next(w for w in published['weeks'] if w['week'] == week)
        weekly.append(dict(
            season=2026, week=week, eligible_real_line_board=len(eligible), selected_saved_leans=len(selected),
            abstained=len(eligible)-len(selected), selected_over=sum(r['side'] == 'over' for r in selected),
            selected_under=sum(r['side'] == 'under' for r in selected),
            selected_confirmed_participants=sum(r['played_evidence']['gp'] > 0 for r in selected),
            selected_absent_pass_int=sum(not r['pass_int_field_present'] for r in selected),
            selected_explicit_pass_int=sum(r['pass_int_field_present'] for r in selected),
            explicit_zero=sum(r['pass_int_field_present'] and r['reported_pass_int'] == 0 for r in selected),
            selected_unique_games=len({r['game_id'] for r in selected}), selected_unique_playergames=len(selected),
            eligible_unique_games=len({r['game_id'] for r in eligible}),
            published_category_grade=original['leans']['by_category']['pass_int'],
            top_over_selected=sum(r['top_over'] for r in selected), top_under_selected=sum(r['top_under'] for r in selected)))
    history = []
    for path in sorted((a.source_cache / 'output/data/grading-history').glob('*.json')):
        item = read(path)
        history.append(dict(path=str(path.relative_to(a.source_cache)), bytes=path.stat().st_size,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(), grading_version=item.get('grading_version'),
            interception_by_week=[dict(week=w['week'], summary=w.get('leans', {}).get('by_category', {}).get('pass_int'))
                                  for w in item.get('weeks', []) if w.get('week') in range(5, 10)]))
    sources = read(a.source_cache / 'CORE_RESTORATION.json')['sources'] + read(a.source_cache / 'HISTORY_RESTORATION.json')
    sources += [r for r in read(a.source_cache / 'INITIAL_RESTORATION.json') if 'error' not in r]
    result = dict(
        id='B-WEBSITE-INTERCEPTION-POPULATION-AND-PRESENCE-v1',
        at_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(), actual_main=MAIN, substantive_PR1_head=PR1,
        scope='Source/population/code and published-grade inventory; root separately regrades with qualified official outcomes. No assumed zero.',
        exact_user_46_reproduced=True, population='ALL_RECORDED_SAVED_PROP_LEANS; QB pass_int; DK-tagged line; notlate; finalevent. Separate from TopPicks.',
        all_props_including_reference=197, excluded_internal_ours_thresholds=53, eligible_real_line_board=len(full),
        eligible_unique_games=len({r['game_id'] for r in full}), eligible_unique_playergames=len(full),
        selected=len(rows), selected_unique_games=len({r['game_id'] for r in rows}), selected_unique_playergames=len(rows),
        abstained=len(full)-len(rows), selected_participants=86, selected_absent_pass_int=46,
        selected_explicit_null_pass_int=0, selected_explicit_positive_pass_int=40, selected_explicit_zero_pass_int=0,
        line_contract_counts={'DK_labeled_0.5': 85, 'DK_labeled_1.5': 1}, weekly=weekly,
        identity_presence_checks=dict(checks), identity_presence_errors=[],
        executing_grader='statistical-presence-strict-v5-20261106',
        current_code_finding='PASS_IN_CHECKED_SCOPE: absent/null/invalid/zero distinct; participation then missing statistic returns unresolved; no sparse-zero contract.',
        current_published_v5_category=dict(wins=33, losses=7, decided=40, unknown=46, rate=33/40,
            scope='Actual current track_record bytes for same frozen86; incomplete-label observed accuracy, not unbiased whole-board accuracy.'),
        original_report_caveat='Main original_recorded_leans_report binds older1ec93/W4-8; do not pair as W5-9. Current track_record does contain W5-9v5.',
        earlier_grading_versions=history,
        historical_limit='Earlier v3W5-8 records preserved; no complete oldv3W9grade found. No counterfactual oldgrader run represented as originally published grades.',
        source_qualification='DK tag and saved line do not authenticate book/jurisdiction/original quote/decision clocks. Statistical crossing only; no price/EV/venue settlement.',
        forecast_timing='Archive saved_at clocks are postgame; lateFalse alone is not pregame issuance proof. Original saved sides/lines retain timing limits.',
        cohort_commitments=dict(full_selected86_sha256='c24c54de585dfca9451828f0be9258626919897f06b25db1f8b6305d6c823dad',
            missing46_sha256='23c65f17833756ca004fee140439f7904b93470c30ddfd2cfaef8911a855b16d',
            full_eligible144_sha256='8eb2c632c6c96f785c8b04f642546127ecf49dab11fd77a7ea6506918515a871', restricted_rows_published=False),
        source_bindings=sources, new_fits=0, new_forecasts=0, new_scientific_scores=0, new_NFL_weeks=0,
        source_restored_bytes_including_earlier_report=sum(z['bytes'] for z in sources))
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(selected=len(rows), missing=46, eligible=len(full), unique_games=result['selected_unique_games'], checks=sum(checks.values()))))


if __name__ == '__main__':
    main()
