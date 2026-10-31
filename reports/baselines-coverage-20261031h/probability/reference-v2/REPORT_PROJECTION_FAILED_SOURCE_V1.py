"""Public presentation and coverage projection of completed H baseline scores."""
import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import sha,write
from tools.numerical_championship import csvwrite


def main(a):
    p=a.output
    scores=json.loads((p/'SCORES.json').read_bytes())
    comparisons=json.loads((p/'PAIRED_REFERENCE_COMPARISONS.json').read_bytes())
    diagnostics={r['record_id']:r for r in json.loads((p/'CALIBRATION_AND_DISCRIMINATION.json').read_bytes())}
    publiccache={}
    universe=collections.defaultdict(dict)
    for row in scores:
        for source in row['source_records']:
            path=a.root/source['source_artifact']
            if path not in publiccache:
                if sha(path)!=source['source_artifact_sha256']:raise ValueError('bound public source changed')
                publiccache[path]=json.loads(path.read_bytes())
            r=publiccache[path][source['source_row_index']]
            week=r['evaluation_weeks'][0]
            universe[r['target']][week]=r['forecast_rows']
    coverage=[]
    for row in scores:
        if row['reference_id']!='candidate' or row['fallback_view']!='FULL':continue
        sources=[publiccache[a.root[s['source_artifact']]][s['source_row_index']] for s in row['source_records']]
        outer=sum(universe[row['target']][w] for w in row['evaluation_weeks'])
        admitted=sum(r['admitted_forecast_rows'] for r in sources)
        supported=sum(r['n'] for r in sources)
        coverage.append(dict(record_id=row['record_id'],target=row['target'],procedure_id=row['matched_candidate_procedure_id'],history_regime=row['history_regime'],strict_current_information=row['strict_current_information'],evaluation_weeks=row['evaluation_weeks'],source_recipe_weeks=sorted({w for r in sources for w in r['evaluation_weeks']}),outer_source_offer_universe=outer,admitted_law_rows=admitted,unavailable_law_rows=outer-admitted,qualified_probability_and_outcome_mask=supported,admitted_missing_or_unknown_outcome_rows=admitted-supported,qualified_probability_mask_coverage=supported/outer if outer else None,baseline_comparison_n=row['n'],candidate_source_prior_rows=row['candidate_prior_rows'],source_records=row['source_records'],coverage_note='H forecast_rows is the retained qualified comparison mask, not the source universe; FULL means full qualified mask before learned/prior partition.'))
    write(p/'MASK_AND_OUTER_COVERAGE.json',coverage)
    csvwrite(p/'MASK_AND_OUTER_COVERAGE.csv',coverage)
    common=[]
    bykey=collections.defaultdict(dict)
    for row in scores:
        if row['fallback_view']!='FULL' or row['evaluation_weeks']!=[6,7]:continue
        key=(row['target'],row['matched_candidate_procedure_id'],row['history_regime'])
        bykey[key][row['reference_id']]=row
    for key,refs in sorted(bykey.items()):
        candidate=refs['candidate']
        common.append(dict(target=key[0],procedure_id=key[1],history_regime=key[2],strict_current_information=candidate['strict_current_information'],n=candidate['n'],candidate_brier=candidate['brier'],neutral_brier=refs['B0']['brier'],earlier_prevalence_brier=refs['B1']['brier'],candidate_decisive_auc=diagnostics[candidate['record_id']]['decisive_over_auc'],neutral_decisive_auc=diagnostics[refs['B0']['record_id']]['decisive_over_auc'],earlier_prevalence_decisive_auc=diagnostics[refs['B1']['record_id']]['decisive_over_auc'],candidate_minus_neutral=candidate['brier']-refs['B0']['brier'] if candidate['n'] else None,candidate_minus_prevalence=candidate['brier']-refs['B1']['brier'] if candidate['n'] else None,source_records=candidate['source_records']))
    write(p/'CUMULATIVE_PRIMARY_BASELINE_TABLE.json',common)
    csvwrite(p/'CUMULATIVE_PRIMARY_BASELINE_TABLE.csv',common)
    display=collections.defaultdict(dict)
    for r in common:
        if r['history_regime']!='H-MULTI' or r['strict_current_information']:continue
        proc=r['procedure_id']
        family='C02' if 'c02' in proc else 'Leaf' if 'ordered_leaf_cdf' in proc else 'GLM' if 'regularized_glm_law' in proc else None
        if family:display[r['target']][family]=r
    lines=['# Actual-line probability references: what the models beat', '',
      '**The stronger comparison changes the conclusion:** on the same rolling Weeks 6–7 H-MULTI offers, Leaf and C02 improve Brier over GLM in nine of ten categories, but each beats the neutral 50/50 reference in only two: passing touchdowns and interceptions. Each beats the earlier same-position prevalence reference in eight categories, losing passing attempts and completions. These are observed differences on two exposed weeks, not established future superiority.', '',
      '| Category | Paired n | Neutral Brier | Earlier prevalence | Leaf Brier | C02 Brier | GLM Brier |',
      '|---|---:|---:|---:|---:|---:|---:|']
    for target,rr in sorted(display.items()):
        leaf=rr['Leaf'];lines.append(f"| {target} | {leaf['n']} | {leaf['neutral_brier']:.6f} | {leaf['earlier_prevalence_brier']:.6f} | {leaf['candidate_brier']:.6f} | {rr['C02']['candidate_brier']:.6f} | {rr['GLM']['candidate_brier']:.6f} |")
    lines += ['',
      'For passing attempts (52 matched offers), Leaf Brier is **0.264387**, worse than neutral **0.250000** and earlier prevalence **0.261553**, even though it beats GLM **0.360829**. Leaf minus neutral is +0.014387; its game-cluster sensitivity 95% interval is [−0.015123, +0.043897]. The difference from earlier prevalence is +0.002835, interval [−0.025923, +0.031593].', '',
      'For passing touchdowns (52 offers), Leaf improves 0.250000→0.226881 against neutral; difference −0.023119, interval [−0.047364, +0.001127]. Against earlier prevalence 0.237526, its difference is −0.010644, interval [−0.043528, +0.022240]. These intervals show how limited two weeks remain. The registered week-based interval is unavailable with only two clusters; game intervals are descriptive sensitivity analyses without multiplicity or selection adjustment.', '',
      'The constant reference assigns Over=0.5, Under=0.5, Push=0 at each threshold. Its half multiclass Brier is 0.25 for decisive outcomes, 0.75 for pushes; push log loss is infinite. It is a threshold-local neutral reference, not a global CDF or an authenticated bookmaker forecast. No statistical pushes occur on the retained evaluated panel.', '',
      'The prevalence reference counts earlier positively verified participants at the same position and exact target, evaluating their official full-game outcomes against the query line. Every consumed kickoff+7-day availability time must be strictly before the actual decision clock. H-CURRENT uses 2026, H-RECENT uses 2025–2026, H-MULTI starts in 2022. Strict-current candidate rows use a separate 2026-only reference with no older football priors, features or calibration. Empty history explicitly falls back to the neutral reference; it never borrows older seasons. No smoothing was added, so genuine zero-probability log losses remain infinite.', '',
      'Same-position historical participants may differ from offered stars, promoted roles or replacements. This simple reference measures whether additional forecasting complexity improves the offered-event score; it does not isolate a causal player or defense effect. Current-season fitting with older feature memory remains different from strict-current information. The machine tables preserve both, every history, weekly reversals and all supported parametric law subsets; no method or sparse case was removed after scoring.', '',
      '`FULL` means the entire **qualified saved-law/outcome comparison mask**, not every offered opportunity. [Outer coverage](MASK_AND_OUTER_COVERAGE.csv) retains the source universe, law admission failures and unavailable outcomes. For example, a 52-row cumulative passing comparison is drawn from a larger original source offer universe. LEARNED and PRIOR views partition that mask using explicit retained-law origins; baseline empty-prefix fallback is a separate field.', '',
      'Fixed ten-bin per-region reliability diagrams and decisive-outcome rank AUC are [separate diagnostics](CALIBRATION_AND_DISCRIMINATION.json). The AUC uses only actual nonpush outcomes and over/(over+under); it does not replace the three-region proper score. Constant forecasts have AUC 0.5 if both classes occur and N/A for a single class. These diagnostics do not fit or validate a calibrator.', '',
      'This wave evaluates probabilities only: it adds no selected-side, price-aware, top-K or settlement strategy. Existing G original selections and P1/P2 scorecards remain unchanged. Authenticated price/status evidence is absent, so market probabilities, EV, ROI and CLV remain unestablished. No point-to-probability transformation, model inference, fit, capture or Week 8 outcome read occurred.', '',
      '[All histories and strict arms](CUMULATIVE_PRIMARY_BASELINE_TABLE.csv) · [Canonical scores](SCORES.json) · [All paired differences and uncertainty](PAIRED_REFERENCE_COMPARISONS.csv) · [Frozen protocol](FROZEN_PROTOCOL.json) · [Resource/evidence receipt](RUN_RECEIPT.json).', '',
      'The first preparation attempt failed on a path-type typo before reading prior values or G losses and produced no scores. Its original source, protocol and failure receipt remain in `../reference-v1/`; this successful independently identified version preserves them.']
    (p/'README.md').write_text('\n'.join(lines)+'\n')
    write(p/'REPORT_PROJECTION_RECEIPT.json',dict(code_sha256=sha(__file__),source_scores_sha256=sha(p/'SCORES.json'),source_pairs_sha256=sha(p/'PAIRED_REFERENCE_COMPARISONS.json'),source_diagnostics_sha256=sha(p/'CALIBRATION_AND_DISCRIMINATION.json'),coverage_rows=len(coverage),cumulative_rows=len(common),new_scores=0,new_fits=0,new_inference=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
