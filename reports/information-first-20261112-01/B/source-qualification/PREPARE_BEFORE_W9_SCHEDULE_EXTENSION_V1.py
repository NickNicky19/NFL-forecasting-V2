"""Qualified two-flag QB-game projection and W9-only context extension.

FTN-dependent projections: CC-BY-SA-4.0, FTN Data via nflverse.
PBP/stat-only context projection: CC-BY-4.0, nflverse/nflfastR.
Raw feeds stay outside public Git. No fitting, inference or scoring occurs here.
"""
import argparse
import collections
import csv
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[4]
while not (ROOT/'nfl_v2').exists(): ROOT=ROOT.parent
sys.path.insert(0,str(ROOT))
from nfl_v2.hgb_control import schedules
from tools.run_player_context_wave import read,write,sha,now

FLAGS=('is_interception_worthy','is_throw_away')
FIELDS=('ydstogo','yardline_100','game_seconds_remaining','score_differential')


def number(value):
    try:
        value=float(value)
        return value if math.isfinite(value) else None
    except (TypeError,ValueError):return None


def credited(row):
    return all(number(row[k])==v for k,v in [('pass_attempt',1),('sack',0),('two_point_attempt',0),('play_deleted',0)])


def playkey(row,ftn=False):
    game=row['nflverse_game_id'if ftn else'game_id']
    value=number(row['nflverse_play_id'if ftn else'play_id'])
    if not game or value is None or value!=int(value):raise ValueError('Invalid game/play identity')
    return game,str(int(value))


def context(row):
    down=number(row['down']);air=number(row['air_yards'])
    d=int(down)-1 if down in(1,2,3,4)else 4
    j=4 if air is None else 0 if air<0 else 1 if air<10 else 2 if air<20 else 3
    return d*5+j


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--old-root',type=Path,required=True);ap.add_argument('--fresh-root',type=Path,required=True)
    ap.add_argument('--weekly',type=Path,required=True);ap.add_argument('--games',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=True)
    oldinputs=ROOT/'reports/player-context-matchup-01/B/source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz';oldrows=read(oldinputs)
    oldexpected={r['name']:r['sha256']for r in read(ROOT/'reports/player-context-matchup-01/B/source-qualification-v1/SOURCE_RECEIPTS.json')['sources']}
    fresh_expected={'ftn_charting_2026.csv':'8c377a0af1a932a8d19b091683d91fbfb3cd812cda45a5f50cfbba810b9ab769',
                    'play_by_play_2026.csv.gz':'1aa9d0dadf7152ee17b8df94b0d8e5c944d43c4cf217518acd60311455cbe818'}
    games=schedules(a.games);w9plays=collections.defaultdict(list);physical=set()
    with gzip.open(a.fresh_root/'play_by_play_2026.csv.gz','rt')as f:
        for r in csv.DictReader(f):
            if r['season_type']!='REG'or number(r['week'])!=9:continue
            for name in('passer_player_id','rusher_player_id','receiver_player_id'):
                if r.get(name):physical.add((r['game_id'],r[name]))
            if credited(r):w9plays[r['game_id'],r['passer_player_id']].append(r)
    w9=[];recon=[]
    with a.weekly.open()as f:
        for r in csv.DictReader(f):
            if r['season_type']!='REG'or r['position']!='QB'or int(r['week'])!=9:continue
            key=r['game_id'],r['player_id'];g=games[key[0]];plays=w9plays.get(key,[])
            aa=[0]*25;cc=[0]*25;contexts={name:[]for name in FIELDS};dest=collections.Counter()
            for x in plays:
                if x['posteam']!=r['team']or x['defteam']!=r['opponent_team']:raise ValueError('Historical team/opponent mismatch')
                j=context(x);aa[j]+=1;cc[j]+=int(number(x['complete_pass'])==1)
                for name in FIELDS:
                    value=number(x[name])
                    if value is not None:contexts[name].append(value)
                dest[x['pass_location']or'UNKNOWN']+=1
            official=[number(r['attempts']),number(r['completions'])]
            if any(v is None or v<0 or int(v)!=v for v in official):raise ValueError('Unknown official target')
            parity=official==[sum(aa),sum(cc)]
            if not parity:raise ValueError('W9 credited PBP/official target mismatch')
            participated=key in physical or any((number(r.get(k))or 0)>0 for k in('attempts','carries','sacks_suffered','receptions'))
            q=dict(game_id=key[0],player_id=key[1],season=2026,week=9,team=r['team'],opponent=r['opponent_team'],
                   kickoff=g['kickoff'],available=g['kickoff']+7*86400,attempts=sum(aa),completions=sum(cc),
                   context_attempts=aa,context_completions=cc,
                   field_context={name:dict(mean=sum(v)/len(v)if v else None,n=len(v))for name,v in contexts.items()},
                   pass_destination_counts=dict(dest),known_receiver_throws=sum(bool(x['receiver_player_id'])for x in plays),
                   unknown_receiver_throws=sum(not x['receiver_player_id']for x in plays),
                   throwing_population='PBP credited passer; QB target eligibility separately reconciled to official rows'if plays else'Official explicitly reported zero QB stat row',
                   official_attempts=int(official[0]),official_completions=int(official[1]),target_parity=parity,position='QB',
                   physical_participation=participated,label_status='SUPPORTED_PLAYED'if participated else'UNKNOWN_PARTICIPATION',
                   population='RETROSPECTIVE_OFFICIAL_QB_STAT_ROWS_NOT_EXANTE_ROSTER')
            w9.append(q);recon.append(dict(game_id=key[0],attempts=q['attempts'],completions=q['completions'],participated=participated))
    assert len(w9)==38 and len({(r['game_id'],r['player_id'])for r in w9})==38
    write(a.out/'QB_CONTEXT_W9_EXTENSION_V1.json.gz',w9)
    allrows=oldrows+w9;rowmap={(r['game_id'],r['player_id']):r for r in allrows};assert len(rowmap)==len(allrows)
    values={key:dict(**{name:r[name]for name in('game_id','player_id','season','week','team','opponent','kickoff','available')},
                    eligible_throws=r['attempts'],charted_throws=0,
                    flags={name:dict(known=0,positive=0,unknown=0)for name in FLAGS},date_pulled_min=None,date_pulled_max=None)
            for key,r in rowmap.items()}
    binding=[];weekly=[];semantics=[]
    for year in range(2022,2027):
        pieces=[(a.old_root,lambda w:year!=2026 or w<=8,'FROZEN_BASE_VINTAGE')]
        if year==2026:pieces.append((a.fresh_root,lambda w:w==9,'CURRENT_W9_ONLY_EXTENSION'))
        seenftn=set();seenpbp=set();weekstats=collections.defaultdict(collections.Counter);fieldcounts=collections.defaultdict(collections.Counter)
        for source_root,predicate,piece in pieces:
            pp=source_root/f'play_by_play_{year}.csv.gz';fp=source_root/f'ftn_charting_{year}.csv'
            expected=oldexpected if source_root==a.old_root else fresh_expected
            for path in(pp,fp):
                assert sha(path)==expected[path.name]
                binding.append(dict(season=year,piece=piece,name=path.name,bytes=path.stat().st_size,sha256=sha(path),
                                    used_weeks='<=8'if year==2026 and piece=='FROZEN_BASE_VINTAGE'else'9'if year==2026 else'REG'))
            pbp={};eligible={};counts=collections.Counter()
            with gzip.open(pp,'rt')as f:
                for r in csv.DictReader(f):
                    if r['season_type']!='REG'or not predicate(int(r['week'])):continue
                    pk=playkey(r)
                    if pk in seenpbp:raise ValueError('Duplicate PBP game/play key')
                    seenpbp.add(pk);pbp[pk]=r
                    key=r['game_id'],r['passer_player_id']
                    if credited(r)and key in rowmap:
                        eligible[pk]=key;counts[key]+=1
                        weekstats[int(r['week'])]['eligible_QB_throws']+=1
                        weekstats[int(r['week'])]['credited_no_play_rows_retained']+=int(r['play_type']=='no_play')
                        weekstats[int(r['week'])]['credited_spike_rows_retained']+=int(number(r['qb_spike'])==1)
            for key,count in counts.items():
                if count!=rowmap[key]['attempts']:raise ValueError('Existing credited attempt denominator changed')
            with fp.open()as f:
                for r in csv.DictReader(f):
                    if not predicate(int(r['week'])):continue
                    pk=playkey(r,True)
                    # Postseason FTN rows have no REG PBP entry; retain audit exclusion.
                    if pk in seenftn:raise ValueError('Duplicate FTN game/play key')
                    seenftn.add(pk);w=int(r['week']);wk=weekstats[w];wk['FTN_rows']+=1
                    wk['exact_PBP_matches']+=int(pk in pbp);wk['unmatched_REG_or_postseason_FTN_rows']+=int(pk not in pbp)
                    for name in FLAGS+('is_catchable_ball','is_drop','is_screen_pass','is_play_action','read_thrown','n_blitzers','n_pass_rushers'):
                        fieldcounts[name][r[name]or'MISSING']+=1
                    if pk not in eligible:continue
                    key=eligible[pk];v=values[key];v['charted_throws']+=1;wk['matched_eligible_QB_throws']+=1
                    for name in FLAGS:
                        flag=r[name]
                        if flag not in('TRUE','FALSE',''):raise ValueError('Unexpected flag code')
                        v['flags'][name]['known']+=int(flag!='');v['flags'][name]['positive']+=int(flag=='TRUE');v['flags'][name]['unknown']+=int(flag=='')
                        wk[name+'_known']+=int(flag!='');wk[name+'_positive']+=int(flag=='TRUE')
                    d=r['date_pulled']
                    if d:v['date_pulled_min']=min(v['date_pulled_min']or d,d);v['date_pulled_max']=max(v['date_pulled_max']or d,d)
        for key,v in values.items():
            if v['season']!=year:continue
            assert 0<=v['charted_throws']<=v['eligible_throws']
            for f in v['flags'].values():assert 0<=f['positive']<=f['known']<=v['charted_throws']and f['known']+f['unknown']==v['charted_throws']
        weekly.extend(dict(season=year,week=w,**dict(v))for w,v in sorted(weekstats.items()))
        semantics.append(dict(season=year,values={name:dict(counts)for name,counts in fieldcounts.items()}))
    result=sorted(values.values(),key=lambda r:(r['kickoff'],r['game_id'],r['player_id']))
    write(a.out/'FTN_BALL_QUALITY_QB_GAME_INPUTS_V1.json.gz',result)
    write(a.out/'SOURCE_JOIN_AND_DENOMINATOR_RECEIPT_V1.json',dict(at_UTC=now(),state='QUALIFIED_CURRENT_VINTAGE_DIAGNOSTIC_TWO_FLAG_SOURCE',
        old_QB_context_input_sha256=sha(oldinputs),old_QB_context_rows_preserved=len(oldrows),new_W9_QB_context_rows=len(w9),W9_all_target_parity=True,W9_all_physical_participation=all(r['physical_participation']for r in w9),
        games_schedule_sha256=sha(a.games),weekly_stats_sha256=sha(a.weekly),source_bindings=binding,weekly=weekly,field_code_counts=semantics,
        ball_quality_rows=len(result),definitions='Eligible QB credited attempts: pass_attempt1,sack0,two_point_attempt0,play_deleted0; knownTRUE/FALSE flags only. Sacks/deleted/twopoint/unknown safety excluded; statcredited no_play/spikes/throwaways retained. Known false differs from unknown/unmatched.',
        chronology='Same declaredstrict kickoff+7days available policy as baseline; originalpublicationunknown. date_pulled onlyAPIretrieval, never backdated sourceavailability. W9charting is postgame, noown-gamepredictor.',
        hybrid_vintage='Frozen2022-25 andfrozen2026W1-8 sources retained; fresh2026W9 only appended. No silent historicalbase revision.',
        source_rights='FTN quality derivatives/models/results CC-BY-SA4.0, FTN Data via nflverse; PBP/stat-onlycontext derivatives CC-BY4.0,nflverse/nflfastR; rawfeeds notpublished.',
        new_fits=0,new_predictions=0,new_scores=0))
    print(json.dumps(dict(old_context_rows=len(oldrows),new_W9_rows=len(w9),ball_quality_rows=len(result),source_read_pieces=len(binding))))


if __name__=='__main__':main()
