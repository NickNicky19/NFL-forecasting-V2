"""Actual-side and predeclared top-K projections of retained grades only.

No threshold regrading, label/provider reads, fitting or new forecasts. The
285-case conditional panel and full-feed selection denominator stay distinct.
"""
from __future__ import annotations
import collections,gzip,hashlib,json,resource,time
from datetime import datetime,timezone
from pathlib import Path
from . import recorded_prop_grading as first,scoring

VERSION='v2-recorded-prop-actual-side-and-retro-K-projection-v2'
UNSUPPORTED_TARGETS=('anytime_td','nick-chart-ppr-v1')
TARGETS=tuple(t for t in scoring.TARGETS if t not in UNSUPPORTED_TARGETS)
SIDES=('over','under','Combined')
PERIODS=('2026_W7_13_GAME_SLICE','2026_SEASON_SUPPORTED_W7_ONLY_ALIAS')
K_VALUES=(6,10,20)
RANK_SCOPES=('Combined','over','under')
canonical=first.canonical;sha=first.sha;now=first.now;load=first.load;write=first.write

def exact_rank(r):
    gap=abs(scoring.exact_decimal(r['prediction'])-scoring.exact_decimal(r['line']))
    return(-gap,r['game_id'],r['player_id'],r['target'],str(scoring.exact_decimal(r['line'])),r['selected_side']or'',r['source_row_index'])

def select_k(rows,scope,k):
    eligible=[r for r in rows if r['selected_side']in('over','under')and(scope=='Combined'or r['selected_side']==scope)]
    # Outcomes, participation and recorded wins are deliberately unused here.
    return sorted(eligible,key=exact_rank)[:k],len(eligible)

def make_memberships(records):
    by=collections.defaultdict(list)
    for r in records:by[r['strategy'],r['target']].append(r)
    out=[]
    for strategy in first.STRATEGIES:
        for target in TARGETS:
            for scope in RANK_SCOPES:
                for k in K_VALUES:
                    selected,n=select_k(by[strategy,target],scope,k)
                    out.append(dict(strategy=strategy,target=target,rank_scope=scope,K=k,eligible_pool_n=n,
                        source_row_indices=[r['source_row_index']for r in selected],
                        identity='NEW_RETRO_SUBSET_WITHIN_ORIGINAL_SELECTED_PANEL;notoriginalissuedK',
                        rank='descendingabs(savedpoint-line),thenstablegame/player/target/line/selectedside/sourceindex;retainedprecisiononly'))
    return out

def normalize_universe(coverage,census):
    full={r['target']:r['eligible_original_source_rows']for r in coverage['target_coverage']};selected={r['target']:r['frozen_selected_rows']for r in coverage['target_coverage']}
    providers=collections.Counter();synthetic=collections.Counter()
    for r in census['target_cross_states']:
        if r['finite_line']and r['adjusted_point_present']:(providers if r['line_from']in('dk','sleeper')else synthetic)[r['target']]+=r['n']
    if sum(full.values())!=1419 or sum(selected.values())!=285 or sum(providers.values())!=462 or sum(synthetic.values())!=957:raise ValueError('exactfullfeed/provider/generatedmetadata required')
    return dict(eligible_universe_count=1419,selection_pool_count=285,eligible_universe_by_target=full,selected_by_target=selected,provider_threshold_by_target=dict(providers),synthetic_threshold_by_target=dict(synthetic))

def prepare(*,graded,source_receipt,cohort_tags,universe,threshold_census,output,private_output):
    out,priv=Path(output),Path(private_output)
    if out.exists()or priv.exists():raise ValueError('fresh immutable side projection required')
    if priv.resolve().is_relative_to(Path(__file__).resolve().parents[1]):raise ValueError('private memberships outside Git required')
    receipt=load(source_receipt)
    if sha(graded)!=receipt['private_grade_packet']['sha256']:raise ValueError('retained grade packet source hash mismatch')
    packet=json.loads(gzip.decompress(Path(graded).read_bytes()));records=packet['rows']
    if packet['schema']!=first.VERSION or len(records)!=1140 or set(r['strategy']for r in records)!=set(first.STRATEGIES):raise ValueError('exact1140 retained four-strategy grades required')
    if any((r['season'],r['week'])!=(2026,7)for r in records):raise ValueError('no other season/week outcomes admitted')
    tag_packet=json.loads(gzip.decompress(Path(cohort_tags).read_bytes()))if str(cohort_tags).endswith('.gz')else load(cohort_tags)
    universe_packet=normalize_universe(load(universe),load(threshold_census))
    # Only recorded point/line/direction metadata enter this pre-score freeze.
    memberships=make_memberships(records)
    out.mkdir(parents=True);priv.mkdir(parents=True)
    write(priv/'INPUT_BINDINGS_PRIVATE.json',dict(graded=str(graded),cohort_tags=str(cohort_tags),universe=str(universe),threshold_census=str(threshold_census)))
    body=canonical(dict(schema=VERSION,rows=memberships));blob=gzip.compress(body,mtime=0)
    with(priv/'FROZEN_K_MEMBERSHIPS.json.gz').open('xb')as f:f.write(blob)
    p=dict(protocol_id=VERSION,state='FROZEN_K_MEMBERSHIPS_BEFORE_SUBSET_METRICS',registered_at_utc=now(),code_sha256=sha(__file__),
        first_scorer_sha256=sha(first.__file__),ROOT_scoring_sha256=sha(scoring.__file__),source_grade_sha256=sha(graded),source_grade_receipt_sha256=sha(source_receipt),
        source_grade_protocol_sha256=receipt['protocol_sha256'],private_binding_sha256=sha(priv/'INPUT_BINDINGS_PRIVATE.json'),cohort_tags_sha256=sha(cohort_tags),universe_metadata_sha256=sha(universe),threshold_census_sha256=sha(threshold_census),
        frozen_memberships_sha256=sha(priv/'FROZEN_K_MEMBERSHIPS.json.gz'),strategies=list(first.STRATEGIES),targets=list(TARGETS),sides=list(SIDES),time_panels=list(PERIODS),
        side_partition='Actual selected direction. Combined=over+under for every W/L/push/unknown count; abstentions remain outside selected-side partition with outerpool coverage, never counted as wagers or losses.',
        population='Controls evaluated ONLY on original preselected285, not all1419. Fullforecastfeed1419=462provider-labelledfinite-thresholdrows+957site-generatedrows, NOTauthenticpricedofferuniverse. Originalfullfeedcoverage285/1419 and provider-thresholdcoverage285/462 distinct;1134nooriginalside remain known original abstentions. Category denominators use frozenmetadata; subgroup universe unavailable remainsnull.',
        topK='K6/10/20 PER CATEGORY and strategy; separately Combined/overonly/underonly ranked candidatepools. Rankabs(savedpoint-line) at retainedprecision, stablecanonicalties. Unknown/DNP/missing graded outcomes do not remove rows from ranking. NEW_RETRO_SUBSET, not originalissuedK or full14game/fullweek selection. No cross-category gap rank.',
        time_scope='Week7partial13game source slice. Season2026view is EXACTsameW7rows alias, not season-to-date/fullseason/newobservations.',
        cohorts='Existing frozen reconstruction tags/position/originalsavedtopflags. Prior-workload membership reconstructed and actuallyfrozenOct30; NOTauthenticoriginalstarlist. Missingtags remain outer coverage.',
        zero='Emit every supported strategy/category/actualside/cohort/timecell including legitimateemptyN/A. Chart/ATDUNAVAILABLE_CELLS keptSEPARATEfromcanonicalSCORES, counts/ratesNULL notfabricatedzero.',
        probability_returns='AlwaysNULL: source has no qualifiedprobabilities/prices/booksettlement. Statistical direction grade reuse only.',
        budget=dict(wall_seconds=180,max_RSS_bytes=1073741824,max_private_bytes=8388608,max_public_bytes=67108864,max_threads=1,new_fits=0,new_forecasts=0,new_threshold_grades=0),
        root_execution_required=True,current2026_week8_outcomes_read=0)
    write(out/'FROZEN_PROTOCOL.json',p)
    with(out/'PROJECTION_SOURCE_SNAPSHOT.py').open('xb')as f:f.write(Path(__file__).read_bytes())
    return p

def tag_rows(packet):
    rows=packet['rows']if isinstance(packet,dict)else packet
    lookup={}
    for r in rows:
        i=r['source_row_index']
        if i in lookup:raise ValueError('duplicate source cohort tag')
        lookup[i]=dict(r,cohorts=r.get('source_cohorts',r.get('cohorts',[])))
    return lookup

def cohort_list(tags):
    inherited=sorted({c for r in tags.values()for c in r.get('cohorts',[])if c!='all'})
    return ['ALL']+['position:'+p for p in('QB','RB','WR','TE')]+['original_saved_top_over','original_saved_top_under','any_original_saved_top','not_original_saved_top','cohort_unavailable']+['reconstructed:'+c for c in inherited]

def in_cohort(r,name,tags):
    if name=='ALL':return True
    if name.startswith('position:'):return r['position']==name.split(':',1)[1]
    if name=='original_saved_top_over':return bool(r['top_over'])
    if name=='original_saved_top_under':return bool(r['top_under'])
    if name=='any_original_saved_top':return bool(r['top_over']or r['top_under'])
    if name=='not_original_saved_top':return not(r['top_over']or r['top_under'])
    tag=tags.get(r['source_row_index'])
    if name=='cohort_unavailable':return tag is None or not tag.get('cohorts')
    return bool(tag and name.split(':',1)[1]in tag.get('cohorts',[]))

def summarize(rr,*,source_pool,universe_n,strategy,target,side,cohort,time_panel,rank_scope=None,K=None,rank_pool_n=None,provider_n=None,synthetic_n=None):
    counts=collections.Counter(r['statistical_state']for r in rr);wins,losses,pushes=counts['WIN'],counts['LOSS'],counts['PUSH'];n=wins+losses;outer=len(rr)
    reason='UNSUPPORTED_SOURCE_TARGET_CONTRACT'if target in('anytime_td','nick-chart-ppr-v1')else'NO_SELECTED_CASES_IN_SIDE_COHORT'if not outer else'NO_DECIDED_CASES'if not n else None
    group=dict(cohort=cohort,rank_scope=rank_scope,K=K)
    rid='PROP-SIDE-'+hashlib.sha256(canonical([VERSION,strategy,target,side,time_panel,group])).hexdigest()[:24]
    metrics=dict(status_counts={s:counts[s]for s in('WIN','LOSS','PUSH','UNKNOWN_PARTICIPATION','MISSING_ACTUAL','DNP','PENDING','ABSTAIN')},WIN=wins,LOSS=losses,PUSH=pushes,hit_rate=wins/n if n else None,
        denominators=dict(outer_rows=outer,decided=n,supported_threshold_outcomes=n+pushes,unresolved=outer-n-pushes),
        full_forecast_feed_count=universe_n,provider_labelled_finite_threshold_count=provider_n,site_generated_threshold_count=synthetic_n,authentic_offer_universe_count=None,selection_pool_count=len(source_pool),
        original_fullfeed_selected_count=285,original_fullfeed_eligible_count=1419,original_fullfeed_abstentions=1134,original_fullfeed_coverage=285/1419,
        original_provider_threshold_selected_count=285,original_provider_threshold_count=462,original_provider_threshold_abstentions=177,original_provider_threshold_coverage=285/462,
        conditional_selection_coverage=outer/len(source_pool)if source_pool else None,
        coverage_scope='conditionaloriginal285panel;universegroupmetadataonly;neverP1evaluatedonall1419',
        abstentions_outside_selected_partition=sum(r['selected_side']not in('over','under')for r in source_pool),
        bookmaker_settlement_status_counts={'UNRESOLVED_CONTRACT':outer},probability_scores=dict(brier=None,log_loss=None,reason='NO_QUALIFIED_PROBABILITY'),
        returns=dict(net=None,ROI=None,drawdown=None,reason='NO_VERIFIED_PRICE_OR_SETTLEMENT'),game_uncertainty=first.bootstrap(rr))
    if rank_scope is not None:metrics.update(K=K,rank_scope=rank_scope,eligible_rank_pool_n=rank_pool_n,selection_identity='NEW_RETRO_SUBSET_WITHIN_ORIGINAL_SELECTED_PANEL_NOT_ORIGINAL_ISSUED_K')
    return dict(record_id=rid,record_kind='prop_selection_evaluation',procedure_id=first.VERSION+':'+strategy,product_id='recorded_threshold_decision',strategy=strategy,target=target,side=side,
        actual_preselected_side=side,group_id=cohort+(':'+str(rank_scope)+':K'+str(K)if K is not None else''),cohort_id=cohort,rank_scope=rank_scope,K=K,
        horizon_id='SERVER_RETAINED_BEFORE_T90_INPUT_QUOTE_VINTAGE_UNVERIFIED',time_panel_id=time_panel,season=2026,week=7 if time_panel==PERIODS[0]else'SUPPORTED_W7_ONLY',
        evaluation_seasons=[2026],evaluation_weeks=[7],period='REG',evaluation_panel_id=VERSION,source_panel='PARTIAL13GAME_W7_ORIGINAL_SELECTED285',
        season_alias_of_week_view=time_panel==PERIODS[1],n=n,forecast_rows=outer,unique_games=len({r['game_id']for r in rr}),
        query_membership_sha256=hashlib.sha256(canonical(sorted(r['source_row_index']for r in rr))).hexdigest(),selection_metrics=metrics,selection_loss_rate=losses/n if n else None,
        state='N_A'if reason else'SCORED_SUPPORTED',null_reason=reason,mae=None,mse=None,brier=None,log_loss=None,
        evidence='REPRODUCED_FROM_RETAINED_GRADES',settlement_status='UNRESOLVED_CONTRACT',source_vintage='ORIGINAL_RECORDED_SELECTION_CURRENT_VINTAGE_QUALIFIED_LABELS')

def run(*,output,private_output,root_execution_released=False):
    if not root_execution_released:raise ValueError('ROOT projection release required')
    out,priv=Path(output),Path(private_output);p=load(out/'FROZEN_PROTOCOL.json');start=time.monotonic()
    if p['code_sha256']!=sha(__file__)or p['first_scorer_sha256']!=sha(first.__file__)or p['ROOT_scoring_sha256']!=sha(scoring.__file__):raise ValueError('frozen projection/helpers changed')
    if sha(priv/'INPUT_BINDINGS_PRIVATE.json')!=p['private_binding_sha256']:raise ValueError('inputbindingchanged')
    m=load(priv/'INPUT_BINDINGS_PRIVATE.json')
    for key,field in(('graded','source_grade_sha256'),('cohort_tags','cohort_tags_sha256'),('universe','universe_metadata_sha256'),('threshold_census','threshold_census_sha256')):
        if sha(m[key])!=p[field]:raise ValueError('source bytes changed')
    if sha(priv/'FROZEN_K_MEMBERSHIPS.json.gz')!=p['frozen_memberships_sha256']:raise ValueError('frozenrankmemberships changed')
    records=json.loads(gzip.decompress(Path(m['graded']).read_bytes()))['rows'];tag_packet=json.loads(gzip.decompress(Path(m['cohort_tags']).read_bytes()))if m['cohort_tags'].endswith('.gz')else load(m['cohort_tags']);tags=tag_rows(tag_packet);universe=normalize_universe(load(m['universe']),load(m['threshold_census']));ks=json.loads(gzip.decompress((priv/'FROZEN_K_MEMBERSHIPS.json.gz').read_bytes()))['rows']
    def guard():
        if time.monotonic()-start>180 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('BOUNDED_SIDE_PROJECTION_LIMIT')
    write(out/'EXECUTION_REGISTRATION.json',dict(protocol_sha256=sha(out/'FROZEN_PROTOCOL.json'),actual_started_at_utc=now(),root_execution_released=True,new_threshold_grades=0,new_fits=0,new_forecasts=0))
    by=collections.defaultdict(list)
    for r in records:by[r['strategy']].append(r)
    scores=[];checks=[];cohorts=cohort_list(tags)
    for strategy in first.STRATEGIES:
        for target in('ALL',)+TARGETS:
            source=[r for r in by[strategy]if target=='ALL'or r['target']==target]
            universe_n=1419 if target=='ALL'else universe['eligible_universe_by_target'].get(target)
            provider_n=462 if target=='ALL'else universe['provider_threshold_by_target'].get(target,0);synthetic_n=957 if target=='ALL'else universe['synthetic_threshold_by_target'].get(target,0)
            for cohort in cohorts:
                population=[r for r in source if in_cohort(r,cohort,tags)];selected=[r for r in population if r['selected_side']in('over','under')]
                for period in PERIODS:
                    current=[]
                    for side in SIDES:
                        rr=[r for r in selected if side=='Combined'or r['selected_side']==side]
                        row=summarize(rr,source_pool=population,universe_n=universe_n if cohort=='ALL'else None,provider_n=provider_n if cohort=='ALL'else None,synthetic_n=synthetic_n if cohort=='ALL'else None,strategy=strategy,target=target,side=side,cohort=cohort,time_panel=period);scores.append(row);current.append(row)
                    for state in('WIN','LOSS','PUSH','UNKNOWN_PARTICIPATION','MISSING_ACTUAL','DNP','PENDING','ABSTAIN'):
                        assert current[2]['selection_metrics']['status_counts'][state]==sum(x['selection_metrics']['status_counts'][state]for x in current[:2])
                    checks.append(dict(strategy=strategy,target=target,cohort=cohort,time_panel=period,Combined=len(selected),Over=current[0]['forecast_rows'],Under=current[1]['forecast_rows'],abstentions=len(population)-len(selected),status='PASS_EXACT_ACTUAL_SIDE_PARTITION'));guard()
    lookup={(r['strategy'],r['source_row_index']):r for r in records}
    for membership in ks:
        strategy,target=membership['strategy'],membership['target'];source=[r for r in by[strategy]if r['target']==target];chosen=[lookup[strategy,i]for i in membership['source_row_indices']]
        for period in PERIODS:
            current=[]
            for side in SIDES:
                rr=[r for r in chosen if side=='Combined'or r['selected_side']==side]
                row=summarize(rr,source_pool=source,universe_n=universe['eligible_universe_by_target'].get(target),provider_n=universe['provider_threshold_by_target'].get(target,0),synthetic_n=universe['synthetic_threshold_by_target'].get(target,0),strategy=strategy,target=target,side=side,cohort='NEW_RETRO_PICK_SUBSET',time_panel=period,rank_scope=membership['rank_scope'],K=membership['K'],rank_pool_n=membership['eligible_pool_n']);scores.append(row);current.append(row)
            for state in('WIN','LOSS','PUSH','UNKNOWN_PARTICIPATION','MISSING_ACTUAL','DNP','PENDING','ABSTAIN'):
                assert current[2]['selection_metrics']['status_counts'][state]==sum(x['selection_metrics']['status_counts'][state]for x in current[:2])
            checks.append(dict(strategy=strategy,target=target,cohort='NEW_RETRO_PICK_SUBSET',rank_scope=membership['rank_scope'],K=membership['K'],time_panel=period,Combined=len(chosen),Over=current[0]['forecast_rows'],Under=current[1]['forecast_rows'],status='PASS_EXACT_ACTUAL_SIDE_PARTITION'))
        guard()
    body=canonical(scores)
    if len(body)>67108864:raise RuntimeError('PUBLIC64MIB_LIMIT')
    with(out/'SCORES.json').open('xb')as f:f.write(body)
    write(out/'ACTUAL_SIDE_RECONCILIATION.json',dict(source_score_sha256=sha(out/'SCORES.json'),rows=checks))
    unavailable=[dict(strategy=s,target=t,side=side,time_panel_id=period,state='UNAVAILABLE',selection_count=None,n=None,WIN=None,LOSS=None,PUSH=None,hit_rate=None,selection_loss_rate=None,
        reason='NO_QUALIFIED_NICK_CHART_THRESHOLD_SELECTION_CONTRACT;websitefptsisaseparatetarget'if t=='nick-chart-ppr-v1'else'NO_QUALIFIED_RUSH_OR_RECEIVE_TD_OFFER_AND_PROBABILITY_CONTRACT_IN_NUMERIC_PANEL')for s in first.STRATEGIES for t in UNSUPPORTED_TARGETS for side in SIDES for period in PERIODS]
    write(out/'UNAVAILABLE_CELLS.json',unavailable)
    receipt=dict(protocol_id=VERSION,state='COMPLETE_RETAINED_GRADE_SIDE_AND_RETRO_SUBSET_PROJECTION',actual_completed_at_utc=now(),protocol_sha256=sha(out/'FROZEN_PROTOCOL.json'),
        source_grade_sha256=p['source_grade_sha256'],source_strategy_grade_views=len(records),source_outer_rows=285,eligible_universe_count=1419,original_selection_coverage=285/1419,
        canonical_score_views=len(scores),actual_side_reconciliations=len(checks),frozen_topK_lists=len(ks),cohort_names=cohorts,score_sha256=sha(out/'SCORES.json'),
        resource=dict(wall_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,max_threads=1),new_threshold_grades=0,new_fits=0,new_forecasts=0,current2026_week8_outcomes_read=0)
    write(out/'RUN_RECEIPT.json',receipt);return receipt
