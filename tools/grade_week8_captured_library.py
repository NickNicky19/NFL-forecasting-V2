"""Grade the finite retained Week8 library; never fit or execute a forecast model.

This adapter normalizes existing capture schemas and calls the existing V2
numeric/threshold scorers. Capture versions, histories and output views stay
distinct. The source roster is frozen before this adapter evaluates its losses.
"""
from __future__ import annotations
import argparse,collections,gzip,hashlib,json,math,sys,time
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from tools import grade_saved_week8 as core
from nfl_v2 import scoring,full_provider_prop_replay as shared
from nfl_v2.precision_grid import chart_median_precision
from nfl_v2.recorded_prop_grading import canonical

CASES=[
 ('EARLY_EMPIRICAL','week8-shadow-v2/shadow-forecasts.json.gz','reports/continuation-20261029/week8-shadow-v2/CAPTURE_RECEIPT.json'),
 ('EARLY_HGB','hgb-history-v1/WEEK8_SHADOWS.json.gz','reports/continuation-20261029/hgb-history-v1/WEEK8_CAPTURE_RECEIPT.json'),
 ('COMMON_ASOF_EMPIRICAL','empirical-common-asof-shadow-v1/shadow-forecasts.json.gz','reports/continuation-20261030/empirical-common-asof-shadow-v1/CAPTURE_RECEIPT.json'),
 ('DISTRIBUTION_WAVE','distribution-wave-v2/WEEK8_OPEN_T90_SHADOWS.json.gz','reports/continuation-20261030/distribution-wave-v2/WEEK8_CAPTURE_RECEIPT.json'),
 ('COUNT_ABLATION','count-ablation-wave-v1/WEEK8_OPEN_T90_SHADOWS.json.gz','reports/continuation-20261030/count-ablation-wave-v1/WEEK8_CAPTURE_RECEIPT.json'),
 ('CHART_WAVE','chart-wave-v1/WEEK8_CHART_SHADOWS.json.gz','reports/continuation-20261030/chart-wave-v1/WEEK8_CAPTURE_RECEIPT.json'),
 ('CHART_EMPIRICAL','chart-wave-v1/WEEK8_CHART_EMPIRICAL_SHADOWS.json.gz','reports/continuation-20261030/chart-wave-v1/EMPIRICAL_FUTURE_CAPTURE_RECEIPT.json'),
 ('AVAILABILITY_AB','availability-wave-v1/AB-STAGED_SHADOWS.json.gz','reports/continuation-20261030b/availability-wave-v1/AB-RUN_RECEIPT.json'),
 ('AVAILABILITY_C','availability-wave-v1/C-STAGED_SHADOWS.json.gz','reports/continuation-20261030b/availability-wave-v1/C-RUN_RECEIPT.json'),
 ('C02','c02-future-shadow-v1/STAGED_SHADOWS.json.gz','reports/continuation-20261030b/c02-future-shadow-v1/RUN_RECEIPT.json'),
 ('STRICT_HGB','strict-hgb-future-v1/STAGED_SHADOWS.json.gz','reports/continuation-20261030c/strict-hgb-future-v1/EXPORT_RECEIPT.json'),
 ('D1_D2','qualified-defense-information-v1/WEEK8_PAIRED_SHADOWS.json.gz','reports/continuation-20261030c/qualified-defense-information-v1/WEEK8_CAPTURE_RECEIPT.json')]
LAST='ea2ce5f57146112bb4b5ccebcf8544b181192f50'
VERSION='v2-week8-saved-capture-library-grading-v1'
ORDINARY=core.ORDINARY


def rows(body):
    obj=json.loads(body);return obj['rows'],obj
def key(r):return r['game_id'],r['player_id']or r['source_player_id'],r['target']
def group(r):return tuple(r[k]for k in('capture_version','procedure_id','history_regime','product_id','information_policy','availability_arm','target'))
def view_id(g):return hashlib.sha256(canonical(g)).hexdigest()[:24]


def packet_specs(private,public):
    evidence=Path(core.read(private/'LOCAL_INPUT_BINDINGS_V1.json')['private_evidence_root'])
    pre=core.read(public/'independent/CAPTURE_BYTE_PREFLIGHT_REVIEW_V1.json');verified={r['capture_version']:r for r in pre['captures']}
    out=[]
    for capture,rel,receipt in CASES:
        p=evidence/rel;rr=core.read(ROOT/receipt)
        if capture=='CHART_EMPIRICAL':expected=rr['packet']['sha256']
        else:expected=verified[capture]['forecast_sha256']
        if core.sha(p)!=expected and capture=='D1_D2':p=evidence/'continuation-20261030c/SMALL_AND_DEFENSE_STAGING'/rel
        assert core.sha(p)==expected,(capture,'capture byte mismatch')
        persisted=next((rr[k]for k in('actual_persistence_completed_at','actual_aggregate_persistence_completed_at','actual_completed_at','actual_completed_at_utc')if rr.get(k)),None)
        assert persisted,capture
        out.append(dict(capture_version=capture,source_path=p,source_sha256=expected,receipt=receipt,receipt_sha256=core.sha(ROOT/receipt),persisted_at=persisted))
    return out


def normalize(raw,*,capture,schema,persisted,labels,index,source_sha,owner=None):
    target=raw.get('target',raw.get('category'));assert target in scoring.TARGETS
    objective=raw.get('objective');product=raw.get('product_id',raw.get('product'))
    if objective:product=objective
    proc=raw.get('procedure_id')or('hgb-direct-history-controls-v1:'+objective if objective else'empirical-player-history-control-v1')
    if owner:proc=owner
    history=raw.get('history_regime','FIXED_ARCHIVED_REFERENCE')
    info=raw.get('information_policy')or('AVAILABILITY-'+str(raw.get('availability_arm'))if raw.get('availability_arm')else'ORIGINAL_CAPTURE_FEATURE_POLICY')
    point=raw.get('prediction',raw.get('forecast_value'));issued=raw.get('issued_at_utc')or raw.get('issued_at')or raw.get('actual_generated_at')
    assert issued,(capture,'no original issuance clock')
    game=raw.get('game_id');player=raw.get('player_id')or raw.get('sleeper_id');gid=labels.game(game)
    kick=raw.get('kickoff_utc')or raw.get('kickoff')or(labels.frozen[gid]['kickoff_utc']if gid else None)
    originally_issued=core.finite(point)and raw.get('status')!='ABSTAIN'
    eligible=bool(gid and kick and core.aware(issued)<core.aware(kick)and core.aware(persisted)<core.aware(kick))
    t90=bool(eligible and max(core.aware(issued),core.aware(persisted)).timestamp()<=core.aware(kick).timestamp()-5400)
    if gid and kick:assert core.aware(kick)==core.aware(labels.frozen[gid]['kickoff_utc'])
    if raw.get('actual')is not None:raise ValueError('unexpected target outcome in original future forecast')
    row=core.base_row(labels,game=game,player=player,target=target,line=0.,point=point,raw=None,side=None,index=index,position=raw.get('position'),
        capture_version=capture,source_schema=schema,capture_sha256=source_sha,procedure_id=proc,history_regime=history,product_id=product,
        information_policy=info,availability_arm=raw.get('availability_arm','NONE'),
        query_id=raw.get('query_id'),forecast_status=raw.get('status','ISSUED_ARCHIVED_REFERENCE'),
        original_forecast_issued=originally_issued,pregame_retention_eligible=eligible,T90_eligible=t90,
        issued_at_utc=issued,persistence_completed_at=persisted,feature_cutoff_utc=raw.get('feature_cutoff_utc',raw.get('source_cutoff_utc',raw.get('cutoff'))),
        fallback=raw.get('fallback','UNKNOWN_NOT_RETAINED'),model_version=raw.get('model_version',raw.get('model_artifact_id')),
        source_functional=raw.get('prediction_functional'),abstention_reason=raw.get('abstention_reason'),
        source_row_index_within_capture=index)
    row['scored']=bool(originally_issued and eligible and row['label_state']=='SUPPORTED')
    row['error']=point-row['actual']if row['scored']else None
    return row


def research_rows(specs,labels):
    result=[];census=[]
    for spec in specs:
        rr,obj=rows(gzip.decompress(spec['source_path'].read_bytes()));capture=spec['capture_version'];start=len(result)
        for i,r in enumerate(rr):result.append(normalize(r,capture=capture,schema=obj['schema'],persisted=spec['persisted_at'],labels=labels,index=i,source_sha=spec['source_sha256']))
        part=result[start:];pairs=[(group(r),key(r))for r in part];assert len(pairs)==len(set(pairs)),(capture,'duplicate method opportunity')
        census.append({k:v for k,v in spec.items()if k!='source_path'}|dict(rows=len(rr),original_issued=sum(r['original_forecast_issued']for r in part),preadmission_exclusions=sum(r['original_forecast_issued']and not r['pregame_retention_eligible']for r in part),before_T90=sum(r['original_forecast_issued']and r['T90_eligible']for r in part),groups=len({group(r)for r in part})))
    return result,census


def owner_rows(private,labels):
    result=[];census=[];proofs=core.read(ROOT/'reports/week8-grading-20261102l/FROZEN_SOURCE_ASSIGNMENTS_V1.json')['proofs'];first={}
    for proof in proofs:
        head=proof['head'];dd=core.read(private/('classic_directory.json'if head==LAST else f'classic-directory-{head}.json'))
        for f in dd:
            old=first.get(f['name'])
            if old is None or proof['server_retained_at']<old['server_retained_at']:first[f['name']]=proof
    for path in sorted((private/'source-metadata').glob('classic-*.gz')):
        obj=core.read_gzip(path)if hasattr(core,'read_gzip')else json.loads(gzip.decompress(path.read_bytes()));payload=obj['payload'];receipt=first[path.name[8:]]
        assert hashlib.sha256(canonical(payload)).hexdigest()==obj['payload_sha256']
        rows0=payload['rows'];capture='CLASSIC:'+path.name[8:24];start=len(result)
        for i,r in enumerate(rows0):
            if r['category']not in scoring.TARGETS:continue
            raw=dict(r,prediction=r['adjusted_projection'],issued_at=payload['forecast_generated_at'],product_id='saved_adjusted_recipe_point',model_version=payload['engine_sha256'],actual=None)
            result.append(normalize(raw,capture=capture,schema=payload['schema_version'],persisted=receipt['server_retained_at'],labels=labels,index=i,source_sha=core.sha(path),owner=payload['model']))
        part=result[start:];census.append(dict(capture_version=capture,rows=len(part),all_source_rows=len(rows0),unsupported_website_fantasy_rows=sum(r['category']=='fpts'for r in rows0),forecast_generated_at=payload['forecast_generated_at'],captured_at=payload['captured_at'],server_retained_by=receipt['server_retained_at'],source_head=receipt['head'],source_sha256=core.sha(path),original_issued=sum(r['original_forecast_issued']for r in part),preadmission_exclusions=sum(r['original_forecast_issued']and not r['pregame_retention_eligible']for r in part),groups=len({group(r)for r in part}),source_timestamps_verified=False))
    # The last original adaptive packet was independently retained by V2 before
    # Week8 kickoff. Earlier public versions need their own owner-clock proof.
    evidence=Path(labels.binding['private_evidence_root']);path=evidence/'week8-public-original-3907ca38.json';packet=core.read(path)
    capture='WEBSITE_ADAPTIVE_ORIGINAL_3907';start=len(result)
    for i,r in enumerate(packet['rows']):
        out=normalize(dict(r,actual=None),capture=capture,schema=packet['schema_version'],persisted=r['persistence_completed_at'],labels=labels,index=i,source_sha=core.sha(path),owner='P2_SELECTED:'+r['procedure_version'])
        result.append(out)
    part=result[start:];census.append(dict(capture_version=capture,rows=len(part),source_sha256=core.sha(path),original_issued=len(part),groups=len({group(r)for r in part}),retention='Previously hash-bound V2 original public pregame packet; original per-record issue/persistence retained'))
    return result,census


def numeric(rr,g,panel):
    valid=[r for r in rr if r['scored']];target=g[-1];product=g[3]
    pp=[r['prediction']for r in valid];yy=[r['actual']for r in valid]
    metric=scoring.point_metrics(pp,yy,target)
    if target=='nick-chart-ppr-v1'and product=='lower_median':
        precision=chart_median_precision(pp,yy,product_id=product)
        for name,v in precision.items():metric[name]=v['rate']
    else:precision={name:dict(numerator=sum((abs(p-y)<int(name.rsplit('_',1)[1])if '_lt_'in name else abs(p-y)<=int(name.rsplit('_',1)[1]))for p,y in zip(pp,yy)),denominator=len(valid))for name in metric if name.startswith(('abs_lt_','abs_le_'))}
    for k,v in list(metric.items()):
        if isinstance(v,float)and not math.isfinite(v):metric[k]='Infinity'if v>0 else'-Infinity'
    pid=view_id(g);ident=[VERSION,g,panel]
    return dict(record_id='W8-NUM-'+hashlib.sha256(canonical(ident)).hexdigest()[:24],record_kind='forecast_evaluation_view',
        procedure_id=g[1],capture_version=g[0],history_regime=g[2],product_id=product,information_policy=g[4],availability_arm=g[5],target=target,
        method_key=pid,evaluation_panel_id=panel+':'+g[0],time_panel_id='2026_W8_PARTIAL',season=2026,week=8,evaluation_weeks=[8],evaluation_seasons=[2026],period='full_game',season_type='REG',
        horizon_id=panel,forecast_rows=len(rr),scored_forecast_rows=len(valid),issued_forecast_rows=sum(r['original_forecast_issued']for r in rr),
        pending_rows=sum(r['outcome_state']=='pending'for r in rr),unknown_rows=sum(r['outcome_state']!='pending'and not r['scored']and r['original_forecast_issued']for r in rr),
        abstention_rows=sum(not r['original_forecast_issued']for r in rr),fallback_rows=sum(r['fallback']not in(None,False,'none','NONE','UNKNOWN_NOT_RETAINED')for r in rr),
        fallback_unknown_rows=sum(r['fallback']=='UNKNOWN_NOT_RETAINED'for r in rr),
        unique_games=len({r['game_id']for r in valid}),unique_players=len({r['player_id']for r in valid}),scored_key_sha256=hashlib.sha256(canonical(sorted(key(r)for r in valid))).hexdigest(),
        precision_counts=precision,source_vintage='AUTHENTIC_SAVED_PREGAME_OUTPUT_CURRENT_VINTAGE_FINAL_LABELS',evidence='REPRODUCED_FROM_DATA',
        uncertainty='INSUFFICIENT_WEEK_CLUSTERS_ONE_EXPOSED_WEEK; paired game sensitivity separately where supported',
        whole_week_complete=False,scoring_version=VERSION,null_reason=None if valid else'NO_QUALIFIED_FINAL_PLAYED_OUTPUTS',**metric)


def run(private,public):
    started=time.monotonic();out=public/'captured-library-v2';out.mkdir(exist_ok=False)
    labels=core.Labels(private);specs=packet_specs(private,public);data,census=research_rows(specs,labels);owned,owner_census=owner_rows(private,labels);data.extend(owned);census.extend(owner_census)
    by=collections.defaultdict(list)
    for r in data:by[group(r)].append(r)
    # Metadata roster fixed before this adapter evaluates any library losses.
    roster=[dict(method_key=view_id(g),capture=g[0],procedure_id=g[1],history=g[2],product=g[3],information_policy=g[4],availability_arm=g[5],target=g[6],outer_rows=len(rr))for g,rr in sorted(by.items())]
    core.save(out/'FROZEN_CAPTURE_ROSTER_V1.json',dict(state='FINITE_CAPTURE_ROSTER_BEFORE_NEW_LIBRARY_METRICS',at=core.now(),sources=census,method_output_category_cells=roster,rule='No point/side/score-based capture selection. All versions retained; fixed PRIMARY_COMMON excludes later partial classic versions.'))
    classics=sorted(owner_census[:-1],key=lambda x:(x['server_retained_by'],x['source_sha256']));primary_classic=classics[0]['capture_version']
    primary_captures={s['capture_version']for s in specs}|{primary_classic,'WEBSITE_ADAPTIVE_ORIGINAL_3907'}
    common={};members=collections.defaultdict(list)
    for g,rr in by.items():
        if g[0]not in primary_captures:continue
        members[g[-1]].append({key(r)for r in rr if r['scored']and r['T90_eligible']})
    for target,sets in members.items():common[target]=set.intersection(*sets)if sets else set()
    scores=[];sides=[];p1rows=[];comparisons=[]
    offers=json.loads(gzip.decompress((private/'ORIGINAL_JOINED_ROWS_V1.json.gz').read_bytes()))['rows'];offers={key(r):r for r in offers if r['panel']=='ORIGINAL_PROVIDER_T90'}
    reference={key(r):r for r in data if r['capture_version']=='WEBSITE_ADAPTIVE_ORIGINAL_3907'and r['scored']and r['T90_eligible']}
    for g,rr in sorted(by.items()):
        # Original native graders already emit the full early14-game view.
        if g[0]not in('EARLY_EMPIRICAL','EARLY_HGB'):scores.append(numeric(rr,g,'OWN_CAPTURE_FULL_SYSTEM'))
        tt=[r for r in rr if r['T90_eligible']or not r['original_forecast_issued']];scores.append(numeric(tt,g,'OWN_CAPTURE_T90_SYSTEM'))
        if g[0]in primary_captures:
            cc=[r for r in rr if key(r)in common.get(g[-1],set())and r['T90_eligible']];scores.append(numeric(cc,g,'PRIMARY_ALL_METHOD_COMMON_FINAL_ROWS'))
        matched=[r for r in rr if r['scored']and r['T90_eligible']and key(r)in reference]
        if matched:
            delta=[abs(r['error'])-abs(reference[key(r)]['error'])for r in matched];metric='Brier'if g[-1]=='anytime_td'else'MAE'
            if metric=='Brier':delta=[r['error']**2-reference[key(r)]['error']**2 for r in matched]
            comparisons.append(dict(method_key=view_id(g),capture=g[0],procedure_id=g[1],history=g[2],product=g[3],target=g[-1],metric=metric,n=len(matched),games=len({r['game_id']for r in matched}),candidate_minus_incumbent=sum(delta)/len(delta),comparator='WEBSITE_ADAPTIVE_ORIGINAL_3907',comparison_scope='Identical qualified final player-games; different source/capture information horizons disclosed, not pure learner effect'))
        if g[-1]not in ORDINARY:continue
        joined=[]
        for r in rr:
            offered=offers.get(key(r))
            if not offered or not r['original_forecast_issued']or not r['T90_eligible']:continue
            q=dict(offered,prediction=r['prediction'],raw_prediction=None,side=None,original_side=None,source_row_index=r['source_row_index'],
                   capture_version=g[0],procedure_id=g[1],history_regime=g[2],product_id=g[3],method_key=view_id(g),model_version=r['model_version'],
                   forecast_issued_at=r['issued_at_utc'],forecast_persistence_at=r['persistence_completed_at'],fallback=r['fallback'])
            joined.append(q)
        grades=shared.grade(joined,strategies=(shared.ADJUSTED,))
        for r in grades:
            r.update(method_key=view_id(g),capture_version=g[0]);p1rows.append(r)
        ss=core.aggregate(grades,panel='EARLY_SAVED_FORECAST_ON_RETAINED_T90_THRESHOLD_P1:'+g[0],method=g[1]+':'+view_id(g),track='C_RESEARCH_REPLAY',strategy='P1',pool=grades)
        for s in ss:
            s.update(history_regime=g[2],product_id=g[3],information_policy=g[4],availability_arm=g[5],capture_version=g[0],method_key=view_id(g),base_procedure_id=g[1])
        sides.extend(s for s in ss if s['target']==g[-1])
    core.save(out/'SCORES.json',scores);core.save(out/'SELECTION_SCORES.json',sides);core.save(out/'NUMERICAL_TABLE.json',scores);core.write_csv(out/'NUMERICAL_TABLE.csv',scores)
    wide=core.wide(sides);core.save(out/'SELECTION_SIDE_TABLE.json',wide);core.write_csv(out/'SELECTION_SIDE_TABLE.csv',wide)
    core.save(out/'MATCHED_INCUMBENT_COMPARISONS.json',comparisons);core.write_csv(out/'MATCHED_INCUMBENT_COMPARISONS.csv',comparisons)
    core.save(out/'COMMON_PANEL_DEFINITION.json',dict(primary_classic=primary_classic,primary_captures=sorted(primary_captures),common_final_rows={t:len(v)for t,v in common.items()},own_system_and_common_masks_separate=True,notes='No later five-game classic version shrinks the fixed thirteen-game common comparison; later versions retain own-pool views. One exposed week; no selection-policy performance is inferred from hindsight minima.'))
    # Store compact recoverable row evidence; original forecast bytes stay intact.
    fields=['capture_version','procedure_id','history_regime','product_id','information_policy','availability_arm','target','query_id','game_id','player_id','source_player_id','prediction','actual','error','label_state','outcome_state','original_forecast_issued','pregame_retention_eligible','T90_eligible','issued_at_utc','persistence_completed_at','feature_cutoff_utc','fallback','model_version','capture_sha256']
    core.savegz(private/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz',dict(rows=[{k:r.get(k)for k in fields}for r in data]))
    core.savegz(private/'CAPTURED_LIBRARY_P1_ROWS_V1.json.gz',dict(rows=p1rows))
    elapsed=time.monotonic()-started
    core.save(out/'RUN_RECEIPT.json',dict(state='PARTIAL_WEEK_RETAINED_LIBRARY_NUMERICAL_AND_P1_SCORED',completed_at_utc=core.now(),wall_seconds=elapsed,original_capture_files=len(census),normalized_output_rows=len(data),unique_outcome_keys=len({key(r)for r in data}),numeric_score_views=len(scores),P1_score_views=len(sides),P1_grade_rows=len(p1rows),
        numeric_private_sha256=core.sha(private/'CAPTURED_LIBRARY_NUMERIC_ROWS_V1.json.gz'),P1_private_sha256=core.sha(private/'CAPTURED_LIBRARY_P1_ROWS_V1.json.gz'),numeric_scores_sha256=core.sha(out/'SCORES.json'),selection_scores_sha256=core.sha(out/'SELECTION_SCORES.json'),code_sha256=core.sha(__file__),helper_sha256=core.sha(core.__file__),core_sha256=core.sha(scoring.__file__),identity_bridge_sha256=labels.binding['identity_roster_sha256'],new_fits=0,new_model_inference=0,new_forecasts=0,whole_week_complete=False))
    print(json.dumps(dict(state='PARTIAL_WEEK_LIBRARY_SCORED',wall_seconds=elapsed,rows=len(data),numeric_views=len(scores),P1_views=len(sides),common={t:len(v)for t,v in common.items()})))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-root',type=Path,required=True);p.add_argument('--public-root',type=Path,required=True);a=p.parse_args();run(a.private_root,a.public_root)
