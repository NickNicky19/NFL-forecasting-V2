"""New B opportunity/defense component; retained bytes only, no fits/scoring."""
import argparse
import collections
import csv
import gzip
import json
import resource
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from nfl_v2.passing_opportunity_profiles import (VERSION, TEAMS, COUNT_NAMES, OpportunityHistory,
    blank_counts, blank_cells, add_counts, coarse_bins, number, play_counts)
from tools.run_player_context_wave import read, write, sha, now


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(); a.out=a.out.resolve()
    registration=a.out/'EXTRACTION_REGISTRATION_V2.json'
    config=read(registration); budget=config['budget']
    started=time.monotonic(); cpu=time.process_time()
    def check():
        if time.monotonic()-started > budget['wall_seconds']: raise RuntimeError('WALL_BUDGET')
        if time.process_time()-cpu > budget['cpu_seconds']: raise RuntimeError('CPU_BUDGET')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024 > budget['max_RSS_bytes']: raise RuntimeError('MEMORY_BUDGET')
        if sum(p.stat().st_size for p in a.out.rglob('*') if p.is_file()) > budget['public_retention_bytes']: raise RuntimeError('RETENTION_BUDGET')
    base=ROOT/'reports/player-context-matchup-01/B'
    inputs_path=base/'source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz'
    inputs=read(inputs_path)
    expected={r['name']:r for r in read(base/'source-qualification-v1/SOURCE_RECEIPTS.json')['sources']}
    game={}
    qb={}
    for r in inputs:
        if r['available'] != r['kickoff']+7*86400: raise ValueError('Changed inherited information policy')
        if r['team'] not in TEAMS or r['opponent'] not in TEAMS: raise ValueError('Noncanonical team')
        game[r['game_id']]=dict(game_id=r['game_id'],season=r['season'],week=r['week'],kickoff=r['kickoff'],available=r['available'])
        key=r['game_id'],r['player_id']
        if key in qb: raise ValueError('Duplicate accepted identity')
        qb[key]=dict(**{k:r[k] for k in ('game_id','player_id','team','opponent','season','week','kickoff','available')},counts=blank_counts(),cells=blank_cells())
    teams={}; coverage=[]; bindings=[]; total_rows=0
    for season in range(2022,2027):
        path=a.source_root/f'play_by_play_{season}.csv.gz'
        check()
        if sha(path) != expected[path.name]['sha256']: raise ValueError('Source hash mismatch')
        bindings.append(dict(source=path.name,sha256=sha(path),bytes=path.stat().st_size))
        seen=set(); audit=collections.Counter(); weekly=collections.defaultdict(collections.Counter)
        with gzip.open(path,'rt') as f:
            reader=csv.DictReader(f)
            required={'play_id','game_id','season_type','posteam','defteam','down','ydstogo','yardline_100','pass_attempt','rush_attempt','qb_dropback','sack','qb_scramble','qb_spike','qb_kneel','complete_pass','play_deleted','two_point_attempt','passer_player_id','rusher_player_id'}
            if not required <= set(reader.fieldnames): raise ValueError('Missing source fields')
            for r in reader:
                total_rows+=1
                if total_rows>budget['max_source_rows']: raise RuntimeError('SOURCE_ROW_BUDGET')
                if total_rows%10000==0: check()
                if r['season_type']!='REG' or r['game_id'] not in game: continue
                pk=r['game_id'],r['play_id']
                if pk in seen: raise ValueError('Duplicate PBP identity')
                seen.add(pk);audit['supported_raw_rows']+=1
                row=play_counts(r)
                if row is None:
                    audit['excluded_or_unknown_safety_rows']+=1;continue
                team,opponent=r['posteam'],r['defteam']
                if team not in TEAMS or opponent not in TEAMS: raise ValueError('Opportunity missing canonical team')
                key=r['game_id'],team
                if key not in teams:
                    teams[key]=dict(**game[r['game_id']],team=team,opponent=opponent,counts=blank_counts(),cells=blank_cells())
                if teams[key]['opponent'] != opponent: raise ValueError('Conflicting historical team')
                player=r['rusher_player_id'] if row['scrambles'] else r['passer_player_id']
                playerkey=r['game_id'],player
                # Known QB membership is inherited from accepted QB identities;
                # unprofiled/unknown passer exposure stays in the team bucket.
                is_qb_passing=bool(row['dropbacks'] or row['credited_attempts'] or row['sacks']) and playerkey in qb
                row['unassigned_dropbacks']=int(bool(row['dropbacks']) and not is_qb_passing)
                row['unassigned_attempts']=int(bool(row['credited_attempts']) and not is_qb_passing)
                add_counts(teams[key]['counts'],row)
                for name,index in zip(('down','distance','field'),coarse_bins(r)):
                    add_counts(teams[key]['cells'][name][index],row)
                if is_qb_passing:
                    if qb[playerkey]['team'] != team: raise ValueError('QB historical team conflict')
                    add_counts(qb[playerkey]['counts'],row)
                    for name,index in zip(('down','distance','field'),coarse_bins(r)):
                        add_counts(qb[playerkey]['cells'][name][index],row)
                wk=weekly[game[r['game_id']]['week']]
                for k,v in row.items(): wk[k]+=v
                audit['attempts_outside_provider_dropback']+=int(bool(row['credited_attempts']) and not row['dropbacks'])
                audit['sacks_outside_provider_dropback']+=int(bool(row['sacks']) and not row['dropbacks'])
                audit['scrambles_outside_provider_dropback']+=int(bool(row['scrambles']) and not row['dropbacks'])
        for r in inputs:
            if r['season']!=season:continue
            x=qb[r['game_id'],r['player_id']]['counts']
            if (x['credited_attempts'],x['completions']) != (r['attempts'],r['completions']):
                raise ValueError('Accepted official attempt/completion parity changed')
        coverage.append(dict(season=season,team_games=sum(r['season']==season for r in teams.values()),QB_game_rows=sum(r['season']==season for r in qb.values()),
                             audit=dict(audit),weekly=[dict(week=w,counts=dict(v)) for w,v in sorted(weekly.items())]))
    for r in qb.values():
        team=teams[(r['game_id'],r['team'])]
        r['counts']['attributed_team_dropbacks']=team['counts']['dropbacks']
        r['counts']['attributed_team_attempts']=team['counts']['credited_attempts']
        # The same-game team denominator is attached only after raw extraction;
        # query use remains restricted to earlier eligible games.
    teamrows=sorted(teams.values(),key=lambda r:(r['kickoff'],r['game_id'],r['team']))
    qbrows=sorted(qb.values(),key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
    history=OpportunityHistory(teamrows,qbrows)
    artifacts=[]
    artifacts.append(write(a.out/'PASSING_OPPORTUNITY_GAME_INPUTS_V2.json.gz',dict(version=VERSION,team_games=teamrows,QB_games=qbrows)))
    queries=[r for r in inputs if r['season'] in (2025,2026)]
    profiles=[history.build(q) for q in queries]
    artifacts.append(write(a.out/'QB_OPPORTUNITY_ASOF_PROFILES_V2.json.gz',profiles))
    origins=sorted({(r['season'],r['week']) for r in queries})
    defense=[]
    for season,week in origins:
        cutoff=min(q['kickoff'] for q in queries if(q['season'],q['week'])==(season,week))
        defense.extend(history.defense_profile(team,cutoff,season,week) for team in TEAMS)
    artifacts.append(write(a.out/'PASSING_DEFENSE_ASOF_PROFILES_V2.json.gz',defense))
    # Deterministic representative profiles: ordinary, startup/no-own-history,
    # known-zero sack numerator and source-blocked annotations are explicit.
    examples={}
    for label,predicate in (('ordinary',lambda p:p['own']['games']>=8),('sparse',lambda p:not p['own']['games']),
                            ('known_zero_sacks',lambda p:p['own']['games'] and p['own']['counts']['sacks']==0)):
        examples[label]=next((p for p in profiles if predicate(p)),None)
    artifacts.append(write(a.out/'PROFILE_EXAMPLES_V2.json',examples))
    artifacts.append(write(a.out/'SOURCE_COVERAGE_V2.json',dict(version=VERSION,at_utc=now(),source_bindings=bindings,
        accepted_QB_inputs=dict(path=str(inputs_path.relative_to(ROOT)),sha256=sha(inputs_path),rows=len(inputs)),coverage=coverage,
        semantics='Current revised PBP; exact existing seven-day reconstruction. No original publication clocks; no authenticated expected-starter membership.',
        missing_fields=dict(charted_throwaway='NOT_ADDED; retained FTN annotations remain separate',pressure='SOURCE_NOT_QUALIFIED; sack is not pressure',
            catchability='NO_CHANGE; closed catchability experiment not repeated',designed_pass_call='NOT_OBSERVED; provider qb_dropback only'),
        attribution='nflverse/nflfastR PBP derivatives, CC-BY-4.0; see existing source receipts',new_raw_downloads=0)))
    check()
    receipt=dict(version=VERSION,completed_at_utc=now(),registration_sha256=sha(registration),source_tier='CURRENT_REVISED_SOURCE_SEVEN_DAY_RECONSTRUCTION',
        QB_game_input_rows=len(qbrows),team_game_input_rows=len(teamrows),historical_QB_profiles=len(profiles),defense_profiles=len(defense),teams=len(TEAMS),origins=len(origins),
        historical_query_universe='941 retained QB statistical rows, not authenticated pregame starters',
        current_query_status='ADAPTER_CAN_ACCEPT_EXPLICIT_QUALIFIED_QUERY; no authenticated current universe supplied',
        artifacts=artifacts,code_sha256={str(p.relative_to(ROOT)):sha(p) for p in (Path(__file__),ROOT/'nfl_v2/passing_opportunity_profiles.py')},
        resources=dict(wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                       source_rows_read=total_rows,public_bytes=sum(p.stat().st_size for p in a.out.rglob('*') if p.is_file()),new_fits=0,new_forecasts=0,new_scores=0,new_NFL_test_weeks=0))
    write(a.out/'EXTRACTION_RECEIPT_V2.json',receipt)
    print(json.dumps({k:receipt[k] for k in ('QB_game_input_rows','team_game_input_rows','historical_QB_profiles','defense_profiles','resources')}))

if __name__=='__main__':main()
