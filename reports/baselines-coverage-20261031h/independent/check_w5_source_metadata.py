"""Independent H W5 immutable-blob/clock/identity/selection-metadata audit."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys
from zoneinfo import ZoneInfo


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def clock(t):return datetime.fromisoformat(t.replace('Z','+00:00'))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--private-source',type=Path,required=True);ap.add_argument('--football-source',type=Path,required=True);ap.add_argument('--week',type=int,required=True);ap.add_argument('--public-root',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();sys.path.insert(0,str(a.repo_root.resolve()))
    # Reuse only the pre-existing lexical field projector, never a producer join/grader.
    from nfl_v2 import prop_evidence_metadata_v2 as lexical
    allowed=lexical.ALLOWED;lexical.ALLOWED=allowed|{'id','pos','team','opp','key','source','direction','late','saved_at','generated_at'}
    public=a.public_root;p=read(public/'FROZEN_ROLLING_SOURCE_ASSIGNMENTS.json');receipt=read(public/'METADATA_QUALIFICATION_RECEIPT.json')
    assert sha(public/'FROZEN_ROLLING_SOURCE_ASSIGNMENTS.json')==receipt['source_assignment_protocol_sha256']
    runpath=a.private_source/f'W{a.week}_SERVER_RUN_METADATA.json';assert sha(runpath)==p['source_run_metadata_sha256'];runs=read(runpath)['runs'];assert runs
    assignments=p['assignments'];assert len(assignments)==14 and len({r['game_id']for r in assignments})==14
    assert sha(a.football_source/'games.csv')==receipt['source_schedule_sha256'];assert sha(a.football_source/'roster-week8-identity-2026.csv.gz')==receipt['identity_bridge_sha256']
    with(a.football_source/'games.csv').open()as f:schedule={r['espn']:r for r in csv.DictReader(f)if(r['season'],r['game_type'],r['week'])==('2026','REG',str(a.week))}
    byhead=defaultdict(list)
    for row in assignments:
        possible=[r for r in runs if clock(r['created_at'])<=clock(row['T90'])]
        chosen=max(possible,key=lambda r:(clock(r['created_at']),r['head_sha'],r['id']))
        assert(chosen['head_sha'],chosen['id'],chosen['created_at'])==(row['selected_source_commit'],row['server_run_id'],row['source_server_clock'])
        g=schedule[row['source_ESPN_event_id']];kickoff=datetime.fromisoformat(g['gameday']+'T'+g['gametime']).replace(tzinfo=ZoneInfo('America/New_York'))
        assert g['game_id']==row['game_id']and kickoff==clock(row['kickoff'])and kickoff-timedelta(minutes=90)==clock(row['T90'])
        byhead[row['selected_source_commit']].append(row)
    missing=p['missing_games'];assert len(schedule)==15 and len(assignments)==14 and len(missing)==1
    assert set(r['game_id']for r in assignments)|set(r['game_id']for r in missing)==set(g['game_id']for g in schedule.values())
    for r in missing:assert not any(clock(v['created_at'])<=clock(r['T90'])for v in runs)
    repo=read(public.parent/'independent/PRODUCTION_REPOSITORY_CREATION_READBACK.json');assert repo['created_at']==p['repository_creation_clock']and clock(repo['created_at'])>clock(missing[0]['kickoff'])
    forward,reverse=defaultdict(set),defaultdict(set)
    with gzip.open(a.football_source/'roster-week8-identity-2026.csv.gz','rt')as f:
        for r in csv.DictReader(f):
            if r['season']=='2026'and int(r['week'])<=a.week and r['sleeper_id']and r['gsis_id']:forward[r['sleeper_id']].add(r['gsis_id']);reverse[r['gsis_id']].add(r['sleeper_id'])
    bridge={k:next(iter(v))for k,v in forward.items()if len(v)==1 and len(reverse[next(iter(v))])==1}
    source_receipts={r['head_sha']:r for r in receipt['source_sources']};expected=[];census=Counter();targets={'pass_yd','pass_td','pass_cmp','pass_att','pass_int','rush_yd','rush_att','rec','rec_yd','rush_rec_yd'};aliases={'LAR':'LA','WSH':'WAS','JAC':'JAX'}
    for head,aa in sorted(byhead.items()):
        raw=(a.private_source/(f'W{a.week}_SOURCE_'+head+'.json')).read_bytes();transport=read(a.private_source/(f'W{a.week}_TRANSPORT_'+head+'.json'));source=source_receipts[head]
        assert transport['head_sha']==head and transport['github_blob_sha']==source['blob_sha1']
        assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==source['blob_sha1']and hashlib.sha256(raw).hexdigest()==source['source_sha256']
        metadata,skipped=lexical.project_metadata(raw.decode());assert(metadata['season'],metadata['week'])==(2026,a.week)
        sourcegames={str(g['id']):g for g in metadata['games']};assigned={r['source_ESPN_event_id']:r for r in aa}
        top={side:{(str(r.get('player_id')),str(r.get('game_id')),r.get('key'))for r in metadata.get('picks',{}).get(side,[])}for side in('over','under')}
        for pi,player in enumerate(metadata['players']):
            game=str(player.get('game_id'));assignment=assigned.get(game)
            if assignment is None:continue
            assert clock(sourcegames[game]['kickoff'])==clock(assignment['kickoff'])
            for qi,prop in enumerate(player['props']):
                census['all_prop_records']+=1;target=prop.get('key')
                if target not in targets:census['unsupported_contract']+=1;continue
                census['ordinary_records']+=1;line=prop.get('line')
                if not isinstance(line,(int,float))or isinstance(line,bool):census['missing_threshold']+=1;continue
                if prop.get('line_from')not in('dk','sleeper'):census['generated_or_unqualified_threshold']+=1;continue
                census['qualified_provider_labelled_threshold']+=1;sid=str(player['id']);pid=bridge.get(sid)
                g=schedule[game];team=aliases.get(player.get('team'),player.get('team'));assert team in(g['home_team'],g['away_team'])
                expected.append(dict(source_row_index=len(expected),source_head=head,source_git_blob=source['blob_sha1'],source_player_index=pi,source_prop_index=qi,source_game_id=game,source_player_id=sid,game_id=g['game_id'],player_id=pid,target=target,position=player.get('pos'),team=player.get('team'),line=line,line_from=prop['line_from'],original_side=prop.get('lean'),side=prop.get('lean'),source_marked_late=player.get('late'),top_over=(sid,game,target)in top['over'],top_under=(sid,game,target)in top['under'],season=2026,week=a.week,kickoff=assignment['kickoff'],source_server_clock=assignment['source_server_clock'],server_retained_by=assignment['source_server_clock'],source_server_run_id=assignment['server_run_id'],source_T90_deadline=assignment['T90'],identity_state='EXACT_SCHEDULE_AND_STABLE_ID_BRIDGE'if pid is not None else'PLAYER_ID_UNRESOLVED'))
    file=a.private_source/f'FROZEN_W{a.week}_METADATA.json.gz';assert sha(file)==receipt['metadata_sha256'];retained=json.loads(gzip.decompress(file.read_bytes()))['rows'];assert expected==retained and len(expected)==receipt['provider_thresholds']
    assert len({(r['game_id'],r['player_id']or('SOURCE-ID:'+r['source_player_id']),r['target'])for r in expected})==receipt['provider_thresholds']
    assert Counter(r['side']or'ABSTAIN'for r in expected)==receipt['original_sides']
    assert dict(census)==receipt['source_census']
    report=dict(state='PASS_INDEPENDENT_ROLLING_SERVER_CLOCK_GIT_BLOB_MEMBERSHIP_AND_CONTEXT',week=a.week,at=datetime.now(timezone.utc).isoformat(),protocol_sha256=receipt['source_assignment_protocol_sha256'],metadata_sha256=receipt['metadata_sha256'],server_run_metadata_sha256=p['source_run_metadata_sha256'],server_runs_compared=len(runs),game_assignments=14,immutable_sources=len(byhead),canonical_provider_threshold_rows=len(expected),original_selected=sum(r['side']in('over','under')for r in expected),original_over=sum(r['side']=='over'for r in expected),original_under=sum(r['side']=='under'for r in expected),original_abstentions=sum(r['side']is None for r in expected),source_census=dict(census),side_grouping='Original retained pre-outcome selected side; no result crossing or grades computed.',source_truth_limit='Pinned Git blob plus retained GitHub run head/created_at metadata binds pregame bytes. No independent new GitHub API request, quote freshness, book rules, prices or actual NFL label truth authenticated here.',unresolved_identity_rows=sum(r['player_id']is None for r in expected),new_fits=0,new_inference=0,new_forecasts=0,new_grades=0,new_NFL_observations=0,current2026_Week8_outcomes_read=0)
    with a.output.open('x')as f:json.dump(report,f,indent=2);f.write('\n')
    print(json.dumps({k:report[k]for k in('state','game_assignments','immutable_sources','canonical_provider_threshold_rows','original_selected','original_abstentions')}))


if __name__=='__main__':main()
