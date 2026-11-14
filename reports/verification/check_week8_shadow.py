"""Independent audit of already captured research shadows. No inference run/fit."""
from collections import Counter,defaultdict
import csv
from datetime import datetime
from decimal import Decimal,localcontext
import gzip,hashlib,json,math,re,tarfile
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from check_empirical_diagnostic import ACTION_COUNTS,ACTION_YARDS,count,num,value

def stamp(x):
    d=datetime.fromisoformat(x.replace('Z','+00:00'));assert d.tzinfo is not None
    return d

def hashfile(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()

def verify_restoration(archive,public):
    binding=json.loads((public/'PRIVATE_RESTORATION.json').read_text())
    protocol=json.loads((public/'FROZEN_PROTOCOL.json').read_text())
    assert archive.stat().st_size==binding['archive_bytes'] and hashfile(archive)==binding['archive_sha256']
    expected={'shadow-forecasts.json.gz':binding['predictions_sha256'],
        'frozen-queries.json':protocol['query_membership_sha256'],
        'week8-production-board-911a81.json':protocol['frozen_board_sha256'],
        'week8-public-original-3907ca38.json':protocol['frozen_feed_sha256'],
        'week8_shadow.py':protocol['code_sha256'],'empirical_benchmark.py':protocol['helper_code_sha256'],
        'FROZEN_PROTOCOL.json':hashfile(public/'FROZEN_PROTOCOL.json'),
        'CAPTURE_RECEIPT.json':hashfile(public/'CAPTURE_RECEIPT.json')}
    expected.update({x['name']:x['sha256'] for x in protocol['source_ids'] if x['name'].endswith('.gz')})
    with tarfile.open(archive,'r:gz') as t:
        by_name=defaultdict(list)
        for member in t.getmembers():
            if member.isfile():by_name[Path(member.name).name].append(member)
        for name,sha in expected.items():
            assert len(by_name[name])==1
            assert hashlib.sha256(t.extractfile(by_name[name][0]).read()).hexdigest()==sha
    return dict(public_safe_artifact_id=binding['artifact_id'],archive_sha256=binding['archive_sha256'],
        independently_checked_restored_members=len(expected),restored_predictions_sha256=binding['predictions_sha256'],
        evidence='fresh downloaded archive bytes independently inspected; private-store ownership/sharing attested separately by executor')

def audit(source,private,public,evidence):
    protocol=json.loads((public/'FROZEN_PROTOCOL.json').read_text())
    receipt=json.loads((public/'CAPTURE_RECEIPT.json').read_text())
    query_bytes=(private/'frozen-queries.json').read_bytes();queries=json.loads(query_bytes)
    blob=(private/'shadow-forecasts.json.gz').read_bytes();decoded=gzip.decompress(blob);rows=json.loads(decoded)['rows']
    assert hashlib.sha256(blob).hexdigest()==receipt['private_forecast_sha256']
    assert hashlib.sha256(decoded).hexdigest()==receipt['private_uncompressed_sha256']
    assert hashlib.sha256(query_bytes).hexdigest()==protocol['query_membership_sha256']==receipt['query_membership_sha256']
    assert hashfile(public/'FROZEN_PROTOCOL.json')==receipt['protocol_sha256']
    assert hashfile(ROOT/'nfl_v2/week8_shadow.py')==receipt['code_sha256']==protocol['code_sha256']
    assert hashfile(ROOT/'nfl_v2/empirical_benchmark.py')==receipt['helper_code_sha256']
    for item in protocol['source_ids']:
        p=source/item['name'];assert p.stat().st_size==item['bytes'];assert hashfile(p)==item['sha256']
    assert protocol['histories']=={'H-CURRENT':[2026],'H-RECENT':[2025,2026],'H-MULTI':[2022,2023,2024,2025,2026]}
    # Reconstruct strict bijective identity bridge independently, not by names.
    forward=defaultdict(set);reverse=defaultdict(set)
    with gzip.open(source/'roster-week8-identity-2026.csv.gz','rt') as f:
        for r in csv.DictReader(f):
            if r['season']=='2026' and int(r['week'])<=8 and r['sleeper_id'] and r['gsis_id']:
                forward[r['sleeper_id']].add(r['gsis_id']);reverse[r['gsis_id']].add(r['sleeper_id'])
    bridge={sid:next(iter(gs)) for sid,gs in forward.items() if len(gs)==1
        and re.fullmatch(r'00-\d{7}',next(iter(gs))) and len(reverse[next(iter(gs))])==1}
    with gzip.open(source/'players-week8-identity.csv.gz','rt') as f:
        players={r['gsis_id'] for r in csv.DictReader(f) if re.fullmatch(r'00-\d{7}',r['gsis_id'] or '')}
    feed=json.loads((evidence/'week8-public-original-3907ca38.json').read_text())
    board=json.loads((evidence/'week8-production-board-911a81.json').read_text())
    assert hashfile(evidence/'week8-public-original-3907ca38.json')==protocol['frozen_feed_sha256']
    assert hashfile(evidence/'week8-production-board-911a81.json')==protocol['frozen_board_sha256']
    metadata=defaultdict(list)
    for b in board['players']:metadata[(str(b['id']),str(b['game_id']))].append(b)
    by_q={q['query_id']:q for q in queries};assert len(by_q)==len(queries)
    games={};schedule={}
    with (source/'games.csv').open() as f:
        for r in csv.DictReader(f):
            if r['game_type']!='REG' or int(r['season']) not in range(2022,2027) or (int(r['season'])==2026 and int(r['week'])>8):continue
            t=datetime.fromisoformat(r['gameday']+'T'+r['gametime']).replace(tzinfo=ZoneInfo('America/New_York'))
            g=dict(kickoff=t,home=r['home_team'],away=r['away_team'],season=int(r['season']),week=int(r['week']))
            schedule[r['game_id']]=g
            if g['season']==2026 and g['week']==8:games[r['espn']]=(r['game_id'],g)
    query_checks=0;expected_membership=set()
    for r in feed['rows']:
        sid,espn,target=str(r['player_id']),str(r['game_id']),r['category']
        qid=hashlib.sha256(canonical((sid,espn,target))).hexdigest();q=by_q[qid];expected_membership.add(qid)
        gid,g=games[espn];assert stamp(r['kickoff_utc'])==g['kickoff']==stamp(q['kickoff_utc'])
        assert q['game_id']==gid and q['target']==target and q['sleeper_id']==sid and q['owner_input_cutoff_utc']==r['source_cutoff_utc']
        bs=metadata[(sid,espn)];blocked=None;position=None
        if len(bs)!=1:blocked='MISSING_OR_AMBIGUOUS_FROZEN_BOARD_CONTEXT'
        else:
            b=bs[0];position=b['pos']
            if position not in {'QB','RB','FB','WR','TE'}:blocked='UNSUPPORTED_POSITION'
            else:
                alias=lambda t:'LA' if t=='LAR' else t
                if (alias(b['team']),alias(b['opp'])) not in [(g['home'],g['away']),(g['away'],g['home'])]:blocked='BOARD_TEAM_OPPONENT_MISMATCH'
        pid=bridge.get(sid)
        if pid is None:blocked=blocked or 'NO_UNIQUE_QUALIFIED_GSIS_BRIDGE'
        elif pid not in players:blocked=blocked or 'GSIS_NOT_IN_CURRENT_PLAYER_REGISTRY'
        assert q['player_id']==pid and q['position']==position and q['blocked_reason']==blocked
        query_checks+=7
    assert expected_membership==set(by_q)
    origin=stamp(receipt['actual_feature_cutoff_utc']);started=stamp(receipt['actual_inference_started_at'])
    ended=stamp(receipt['actual_inference_completed_at']);persisted=stamp(receipt['actual_persistence_completed_at'])
    assert stamp(protocol['registered_at_utc'])<=origin<=started<=ended<=persisted
    seen=set();grouped=defaultdict(list);clocks=0;late=Counter();matrix=Counter();sample={}
    for r in rows:
        q=by_q[r['query_id']]
        for k,v in q.items():assert r[k]==v
        k=(r['query_id'],r['history_regime'],r['product']);assert k not in seen;seen.add(k)
        assert r['history_regime'] in protocol['histories']
        assert stamp(r['feature_cutoff_utc'])==origin
        issued=stamp(r['issued_at_utc']);kickoff=stamp(r['kickoff_utc'])
        assert started<=issued<=ended<=persisted<kickoff
        assert math.isclose(r['actual_horizon_seconds'],(kickoff-issued).total_seconds(),abs_tol=1e-9)
        expected='LATER_THAN_OWNER_INPUT_CUTOFF' if issued>stamp(q['owner_input_cutoff_utc']) else 'BEFORE_OWNER_INPUT_CUTOFF'
        assert r['owner_cutoff_status']==expected
        assert not any(k in r for k in ['actual','outcome','label','realized_stats'])
        if q['blocked_reason']:
            assert r['status']=='ABSTAIN' and r['prediction'] is None and r['fallback'] is None and r['used_n'] is None
            assert r['abstention_reason']==q['blocked_reason']
        else:
            assert r['status']=='ISSUED_SHADOW' and r['abstention_reason'] is None
            assert isinstance(r['prediction'],(int,float)) and math.isfinite(r['prediction'])
            if r['product']=='event_probability':assert 0<=r['prediction']<=1 and r['target']=='anytime_td'
            if r['latest_training_available_utc']:assert stamp(r['latest_training_available_utc'])<origin
            late[expected]+=1
            sk=(r['target'],r['history_regime'],r['fallback'])
            if sk not in sample or r['query_id']<sample[sk]['query_id']:sample[sk]=r
        grouped[r['query_id']].append(r);clocks+=6
        matrix[(r['target'],r['history_regime'],r['product'],r['status'],r['abstention_reason'] or r['fallback'])]+=1
    for qid,rs in grouped.items():
        products=['event_probability'] if by_q[qid]['target']=='anytime_td' else ['empirical_mean','lower_median']
        assert {(r['history_regime'],r['product']) for r in rs}=={(a,p) for a in protocol['histories'] for p in products}
    published=json.loads((public/'PROCEDURE_MATRIX.json').read_text())
    assert {(r['target'],r['history_regime'],r['product'],r['state'],r['reason_or_fallback']):r['rows'] for r in published}==dict(matrix)
    observations=defaultdict(list);future_rows=0
    for year in range(2022,2027):
        with (source/f'stats_player_week_{year}.csv').open() as f:
            for r in csv.DictReader(f):
                if r['season_type']!='REG' or int(r['season'])!=year or (year==2026 and int(r['week'])>7):continue
                g=schedule[r['game_id']];available=int(g['kickoff'].timestamp())+7*86400
                if available>=origin.timestamp():future_rows+=1;continue
                if r['position'] not in {'QB','RB','FB','WR','TE'} or not re.fullmatch(r'00-\d{7}',r['player_id']):continue
                assert (r['team'],r['opponent_team']) in [(g['home'],g['away']),(g['away'],g['home'])]
                played=any(count(num(r[k])) and num(r[k])>0 for k in ACTION_COUNTS) or any(num(r[k]) not in [None,0] for k in ACTION_YARDS)
                if not played:continue
                for target in protocol['targets']:
                    v=value(target,r)
                    if v is not None:observations[(target,r['position'])].append((year,available,r['player_id'],v,int(r['week'])))
    assert future_rows==receipt['source_row_counts']['unavailable_before_numeric_decode']
    prefix_checks=0;fallback_types=Counter();sampled_rows=0
    for sampled in sample.values():
        qid=sampled['query_id'];arm=sampled['history_regime']
        candidates=[o for o in observations[(sampled['target'],sampled['position'])] if o[0] in protocol['histories'][arm]]
        own=[o for o in candidates if o[2]==sampled['player_id']];chosen=own or candidates
        fb='none' if own else 'position_empirical' if candidates else 'constant_zero'
        vs=sorted(o[3] for o in chosen);latest=max((o[1] for o in chosen),default=None)
        assert all(o[1]<origin.timestamp() and not(o[0]==2026 and o[4]>7) for o in chosen)
        for r in grouped[qid]:
            if r['history_regime']!=arm:continue
            expected=(sum(vs)/Decimal(len(vs)) if r['product']!='lower_median' else vs[(len(vs)-1)//2]) if vs else Decimal(0)
            assert math.isclose(float(expected),r['prediction'],rel_tol=3e-14,abs_tol=3e-12)
            assert (r['own_n'],r['used_n'],r['fallback'])==(len(own),len(chosen),fb)
            assert (stamp(r['latest_training_available_utc']).timestamp() if r['latest_training_available_utc'] else None)==latest
            prefix_checks+=4;sampled_rows+=1;fallback_types[(arm,fb)]+=1
    return dict(status='PASS_NEW_SHADOW_CAPTURE_WITH_LATE_OWNER_CUTOFF_DISCLOSED',
        forecast_sha256=receipt['private_forecast_sha256'],query_membership_sha256=protocol['query_membership_sha256'],
        source_files_hash_verified=len(protocol['source_ids']),query_cells=len(queries),query_binding_checks=query_checks,
        output_views=len(rows),issued_views=sum(r['status']=='ISSUED_SHADOW' for r in rows),
        abstention_views=sum(r['status']=='ABSTAIN' for r in rows),chronology_field_checks=clocks,
        raw_prefix_sampled_views=sampled_rows,raw_prefix_checks=prefix_checks,
        sample_fallback_coverage=[dict(history=a,fallback=fb,views=n) for (a,fb),n in sorted(fallback_types.items())],
        owner_cutoff_status=dict(late),actual_feature_cutoff_utc=origin.isoformat(),actual_persisted_at=persisted.isoformat(),
        minimum_horizon_seconds=min(r['actual_horizon_seconds'] for r in rows if r['status']=='ISSUED_SHADOW'),
        excluded_unavailable_source_rows=future_rows,all_issued_persisted_before_kickoff=True,
        original_optimizer_fits_added=0,new_inference_runs_added=0,week8_outcomes_read_or_scored=0,
        offhost_restore_verification='root executor must bind fresh restored private-bundle bytes; this script checks supplied retained bytes only',
        limits=['First-game shadows were issued after owner T-90 input cutoff; late tags retained, no backdating.',
            'One empirical family with3historyarms; not five independent ready models per category.',
            'No chart PPR, official capture, deployed website procedure, calibrated law qualification or scoring claim.',
            'Current identity snapshots are source-bridged; historical statistics current-vintage with assumed7dayavailability.',
            'Eligibility is the frozen existing public-feed population, not proof of game-day appearance.'])

if __name__=='__main__':
    with localcontext() as ctx:
        ctx.prec=50
        result=audit(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]),Path(sys.argv[4]))
        if len(sys.argv)>5:
            result['offhost_restoration']=verify_restoration(Path(sys.argv[5]),Path(sys.argv[3]))
            result['offhost_restore_verification']='fresh downloaded archive independently hash/member-checked; unchanged original capture and cutoff tags'
    (ROOT/'reports/verification/WEEK8_SHADOW_INDEPENDENT_QA.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','query_cells','output_views','issued_views','abstention_views','query_binding_checks','chronology_field_checks','raw_prefix_checks','owner_cutoff_status']},indent=2))
