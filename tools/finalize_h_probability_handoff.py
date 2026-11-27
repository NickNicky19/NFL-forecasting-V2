"""Seal readable H probability/P1 projections and source bindings, no scores."""
import argparse
import collections
import csv
import gzip
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import now,sha,write
from tools.numerical_championship import csvwrite


def main(a):
    h=a.root/'reports/baselines-coverage-20261031h';out=h/'probability/w5-w7-cumulative-v1'
    scores=json.loads((out/'SCORES.json').read_bytes());proper=[r for r in scores if r['record_kind']=='prop_threshold_probability_evaluation'];point=[r for r in scores if r['record_kind']=='prop_selection_evaluation']
    grouped=collections.defaultdict(dict)
    for r in proper:
        if r['fallback_view']=='FULL':grouped[r['target'],r['matched_candidate_procedure_id'],r['history_regime']][r['reference_id']]=r
    coverage_indexes=[];universe=collections.defaultdict(dict)
    for folder,weeks in(('w5-reference-v1',(5,)),('reference-v2',(6,7))):
        items=json.loads((h/'probability'/folder/'MASK_AND_OUTER_COVERAGE.json').read_bytes());idx={}
        for r in items:
            if folder=='reference-v2' and r['evaluation_weeks']!=[6,7]:continue
            key=(r['target'],r['procedure_id'],r['history_regime']);idx[key]=r;universe[r['target']][weeks]=r['outer_source_offer_universe']
        coverage_indexes.append(idx)
    table=[];coverage=[]
    for key,rr in sorted(grouped.items()):
        c=rr['candidate'];target,proc,arm=key;outer=sum(universe[target].values());parts=[i[key] for i in coverage_indexes if key in i]
        admitted=sum(r['admitted_law_rows'] for r in parts)
        table.append(dict(target=target,procedure_id=proc,history_regime=arm,strict_current_information=c['strict_current_information'],n=c['n'],outer_source_offers=outer,coverage=c['n']/outer if outer else None,candidate_brier=c['brier'],neutral_brier=rr['B0']['brier'],earlier_prevalence_brier=rr['B1']['brier'],candidate_log_loss=c['log_loss'],neutral_log_loss=rr['B0']['log_loss'],earlier_prevalence_log_loss=rr['B1']['log_loss'],source_record_id=c['record_id']))
        coverage.append(dict(record_id=c['record_id'],target=target,procedure_id=proc,history_regime=arm,evaluation_weeks=[5,6,7],outer_source_offer_universe=outer,admitted_law_rows=admitted,unavailable_law_rows=outer-admitted,qualified_mask_n=c['n'],admitted_missing_or_unknown_outcomes=admitted-c['n'],probability_mask_coverage=c['n']/outer if outer else None,scope='FULL means full qualified candidate probability/outcome mask, not every outer offer; explicit origin partitions retained in canonical scores.'))
    write(out/'PRIMARY_PROBABILITY_TABLE.json',table);csvwrite(out/'PRIMARY_PROBABILITY_TABLE.csv',table);write(out/'MASK_AND_OUTER_COVERAGE.json',coverage);csvwrite(out/'MASK_AND_OUTER_COVERAGE.csv',coverage)
    # Reshape existing count scores only; every number remains source-bound.
    trip=collections.defaultdict(dict)
    for r in point:trip[r['target'],r['procedure_id'],r['history_regime'],r['product_id']][r['side']]=r
    wide=[]
    for (target,proc,arm,product),rr in sorted(trip.items()):
        row=dict(target=target,procedure_id=proc,history_regime=arm,product_id=product,decision_rule='P1',evaluation_weeks=[5,6,7],eligible_opportunities=rr['Combined']['selection_metrics']['selection_pool_count'],admitted_forecasts=rr['Combined']['selection_metrics']['admitted_forecast_opportunities'],forecast_unavailable=rr['Combined']['selection_metrics']['unavailable_forecast_opportunities'],admitted_rule_abstentions=rr['Combined']['selection_metrics']['admitted_rule_abstentions'],selected_fallback_rows=None,selected_fallback_null_reason='Parent fallback_issued covers admitted pool and is not a selected-side count; not summed as selected fallback.')
        for side,prefix in(('over','Over'),('under','Under'),('Combined','Combined')):
            s=rr[side];m=s['selection_metrics']
            for k,v in dict(selected=s['forecast_rows'],wins=m['WIN'],losses=m['LOSS'],decided=m['denominators']['decided'],hit_rate=m['hit_rate'],push=m['PUSH'],void=m['status_counts']['VOID'],pending=m['status_counts']['PENDING'],unknown_participation=m['status_counts']['UNKNOWN_PARTICIPATION'],missing_actual=m['status_counts']['MISSING_ACTUAL'],statistical_unresolved=m['status_counts']['UNRESOLVED_CONTRACT'],book_contract_unresolved=s['forecast_rows']).items():row[prefix+'_'+k]=v
        wide.append(row)
    write(out/'PRIMARY_P1_WIDE_TABLE.json',wide);csvwrite(out/'PRIMARY_P1_WIDE_TABLE.csv',wide)
    maxima=[]
    for target in sorted({r['target'] for r in point}):
        for side in('over','under','Combined'):
            eligible=[r for r in point if r['target']==target and r['side']==side and r['selection_metrics']['hit_rate'] is not None]
            best=max(r['selection_metrics']['hit_rate'] for r in eligible)
            maxima.extend(dict(target=target,side=side,procedure_id=r['procedure_id'],history_regime=r['history_regime'],product_id=r['product_id'],wins=r['selection_metrics']['WIN'],losses=r['selection_metrics']['LOSS'],decided=r['selection_metrics']['denominators']['decided'],selected=r['forecast_rows'],hit_rate=best,eligible=r['selection_metrics']['selection_pool_count'],coverage=r['selection_metrics']['selection_coverage'],source_record_id=r['record_id'],interpretation='Raw own-selected-pool maximum; no posthoc support filter, not pure learner comparison or earlier executable policy') for r in eligible if abs(r['selection_metrics']['hit_rate']-best)<=1e-12)
    write(out/'RAW_PRIMARY_P1_SIDE_MAXIMA.json',maxima);csvwrite(out/'RAW_PRIMARY_P1_SIDE_MAXIMA.csv',maxima)
    priorfile=a.root/'reports/completion-20261031g/roster/actual-method-period-summary-v2/CUMULATIVE_W6_W7_METHOD_SIDE_TABLES.csv.gz'
    old={}
    with gzip.open(priorfile,'rt') as f:
        for r in csv.DictReader(f):
            if r['cohort_id']=='ALL' and not r['K'] and r['decision_rule']=='P1':old[r['target'],r['procedure_id'],r['history_regime'],r['product_id']]=r
    display=collections.defaultdict(dict)
    for r in table:
        if r['history_regime']!='H-MULTI' or r['strict_current_information']:continue
        family='C02' if 'c02' in r['procedure_id'] else 'Leaf' if 'ordered_leaf' in r['procedure_id'] else 'GLM' if 'regularized_glm' in r['procedure_id'] else None
        if family:display[r['target']][family]=r
    lines=['# Three-week probability baseline and selected-side checkpoint','','**Beating GLM did not establish useful probability skill.** On the same W5–7 H-MULTI offered-event masks, Leaf/C02 improve Brier over GLM in nine of ten categories, yet beat the neutral reference only for passing touchdowns and interceptions. They beat the chronological same-position prevalence reference in seven categories; passing attempts, completions and interceptions lose. The initial W1–7 numerical championship is unchanged.','','| Category | Matched n / outer offers | Neutral Brier | Earlier prevalence | Leaf | C02 | GLM |','|---|---:|---:|---:|---:|---:|---:|']
    for target,rr in sorted(display.items()):
        r=rr['Leaf'];lines.append(f"| {target} | {r['n']}/{r['outer_source_offers']} | {r['neutral_brier']:.6f} | {r['earlier_prevalence_brier']:.6f} | {r['candidate_brier']:.6f} | {rr['C02']['candidate_brier']:.6f} | {rr['GLM']['candidate_brier']:.6f} |")
    lines += ['', 'The expanded passing-attempt panel is 80/84 outer offers: Leaf Brier 0.255654, C02 0.264041 and GLM 0.339025 versus neutral 0.250000 and prior prevalence 0.252687. Interceptions reverses against prior prevalence: Leaf 0.246365 and C02 0.247754 lose to 0.245527, despite both beating neutral. Passing touchdowns improves against both references: C02 0.236405 and Leaf 0.241014 versus neutral 0.250000 and prior prevalence 0.254341.', '', 'Weekly changes remain visible: in W5, Leaf/C02 beat neutral for attempts and interceptions, while passing touchdowns loses; in W6–7, touchdowns and interceptions beat neutral while attempts loses. These are already exposed observations. Three weeks do not support the registered whole-week bootstrap. Paired game-cluster sensitivity intervals are descriptive and unadjusted for multiplicity/selection; point estimates are not permanent superiority claims.', '', 'The complete [probability table](PRIMARY_PROBABILITY_TABLE.csv) retains CURRENT, RECENT, MULTI and strict-current candidates. CURRENT fitting with older feature memory is distinct from strict-current information. B1 uses exactly earlier same-position football outcomes with kickoff+7d strictly before the actual decision clock; CURRENT/strict uses2026 only, RECENT2025–26, MULTI2022–26. Empty prefixes explicitly use neutral; no old fallback is hidden. This reference has population limitations for offered stars and changed roles. FULL/LEARNED/PRIOR scores and common-learned law comparisons remain separate; no small prior-only case is promoted as a full-population winner.', '', 'B0 is a threshold-local Over=.5/Under=.5/Push=0 reference, not a global CDF or authenticated market. Brier is .25 on decisive outcomes and .75 on pushes; true zero-mass log losses remain infinite. Per-region calibration diagrams and decisive-outcome AUC are separate diagnostics, not fitted calibration. All probabilities condition on modeled appearance; bookmaker nonvoid/settlement and prices remain unverified.', '', '## Selected-side continuity example', '', 'The following uses the same registered C02 H-MULTI lower-median P1 recipe. It compares the prior W6–7 period with W5–7; different calendar coverage is explicit. It does not claim a controlled learner improvement or retrospectively choose a winner.', '', '| Category | W6–7 combined wins/decided | W5–7 predicted Over wins/decided | W5–7 predicted Under wins/decided | W5–7 combined wins/decided |', '|---|---:|---:|---:|---:|']
    for r in wide:
        if not('v2-c02-' in r['procedure_id'] and 'strict' not in r['procedure_id'] and r['history_regime']=='H-MULTI' and r['product_id']=='lower_median'):continue
        prior=old[r['target'],r['procedure_id'],r['history_regime'],r['product_id']]
        lines.append(f"| {r['target']} | {prior['Combined_wins']}/{prior['Combined_decided']} | {r['Over_wins']}/{r['Over_decided']} | {r['Under_wins']}/{r['Under_decided']} | {r['Combined_wins']}/{r['Combined_decided']} |")
    lines += ['', '[Every primary P1 method/strategy with Over, Under and Combined](PRIMARY_P1_WIDE_TABLE.csv) retains exact counts, abstentions, unavailable forecasts and unresolved states. Combined rates use summed decided counts. [Raw own-pool side maxima](RAW_PRIMARY_P1_SIDE_MAXIMA.csv) retain every tied observed maximum, including small or low-coverage pools, without a posthoc minimum-support veto. They are separate from the common-mask probability comparison and an earlier-executable selector. No top-player and top-pick cohorts are mixed here; existing weekly cohort/K products remain under their original identities.', '', 'P1 fallback counts remain null in this count-only cumulative projection: the parent fallback_issued field counts the admitted pool, not selected-side fallback. Distinct players also remain null because players repeat across weeks. Native initial W1–7 scores, all weekly forecasts/grades and original website wins/losses are preserved. Overlapping matched-control-mask variants and the fixed-Friday W7 panel are excluded from this cumulative method sum.', '', '[Canonical aggregate scores](SCORES.json) · [All paired B0/B1 and common-law contrasts](PAIRED_COMPARISONS.csv) · [Whole-offer coverage](MASK_AND_OUTER_COVERAGE.csv) · [Frozen source/code contract](FROZEN_PROTOCOL.json) · [Execution receipt](RUN_RECEIPT.json). This final wave reuses cached loss vectors and original weekly counts only: zero model fits, inference, probability regeneration, source grading, captures or new NFL observations. Production is unchanged.']
    (out/'README.md').write_text('\n'.join(lines)+'\n')
    write(h/'actual-method-w5/CONTRACT_CLARIFICATIONS.json',dict(state='DOCUMENTATION_ONLY_NO_SCORE_OR_SELECTION_CHANGE',parent_protocol='method-comparison-v1/FROZEN_PROTOCOL.json',composite_policy='Shared scorer selects DECISIONS rows where evaluation_week equals frozen protocol evaluation_week=5; original shared prepare literal mentioning W7 is a stale generic description, not actual chosen week.',metadata_annotation='metadata-and-control-k-v1 ran --metadata-only and returns before the shared helper fixed-K branch. Its generic fixed-Friday K text does not define W5 selection; W5 original frozen rolling-greedy K remains authoritative.',source_exposure='W5 football labels were previously exposed in numerical research; historical immutable source retrieval does not reset holdout exposure.'))
    artifact=[]
    for file in sorted(h.rglob('*SCORES.json')):
        rows=json.loads(file.read_bytes());artifact.append(dict(path=file.relative_to(a.root).as_posix(),sha256=sha(file),rows=len(rows)))
    annotation_sources=[]
    ann=h/'actual-method-w5/method-comparison-v1/metadata-and-control-k-v1'
    for name in('SELECTION_PROBABILITY_ANNOTATIONS.json','SELECTION_DENOMINATOR_ANNOTATIONS.json','POINT_PRECISION_ANNOTATIONS.json'):
        file=ann/name;annotation_sources.append(dict(path=file.relative_to(a.root).as_posix(),sha256=sha(file),rows=len(json.loads(file.read_bytes()))))
    origin=h/'actual-method-w5/COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS.json';annotation_sources.append(dict(path=origin.relative_to(a.root).as_posix(),sha256=sha(origin),rows=len(json.loads(origin.read_bytes()))))
    write(h/'H_SCIENTIFIC_HANDOFF.json',dict(at=now(),state='SCIENTIFIC_SCORES_FROZEN_PENDING_ROOT_REGISTRATION_AND_INDEPENDENT_REVIEW',canonical_score_sources=artifact,canonical_source_count=len(artifact),canonical_score_views=sum(r['rows'] for r in artifact),source_bound_annotations=annotation_sources,complete_leaf_default_projection='reports/baselines-coverage-20261031h/actual-method-w5/CURRENT_ACTUAL_METHOD_SCORE_PROJECTION.json',three_week_coverage='reports/baselines-coverage-20261031h/probability/w5-w7-cumulative-v1/MASK_AND_OUTER_COVERAGE.json',baseline_pair_tables=['reports/baselines-coverage-20261031h/probability/reference-v2/PAIRED_REFERENCE_COMPARISONS.json','reports/baselines-coverage-20261031h/probability/w5-reference-v1/PAIRED_REFERENCE_COMPARISONS.json','reports/baselines-coverage-20261031h/probability/w5-w7-cumulative-v1/PAIRED_COMPARISONS.json'],fallback_count_scope='Cumulative P1 selected-side fallback unknown/null; never use parent whole admitted-pool fallback_issued as a selected-side count.',new_fits=0,new_model_inference=0,new_captures=0,production_changed=False))
    print(json.dumps(dict(canonical_sources=len(artifact),canonical_views=sum(r['rows'] for r in artifact),annotation_sources=len(annotation_sources))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);main(p.parse_args())
