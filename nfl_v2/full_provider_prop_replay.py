"""Bounded expansion of retained threshold records using the shared grader.

No collection, fitting, inference, bookmaker settlement or price invention.
"""
from __future__ import annotations
import collections,csv,gzip,hashlib,json,math,resource,time
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from . import scoring,recorded_prop_grading as pilot
from .identity import unique_gsis_bridge
from .prop_evidence_metadata_v2 import object_spans_in_array,project_metadata

VERSION='v2-retained-provider-labelled-full-pool-2026W7-v1'
ADJUSTED='SAVED_ADJUSTED_POINT_DIRECTION_RETAINED_PRECISION'
RAW='SAVED_RAW_PROJECTION_DIRECTION_RETAINED_PRECISION'
STRATEGIES=('original',ADJUSTED,RAW,'alwaysOver','alwaysUnder')
TARGETS=tuple(t for t in scoring.TARGETS if t not in('nick-chart-ppr-v1','anytime_td'))
PROOF='2026-10-23T17:49:53Z'
canonical=pilot.canonical;sha=pilot.sha;now=pilot.now;write=pilot.write


def metadata_panel(metadata):
    return [dict(r)for r in metadata if r['metadata_panel_status']!='SERVER_RETENTION_NOT_BEFORE_T90'
        and r['category']in TARGETS and r.get('line_from')in('dk','sleeper')
        and scoring.finite(r.get('line'))]


def prepare(*,public,private,metadata,forward,reference,source_root,memberships):
    out,priv=Path(public),Path(private)
    if out.exists()or priv.exists():raise ValueError('fresh immutable outputs required')
    if priv.resolve().is_relative_to(Path(__file__).resolve().parents[1]):raise ValueError('private outside Git required')
    expected={'metadata':'bc76e172f2fce63b777b2d05a6bee5e23da45bd2c352f1e4b8db63dd07ede9a7',
        'forward':'e33bda264b397ca9a038e8d01e30caf71c615fd957d0e7f0b911c4c4ff39156e',
        'reference':'9e5e5db552d1a947a7186d64299cf659bdba13e5abfcc7732f373fa8e5c9bdf9',
        'memberships':'9e39ac53f0b0d7160062c52ea15e7e5f6f6b44d2970673cb41c942fcbb0d8281'}
    paths=dict(metadata=Path(metadata),forward=Path(forward),reference=Path(reference),memberships=Path(memberships))
    if any(sha(paths[k])!=v for k,v in expected.items()):raise ValueError('retained input hash mismatch')
    root=Path(source_root);parent=json.loads((Path(__file__).resolve().parents[1]/'reports/continuation-20261030c/server-retained-R0-v1/RUN_RECEIPT.json').read_bytes())
    for name,key in [('roster-week8-identity-2026.csv.gz','identity_bridge_sha256'),('games.csv',None)]:
        wanted=parent[key]if key else next(r['sha256']for r in parent['source_labels']if r['name']==name)
        if sha(root/name)!=wanted:raise ValueError('identity/schedule bytes changed')
    rows=metadata_panel(json.loads(gzip.decompress(paths['metadata'].read_bytes()))['rows'])
    if len(rows)!=462 or collections.Counter(r['line_from']for r in rows)!=dict(dk=441,sleeper=21):raise ValueError('source universe mismatch')
    if sum(r.get('lean')in('over','under')for r in rows)!=285:raise ValueError('original selection changed')
    proof=pilot.aware(PROOF).timestamp()
    if any(pilot.aware(r['kickoff']).timestamp()-5400<=proof for r in rows):raise ValueError('closed source horizon')
    out.mkdir(parents=True);priv.mkdir(parents=True)
    bindings=dict(paths,source_root=root)
    write(priv/'INPUTS_PRIVATE.json',{k:str(v)for k,v in bindings.items()})
    member_body=gzip.compress(canonical(dict(rows=rows)),mtime=0)
    with(priv/'FROZEN_FULL_POOL_METADATA.json.gz').open('xb')as f:f.write(member_body)
    p=dict(protocol_id=VERSION,registered_at_utc=now(),state='FROZEN_FULL_THRESHOLD_POOL_BEFORE_NEW_LABEL_OR_DIRECTION_SCORES',
        code_sha256=sha(__file__),core_sha256=sha(scoring.__file__),bootstrap_helper_sha256=sha(pilot.__file__),
        input_sha256=expected,source_schedule_sha256=sha(root/'games.csv'),identity_bridge_sha256=sha(root/'roster-week8-identity-2026.csv.gz'),
        bindings_sha256=sha(priv/'INPUTS_PRIVATE.json'),metadata_panel_sha256=sha(priv/'FROZEN_FULL_POOL_METADATA.json.gz'),
        selection_universe='All462finiteprovider-labelled ordinary-stat thresholds across13laterW7games;nooriginalsidefilter;957generatedthresholds excluded.',
        source_clock=PROOF,recorded_internal_capture='2026-10-22T17:55:30Z',horizon='Serverretainedbefore13laterT90deadlines;notauthenticT90forecastor executablequote;sourcequoteandinternalclocksunverified.',
        strategies=list(STRATEGIES),point_precision='Original adjusted_projection and raw_projection are saved two-decimal fields. No internal unrounded P1 claimed; no additional rounding.',
        original='Exactly285saved original sides remain;177no-side records are original abstentions, never reconstructed original picks.',
        label_policy='Exactcanonicalgame/GSIS/target/position, existing qualified explicit ordinary credits and positive physical appearance; unknowns/nulls retained. Filterreferencekeys before decoding labels.',
        raw_point_attribution='Saved source raw_projection field; verify exact equality to archived provider_point. This name does not authenticate external supplier algorithm/vintage.',
        products='Statistical direction only. AllbooksettlementUNRESOLVED; allprices/probabilities/EV/ROI/CLVnull;Sleepermultipliersnotcashodds.',
        subgroups='ALL,positions,original-selected versus original-abstained, recordedTop flags, fixed earlierworkload/topplayer memberships; missingmembershipsretained. No rerankingplayers.',
        topK='6/10/20 per target and strategy; Combined,Over-only,Under-only pools; absolute point-line gap at retained precision with stablecanonicaltie order; no outcomes/participation filter. Retrospectivepartial13game snapshot, notissuedweeklyK.',
        uncertainty='500whole-gamePCG64bootstrap seed1703 >=8decidedgames; oneweek interval unavailable. Exposed descriptive sensitivity; no selection/multiplicity adjustment.',
        exposure='PriorW7 outcomes/old285grades exposed; newraw/fullpoolmetricsnotexamined before this freeze; notfreshholdout.',
        budget=dict(wall_seconds=180,max_RSS_bytes=1073741824,max_private_bytes=8388608,max_threads=1,new_fits=0,new_forecasts=0),
        recoverability='PinnedpublicsourceGitblob+alreadyrestoredqualifiedsource/identity+publicfrozencode. Private derivative scientifically reconstructable; no newoffhostrestore claimed.',
        current2026_week8_outcomes_read=0)
    write(out/'FROZEN_PROTOCOL.json',p)
    (out/'SOURCE_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes())
    return dict(state=p['state'],protocol_sha256=sha(out/'FROZEN_PROTOCOL.json'),outer_rows=len(rows),original_selected=285,original_abstained=177)


def load_joined(out,priv,p):
    bindings=json.loads((priv/'INPUTS_PRIVATE.json').read_bytes());root=Path(bindings['source_root'])
    if sha(priv/'INPUTS_PRIVATE.json')!=p['bindings_sha256']:raise ValueError('binding changed')
    if any(sha(Path(bindings[k]))!=v for k,v in p['input_sha256'].items()):raise ValueError('source changed')
    rows=json.loads(gzip.decompress((priv/'FROZEN_FULL_POOL_METADATA.json.gz').read_bytes()))['rows']
    if sha(priv/'FROZEN_FULL_POOL_METADATA.json.gz')!=p['metadata_panel_sha256']:raise ValueError('membership changed')
    with gzip.open(root/'roster-week8-identity-2026.csv.gz','rt')as f:
        bridge=unique_gsis_bridge([(r['sleeper_id'],r['gsis_id'])for r in csv.DictReader(f)if r['season']=='2026'and int(r['week'])<=7 and r['sleeper_id']and r['gsis_id']],source_id='FROZEN_WEEK_LE7_EXACT_ID_ONLY')
    with(root/'games.csv').open()as f:games={r['espn']:r for r in csv.DictReader(f)if(r['season'],r['game_type'],r['week'])==('2026','REG','7')}
    wanted={};outer_keys={}
    for r in rows:
        g=games.get(str(r['game_id']));gsis=bridge.get(str(r['player_id']));key=(g['game_id'],gsis,r['category'])if g and gsis else None
        if g:
            kick=datetime.fromisoformat(g['gameday']+'T'+g['gametime']).replace(tzinfo=ZoneInfo('America/New_York')).timestamp()
            if kick!=pilot.aware(r['kickoff']).timestamp():raise ValueError('game kickoff conflict')
        if key:
            if key in wanted:raise ValueError('canonical duplicate selection contract')
            wanted[key]=r
        outer_keys[r['source_row_index']]=key
    reference=collections.defaultdict(list);decoded=0
    text=gzip.decompress(Path(bindings['reference']).read_bytes()).decode()
    # Metadata lexical selection precedes decoding point and actual values.
    from tools.join_saved_prop_panel import string_field
    for i,raw in enumerate(object_spans_in_array(text,'rows')):
        meta,_=project_metadata(raw);key=(meta.get('game_id'),meta.get('player_id'),string_field(raw,'target'))
        if key in wanted:reference[key].append((i,json.loads(raw)));decoded+=1
    original={}
    text=gzip.decompress(Path(bindings['forward']).read_bytes()).decode()
    selected={r['source_row_index']for r in rows}
    for i,raw in enumerate(object_spans_in_array(text,'rows')):
        if i in selected:original[i]=json.loads(raw)
    memberships=json.loads(gzip.decompress(Path(bindings['memberships']).read_bytes()))
    member_map={tuple(r['key']):r for r in memberships if str(r['key'][0]).startswith('2026_07_')}
    result=[];states=collections.Counter();point_states=collections.Counter()
    for r in rows:
        raw=original[r['source_row_index']];key=outer_keys[r['source_row_index']];vv=reference.get(key,[])
        for f in('game_id','player_id','category','position','line','lean','line_from'):
            if raw.get(f)!=r.get(f):raise ValueError('frozen original metadata conflict')
        actuals={v['actual']for _,v in vv if v.get('actual')is not None};positions={v.get('position')for _,v in vv};populations={v.get('population')for _,v in vv}
        state='IDENTITY_UNRESOLVED'if key is None else'RETAINED_LABEL_UNRESOLVED'if not vv else'CONFLICTING_RETAINED_VIEWS'if len(actuals)>1 or positions!={r['position']}or len(populations)>1 else'SUPPORTED'if any(v.get('status')=='SUPPORTED'and v.get('actual')is not None for _,v in vv)else vv[0][1].get('status','RETAINED_LABEL_UNRESOLVED')
        actual=next(iter(actuals))if state=='SUPPORTED'else None
        if actual is not None:
            if not scoring.finite(actual)or not float(actual).is_integer():raise ValueError('noninteger ordinary label')
            actual=int(actual)
        points={}
        for field,product in [('adjusted_projection','website_point'),('raw_projection','provider_point')]:
            point=raw.get(field);saved={v['prediction']for _,v in vv if v.get('product_id')==product and v.get('prediction')is not None}
            ok=scoring.finite(point)and saved=={point}
            # An unresolved outcome identity cannot erase a point retained in
            # the original source or turn a difficult case into an abstention.
            source_only=scoring.finite(point)and not vv
            points[field]=point if ok or source_only else None
            point_states[field+':'+('PARITY'if ok else'ORIGINAL_SOURCE_ONLY'if source_only else'MISSING_OR_CONFLICT')]+=1
        pop=next(iter(populations))if len(populations)==1 else None;member=member_map.get((*key,pop))if key else None
        qualified=bool(member and scoring.finite(member.get('ranking_cutoff'))and member['ranking_cutoff']<=pilot.aware(PROOF).timestamp()and(member.get('latest_available')is None or member['latest_available']<member['ranking_cutoff']))
        cohorts=list(member['cohorts'])if qualified else []
        result.append(dict(source_row_index=r['source_row_index'],source_player_id=r['player_id'],source_game_id=r['game_id'],game_id=games.get(str(r['game_id']),{}).get('game_id'),player_id=key[1]if key else None,target=r['category'],population=pop,position=r['position'],line=r['line'],line_from=r['line_from'],
            side=r.get('lean'),original_side=r.get('lean'),top_over=r.get('top_over'),top_under=r.get('top_under'),kickoff=r['kickoff'],season=2026,week=7,
            actual=actual,label_state=state,participation='VERIFIED_PLAYED_POSITIVE_PHYSICAL'if state=='SUPPORTED'else'UNKNOWN',prediction=points['adjusted_projection'],raw_prediction=points['raw_projection'],
            source_cohorts=cohorts,cohort_state='MATCHED_RECONSTRUCTED_PRIOR_CLOCK'if qualified else'MEMBERSHIP_UNKNOWN',ranking_cutoff=member.get('ranking_cutoff')if qualified else None,
            price=None,probability=None,server_retained_by=PROOF,recorded_capture='2026-10-22T17:55:30Z',retained_reference_indices=[i for i,_ in vv]))
        states[state]+=1
    return result,dict(label_state_counts=dict(states),point_parity_counts=dict(point_states),metadata_matched_reference_views_decoded=decoded)


def grade(records):
    out=[]
    for r in records:
        for strategy in STRATEGIES:
            point=r['raw_prediction']if strategy==RAW else r['prediction']
            side=r['side']if strategy=='original'else'over'if strategy=='alwaysOver'else'under'if strategy=='alwaysUnder'else None if point is None else('over'if scoring.exact_decimal(point)>scoring.exact_decimal(r['line'])else'under'if scoring.exact_decimal(point)<scoring.exact_decimal(r['line'])else None)
            state='ABSTAIN'if side is None else'UNKNOWN_PARTICIPATION'if r['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL'else'MISSING_ACTUAL'if r['actual']is None else scoring.threshold_crossing(r['actual'],r['line'],side,target=r['target'])
            settled=scoring.grade_settlement(r['actual'],r['line'],side,target=r['target'],
                participation='PLAYED'if r['participation']=='VERIFIED_PLAYED_POSITIVE_PHYSICAL'else'UNKNOWN',
                outcome_state='final',contract=None,outcome_contract=None,decimal_odds=None)if side else dict(state='NOT_SELECTED')
            out.append(dict(r,strategy=strategy,selected_side=side,statistical_state=state,settlement_state=settled['state'],ranking_point=point,net_return=None))
    return out


def cohort_names(records):
    base=['ALL','ORIGINAL_SELECTED','ORIGINAL_ABSTAINED','position:QB','position:RB','position:WR','position:TE','source:dk','source:sleeper','original_top_over','original_top_under','cohort_unknown']
    return base+['reconstructed:'+c for c in sorted({c for r in records for c in r['source_cohorts']if c!='all'})]


def in_cohort(r,cohort):
    if cohort=='ALL':return True
    if cohort=='ORIGINAL_SELECTED':return r['original_side']in('over','under')
    if cohort=='ORIGINAL_ABSTAINED':return r['original_side']not in('over','under')
    if cohort.startswith('position:'):return r['position']==cohort.split(':',1)[1]
    if cohort.startswith('source:'):return r['line_from']==cohort.split(':',1)[1]
    if cohort=='original_top_over':return bool(r['top_over'])
    if cohort=='original_top_under':return bool(r['top_under'])
    if cohort=='cohort_unknown':return not r['source_cohorts']
    return cohort.split(':',1)[1]in r['source_cohorts']


def rank_key(r):
    gap=abs(scoring.exact_decimal(r['ranking_point'])-scoring.exact_decimal(r['line']))
    return(-gap,r['game_id']or'',r['player_id']or'',r['target'],str(r['line']),r['source_row_index'])


def score_row(rr,pool,*,strategy,target,cohort,side,K=None,rank_scope=None,rank_eligible=None):
    counts=collections.Counter(r['statistical_state']for r in rr);w,l=counts['WIN'],counts['LOSS'];n=w+l
    selected=len(rr);abstained=sum(r['selected_side']is None for r in pool)
    ident=[VERSION,strategy,target,cohort,side,K,rank_scope]
    return dict(record_id='FULL-PROP-'+hashlib.sha256(canonical(ident)).hexdigest()[:24],record_kind='prop_selection_evaluation',procedure_id=VERSION+':'+strategy,product_id='recorded_threshold_decision',
        strategy=strategy,target=target,side=side,cohort_id=cohort,K=K,rank_scope=rank_scope,time_panel_id='2026_W7_FULL_PROVIDER_LABELLED_462_13_GAMES',season_alias_of_week_view=False,
        season=2026,week=7,evaluation_seasons=[2026],evaluation_weeks=[7],period='full_game',season_type='REG',statistic_period='full_game',overtime=True,
        horizon_id='SERVER_RETAINED_BEFORE_LATER_T90_QUOTE_VINTAGE_UNVERIFIED',evaluation_panel_id=VERSION,n=n,forecast_rows=selected,
        unique_games=len({r['game_id']for r in rr if r['game_id']}),unique_players=len({r['player_id']for r in rr if r['player_id']}),unique_player_games=len({(r['game_id'],r['player_id'])for r in rr if r['player_id']}),
        query_membership_sha256=hashlib.sha256(canonical(sorted(r['source_row_index']for r in rr))).hexdigest(),
        selection_metrics=dict(WIN=w,LOSS=l,PUSH=counts['PUSH'],status_counts={s:counts[s]for s in('WIN','LOSS','PUSH','UNKNOWN_PARTICIPATION','MISSING_ACTUAL','PENDING','VOID','UNRESOLVED_CONTRACT')},
            hit_rate=w/n if n else None,denominators=dict(outer_rows=selected,decided=n,supported_threshold_outcomes=n+counts['PUSH'],unresolved=selected-n-counts['PUSH']),
            selection_pool_count=len(pool),eligible_rank_pool_n=rank_eligible if K is not None else len(pool),abstentions_outside_selected_partition=abstained,
            selection_coverage=selected/(rank_eligible if K is not None else len(pool))if(rank_eligible if K is not None else len(pool))else None,
            bookmaker_settlement_status_counts={'UNRESOLVED_CONTRACT':selected},probability_scores=dict(brier=None,log_loss=None,reason='NO_QUALIFIED_LINE_PROBABILITY'),
            returns=dict(net=None,ROI=None,drawdown=None,reason='NO_QUALIFIED_PRICE_OR_BOOK_SETTLEMENT'),game_uncertainty=pilot.bootstrap(rr)),
        selection_loss_rate=l/n if n else None,mae=None,mse=None,brier=None,log_loss=None,evidence='REPRODUCED_FROM_RETAINED_SOURCE_NEW_RETROSPECTIVE_RULES',
        selection_evidence='ORIGINAL_RECORDED_SELECTION'if strategy=='original'and K is None else'RETROSPECTIVE_RULE_REPLAY',
        source_vintage='SERVER_BOUND_ORIGINAL_THRESHOLDS_AND_POINTS;CURRENT_VINTAGE_QUALIFIED_LABELS',settlement_status='UNRESOLVED_CONTRACT',
        null_reason='NO_SELECTED_CASES'if not selected else'NO_DECIDED_CASES'if not n else None)


def project(grades,ks):
    scores=[];checks=[];cohorts=cohort_names(grades)
    for strategy in STRATEGIES:
        source=[r for r in grades if r['strategy']==strategy]
        for target in('ALL',)+TARGETS:
            tt=[r for r in source if target=='ALL'or r['target']==target]
            for cohort in cohorts:
                pool=[r for r in tt if in_cohort(r,cohort)];selected=[r for r in pool if r['selected_side']]
                views=[]
                for side in('over','under','Combined'):
                    rr=[r for r in selected if side=='Combined'or r['selected_side']==side]
                    v=score_row(rr,pool,strategy=strategy,target=target,cohort=cohort,side=side);scores.append(v);views.append(v)
                check_triplet(views);checks.append([strategy,target,cohort,None,None])
    lookup={(r['strategy'],r['source_row_index']):r for r in grades}
    for k in ks:
        pool=[r for r in grades if r['strategy']==k['strategy']and r['target']==k['target']]
        chosen=[lookup[k['strategy'],i]for i in k['source_row_indices']];views=[]
        for side in('over','under','Combined'):
            rr=[r for r in chosen if side=='Combined'or r['selected_side']==side]
            v=score_row(rr,pool,strategy=k['strategy'],target=k['target'],cohort='RETROSPECTIVE_TOP_PICK_SUBSET',side=side,K=k['K'],rank_scope=k['rank_scope'],rank_eligible=k['eligible_pool_n']);scores.append(v);views.append(v)
        check_triplet(views);checks.append([k['strategy'],k['target'],'RETROSPECTIVE_TOP_PICK_SUBSET',k['K'],k['rank_scope']])
    return scores,checks


def check_triplet(views):
    assert {r['side']for r in views}=={'over','under','Combined'}
    a,b,c=views
    assert c['forecast_rows']==a['forecast_rows']+b['forecast_rows']and c['n']==a['n']+b['n']
    for s in c['selection_metrics']['status_counts']:
        assert c['selection_metrics']['status_counts'][s]==a['selection_metrics']['status_counts'][s]+b['selection_metrics']['status_counts'][s]


def run(*,public,private,execution_released=False):
    if not execution_released:raise ValueError('explicit task execution release required')
    out,priv=Path(public),Path(private);p=json.loads((out/'FROZEN_PROTOCOL.json').read_bytes());start=time.monotonic()
    if p['code_sha256']!=sha(__file__)or p['core_sha256']!=sha(scoring.__file__)or p['bootstrap_helper_sha256']!=sha(pilot.__file__):raise ValueError('frozen code changed')
    def guard():
        if time.monotonic()-start>180 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('bounded fullpool resource limit')
    write(out/'EXECUTION_REGISTRATION.json',dict(protocol_sha256=sha(out/'FROZEN_PROTOCOL.json'),actual_started_at=now(),new_fits=0,new_forecasts=0))
    rows,joined_counts=load_joined(out,priv,p);guard()
    with(priv/'JOINED_ROWS.json.gz').open('xb')as f:f.write(gzip.compress(canonical(dict(rows=rows)),mtime=0))
    # Freeze K memberships from selected directions and point/line metadata before
    # any new threshold is graded. Selection does not inspect actual/participation.
    metadata=[]
    for r in rows:
        for strategy in STRATEGIES:
            point=r['raw_prediction']if strategy==RAW else r['prediction']
            side=r['side']if strategy=='original'else'over'if strategy=='alwaysOver'else'under'if strategy=='alwaysUnder'else None if point is None else('over'if scoring.exact_decimal(point)>scoring.exact_decimal(r['line'])else'under'if scoring.exact_decimal(point)<scoring.exact_decimal(r['line'])else None)
            metadata.append(dict(r,strategy=strategy,selected_side=side,ranking_point=point))
    ks=[]
    for strategy in STRATEGIES:
        for target in TARGETS:
            for scope in('Combined','over','under'):
                pool=[r for r in metadata if r['strategy']==strategy and r['target']==target and r['selected_side']and r['ranking_point']is not None and(scope=='Combined'or r['selected_side']==scope)]
                ordered=sorted(pool,key=rank_key)
                for K in(6,10,20):ks.append(dict(strategy=strategy,target=target,rank_scope=scope,K=K,eligible_pool_n=len(pool),source_row_indices=[r['source_row_index']for r in ordered[:K]]))
    with(priv/'FROZEN_K_MEMBERSHIPS.json.gz').open('xb')as f:f.write(gzip.compress(canonical(dict(rows=ks)),mtime=0))
    write(out/'K_MEMBERSHIP_FREEZE_RECEIPT.json',dict(actual_frozen_at=now(),before_new_threshold_grades=True,sha256=sha(priv/'FROZEN_K_MEMBERSHIPS.json.gz'),lists=len(ks),selection='noactual/participationfilter;per-categoryretrospectiveonly'))
    grades=grade(rows);guard();scores,checks=project(grades,ks);guard()
    with(priv/'GRADED_ROWS.json.gz').open('xb')as f:f.write(gzip.compress(canonical(dict(rows=grades)),mtime=0))
    if sum(f.stat().st_size for f in priv.iterdir()if f.is_file())>8388608:raise RuntimeError('new private cap')
    write(out/'SCORES.json',scores);write(out/'SIDE_RECONCILIATION.json',dict(score_sha256=sha(out/'SCORES.json'),checks=checks))
    unavailable=[dict(target=t,strategy=s,side=d,state='UNAVAILABLE',selected=None,n=None,wins=None,losses=None,hit_rate=None,reason='NO_MATCHING_TARGET_THRESHOLD_CONTRACT_IN_SOURCE')for t in('anytime_td','nick-chart-ppr-v1')for s in STRATEGIES for d in('over','under','Combined')]
    write(out/'UNAVAILABLE_CELLS.json',unavailable)
    summary=[r for r in scores if r['target']=='ALL'and r['cohort_id']=='ALL']
    receipt=dict(state='COMPLETE_FULL_PROVIDER_LABELLED_THRESHOLD_POOL',protocol_id=VERSION,completed_at_utc=now(),protocol_sha256=sha(out/'FROZEN_PROTOCOL.json'),code_sha256=sha(__file__),core_sha256=sha(scoring.__file__),
        source_rows=462,source_provenance=dict(dk=441,sleeper=21),original_selected=285,original_abstained=177,joined_counts=joined_counts,
        strategies=len(STRATEGIES),strategy_grade_views=len(grades),canonical_score_views=len(scores),side_triplets=len(checks),topK_lists=len(ks),
        public_score_sha256=sha(out/'SCORES.json'),private_grade_sha256=sha(priv/'GRADED_ROWS.json.gz'),private_joined_sha256=sha(priv/'JOINED_ROWS.json.gz'),
        new_fits=0,new_forecasts=0,new_inference_calls=0,new_current2026_week8_outcomes_read=0,
        resource=dict(wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=1),
        all_method_sides=[dict(strategy=r['strategy'],side=r['side'],selected=r['forecast_rows'],n=r['n'],wins=r['selection_metrics']['WIN'],losses=r['selection_metrics']['LOSS'],hit_rate=r['selection_metrics']['hit_rate'],unknown=r['selection_metrics']['status_counts']['UNKNOWN_PARTICIPATION'],abstained=r['selection_metrics']['abstentions_outside_selected_partition'])for r in summary])
    write(out/'RUN_RECEIPT.json',receipt);return receipt
