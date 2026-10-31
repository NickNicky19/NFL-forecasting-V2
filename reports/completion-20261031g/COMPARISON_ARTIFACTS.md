# Comparison artifacts and reading order

The new rolling evidence covers all fourteen games in each of 2026 Weeks 6 and 7. Original recorded selections won **445/801 decided cases (55.56%)**: Over **236/446 (52.91%)**, Under **209/355 (58.87%)**. The earlier fixed-Friday Week 7 panel remains separate. Complete base Leaf-CDF/C02 laws now support actual-line probability comparisons; prices and sportsbook settlement remain unestablished. No new forecast capture occurred in this checkpoint.

Start with the [full category report](FULL_CATEGORY_CHAMPIONSHIP_REPORT.md), [executive decisions](EXECUTIVE_CATEGORY_DECISIONS.json) and [category release packages](CATEGORY_RELEASE_PACKAGES.md). Numerical error, actual-line probability scores, selected-side hit rates and operational readiness have different winners and requirements.

## Source panels and exact timing

| Panel | Actual scope | Sources, freeze and original/control results |
|---|---|---|
| Rolling Week 6 | 670 provider-labelled thresholds; 14 games; seven source-clock batches | [Source assignments](source-expansion/FROZEN_ROLLING_SOURCE_ASSIGNMENTS.json), [source qualification](source-expansion/METADATA_QUALIFICATION_RECEIPT.json), [original and saved-point scores](source-expansion/SCORES.json), [readable side tables](source-expansion/README.md) |
| Rolling Week 7 | 649 thresholds; 14 games including Thursday; four source-clock batches | [Assignments](source-expansion/w7-rolling-v1/FROZEN_ROLLING_SOURCE_ASSIGNMENTS.json), [qualification](source-expansion/w7-rolling-v1/METADATA_QUALIFICATION_RECEIPT.json), [scores](source-expansion/w7-rolling-v1/SCORES.json), [readable tables](source-expansion/w7-rolling-v1/README.md) |
| Preserved fixed-Friday Week 7 | 462 thresholds; 13 later games; common server retention bound October 23 at 17:49:53 UTC | [F source protocol](../championship-20261030f/offer-expansion/full-pool-v1/FROZEN_PROTOCOL.json), [unchanged scores](../championship-20261030f/offer-expansion/full-pool-v1/SCORES.json), [original/full-pool comparison](../championship-20261030f/offer-expansion/full-pool-v1/README.md) |
| Missing earlier periods | W1–3 canonical original archive paths absent in inspected history; W4–5 commit-timed archives lack qualifying independently verified pregame server clocks in the inspected scopes | [Week-by-week source pins, clocks and reasons](source-expansion/WEEK_SOURCE_COVERAGE.csv), [JSON](source-expansion/WEEK_SOURCE_COVERAGE.json), [upstream refresh](source-expansion/UPSTREAM_REFRESH.json) |

The rolling rule selects the latest independently server-retained archive head before each game's T-minus-90 deadline. The actual decision time is that server clock; it is not silently relabelled an exact T-minus-90 forecast. Source membership was frozen before new grading. Saved original no-selection states remain abstentions; subsequent point/probability rules are retrospective decisions.

A Git blob and server clock establish retained snapshot bytes. They do **not** authenticate every provider input vintage, quote age, executable cash price or bookmaker rule. Football training/features/outcomes remain qualified current/revised-source reconstructions under the registered availability assumptions. The [temporal admission contracts](roster/finite-v2/README.md#saved-row-admission-at-actual-thresholds) distinguish these claims. Raw player-game records and model payloads remain private; public receipts carry safe IDs and hashes.

## Every actual method, week, side and product

The [current reading contract](roster/actual-method-period-summary-v2/FINAL_REPORT_READING_CONTRACT_V2.json) and [current actual-method projection](roster/actual-method-period-summary-v2/CURRENT_ACTUAL_METHOD_SCORE_PROJECTION.json) define valid default views and complete-law replacements. Superseded, partial and losing versions remain in the audit.

| Readable or machine view | What it contains |
|---|---|
| [Actual-method comparison guide](roster/actual-method-period-summary-v2/README.md) | Scope, an actual gain, adverse week reversals, timing, coverage and interpretation |
| [Compact primary side table, V3](roster/actual-method-period-summary-v2/ALL_METHOD_PRIMARY_SIDE_TABLES_V3.csv) | One row per procedure/history/output/decision rule and panel; Over, Under and Combined counts/rates with current denominator annotations |
| [Every weekly side/cohort/K view](roster/actual-method-period-summary-v2/ALL_WEEKLY_METHOD_SIDE_TABLES.csv.gz) | Exact source score IDs, wins/losses/pushes/unknowns, coverage, abstentions, fallback and uncertainty; [JSON](roster/actual-method-period-summary-v2/ALL_WEEKLY_METHOD_SIDE_TABLES.json.gz) |
| [Every cumulative W6–7 side/cohort/K view](roster/actual-method-period-summary-v2/CUMULATIVE_W6_W7_METHOD_SIDE_TABLES.csv.gz) | Weighted counts across only the two nonoverlapping rolling panels; weekly K rules reset as registered; [JSON](roster/actual-method-period-summary-v2/CUMULATIVE_W6_W7_METHOD_SIDE_TABLES.json.gz) |
| [Weekly native and proper products](roster/actual-method-period-summary-v2/ALL_NATIVE_AND_PROPER_PRODUCTS.csv) | Point MAE and separate legitimate actual-line Brier/log-loss products; [JSON](roster/actual-method-period-summary-v2/ALL_NATIVE_AND_PROPER_PRODUCTS.json) |
| [Cumulative native/proper products](roster/actual-method-period-summary-v2/CUMULATIVE_W6_W7_NATIVE_AND_PROPER.csv) | Explicit sum(n × loss)/sum(n), with missing periods retained; [JSON](roster/actual-method-period-summary-v2/CUMULATIVE_W6_W7_NATIVE_AND_PROPER.json) |
| [All raw observed side maxima](roster/actual-method-period-summary-v2/OBSERVED_RAW_SIDE_MAXIMA.csv) | Ties, losses and sample sizes, including tiny perfect selected subsets |
| [Cumulative completeness annotations](roster/actual-method-period-summary-v2/CUMULATIVE_COMPLETENESS_ANNOTATIONS_V2.json) | Intended opportunities, genuine missing weeks, cohort membership and outside-cohort rows |
| [Field semantics](roster/actual-method-period-summary-v2/FIELD_SEMANTICS.json) | Distinct eligible/admitted/unavailable, selected/abstained, statistical unresolved and unverified book settlement fields |

Top-6/10/20 policies have separate combined-side, Over-only and Under-only pools, per category. Rolling rules consume remaining slots at increasing source-clock batches. The fixed-Friday panel is a separately declared fixed partial-week reconstruction. Neither is an originally issued weekly top-K list. Top-ranked picks are separate from top-ranked players. Empty decided sides have N/A hit rates.

## Canonical score arrays behind those views

| Product/panel | Exact canonical source and supplemental arrays |
|---|---|
| Fixed-Friday actual-method P1 and initially complete parametric/fallback P2 | [Main scores](roster/w7-method-comparison-v2/SCORES.json), [supplemental category arrays](roster/w7-method-comparison-v2/SUPPLEMENTAL_SCORE_ARTIFACTS.json), [matched-control K/metadata projection](roster/w7-method-comparison-v2/metadata-and-control-k-v1/RUN_RECEIPT.json) |
| Rolling W6 actual methods | [Main scores](roster/w6-rolling-method-comparison-v1/SCORES.json), [category arrays](roster/w6-rolling-method-comparison-v1/SUPPLEMENTAL_SCORE_ARTIFACTS.json), [matched-control K/metadata](roster/w6-rolling-method-comparison-v1/metadata-and-control-k-v1/RUN_RECEIPT.json) |
| Rolling W7 actual methods | [Main scores](roster/w7-rolling-method-comparison-v1/SCORES.json), [category arrays](roster/w7-rolling-method-comparison-v1/SUPPLEMENTAL_SCORE_ARTIFACTS.json), [matched-control K/metadata](roster/w7-rolling-method-comparison-v1/metadata-and-control-k-v1/RUN_RECEIPT.json) |
| Complete learned base Leaf/C02 P2, fixed-Friday | [Main scores](roster/fixed-w7-complete-leaf-law-v1/SCORES.json), [category arrays](roster/fixed-w7-complete-leaf-law-v1/SUPPLEMENTAL_SCORE_ARTIFACTS.json) |
| Complete learned base Leaf/C02 P2, rolling W6 | [Main scores](roster/w6-complete-leaf-law-v1/SCORES.json), [category arrays](roster/w6-complete-leaf-law-v1/SUPPLEMENTAL_SCORE_ARTIFACTS.json) |
| Complete learned base Leaf/C02 P2, rolling W7 | [Main scores](roster/w7-complete-leaf-law-v1/SCORES.json), [category arrays](roster/w7-complete-leaf-law-v1/SUPPLEMENTAL_SCORE_ARTIFACTS.json) |
| Corrected shared player/workload cohorts for original/saved controls | [W6 scores](source-expansion/cohort-projection-v3/SCORES.json), [W6 readable groups](source-expansion/cohort-projection-v3/README.md), [W7 scores](source-expansion/w7-rolling-v1/cohort-projection-v3/SCORES.json), [W7 groups](source-expansion/w7-rolling-v1/cohort-projection-v3/README.md) |
| Common-row probability comparisons | [All 480 contrasts](roster/paired-probability-v1/PAIRED_PROBABILITY_COMPARISONS.csv), [source-score annotations](roster/paired-probability-v1/PROPER_SCORE_COMPARISON_ANNOTATIONS.json), [readable comparison](roster/paired-probability-v1/README.md) |
| Complete-law learned/prior decomposition | [Canonical origin diagnostics](roster/actual-method-period-summary-v2/fallback-diagnostic-v1/SCORES.json), [full decomposition](roster/actual-method-period-summary-v2/COMPLETE_LEAF_FALLBACK_DECOMPOSITION.csv), [origin annotations](roster/actual-method-period-summary-v2/COMPLETE_LEAF_LAW_ORIGIN_ANNOTATIONS_V2.json) |

The [histogram recovery proof](law-recovery/v1/README.md) restores full support/weights/prior from original saved leaf IDs and 160 restored models, without predict/apply/refitting. Its [parity proof](law-recovery/v1/MODEL_AND_LAW_PARITY_PROOF.json) reproduces 24,588 retained mean/median witnesses with maximum summary difference 0.0. These witnesses and output views are not independent NFL observations. [Actual thread-control finding](law-recovery/v1/ENVIRONMENT_AND_THREAD_LIMIT_FINDING.json) preserves the runtime limitation and future fix.

## Numerical seasons, histories and chronological policies

- [Finite implemented roster](roster/finite-v2/FINITE_IMPLEMENTED_PROCEDURE_ROSTER.csv) and [roster explanation](roster/finite-v2/README.md): 11 fixed mechanisms; 641 target/history/output recipes, with 620 complete current scores and 21 original strict-HGB recipes still unrun. Aliases, output views, fits and methods remain different units.
- [Every exact current numerical recipe](roster/finite-v2/CURRENT_METHOD_COMPARISONS.csv) and [JSON](roster/finite-v2/CURRENT_METHOD_COMPARISONS.json): native MAE/MSE/RMSE, bias/tails, precision numerators/denominators, fallback, source IDs and explicit nulls.
- [Finite recipe/season coverage grid](roster/finite-v2/FINITE_RECIPE_CATEGORY_PERIOD_PRODUCT_GRID.csv): supported full 2022–2025 seasons and fixed 2026 W1–7; exact D1/D2/strict/source gaps remain visible.
- [Five-season numerical comparison](../championship-20261030f/CATEGORY_CHAMPIONS.md) and [all representatives](../championship-20261030f/numerical-v2/ALL_VALID_REPRESENTATIVES.csv): observed leaders, distinct runners-up, adverse seasons and paired same-row results.
- [Season-relative selectors](season-selector/README.md), [all season policy scores](season-selector/ALL_SEASON_POLICY_RESULTS.csv), [policy comparisons](season-selector/POLICY_SEASON_COMPARISON.csv) and [micro/season-balanced aggregates](season-selector/COMPLETE_SEASON_AGGREGATES.csv): full 2023–2025 and preserved 2026 W1–7 policies that choose using only earlier available scores. Hindsight weekly winners receive no live-policy credit.
- [Adjacent-history comparisons](../continuation-20261030d/README.md): CURRENT versus RECENT and RECENT versus MULTI, full-system and common-learned masks. Current-season fitting remains separate from strict-current information; the 2022 RECENT proxy is not an exact 2021-trained arm.

## Audit, recovery and upcoming operation

[Report bindings](REPORT_BINDINGS.json), [current prop projection](CURRENT_PROP_SCOREBOARD_VIEW.json), [canonical score manifest](NEW_CANONICAL_SCORE_MANIFEST.json), [annotation manifest](REPORTING_ANNOTATION_MANIFEST_V2.json) and [permanent index](results-index-v1/INDEX_MANIFEST.json) link rows back to exact versions. Public gzip files are lossless delivery encodings. Older source score bytes, corrected versions, failures and losses remain preserved.

[Independent executable reviews](independent/) check actual source/timing joins, wins/losses, boundaries, side partitions, rolling K, retained-law lookup and probability calculations. [Software verification manifest](SOFTWARE_VERIFICATION_MANIFEST.json) keeps fixtures separate from NFL samples.

[Recovery status](ARTIFACT_RECOVERY_STATUS.md) identifies the exact missing parts, while [upcoming category capture status](UPCOMING_CATEGORY_CAPTURE_STATUS.md) distinguishes existing immutable shadows, restored own models, scheduler configuration, actual new inference/persistence, owner admission, publication and served verification. Unrelated recovery gaps do not stop independently ready owner captures. No new universal waiting period or same-cutoff website-win gate is introduced; each procedure still needs its own source/model/runtime/consumer/fallback/rollback checks and retained-owner admission.
