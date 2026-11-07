"""Grade newly authenticated saved versions; no forecast model execution."""
from __future__ import annotations
import argparse,collections,gzip,hashlib,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import grade_saved_week8 as core,grade_week8_captured_library as library
from nfl_v2 import full_provider_prop_replay as shared


def run(private,public):
    started=time.monotonic();out=public/'additional-saved-versions-v1';out.mkdir(exist_ok=False)
    labels=core.Labels(private);census=core.read(public/'original-v1/SAVED_LIST_VERSION_CENSUS.json')
    primary=census['primary'];head=primary['source_head'];boardpath=private/f'source-metadata/board-{head}.json';board=core.read(boardpath)
    proof=core.read(public/'independent/ADAPTIVE_ORIGINAL_PUBLICATION_CLOCK_REVIEW_V1.json')
    paths=sorted((private/'source-metadata/adaptive-verified').glob('*.json'))
    core.save(out/'FROZEN_SCOPE_V1.json',dict(at_utc=core.now(),state='REGISTERED_BEFORE_ADDITIONAL_VERSION_LOSSES',
        exposure='Week8 original and library point losses already exposed; descriptive saved-version extension, not fresh holdout.',
        sources=[dict(sha256=core.sha(p),bytes=p.stat().st_size)for p in paths],adaptive_publication_review_sha256=core.sha(public/'independent/ADAPTIVE_ORIGINAL_PUBLICATION_CLOCK_REVIEW_V1.json'),
        same_snapshot_board_sha256=core.sha(boardpath),primary_saved_top_list=primary['panel'],
        selection_rule='Original saved lean; primary top-list exact identities and sides. P1 uses unrounded retained adaptive point against later retained T90 threshold; not original issue or same-information learner comparison.',
        horizons='Earlier adaptive source_cutoff_utc is scheduled deadline, not authenticated feature freshness. Exact job-bound source bytes establish early pregame retention.',new_fits=0,new_forecasts=0,new_inference=0))
    # Fair top/all comparison: the exact board retained with the earliest list,
    # not the primary rolling T90 board used elsewhere.
    original=[]
    for player in board['players']:
        for q in player['props']:
            if q['key']not in core.ORDINARY or not core.finite(q.get('line')):continue
            original.append(core.base_row(labels,game=player['game_id'],player=player['id'],target=q['key'],line=q['line'],point=q.get('adj'),raw=q.get('proj'),side=q.get('lean'),index=len(original),position=player.get('pos'),
                panel='ORIGINAL_EARLIEST_TOP_SNAPSHOT_ALL_LEANS',line_from=q.get('line_from'),source_head=head,source_server_clock=primary['server_retained_by'],decision_time=board.get('saved_at'),fallback='NOT_RETAINED'))
    grades=shared.grade(original,strategies=('original',));scores=core.aggregate(grades,panel='ORIGINAL_EARLIEST_TOP_SNAPSHOT_ALL_LEANS',method='WEBSITE_ORIGINAL_LEANS_EARLIEST_TOP_SOURCE',track='A_ORIGINAL',pool=grades)
    # Saved list already graded in original-v1; copying its grade rows is not a
    # second grading pass or a new independent weekly selection record.
    prior=json.loads(gzip.decompress((private/'ORIGINAL_AND_TOP_GRADED_ROWS_V1.json.gz').read_bytes()))['rows']
    top=[r for r in prior if r['panel']==primary['panel']]
    assert len(top)==primary['rows']
    topkeys={(r['game_id'],r['player_id'],r['target'],str(r['line']),r['selected_side'])for r in top}
    matched=[r for r in grades if(r['game_id'],r['player_id'],r['target'],str(r['line']),r['selected_side'])in topkeys]
    assert len(matched)==len(top)
    assert {(r['game_id'],r['player_id'],r['target'],r['threshold_state'])for r in matched}=={(r['game_id'],r['player_id'],r['target'],r['threshold_state'])for r in top}
    # Authentic two early adaptive captures, retained separately from 3907.
    provider=[r for r in json.loads(gzip.decompress((private/'ORIGINAL_JOINED_ROWS_V1.json.gz').read_bytes()))['rows']if r['panel']=='ORIGINAL_PROVIDER_T90']
    offers={library.key(r):r for r in provider};numeric=[];replay=[];numeric_rows=[];spec=[]
    for path in paths:
        obj=core.read(path);capture='WEBSITE_ADAPTIVE_ORIGINAL_'+core.sha(path)[:8];grouped=collections.defaultdict(list)
        for i,raw in enumerate(obj['rows']):
            row=library.normalize(dict(raw,actual=None),capture=capture,schema=obj['schema_version'],persisted=raw['persistence_completed_at'],labels=labels,index=i,source_sha=core.sha(path),owner='P2_SELECTED:'+raw['procedure_version'])
            assert row['pregame_retention_eligible'] and row['T90_eligible'];grouped[library.group(row)].append(row);numeric_rows.append(row)
        for g,rr in sorted(grouped.items()):
            numeric.append(library.numeric(rr,g,'ORIGINAL_EARLY_CAPTURE_OWN_SYSTEM_V1'))
            if g[-1]not in core.ORDINARY:continue
            joined=[]
            for r in rr:
                offer=offers.get(library.key(r))
                if not offer:continue
                joined.append(dict(offer,prediction=r['prediction'],side=None,original_side=None,raw_prediction=None,method_key=library.view_id(g),capture_version=capture,product_id=g[3],procedure_id=g[1],history_regime=g[2],fallback=r['fallback'],model_version=r['model_version'],forecast_issued_at=r['issued_at_utc'],forecast_persistence_at=r['persistence_completed_at']))
            gg=shared.grade(joined,strategies=(shared.ADJUSTED,));replay.extend(gg)
            ss=core.aggregate(gg,panel='EARLY_SAVED_FORECAST_ON_RETAINED_T90_THRESHOLD_P1:'+capture,method=g[1]+':'+library.view_id(g),track='B_REPLAY',strategy='P1',pool=gg)
            for s in ss:
                if s['target']!=g[-1]:continue
                s.update(method_key=library.view_id(g),base_procedure_id=g[1],history_regime=g[2],product_id=g[3],capture_version=capture);scores.append(s)
        spec.append(dict(capture_version=capture,source_sha256=core.sha(path),rows=len(obj['rows']),groups=len(grouped),feature_cutoff_qualification='FUTURE_T90_FIELD_IS_DEADLINE_NOT_AUTHENTICATED_FEATURE_AVAILABILITY'))
    core.save(out/'SCORES.json',numeric);core.save(out/'SELECTION_SCORES.json',scores);core.write_csv(out/'NUMERICAL_TABLE.csv',numeric)
    wide=core.wide(scores);core.save(out/'SELECTION_SIDE_TABLE.json',wide);core.write_csv(out/'SELECTION_SIDE_TABLE.csv',wide)
    core.savegz(private/'ADDITIONAL_SAVED_VERSION_ROWS_V1.json.gz',dict(numeric=numeric_rows,original=grades,P1=replay))
    core.save(out/'SAVED_LIST_REPORTING_ANNOTATIONS_V1.json',dict(primary=primary['panel'],versions=[dict(panel=v['panel'],whole_list_fixed_before_first_included_game=v['prepared_at']<'2026-10-30T00:15:00+00:00',
        primary=v['panel']==primary['panel'],reporting='FIXED_WEEKLY_PRESTART_LIST'if v['prepared_at']<'2026-10-30T00:15:00+00:00'else'POSTSTART_PARTIAL_OR_ROLLING_REUSED_RECORD_LIST_DIAGNOSTIC; per-record pregame qualification separate')for v in census['versions']],
        no_union_or_independence_claim=True,top_all_fair_comparison='Same earliest source board and the exact original list; later rolling T90 all-leans table is a different clock panel.'))
    core.save(out/'RUN_RECEIPT.json',dict(state='ADDITIONAL_AUTHENTIC_SAVED_VERSION_GRADING_COMPLETE_PARTIAL_WEEK',completed_at_utc=core.now(),wall_seconds=time.monotonic()-started,sources=spec,same_snapshot_original_rows=len(grades),saved_top_rows_reused=len(top),same_source_top_join_equal=True,numeric_views=len(numeric),side_views=len(scores),private_rows_sha256=core.sha(private/'ADDITIONAL_SAVED_VERSION_ROWS_V1.json.gz'),code_sha256=core.sha(__file__),new_fits=0,new_inference=0,new_forecasts=0))
    print(json.dumps(dict(state='SCORED',numeric_views=len(numeric),side_views=len(scores),same_source_original_rows=len(grades))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-root',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);a=p.parse_args();run(a.private_root,a.public_root)
