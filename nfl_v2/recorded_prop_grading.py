"""One-pass original-selection replay using the shared ROOT scoring engine.

No fits, new forecasts, provider requests, probability inference or wagers.
Raw graded rows stay private; all bookmaker settlements remain unqualified.
"""
from __future__ import annotations
import collections,csv,gzip,hashlib,json,math,os,resource,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from . import scoring

VERSION='v2-original-recorded-prop-panel-W7-first-score-v1'
SAVED_POINT='SAVED_POINT_DIRECTION_RETAINED_PRECISION'
STRATEGIES=('original',SAVED_POINT,'alwaysOver','alwaysUnder')
TARGETS=set(scoring.TARGETS)-{'anytime_td','nick-chart-ppr-v1'}
def now():return datetime.now(timezone.utc).isoformat()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())
def write(path,obj):
    with Path(path).open('xb')as f:f.write(canonical(obj));f.flush();os.fsync(f.fileno())
def aware(value):
    x=datetime.fromisoformat(value.replace('Z','+00:00'))
    if x.tzinfo is None or x.utcoffset()is None:raise ValueError('aware source/game clocks required')
    return x

def prepare(*,joined,expected_sha256,output,private_output,initial_protocol):
    joined,out,priv=map(Path,(joined,output,private_output))
    if out.exists()or priv.exists():raise ValueError('fresh immutable outputs required')
    if priv.resolve().is_relative_to(Path(__file__).resolve().parents[1]):raise ValueError('private grades outside publicGit required')
    if sha(joined)!=expected_sha256:raise ValueError('frozen joined input hash mismatch')
    packet=json.loads(gzip.decompress(joined.read_bytes()))
    if len(packet['rows'])!=285:raise ValueError('exact285 outer original rows required')
    # Metadata only: no threshold crossing or loss is computed in preparation.
    if any((r['season'],r['week'])!=(2026,7)for r in packet['rows']):raise ValueError('only fixed2026W7 panel admitted')
    out.mkdir(parents=True);priv.mkdir(parents=True)
    write(priv/'INPUT_BINDING_PRIVATE.json',dict(joined=str(joined)))
    p=dict(protocol_id=VERSION,registered_at_utc=now(),state='FROZEN_BEFORE_FIRST_DIRECTION_GRADES',code_sha256=sha(__file__),scoring_sha256=sha(scoring.__file__),
        joined_sha256=expected_sha256,joined_protocol_sha256=packet['protocol_sha256'],initial_protocol_sha256=sha(initial_protocol),
        private_binding_sha256=sha(priv/'INPUT_BINDING_PRIVATE.json'),strategies=list(STRATEGIES),
        saved_point_rule='Recorded original point > line OVER, < line UNDER, equality ABSTAIN; no additional V2 rounding. Shared threshold_crossing target=None accepts point means.',
        strict_P1_status='UNAVAILABLE_INTERNAL_UNROUNDED_POINT_NOT_RETAINED; original source rounds adjusted projection before retention, current code trace; do not invent lost precision.',
        selection='Exact285originalpreselectedsource rows; no outcome filter, rerank, replacement, newtopK or newmodel. Preserve unknown appearance/DNP/missing/playedzero/early exits.',
        groups=['ALL','category','original_side_fixed_pool','line_source','position','saved_top_over','saved_top_under','any_saved_top','not_saved_top'],
        side_definition='Subgroup original_side pools remain fixed for all strategies; canonical side records actual selected-direction composition, with original_side separately retained.',
        metrics='StatisticalWIN/LOSS/PUSH separate; hit_rate=WIN/(WIN+LOSS), n=WIN+LOSS; pushes/abstentions/unresolved preserveoutercoverage. Selection_loss_rate=LOSS/(WIN+LOSS). No MAE accuracy conversion.',
        settlement='Call shared grade_settlement with contract=None/outcome_contract=None. All booksettlements UNRESOLVED_CONTRACT; noDNPvoid. Prices/probabilities unqualified/null; Brier/logloss/EV/ROI/drawdown NULL.',
        uncertainty='Whole-game PCG64bootstrap500seed1703,2.5/97.5linearquantiles if>=8decidedgames; paired loss difference against original onshareddecidedcases. Singleweek intervalNULL/INSUFFICIENT_WEEK_CLUSTERS. Exposed,notselection/multiplicityadjusted.',
        budget=dict(wall_seconds=180,max_RSS_bytes=1073741824,max_private_bytes=8388608,max_rows=285,max_threads=1,new_fits=0,new_forecasts=0),
        execution='Root alone invokes run with explicit --root-execution-released after sealing; preparation is not grading.',current2026_week8_outcomes_read=0)
    write(out/'FROZEN_PROTOCOL.json',p)
    with(out/'SCORER_SOURCE_SNAPSHOT.py').open('xb')as f:f.write(Path(__file__).read_bytes())
    with(out/'ROOT_SCORING_SOURCE_SNAPSHOT.py').open('xb')as f:f.write(Path(scoring.__file__).read_bytes())
    return p

def choose_side(r,strategy):
    if strategy=='original':return r['side']
    if strategy=='alwaysOver':return'over'
    if strategy=='alwaysUnder':return'under'
    if strategy not in(SAVED_POINT,'P1'):raise ValueError('unregistered strategy')
    if r.get('prediction')is None:return None
    crossing=scoring.threshold_crossing(r['prediction'],r['line'],'over')
    return'over'if crossing=='WIN'else'under'if crossing=='LOSS'else None

def grade_records(rows):
    records=[]
    for r in rows:
        for strategy in STRATEGIES:
            side=choose_side(r,strategy);part=r['participation']
            if side is None:state='ABSTAIN'
            elif part in('UNKNOWN','APPEARANCE_UNKNOWN'):state='UNKNOWN_PARTICIPATION'
            elif part=='DNP':state='DNP'
            elif r.get('outcome_state')=='pending':state='PENDING'
            elif r['actual']is None:state='MISSING_ACTUAL'
            elif part not in('PLAYED','VERIFIED_PLAYED_POSITIVE_PHYSICAL'):state='UNKNOWN_PARTICIPATION'
            else:state=scoring.threshold_crossing(r['actual'],r['line'],side,target=r['target'])
            settled=scoring.grade_settlement(r['actual'],r['line'],side,target=r['target'],participation='PLAYED'if part in('PLAYED','VERIFIED_PLAYED_POSITIVE_PHYSICAL')else'DNP'if part=='DNP'else'UNKNOWN',outcome_state=r.get('outcome_state','final'),contract=None,outcome_contract=None,decimal_odds=None)
            records.append(dict(r,strategy=strategy,original_side=r['side'],selected_side=side,statistical_state=state,settlement_state=settled['state'],settlement_reason=settled['reason'],net_return=None))
    return records

def bootstrap(rows,baseline=None):
    if baseline is None:
        pairs=[(r,None)for r in rows if r['statistical_state']in('WIN','LOSS')]
    else:pairs=[(r,baseline[r['source_row_index']])for r in rows if r['statistical_state']in('WIN','LOSS')and baseline[r['source_row_index']]['statistical_state']in('WIN','LOSS')]
    games=sorted({r['game_id']for r,b in pairs});n=len(pairs)
    out=dict(paired_n=n if baseline is not None else None,game_clusters=len(games),replicates=500,seed=1703,week_interval=None,week_interval_status='INSUFFICIENT_WEEK_CLUSTERS',game_interval=None,game_interval_status='INSUFFICIENT_GAME_CLUSTERS',selection_limit='exposeddescriptive;notselection/multiplicityadjusted')
    if not n:return dict(out,estimate=None)
    per=collections.defaultdict(lambda:[0.,0])
    for r,b in pairs:
        value=float(r['statistical_state']=='WIN')if b is None else float(r['statistical_state']=='LOSS')-float(b['statistical_state']=='LOSS')
        per[r['game_id']][0]+=value;per[r['game_id']][1]+=1
    nums=np.asarray([per[g][0]for g in games]);dens=np.asarray([per[g][1]for g in games]);out['estimate']=float(nums.sum()/dens.sum())
    if len(games)>=8:
        draws=np.random.default_rng(1703).integers(0,len(games),size=(500,len(games)));values=nums[draws].sum(axis=1)/dens[draws].sum(axis=1)
        out.update(game_interval=[float(x)for x in np.quantile(values,[.025,.975],method='linear')],game_interval_status='GAME_CLUSTER_SENSITIVITY_BOOTSTRAP')
    return out

def groups(r):
    yield'ALL','ALL'
    yield'category',r['target']
    yield'original_side',r['original_side']
    yield'line_source',r['line_from']
    yield'position',r['position']
    if r['top_over']:yield'saved_top_over','true'
    if r['top_under']:yield'saved_top_under','true'
    yield('any_saved_top','true')if r['top_over']or r['top_under']else('not_saved_top','true')

def aggregate(records):
    index=collections.defaultdict(list);baseline={r['source_row_index']:r for r in records if r['strategy']=='original'}
    for r in records:
        for dim,value in groups(r):index[r['strategy'],dim,value].append(r)
    out=[]
    for (strategy,dim,value),rr in sorted(index.items()):
        counts=collections.Counter(r['statistical_state']for r in rr);win,loss,push=counts['WIN'],counts['LOSS'],counts['PUSH'];n=win+loss;settlement=collections.Counter(r['settlement_state']for r in rr);directions={r['selected_side']for r in rr}
        actual_side=next(iter(directions))if len(directions)==1 else'mixed';queryhash=hashlib.sha256(canonical(sorted(r['source_row_index']for r in rr))).hexdigest()
        sm=dict(status_counts=dict(counts),WIN=win,LOSS=loss,PUSH=push,hit_rate=win/n if n else None,
            denominators=dict(outer_rows=len(rr),decided=n,supported_threshold_outcomes=n+push,abstained=counts['ABSTAIN'],unresolved=len(rr)-n-push-counts['ABSTAIN']),
            bookmaker_settlement_status_counts=dict(settlement),probability_scores=dict(brier=None,log_loss=None,reason='NO_QUALIFIED_FORECAST_PROBABILITIES'),
            returns=dict(net=None,ROI=None,drawdown=None,reason='NO_VERIFIED_PRICE_OR_SETTLEMENT_CONTRACT'),
            game_uncertainty=bootstrap(rr),paired_vs_original=bootstrap(rr,baseline))
        out.append(dict(record_id='PROP-'+hashlib.sha256(canonical([VERSION,strategy,dim,value])).hexdigest()[:24],record_kind='prop_selection_evaluation',procedure_id=VERSION+':'+strategy,
            product_id='recorded_threshold_decision',strategy=strategy,target=value if dim=='category'else'ALL',side=actual_side or'ABSTAIN',original_side=value if dim=='original_side'else'ALL',
            line_source=value if dim=='line_source'else'ALL',position=value if dim=='position'else'ALL',group_id=dim+':'+value,grouping_dimension=dim,
            horizon_id='SERVER_RETAINED_BEFORE_T90_INPUT_QUOTE_VINTAGE_UNVERIFIED',season=2026,week=7,period='REG',evaluation_panel_id=VERSION,
            n=n,forecast_rows=len(rr),unique_games=len({r['game_id']for r in rr}),unique_player_games=len({(r['game_id'],r['player_id'])for r in rr}),
            query_membership_sha256=queryhash,selection_metrics=sm,selection_loss_rate=loss/n if n else None,mae=None,mse=None,brier=None,log_loss=None,
            evidence='REPRODUCED_FROM_DATA',source_vintage='ORIGINAL_RETAINED_SELECTION_WITH_QUALIFIED_CURRENT_VINTAGE_LABELS',settlement_status='UNRESOLVED_CONTRACT'))
    return out

def run(*,output,private_output,root_execution_released=False):
    if not root_execution_released:raise ValueError('explicit ROOT execution release required')
    out,priv=map(Path,(output,private_output));p=load(out/'FROZEN_PROTOCOL.json');start=time.monotonic()
    if p['code_sha256']!=sha(__file__)or p['scoring_sha256']!=sha(scoring.__file__):raise ValueError('sealed scorer or ROOT engine changed')
    if sha(priv/'INPUT_BINDING_PRIVATE.json')!=p['private_binding_sha256']:raise ValueError('private input binding changed')
    path=Path(load(priv/'INPUT_BINDING_PRIVATE.json')['joined'])
    if sha(path)!=p['joined_sha256']:raise ValueError('joined input changed')
    packet=json.loads(gzip.decompress(path.read_bytes()));rows=packet['rows']
    if packet['protocol_sha256']!=p['joined_protocol_sha256']or len(rows)!=285:raise ValueError('frozen join protocol/outer count mismatch')
    seen=set()
    for r in rows:
        if(r['season'],r['week'])!=(2026,7)or r['target']not in TARGETS or r['side']not in('over','under'):raise ValueError('wrong panel/target/originalside')
        if r['source_row_index']in seen:raise ValueError('duplicate frozen source row')
        seen.add(r['source_row_index'])
        if not scoring.finite(r['line'])or r['point_state']!='EXACT_ORIGINAL_AND_RETAINED_PARITY':raise ValueError('invalid recorded line/point parity')
        if r['price']is not None or r['probability']is not None:raise ValueError('this first packet admits no prices/probabilities')
        if aware(r['server_retained_by']).timestamp()>=aware(r['kickoff']).timestamp()-5400:raise ValueError('server-retained T90 condition failed')
        if r['label_state']=='SUPPORTED'and(r['actual']is None or r['participation']!='VERIFIED_PLAYED_POSITIVE_PHYSICAL'):raise ValueError('unsupported label/appearance combination')
        if r['participation']=='UNKNOWN'and r['actual']is not None:raise ValueError('unknown participation cannot borrow a numeric outcome')
    def guard():
        if time.monotonic()-start>180 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('BOUNDED_FIRST_SCORECARD_RESOURCE_LIMIT')
    write(out/'EXECUTION_REGISTRATION.json',dict(protocol_sha256=sha(out/'FROZEN_PROTOCOL.json'),actual_started_at_utc=now(),root_execution_released=True,new_fits=0,new_forecasts=0))
    guard();records=grade_records(rows);guard();scores=aggregate(records);guard()
    raw=canonical(dict(schema=VERSION,rows=records));blob=gzip.compress(raw,mtime=0)
    if sum(f.stat().st_size for f in priv.rglob('*')if f.is_file())+len(blob)>8388608:raise RuntimeError('PRIVATE_OUTPUT8MIB_LIMIT')
    target=priv/'GRADED_ROWS.json.gz'
    with target.open('xb')as f:f.write(blob);f.flush();os.fsync(f.fileno())
    if target.read_bytes()!=blob:raise ValueError('private grade row readback failed')
    guard();write(out/'SCORES.json',scores);guard()
    receipt=dict(protocol_id=VERSION,state='COMPLETE_FIRST_ORIGINAL_SELECTION_SCORECARD',actual_completed_at_utc=now(),protocol_sha256=sha(out/'FROZEN_PROTOCOL.json'),
        source_joined_sha256=p['joined_sha256'],ROOT_scoring_sha256=p['scoring_sha256'],scorer_sha256=p['code_sha256'],outer_original_rows=len(rows),strategy_grade_views=len(records),canonical_score_views=len(scores),
        score_sha256=sha(out/'SCORES.json'),private_grade_packet=dict(artifact_id='V2-PROP-W7-FIRST-GRADES-V1',sha256=sha(target),bytes=target.stat().st_size),
        all_four_strategy_summary=[dict(strategy=r['strategy'],n=r['n'],selection_metrics=r['selection_metrics'],selection_loss_rate=r['selection_loss_rate'])for r in scores if r['group_id']=='ALL:ALL'],
        resource=dict(wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=1),new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0,
        settlement='UNRESOLVED_CONTRACT_FOR_ALL; statisticalcrossingsarenotvenueprofit')
    write(out/'RUN_RECEIPT.json',receipt);return receipt
