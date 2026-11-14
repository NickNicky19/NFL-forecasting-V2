"""Render retained aggregate evidence. No grading, model calls or new scores."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/abc-predictive-improvement-01/b-intercept-v1'


def read(name):
    return json.loads((OUT / name).read_bytes())


def cell(row):
    s = row['selection_metrics']
    n = s['WIN'] + s['LOSS']
    assert n == row['n']
    rate = f'{100 * s["WIN"] / n:.2f}%' if n else 'N/A'
    return f'{s["WIN"]}–{s["LOSS"]}/{n} ({rate})'


def main():
    original_path = ROOT / 'reports/abc-championship/continuation-20261103-v1/original-selected-under-control-v1/SCORES.json'
    original = json.loads(original_path.read_bytes())
    original = {(r['target'], r['side']): r for r in original if r['procedure_id'] == 'B_ORIGINAL_RECORDED'}
    scores = read('SCORES.json')
    targets = ['pass_yd', 'pass_td', 'pass_cmp', 'pass_att', 'pass_int', 'rush_yd', 'rush_att',
               'rec', 'rec_yd', 'rush_rec_yd', 'anytime_td', 'nick-chart-ppr-v1']
    eligible = dict(zip(targets[:10], [28, 28, 28, 28, 28, 87, 43, 174, 175, 42]))
    text = '''# B: targeted exact-line repair and selective reliability

Receptions improved **194/337 → 195/337 correct (+0.30 percentage points)**, but its Brier worsened **0.259868 → 0.260203**. Passing TD direction stayed **14/26** while Brier improved **0.266196 → 0.264826**. Both repaired products still lost the matched **0.25 neutral reference**. The earlier-only selective gate lost the strongest constant on its own selected rows. **The 90% target is not established: the fixed 0.90 gate selected zero picks.**

This is Session B's executed contribution to **ABC-PREDICTIVE-IMPROVEMENT-01**, using C's pinned `ABC-ACTUAL-PROP-CHAMPIONSHIP-v2-C-1` scorer contract (protocol SHA `fa19581487519a854948269bc1ce328cbbcdc734afee2464f1ff778d1ff241a1`). C remains coordinator. This local wave is **not newly C-admitted** and does not complete the W1–8/historical championship. Existing scientific registrations, source restrictions, captures, losses and owner authority remain.

## Table A — original recorded selections, retained Week 8

Each cell is **wins–losses / decided (hit rate)**, grouped by the originally selected side. This table reuses the already completed final grade; it is not a new calculation or a result of B1. All **14 games are final**. Period is **2026 Week 8 only**, separate from Weeks 1–7 and all reconstructed rules. Venue settlement and returns remain unverified.

| Category | Predicted Over | Predicted Under | Combined | Selected/eligible | Unknown O/U |
|---|---:|---:|---:|---:|---:|
'''
    for target in targets:
        if (target, 'Combined') not in original:
            reason = 'No matching offered event' if target == 'anytime_td' else 'No same-chart offer'
            text += f'| {target} | N/A | N/A | N/A | {reason} | — |\n'
            continue
        side = {s: original[target, s] for s in ['over', 'under', 'Combined']}
        for key in ['WIN', 'LOSS']:
            assert side['Combined']['selection_metrics'][key] == sum(side[s]['selection_metrics'][key] for s in ['over', 'under'])
        unknown = [side[s]['selection_metrics']['status_counts']['UNKNOWN_PARTICIPATION'] for s in ['over', 'under']]
        text += f'| {target} | {cell(side["over"])} | {cell(side["under"])} | {cell(side["Combined"])} | {side["Combined"]["forecast_rows"]}/{eligible[target]} | {unknown[0]}/{unknown[1]} |\n'
    text += '''
Total: **Over 109–128/237 (45.99%); Under 96–82/178 (53.93%); combined 205–210/415 (49.40%)**. There were **427 selections/661 eligible offers**, 12 unknown-participation selections (8 Over, 4 Under), no pending results and no statistical pushes. All 427 venue settlements remain unverified. Always-Under on those same 415 decided opportunities scored **224/415**, 19 more wins; that is a control diagnostic, not a proposed future Under policy. Prior W5–7 originals and fixed-Friday W7 remain separately indexed and unchanged; this table is not cumulative W1–8. Earlier missing periods/source gates remain in the existing week-gap table.

## Table B — actual procedures in this controlled wave

Requested current period is **2026 W1–8**. Receptions actually evaluates **W2–3** on C's Pinnacle board: 362 opportunities, 32 games, 340 probability outputs and 337 resolved appearances. Passing TD actually evaluates **W8**: 28 opportunities/14 source games, 26 retained C02 probability outputs/13 games, two Thursday outputs unavailable. These panels have different source/decision products and are not pooled into an eight-week record.

Full procedure IDs use prefix `B::ABC-PREDICTIVE-IMPROVEMENT-01-B-INTERCEPT-v1::<category>::`. B0 is unchanged **C P3_HGB/H-MULTI/E0_OP** for receptions, and the **C02 H-MULTI historical-to-original-W8-capture transfer adapter** for passing TD. B1 applies the single earlier-trained intercept to that same baseline. `ALL` chooses the higher exact-line Over/Under probability, ties abstain. There are no confidence abstentions in ALL; missing laws remain unavailable.

| Category | Exact arm / history / product / rule | Actual weeks | Own native point error | Over | Under | Combined | Eligible/selected/unavailable | Brier |
|---|---|---|---|---:|---:|---:|---:|---:|
'''
    for target in targets:
        if target not in ['rec', 'pass_td']:
            reason = 'No matching actual offer' if target == 'anytime_td' else 'No exact-chart actual offer' if target == 'nick-chart-ppr-v1' else 'New mechanism queued; prior methods/results retained'
            text += f'| {target} | N/A: {reason} | — | N/A | N/A | N/A | N/A | — | N/A |\n'
            continue
        for arm in [0, 1]:
            wk = 'ALL' if target == 'rec' else '8'
            rr = [r for r in scores if r.get('side') and r['target'] == target and str(r['week']) == wk and r['procedure_id'].endswith('::B' + str(arm)) and r['strategy'] == 'ALL']
            side = {r['side']: r for r in rr}
            assert len(side) == 3
            proper = next(r for r in scores if r['record_kind'] == 'prop_threshold_probability_evaluation' and r['target'] == target and str(r['week']) == wk and r['procedure_id'].endswith('::B' + str(arm)))
            s = side['Combined']['selection_metrics']
            point = 'N/A: event product; original mean ancillary 1.04768 TD' if target == 'pass_td' else 'N/A: direct event product'
            text += f'| {target} | B{arm} / H-MULTI / exact-line probabilities / ALL | {"2–3" if target == "rec" else "8"} | {point} | {cell(side["over"])} | {cell(side["under"])} | {cell(side["Combined"])} | {s["selection_pool_count"]}/{side["Combined"]["forecast_rows"]}/{s["technical_unavailable"]} | {proper["brier"]:.6f} |\n'
    text += '''
Receptions B1 is the observed full-board direction leader **within this controlled two-arm comparison**. B0 leads its probability score. Passing TD ties direction; B1 leads its Brier, with no demonstrated improvement over neutral. Neither is a validated category champion or automatic release recommendation. Existing point-MAE, separate side maxima and complete-method rankings remain at their own retained panels in the [prior local report](../../abc-championship/continuation-20261103-v4/B_PERIOD_COMPARISON_REPORT.md) and [complete-law continuation](../../abc-championship/leaf-law-continuation-20261104-v2/README.md). No one method's Over and another's Under were spliced into a combined procedure.

## What changed and what was held fixed

The diagnosed pattern was low average forecast Over probability and weak reliability on held-earlier actual lines. The one allowed change is a game-weighted **single intercept**, slope fixed at one, with a strong zero-centered prior. For a valid baseline CDF value, `g(x)=sigmoid(logit(x)-alpha)` preserves exact endpoints. Under is `g(p_under)`, push is `g(p_under+p_push)-g(p_under)`, and Over is the complement. No point-to-probability conversion, independent side calibration, artificial evaluation lines, clipping away impossible observations, or base-classifier refit occurs.

Fit loss is the sum of game-average binary log losses plus `alpha²/(2*0.5²)`, bounded alpha ±1.5, with no parameter search. A fit needs 20 resolved earlier rows, five games and three outcomes in each class; otherwise the registered identity fallback applies. Labels are conservatively eligible strictly after kickoff + seven days. This rule is a reconstruction assumption, not authenticated source publication history. C's rec model/gates update by original decision batch; passing TD coefficients freeze before the first W8 game using eligible W6 cases. W5 selected the base recipe, and earlier W7 temporal OOF predictions set the confidence gate; those development rows are not new W8 observations.

The historical C02 query recipe and the original future capture adapter are different products. Their transfer is explicitly registered; ordinary Leaf results do not authenticate this exact adapter in older seasons. All studied periods were already research-exposed. Current fitted repair parameters were computed November 4, with simulated origins retained separately; B1 and B2 were not originally issued picks.

Closest completed calibration work remains visible: C's two-parameter 2025 synthetic-grid sigmoid lost for receptions (0.1172677→0.1175754) and passing TD (0.1462724→0.1465855). Those differently normalized scores are not compared numerically with actual-offer Brier. This is a changed one-parameter, strongly pooled, actual-line continuation, not a claim that calibration is new. A retains its market-reception study; B did not duplicate it. All prior B GLM/leaf proper-score losses remain indexed.

## Selection coverage and strong controls

B2 uses the median earlier OOF confidence, floor 0.60 and minimum 20 earlier probabilities; it learns no correctness labels. Each atomic original-decision batch has equal B0/B1 selection count, limited by each arm's qualified candidates. Each arm ranks its own probabilities with stable offer-ID ties. This tests achieved coverage; it does not assume every selected forecast is calibrated or equally easy.

| Category/arm/policy | Over | Under | Combined | Selected/eligible | Same-selected strongest control |
|---|---:|---:|---:|---:|---|
'''
    for target in ['rec', 'pass_td']:
        for arm in [0, 1]:
            rr = [r for r in scores if r.get('side') and r['target'] == target and str(r['week']) == ('ALL' if target == 'rec' else '8') and r['procedure_id'].endswith('::B' + str(arm)) and r['strategy'] == 'B2_MATCHED_EARLIER_CONFIDENCE']
            side = {r['side']: r for r in rr}
            c = side['Combined']
            control = 'Always-Under 87/160' if target == 'rec' else 'Always-Over 7/13' if arm == 0 else 'Always-Under 7/13'
            text += f'| {target} / B{arm} / B2 | {cell(side["over"])} | {cell(side["under"])} | {cell(c)} | {c["forecast_rows"]}/{c["selection_metrics"]["selection_pool_count"]} | {control} |\n'
    text += '''
Receptions selected 161/362 (44.48%), with one selected unknown; both arms scored 85/160 (53.12%). Passing TD selected 13/28 (46.43%); B0 scored 5/13 and B1 6/13. That +7.69-point own-pool difference has game sensitivity **−7.63 to +23.01 points**, involves changed selected pools and still loses 7/13 to a matched constant. It is not a clean one-row architecture gain or useful 90% performance.

On the full common resolved board, rec B1's +0.30-point hit-rate change has descriptive game-cluster 95% sensitivity **−1.47 to +2.06 points**. Its Brier change is **+0.000334** (worse), sensitivity **−0.000910 to +0.001579**. Passing-TD Brier change is **−0.001370**, sensitivity **−0.008830 to +0.006090**. Its direction decisions are identical, so the observed paired direction difference is exactly zero; that does not certify future equality. There are only two rec weeks and one PT week: insufficient week clusters, exposed data, no selection/multiplicity correction.

The same-mask earlier simple probability references also lose neutral: rec **0.283621**, PT **0.279936**. B1 beats those weak references without beating 0.25. Matched constants and prior references are in [selected controls](MATCHED_SELECTED_CONTROL_SCORES.json) and [proper baselines](REFERENCE_PROBABILITY_SCORES.json). Constant directions with 0.50 event probabilities are control policies, not newly trained probability models. Prices, paired venue settlement and closing evidence are unqualified, so EV/ROI/CLV remain unavailable.

Discrimination does not improve: full rec Over AUC **0.532884→0.528758**; PT **0.491124→0.491124**. A single fixed intercept preserves its within-fit ranking, but changing rolling intercepts can change pooled rec rankings. Mean predicted Over moved toward prevalence (rec 0.39061→0.39765 versus actual 0.46291; PT 0.44712→0.46238 versus actual 0.5), while rec proper scores still worsened. These patterns do not identify a cause or validate another correction.

## Frozen top-K and player/workload views

The prior Top-K policies are unchanged. New rolling K6/10/20 here are per category/week, separately Combined/Over-only/Under-only, floor 0.60, chronological original decision batches, earliest batches fill remaining slots, no replacement or forced weak picks. They are retrospective rolling policies, not fixed weekly lists or original tickets. No cross-category raw-unit-gap ranking is used.

B1 combined rolling K6/10/20: rec **3/11, 11/19, 25/39**, selected **12/20/40** with one unknown in each cumulative policy; PT **3/6, 4/10, 6/13**. K is per week: rec spans two weeks. Full side lists are in [weekly and cumulative side table](WEEKLY_AND_CUMULATIVE_SIDE_TABLE_V2.csv). These are not six-leg tickets or a 90% result.

Player ranks reuse the original frozen mean of earlier opportunities, not outcomes or pick confidence; rec opportunities are targets, passing opportunities are attempts. Identical competitor membership is preserved. W2–3 historical participant membership and W8 original future-query membership remain distinct. There are 340 matched rec memberships and 26 PT memberships; missing-law rows remain in the unavailable/missing-membership census, not deleted.

| Cohort | rec B0→B1 wins/decided | PT B0→B1 wins/decided |
|---|---|---|
| Active fitted repair, common rows | 41/64→42/64 (65 issued; one unknown) | 14/26→14/26 |
| Top 10 players | 8/19→9/19 | 6/10→6/10 |
| Top 15 players | 13/28→14/28 | 8/15→8/15 |
| Top 20 players | 19/38→20/38 | 10/18→10/18 |
| Disjoint 11–15 | 5/9→5/9 | 2/5→2/5 |
| Disjoint 16–20 | 6/10→6/10 | 2/3→2/3 |
| Remainder rank 21+ | 171/290→171/290 | 4/8→4/8 |
| High earlier workload | 16/33→17/33 | 5/8→5/8 |
| Middle earlier workload | 107/183→108/183 | 9/18→9/18 |
| Low earlier workload | 66/111→65/111 | N/A: no eligible members |

Role reversal is retained: rec RB **47/82→46/82**, WR **99/177→99/177**, TE **48/78→50/78**. This is a descriptive pattern, not a validated role router. B1 had 65 rec active-repair outputs and 275 identity outputs; 22 base laws were unavailable. Identity fallback is not a base-football fallback or deliberate confidence abstention. PT has 26 original base-learned outputs and two unavailable Thursday queries.

[Common cohort scores](COMMON_COHORT_SCORES.json) include own Over/Under/Combined for ALL. [Policy/cohort scores](POLICY_COHORT_SCORES.json) cover the remaining 14 policies across the same 20 fixed cohorts, all original periods, with no subgroup reranking or refilling. These are overlapping diagnostic views, not extra NFL trials.

## 90% target and recommendation

Both arms selected **zero** at confidence ≥0.90. Accuracy is **N/A**, coverage **0%**, status **TARGET_NOT_ESTABLISHED**. The separate PT ≥0.80 rule observed **1/1** at 3.57% of eligible offers; ≥0.70 B1 also has 1/1. Those tiny exposed maxima remain visible without becoming category-wide 100% claims. No gate was searched until it reached 90%, no picks were inverted, and no bias was added from evaluated outcomes.

The study's predeclared +1-point practical-improvement planning target was not met on the full board. Do **not recommend a production switch from this repair**. Existing independently eligible packages retain their own provisional owner policy; this result introduces no universal future-evidence, full-history or eight-week waiting gate. Scientific 90% claim criteria and the owner's provisional-release policy remain separate.

The reusable adapter is [exact_line_repair.py](../../../nfl_v2/exact_line_repair.py): exact-line input binding, coherent three-state output, identity fallback for insufficient earlier support, no output when the base law is unavailable. Single-line C direct inputs do not establish a complete CDF. The monotone transform preserves a valid base order but cannot authenticate unretained cross-line predictions. Changed/unbound lines require owner recomputation and consistency checks, never nearest-grid substitution. Coefficients/rows are retained privately; no offhost restoration claim is made. New method capture starts only when actually admitted and persisted under the existing owner route.

## Execution, verification, recovery and next action

This wave executed **six scalar calibration fits**, zero new football fits/model inference, 391 probability applications, zero new original forecasts or NFL observations. Original retained evaluation universe is 362 rec plus 28 PT opportunities; 337 and 26 outcomes qualify, respectively. Rec spans 32 games; PT has 13 scored/14 source games. No original recommendation was changed.

Measured primary run: **0.906 seconds wall / 0.906 CPU, 164,745,216 bytes peak RSS, 517,786 new private bytes** under the bounded 4 MiB private allocation. All original and amended prepared inputs, failures and hashes remain. The declared two-thread cap was **not demonstrably enforced** in the original six tiny scalar fits; active fit threads were unrecorded. That resource nonconformance is disclosed in [RESOURCE_QUALIFICATION.json](RESOURCE_QUALIFICATION.json). The new guarded future entrypoint explicitly limits thread pools and refuses completed outputs; it was not used to rewrite these results.

Independent calculations reproduced all six fitted intercepts by separate bisection, chronology and future-mutation invariance, side partitions, proper scores, selected controls, original mean attribution, all frozen memberships and policy/cohort partitions. Representative source identity/line/capture bindings match the original retained rows. Software fixtures and thousands of views add no new NFL samples. The original point mean is separately indexed as an unchanged ancillary product: MAE **1.047685 TD**, bias **−0.026023**, RMSE **1.201537**, P95 absolute error **1.511364**, strict and inclusive one-TD tolerance **13/26**. It is not the mean of a repaired outcome law or a constant-side forecast. Source-bound metadata prevents those borrowed errors from entering the event/control numeric rankings.

Before publication, the shared aggregation helper was found to have inherited C's kickoff/Pinnacle source labels for B's passing-TD controls and cohort views. [Source-clock qualification](SOURCE_CLOCK_AND_ATTRIBUTION_QUALIFICATION_V3.json) corrects those metadata in the default **results-index-v5**, with exact [source bindings](SOURCE_AND_CLOCK_BINDINGS.json); all source SCORES, old annotations and all four unpublished index drafts remain. The final [exposure correction](FINAL_SOURCE_CLOCK_EXPOSURE_V4.json) also preserves the bound horizon directly on numeric/probability index records. No probability, selection, outcome or score changed. Consumers must apply the bound source-clock annotations instead of copying generic raw-score labels.

The exact current full-period gaps are in [METHOD_PERIOD_COVERAGE_ADDITION.json](METHOD_PERIOD_COVERAGE_ADDITION.json) and the existing [week/source gap overlay](../../abc-championship/continuation-20261103-v4/B_EXACT_WEEK_GAP_OVERLAY.csv). For this repair, earlier actual-line calibration/origin rows and qualified annual thresholds are not yet received for 2022–2025. A's public annual aggregates are not B raw-row access. Completed B base numerical historical tests remain reused; no Leaf result substitutes for older D1/D2.

The last verified large recovery backlog remains **38 parts / 796,917,760 bytes**, not a new quota observation. It gates the **147 original strict-HGB origins** and **736 older exact D1/D2 output cells**, plus their relevant training-window/source extensions. Existing approved uploader/account/capacity qualification and missing-only upload, complete download/reassembly and inner/whole-hash restoration are required. No repeated bulk attempt, data deletion, sharing change or new destination occurred. New tiny scalar work does not waive that large-fit gate; unrelated ready owner captures remain independent.

At **November 4, 2:56 p.m. CST**, production readback shows a new successful owner scheduled action **41909390038** and immutable published reference packet prepared **2:45 p.m. CST**. The new classic packet is **12 Overs + 12 Unders = 24**, across **11 games**, all CURRENT_BASELINE / sleeper-matchup-classic-fg-identity-v1. The adaptive overlay remains DISABLED_USE_R0, zero selected-model rows. Both pointer/payload byte pairs match their served endpoints. This supersedes only the old current-status observation; old packets remain unchanged. Browser consumption was not inspected. B1 admission, B1 capture and a B-caused release are **not verified**. See [owner execution](CURRENT_OWNER_STATUS.json) and [actual selection counts](CURRENT_OWNER_SELECTION_COUNTS.json).

**Next executable package:** C intake of the new immutable B export and a permitted next-origin B0 exact-line probability/input binding; B then freezes/persists any new repair/gate evaluation before outcomes through the existing owner route. A point-only classic packet cannot supply probabilities. Historical extensions need qualified annual offer clocks and exact-origin baseline probability rows, independently of missing original picks. The retained recovery-dependent exact seasonal queue stays open. This controlled repair is complete for its named cells; the full category championship and historical claim remain partial.

[Frozen binding](CURRENT_EXECUTION_BINDING.json) · [original protocol](FROZEN_PROTOCOL.json) · [prefit metadata amendment](FROZEN_PROTOCOL_V2.json) · [canonical scores](SCORES.json) · [all new score sources](NEW_CANONICAL_SCORE_MANIFEST_V2.json) · [paired loss index](paired-analysis-index-v1/ANALYSIS_MANIFEST.json) · [permanent results](results-index-v5/README.md) · [90% status](TARGET_90_STATUS.json) · [independent source check](INDEPENDENT_PROBABILITY_SOURCE_BINDINGS_V1.json) · [independent controls/cohorts/typing](INDEPENDENT_SUPPLEMENT_CONTROLS_COHORTS_AND_TYPING_V1.json) · [independent policy partitions](INDEPENDENT_POLICY_COHORT_PARTITIONS_V1.json) · [final index/source-clock check](INDEPENDENT_SOURCE_CLOCK_AND_INDEX_PROJECTION_V4.json).
'''
    destination = OUT / 'B_PREDICTIVE_IMPROVEMENT_REPORT.md'
    if destination.exists():
        raise ValueError('Do not overwrite an already retained report version')
    destination.write_text(text)
    print(destination.relative_to(ROOT))


if __name__ == '__main__':
    main()
