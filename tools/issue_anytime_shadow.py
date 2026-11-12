"""Issue one prepared research packet after fresh native event admission.

Uses the already approved public event-status route. No fits, offers, selector,
roster collection, scheduler, or production mutation. Expired input fails closed.
"""
import argparse
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from capture_qb_forward_timing import digest, event_reason, http_expiry, read


def stamp():
    return datetime.now(timezone.utc).timestamp()


def iso(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def persist(path, value):
    data = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    with path.open('xb') as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    return stamp()


def issue(out):
    protocol = read(out / 'FROZEN_PROTOCOL.json')
    prepared = read(out / 'PREPARED_FORECASTS.json')
    if (out / 'ISSUED_PACKET.json').exists():
        raise ValueError('Frozen packet already issued; do not refresh or overwrite')
    source_expiry = protocol['current_roster']['source_expires_at']
    if stamp() >= source_expiry:
        raise ValueError('Current roster source expired; no issuance permitted')
    if prepared['model_sha256'] != digest(out / 'MODEL.json.gz'):
        raise ValueError('Model binding changed')
    if len(prepared['predictions']) != 50 or prepared['new_grades'] or prepared['new_offers']:
        raise ValueError('Unexpected prepared scope')
    query = prepared['predictions'][0]['identity']
    url = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates=20261112&limit=100'
    started = stamp()
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'NFL-B-research-shadow-event-admission/1'}), timeout=30) as response:
        raw = response.read()
        headers = dict(response.headers)
        http_date, http_age = response.headers.get('Date'), response.headers.get('Age')
        status = response.status
    observed = stamp()
    data = json.loads(raw)
    matches = [e for e in data.get('events', []) if e['id'] == query['native_event_id']]
    if len(matches) != 1 or status != 200:
        raise ValueError('Native event not uniquely present')
    event = matches[0]
    competition = event['competitions'][0]
    teams = {c['homeAway']: c['team']['abbreviation'] for c in competition['competitors']}
    normalize = lambda team: 'WAS' if team == 'WSH' else team
    native = dict(game_id=query['game_id'], native_event_id=event['id'], competition_id=competition['id'],
        season=event['season']['year'], season_type=event['season']['type'], week=event['week']['number'],
        kickoff=datetime.fromisoformat(event['date'].replace('Z', '+00:00')).timestamp(),
        home_team=normalize(teams['home']), away_team=normalize(teams['away']),
        state=event['status']['type']['state'], status_name=event['status']['type']['name'],
        completed=event['status']['type']['completed'], observed_at=observed, retained_at=stamp(),
        expires_at=http_expiry(observed, http_age, http_date), HTTP_Date=http_date, HTTP_Age=http_age,
        request_started_UTC=iso(started), source_url=url, raw_response_sha256=hashlib.sha256(raw).hexdigest(),
        HTTP_status=status, native_team_aliases=teams, alias_rule='ESPN WSH -> canonical WAS; NYG unchanged',
        raw_response_not_redistributed=True)
    persist(out / 'NATIVE_EVENT_RECEIPT.json', native)
    issued = stamp()
    reason = event_reason(native, query, issued)
    if reason or issued >= source_expiry:
        persist(out / 'FAILED_ISSUE_V1.json', dict(actual_UTC=iso(issued), reason=reason or 'ROSTER_EXPIRED', new_issue=False))
        raise ValueError(reason or 'Roster expired')
    expiry = min(source_expiry, native['expires_at'], query['kickoff'] - 300)
    rows = []
    for row in prepared['predictions']:
        if event_reason(native, row['identity'], issued):
            raise ValueError('Per-query event/role identity mismatch')
        if not (0 <= row['probability'] <= 1 and abs(row['probability'] + row['complement'] - 1) < 1e-12):
            raise ValueError('Probability mass')
        rows.append(dict(row, issued_at_UTC=iso(issued), expires_at_UTC=iso(expiry),
            conditioning='Rushing-or-receiving TD conditional on qualified physical appearance; not participation forecast',
            participation_probability=None))
    packet = dict(id='B-ANYTIME-HGB-EMPIRICAL-20261112-W10-FIRST-01',
        issue_UTC=iso(issued), source_event_observed_UTC=iso(observed), expires_UTC=iso(expiry),
        procedure_registration_sha256=digest(out / 'FROZEN_PROTOCOL.json'),
        frozen_source_commit='636424ee206c7d679d58a6165129bfe6549d5d9d',
        source_event_sha256=digest(out / 'NATIVE_EVENT_RECEIPT.json'),
        model_sha256=prepared['model_sha256'], prepared_forecasts_sha256=digest(out / 'PREPARED_FORECASTS.json'),
        issue_adapter_sha256=digest(Path(__file__)), feature_cutoff=protocol['fit_cutoff'],
        predictions=rows, basic_query_records=prepared['basic'],
        counts=dict(forecasts=len(rows), eligible_players=25, basic_players=52, procedures=2,
            actual_offers=0, selected_picks=0, grades=0, new_evaluated_weeks=0),
        evidence='GENUINE_PREGAME_FORECAST_ONLY_SHADOW; current-vintage history under declared seven-day reconstruction',
        product='RAW_EVENT_PROBABILITY; NOT calibrated confidence, EV, category O/U, Top Picks or primary replacement',
        current_universe='Source-known ACT RB/WR/TE; role/transaction-effective uncertainty retained; no target outcomes required',
        capture_expiry_semantics='Expiry stops fresh recommendation use; frozen future grading remains valid',
        disposition='SHADOW', production_activation=False,
        grading='Existing inherited rushing-or-receiving event contract; final qualified physical appearance/components required; unknown stays unresolved')
    persisted = persist(out / 'ISSUED_PACKET.json', packet)
    persist(out / 'LOCAL_PERSISTENCE_RECEIPT.json', dict(packet_id=packet['id'],
        issued_UTC=iso(issued), local_fsynced_UTC=iso(persisted), packet_sha256=digest(out / 'ISSUED_PACKET.json'),
        before_event_cutoff=True, input_unexpired_at_local_persistence=persisted < expiry,
        remote_publication='Separate Git commit/readback receipt; not implied by this local fsync',
        source_expiry_UTC=iso(source_expiry), native_expiry_UTC=iso(native['expires_at'])))
    print(json.dumps(dict(id=packet['id'], issued_UTC=iso(issued), local_persisted_UTC=iso(persisted),
        expires_UTC=iso(expiry), forecasts=len(rows), offered_selections=0, grades=0)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    issue(parser.parse_args().out)
