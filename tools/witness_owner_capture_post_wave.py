"""Read-only, hash-bound witness of the incumbent owner's retained capture.

No provider call, inference, selection, publication, dispatch or credential use.
Raw public board bytes are kept outside the public research repository; this
emits only safe receipt fields and counts. GitHub cannot serve binary capture
bytes through its connector, so this bounded authorized HTTPS read uses urllib.
"""
import collections
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = 'af8bc14abe4a4148a3f84e6c131775923b5300f4'
RAW = f'https://raw.githubusercontent.com/NickNicky19/nicks-expert-nfl-picks/{COMMIT}/'
SERVED = 'https://nicknicky19.github.io/nicks-expert-nfl-picks/'
SCRATCH = Path('/workspace/scratch/post-wave-owner-readback')
OUT = ROOT / 'reports/post-wave-5w-v1/OWNER_CAPTURE_READBACK.json'


def digest(b):
    return hashlib.sha256(b).hexdigest()


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'NFL-V2-owner-readonly-witness'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    if OUT.exists():
        raise FileExistsError('Immutable receipt already exists; do not refresh it in place')
    SCRATCH.mkdir(parents=True, exist_ok=True)
    paths = [
        'output/data/week.json', 'output/data/weekly-selected-rankings.json',
        'output/data/weekly-selected-rankings/5ed15062d2bdef11db823d9f15a3f5a002e857c76fa5ea7b457e8d1ef8ad9ac2.json',
        'output/data/weekly-adaptive-overlay.json',
        'output/data/weekly-adaptive/f65e8f94329048ab8b087949a577368d45f112b5b77cc0faa871a08241d44dac.json',
        'config/weekly-derived-selected-policy-v7.json',
        'data/current-classic/2026/w09/bbbb32867fb5150bbed7eea14b3aa95ee42269a0302911369dde3b430cb525c0.json.gz',
        'data/classic-r0-shadow/latest.json', '.github/workflows/hourly.yml',
    ]
    jobs = [('git:' + p, RAW + p) for p in paths]
    jobs += [('served:' + p, SERVED + p.removeprefix('output/')) for p in paths if p.startswith('output/')]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        data = dict(zip((k for k, _ in jobs), pool.map(fetch, (u for _, u in jobs))))
    for name, body in data.items():
        target = SCRATCH / (name.replace(':', '-').replace('/', '__'))
        if target.exists() and target.read_bytes() != body:
            raise ValueError('Readback scratch collision; preserve existing receipt')
        target.write_bytes(body)
    def obj(p):
        b = data['git:' + p]
        return json.loads(gzip.decompress(b) if p.endswith('.gz') else b)
    board = obj(paths[0]); rank = obj(paths[2]); overlay = obj(paths[4])
    capture = obj(paths[6]); policy = obj(paths[5])
    parity = []
    for path in paths:
        if 'served:' + path in data:
            parity.append(dict(path=path, git_sha256=digest(data['git:' + path]),
                               served_sha256=digest(data['served:' + path]),
                               equal=data['git:' + path] == data['served:' + path]))
    assert all(r['equal'] for r in parity)
    # Never emit player names, lines or player-level record values.
    result = dict(
        evaluated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        kind='B_READ_ONLY_OWNER_CAPTURE_WITNESS_NOT_NEW_CAPTURE',
        production_commit=COMMIT,
        source_bindings=[dict(path=p, bytes=len(data['git:' + p]), sha256=digest(data['git:' + p])) for p in paths],
        served_bytes_parity=parity,
        owner_policy=dict(path=paths[5], file_sha256=digest(data['git:' + paths[5]]),
                          registration_id=policy.get('registration_id'), state=policy.get('state'),
                          current_execution=policy.get('current_execution')),
        board_schema_keys=list(board) if isinstance(board, dict) else None,
        capture_schema_keys=list(capture) if isinstance(capture, dict) else None,
        ranking_schema_keys=list(rank),
        board_safe_metadata={k: board[k] for k in ('season', 'week', 'generated_at', 'built_at', 'model', 'schema_version') if isinstance(board, dict) and k in board},
        capture_safe_metadata={k: capture[k] for k in ('season', 'week', 'generated_at', 'captured_at', 'model', 'schema_version', 'recorded_at', 'created_at') if isinstance(capture, dict) and k in capture},
        overlay_safe_metadata={k: overlay[k] for k in ('season', 'week', 'state', 'prepared_at', 'packaged_at', 'display_board_sha256')},
        selected_research_rows=len(overlay['rows']),
        ranking_safe_metadata={k: rank[k] for k in ('season', 'week', 'prepared_at', 'display_board_sha256', 'policy_sha256')},
        top_pick_shape={k: len(v) if isinstance(v, list) else type(v).__name__ for k, v in rank.get('picks', {}).items()} if isinstance(rank.get('picks'), dict) else len(rank.get('picks', [])),
        new_B_inference=0, new_B_captures=0, no_owner_mutation=True,
        limits=['Served bytes and retained owner records verified; no browser rendering performed by B.',
                'Provider publication/quote clocks and bookmaker settlement remain unverified.',
                'Owner packet is the incumbent reference; no B/G1/Count A admission follows from its persistence.'])
    OUT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(path=str(OUT.relative_to(ROOT)), parity=len(parity),
                         policy_sha256=result['owner_policy']['file_sha256'],
                         top_pick_shape=result['top_pick_shape'],
                         board_keys=result['board_schema_keys'], capture_keys=result['capture_schema_keys'],
                         capture_metadata=result['capture_safe_metadata'])))


if __name__ == '__main__':
    main()
