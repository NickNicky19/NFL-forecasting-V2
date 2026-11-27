"""Read-only exact-source audit of recorded QB interception opportunities.

Private player/line/source rows remain owner-local. This program supplies labels,
not a scorer, model, source scheduler or production change. No sparse-zero fill.
"""
from __future__ import annotations

import argparse
import collections
import concurrent.futures
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path
import threading
import urllib.request


TEAMS = {'ATL':1,'BUF':2,'CHI':3,'CIN':4,'CLE':5,'DAL':6,'DEN':7,
         'DET':8,'GB':9,'TEN':10,'IND':11,'KC':12,'LV':13,'LAR':14,
         'MIA':15,'MIN':16,'NE':17,'NO':18,'NYG':19,'NYJ':20,'PHI':21,
         'ARI':22,'PIT':23,'LAC':24,'SF':25,'SEA':26,'TB':27,'WAS':28,
         'CAR':29,'JAX':30,'BAL':33,'HOU':34}
ALIASES = {'LA':'LAR','WSH':'WAS','OAK':'LV','SD':'LAC'}
ROOT_API = 'https://sports.core.api.espn.com/v2/sports/football/leagues/nfl'


def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def team(value): return ALIASES.get(str(value),str(value))
def read_csv(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path,'rt',newline='') as handle: return list(csv.DictReader(handle))


def count(value):
    if value is None or isinstance(value,bool): raise ValueError('Unreported count')
    number=float(value)
    if not math.isfinite(number) or number<0 or number!=int(number):
        raise ValueError('Invalid explicit nonnegative integer count')
    return int(number)


class SourceCache:
    def __init__(self, root, limit):
        self.root=root; self.limit=limit; self.lock=threading.Lock()
        self.bytes=sum(p.stat().st_size for p in root.glob('*.json') if not p.name.endswith('.receipt.json'))
        self.members={}

    def get(self, name, url):
        path=self.root/(name+'.json'); rp=self.root/(name+'.receipt.json')
        if path.exists():
            body=path.read_bytes()
            if rp.exists():
                receipt=json.loads(rp.read_text())
                if receipt.get('url')!=url or receipt.get('sha256')!=hashlib.sha256(body).hexdigest():
                    raise ValueError('Existing source receipt mismatch')
            else: raise ValueError('Existing unbound source bytes')
        else:
            started=now()
            with urllib.request.urlopen(url,timeout=30) as response:
                body=response.read(2*1024*1024+1)
                if len(body)>2*1024*1024: raise ValueError('Oversized source response')
                headers={k:response.headers.get(k) for k in ('Date','Last-Modified','ETag','Content-Type')}
                status=response.status
            with self.lock:
                if self.bytes+len(body)>self.limit: raise ValueError('Source budget exceeded')
                self.bytes+=len(body)
            receipt=dict(url=url,started_UTC=started,retrieved_UTC=now(),status=status,
                         bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),headers=headers)
            path.write_bytes(body); rp.write_text(json.dumps(receipt,indent=2)+'\n')
        with self.lock:
            self.members[name]=dict(bytes=len(body),sha256=hashlib.sha256(body).hexdigest())
        return json.loads(body)


def main():
    ap=argparse.ArgumentParser()
    for name in ('cohort','stats','roster','players','schedule','cache','private-output','receipt'):
        ap.add_argument('--'+name,type=Path,required=True)
    ap.add_argument('--expected-rows',type=int,default=86)
    a=ap.parse_args(); a.cache.mkdir(parents=True,exist_ok=True)
    cohort=json.loads(a.cohort.read_text())
    assert len(cohort)==len({(r['season'],r['week'],r['player_id'],r['game_id'])for r in cohort})==a.expected_rows
    roster=read_csv(a.roster); players=read_csv(a.players)
    sleeper=collections.defaultdict(set); espn=collections.defaultdict(set)
    for r in roster:
        if r.get('sleeper_id') and r.get('gsis_id'): sleeper[r['sleeper_id']].add(r['gsis_id'])
    for r in players:
        if r.get('gsis_id') and r.get('espn_id'): espn[r['gsis_id']].add(r['espn_id'])
    stats=collections.defaultdict(list)
    for r in read_csv(a.stats): stats[r['season'],r['week'],r['player_id']].append(r)
    schedule={r['espn']:r for r in read_csv(a.schedule) if r['season']=='2026'}
    bound=[]
    for original in cohort:
        ids=sleeper[original['player_id']]
        if len(ids)!=1: raise ValueError('Unresolved Sleeper/GSIS bridge')
        gsis=next(iter(ids)); eids=espn[gsis]
        if len(eids)!=1: raise ValueError('Unresolved GSIS/ESPN bridge')
        event=original['game_id']; game=schedule[event]
        if (game['season'],game['week'])!=(str(original['season']),str(original['week'])):
            raise ValueError('Event season/week mismatch')
        t=team(original['team']); opp=team(original['opponent'])
        if {t,opp}!={team(game['home_team']),team(game['away_team'])}:
            raise ValueError('Event team/opponent mismatch')
        rr=stats[str(original['season']),str(original['week']),gsis]
        if len(rr)!=1 or rr[0]['position']!='QB': raise ValueError('Weekly QB record unresolved')
        stat=rr[0]
        if (team(stat['team']),team(stat['opponent_team']))!=(t,opp):
            raise ValueError('Historical team/opponent mismatch')
        interceptions=count(stat['passing_interceptions'])
        bound.append(dict(original=original,gsis_id=gsis,espn_id=next(iter(eids)),
                          canonical_game_id=game['game_id'],team=t,opponent=opp,
                          official_weekly_pass_int=interceptions,
                          official_weekly_attempts=count(stat['attempts']),
                          official_weekly_completions=count(stat['completions'])))
    cache=SourceCache(a.cache,20*1024*1024)
    def fetch_status(event):
        url=f'{ROOT_API}/events/{event}/competitions/{event}/status?lang=en&region=us'
        payload=cache.get('STATUS_'+event,url)
        if payload.get('type',{}).get('completed') is not True or payload['type'].get('state')!='post':
            raise ValueError('Outcome not source-final')
        if f'/events/{event}/competitions/{event}/status?' not in payload.get('$ref',''):
            raise ValueError('Finality event mismatch')
        return event,payload['type']['name']
    with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:
        finality=dict(pool.map(fetch_status,sorted({r['original']['game_id']for r in bound})))
    def fetch_athlete(r):
        event=r['original']['game_id']; aid=r['espn_id']; tid=TEAMS[r['team']]
        url=f'{ROOT_API}/events/{event}/competitions/{event}/competitors/{tid}/roster/{aid}/statistics/0?lang=en&region=us'
        payload=cache.get('CORE_'+event+'_'+aid,url)
        expected=f'/events/{event}/competitions/{event}/competitors/{tid}/roster/{aid}/statistics/0?'
        if expected not in payload.get('$ref',''):raise ValueError('Game/team/athlete statistics mismatch')
        if f'/athletes/{aid}?' not in payload.get('athlete',{}).get('$ref',''):raise ValueError('Athlete reference mismatch')
        if f'/events/{event}/competitions/{event}?' not in payload.get('competition',{}).get('$ref',''):raise ValueError('Competition reference mismatch')
        categories=payload['splits']['categories']
        passing=[x for x in categories if x['name']=='passing']
        if len(passing)!=1: raise ValueError('Missing or ambiguous passing category')
        values=collections.defaultdict(list)
        for field in passing[0]['stats']: values[field['name']].append(field)
        for name in ('interceptions','passingAttempts','completions'):
            if len(values[name])!=1: raise ValueError('Missing or ambiguous explicit passing statistic')
        integer=count(values['interceptions'][0]['value'])
        description=values['interceptions'][0].get('description','')
        if description!='The number of passes thrown that were intercepted by the opposing team.':
            raise ValueError('Interception definition changed')
        attempts=count(values['passingAttempts'][0]['value']); completions=count(values['completions'][0]['value'])
        if (integer,attempts,completions)!=(r['official_weekly_pass_int'],r['official_weekly_attempts'],r['official_weekly_completions']):
            raise ValueError('NFLverse/ESPN final passing statistics conflict')
        original=r['original']; reported=original['reported_pass_int']
        if original['pass_int_field_present'] and count(reported)!=integer:
            raise ValueError('Originally reported nonmissing interception conflicts')
        return dict(season=original['season'],week=original['week'],source_player_id=original['player_id'],
                    player_id=r['gsis_id'],source_game_id=event,game_id=r['canonical_game_id'],
                    team=r['team'],opponent=r['opponent'],espn_athlete_id=aid,
                    original_field_present=original['pass_int_field_present'],original_pass_int=reported,
                    corrected_pass_int=integer,label_version='B-OFFICIAL-PASSING-INTERCEPTIONS-20261112-v1',
                    label_support='EXPLICIT_NFLVERSE_PASSING_INTERCEPTIONS_AND_ESPN_PASSING_INTERCEPTIONS_AGREE',
                    official_attempts=attempts,official_completions=completions,
                    finality=finality[event],source_clock_tier='CURRENT_VINTAGE_FINAL_OUTCOME_RECHECK_NOT_ORIGINAL_SOURCE_VINTAGE',
                    weekly_source_sha256=sha(a.stats),espn_source_sha256=cache.members['CORE_'+event+'_'+aid]['sha256'],
                    finality_source_sha256=cache.members['STATUS_'+event]['sha256'])
    with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool: corrected=list(pool.map(fetch_athlete,bound))
    a.private_output.write_text(json.dumps(corrected,indent=2)+'\n')
    missing=[r for r in corrected if not r['original_field_present']]
    observed=[r for r in corrected if r['original_field_present']]
    def counts(rows):return dict(collections.Counter(str(r['corrected_pass_int'])for r in rows))
    public=dict(state='PASS_EXACT_IDENTITY_EXPLICIT_CURRENT_FINAL_PASSING_INTERCEPTION_LABELS',at_UTC=now(),
        original_cohort_rows=len(cohort),original_cohort_sha256=sha(a.cohort),
        original_missing_count=len(missing),missing_supported_explicit_zero=sum(r['corrected_pass_int']==0 for r in missing),
        missing_supported_nonzero=sum(r['corrected_pass_int']>0 for r in missing),unknown_or_conflicting=0,
        existing_reported_count=len(observed),existing_reported_all_match=True,
        all_corrected_value_counts=counts(corrected),original_missing_value_counts=counts(missing),
        weekly=[dict(week=w,rows=len([r for r in corrected if r['week']==w]),
                     original_missing=len([r for r in missing if r['week']==w]),
                     explicit_current_zero=len([r for r in corrected if r['week']==w and r['corrected_pass_int']==0]))for w in range(5,10)],
        unique_games=len(finality),source_final_games=len(finality),
        identity_checks='Exact frozen Sleeper→GSIS→ESPN IDs; event→season/week/team/opponent; no fuzzy names, no target participation used to infer zero.',
        target_definition='Official QB interceptions thrown, full game; NFLverse passing_interceptions and ESPN passing.interceptions; defensive interceptions excluded.',
        qualified_zero='Each zero explicitly present in both named passing-stat sources. No source-field omission, participation flag, pass attempts or source-zero completeness assumption substituted for observation.',
        source_tier='Current-vintage final-stat correction. Does not prove what historical compacted Sleeper absence originally meant, original pregame forecast/line availability, venue settlement, or prediction improvement.',
        bindings=[dict(kind=kind,sha256=sha(path),bytes=path.stat().st_size)for kind,path in [('weekly_stats',a.stats),('identity_roster',a.roster),('identity_players',a.players),('schedule',a.schedule)]],
        current_weekly_source='https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv',
        espn_route_template=ROOT_API+'/events/{event}/competitions/{event}/competitors/{team}/roster/{athlete}/statistics/0?lang=en&region=us',
        espn_member_count=len(cache.members),espn_member_bytes=sum(x['bytes']for x in cache.members.values()),
        espn_source_hashes=[dict(ordinal=i+1,**value)for i,(_,value)in enumerate(sorted(cache.members.items()))],
        private_correction_map_sha256=sha(a.private_output),private_correction_map_rows=len(corrected),
        grader_calls=0,new_fits=0,new_predictions=0,new_original_selections=0,new_NFL_games=0,
        public_player_or_offer_rows=False,production_changes=0)
    a.receipt.parent.mkdir(parents=True,exist_ok=True);a.receipt.write_text(json.dumps(public,indent=2)+'\n')
    print(json.dumps({k:public[k]for k in ['state','original_cohort_rows','original_missing_count','missing_supported_explicit_zero','existing_reported_all_match','unique_games','espn_member_bytes']}))


if __name__=='__main__': main()
