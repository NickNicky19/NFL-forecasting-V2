"""Metadata-only adapter of pinned original players[].props[] archive sources."""
from __future__ import annotations
import argparse,collections,csv,gzip,hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import prop_evidence_metadata_v2 as lexical
from nfl_v2 import scoring
from nfl_v2.identity import unique_gsis_bridge

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=ROOT/'reports/completion-20261031g/source-expansion'
TARGETS=set(scoring.TARGETS)-{'nick-chart-ppr-v1','anytime_td'}


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def save(path,value):
    with Path(path).open('xb')as f:f.write(canonical(value))
def metadata_only(text):
    # Reuse the single lexical scanner; this process has no threads. Added keys
    # identify the earlier schema and never admit forecast points or outcomes.
    prior=lexical.ALLOWED
    lexical.ALLOWED=prior|{'id','pos','team','opp','key','source','direction','late','saved_at','generated_at'}
    try:return lexical.project_metadata(text)
    finally:lexical.ALLOWED=prior


def main(private,cache):
    PRIVATE,CACHE=Path(private),Path(cache)
    start=time.monotonic();protocol=json.loads((PUBLIC/'FROZEN_ROLLING_SOURCE_ASSIGNMENTS.json').read_bytes())
    assignments=protocol['assignments'];byhead=collections.defaultdict(list)
    for r in assignments:byhead[r['selected_source_commit']].append(r)
    games={r['espn']:r for r in csv.DictReader((CACHE/'games.csv').open())if(r['season'],r['game_type'],r['week'])==('2026','REG','6')}
    with gzip.open(CACHE/'roster-week8-identity-2026.csv.gz','rt')as f:
        bridge=unique_gsis_bridge([(r['sleeper_id'],r['gsis_id'])for r in csv.DictReader(f)if r['season']=='2026'and int(r['week'])<=6 and r['sleeper_id']and r['gsis_id']],source_id='WEEK_LE6_EXACT_ID_BRIDGE_ONLY_NO_ROSTER_FEATURE_SUBSTITUTION')
    rows=[];counts=collections.Counter();sources=[];scope_counts=[]
    for head,aa in sorted(byhead.items()):
        tpath=PRIVATE/('W6_TRANSPORT_'+head+'.json');transport=json.loads(tpath.read_bytes());raw=transport['content'].encode();expected=transport['github_blob_sha']
        def gh(value):return hashlib.sha1(b'blob '+str(len(value)).encode()+b'\x00'+value).hexdigest()
        if gh(raw)!=expected and raw.endswith(b'\n')and gh(raw[:-1])==expected:raw=raw[:-1]
        if gh(raw)!=expected:raise ValueError('Git blob source identity mismatch')
        sourcepath=PRIVATE/('W6_SOURCE_'+head+'.json');sourcepath.write_bytes(raw)
        metadata,skipped=metadata_only(raw.decode());assert(metadata['season'],metadata['week'])==(2026,6)
        sourcegames={str(g['id']):g for g in metadata['games']};wanted={a['source_ESPN_event_id']:a for a in aa}
        top={side:{(str(r.get('player_id')),str(r.get('game_id')),r.get('key'))for r in metadata.get('picks',{}).get(side,[])}for side in('over','under')}
        within=collections.Counter()
        for pi,p in enumerate(metadata['players']):
            game=str(p.get('game_id'));a=wanted.get(game)
            if not a:continue
            if sourcegames[game]['kickoff']!=a['kickoff'].replace('+00:00','Z'):
                from datetime import datetime
                assert datetime.fromisoformat(sourcegames[game]['kickoff'].replace('Z','+00:00'))==datetime.fromisoformat(a['kickoff'])
            for qi,q in enumerate(p['props']):
                cat=q.get('key');within['all_prop_records']+=1
                if cat not in TARGETS:within['unsupported_contract']+=1;continue
                within['ordinary_records']+=1
                source=q.get('line_from');line=q.get('line')
                if not scoring.finite(line):within['missing_threshold']+=1;continue
                if source not in('dk','sleeper'):within['generated_or_unqualified_threshold']+=1;continue
                within['qualified_provider_labelled_threshold']+=1
                player=str(p.get('id'));gsis=bridge.get(player);canonicalgame=games[game]['game_id']
                row=dict(source_row_index=len(rows),source_head=head,source_git_blob=expected,source_player_index=pi,source_prop_index=qi,
                  source_game_id=game,source_player_id=player,game_id=canonicalgame,player_id=gsis,target=cat,position=p.get('pos'),team=p.get('team'),
                  line=line,line_from=source,original_side=q.get('lean'),side=q.get('lean'),source_marked_late=p.get('late'),top_over=(player,game,cat)in top['over'],top_under=(player,game,cat)in top['under'],
                  season=2026,week=6,kickoff=a['kickoff'],source_server_clock=a['source_server_clock'],server_retained_by=a['source_server_clock'],source_server_run_id=a['server_run_id'],source_T90_deadline=a['T90'],
                  identity_state='EXACT_SCHEDULE_AND_STABLE_ID_BRIDGE'if gsis else'PLAYER_ID_UNRESOLVED')
                if row['side']not in(None,'over','under'):raise ValueError('unknown original side encoding')
                rows.append(row)
        counts.update(within);scope_counts.append(dict(source_head=head,assigned_games=len(aa),source_clock=aa[0]['source_server_clock'],**dict(within)))
        sources.append(dict(head_sha=head,path='output/data/archive/2026_w06.json',blob_sha1=expected,source_sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),player_records=len(metadata['players']),metadata_skipped_unknown_scalars=skipped))
    keys=[(r['game_id'],r['player_id']or r['source_player_id'],r['target'])for r in rows]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate canonical game/player/target in frozen rolling panel')
    body=gzip.compress(canonical(dict(schema='v2-W6-rolling-source-metadata-v1',rows=rows)),mtime=0)
    with(PRIVATE/'FROZEN_W6_METADATA.json.gz').open('xb')as f:f.write(body)
    receipt=dict(state='METADATA_FROZEN_BEFORE_LABEL_JOIN_AND_GRADES',source_assignment_protocol_sha256=sha(PUBLIC/'FROZEN_ROLLING_SOURCE_ASSIGNMENTS.json'),code_sha256=sha(Path(__file__)),lexical_parser_sha256=sha(Path(lexical.__file__)),
      source_sources=sources,metadata_sha256=hashlib.sha256(body).hexdigest(),source_count=len(sources),games=len({r['game_id']for r in rows}),provider_thresholds=len(rows),original_sides=dict(collections.Counter(r['side']or'ABSTAIN'for r in rows)),line_sources=dict(collections.Counter(r['line_from']for r in rows)),categories=dict(collections.Counter(r['target']for r in rows)),
      source_marked_late_counts={str(k):v for k,v in collections.Counter(r['source_marked_late']for r in rows).items()},identity_states=dict(collections.Counter(r['identity_state']for r in rows)),source_scope_counts=scope_counts,
      source_schedule_sha256=sha(CACHE/'games.csv'),identity_bridge_sha256=sha(CACHE/'roster-week8-identity-2026.csv.gz'),source_census=dict(counts),new_fits=0,new_forecasts=0,new_inference=0,new_grades=0,current_Week8_outcomes_read=0,wall_seconds=time.monotonic()-start)
    save(PUBLIC/'METADATA_QUALIFICATION_RECEIPT.json',receipt)
    (PUBLIC/'METADATA_ADAPTER_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({k:receipt[k]for k in('state','source_count','games','provider_thresholds','original_sides','line_sources','categories','source_marked_late_counts','identity_states','wall_seconds')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--private',required=True);p.add_argument('--source-root',required=True);a=p.parse_args();main(a.private,a.source_root)
