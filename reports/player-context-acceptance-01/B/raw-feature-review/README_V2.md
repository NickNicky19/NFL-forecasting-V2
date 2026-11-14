# B independent raw-to-feature acceptance

This review is owner-local Session B evidence for C's independent acceptance of B, not a claim that C has received or accepted it. All comparisons bind B `2fa855fc4dd7e9e495126dea93ba90a33fee4be3`. No new model, NFL fit, source collection, capture, offer, grading version or production change was made.

The source files really exist, and all ten retained raw PBP/FTN files match the original source SHA/byte receipts. An independent streaming CSV implementation rebuilt all 2,901 regular-season QB-game completion/attempt vectors, down/depth counts, field sums/means, team identities and FTN flag denominators. Exact counts match for 633/663/664/664/277 rows in 2022/2023/2024/2025/2026. The 2026 panel is Weeks 1–8 only. That full parity closes raw-to-cache meaning in this source version, not authenticity of historical first publication.

Eight cases were fixed by source metadata before looking at comparative performance: earliest game/QB in each source year; earliest physically supported explicit zero; the distinct unknown-participation case; and the 2025 Week 2 stat-credited no-play. The protected win/loss examples use a declared canonical order and are retained only as hashes and aggregate state evidence. Both earlier quote clocks precede the kickoff-information forecast cutoff: they remain timing-unverified actual-line diagnostics, not earlier-executable original picks.

## Explicit zero and unknown

All needed raw QB ATT/CMP cells are finite numeric values: 124 explicit attempt zeros and 176 explicit completion zeros, and no missing/nonfinite cells. No sparse absence-to-zero assumption was needed. The played-zero sample has literal `0`/`0` plus a separate raw reported carry and a matching PBP credited rush. The unknown-participation sample also has literal `0`/`0`, but no positive physical credit or named passing/rushing/receiving PBP event; it remains UNKNOWN_PARTICIPATION. Presence and participation are separate. Missing-stat behavior was not claimed as an observed NFL case in this source panel.

## Context-specific opponent equation

For context j, B computes a predicted own mix m_j, a historical observed QB-throw defense count A_j/C_j, and expected historical completions E_j using the earlier quarterback's prior context rate. The residual is `r_j = (C_j - E_j)/(A_j + 100)` and the E3 feature is `m_j*r_j` separately for every one of 25 contexts. The historical offense-quality reference is recomputed at each past game's own eligible origin. Backup QB rows are summed within one team/game before choosing the last 16 observed games, so a backup does not create another defense-game observation. Counts deliberately weight throws rather than averaging player percentages.

The fixed 2025 Week 1 example has 17 distinct residual values. In first-down 0–9 air yards, `m=0.217461864`, `A=95`, `C=68`, `E=68.427411606`; therefore `r=-0.002191854391` and the interaction is `-0.000476644742`. The sum of actual context products is `-0.006159344743`, different from the overall scalar residual `-0.017123124721`. Repeating that one scalar across exhaustive shares would indeed collapse to the scalar, but this implementation does not do that. The direct learner receives separate context products; no claim that it must use them or estimate causal defensive talent follows.

This is QB official-throw context, not all designed dropbacks, a QB-stint opportunity model or an iterative opponent-adjusted talent model. Lagged mean distance/field/clock/score values are not a predicted full future game-script distribution. Pass destination is not receiver alignment. Completion and provider catchability/drop/contested annotations remain separate; all eight FTN TRUE/FALSE dictionaries were checked, known FALSE is counted as known but not positive, and unmatched chart data stays missing.

## Population and chronology

The current numerical panel has 277 QB-player-games; each actual-line panel has 112 of those and 165 nonoffered numerical queries, 56 games and four weeks. All 224 category-offer labels match the raw-verified source, with no unknown participation or new-method inference failure. The four preserved boards still miss Weeks 1–4 and one Week 5 game; historical offers were not added. Original saved selections and retrospective rules remain separate.

Seven-day availability is a reconstruction policy consistently used in historical training/query features, not an authenticated source clock. The complete earlier E3 feature vector stayed identical after changing target/future outcomes and realized attempt/context exposures. A future query containing only game/player/team/opponent/kickoff/season also produces identical history features and attempt law without any known final outcome. A historical grading runner's label fields are not therefore live-input requirements.

## Scoped metadata finding

The original inventory field `rows_excluded_no_play` counts all marked no-play source rows, not actual mask exclusions. All 81 source-week counters reproduce exactly: 20,239 marked rows, including one admitted stat-credited QB attempt in 2025 Week 2 (288 marked, 287 not admitted, one retained). The minimum correction is a source-bound label interpretation such as `marked_no_play_rows`; changing the credited-attempt mask would be wrong. No saved forecast or grade was affected.

The new optional named adapter enforces declared feature order/model/schema hashes and rejects non-finite inputs. Its prior is externally supplied: complete inference also needs the registered origin-prior binding. This is a boundary qualification, not demonstrated wrong prior use in saved NFL forecasts. The parent fit/inference reviewer covers fresh fitting and round-trip behavior.

A checker initially attempted to parse an unrelated 1999 schedule row lacking time; the failed helper/receipt were retained and the checker was restricted to the declared source years. It was not a producer or forecasting defect.

## Limits and evidence

[Exact A–F scope verdicts](RAW_REVIEW_ACCEPTANCE_VERDICTS_V1.json), [raw reconstruction](RAW_TO_FEATURE_ACCEPTANCE_RECEIPT_V1.json), [zero/unknown semantics](EXPLICIT_ZERO_AND_UNKNOWN_SEMANTICS_V1.json), [277/112 crosswalk](RAW_VERIFIED_POPULATION_CROSSWALK_V1.json), [counter qualification](SOURCE_NO_PLAY_COUNTER_QUALIFICATION_V1.json), [outcome-free query](QUERY_WITHOUT_OUTCOMES_REVIEW_V1.json), and the two portable independent helpers provide the bindings. Code accepts explicit source/owner-local paths; no protected lines or private locators are published. Another reviewer needs source-owner permission to reproduce the protected win/loss examples. Public raw/derived source checks are reproducible under the original licenses.

Raw PBP/stat-only derivatives are CC BY 4.0, attributed to nflverse/nflfastR. FTN-dependent fields and this combined derivative review are CC BY-SA 4.0, attributed to FTN Data via nflverse. No visibility or source permissions changed.


## Version 2 population/time closure

The earlier literal `165 nonoffered` shorthand is qualified by [the exact partition](POPULATION_TIME_PARTITION_QUALIFICATION_V2.json): 277 W1–8 numerical queries consist of 146 in W1–4 and 131 in W5–8. The latter have 129 queries within the board's 56 games and two in the missing Week 5 game. Within those same 56 games, 112 are offered and 17 are other QB-game queries. The 165 outside the inspected offer panel therefore are not 165 intentional abstentions, and a 277-versus-112 comparison alone cannot isolate offer population from time/game coverage.

Eight new numerical views in `SCORES.json` project frozen mean/median outputs onto the covered 129-query/56-game mask for E0, E3, F2 completions and the shared attempt-exposure law. No new fit, inference, prop grade, offer or NFL outcome was created. The 277, 131 and 112 views are reused from their original canonical source rows. The source-projection helper calls the existing native point-metric implementation, not a second grader.

| Frozen mean | W1–8 all277 bias | W5–8 all131 bias | Same56games129 bias | Offered112 bias |
|---|---:|---:|---:|---:|
| Common attempt exposure | -0.8375 | -0.7593 | -0.6618 | -3.1658 |
| E0 completions | -1.2233 | -0.4625 | -0.3796 | -1.7291 |
| E3 completions | -0.9234 | -0.2728 | -0.1722 | -1.4779 |
| F2 completions | -1.0700 | -0.2974 | -0.2074 | -1.4781 |

The corresponding covered-129 mean MAEs are 8.804579 attempts, 5.998932 E0 completions, 5.878341 E3, and 5.854435 F2. [The full projection](TIME_GAME_OFFERED_NUMERICAL_PROJECTION_V2.json) retains both mean and median metrics with canonical source IDs. These are population/time diagnostics, not a causal role explanation or a replacement of the full-system panel. Model-versus-model comparisons on the same 112 offers remain unchanged.
