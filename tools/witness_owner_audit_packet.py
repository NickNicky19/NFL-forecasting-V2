"""Read an exact owner packet and served bytes; never dispatch or republish it."""
import argparse
import collections
import gzip
import hashlib
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REF = 'a478db86e2702d9fa632a23bfaf9c575a67ea902'
CAPTURE = 'data/current-classic/2026/w09/1dafcf9e9ee4acb130bc617be234f76d8ba5ffcf33002c1b200bc6e59a0a1a78.json.gz'
BASE = 'https://raw.githubusercontent.com/NickNicky19/nicks-expert-nfl-picks/' + REF + '/'
SITE = 'https://nicknicky19.github.io/nicks-expert-nfl-picks/'


def sha(body):
    return hashlib.sha256(body).hexdigest()


def clock(text):
    return datetime.fromisoformat(text.replace('Z', '+00:00'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, required=True,
                        help='Explicit permitted private cache for retained public inputs.')
    cache = parser.parse_args().cache
    cache.mkdir(exist_ok=False)
    fetched = []

    def read(path, served=False):
        url = SITE + path.removeprefix('output/') if served else BASE + path
        with urllib.request.urlopen(url, timeout=45) as response:
            body = response.read()
        name = ('served-' if served else 'git-') + str(len(fetched)) + '.bin'
        (cache / name).write_bytes(body)
        fetched.append(dict(path=path, kind='served' if served else 'git', local_name=name,
                            sha256=sha(body), bytes=len(body)))
        return body

    pairs = []

    def pair(path):
        git = read(path)
        served = read(path, True)
        pairs.append(dict(path=path, bytes=len(git), git_sha256=sha(git),
                          served_sha256=sha(served), equal=git == served))
        return json.loads(git)

    board = pair('output/data/week.json')
    meta = pair('output/data/meta.json')
    pointer = pair('output/data/weekly-selected-rankings.json')
    ranking = pair('output/data/' + pointer['path'])
    overlay_pointer = pair('output/data/weekly-adaptive-overlay.json')
    overlay = pair('output/' + overlay_pointer['path'])
    stored = read(CAPTURE)
    wrapped = json.loads(gzip.decompress(stored))
    capture = wrapped['payload']
    canonical = json.dumps(capture, sort_keys=True, separators=(',', ':')).encode()
    assert sha(canonical) == wrapped['payload_sha256']
    assert capture['input_sha256'] == pairs[0]['git_sha256']
    assert pointer['sha256'] == pairs[3]['git_sha256'] and pointer['bytes'] == pairs[3]['bytes']
    assert ranking['display_board_sha256'] == pairs[0]['git_sha256']
    picks = ranking['picks']['over'] + ranking['picks']['under']
    assert len({(r['game_id'], r['player_id'], r['key'], r['line']) for r in picks}) == len(picks)
    by_identity = {(r['game_id'], r['player_id'], r['category']): r for r in capture['rows']}
    assert len(by_identity) == len(capture['rows'])
    for pick in picks:
        original = by_identity[pick['game_id'], pick['player_id'], pick['key']]
        assert original['line'] == pick['line'] and original['adjusted_projection'] == pick['adj']
        assert original['top_' + pick['direction']]
        assert pick['model_version'] == capture['model']
    first = min(clock(g['kickoff']) for g in board['games'])
    clocks = {k: capture[k] for k in ('forecast_generated_at', 'captured_at')}
    clocks['selection_prepared_at'] = ranking['prepared_at']
    clocks['pointer_published_at'] = pointer['published_at']
    (cache / 'MAP.json').write_text(json.dumps(dict(ref=REF, files=fetched), indent=2) + '\n')
    result = dict(
        state='PINNED_OWNER_PACKET_AND_CURRENT_SERVED_BYTE_COMPARISON',
        at_utc=datetime.now(timezone.utc).isoformat(), production_data_commit=REF,
        capture_path=CAPTURE, capture_file_sha256=sha(stored),
        capture_payload_sha256=wrapped['payload_sha256'],
        capture_schema=capture.get('schema_version'), model=capture['model'],
        clocks=clocks, first_kickoff_utc=first.isoformat(),
        first_T90_utc=(first - timedelta(minutes=90)).isoformat(),
        capture_is_pregame=clock(capture['captured_at']) < first,
        capture_pre_first_T90=clock(capture['captured_at']) < first - timedelta(minutes=90),
        served_pairs=pairs, all_pairs_equal=all(p['equal'] for p in pairs),
        forecast_rows=len(capture['rows']), games=len({r['game_id'] for r in capture['rows']}),
        source_publication_verified_rows=sum(bool(r.get('source_timestamps_verified')) for r in capture['rows']),
        top_picks=dict(total=len(picks), sides=dict(collections.Counter(r['direction'] for r in picks)),
                       games=len({r['game_id'] for r in picks}),
                       sources=sorted({r['forecast_source'] for r in picks}),
                       products=sorted({r['product'] for r in picks}),
                       exact_capture_value_and_membership_parity=True),
        execution_model=meta.get('execution_model'), overlay_state=overlay['state'],
        selected_research_rows=len(overlay.get('rows', [])),
        source_read_scope='Public retained source and served data; no browser render or historical quote authentication.',
        owner_run=dict(id=42138147981, source_commit='93a6dae95f4a40455c39245e09046340e4c43c30',
                       completed_UTC='2026-11-06T00:38:31Z', conclusion='success'),
        concurrent_newer_owner_run=dict(id=42140841281, source_commit='9cee046490b9144bf047bc492cd46f459eabfaff',
                                       status='in_progress at 2026-11-06T01:00:30Z; not assumed successful'),
        B_dispatches=0, B_production_mutations=0, new_B_forecasts=0,
        limits=['A later owner refresh may legitimately change current served pointers; unequal pairs stay unequal.',
                'Safety/source-presence repair is not evidence of a new forecasting winner.',
                'Source, offer clocks and primary product qualification remain separate.',
                'Retained raw metadata label is not overwritten by this observer.'])
    out = Path('reports/audit-remediation-20261105-v1/B/OWNER_PRESENCE_SAFE_PACKET_READBACK_V1.json')
    if out.exists():
        raise FileExistsError(out)
    out.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
