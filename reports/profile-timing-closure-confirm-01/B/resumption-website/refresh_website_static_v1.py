"""Read-only one-pass verification of existing original-site public assets."""
import concurrent.futures
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
ORIGINAL = json.loads((ROOT / 'reports/profile-timing-closure-confirm-01/B/WEBSITE_AND_C_CAPTURE_SCOPE_V1.json').read_text())
BASE = ORIGINAL['website']['served_B_check']['base_URL']


def minimal(value):
    if isinstance(value, list):
        return {'list_count': len(value)}
    if isinstance(value, dict):
        return {k: minimal(v) for k, v in value.items()}
    return value


def one(binding):
    start = datetime.now(timezone.utc)
    req = urllib.request.Request(BASE + binding['path'], headers={'User-Agent': 'NFL-B-ReadOnly-Static-Verification/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            body = response.read(1024 * 1024 + 1)
            if len(body) > 1024 * 1024:
                raise ValueError('Registered metadata asset byte bound exceeded')
            headers = {k.lower(): v for k, v in response.headers.items()}
            status = response.status
        observed = datetime.now(timezone.utc)
        digest = hashlib.sha256(body).hexdigest()
        obj = json.loads(body)
        # Never retain a new full player-level or pick board in this receipt.
        if binding['path'] == 'data/meta.json':
            projection = {k: obj.get(k) for k in ('season', 'week', 'generated_at', 'execution_model')}
        elif binding['path'] == 'data/health.json':
            projection = obj
        elif binding['path'].startswith('data/weekly-adaptive/'):
            projection = {k: v for k, v in obj.items() if not isinstance(v, list)}
            projection['list_field_counts'] = {k: len(v) for k, v in obj.items() if isinstance(v, list)}
        else:
            projection = {k: v for k, v in obj.items() if not isinstance(v, list)}
            projection['list_field_counts'] = {k: len(v) for k, v in obj.items() if isinstance(v, list)}
        return dict(path=binding['path'], served_url=BASE + binding['path'], HTTP_status=status,
                    request_started_UTC=start.isoformat(), observed_UTC=observed.isoformat(),
                    HTTP_Date=headers.get('date'), HTTP_Age=headers.get('age'), bytes=len(body),
                    SHA256=digest, expected_commit=ORIGINAL['website']['commit'],
                    expected_SHA256=binding['sha256'], exact_parity=digest == binding['sha256'],
                    projection=minimal(projection))
    except Exception as error:
        return dict(path=binding['path'], observed_UTC=datetime.now(timezone.utc).isoformat(),
                    state='READ_FAILED', error=type(error).__name__, reason=str(error))


def main():
    target = OUT / 'SERVED_STATIC_REFRESH_V1.json'
    if target.exists():
        raise FileExistsError('Readback is append-only; no unchanged-route retry')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(one, ORIGINAL['website']['served_B_check']['records']))
    now = datetime.now(timezone.utc)
    meta = next((r.get('projection', {}) for r in results if r['path'] == 'data/meta.json'), {})
    generated = meta.get('generated_at')
    age = (now - datetime.fromisoformat(generated.replace('Z', '+00:00'))).total_seconds() / 60 if generated else None
    out = dict(id='B-ORIGINAL-SITE-BOUNDED-STATIC-REFRESH-20261111-v1',
               completed_UTC=now.isoformat(), actual_owner_HEAD=ORIGINAL['website']['commit'],
               state='PASS_ALL_SIX_STATIC_BYTES' if all(r.get('exact_parity') for r in results) else 'PARTIAL_OR_CHANGED',
               records=results, build_age_at_observation_minutes=age,
               declared_max_build_age_minutes=120,
               freshness='Frozen health age is a build-time check; age recomputed from actual generated_at. No current DOM or stale-warning rendering claim.',
               DOM='NOT_CHECKED', full_board='NOT_FETCHED_OR_RENDERED',
               original_1610_and_C75_and_B10='PRESERVED; NO_REISSUE_OR_NEW_GRADE',
               new_collection=0, new_fits=0, new_forecasts=0, new_actual_offer_selections=0,
               new_website_writes=0, new_dispatches=0)
    target.write_text(json.dumps(out, indent=2, allow_nan=False) + '\n')
    print(json.dumps(dict(state=out['state'], records=len(results), build_age_minutes=age,
                          SHA256=hashlib.sha256(target.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
