"""Independent pre-fit input/feature checks only; no model fit or inference."""
import csv
import gzip
import hashlib
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from nfl_v2 import hgb_control as hgb
from nfl_v2 import empirical_benchmark as empirical


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    b=path.read_bytes();return json.loads(gzip.decompress(b)if path.suffix=='.gz'else b)
def finite(x):
    try:v=float(x)
    except(TypeError,ValueError):return None
    return v if math.isfinite(v)else None
def valid_count(v):return v is not None and v>=0 and v.is_integer()
def manual_event(raw):
    n={k:finite(raw.get(k))for k in set(empirical.PHYSICAL_COUNTS)|set(empirical.PHYSICAL_YARDS)|{'rushing_tds','receiving_tds'}}
    played=any(valid_count(n[k])and n[k]>0 for k in empirical.PHYSICAL_COUNTS)or any(n[k]is not None and n[k]!=0 for k in empirical.PHYSICAL_YARDS)
    a,b=n['rushing_tds'],n['receiving_tds']
    target=None if not played or any(v is not None and not valid_count(v)for v in(a,b))else 1. if any(v is not None and v>0 for v in(a,b))else 0. if a==0 and b==0 else None
    return played,target
def manual_features(rows,pid,position,cutoff):
    selected=sorted([r for r in rows if r['player_id']==pid and r['available']<cutoff],key=lambda r:(r['kickoff'],r['game_id']))[-8:]
    result=[]
    for n in(3,8):
        values=[r['values']['anytime_td']for r in selected[-n:]if r['values']['anytime_td']is not None]
        result.extend([sum(values)/len(values)if values else math.nan,float(len(values))])
    for n in range(1,5):
        row=selected[-n]if len(selected)>=n else None;value=row['values']['anytime_td']if row else None
        result.extend([value if value is not None else math.nan,(cutoff-row['kickoff'])/86400 if row else math.nan,float(value is None)])
    result.extend(float(position==p)for p in('QB','RB','WR','TE'))
    return result,selected
def compare(a,b):
    assert len(a)==len(b)==20
    for x,y in zip(a,b):assert(math.isnan(x)and math.isnan(y))or abs(x-y)<1e-12,(x,y)


def main():
    out=Path(__file__).resolve().parent;b=ROOT/'reports/category-decision-release-01/B/anytime-current-v1'
    p=read(b/'FROZEN_PROTOCOL.json');rows=read(b/'EVENT_HISTORY.json.gz');queries=read(b/'CURRENT_QUERIES.json')['basic'];cutoff=p['fit_cutoff']
    assert sha(b/'EVENT_HISTORY.json.gz')==p['inputs_sha256']and sha(b/'CURRENT_QUERIES.json')==p['queries_sha256']
    for name,h in p['code_sha256'].items():assert sha(ROOT/name)==h,name
    assert p['feature_order']==list(hgb.FEATURES)and len(hgb.FEATURES)==20 and p['params']==hgb.PARAMS
    old=read(ROOT/'reports/continuation-20261029/hgb-history-v1/FROZEN_PROTOCOL.json')
    assert old['params']==p['params']and old['feature_columns']==p['feature_order']
    assert hgb.allowed_roles(old,'anytime_td')=={'QB','RB','WR','TE'}
    assert len({(r['game_id'],r['player_id'])for r in rows})==len(rows)
    assert all(r['available']==r['kickoff']+604800 and isinstance(r['available'],(int,float))and math.isfinite(r['available'])for r in rows)
    train=[r for r in rows if r['available']<cutoff and r['values']['anytime_td']is not None]
    assert not any(r['season']==2026 and r['week']>=9 for r in train)
    assert set(r['values']['anytime_td']for r in train)=={0.,1.}
    schedule_path=ROOT.parent/'v2-source-cache/games.csv';assert sha(schedule_path)==p['schedule']['sha256']
    games={}
    for raw in csv.DictReader(schedule_path.open()):
        if raw['game_type']=='REG'and raw['season']in{str(y)for y in range(2022,2027)}and raw['gametime']:
            games[raw['game_id']]=dict(season=int(raw['season']),week=int(raw['week']),kickoff=datetime.fromisoformat(raw['gameday']+'T'+raw['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp(),home=raw['home_team'],away=raw['away_team'],native=str(raw.get('espn','')).removesuffix('.0'))
    legacy=hgb.schedules(schedule_path)
    assert all(all(games[k][f]==v[f]for f in('season','week','kickoff','home','away'))for k,v in legacy.items())
    target=games['2026_10_WAS_NYG'];assert target['kickoff']==1794532500. and target['home']=='NYG'and target['away']=='WAS'and target['native']=='401873052'
    assert all(q['game_id']=='2026_10_WAS_NYG'and q['kickoff']==target['kickoff']and q['native_event_id']==target['native']and q['season']==2026 and q['week']==10 and q['team']in('WAS','NYG')and q['opponent']in('WAS','NYG')and q['team']!=q['opponent']and q['position']in('RB','WR','TE')and q['cutoff']==cutoff and q['eligible']==(q['provider_status']=='ACT')for q in queries)
    assert len({q['player_id']for q in queries})==len(queries)
    history=hgb.FeatureHistory(rows)
    special=next(r for r in rows if r['season']==2022 and r['played']and r['values']['anytime_td']==0 and r['physical_proof']['field'].startswith('def_'))
    missing=next(r for r in rows if r['season']==2022 and r['values']['anytime_td']is None)
    ordinary=next(r for r in rows if r['season']==2026 and r['values']['anytime_td']==1)
    samples=[('KNOWN_ZERO_SPECIAL_TEAM_PROOF',special),('UNPROVED_PARTICIPATION_UNKNOWN_NOT_ZERO',missing),('ORDINARY_POSITIVE_EVENT',ordinary)]
    raw_expected={(r['game_id'],r['player_id']):(name,r)for name,r in samples};raw_matches=[]
    for season in(2022,2026):
        path=ROOT.parent/'v2-source-cache'/('stats_player_week_'+str(season)+'.csv')if season<2026 else ROOT.parent/'research-evidence/player-context-matchup-01/weekly-v2/stats_player_week_2026.csv'
        wanted=next(r for r in p['source_ids']if r['source_id']==path.name);assert sha(path)==wanted['sha256']
        for raw in csv.DictReader(path.open()):
            key=raw['game_id'],raw['player_id']
            if key not in raw_expected:continue
            name,r=raw_expected[key];played,event=manual_event(raw);assert played==r['played']and event==r['values']['anytime_td']
            raw_matches.append(dict(case=name,game_id=r['game_id'],player_id=r['player_id'],role=r['position'],played=played,event=event,rushing_tds=r['rushing_tds'],receiving_tds=r['receiving_tds'],source_id=path.name,source_sha256=wanted['sha256']))
    assert len(raw_matches)==3
    feature_checks=[]
    for name,r in samples:
        expected,selected=manual_features(rows,r['player_id'],r['position'],r['kickoff']);actual,latest=history.get(r['player_id'],r['position'],'anytime_td',r['kickoff']);compare(expected,actual)
        feature_checks.append(dict(case=name,game_id=r['game_id'],player_id=r['player_id'],selected_prior_slots=len(selected),known_last3=actual[1],known_last8=actual[3],latest_available=latest,target_cutoff=r['kickoff']))
    no_own=[]
    for q in queries:
        if not q['eligible']:continue
        expected,selected=manual_features(rows,q['player_id'],q['position'],cutoff)
        if selected:continue
        actual,latest=history.get(q['player_id'],q['position'],'anytime_td',cutoff);compare(expected,actual);assert latest is None and actual[1]==actual[3]==0 and sum(actual[16:])==1
        no_own.append(dict(player_id=q['player_id'],role=q['position'],known_last3=actual[1],known_last8=actual[3],lag_missing=[actual[i]for i in(6,9,12,15)]))
    assert len(no_own)==2
    fixture=[dict(player_id='SYNTHETIC',game_id=str(i),kickoff=float(i*604800),available=float((i+1)*604800),values={'anytime_td':v})for i,v in enumerate([0.,None,1.])]
    at=1814400.;actual,_=hgb.FeatureHistory(fixture).get('SYNTHETIC','RB','anytime_td',at);expected,selected=manual_features(fixture,'SYNTHETIC','RB',at);compare(expected,actual);assert len(selected)==2 and actual[:4]==[0.,1.,0.,1.]and math.isnan(actual[4])and actual[6]==1
    future=dict(player_id='SYNTHETIC',game_id='FUTURE',kickoff=at+1,available=at+604801,values={'anytime_td':1.});after,_=hgb.FeatureHistory(fixture+[future]).get('SYNTHETIC','RB','anytime_td',at);compare(actual,after)
    recorded=datetime.fromisoformat(p['registered_UTC']).timestamp();assert cutoff<=recorded<datetime.now(timezone.utc).timestamp()and cutoff<target['kickoff']
    result=dict(id='B-ANYTIME-CURRENT-PREFIT-INDEPENDENT-REVIEW-v1',reviewed_UTC=datetime.now(timezone.utc).isoformat(),state='PASS_IN_CHECKED_PREFIT_SCOPE;NOT_A_CAPTURE_OR_PRIMARY_ADMISSION',protocol_sha256=sha(b/'FROZEN_PROTOCOL.json'),code_sha256=p['code_sha256'],input_sha256=p['inputs_sha256'],queries_sha256=p['queries_sha256'],source_scope='ExistinglicensedBbasic-statderivative and Ccurrent-knownroster; no sourceacquisition or full2394-row rawparity repeated',feature_count=20,params_exact_original=True,training_roles=['QB','RB','WR','TE'],primary_query_roles=['RB','WR','TE'],history_slots=len(rows),known_eligible_training_rows=len(train),training_by_role=dict(Counter(r['position']for r in train)),training_classes={str(k):v for k,v in Counter(r['values']['anytime_td']for r in train).items()},training2026weeks=sorted({r['week']for r in train if r['season']==2026}),W9_eligible_labels=0,unknown_slots_retained=sum(r['values']['anytime_td']is None for r in rows),source_samples=raw_matches,independent_historical_feature_cases=feature_checks,no_own_current_cases=no_own,synthetic_boundary='PASS_unknownconsumesslot/strictavailableequalityexcluded/futurerowinvariant;no syntheticfit',all_current_basic=len(queries),ACT_forecast_candidates=sum(q['eligible']for q in queries),query_role_counts=dict(Counter(q['position']for q in queries if q['eligible'])),schedule=dict(source_sha256=p['schedule']['sha256'],old_game_clocks_unchanged=len(legacy),target=target,game_id='2026_10_WAS_NYG'),feature_freeze_to_registration_seconds=recorded-cutoff,registration_interpretation='Actualsourcefreeze occurs atpreparestart;registrationwrittenafterderivation but beforeanyfit;not a backdatedforecast or authenticatedhistoricalpublication',source_expiry_UTC=datetime.fromtimestamp(p['current_roster']['source_expires_at'],timezone.utc).isoformat(),model_export_review='StaticnumericHGBbaseline-logit plusone-treeperstage leafvalues/finite-or-infinite numeric thresholds/missingrouting/class1orientation; stablelogistic; ownnewmodelonly, no pickleload. Parenttoy4test receipt reused; no model tested here.',nonblocking_limits=['Currentrunner refuses minimum-support/single-class failure ratherthan executing old empiricalfallback; boundcurrenttrain25830/bothclasses makes this branch unreachable for this frozeninput. No general primary-runtime parity claim.','Target schedule literal matches boundfullschedule; freshnative/status and realissue/sourceexpiry/persistence gate stillrequired separately.','RAW probabilities are not calibration/per-pickconfidence/EV or offeredNO/Under selections.','CurrentACTconditionalroster scope is distinct from authenticatedpregamestarter/health and retrospectiveparticipant scoring.'],pending=['Immutablecode/input/protocolGitHubreadbackbeforetheonecurrentfit','NativeversustrustedJSONrestoration onactualnewmodel afterfit','Freshnative event and unexpiredsource atactualissue/persistence','Consumeradmission and anyscientificprimaryqualification remainseparate'],new_fits=0,new_model_inference=0,new_forecasts=0,new_grades=0,new_NFL_observations=0)
    dest=out/'PREFIT_INDEPENDENT_REVIEW_V1.json';assert not dest.exists();dest.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(dict(state=result['state'],history_slots=len(rows),training_rows=len(train),samples=len(raw_matches),current_no_own=len(no_own),old_clocks=len(legacy),ACT=sum(q['eligible']for q in queries))))


if __name__=='__main__':main()
