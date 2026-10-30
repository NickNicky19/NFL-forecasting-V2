#!/usr/bin/env python3
"""Zero-fit replay of reference bytes proven retained before later W7 games."""
import collections,csv,gzip,hashlib,json,math,sys,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from nfl_v2 import hgb_control as src
from nfl_v2.identity import unique_gsis_bridge
from nfl_v2.scoring import point_metrics
from nfl_v2.shared_subgroups import packet_rows


def main():
    start=time.monotonic();base=Path(sys.argv[1]);cache=Path(sys.argv[2]);public=ROOT/'reports/continuation-20261030c/server-retained-R0-v1';private=base/'server-retained-R0-v1'
    public.mkdir();private.mkdir();protocol_path=public.parent/'SERVER_R0_REFERENCE_PROTOCOL.json';p=json.loads(protocol_path.read_text());proof=src.utc(p['proven_retained_by_utc']).timestamp()
    raw=base/'website-reference-probe-v1'/Path(p['source_blob']['path']).name;b=raw.read_bytes()
    if len(b)!=p['source_blob']['size']or src.sha(raw)!=p['gzip_sha256']or hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()!=p['source_blob']['sha']:raise ValueError('server-bound source blob mismatch')
    envelope=json.loads(gzip.decompress(b));packet=envelope['payload']
    if hashlib.sha256(src.canonical(packet)).hexdigest()!=p['payload_sha256']:raise ValueError('source payload hash mismatch')
    oldp=json.loads((ROOT/'reports/continuation-20261030/distribution-wave-v2/FROZEN_PROTOCOL.json').read_text())
    for s in oldp['source_ids']:
        if src.sha(cache/s['name'])!=s['sha256']:raise ValueError('label source changed')
    source,games,_=src.load_source(cache,oldp);labels={(r['game_id'],r['player_id']):r for r in source if r['season']==2026 and r['week']==7};byespn={g['espn']:g for g in games.values()if g['season']==2026 and g['week']==7}
    with gzip.open(cache/'roster-week8-identity-2026.csv.gz','rt')as f:
        bridge=unique_gsis_bridge([(r['sleeper_id'],r['gsis_id'])for r in csv.DictReader(f)if r['season']=='2026'and int(r['week'])<=7 and r['sleeper_id']and r['gsis_id']],source_id='FROZEN_WEEK_LE7_EXACT_ID_ONLY')
    top=ROOT/'reports/continuation-20261030b/TOP5_BY_CATEGORY_PRODUCT.json';leaders={r['target']:r for r in json.loads(top.read_text())if r['rank']==1 and r['ranking_product']=='display_point'}
    candidates={(r['game_id'],r['player_id'],r['target'],r['population']):r for r in json.loads((base/'website-reference-replay-v1/MATCHED_ROWS.json').read_text())['candidates']}
    for r in packet_rows(base/'ordered-information-ablation-v1/ALL_PREDICTIONS.json.gz'):
        lead=leaders.get(r['target'])
        if int(r['week'])!=7 or not lead or not lead['procedure_id'].startswith('v2-c02-'):continue
        if r['history_regime']==lead['history_regime']and r['product_id']==lead['product']and r['procedure_id']==lead['procedure_id']:
            candidates[(r['game_id'],r['player_id'],r['target'],r['population'])]=r
    groups=collections.defaultdict(list);retained=[];excluded=set();seen=set();eligible_games=set()
    for r in packet['rows']:
        if(r['season'],r['week'])!=(2026,7):raise ValueError('wrong reference period')
        g=byespn.get(str(r['game_id']))
        if not g or src.utc(r['kickoff']).timestamp()!=g['kickoff']:raise ValueError('reference game mismatch')
        if g['kickoff']-90*60<=proof:excluded.add(g['game_id']);continue
        eligible_games.add(g['game_id']);pid=bridge.get(str(r['player_id']));a=labels.get((g['game_id'],pid));t=r['category'];key=(g['game_id'],pid,t)
        if key in seen and pid is not None:raise ValueError('ambiguous reference row')
        seen.add(key)
        status=('TARGET_CONTRACT_NOT_COMPARABLE'if t not in src.TARGETS else'UNLINKED_ID'if pid is None else'APPEARANCE_UNKNOWN'if a is None or not a['played']else'POSITION_MISMATCH'if a['position']!=r['position']else'SUPPORTED')
        pop='primary'if r['position']in oldp['source_role_contract']['primary'].get(t,[])else'extended'
        for product,value in [('website_point',r.get('adjusted_projection')),('provider_point',r.get('raw_projection'))]:
            why=status
            if why=='SUPPORTED'and(not isinstance(value,(int,float))or not math.isfinite(value)):why='EXPLICIT_FORECAST_UNAVAILABLE'
            y=a['values'][t]if why=='SUPPORTED'else None
            if why=='SUPPORTED'and y is None:why='MISSING_ACTUAL'
            record=dict(game_id=g['game_id'],player_id=pid,target=t,population=pop,position=r['position'],product_id=product,prediction=value,actual=y,status=why,recorded_capture=packet['captured_at'],server_retained_by=p['proven_retained_by_utc'])
            retained.append(record)
            if t in src.TARGETS and t!='anytime_td':groups[t,pop,product].append(record)
    scores=[];contrasts=[]
    for(t,pop,product),issued in sorted(groups.items()):
        scored=[r for r in issued if r['status']=='SUPPORTED'];n=len(scored)
        if not n:continue
        identity='server-retained-website-R0-reference-v1'if product=='website_point'else'server-retained-provider-reference-v1'
        shared=dict(target=t,population=pop,season=2026,week=7,evaluation_seasons=[2026],evaluation_weeks=[7],record_kind='forecast_evaluation_view',evidence='REPRODUCED_FROM_DATA',history_regime='FIXED_ARCHIVE_NOT_RETRAINABLE',cutoff='publicbytesknownby'+p['proven_retained_by_utc']+';recordedearliercaptureunverified',source_vintage='SERVER_SOURCE_RETENTION_BEFORE_GAME;providerinputvintageunqualified;currentvintagequalifiedlabels',cohort_limit='conditionalqualifiedappearanceinsidearchivedissuance;NOTtodaysselectedwebsiteorsamecutoffV2',uncertainty='oneweek;insufficient_week_clusters;no selectionadjustment',fallback_rows=None)
        scores.append(dict(shared,procedure_id=identity,procedure_family_id='ARCHIVED_REFERENCE',product_id=product,evaluation_panel_id='server-retained-R0-13game-W7-reference-v1',forecast_rows=len(issued),unique_games=len({r['game_id']for r in scored}),**point_metrics([r['prediction']for r in scored],[r['actual']for r in scored],t)))
        paired=[]
        for r in scored:
            c=candidates.get((r['game_id'],r['player_id'],t,pop))
            if not c or c.get('prediction')is None or c.get('actual')is None:continue
            if c['actual']!=r['actual']:raise ValueError('matched outcome mismatch')
            paired.append(dict(r,candidate_prediction=float(c['prediction']),candidate_fallback=c.get('fallback')))
        if not paired:continue
        am=point_metrics([r['candidate_prediction']for r in paired],[r['actual']for r in paired],t);bm=point_metrics([r['prediction']for r in paired],[r['actual']for r in paired],t);lead=leaders[t]
        membership=hashlib.sha256(src.canonical(sorted((r['game_id'],r['player_id'],t,pop)for r in paired))).hexdigest()
        cmp=dict(status='PAIRED_RETAINED_ROWS',metric='mae',candidate_error=am['mae'],comparator_error=bm['mae'],paired_n=len(paired),membership_sha256=membership,comparator_procedure_id=identity,comparator_history_regime='FIXED_ARCHIVE_NOT_RETRAINABLE',comparator_product_id=product,cutoff_policy='DIFFERENT_HORIZON_AND_INFORMATION;authenticreference_retention_only',uncertainty=shared['uncertainty'])
        scores.append(dict(shared,procedure_id=lead['procedure_id'],procedure_family_id='EXISTING_FROZEN_V2_REPRESENTATIVE',history_regime=lead['history_regime'],product_id=lead['product'],evaluation_panel_id='server-retained-W7-shared-outcomes-'+product+'-v1',forecast_rows=len(paired),unique_games=len({r['game_id']for r in paired}),comparison=cmp,**am))
        contrasts.append(dict(target=t,population=pop,reference_product=product,n=len(paired),reference_mae=bm['mae'],candidate_mae=am['mae'],delta_mae=am['mae']-bm['mae'],relative_error_change=(am['mae']-bm['mae'])/bm['mae']if bm['mae']else None,comparison=cmp))
    with gzip.open(private/'RETAINED_AND_MATCHED.json.gz','wt')as f:json.dump(dict(rows=retained,candidates=[dict(key=k,**v)for k,v in candidates.items()]),f,separators=(',',':'),allow_nan=False)
    src.immutable_json(public/'SCORES.json',scores);src.immutable_json(public/'PAIRED_COMPARISONS.json',contrasts)
    receipt=dict(state='COMPLETE_SERVER_RETAINED_REFERENCE_REPLAY',actual_completed_at=src.now(),protocol_sha256=src.sha(protocol_path),code_sha256=src.sha(__file__),fixed_V2_choices_sha256=src.sha(top),source_labels=[dict(name=s['name'],sha256=s['sha256'])for s in oldp['source_ids']],identity_bridge_sha256=src.sha(cache/'roster-week8-identity-2026.csv.gz'),eligible_games=len(eligible_games),excluded_unproven_games=sorted(excluded),retained_views=len(retained),supported_reference_views=sum(r['status']=='SUPPORTED'for r in retained),score_views=len(scores),paired_contrasts=len(contrasts),private_rows_sha256=src.sha(private/'RETAINED_AND_MATCHED.json.gz'),new_fits=0,new_forecasts=0,current_2026_week8_outcomes_read=0,wall_seconds=time.monotonic()-start,source_input_timing='UNQUALIFIED',actual_current_website_comparison='UNESTABLISHED')
    src.immutable_json(public/'RUN_RECEIPT.json',receipt);print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
