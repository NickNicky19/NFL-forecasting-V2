"""Build a private, source-bound W9 QB offered panel; no grading or modeling."""
import argparse
import collections
import datetime
import gzip
import hashlib
import json
from pathlib import Path

HEAD='fe369c7462e4e4f290727b2d03b696d28ef5454b'
ARCHIVE_SHA='2a278acf1aac84f5431cc9879f05f247a1f9b21b86d5a590a47d2c30c0a9c32a'
WEEK_SHA='e25d4a8c5dc0d23adc8d2801f370150121acfbf04178926e229c637236fa64fb'
RETAINED='2026-11-05T23:42:41Z'

def sha(b):return hashlib.sha256(b).hexdigest()
def clock(s):return datetime.datetime.fromisoformat(s.replace('Z','+00:00'))

def main():
    ap=argparse.ArgumentParser()
    for name in ('archive','served-week','labels','out','receipt'):
        ap.add_argument('--'+name,type=Path,required=True)
    a=ap.parse_args();raw=a.archive.read_bytes();week=a.served_week.read_bytes()
    assert sha(raw)==ARCHIVE_SHA and sha(week)==WEEK_SHA
    archive=json.loads(raw);served=json.loads(week);labels=json.loads(a.labels.read_bytes())
    lm={(str(r['source_game_id']),str(r['source_player_id'])):r for r in labels if(r['season'],r['week'])==(2026,9)}
    assert len(lm)==30
    gm={str(g['id']):g for g in archive['games']}
    original={(str(r['game_id']),str(r['id']),p['key']):p for r in served['players']if r['pos']=='QB'
              for p in r['props']if p['key']in('pass_cmp','pass_att')and p.get('line_from')in('dk','sleeper')}
    rows=[];parity=0
    for pi,player in enumerate(archive['players']):
        if player['pos']!='QB':continue
        for qi,prop in enumerate(player['props']):
            if prop['key']not in('pass_cmp','pass_att')or prop.get('line_from')not in('dk','sleeper'):continue
            event,pid=str(player['game_id']),str(player['id']);key=(event,pid);label=lm[key];game=gm[event]
            assert label['finality']=='STATUS_FINAL' and label['label_support']=='EXPLICIT_NFLVERSE_PASSING_INTERCEPTIONS_AND_ESPN_PASSING_INTERCEPTIONS_AGREE'
            assert label['team']==player['team'] and label['opponent']==player['opp']
            assert player['team']in(game['home'],game['away']) and not player['late']
            counterpart=original[event,pid,prop['key']]
            assert all(counterpart.get(k)==prop.get(k)for k in('line','proj','adj','lean','line_from'))
            kickoff=clock(game['kickoff']);deadline=kickoff-datetime.timedelta(minutes=90)
            assert clock(RETAINED)<=deadline
            target=prop['key'];actual=label['official_completions'if target=='pass_cmp'else'official_attempts']
            assert isinstance(actual,int)and not isinstance(actual,bool)and actual>=0
            rows.append(dict(season=2026,week=9,game_id=label['game_id'],player_id=label['player_id'],
                source_game_id=event,source_player_id=pid,position='QB',team=player['team'],opponent=player['opp'],
                target=target,line=prop['line'],line_from=prop['line_from'],prediction=prop.get('adj'),raw_prediction=prop.get('proj'),
                original_side=prop.get('lean'),side=prop.get('lean'),actual=actual,label_state='SUPPORTED',
                participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL',source_head=HEAD,source_server_clock=RETAINED,
                source_server_run_id=42131457850,source_server_run_repository='NickNicky19/NFL-forecasting-V2',
                source_server_run_head='38d2a4db75b4a8413183929776d1d3b22b802627',
                retention_proof='SERVER_BOUND_B_HASH_COMMITMENT_TO_EXACT_ORIGINAL_SITE_BYTES;NOT_PRODUCER_RUN_HEAD_IDENTITY',
                kickoff=kickoff.isoformat(),source_T90_deadline=deadline.isoformat(),source_row_index=len(rows),
                source_player_index=pi,source_prop_index=qi,panel='W9_PRE_T90_COMMITTED_PROVIDER_LABELLED_THRESHOLDS',
                strategy='original',method_key=None,model_output_source='RETAINED_WEBSITE_ADJUSTED_RAW',
                original_bookmaker_quote_clock='UNVERIFIED',label_version='CURRENT_VINTAGE_FINAL_CMP_ATT_MATCHED_TO_QUALIFIED_144_LABEL_MAP'))
            parity+=1
    assert len(rows)==60 and len({(r['game_id'],r['player_id'],r['target'])for r in rows})==60
    assert len({r['game_id']for r in rows})==15
    identity=lambda r:tuple(str(r[k])if k=='line'else r.get(k)for k in('game_id','player_id','target','line','line_from','source_head','source_server_clock'))
    compressed=gzip.compress((json.dumps({'schema':'B_INFORMATION_FIRST_W9_SOURCE_BOUND_QB_OFFERS_v1','rows':rows},sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.out.exists():assert a.out.read_bytes()==compressed
    else:a.out.write_bytes(compressed)
    receipt=dict(id='B-INFORMATION-FIRST-W9-OFFER-PANEL-v1',checked_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        original_site_source_head=HEAD,archive_sha256=ARCHIVE_SHA,archive_bytes=len(raw),predeadline_served_week_sha256=WEEK_SHA,
        predeadline_served_week_bytes=len(week),exact_archive_live_prop_parity=parity,rows=len(rows),
        category_counts=dict(collections.Counter(r['target']for r in rows)),games=15,unique_player_games=30,
        line_sources=dict(collections.Counter(r['line_from']for r in rows)),source_observed_before_all_T90=True,
        source_retained_by_UTC=RETAINED,first_T90_UTC=min(r['source_T90_deadline']for r in rows),
        proof='Prior B38d2a4 hash commitment contains exactweekSHA and ownerfe369head; authenticated GitHubBpushrun42131457850 created23:42:41before23:45. OldBservedwitness23:39:58and ownercompletion23:32:58 retained.',
        proof_limit='This authenticates prior commitment/retention of exact bytes, not original upstream quote timestamp or historical football-feature vintages. New models are retrospective diagnostics, not new originally issued picks.',
        identity_join='Exact previous qualified final144map Sleeper/ESPN event→GSIS/canonical NFL game and historicalteam/opponent; all30 earlyoffered players remain, no final-starter filtering.',
        final_label_map_sha256=sha(a.labels.read_bytes()),private_normalized_sha256=sha(compressed),private_normalized_bytes=len(compressed),
        offer_identity_sha256=sha(json.dumps(sorted(identity(r)for r in rows),separators=(',',':')).encode()),
        source_adjusted_points=60,source_raw_points=60,new_model_fits=0,new_predictions=0,new_grades=0,raw_rows_public=False,
        source_panel='One fixed pre-first-gameT90 W9snapshot, unlike earlier per-game rolling source assignments. Keep row source contracts/age explicit; do not silently claim identical refresh schedule or concatenate overlappingAboards.',
        W1_W4='Bnativeoffered-line cells still unavailable; Aannual88CMPprivateowner-local route separate; no borrowing its coverage for newrecipe.',
        prior_season_offers='Not obtained by this source task; numeric history does not fill actual-line gaps.')
    a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({k:receipt[k]for k in('rows','category_counts','games','source_observed_before_all_T90','private_normalized_sha256')}))

if __name__=='__main__':main()
