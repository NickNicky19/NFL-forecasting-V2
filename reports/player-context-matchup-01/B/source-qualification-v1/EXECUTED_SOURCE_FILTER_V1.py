"""Qualify consumed PBP/FTN fields and produce attributed QB-game aggregates.

No acquisition, model fitting, target-game predictor construction or scoring.
PBP derivatives are CC-BY 4.0; FTN charting coverage is CC-BY-SA 4.0.
"""
import argparse
import collections
import csv
import gzip
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nfl_v2.hgb_control import schedules

FIELDS = ['play_id', 'game_id', 'season', 'week', 'season_type', 'posteam', 'defteam',
          'down', 'ydstogo', 'yardline_100', 'game_seconds_remaining', 'score_differential',
          'play_type', 'pass_attempt', 'complete_pass', 'sack', 'qb_dropback', 'qb_scramble',
          'qb_spike', 'qb_kneel', 'two_point_attempt', 'play_deleted', 'passer_player_id',
          'receiver_player_id', 'air_yards', 'pass_location', 'passing_yards',
          'yards_after_catch', 'cp', 'cpoe', 'epa', 'first_down_pass', 'penalty']
NUMERIC = set(FIELDS) - {'game_id', 'season_type', 'posteam', 'defteam', 'play_type',
                        'passer_player_id', 'receiver_player_id', 'pass_location'}
DEPTHS = ['BEHIND_LOS', 'YARDS_0_9', 'YARDS_10_19', 'YARDS_20_PLUS', 'UNKNOWN']
FTN_FLAGS = ['is_catchable_ball', 'is_contested_ball', 'is_drop', 'is_throw_away',
             'is_motion', 'is_screen_pass', 'is_play_action', 'is_rpo']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def save(path, value):
    if path.exists():
        raise FileExistsError(path)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def depth_index(value):
    if not np.isfinite(value):
        return 4
    return 0 if value < 0 else 1 if value < 10 else 2 if value < 20 else 3


def context_index(down, depth):
    d = int(down) - 1 if np.isfinite(down) and down in (1, 2, 3, 4) else 4
    return d * 5 + depth_index(depth)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--weekly-root', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    games = schedules(args.weekly_root / 'games.csv')
    coverage, field_coverage, contracts, raw_rows, reconciliation = [], [], [], [], []
    source_receipts = []
    for year in range(2022, 2027):
        path = args.source_root / f'play_by_play_{year}.csv.gz'
        with gzip.open(path, 'rt') as f:
            header = next(csv.reader(f))
        if not set(FIELDS) <= set(header):
            raise ValueError('PBP required schema')
        p = pd.read_csv(path, usecols=FIELDS, dtype={c: 'string' for c in set(FIELDS) - NUMERIC},
                        low_memory=False)
        for name in NUMERIC:
            p[name] = pd.to_numeric(p[name], errors='coerce')
        p = p.loc[p.season_type.eq('REG')].copy()
        if p.duplicated(['game_id', 'play_id']).any():
            raise ValueError('PBP game/play identity collision')
        # Missing safety flags on attempt candidates are unqualified, not false.
        mask = (p.pass_attempt.eq(1) & p.sack.eq(0) & p.two_point_attempt.eq(0)
                & p.play_type.ne('no_play').fillna(False) & ~p.play_deleted.eq(1))
        eligible = p.loc[mask].copy()
        eligible['context'] = [context_index(d, a) for d, a in zip(eligible.down, eligible.air_yards)]
        for week, group in p.groupby('week'):
            a = eligible.loc[eligible.week.eq(week)]
            coverage.append(dict(source='PBP', season=year, week=int(week), rows=len(group),
                games=int(group.game_id.nunique()), dropback_rows=int(group.qb_dropback.eq(1).sum()),
                raw_pass_attempt_including_sack=int(group.pass_attempt.eq(1).sum()),
                sacks=int(group.sack.eq(1).sum()), scrambles=int(group.qb_scramble.eq(1).sum()),
                official_attempt_candidates=len(a), unassigned_attempts=int(a.passer_player_id.isna().sum()),
                missing_depth=int(a.air_yards.isna().sum()), missing_down=int(a.down.isna().sum()),
                spike_attempts=int(a.qb_spike.eq(1).sum()),
                rows_excluded_no_play=int(group.play_type.eq('no_play').sum()),
                license='CC-BY-4.0'))
            for field in ['down', 'ydstogo', 'yardline_100', 'game_seconds_remaining',
                          'score_differential', 'air_yards', 'pass_location', 'cp', 'cpoe']:
                field_coverage.append(dict(source='PBP', season=year, week=int(week), field=field,
                    denominator='registered official-attempt candidates', n=len(a),
                    present=int(a[field].notna().sum()), missing=int(a[field].isna().sum())))
        for (gid, pid), group in eligible.dropna(subset=['passer_player_id']).groupby(['game_id', 'passer_player_id']):
            game = games.get(gid)
            if game is None:
                # Newer games outside the retained schedule do not enter the model lane.
                continue
            if group.posteam.nunique() != 1 or group.defteam.nunique() != 1:
                raise ValueError('Conflicting QB team identity')
            att = np.bincount(group.context, minlength=25).astype(int)
            comp = np.bincount(group.context, weights=group.complete_pass.eq(1), minlength=25).astype(int)
            if not np.all(comp <= att):
                raise ValueError('Completion/attempt support')
            means = {}
            for name in ['ydstogo', 'yardline_100', 'game_seconds_remaining', 'score_differential']:
                v = group[name].dropna()
                means[name] = dict(mean=None if v.empty else float(v.mean()), n=len(v))
            destinations = dict(collections.Counter(group.pass_location.fillna('UNKNOWN')))
            raw_rows.append(dict(game_id=gid, player_id=pid, season=year, week=int(group.week.iloc[0]),
                team=group.posteam.iloc[0], opponent=group.defteam.iloc[0], kickoff=game['kickoff'],
                available=game['kickoff'] + 7 * 86400, attempts=int(att.sum()), completions=int(comp.sum()),
                context_attempts=att.tolist(), context_completions=comp.tolist(), field_context=means,
                pass_destination_counts=destinations, known_receiver_throws=int(group.receiver_player_id.notna().sum()),
                unknown_receiver_throws=int(group.receiver_player_id.isna().sum()),
                throwing_population='PBP credited passer; QB target eligibility separately reconciled to official rows'))
        fp = args.source_root / f'ftn_charting_{year}.csv'
        f = pd.read_csv(fp, dtype='string')
        if f.duplicated(['nflverse_game_id', 'nflverse_play_id']).any():
            raise ValueError('FTN game/play identity collision')
        for flag in FTN_FLAGS:
            unexpected = set(f[flag].dropna()) - {'TRUE', 'FALSE'}
            if unexpected:
                raise ValueError('FTN flag-code change: ' + flag)
        lookup = p[['game_id', 'play_id', 'season_type', 'week']].copy()
        lookup['play_id'] = lookup.play_id.astype('Int64').astype('string')
        joined = f.merge(lookup, left_on=['nflverse_game_id', 'nflverse_play_id'],
                         right_on=['game_id', 'play_id'], how='left', validate='one_to_one', indicator=True,
                         suffixes=('', '_pbp'))
        for week, group in f.groupby('week'):
            w = int(week)
            c = joined.loc[joined.week.eq(week)]
            coverage.append(dict(source='FTN_CHARTING', season=year, week=w, rows=len(group),
                games=int(group.nflverse_game_id.nunique()), exact_PBP_keys=int(c['_merge'].eq('both').sum()),
                license='CC-BY-SA-4.0', source_publication='date_pulled is producer API receipt, not authenticated initial availability'))
            for field in FTN_FLAGS + ['starting_hash', 'qb_location', 'read_thrown', 'date_pulled']:
                field_coverage.append(dict(source='FTN_CHARTING', season=year, week=w, field=field,
                    denominator='all charting rows; throw-specific denominator requires matched official-throw eligibility',
                    n=len(group), present=int(group[field].notna().sum()), missing=int(group[field].isna().sum()),
                    value_counts=dict(collections.Counter(group[field].fillna('MISSING')))
                    if field != 'date_pulled' else None))
        contracts.append(dict(season=year, FTN_starting_hash_codes=dict(collections.Counter(f.starting_hash.fillna('MISSING'))),
            FTN_qb_location_codes=dict(collections.Counter(f.qb_location.fillna('MISSING'))),
            all_receiver_route_denominator_fields=[], true_receiver_alignment_state='SOURCE_BLOCKED_NO_ALL_ROUTE_OR_SNAP_PLAYER_ALIGNMENT_ROWS',
            pass_location_not_alignment=True, motion_does_not_identify_player=True,
            NGS_CP_CPOE='Not admitted as catchability; difficulty-model historical provenance not authenticated.'))
        source_receipts += [dict(name=path.name, sha256=sha(path), bytes=path.stat().st_size, license='CC-BY-4.0'),
                            dict(name=fp.name, sha256=sha(fp), bytes=fp.stat().st_size, license='CC-BY-SA-4.0')]
    derived = { (r['game_id'], r['player_id']): r for r in raw_rows }
    qb = []
    for year in range(2022, 2027):
        path = args.weekly_root / f'stats_player_week_{year}.csv'
        with path.open() as handle:
            for row in csv.DictReader(handle):
                if row['season_type'] != 'REG' or row['position'] != 'QB':
                    continue
                if year == 2026 and int(row['week']) > 8:
                    continue
                game = games.get(row['game_id'])
                if game is None:
                    continue
                numeric = []
                for key in ['attempts', 'completions']:
                    try:
                        value = float(row[key])
                        numeric.append(int(value) if np.isfinite(value) and value >= 0 and value == int(value) else None)
                    except (ValueError, TypeError):
                        numeric.append(None)
                record = derived.get((row['game_id'], row['player_id']))
                # An explicit official zero can qualify a zero-count context record;
                # an absent/unknown official statistic cannot.
                if record is None and numeric == [0, 0]:
                    record = dict(game_id=row['game_id'], player_id=row['player_id'], season=year, week=int(row['week']),
                        team=row['team'], opponent=row['opponent_team'], kickoff=game['kickoff'],
                        available=game['kickoff'] + 7 * 86400, attempts=0, completions=0,
                        context_attempts=[0]*25, context_completions=[0]*25,
                        field_context={k:dict(mean=None,n=0) for k in ['ydstogo','yardline_100','game_seconds_remaining','score_differential']},
                        pass_destination_counts={},known_receiver_throws=0,unknown_receiver_throws=0,
                        throwing_population='Official explicitly reported zero QB stat row')
                match = record is not None and numeric == [record['attempts'], record['completions']]
                identity = record is not None and record['team'] == row['team'] and record['opponent'] == row['opponent_team']
                reconciliation.append(dict(season=year, week=int(row['week']), match=match, identity_match=identity,
                    official_attempts=numeric[0], PBP_attempts=None if record is None else record['attempts'],
                    official_completions=numeric[1], PBP_completions=None if record is None else record['completions']))
                if record is not None:
                    qb.append(dict(record, official_attempts=numeric[0], official_completions=numeric[1],
                        target_parity=bool(match and identity), position='QB',
                        population='RETROSPECTIVE_OFFICIAL_QB_STAT_ROWS_NOT_EXANTE_ROSTER'))
    body = (json.dumps(qb, separators=(',', ':'), allow_nan=False) + '\n').encode()
    compressed = gzip.compress(body, compresslevel=9, mtime=0)
    (args.out / 'DERIVED_QB_GAME_INPUTS.json.gz').write_bytes(compressed)
    save(args.out/'SOURCE_FIELD_WEEK_COVERAGE.json',dict(rows=coverage,fields=field_coverage,contracts=contracts,
        source_bytes=source_receipts,unit_contract='air yards signed; distances yards; clock seconds; score points; counts unrounded integers',
        QB_derived_rows=len(qb),PBP_REG_passer_game_rows=len(raw_rows),
        declared_timing='current/revised source + strict kickoff+7day reconstruction; historical first publication unknown',
        original_selections_or_new_forecasts=False))
    summary=[]
    for year in range(2022,2027):
        rows=[r for r in reconciliation if r['season']==year]
        summary.append(dict(season=year,official_QB_rows=len(rows),exact_target_and_identity=sum(r['match']and r['identity_match'] for r in rows),
                            mismatched=sum(not(r['match']and r['identity_match'])for r in rows),
                            examples_without_player_identifiers=[r for r in rows if not r['match']][:8]))
    save(args.out/'TARGET_RECONCILIATION.json',dict(seasons=summary,interpretation='No convenience filter silently substitutes targets. Mismatches remain unavailable for context components and visible in coverage; final official targets retained.',
        retained_source_vintage='Existing approved weekly-stat source versions, not newly authenticated as-of labels.',
        derived_input=dict(path=str(args.out/'DERIVED_QB_GAME_INPUTS.json.gz'),sha256=sha(args.out/'DERIVED_QB_GAME_INPUTS.json.gz'),bytes=len(compressed),
                           uncompressed_sha256=hashlib.sha256(body).hexdigest(),uncompressed_bytes=len(body),license='CC-BY-4.0; attribution nflverse/nflfastR; derived by SessionB')))
    print(json.dumps(dict(QB_rows=len(qb),coverage_rows=len(coverage),field_week_cells=len(field_coverage),reconciliation=summary)))


if __name__=='__main__':
    main()
