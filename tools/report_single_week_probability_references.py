"""Readable projection of an already completed single-week H probability wave."""
import argparse
import collections
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from nfl_v2.shared_subgroups import sha,write
from tools.numerical_championship import csvwrite


def main(a):
    out=a.output;ss=json.loads((out/'SCORES.json').read_bytes());group=collections.defaultdict(dict);coverage=[];cache={}
    for r in ss:
        if r['fallback_view']=='FULL':group[r['target'],r['matched_candidate_procedure_id'],r['history_regime']][r['reference_id']]=r
    table=[]
    for (target,proc,arm),refs in sorted(group.items()):
        c=refs['candidate'];sources=[]
        for b in c['source_records']:
            path=a.root/b['source_artifact']
            if path not in cache:
                if sha(path)!=b['source_artifact_sha256']:raise ValueError('public source changed')
                cache[path]=json.loads(path.read_bytes())
            sources.append(cache[path][b['source_row_index']])
        outer=sum(r['forecast_rows'] for r in sources);admitted=sum(r['admitted_forecast_rows'] for r in sources)
        coverage.append(dict(record_id=c['record_id'],target=target,procedure_id=proc,history_regime=arm,strict_current_information=c['strict_current_information'],qualified_mask_n=c['n'],outer_source_offer_universe=outer,admitted_law_rows=admitted,unavailable_law_rows=outer-admitted,admitted_missing_or_unknown_outcome_rows=admitted-c['n'],coverage=c['n']/outer if outer else None,source_records=c['source_records']))
        table.append(dict(target=target,procedure_id=proc,history_regime=arm,strict_current_information=c['strict_current_information'],n=c['n'],candidate_brier=c['brier'],neutral_brier=refs['B0']['brier'],earlier_prevalence_brier=refs['B1']['brier'],candidate_minus_neutral=c['brier']-refs['B0']['brier'] if c['n'] else None,candidate_minus_prevalence=c['brier']-refs['B1']['brier'] if c['n'] else None,source_records=c['source_records']))
    write(out/'PRIMARY_BASELINE_TABLE.json',table);csvwrite(out/'PRIMARY_BASELINE_TABLE.csv',table);write(out/'MASK_AND_OUTER_COVERAGE.json',coverage);csvwrite(out/'MASK_AND_OUTER_COVERAGE.csv',coverage)
    display=collections.defaultdict(dict)
    for r in table:
        if r['history_regime']!='H-MULTI' or r['strict_current_information']:continue
        family='C02' if 'c02' in r['procedure_id'] else 'Leaf' if 'ordered_leaf' in r['procedure_id'] else 'GLM' if 'regularized_glm' in r['procedure_id'] else None
        if family:display[r['target']][family]=r
    lines=['# Week 5 probability references','','This newly supported week changes which categories beat the neutral reference. H-MULTI Leaf and C02 beat neutral Brier 0.25 for **passing attempts and interceptions**, while passing touchdowns loses. In Weeks 6–7, passing touchdowns and interceptions beat neutral while passing attempts loses. On Week 5 each procedure beats the earlier same-position prevalence reference in six of ten categories; both lose passing attempts, completions, interceptions and passing yards. These are descriptive weekly reversals, not an earlier-executable method selector.','','| Category | Matched n | Neutral | Earlier prevalence | Leaf | C02 | GLM |','|---|---:|---:|---:|---:|---:|---:|']
    for target,rr in sorted(display.items()):
        r=rr['Leaf'];lines.append(f"| {target} | {r['n']} | {r['neutral_brier']:.6f} | {r['earlier_prevalence_brier']:.6f} | {r['candidate_brier']:.6f} | {rr['C02']['candidate_brier']:.6f} | {rr['GLM']['candidate_brier']:.6f} |")
    lines += ['', 'Only Week 5 was newly evaluated here; the completed Weeks 6–7 baseline files were not regenerated. The new source panel covers 14/15 games and 617 original thresholds, with 606 supported qualified outcomes. Exact candidate masks and history/strict arms remain separate. `FULL` means all qualified saved-law/outcome rows, not all offered opportunities; outer coverage and all exclusions are retained in the linked table.', '', 'B0 is the threshold-local Over=.5/Under=.5/Push=0 reference, not an authenticated market or global CDF. Its Brier is .25 on decisive outcomes and .75 on pushes, with infinite log loss on a push. B1 uses unsmoothed earlier same-position, same-target official full-game outcomes at the exact offered line; kickoff+7d availability must be strictly before each decision clock. CURRENT uses2026, RECENT2025–26, MULTI2022–26. Existing strict candidates receive a2026-only baseline without older priors/features/calibration. Empty prefixes explicitly use B0. No result-dependent calibration or source-lag repair occurs.', '', 'Per-region calibration bins and decisive-event AUC are diagnostic outputs, not fitted calibration or a new selection rule. True-zero probabilities retain infinite log losses. Game-cluster paired intervals are descriptive and unadjusted for selection/multiplicity; one week cannot support the registered whole-week uncertainty method. Conditional modeled appearance is distinct from bookmaker nonvoid settlement. No prices, EV, ROI, CLV or betting profitability are established.', '', '[All methods/history/strict arms](PRIMARY_BASELINE_TABLE.csv) · [Outer coverage](MASK_AND_OUTER_COVERAGE.csv) · [Canonical scores](SCORES.json) · [Paired errors and uncertainty](PAIRED_REFERENCE_COMPARISONS.csv) · [Calibration/discrimination diagnostics](CALIBRATION_AND_DISCRIMINATION.json) · [Frozen protocol](FROZEN_PROTOCOL.json) · [Resource/evidence receipt](RUN_RECEIPT.json).']
    (out/'README.md').write_text('\n'.join(lines)+'\n');write(out/'REPORT_RECEIPT.json',dict(code_sha256=sha(__file__),source_scores_sha256=sha(out/'SCORES.json'),primary_rows=len(table),coverage_rows=len(coverage),new_scores=0,new_fits=0,new_inference=0))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--output',type=Path,required=True);main(p.parse_args())
