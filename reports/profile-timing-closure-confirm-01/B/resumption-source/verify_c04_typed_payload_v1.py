"""Verify the existing point-only C04 handoff; no football scoring/inference."""
import argparse
import collections
import datetime
import hashlib
import json
import lzma
import math
from pathlib import Path
import re

EXPECTED = '4fd67d7915f9da3df9bec152155e809eb34d60f89d3ea751e26da9eb0a5c8abc'
MANIFEST = 'bd541f4425f1ac0c627583fbcf5fad8fd7a4fcd598526fe803ea89d84d97367c'
REF = 'd3d1ef4dc60826334234cfa1a1b8e373b2ee024e'
ARMS = ('F0', 'F1', 'F2', 'F3')
ALIASES = {'LAR': 'LA', 'WSH': 'WAS', 'JAC': 'JAX', 'LVR': 'LV', 'AZ': 'ARI'}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--payload', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise ValueError('Preserve prior immutable receipt')
    body = a.payload.read_bytes()
    assert len(body) == 234104 and hashlib.sha256(body).hexdigest() == EXPECTED
    mb = a.manifest.read_bytes()
    assert hashlib.sha256(mb).hexdigest() == MANIFEST
    manifest = json.loads(mb)
    decoded = lzma.decompress(body)
    packet = json.loads(decoded)
    assert packet['id'] == 'C04-POINT-ONLY-OWNER-LOCAL-HANDOFF-v1'
    rows = packet['rows']
    seen, origins = set(), set()
    roles, weeks, zeros, nulls = (collections.Counter() for _ in range(4))
    prohibited = {'actual', 'line', 'price', 'probability', 'selected_side', 'participation', 'EV', 'grade', 'Top_Picks'}
    fit_ages = []
    for row in rows:
        key = row['game_id'], row['player_id']
        assert key not in seen and re.fullmatch(r'00-\d{7}', row['player_id'])
        seen.add(key)
        assert row['category'] == 'rec' and row['position'] in ('RB', 'WR', 'TE')
        game = row['game_id'].split('_')
        assert len(game) == 4 and int(game[0]) == row['season'] and int(game[1]) == row['week']
        canonical = lambda t: ALIASES.get(t, t)
        assert {canonical(row['team']), canonical(row['opponent_team'])} == {canonical(t) for t in game[2:]}
        assert not (prohibited & set(row))
        assert row['season'] in (2025, 2026) and row['week'] in range(1, 9)
        assert set(row['forecasts']) == set(ARMS)
        roles[row['position']] += 1
        weeks[f"{row['season']}-W{row['week']:02}"] += 1
        cutoff = datetime.datetime.fromisoformat(row['query_cutoff_UTC'])
        assert cutoff.tzinfo is not None
        for arm, forecast in row['forecasts'].items():
            origin_ref = f"{row['season']}-W{row['week']:02}-{arm}"
            assert forecast['origin_ref'] == origin_ref
            origins.add(origin_ref)
            origin = manifest['origins'][origin_ref]
            assert origin['arm'] == arm
            fit = datetime.datetime.fromisoformat(origin['model_fit_cutoff_UTC'])
            assert fit.tzinfo is not None and fit <= cutoff
            fit_ages.append((cutoff-fit).total_seconds())
            for product, suffix in (('mean', 'MEAN'), ('median', 'MEDIAN')):
                value = forecast[product]
                nulls[f'{arm}::{product}'] += value is None
                assert not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0
                assert forecast[product+'_procedure_id'] == f'C-RECEIVING-ALIGNED-TIMING-v1::{arm}::{suffix}'
                zeros[f'{arm}::{product}'] += value == 0
            assert float(forecast['median']).is_integer()
    assert len(rows) == 4811 and len(origins) == 64
    receipt = dict(id='B-C04-POINT-PAYLOAD-SCHEMA-READBACK-v1',
        reviewed_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        state='PASS_ACTUAL_BYTES_XZ_DECODE_AND_TYPED_SCHEMA_ONLY',
        source=dict(repository='NickNicky19/NFL-forecasting-NGS-C', commit=REF,
            path='reports/profile-closure-next-02/timing/POINT_HANDOFF.json.xz',
            sha256=EXPECTED, bytes=len(body), decoded_bytes=len(decoded), decoded_sha256=hashlib.sha256(decoded).hexdigest(),
            manifest_path='reports/profile-closure-next-02/timing/POINT_HANDOFF_MANIFEST.json', manifest_sha256=MANIFEST),
        rows=len(rows), typed_point_values=len(rows)*8, role_counts=dict(roles), actual_numerical_season_weeks=dict(weeks),
        duplicate_game_player_keys=0, native_identity_or_team_conflicts=0, nonfinite_or_negative_points=0,
        null_points=dict(nulls), finite_zero_points=dict(zeros), declared_origins=len(origins),
        declared_fit_to_query_seconds_minmax=[min(fit_ages), max(fit_ages)],
        exact_products=manifest['procedures'],
        baseline_mapping=dict(F0='C03_R1_SUPPORT_BASELINE', F1='C03_R2_PLAYER_PROFILE'),
        information_policy=dict(F0_F1='RECONSTRUCTED_KICKOFF_PLUS7D_STRICT_CURRENT_VINTAGE',
            F2_F3='RECONSTRUCTED_KICKOFF_PLUS1D_STRICT_CURRENT_VINTAGE_NOT_OBSERVED_PUBLICATION'),
        evidence_tier=manifest['historical_tier'], query_universe=manifest['query_universe'],
        absent_products=manifest['not_supplied'],
        row_fallback_support_flags='NOT_EXPORTED; do not infer zero fallback or full offer coverage',
        point_zero_semantics='Valid zero forecast, not an outcome/participation observation or missing-stat replacement',
        limits=['No independent model restoration/fresh fit or raw feature reconstruction.',
            'Declared model/query clocks are consistent; original historical source observation availability is unauthenticated.',
            'No actual lines/outcomes transferred; numerical row coverage is not an offered-line test.',
            'No probabilities, EV, Top Picks or exact-line selected sides inferred from typed point outputs.',
            'Original C03 baseline value/model parity is A/C-reported and bound separately; not independently recomputed by this payload-schema check.'],
        new_fits=0, new_model_inference=0, new_join_scoring=0, new_NFL_observations=0,
        retained_payload='Existing immutable C GitHub bytes; no duplicate shared archive or repackaging',
        checker_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    a.out.write_text(json.dumps(receipt, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(state=receipt['state'], rows=len(rows), typed_points=len(rows)*8, origins=len(origins))))


if __name__ == '__main__':
    main()
