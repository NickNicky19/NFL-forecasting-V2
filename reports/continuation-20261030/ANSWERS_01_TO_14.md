# Fourteen answers: October30 executed continuation

Evidence is **NEW_EXPERIMENT**, with separate **REPRODUCED_FROM_DATA** scorer/model-prefix checks and **VERIFIED_FROM_CODE** mechanism traces. Earlier reported/private experiments retain their earlier labels; this is not a lifetime census or untouched confirmation. [Category numbers](TWELVE_CATEGORY_SUMMARY.md), [all score views](results-index/README.md), [grid](EXPERIMENT_GRID.csv), and [completeness](INVENTORY_COMPLETENESS.md).

## Q1. How did we test every forecasting method?

We have not authenticated every historical method. We executed three additional bounded fitting waves:704 distribution cells,224 count/role cells and64 chart cells. They produced840 unique new NFL fits plus152 no-fit fallback cells. The first failed version's57 models were reused, not refitted. A completed fit, forecast product, source alias and evaluation view remain different counts.

Exact implementations/configurations are [distribution laws](../../nfl_v2/distribution_laws.py), [failed/original distribution runner](../../nfl_v2/distribution_wave.py), [recovery](../../nfl_v2/distribution_wave_v2.py), [count/role ablations](../../nfl_v2/count_ablations.py) and [chart adapter](../../nfl_v2/chart_sources.py), bound to their frozen protocols and source hashes. Objectives, parameters, priors, weekly fit/per-game refresh rules, fallbacks and comparators are recorded per run. Numerical replay independently checks all2,736 distribution,424 count and208 chart-direct score views. Next: another registered mechanism/source ablation, not a renamed seed.

## Q2. Which years did every method test?

New learned reconstructions train on eligible2026,2025–2026 or2022–2026 outcomes and evaluate identical2026 Weeks1–7 query identities,107 games. STRICT-CURRENT restricts training, historical training-row features, priors and transforms to2026; common-memory H-CURRENT only restricts fitting. [Source-bound dates](distribution-wave-v2/SCORE_DATE_PROJECTION.json) include actual learned-only supported weeks; they do not replace missing periods with zeros.

Empirical football and chart controls have rolling2022–2026 results, with expanding-from2022 startup. Chart has2,394 current query rows/2,359 supported labels. New learned models have not yet completed all2022–2025 rolling evaluation origins. That is executable queued work, not evidence they were tested on those evaluation seasons merely because they trained on them.

## Q3. What are all methods tested so far, and what years did they use?

The permanent index retains old4,832 reported views, original replays, later-label evidence, empirical/HGB controls and all new versions. Four newly executable families are empirical, HGB, ordered leaf-CDF and regularized GLM law; HGB losses/objectives/role variants remain distinct procedures within one family. [Legacy reconciliation](distribution-wave-v1/LEGACY_MECHANISM_RECONCILIATION.json) links old Leaf/ordered/count recipes to pinned code and distinguishes reconstructions from original issuance.

The original private attempt census, instruction amendments and exact complex-model/query bindings remain incomplete. The earlier5,408 provisional cells are not a lifetime-method denominator. [Current completeness](INVENTORY_COMPLETENESS.md) preserves failed versions and unresolved references. Next: recover compatible owner exports and continue the next supported reconstruction wave independently.

## Q4. How exactly did we determine workload?

The common direct-model inputs actually consumed are target-history mean/count3/8, four ordered values/age/missing indicators and four position indicators. They do not contain routes, snap exposure, target-game attempts or invented injury penalties. [Raw-prefix checks](DISTRIBUTION_INDEPENDENT_PREFIX_REVIEW.json) rebuild actual training/query values and strict-policy floors.

Separate [pregame cohort views](pregame-cohort-scorecards-v2/SCORES.csv) rank mean prior3 available attempts for passing, carries for rushing, targets for receiving, and carries+targets for combined yards/TD. Missing slots consume the window. Cutoff is the week's earliest scheduled kickoff minus90minutes under the disclosed seven-day availability policy. Every competitor uses identical frozen rank/workload membership, including unknowns; these historical queries still come from retrospective stat rows. No target-game outcome defines a role or rank. Full/limited/replacement injury states remain unqualified, not inferred from a workload field. Next: a qualified role/availability addition with the learner fixed.

## Q5. How are similar players compared and how does defense enter?

Leaf-CDF weights are equal-tree terminal-leaf empirical masses, mixed95/5 with the registered same-arm role prior. This is partition-based weighting, not learned chronological TabR or a direct nearest-neighbor distance. The GLM fits pooled relationships with regularization and position indicators; it does not retrieve historical neighbors. All contributing labels satisfy registered chronology and support.

These new models do not consume opponent/defense features. Same position or a shared leaf does not establish matchup adjustment. Independent law replay reconstructs1,386 representative distribution laws without production scoring calls, and retains both wins and losses. Next: no-defense versus one justified opponent feature block on identical rows; new learned retrieval remains a separate queued mechanism.

## Q6. Are we testing correctly and in the strongest defensible way?

PASS within the stated reconstruction: source hashes/joins, actual feature prefixes, training membership, strict floors, count/signed support, retained-model inference, PMF scores, chart scaling, fallback coverage and aggregate math have independent checks. [Reviews](DISTRIBUTION_INDEPENDENT_SCORE_REVIEW.json) are numerical rather than prose approval. The HGB carry failure is explained, not erased; the first missing-board inference failure is retained and repaired under a new version.

UNKNOWN/limited: authentic historical publication vintages, full ex-ante historical eligibility, complete rare-chart credits, many private originals and broad external-source contracts. The seven-day rule omits some already-retained current snapshot data; it is not proof of target leakage or a universal live defect. [Availability audit](SEVEN_DAY_AVAILABILITY_AUDIT.json). Selection/multiplicity exposure and seven current week clusters limit conclusions. Next: qualified availability ablation and older rolling seasons; production parity remains owner review.

## Q7. How fully do we model defensive strength?

None of the new20-feature models adds defensive personnel, pressure, coverage, run-type or opponent-adjusted effects. Their measured gains cannot be credited to defense. Historical legacy defense results remain at their previous evidence levels. No no/current/richer-defense causal or incremental-value claim is established.

Next: register one source-qualified earlier opponent-efficiency group and its coverage, hold learner/population/cutoff fixed, compare against no-defense. Final-season ranks and realized target pressure remain forbidden.

## Q8. How do playbooks and playcalling affect forecasts?

The new models infer tendencies only indirectly through earlier player production and position. No upcoming playbook, formation, personnel, motion, actual clock pace or target-game script is used. A pass/rush production proxy is not a measured playcalling or snap-pace feature.

Next: qualify lagged team opportunity/pace/coaching proxies with event availability and test that information group alone. No access to unreleased playbooks is claimed.

## Q9. What should we improve in the tests?

The completed repair experiment isolates QB/RB-only rushing training while holding common features/absolute-loss HGB parameters fixed. On844 shared primary outcomes, multiseason MAE improves6.569905→3.091618; on disjoint WR/TE outcomes it worsens. The old pooled model's zero intercept/uniform tie subgradient/repeated extreme splits, rather than clipping, cause its failure. [Corrected diagnosis](HGB_RUSH_ATT_COLLAPSE_DIAGNOSIS_V2.md), [paired results](count-ablation-wave-v1/PAIRED_OLD_CONTROL_COMPARISON_V2.csv). Do not apply that specialization universally.

Next priorities: availability/query-freshness ablation from the proven pregame snapshot, isolate the ordered-history block against an unordered strong control, complete earlier seasons for new learned families, qualify remaining chart credits, then distinct learners/information groups. Preserve optimizer warnings and infinite log losses. No completed fit was rerun just to refresh documentation. A final exact-grid audit also fixes chart-median tolerance diagnostics under a [new score version](chart-grid-precision-correction-v1/README.md), preserving originals and all forecast/MAE values.

## Q10. Did the top five methods do better on selected Overs or Unders?

UNKNOWN for the new methods: no authenticated offer/price/settlement packet and frozen pick rule has been admitted. Forecast MAE, CDF calibration, tolerance accuracy and top-player membership do not create a pregame betting selection. Up to four family representatives are shown rather than padding five.

Earlier recorded thresholds retain their original reported evidence; they are not automatically actual bookmaker offers. Next: obtain the owner's approved matched export, freeze selection before labels, and report wins/losses/pushes/voids/unresolved, coverage, scores and supported prices/returns.

## Q11. Is Over or Under more accurate?

No universal side winner is established. New results score point forecasts and proper laws, not a realized-side partition mislabeled pregame selection. We do not infer an Over/Under success rate from a category's MAE or rare-event prevalence.

Next: compare all-Over/all-Under and frozen model selections on the same authenticated book/time/line/price population, retaining integer push mass and abstentions. Missing offers block this analysis, not the completed point comparisons.

## Q12. Which category is truly most accurate or closest?

Native errors and registered tolerances are in the index; yards, counts, chart points and probabilities are different units. [Twelve-category summary](TWELVE_CATEGORY_SUMMARY.md) also declares nonzero baseline-relative skill against fixed empirical H-RECENT means on the same outcomes. It does not divide by zero actual production or turn relative skill into percent accuracy.

Observed examples: leaf attempts MAE8.004132, rushing yards16.750000, carries3.059242, receptions1.253541, receiving yards16.198772. HGB TD-event Brier remains.143144; an interception median MAE.590909 does not alone establish superior probabilistic skill. Chart leaf4.499958 is on a separate2,359-label partial panel. Mean-MSE and proper-law CRPS rankings remain separate. Next: later same-contract evidence and uncertainty, not raw-error cross-category ranking.

## Q13. Which category gives the strongest Over/Under decisions?

UNKNOWN without actual offers, prices and an earlier-frozen category selection rule. New category MAE leaders are exposed research minima and do not establish price-aware expected value, hit rate or profitability.

Next: owner-approved offers/selection export with flat-unit accounting, pushes/voids, drawdown, return per offered opportunity, uncertainty and coverage. No wagers, paid collector or new schedule is authorized or created.

## Q14. Should Over and Under use different methods?

The retained rule begins with one coherent forecast law: `P(Y>L)`, `P(Y<L)` and integer push mass. At a half-integer count line, Over and Under probabilities sum to1; mirroring predictions and outcomes preserves Brier/log loss. These are not independent probability competitions.

The new law implementations pass support, PMF/quantile and numerical-underflow checks. No side specialist, conditional gate or hindsight router was fitted. Any specialist requires an earlier-trained, line-monotone, push-preserving routing rule evaluated later on the full selected pool. [Later grading/selection freeze](LATER_GRADING_SELECTION_AMENDMENT_V1.json). No live policy or production release follows from observed rank.
