"""Build retained-history profile products; never fit or score a model."""
from pathlib import Path
import argparse
import collections
import datetime
import gzip
import hashlib
import json
import resource
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT))
from nfl_v2.player_context_matchup import load_inputs
from nfl_v2.qb_context_profiles import QBProfileAdapter,HISTORICAL_UNIVERSE,VERSION


def encode(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--depth-input')
    args=parser.parse_args()
    base=Path(__file__).resolve().parent
    if (base/'PROFILE_INDEX_V1.json').exists():
        raise SystemExit('Frozen output exists; choose a versioned script/output, do not overwrite.')
    started=time.monotonic();cpu=time.process_time()
    source=ROOT/'reports/player-context-matchup-01/B/source-fields-v3/DERIVED_QB_GAME_INPUTS.json.gz'
    rows=load_inputs(source)
    selected=json.loads((ROOT/'reports/player-context-matchup-01/B/qb-wave-v1/SELECTED_EARLIER_CONFIG.json').read_text())
    charting=None
    if args.depth_input:
        p=ROOT/args.depth_input;data=json.loads(gzip.decompress(p.read_bytes()))
        charting={(r['game_id'],r['player_id']):r for r in data}
        if len(charting)!=len(data):raise ValueError('Repeated depth annotation identity')
    adapter=QBProfileAdapter(rows,window=selected['window'],strength=selected['strength'],depth_annotations=charting)
    queries=[{k:r[k] for k in ('game_id','player_id','season','week','team','opponent','position','kickoff')}
             for r in rows if r['season']in(2025,2026)]
    queries=sorted(queries,key=lambda q:(q['season'],q['week'],q['game_id'],q['player_id']))
    assert len(queries)==941
    profiles=adapter.build_many(queries,universe=HISTORICAL_UNIVERSE)
    grouped=collections.defaultdict(list)
    for profile in profiles:
        identity=profile['identity'];grouped[identity['season'],identity['week']].append(profile)
    artifacts=[];index=[]
    for (season,week),group in sorted(grouped.items()):
        name=f'QB_PROFILES_{season}_W{week:02d}.json.gz';path=base/name
        raw=encode(group);body=gzip.compress(raw,mtime=0);path.write_bytes(body)
        artifacts.append(dict(path=str(path.relative_to(ROOT)),sha256=hashlib.sha256(body).hexdigest(),
            bytes=len(body),uncompressed_sha256=hashlib.sha256(raw).hexdigest(),profiles=len(group),season=season,week=week))
        for profile in group:
            index.append(dict(profile_id=profile['profile_id'],status=profile['status'],identity=profile['identity'],
                artifact=name,source_tier=profile['source_tier'],query_universe=profile['query_universe'],
                fallback=profile.get('fallback'),own_eligible_games=profile.get('history',{}).get('own',{}).get('eligible_games')))
    # Example membership rules were registered before generation. They inspect
    # only prior-support state, never target outcomes or comparative scores.
    ordinary=next(p for p in profiles if p.get('history',{}).get('own',{}).get('eligible_games',0)>=4)
    sparse=next(p for p in profiles if p.get('history',{}).get('own',{}).get('eligible_games')==0)
    zero=next(p for p in profiles if any(c['completion_per_attempt']['state']=='KNOWN_ZERO' for c in p['contexts']))
    oq=next(q for q in queries if q['game_id']==ordinary['identity']['game_id']and q['player_id']==ordinary['identity']['player_id'])
    missing_chart=QBProfileAdapter(rows,window=selected['window'],strength=selected['strength']).build(oq,universe=HISTORICAL_UNIVERSE)
    unavailable_current=adapter.build(oq,universe='SUPPLIED_QUALIFIED_PREGAME_QUERY_UNIVERSE')
    examples={'ordinary':ordinary,'sparse_or_unseen_history':sparse,'known_zero_context':zero,
              'missing_depth_source':missing_chart,'unavailable_current_membership':unavailable_current}
    (base/'DETERMINISTIC_EXAMPLES_V1.json').write_bytes(encode(examples))
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    index_doc=dict(schema_version='B-QB-PROFILE-INDEX-v1',profile_version=VERSION,at_utc=now,
        profile_count=len(profiles),universe=HISTORICAL_UNIVERSE,
        eligibility_limitation='All retained941 official QB-stat query identities, including sparse history. Not authenticated historical pregame rosters; current queries must be explicitly supplied.',
        source=dict(path=str(source.relative_to(ROOT)),sha256=hashlib.sha256(source.read_bytes()).hexdigest()),
        selected_config=dict(path='reports/player-context-matchup-01/B/qb-wave-v1/SELECTED_EARLIER_CONFIG.json',sha256=hashlib.sha256((ROOT/'reports/player-context-matchup-01/B/qb-wave-v1/SELECTED_EARLIER_CONFIG.json').read_bytes()).hexdigest()),
        depth_source=None if not args.depth_input else dict(path=args.depth_input,sha256=hashlib.sha256((ROOT/args.depth_input).read_bytes()).hexdigest()),
        artifacts=artifacts,profiles=index)
    (base/'PROFILE_INDEX_V1.json').write_bytes(encode(index_doc))
    counts=collections.Counter(p['status']for p in profiles)
    fallback=collections.Counter(p.get('fallback','unavailable')for p in profiles)
    resources=dict(wall_seconds=time.monotonic()-started,cpu_seconds=time.process_time()-cpu,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        profiles=len(profiles),new_fits=0,new_scores=0,new_forecasts=0,new_NFL_observations=0)
    receipt=dict(schema_version='B-QB-PROFILE-EXECUTION-v1',at_utc=now,status='PROFILE_PRODUCTS_BUILT_NOT_FORECAST_OR_CAPTURE',
        profiles_by_state=dict(counts),fallback_profiles=dict(fallback),
        seasons={str(s):sum(q['season']==s for q in queries)for s in(2025,2026)},
        weeks=[dict(season=s,week=w,profiles=len(g))for(s,w),g in sorted(grouped.items())],
        query_records_missing_profile=0,current_pregame_queries_supplied=0,current_capture=False,
        new_tests='Two adapter chronology/known-zero/missing-evidence tests; software fixtures add no NFL evidence.',
        resources=resources,
        source_rights='nflverse/nflfastR PBP and player-stat-derived profile sections CC BY4.0; FTN Data via nflverse charting sections, if attached, CC BY-SA4.0. No private offers or raw feeds.',
        example_rules='First lexical profile with own>=4; first own0; first known-zero context; same ordinary profile without depth map; same identity lacking current membership evidence.',
        release='No profile qualifies a forecast/product; current query adapter requires separate owner source/runtime/admission and actual persistence.')
    (base/'PROFILE_EXECUTION_RECEIPT_V1.json').write_bytes(encode(receipt))
    assert resources['cpu_seconds']<=180 and resources['wall_seconds']<=240
    assert resources['peak_RSS_bytes']<=1073741824
    assert sum(p.stat().st_size for p in base.rglob('*')if p.is_file())<=16777216
    print(json.dumps(dict(status='PASS',profiles=len(profiles),states=dict(counts),resources=resources)))


if __name__=='__main__':main()
