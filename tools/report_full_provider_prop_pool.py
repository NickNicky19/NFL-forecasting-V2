"""Read retained grades for readable views, metadata and exact paired annotations.

No new threshold crossing, source labels, fitting, inference or collection.
"""
import argparse,collections,csv,gzip,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2 import full_provider_prop_replay as wave
from nfl_v2 import recorded_prop_grading as pilot


def binding(path):return dict(path=str(path),sha256=wave.sha(path))


def rows_for(score,grades,kmap):
    pool=[r for r in grades if r['strategy']==score['strategy']and(score['target']=='ALL'or r['target']==score['target'])]
    if score['K']is not None:
        indices=kmap[score['strategy'],score['target'],score['rank_scope'],score['K']]
        pool=[r for r in pool if r['source_row_index']in indices]
    else:pool=[r for r in pool if wave.in_cohort(r,score['cohort_id'])]
    return [r for r in pool if r['selected_side']and(score['side']=='Combined'or r['selected_side']==score['side'])]


def format_cell(r):
    m=r['selection_metrics'];hit='N/A'if not r['n']else f"{100*m['hit_rate']:.2f}%"
    return f"{r['forecast_rows']} selected; {m['WIN']}W/{m['LOSS']}L; {r['n']} decided; {hit}; {m['status_counts']['UNKNOWN_PARTICIPATION']} unknown"


def main(args):
    out,priv=args.public,args.private;scores=json.loads((out/'SCORES.json').read_bytes());receipt=json.loads((out/'RUN_RECEIPT.json').read_bytes())
    if wave.sha(out/'SCORES.json')!=receipt['public_score_sha256']or wave.sha(priv/'GRADED_ROWS.json.gz')!=receipt['private_grade_sha256']:raise ValueError('frozen source changed')
    grades=json.loads(gzip.decompress((priv/'GRADED_ROWS.json.gz').read_bytes()))['rows'];ks=json.loads(gzip.decompress((priv/'FROZEN_K_MEMBERSHIPS.json.gz').read_bytes()))['rows']
    kmap={(k['strategy'],k['target'],k['rank_scope'],k['K']):set(k['source_row_indices'])for k in ks}
    baseline={r['source_row_index']:r for r in grades if r['strategy']==wave.ADJUSTED}
    metadata=[];annotations=[];flat=[];paired_cache={}
    for i,r in enumerate(scores):
        rr=rows_for(r,grades,kmap);decided=[x for x in rr if x['statistical_state']in('WIN','LOSS')]
        if len(rr)!=r['forecast_rows']or len(decided)!=r['n']:raise ValueError('metadata membership count changed')
        membership=hashlib.sha256(wave.canonical(sorted(x['source_row_index']for x in rr))).hexdigest()
        if membership!=r['query_membership_sha256']:raise ValueError('metadata membership changed')
        metadata.append(dict(record_id=r['record_id'],alias_of_record_id=None,unique_players=len({x['player_id']for x in rr if x['player_id']}),
            unique_player_games=len({(x['player_id'],x['game_id'])for x in rr if x['player_id']}),unique_weeks=1 if decided else 0,
            decided_unique_games=len({x['game_id']for x in decided}),decided_unique_players=len({x['player_id']for x in decided if x['player_id']}),
            decided_unique_player_games=len({(x['player_id'],x['game_id'])for x in decided if x['player_id']}),decided_week_count=1 if decided else 0,
            registered_week_count=1,registered_weeks=[7],selected_week_count=1 if rr else 0,overtime=True,season_type='REG',statistic_period='full_game'))
        if decided:
            if any(baseline[x['source_row_index']]['statistical_state']not in('WIN','LOSS')for x in decided):raise ValueError('paired learned support mismatch')
            control=sum(baseline[x['source_row_index']]['statistical_state']=='LOSS'for x in decided)/len(decided)
            key=(r['strategy'],tuple(sorted(x['source_row_index']for x in decided)))
            if key not in paired_cache:paired_cache[key]=pilot.bootstrap(rr,baseline)
            comparison=dict(status='PAIRED_RETAINED_ROWS',comparator_procedure_id=wave.VERSION+':'+wave.ADJUSTED,
                comparator_history_regime='ARCHIVED_TRAINING_HISTORY_UNKNOWN',comparator_product_id=r['product_id'],metric='selection_loss_rate',
                candidate_error=r['selection_loss_rate'],comparator_error=control,paired_n=len(decided),
                membership_sha256=hashlib.sha256(wave.canonical(sorted(x['source_row_index']for x in decided))).hexdigest(),
                uncertainty=paired_cache[key],cutoff_policy=r['horizon_id'])
        else:comparison=dict(status='UNESTABLISHED',reason='No decided selected rows; no fabricated zero loss or paired denominator.')
        annotations.append(dict(source_row_index=i,comparison=comparison))
        m=r['selection_metrics'];interval=m['game_uncertainty']
        flat.append(dict(record_id=r['record_id'],method=r['procedure_id'],strategy=r['strategy'],target=r['target'],
            season=r['season'],weeks='7',games=r['unique_games'],horizon=r['horizon_id'],evidence=r['selection_evidence'],
            cohort=r['cohort_id'],K=r['K'],rank_scope=r['rank_scope'],side=r['side'],
            eligible=m['eligible_rank_pool_n'],original_source_pool=m['selection_pool_count'],selected=r['forecast_rows'],
            wins=m['WIN'],losses=m['LOSS'],pushes=m['PUSH'],voids=m['status_counts']['VOID'],pending=m['status_counts']['PENDING'],
            missing_actual=m['status_counts']['MISSING_ACTUAL'],unknown_participation=m['status_counts']['UNKNOWN_PARTICIPATION'],
            book_unresolved=r['forecast_rows'],decided=r['n'],hit_rate=m['hit_rate'],error_rate=r['selection_loss_rate'],
            abstentions=m['abstentions_outside_selected_partition'],selection_coverage=m['selection_coverage'],
            unique_players=metadata[-1]['unique_players'],unique_player_games=metadata[-1]['unique_player_games'],unique_weeks=metadata[-1]['unique_weeks'],
            game_clusters=interval['game_clusters'],game_interval=json.dumps(interval['game_interval']),game_interval_status=interval['game_interval_status'],week_interval=None,
            price=None,probability=None,Brier=None,EV=None,ROI=None,CLV=None,
            comparator=wave.VERSION+':'+wave.ADJUSTED,paired_error_change=None if not decided else r['selection_loss_rate']-control))
    wave.write(out/'METADATA_SUPPLEMENT.json',dict(source_score_sha256=wave.sha(out/'SCORES.json'),rows=metadata))
    wave.write(out/'COMPARISON_ANNOTATIONS.json',dict(source_score_sha256=wave.sha(out/'SCORES.json'),identity='source_row_index',rows=annotations))
    for name,rr in [('ALL_SELECTION_VIEWS.csv',flat),('TOPK_VIEWS.csv',[r for r in flat if r['K']is not None]),('COHORT_VIEWS.csv',[r for r in flat if r['K']is None and r['cohort']!='ALL'])]:
        with(out/name).open('x',newline='')as f:
            w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(rr)
    lookup={(r['strategy'],r['target'],r['side']):r for r in scores if r['cohort_id']=='ALL'and r['K']is None}
    lines=['# Full provider-labelled threshold pool: expanded statistical direction comparison','','The panel expands from 285 originally selected records to **all 462 provider-labelled finite thresholds** in the same proven pregame snapshot and thirteen later 2026 Week 7 games: 441 DraftKings-labelled and 21 Sleeper-labelled. It excludes 957 site-generated thresholds. There are **446 qualified outcomes and 16 unknown appearances**. Provider labels do not authenticate quote age, executable cash prices, jurisdiction or settlement. This is a complete comparison for this one snapshot, not a complete Week 7, season-to-date or season.','','The original 285 recorded selections are unchanged at **183/279 (65.59%)**, with six unknowns and 177 original abstentions. New point-derived decisions on the previously unselected records are retrospective rules, never recovered original selections. The saved adjusted-point rule on the full pool is **272/446 (60.99%)**; the saved raw-projection field rule is **261/446 (58.52%)**. Always-Over is 202/446 (45.29%); always-Under is 244/446 (54.71%). All prices/probabilities/EV/ROI/CLV remain unavailable; all selected book settlements remain unresolved.','','## Every method, category and actual selected side','','Every cell shows selected count, statistical wins/losses, decided denominator, exact count-based hit rate and unknown participation. Combined sums the actual preselected-side buckets. Empty sides are N/A. No statistical push or verified void occurred in this panel; unknowns do not become DNP/zero.']
    for strategy in wave.STRATEGIES:
        lines += ['',f'### {strategy}','','| Category | Predicted Over | Predicted Under | Combined |','|---|---|---|---|']
        for target in('ALL',)+wave.TARGETS:
            lines.append('| '+target+' | '+' | '.join(format_cell(lookup[strategy,target,s])for s in('over','under','Combined'))+' |')
        for target in('nick-chart-ppr-v1','anytime_td'):lines.append('| '+target+' | N/A: no matching target/threshold contract | N/A | N/A |')
    lines += ['','## What changed when coverage expanded','','On the 167 qualified outcomes among the 177 originally unselected records, saved adjusted-point direction is **89/167 (53.29%)**, raw-field direction **83/167 (49.70%)**, and always-Under **97/167 (58.08%)**. The original rule abstains on all 177. The higher original selected-pool rate therefore cannot be applied to the full pool, and the full-pool drop is not a pure learner effect. Coverage, source composition and selection policy differ.','','On the identical 446 full-pool outcomes, the adjustment wins eleven more directions than the saved raw field: 272 versus 261. The [paired comparison annotations](COMPARISON_ANNOTATIONS.json) retain same-case error differences and game-cluster sensitivity. Each source point was already rounded to two decimals; strict internal-unrounded P1 is unavailable. The `raw_projection` label identifies a retained field and its exact archived `provider_point` parity, not authenticated external supplier training or vintage.','','## Cohorts, K and timing','','[All machine-readable views](ALL_SELECTION_VIEWS.csv) · [Cohort views](COHORT_VIEWS.csv) · [Top-K views](TOPK_VIEWS.csv). Each strategy has actual-selected Over/Under/Combined results for fixed role/source/original-selection/workload/player bands and K6/10/20 per category. K has separate Combined, Over-only and Under-only ranking pools. Ranking uses saved point-line gaps within category at retained precision, stable ties and no target/outcome/participation filter; membership was frozen before new subset grades. It is a retrospective thirteen-game source-snapshot strategy, not an originally issued weekly list or a cross-category raw-unit rank.','','Existing top-player/workload memberships are retrospective diagnostics, actually assembled after the games with earlier feature clocks. Missing memberships remain a cohort; no player rank was recomputed. Original marked Top flags remain distinct from new K pick lists and top-player cohorts. No artificial season aliases are created here.','','The server proves retained bytes by October 23 at 17:49:53 UTC, before the thirteen later T-minus-90 deadlines. It does not authenticate the earlier internal capture or quote/source vintages. One week cannot support the registered whole-week interval. Game bootstrap uses 500 draws/seed1703 with at least eight decided games; otherwise uncertainty is unavailable. All results are exposed descriptive evidence, without selection/multiplicity adjustment.','','[Frozen protocol](FROZEN_PROTOCOL.json), [run receipt](RUN_RECEIPT.json), [exact-side reconciliation](SIDE_RECONCILIATION.json), [sample metadata](METADATA_SUPPLEMENT.json) and [unavailable targets](UNAVAILABLE_CELLS.json). Raw rows remain private and scientifically reconstructable from the pinned original source, already-restored qualified source/identity material and frozen code. No fit, inference, new football forecast, collection, wager, production change or Week 8 outcome read occurred.']
    with(out/'README.md').open('x')as f:f.write('\n'.join(lines)+'\n')
    wave.write(out/'REPORT_RECEIPT.json',dict(state='COMPLETE_SOURCE_BOUND_REPORT_METADATA_PAIRED_ANNOTATIONS',code_sha256=wave.sha(Path(__file__)),
        source_score_sha256=wave.sha(out/'SCORES.json'),source_grade_sha256=wave.sha(priv/'GRADED_ROWS.json.gz'),
        metadata_rows=len(metadata),paired_annotations=len(annotations),new_threshold_grades=0,new_fits=0,new_forecasts=0))
    print(json.dumps(dict(state='PASS_REPORT_NO_REGRADING',rows=len(scores),new_grades=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public',required=True,type=Path);p.add_argument('--private',required=True,type=Path);main(p.parse_args())
