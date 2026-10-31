"""Finite primary P2 count closure, using retained directions and grade states."""
import argparse
import collections
import gc
import gzip
import hashlib
import json
import resource
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import recorded_prop_grading as uncertainty
from nfl_v2.shared_subgroups import canonical,now,sha,write
from tools.numerical_championship import csvwrite

VERSION='v2-W5-W7-primary-P2-retained-count-aggregation-v1'
STATES=('WIN','LOSS','PUSH','VOID','PENDING','MISSING_ACTUAL','UNKNOWN_PARTICIPATION','UNRESOLVED_CONTRACT')


def sources(a,week,leaf):
    if week==5:
        suffix='complete-leaf-law-v1' if leaf else 'method-comparison-v1'
        public=a.root/'reports/baselines-coverage-20261031h/actual-method-w5'/suffix
        private=a.private_root/('baselines-coverage-20261031h-w5-'+suffix)
    else:
        suffix=f'w{week}-complete-leaf-law-v1' if leaf else f'w{week}-rolling-method-comparison-v1'
        public=a.root/'reports/completion-20261031g/roster'/suffix
        private=a.private_root/('completion-20261031g-'+suffix)
    return public,private


def prepare(a):
    if a.output.exists():raise ValueError('fresh P2 cumulative output required')
    a.output.mkdir(parents=True);bindings=[];roster=[]
    for week in(5,6,7):
        lp,lv=sources(a,week,True)
        full=json.loads(gzip.decompress((lv/'FROZEN_LAW_DIRECTIONS_K.json.gz').read_bytes()))['plans']
        fullkeys={tuple(v['recipe']) for v in full.values()}
        for leaf in(False,True):
            public,private=sources(a,week,leaf)
            planname='FROZEN_LAW_DIRECTIONS_K.json.gz' if leaf else 'FROZEN_SELECTIONS_AND_K.json.gz'
            gradename='GRADED_COMPLETE_LEAF_LAWS.json.gz' if leaf else 'GRADED_METHOD_ROWS.json.gz'
            for file in(public/'SCORES.json',private/planname,private/gradename):
                bindings.append(dict(week=week,leaf=leaf,source_id=private.name if file.parent==private else public.relative_to(a.root).as_posix(),member=file.name,sha256=sha(file)))
            plans=full if leaf else json.loads(gzip.decompress((private/planname).read_bytes()))['plans']
            for tag,plan in plans.items():
                if not leaf and (plan['rule']!='P2' or tuple(plan['recipe'][:3]) in fullkeys):continue
                target,proc,arm=plan['recipe'][:3]
                roster.append(dict(week=week,target=target,procedure_id=proc+':known-target-time-v1',history_regime=arm,product_id='saved_complete_leaf_law' if leaf else 'saved_parametric_law',method_id=tag,leaf=leaf))
    write(a.output/'FROZEN_PROTOCOL.json',dict(version=VERSION,state='FROZEN_BEFORE_NEW_PRIMARY_P2_CUMULATIVE_COUNTS',at=now(),code_sha256=sha(__file__),bootstrap_helper_sha256=sha(uncertainty.__file__),source_bindings=bindings,weekly_roster=roster,evaluation_weeks=[5,6,7],count_contract='Sum canonical primary P2 selected-side counts per exact law/procedure/history/product. Group by side selected before outcomes. Complete Leaf/C02 laws replace matching partial parent P2 views; other parametric laws and D1/D2 prior-only subsets retain their supported populations. Never pool F fixed panel or matched-control variants.',validation='Independently reconcile summed counts against exact retained selected direction/statistical-state rows. No threshold crossing, CDF, probabilities or selection decisions recomputed.',coverage='Full source opportunity universe includes every category offer in all three weeks. Missing law-week rows are unavailable forecasts; unknown/missing outcomes among actual selections retain their states. Selected fallback is explicit origin, separately from admitted-pool fallback.',uncertainty='Existing500 whole-game sensitivity bootstrap seed1703 from saved WIN/LOSS states when>=8games; three weeks insufficient for registered whole-week CI. Exposed, descriptive, no selection/multiplicity adjustment.',probability_scores='Count-only closure; cumulative all-law proper scores remain separate. Do not substitute all-law Brier for selected-side Brier.',budget=dict(wall_seconds=300,max_RSS_bytes=1073741824,max_private_bytes=0,max_threads=2),new_fits=0,new_model_inference=0,new_probabilities=0,new_grades=0,new_decisions=0,Week8_outcomes_read=0))
    (a.output/'SOURCE_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),weekly_law_roster=len(roster),distinct_laws=len({(r['target'],r['procedure_id'],r['history_regime'],r['product_id']) for r in roster}))))


def run(a):
    start=time.monotonic();cpu=time.process_time();p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes())
    if sha(__file__)!=p['code_sha256'] or sha(uncertainty.__file__)!=p['bootstrap_helper_sha256']:raise ValueError('frozen code changed')
    counts=collections.defaultdict(list);compact=collections.defaultdict(list);outer={};sourcebindings={}
    def guard():
        if time.monotonic()-start>300 or resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>1073741824:raise RuntimeError('finite P2 count wave resource bound')
    for week in(5,6,7):
        for leaf in(False,True):
            public,private=sources(a,week,leaf);scorepath=public/'SCORES.json';gradename='GRADED_COMPLETE_LEAF_LAWS.json.gz' if leaf else 'GRADED_METHOD_ROWS.json.gz'
            for file in(scorepath,private/gradename):
                sid=private.name if file.parent==private else public.relative_to(a.root).as_posix()
                if sha(file)!=next(s['sha256'] for s in p['source_bindings'] if s['source_id']==sid and s['member']==file.name):raise ValueError('frozen source changed')
            wanted={r['method_id']:r for r in p['weekly_roster'] if r['week']==week and r['leaf']==leaf}
            score_rows=json.loads(scorepath.read_bytes())
            for index,r in enumerate(score_rows):
                if r['record_kind']!='prop_selection_evaluation':continue
                outer[r['target'],week]=r['selection_metrics']['selection_pool_count']
                if r.get('decision_rule')!='P2' or r['method_id'] not in wanted or r.get('K') is not None or r['cohort_id']!='ALL':continue
                k=(r['target'],r['procedure_id'],r['history_regime'],r['product_id'])
                binding=dict(source_artifact=scorepath.relative_to(a.root).as_posix(),source_artifact_sha256=sha(scorepath),source_row_index=index,record_id=r['record_id'])
                counts[k,r['side']].append((r,binding))
            grade=json.loads(gzip.decompress((private/gradename).read_bytes()))
            for tag,spec in wanted.items():
                k=(spec['target'],spec['procedure_id'],spec['history_regime'],spec['product_id'])
                for r in grade['graded'][tag]:
                    fallback=r['source']=='REUSED_ELIGIBLE_FALLBACK_LAW' if leaf else r.get('fallback') not in(None,'none')
                    compact[k].append(dict(week=week,source_row_index=r['source_row_index'],game_id=r['game_id'],player_id=r['player_id'],selected_side=r['selected_side'],statistical_state=r['statistical_state'],admitted=r['admitted'],source_fallback=fallback))
            del grade,score_rows
            gc.collect();guard()
    scores=[];wide=[]
    for key,allrows in sorted(compact.items()):
        target,proc,arm,product=key;full=sum(outer[target,w] for w in(5,6,7));admitted=sum(r['admitted'] for r in allrows);abstain=sum(r['admitted'] and r['selected_side'] is None for r in allrows);poolfallback=sum(r['admitted'] and r['source_fallback'] for r in allrows);triplet=[]
        if len({(r['week'],r['source_row_index']) for r in allrows})!=len(allrows):raise ValueError('repeated snapshots within cumulative P2 policy')
        wide_row=dict(target=target,procedure_id=proc,history_regime=arm,product_id=product,decision_rule='P2',evaluation_weeks=[5,6,7],outer_eligible_opportunities=full,admitted_forecast_opportunities=admitted,unavailable_forecast_opportunities=full-admitted,admitted_rule_abstentions=abstain,admitted_pool_fallback_count=poolfallback)
        for side in('over','under','Combined'):
            selected=[r for r in allrows if r['selected_side'] and(side=='Combined' or r['selected_side']==side)]
            expected=collections.Counter(r['statistical_state'] for r in selected);source=counts[key,side]
            summed={state:sum(r['selection_metrics']['status_counts'][state] for r,_ in source) for state in STATES}
            if any(summed[s]!=expected[s] for s in STATES) or len(selected)!=sum(r['forecast_rows'] for r,_ in source):raise ValueError('retained states/canonical counts mismatch')
            n=summed['WIN']+summed['LOSS'];fallback=sum(r['source_fallback'] for r in selected);supportedfallback=sum(r['source_fallback'] and r['statistical_state'] in('WIN','LOSS','PUSH') for r in selected)
            sm=dict(WIN=summed['WIN'],LOSS=summed['LOSS'],PUSH=summed['PUSH'],status_counts=summed,hit_rate=summed['WIN']/n if n else None,denominators=dict(outer_rows=len(selected),decided=n,supported_threshold_outcomes=n+summed['PUSH'],unresolved=len(selected)-n-summed['PUSH']),selection_pool_count=full,selection_coverage=len(selected)/full if full else None,admitted_forecast_opportunities=admitted,unavailable_forecast_opportunities=full-admitted,admitted_rule_abstentions=abstain,selected_any_side_in_pool=sum(r['selected_side'] is not None for r in allrows),selected_side_fallback_count=fallback,selected_side_scored_fallback_count=supportedfallback,admitted_pool_fallback_count=poolfallback,fallback_scope='Selected-side fallback exact source origin; admitted-pool fallback separately named. D1/D2 parametric products cover only saved prior-law subsets when learned law not recovered.',bookmaker_settlement_status_counts=dict(UNRESOLVED_CONTRACT=len(selected)),game_uncertainty=uncertainty.bootstrap(selected),probability_scores=dict(status='NOT_REAGGREGATED_IN_COUNT_ONLY_PRIMARY_P2_CLOSURE',reason='All-law cumulative proper scores have a different mask from selected-side scores; weekly selected-pool probability annotations remain available.'),returns=dict(net=None,ROI=None,drawdown=None,reason='NO_QUALIFIED_PRICE_OR_BOOK_SETTLEMENT'))
            row=dict(record_id='H3-P2-'+hashlib.sha256(canonical([key,side])).hexdigest()[:24],record_kind='prop_selection_evaluation',procedure_id=proc,history_regime=arm,product_id=product,target=target,side=side,decision_rule='P2',season=2026,week='ALL',evaluation_seasons=[2026],evaluation_weeks=[5,6,7],weeks_with_source_views=sorted({r['evaluation_weeks'][0] for r,_ in source}),evaluation_panel_id=VERSION,time_panel_id='2026W5_W7_ROLLING_SOURCE_CLOCKS_42_OF_43_GAMES',horizon_id='PER_GAME_SERVER_SOURCE_CLOCK_T90_QUALIFIED_KNOWN_TARGET_TIME',cohort_id='ALL',K=None,rank_scope=None,selection_evidence='RETROSPECTIVE_RULE_REPLAY',period='full_game',season_type='REG',statistic_period='full_game',overtime=True,forecast_rows=len(selected),n=n,selection_loss_rate=summed['LOSS']/n if n else None,selection_metrics=sm,fallback_rows=fallback,fallback_rate=fallback/len(selected) if selected else None,fallback_count_scope='SELECTED_SIDE_EXACT_SOURCE_ORIGIN',unique_games=len({r['game_id'] for r in selected}),unique_players=len({r['player_id'] for r in selected if r['player_id']}),unique_player_games=len({(r['game_id'],r['player_id']) for r in selected if r['player_id']}),query_membership_sha256=hashlib.sha256(canonical(sorted((r['week'],r['source_row_index']) for r in selected))).hexdigest(),mae=None,mse=None,brier=None,log_loss=None,probability_conditioning='MODELED_APPEARANCE',bookmaker_nonvoid_conditioning='UNESTABLISHED',settlement_status='UNRESOLVED_CONTRACT',source_records=[b for _,b in source],evidence='NEW_PERIOD_AGGREGATION_OF_RETAINED_P2_COUNTS',null_reason=None if n else 'NO_DECIDED_SELECTIONS',new_NFL_observations=0)
            scores.append(row);triplet.append(row)
            prefix='Over' if side=='over' else 'Under' if side=='under' else 'Combined'
            for name,value in dict(selected=len(selected),wins=summed['WIN'],losses=summed['LOSS'],decided=n,hit_rate=sm['hit_rate'],push=summed['PUSH'],void=summed['VOID'],pending=summed['PENDING'],missing_actual=summed['MISSING_ACTUAL'],unknown_participation=summed['UNKNOWN_PARTICIPATION'],statistical_unresolved=summed['UNRESOLVED_CONTRACT'],book_contract_unresolved=len(selected),fallback_count=fallback,fallback_rate=row['fallback_rate'],unique_games=row['unique_games'],unique_players=row['unique_players'],game_uncertainty=sm['game_uncertainty']).items():wide_row[prefix+'_'+name]=value
        over,under,combined=triplet
        if combined['forecast_rows']!=over['forecast_rows']+under['forecast_rows'] or combined['n']!=over['n']+under['n']:raise ValueError('P2 side partition failed')
        for state in STATES:
            if combined['selection_metrics']['status_counts'][state]!=over['selection_metrics']['status_counts'][state]+under['selection_metrics']['status_counts'][state]:raise ValueError('P2 state partition failed')
        if full!=admitted+(full-admitted) or admitted!=abstain+combined['forecast_rows']:raise ValueError('P2 coverage partition failed')
        wide.append(wide_row);guard()
    write(a.output/'SCORES.json',scores);write(a.output/'PRIMARY_P2_SIDE_TABLE.json',wide);csvwrite(a.output/'PRIMARY_P2_SIDE_TABLE.csv',wide)
    write(a.output/'RUN_RECEIPT.json',dict(state='COMPLETE_FINITE_PRIMARY_P2_COUNT_CLOSURE',at=now(),protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),score_sha256=sha(a.output/'SCORES.json'),law_procedure_history_products=len(wide),canonical_side_views=len(scores),side_and_coverage_reconciliation='PASS_EVERY_TRIPLET',private_derivative_bytes=0,new_fits=0,new_model_inference=0,new_probabilities=0,new_grades=0,new_decisions=0,new_NFL_observations=0,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)))
    print(json.dumps(dict(laws=len(wide),score_views=len(scores),wall_seconds=time.monotonic()-start)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a) if a.action=='prepare' else run(a)
