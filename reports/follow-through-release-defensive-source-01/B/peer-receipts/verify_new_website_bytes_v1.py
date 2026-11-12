"""Bounded read-only current website byte/capture witness; no new scoring."""
import collections
import concurrent.futures
import gzip
import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HEAD = '869d9a8839ae83dfccdb3bbb6610a0e0df867667'
GIT = 'https://raw.githubusercontent.com/NickNicky19/nicks-expert-nfl-picks/' + HEAD + '/'
SERVED = 'https://nicknicky19.github.io/nicks-expert-nfl-picks/'
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as response:
        body = response.read(2 * 1024 * 1024 + 1)
        if len(body) > 2 * 1024 * 1024:
            raise ValueError('Public metadata response cap')
        return body, dict(HTTP_status=response.status, HTTP_Date=response.headers.get('Date'),
                         HTTP_Age=response.headers.get('Age'), observed_UTC=datetime.now(timezone.utc).isoformat())


def pair(path):
    git_path = 'output/' + path
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        a, b = list(pool.map(fetch, (GIT + git_path, SERVED + path)))
    assert a[0] == b[0], 'Git/served mismatch: ' + path
    body = a[0]
    return path, json.loads(body), dict(served_path=path, Git_path=git_path,
        expected_commit=HEAD, bytes=len(body), SHA256=hashlib.sha256(body).hexdigest(),
        exact_parity=True, Git_response=a[1], served_response=b[1])


def main():
    target = OUT / 'NEW_WEBSITE_PACKET_AND_SERVED_READBACK_V1.JSON'
    if target.exists():
        raise ValueError('Frozen receipt exists')
    names = ['data/meta.json', 'data/health.json', 'data/weekly-adaptive-overlay.json', 'data/weekly-selected-rankings.json']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        initial = list(pool.map(pair, names))
    data = {name: value for name, value, _ in initial}
    records = [record for _, _, record in initial]
    overlay_path = data[names[2]]['path']
    ranking_path = data[names[3]]['path']
    if not ranking_path.startswith('data/'):
        ranking_path = 'data/' + ranking_path
    more = [pair(overlay_path), pair(ranking_path)]
    records.extend(record for _, _, record in more)
    overlay, ranking = more[0][1], more[1][1]
    assert records[4]['SHA256'] == data[names[2]]['sha256']
    assert records[5]['SHA256'] == data[names[3]]['sha256']
    health, meta = data[names[1]], data[names[0]]
    raw, native_http = fetch(GIT + health['receipt'])
    archive = json.loads(gzip.decompress(raw))
    payload = archive['payload']
    computed_payload = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    assert computed_payload == archive['payload_sha256']
    rows = payload['rows']
    assert len(rows) == health['capture_rows'] == 1614
    previous = json.loads((ROOT / 'reports/category-decision-release-01/B/peer-live/WEBSITE_SERVED_CONSUMER_STATE_V1.json').read_text())
    assert previous['execution_model'] == meta['execution_model']
    assert previous['ranking']['policy_sha256'] == ranking['policy_sha256']
    now = datetime.now(timezone.utc)
    event_times = {r['game_id']: datetime.fromisoformat(r['kickoff'].replace('Z', '+00:00')) for r in rows}
    capture_time = datetime.fromisoformat(payload['captured_at'].replace('Z', '+00:00'))
    category_counts = collections.Counter(r['category'] for r in rows)
    source_counts = collections.Counter(r['line_from'] for r in rows)
    clock_counts = collections.Counter(str(r['source_timestamps_verified']) for r in rows)
    typed = []
    categories = ['pass_yd', 'pass_td', 'pass_cmp', 'pass_att', 'pass_int', 'rush_yd',
                  'rush_att', 'rec', 'rec_yd', 'rush_rec_yd', 'anytime_td', 'nick-chart-ppr-v1']
    for category in categories:
        config = ranking['policy']['categories'].get(category)
        typed.append(dict(category=category,
            actual_model=meta['execution_model']['model'] if category != 'nick-chart-ppr-v1' else None,
            native_forecast_rows=category_counts.get(category, 0),
            exact_chart='UNAVAILABLE_NO_EQUIVALENCE_TO_LEAGUE_FANTASY' if category == 'nick-chart-ppr-v1' else None,
            baseline_point='Native adjusted_projection/recorded lean; point gap has no probability or EV' if config else None,
            selected_override_margin=config['lean'] if config else None,
            selected_ranking_scale=config['scale'] if config else None,
            category_source='CURRENT_BASELINE; no research override' if category != 'nick-chart-ppr-v1' else 'NO_EXACT_PRODUCT',
            direction_policy='Recorded baseline lean; if selected overlay admitted, nonzero-margin selectedPropGap applies' if config else 'NO_QUALIFIED_ACTUAL_OFFER_OU_PRODUCT',
            probability='Guarded uncalibrated baseline event estimate; null retained' if category == 'anytime_td' else 'NONE_FROM_POINT_OR_GAP',
            research_selected_rows=0))
    examples = []
    for category in ('pass_cmp', 'rec', 'rec_yd', 'anytime_td'):
        r = next(r for r in rows if r['category'] == category)
        examples.append({key: r.get(key) for key in ('category', 'player_id', 'game_id', 'position', 'team',
            'raw_projection', 'adjusted_projection', 'line', 'line_from', 'lean', 'probability',
            'source_timestamps_verified', 'settlement_status')})
    commit = json.loads((OUT / 'NEW_WEBSITE_COMMIT_METADATA_V1.json').read_text())
    report = dict(id='B-NEW-WEBSITE-PACKET-SERVED-READBACK-v1', observed_UTC=now.isoformat(),
        source_commit=HEAD, previous_dated_witness_commit=previous['actual_HEAD'],
        state='PASS_SIX_GIT_OUTPUT_TO_SERVED_BYTE_PAIRS_AND_NATIVE_CAPTURE_HASH', records=records,
        execution_model=meta['execution_model'], native=dict(path=health['receipt'], bytes=len(raw),
            SHA256=hashlib.sha256(raw).hexdigest(), payload_sha256=archive['payload_sha256'],
            unique_archive_id=Path(health['receipt']).name.replace('.json.gz', ''),
            unique_games=len(event_times), unique_player_games=len({(r['game_id'], r['player_id']) for r in rows}),
            first_kickoff_UTC=min(event_times.values()).isoformat(), last_kickoff_UTC=max(event_times.values()).isoformat(),
            future_games_at_capture=sum(t > capture_time for t in event_times.values()),
            already_started_games_at_capture=sum(t <= capture_time for t in event_times.values()),
            future_rows_at_capture=sum(datetime.fromisoformat(r['kickoff'].replace('Z', '+00:00')) > capture_time for r in rows),
            already_started_rows_at_capture=sum(datetime.fromisoformat(r['kickoff'].replace('Z', '+00:00')) <= capture_time for r in rows),
            hours_before_first_kickoff=(min(event_times.values())-capture_time).total_seconds()/3600,
            explicit_separate_forecast_issue_clock=None,
            independently_verified_payload_hash=True, HTTP=native_http, rows=len(rows),
            generated_UTC=payload['forecast_generated_at'], captured_UTC=payload['captured_at'],
            source_code_commit=payload['code_commit'], model=payload['model'],
            category_counts=dict(category_counts), source_tag_counts=dict(source_counts),
            source_clock_flags=dict(clock_counts), input_sha256=payload['input_sha256'],
            future_at_capture=all(datetime.fromisoformat(r['kickoff'].replace('Z', '+00:00')) > datetime.fromisoformat(payload['captured_at'].replace('Z', '+00:00')) for r in rows),
            row_truth='Frozen original reference forecast/line/source/lean metadata, not new B predictions or graded selections'),
        health=dict(health, calculated_age_minutes=(now-datetime.fromisoformat(meta['generated_at'].replace('Z', '+00:00'))).total_seconds()/60),
        overlay=dict(state=overlay['state'], rows=len(overlay['rows']), fallback_counts=overlay['fallback_counts'],
            prepared_UTC=overlay['prepared_at'], website_source_sha=overlay['website_source_sha']),
        ranking=dict(policy=ranking['policy'], policy_sha256=ranking['policy_sha256'],
            counts={side: len(picks) for side, picks in ranking['picks'].items()},
            sources={side: dict(collections.Counter(p['forecast_source'] for p in picks)) for side, picks in ranking['picks'].items()},
            prepared_UTC=ranking['prepared_at']),
        twelve_category_actual_metadata=typed, representative_native_values=examples,
        code_semantics=dict(changed_files=commit['changed_count'], changed_code_paths=commit['source_code_changed'],
            direct_parent=commit['parent'], baseline_engine_contract_equal_previous=True,
            selector_policy_equal_previous=True, interpretation='No Python/JS code changed in the direct child commit. Prior exact actual-app margin/null/fallback fixture remains applicable; no repeated policy replay.'),
        latest_workflow=commit['runs'][0], scheduling='Latest update was workflow_dispatch/manual, not proof of unattended schedule reliability. Last observed scheduled success remains43101028574 November11.',
        fresh_offer_qualification='519 displayed props have source real-line tags,1509 internal references; all source/quote-clock qualification remains unknown. Do not count these as qualified prospective O/U decisions.',
        legacy_verifier='Reported failure/NOT_EVALUATED_CURRENT_MODEL_INPUT_CLOSURE_REQUIRED is retained separately; successful updater is not a legacy parity pass.',
        browser='NO_NEW_DIRECT_BROWSER_OR_MOBILE_DOM_CHECK; verified served byte parity and native row values only',
        wrong_initial_route='Initial Git data/meta.json lookup404 was a wrong repository route; actual source path output/data/meta.json verified. No inference of missing model/feed from that404.',
        original_site_research_activation=False, new_B_fits=0, new_B_forecasts=0, new_B_grades=0,
        original_records_preserved=True)
    target.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(state=report['state'], rows=len(rows), overlay=overlay['state'],
        research_rows=len(overlay['rows']), source_tags=dict(source_counts), latest_run=commit['runs'][0]['id'],
        latest_event=commit['runs'][0]['event'], actual_generated=payload['forecast_generated_at'], actual_captured=payload['captured_at'])))


if __name__ == '__main__':
    main()
