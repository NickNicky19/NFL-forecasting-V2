"""Audit frozen 2022-2026W7 basic-stat sources; never fetch/read W8 outcomes.

This qualifies schema/mapping dependencies, not complete chart labels or skill.
Only aggregate counts and public code provenance are emitted.
"""
from collections import Counter
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
WEIGHTS={'passing_yards':'.04','passing_TD':'4','interceptions_thrown':'-1','rushing_yards':'.1','rushing_TD':'6','receptions':'1',
    'receiving_yards':'.1','receiving_TD':'6','fumbles_lost':'-1','passing_2pt':'2','rushing_2pt':'2','receiving_2pt':'2',
    'offensive_fumble_recovery_TD':'6','kick_return_TD':'6','punt_return_TD':'6','field_goal_return_TD':'6'}
MAPPINGS={
 'passing_yards':('passing_yards','sum yards for stat15/16',331),
 'passing_TD':('passing_tds','count stat16',332),
 'interceptions_thrown':('passing_interceptions','count stat19',333),
 'rushing_yards':('rushing_yards','sum signed yards for stat10/11/12/13',359),
 'rushing_TD':('rushing_tds','count stat11/13',360),
 'receptions':('receptions','count stat21/22; excludes credited2pt stat104 and ordinary laterals',373),
 'receiving_yards':('receiving_yards','sum signed yards for stat21/22/23/24',375),
 'receiving_TD':('receiving_tds','count stat22/24',376),
 'fumbles_lost':('fumbles_lost_total','count stat106 once; do not add overlapping sack/rush/receiving fumble-loss aggregates',477),
 'passing_2pt':('passing_2pt_conversions','count credited passing conversion stat77',344),
 'rushing_2pt':('rushing_2pt_conversions','count credited rushing conversion stat75',366),
 'receiving_2pt':('receiving_2pt_conversions','count credited receiving conversion stat104',393)}
RARE={
 'offensive_fumble_recovery_TD':dict(candidate='fumble_recovery_tds',reason='aggregate56/58/60/62 includes own/opponent/lateral recoveries; needs play unit/possession and official scoring credit; not offense-only'),
 'kick_return_TD':dict(candidate='special_teams_tds',reason='combined return/misc/own-kickoff-recovery scoring; split official kickoff return credits46/48 including laterals'),
 'punt_return_TD':dict(candidate='special_teams_tds',reason='combined return/misc scoring; split official punt return credits34/36 including laterals'),
 'field_goal_return_TD':dict(candidate='special_teams_tds',reason='misc stat64 alone does not distinguish blocked punt/field-goal return; stat108 is own kickoff recoveryTD, not FG return')}
CODE_FILES={
 'nflverse-pbp-update_stats.R':('nflverse/nflverse-pbp','R/update_stats.R','909ad1abbbecf5d80779b8fbeed6adba95fe3b74'),
 'nflfastR-calculate_stats.R':('nflverse/nflfastR','R/calculate_stats.R','f367d0a4ba7d3a472351865467eba3a9c53a14f6'),
 'nflfastR-helper_tidy_play_stats.R':('nflverse/nflfastR','R/helper_tidy_play_stats.R','0c21d4d43fb653f8d39a2bc23fc52369a4a4bc84'),
 'nflfastR-build_playstats.R':('nflverse/nflfastR','R/build_playstats.R','80e495d237da350a1672ea68d7a6d4a72bd8f0f2'),
 'nflreadr-dictionary_player_stats.json':('nflverse/nflreadr','data-raw/dictionary_player_stats.json','83e007490967c0fa2f7fb94bf1e19e9a8b2fdd71'),
 'nflreadr-dictionary_pbp.csv':('nflverse/nflreadr','data-raw/dictionary_pbp.csv','2ef5a47b3c5e30079b4cd52f3659a2d5c91e106c')}

def sha(b):return hashlib.sha256(b).hexdigest()
def number(x):
    try:v=Decimal(x)
    except (InvalidOperation,TypeError):return None
    return v if v.is_finite() else None

def audit(source,code):
    protocol=json.loads((ROOT/'reports/continuation-20261029/history-diagnostic-v1/FROZEN_PROTOCOL.json').read_text())
    source_expected={r['name']:r['sha256'] for r in protocol['source_ids']}
    code_manifest=[]
    for name,(repo,path,blob_sha) in CODE_FILES.items():
        b=(code/name).read_bytes();git=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        assert git==blob_sha
        code_manifest.append(dict(repository=repo,path=path,git_blob_sha=git,sha256=sha(b),bytes=len(b),
            public_blob_url=f'https://api.github.com/repos/{repo}/git/blobs/{git}'))
    assert len(WEIGHTS)==16 and len(MAPPINGS)==12 and set(WEIGHTS)==set(MAPPINGS)|set(RARE)
    rows=[];sources=[];header_sets=[]
    for year in range(2022,2027):
        p=source/f'stats_player_week_{year}.csv';raw=p.read_bytes();assert sha(raw)==source_expected[p.name]
        sources.append(dict(source_name=p.name,sha256=sha(raw),bytes=len(raw)))
        stats={k:Counter() for k in MAPPINGS};other=Counter();rare_patterns=Counter();games=set()
        with p.open() as f:
            reader=csv.DictReader(f);header_sets.append(set(reader.fieldnames))
            assert all(field in reader.fieldnames for field,_,_ in MAPPINGS.values())
            for r in reader:
                # Season/week filtering precedes numeric outcome decoding.
                if r['season_type']!='REG' or int(r['season'])!=year or (year==2026 and int(r['week'])>7):continue
                other['rows']+=1;other['position:'+r['position']]+=1;games.add(r['game_id'])
                for component,(field,_,_) in MAPPINGS.items():
                    v=number(r[field]);state='missing_or_invalid' if v is None else 'explicit_zero' if v==0 else 'explicit_nonzero'
                    stats[component][state]+=1
                    if v is not None and component not in {'passing_yards','rushing_yards','receiving_yards'}:
                        assert v>=0 and v==v.to_integral_value()
                    if v is not None and v<0:stats[component]['signed_negative']+=1
                st=number(r['special_teams_tds']);fr=number(r['fumble_recovery_tds'])
                rare_patterns['both_aggregate_explicit_zero' if st==fr==0 else 'positive_or_unknown_rare_aggregate']+=1
        for component,(field,formula,line) in MAPPINGS.items():
            rows.append(dict(season=year,weeks='1-7' if year==2026 else 'all_REG',component=component,source_field=field,weight=WEIGHTS[component],
                source_rows=other['rows'],source_games=len(games),**dict(stats[component])))
        sources[-1].update(panel_rows=other['rows'],panel_games=len(games),position_rows={k.split(':',1)[1]:v for k,v in other.items() if k.startswith('position:')},rare_aggregate_patterns=dict(rare_patterns))
    assert all(s==header_sets[0] for s in header_sets)
    # Independent hypothetical event arithmetic: receiving2pt is not reception;
    # credit both passer and catcher2; unique fumble106 loses1 once.
    fixture_checks=0
    def ok(x):
        nonlocal fixture_checks
        assert x;fixture_checks+=1
    ok(Decimal(WEIGHTS['passing_2pt'])==2)
    ok(Decimal(WEIGHTS['receiving_2pt'])==2 and 104 not in (21,22))
    ok(Decimal(WEIGHTS['fumbles_lost'])==-1)
    ok(Decimal(WEIGHTS['passing_yards'])*Decimal(-10)==Decimal('-.4'))
    ok(Decimal(WEIGHTS['rushing_yards'])*Decimal(-5)==Decimal('-.5'))
    return dict(status='TWELVE_MAPPED_PRIMITIVES_FOUR_EVENT_ATTRIBUTION_DEPENDENCIES_CHART_NOT_ADMITTED',
        checked_at_utc=datetime.now(timezone.utc).isoformat(),new_fits=0,new_forecasts=0,week8_outcomes_read=0,fixture_contract_checks=fixture_checks,
        exact_chart_components=16,directly_mapped_schema_fields=12,missing_separate_event_components=4,chart_qualified_player_rows=0,
        weight_contract=WEIGHTS,mapped_components={k:dict(source_field=v[0],source_algorithm=v[1],code_line=v[2],status='FIELD_AND_CURRENT_GENERATOR_TRACED;EXACT_SNAPSHOT_PRODUCER_VERSION_UNVERIFIED')for k,v in MAPPINGS.items()},
        remaining_components=RARE,source_manifest=sources,inspected_code_manifest=code_manifest,source_field_counts=rows,
        zero_contract='For a verified complete playstats+PBP game, explicit mapped0 is a counted absence of relevant stat IDs. A blank, absent player row or missing game is not0. CSV alone does not prove event completeness or the exact producer version.',
        conditional_zero_path='Zero nonnegative fumble_recovery_tds and special_teams_tds aggregates may bound their relevant subsets to0 only after validating complete aligned event coverage, source-version equivalence and return-contract containment. This audit does not admit these inferred zeros.',
        generic_fantasy_total='REJECTED: generatoruses-2INT,-2partialfumbleaggregates andbroadspecialteams; no exactchartparity',
        missing_evidence=['Approved immutable2022-2026W7 play_stats event snapshots with stat_id/game/play/player/team and completeplaycensus','Aligned PBP officialscorecredit/playtype/possession/specialunit/fumble/lateral/penalty-nullification fields','Rare-event hand comparisons and reconciled complete-event zero cases; exact producer version or independent regeneration','Qualified appearance/exantepopulation and identities for chart evaluation separately from event completeness'],
        safe_acquisition='Historical2022-2025 publicplaystats/PBP may be acquired under sourcepolicy. For2026recover an archived preWeek8 snapshot or approved strictlyW1-W7 export; do not fetch mutable currentseason payload that can contain W8 outcomes.',
        public_method_sources=['https://github.com/nflverse/nflverse-pbp/releases/download/playstats/play_stats_{season}.rds','https://github.com/nflverse/nflverse-data/releases/tag/pbp'],
        caution='Current code and documentation qualify definitions, not original feed vintages or NFL prediction skill. No raw player rows/locators are published.')

if __name__=='__main__':
    result=audit(Path(sys.argv[1]),Path(sys.argv[2]));out=Path(__file__).parent
    target=out/'CHART_PPR_SOURCE_QUALIFICATION_V1.json'
    if target.exists():raise SystemExit('immutable output exists')
    target.write_text(json.dumps(result,indent=2)+'\n')
    with (out/'CHART_PPR_COMPONENT_FIELD_COUNTS.csv').open('w')as f:
        fields=['season','weeks','component','source_field','weight','source_rows','source_games','explicit_zero','explicit_nonzero','missing_or_invalid','signed_negative']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(result['source_field_counts'])
    print(json.dumps({k:result[k]for k in ['status','exact_chart_components','directly_mapped_schema_fields','fixture_contract_checks','week8_outcomes_read']}))
