"""New depth cross-tab only, using already retained and admitted raw sources."""
import argparse, collections, csv, gzip, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT))
from tools.run_player_context_wave import read, write, sha, now
from nfl_v2.qb_depth_catchability import DEPTHS

FLAGS = ('is_catchable_ball', 'is_drop', 'is_contested_ball')

def number(x):
    try: return float(x)
    except (TypeError, ValueError): return float('nan')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--source-root', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True); a = ap.parse_args()
    base = ROOT / 'reports/player-context-matchup-01/B'
    rows = read(base / 'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz')
    expected = {r['name']: r for r in read(base / 'source-qualification-v1/SOURCE_RECEIPTS.json')['sources']}
    result = {(r['game_id'], r['player_id']): dict(**{k:r[k] for k in ('game_id','player_id','season','week','team','opponent','kickoff','available')},
              eligible_throws=[0]*5, flags={f:dict(known=[0]*5, positive=[0]*5)for f in FLAGS}) for r in rows}
    coverage = []; bindings = []
    for year in range(2022, 2027):
        pp = a.source_root / f'play_by_play_{year}.csv.gz'; fp = a.source_root / f'ftn_charting_{year}.csv'
        for p in (pp, fp):
            assert sha(p) == expected[p.name]['sha256']
            bindings.append(dict(source=p.name, sha256=sha(p), bytes=p.stat().st_size))
        throws = {}; seen = set()
        with gzip.open(pp, 'rt') as f:
            reader = csv.reader(f); header = next(reader); ix = {v:i for i,v in enumerate(header)}
            for r in reader:
                if r[ix['season_type']] != 'REG': continue
                pk = r[ix['game_id']], str(int(float(r[ix['play_id']])))
                if pk in seen: raise ValueError('Duplicate PBP identity')
                seen.add(pk)
                if not (number(r[ix['pass_attempt']])==1 and number(r[ix['sack']])==0
                        and number(r[ix['two_point_attempt']])==0 and number(r[ix['play_deleted']])!=1): continue
                key = r[ix['game_id']], r[ix['passer_player_id']]
                if key not in result: continue
                depth = number(r[ix['air_yards']])
                j = 4 if depth != depth else 0 if depth < 0 else 1 if depth < 10 else 2 if depth < 20 else 3
                result[key]['eligible_throws'][j] += 1; throws[pk] = key, j
        matched = 0; seen = set()
        with fp.open() as f:
            for r in csv.DictReader(f):
                pk = r['nflverse_game_id'], r['nflverse_play_id']
                if pk in seen: raise ValueError('Duplicate FTN identity')
                seen.add(pk)
                if pk not in throws: continue
                key,j = throws[pk]; matched += 1
                for field in FLAGS:
                    v = r[field]
                    if v not in ('','TRUE','FALSE'): raise ValueError('FTN value-code change')
                    result[key]['flags'][field]['known'][j] += int(bool(v))
                    result[key]['flags'][field]['positive'][j] += int(v=='TRUE')
        rr = [v for v in result.values() if v['season']==year]
        coverage.append(dict(season=year, QB_game_rows=len(rr), throws_by_depth=[sum(r['eligible_throws'][j]for r in rr)for j in range(5)],
            flags={f:{k:[sum(r['flags'][f][k][j]for r in rr)for j in range(5)]for k in ('known','positive')}for f in FLAGS}, matched_throws=matched))
    for r in rows:
        d = result[r['game_id'],r['player_id']]
        assert sum(d['eligible_throws']) == r['attempts']
        for flag in FLAGS:
            assert all(0<=p<=k<=n for p,k,n in zip(d['flags'][flag]['positive'],d['flags'][flag]['known'],d['eligible_throws']))
    write(a.out/'FTN_DEPTH_QB_GAME_INPUTS.json.gz', list(result.values()))
    write(a.out/'SOURCE_DEPTH_COVERAGE_V1.json', dict(at_utc=now(), state='QUALIFIED_CURRENT_REVISED_DEPTH_DERIVATIVE',
        definitions='Same official attempt eligibility as accepted source-v3. Five air-yard bins including UNKNOWN; TRUE/FALSE known, blank unknown. Catchability/drop/contested independent annotations.',
        depth_order=DEPTHS, source_bindings=bindings, coverage=coverage, source_vintage='CURRENT_REVISED_SEVEN_DAY_RECONSTRUCTION_NOT_AUTHENTICATED',
        license='CC-BY-SA-4.0; FTN Data via nflverse; PBP attribution nflverse/nflfastR', new_raw_downloads=0))
    print(json.dumps(dict(rows=len(result), state='DEPTH_DERIVATIVE_RETAINED')))

if __name__ == '__main__': main()
