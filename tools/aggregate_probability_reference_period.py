"""Final finite W5–7 cached-loss and canonical-primary-count aggregation."""
import argparse
import collections
import gzip
import hashlib
import json
import math
import resource
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import canonical,now,sha,write
from nfl_v2.paired_uncertainty import paired_losses
from tools.numerical_championship import csvwrite
from tools.compare_probability_references import diagnostics

VERSION='v2-finite-W5-W7-cached-probability-and-primary-P1-count-aggregation-v1'
H='reports/baselines-coverage-20261031h'
G='reports/completion-20261031g/roster'


def source_sets(a):
    baseline=[(a.root/H/'probability/w5-reference-v1',a.private_root/'baselines-coverage-20261031h-probability-w5-reference-v1'),(a.root/H/'probability/reference-v2',a.private_root/'baselines-coverage-20261031h-probability-reference-v2')]
    points=[a.root/H/'actual-method-w5/method-comparison-v1/SCORES.json']+[a.root/G/f'w{w}-rolling-method-comparison-v1/SCORES.json' for w in(6,7)]
    return baseline,points


def prepare(a):
    if a.output.exists():raise ValueError('fresh final-period output required')
    a.output.mkdir(parents=True)
    bases,points=source_sets(a);sources=[];roster=[]
    for public,private in bases:
        protocol=json.loads((public/'FROZEN_PROTOCOL.json').read_bytes())
        roster.extend(protocol['roster'])
        for file in(public/'FROZEN_PROTOCOL.json',public/'SCORES.json',private/'BASELINE_AND_CACHED_LAW_ROWS.json.gz'):
            sources.append(dict(kind='private_cached_loss' if file.parent==private else 'public_baseline',source_id=private.name if file.parent==private else public.relative_to(a.root).as_posix(),member=file.name,sha256=sha(file)))
    for file in points:sources.append(dict(kind='public_primary_point_counts',path=file.relative_to(a.root).as_posix(),sha256=sha(file)))
    write(a.output/'FROZEN_PROTOCOL.json',dict(version=VERSION,state='FROZEN_BEFORE_NEW_THREE_WEEK_AGGREGATION',at=now(),code_sha256=sha(__file__),helper_sha256=sha(Path(__file__).with_name('compare_probability_references.py')),paired_helper_sha256=sha(a.root/'nfl_v2/paired_uncertainty.py'),source_bindings=sources,weekly_probability_roster=roster,evaluation_weeks=[5,6,7],probability_scope='Only retained cached vectors/losses; same exact source offer keys. FULL/LEARNED/PRIOR views on the candidate mask; existing B0 and chronological B1 prior vectors reused without reestimation.',primary_P1_scope='Sum original canonical weekly primary P1 counts per exact procedure/history/output/category. Exclude all MATCHED_RETAINED_CONTROL overlapping mask variants and all F fixed panel. Each side and combined from exact original selected-side counts. Not a newly fitted selector or original issued policy.',uncertainty='Probability paired game-cluster sensitivity; only3weeks, registered week-bootstrap insufficient. P1 weekly bootstrap intervals not pooled; three-week counts descriptive, unavailable pooled game resampling explicitly marked. No posthoc support gates.',market='No authenticated prices/settlement; ROI/EV/CLV remain null.',exposure='All football outcomes previously exposed research. Adds a stated-period aggregate, not new NFL outcomes.',budget=dict(wall_seconds=300,max_RSS_bytes=1073741824,max_private_bytes=0,max_threads=2),new_fits=0,new_model_inference=0,new_probabilities=0,new_grades=0,Week8_outcomes_read=0))
    (a.output/'SOURCE_SNAPSHOT.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),weekly_recipe_metadata=len(roster))))


def log_value(v):return math.inf if v=='Infinity' else v


def summarize(rr,ref):
    n=len(rr);logs=[log_value(r[ref+'_log_loss']) for r in rr];inf=sum(math.isinf(v) for v in logs)
    return dict(n=n,brier=math.fsum(r[ref+'_brier'] for r in rr)/n if n else None,log_loss='Infinity' if inf else math.fsum(logs)/n if n else None,infinite_log_losses=inf,null_reason=None if n else 'NO_ROWS_IN_CANDIDATE_ORIGIN_PARTITION')


def run(a):
    start=time.monotonic();cpu=time.process_time();p=json.loads((a.output/'FROZEN_PROTOCOL.json').read_bytes())
    if sha(__file__)!=p['code_sha256']:raise ValueError('frozen aggregate code changed')
    bases,points=source_sets(a);data=collections.defaultdict(dict);bindings=collections.defaultdict(list);public={}
    for directory,private in bases:
        for file in(directory/'FROZEN_PROTOCOL.json',directory/'SCORES.json',private/'BASELINE_AND_CACHED_LAW_ROWS.json.gz'):
            sid=private.name if file.parent==private else directory.relative_to(a.root).as_posix()
            if sha(file)!=next(s['sha256'] for s in p['source_bindings'] if s.get('source_id')==sid and s.get('member')==file.name):raise ValueError('cached baseline source changed')
        rows=json.loads(gzip.decompress((private/'BASELINE_AND_CACHED_LAW_ROWS.json.gz').read_bytes()))
        for r in rows:
            k=(r['target'],r['procedure_id'],r['history_regime']);q=(r['week'],r['source_row_index'])
            if q in data[k]:raise ValueError('overlapping period source keys')
            data[k][q]=r
        for i,r in enumerate(json.loads((directory/'SCORES.json').read_bytes())):
            if r['evaluation_weeks'] not in([5],[6,7]):continue
            key=(r['target'],r['matched_candidate_procedure_id'],r['history_regime'],r['reference_id'],r['fallback_view'])
            bindings[key].append(dict(source_artifact=(directory/'SCORES.json').relative_to(a.root).as_posix(),source_artifact_sha256=sha(directory/'SCORES.json'),source_row_index=i,record_id=r['record_id']))
    scores=[];pairs=[];cal=[];coverage=[]
    for key,dd in sorted(data.items()):
        target,proc,arm=key;allrows=[r for q,r in sorted(dd.items())]
        for partition in('FULL','LEARNED','PRIOR'):
            rr=[r for r in allrows if partition=='FULL' or r['origin']==partition]
            mask=hashlib.sha256(canonical([[r['week'],r['source_row_index'],r['game'],r['player'],r['target'],r['line'],r['actual']] for r in rr])).hexdigest()
            for ref in('candidate','B0','B1'):
                rid='H3-PROB-'+hashlib.sha256(canonical([key,partition,ref])).hexdigest()[:24]
                row=dict(record_id=rid,record_kind='prop_threshold_probability_evaluation',procedure_id=proc+':known-target-time-v1' if ref=='candidate' else ref+':matched-to:'+proc,reference_id=ref,matched_candidate_procedure_id=proc,history_regime=arm,strict_current_information='strict' in proc,product_id='actual_line_categorical_law',target=target,population='qualified_saved_law_outcome_mask_with_outer_coverage_supplement',season=2026,week='ALL',evaluation_seasons=[2026],evaluation_weeks=[5,6,7],evaluation_panel_id=VERSION,fallback_view=partition,forecast_rows=len(allrows),mae=None,mse=None,probability_conditioning='MODELED_APPEARANCE',probability_score_contract='HALF_MULTICLASS_BRIER_OVER_UNDER_PUSH_V1',bookmaker_nonvoid_conditioning='UNESTABLISHED',membership_sha256=mask,source_records=bindings[target,proc,arm,ref,partition],source_prior_rows=sum(r['origin']=='PRIOR' for r in rr),baseline_empty_prefix_rows=sum(r['baseline_origin']=='EMPTY_PREFIX_CONSTANT_HALF' for r in rr),unique_games=len({r['game'] for r in rr}),unique_weeks=len({r['week'] for r in rr}),evidence='NEW_PERIOD_AGGREGATION_OF_RETAINED_PROBABILITY_LOSSES',new_NFL_observations=0,**summarize(rr,ref));scores.append(row);cal.append(dict(record_id=rid,**diagnostics(rr,ref)))
            for ref in('B0','B1'):
                for metric in('brier','log_loss'):
                    u=paired_losses([log_value(r['candidate_'+metric]) for r in rr],[log_value(r[ref+'_'+metric]) for r in rr],[r['week'] for r in rr],[r['game'] for r in rr])
                    pairs.append(dict(comparison_id='H3-PAIR-'+hashlib.sha256(canonical([key,partition,ref,metric])).hexdigest()[:24],target=target,procedure_id=proc,history_regime=arm,strict_current_information='strict' in proc,metric=metric,fallback_view=partition,comparator=ref,evaluation_weeks=[5,6,7],membership_sha256=mask,**u))
        if time.monotonic()-start>300:raise RuntimeError('period wall budget')
    # Matched law-to-law contrasts use exact common identity/label rows; own masks stay visible.
    for key,aa in sorted(data.items()):
        target,proc,arm=key
        if 'ordered_leaf_cdf' not in proc and 'c02' not in proc:continue
        glm='v2-distribution-controls-reconstruction-v2:regularized_glm_law'+(':strict-current-inputs' if 'strict' in proc else '')
        bb=data.get((target,glm,arm),{})
        qq=sorted(set(aa)&set(bb))
        for q in qq:
            if any(aa[q][f]!=bb[q][f] for f in('game','player','target','line','actual')):raise ValueError('law comparison identity/label mismatch')
        for partition in('FULL','COMMON_LEARNED','PRIOR_ANY'):
            jj=[q for q in qq if partition=='FULL' or (partition=='COMMON_LEARNED' and aa[q]['origin']=='LEARNED' and bb[q]['origin']=='LEARNED') or (partition=='PRIOR_ANY' and (aa[q]['origin']=='PRIOR' or bb[q]['origin']=='PRIOR'))]
            for metric in('brier','log_loss'):
                u=paired_losses([log_value(aa[q]['candidate_'+metric]) for q in jj],[log_value(bb[q]['candidate_'+metric]) for q in jj],[q[0] for q in jj],[aa[q]['game'] for q in jj])
                pairs.append(dict(comparison_id='H3-METHOD-PAIR-'+hashlib.sha256(canonical([key,partition,metric])).hexdigest()[:24],target=target,procedure_id=proc,history_regime=arm,strict_current_information='strict' in proc,metric=metric,fallback_view=partition,comparator=glm,evaluation_weeks=[5,6,7],candidate_own_n=len(aa),comparator_own_n=len(bb),both_own_masks_equal=set(aa)==set(bb),**u))
    # Count-only P1 cumulative projection: source weekly rows are unchanged.
    grouped=collections.defaultdict(list);outer={}
    for file in points:
        if sha(file)!=next(s['sha256'] for s in p['source_bindings'] if s.get('path')==file.relative_to(a.root).as_posix()):raise ValueError('canonical weekly count source changed')
        digest=sha(file)
        for i,r in enumerate(json.loads(file.read_bytes())):
            if r['record_kind']!='prop_selection_evaluation' or r['decision_rule']!='P1' or r.get('K') is not None or r['cohort_id']!='ALL':continue
            week=r['evaluation_weeks'][0];outer[r['target'],week]=r['selection_metrics']['selection_pool_count']
            key=(r['target'],r['procedure_id'],r['history_regime'],r['product_id'],r['side'])
            grouped[key].append((r,dict(source_artifact=file.relative_to(a.root).as_posix(),source_artifact_sha256=digest,source_row_index=i,record_id=r['record_id'])))
    primary=[]
    for key,rows in sorted(grouped.items()):
        target,proc,arm,product,side=key
        if len({r['evaluation_weeks'][0] for r,_ in rows})!=len(rows):raise ValueError('duplicate primary weekly views')
        counts={state:sum(r['selection_metrics']['status_counts'][state] for r,_ in rows) for state in('WIN','LOSS','PUSH','VOID','PENDING','MISSING_ACTUAL','UNKNOWN_PARTICIPATION','UNRESOLVED_CONTRACT')}
        selected=sum(r['forecast_rows'] for r,_ in rows);decided=counts['WIN']+counts['LOSS'];universe=sum(outer[target,w] for w in(5,6,7));admitted=sum(r['selection_metrics']['admitted_forecast_opportunities'] for r,_ in rows);abstain=sum(r['selection_metrics']['admitted_rule_abstentions'] for r,_ in rows)
        metrics=dict(**{s:counts[s] for s in('WIN','LOSS','PUSH')},status_counts=counts,hit_rate=counts['WIN']/decided if decided else None,selection_pool_count=universe,selection_coverage=selected/universe if universe else None,admitted_forecast_opportunities=admitted,unavailable_forecast_opportunities=universe-admitted,admitted_rule_abstentions=abstain,denominators=dict(decided=decided,outer_rows=selected,supported_threshold_outcomes=decided+counts['PUSH'],unresolved=sum(counts[s] for s in('MISSING_ACTUAL','UNKNOWN_PARTICIPATION','UNRESOLVED_CONTRACT'))),bookmaker_settlement_status_counts=dict(UNRESOLVED_CONTRACT=selected),game_uncertainty=dict(estimate=counts['WIN']/decided if decided else None,game_interval=None,game_interval_status='NOT_RECOMPUTED_IN_COUNT_ONLY_PERIOD_AGGREGATION',week_interval=None,week_interval_status='INSUFFICIENT_WEEK_CLUSTERS',selection_limit='Exposed descriptive aggregate; no selection/multiplicity adjustment'),returns=dict(ROI=None,net=None,drawdown=None,reason='NO_QUALIFIED_PRICE_OR_BOOK_SETTLEMENT'))
        row=dict(record_id='H3-P1-'+hashlib.sha256(canonical(key)).hexdigest()[:24],record_kind='prop_selection_evaluation',procedure_id=proc,history_regime=arm,product_id=product,target=target,side=side,decision_rule='P1',season=2026,week='ALL',evaluation_seasons=[2026],evaluation_weeks=[5,6,7],weeks_with_source_views=sorted(r['evaluation_weeks'][0] for r,_ in rows),evaluation_panel_id=VERSION,time_panel_id='2026W5_W7_ROLLING_SOURCE_CLOCKS_42_OF_43_GAMES',cohort_id='ALL',K=None,rank_scope=None,selection_evidence='RETROSPECTIVE_RULE_REPLAY',forecast_rows=selected,n=sum(r['n'] for r,_ in rows),selection_loss_rate=counts['LOSS']/decided if decided else None,selection_metrics=metrics,unique_games=sum(r['unique_games'] for r,_ in rows),unique_players=None,unique_players_null_reason='Repeated players across weeks; count-only source projection does not recover distinct player IDs',mae=None,mse=None,brier=None,log_loss=None,settlement_status='UNRESOLVED_CONTRACT',source_records=[b for _,b in rows],evidence='NEW_PERIOD_AGGREGATION_OF_CANONICAL_WEEKLY_COUNTS',new_NFL_observations=0)
        primary.append(row)
    trip=collections.defaultdict(dict)
    for r in primary:trip[r['target'],r['procedure_id'],r['history_regime'],r['product_id']][r['side']]=r
    for rr in trip.values():
        for field in('WIN','LOSS','PUSH'):
            if rr['Combined']['selection_metrics'][field]!=rr['over']['selection_metrics'][field]+rr['under']['selection_metrics'][field]:raise ValueError('period side count mismatch')
        if rr['Combined']['forecast_rows']!=rr['over']['forecast_rows']+rr['under']['forecast_rows']:raise ValueError('period selected count mismatch')
    scores.extend(primary)
    write(a.output/'SCORES.json',scores);write(a.output/'PAIRED_COMPARISONS.json',pairs);csvwrite(a.output/'PAIRED_COMPARISONS.csv',pairs);write(a.output/'CALIBRATION_AND_DISCRIMINATION.json',cal);csvwrite(a.output/'PRIMARY_P1_SIDE_COUNTS.csv',primary)
    write(a.output/'RUN_RECEIPT.json',dict(state='COMPLETE_FINITE_THREE_WEEK_CACHED_AGGREGATION',at=now(),protocol_sha256=sha(a.output/'FROZEN_PROTOCOL.json'),score_sha256=sha(a.output/'SCORES.json'),proper_score_views=len(scores)-len(primary),primary_P1_side_views=len(primary),paired_contrasts=len(pairs),private_derivative_bytes=0,new_fits=0,new_model_inference=0,new_probabilities=0,new_grades=0,new_NFL_observations=0,resources=dict(wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)))
    print(json.dumps(dict(scores=len(scores),proper=len(scores)-len(primary),primary_P1=len(primary),contrasts=len(pairs))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=('prepare','run'));p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--private-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();prepare(a) if a.action=='prepare' else run(a)
