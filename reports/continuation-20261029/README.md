# October 29 continuation: executed tests and Week 8 forecasts

The identity problem is diagnosed, a new same-game history comparison is executed, and new Week 8 research shadows are privately retained. The full legacy-method tournament remains incomplete. The [observed twelve-target comparison](TWO_FAMILY_PRIMARY_COMPARISON_2026_W1_W7.md) and [current inventory boundary](INVENTORY_COMPLETENESS.md) state the supported scope.

- [Every scored test: accuracy, errors, evidence and source links](TEST_RESULTS_INDEX.md)
- [Browse twelve category result tables](categories/README.md)
- [History comparison, including losses and startup effects](history-diagnostic-v1/HISTORY_COMPARISON_REPORT.md)
- [Independent history verification](../verification/EMPIRICAL_HISTORY_DIAGNOSTIC_REVIEW.md)
- [Week 8 captured/blocked status for all located references](WEEK8_ALL_METHOD_STATUS.md)
- [New Week 8 shadow receipt](week8-shadow-v2/CAPTURE_RECEIPT.json)
- [Independent Week 8 checks](../verification/WEEK8_SHADOW_INDEPENDENT_QA.md)
- [Exact fallback diagnosis](FALLBACK_DIAGNOSIS.md)
- [Future reporting contract](../../docs/RESULT_REPORTING_CONTRACT.md)

[Twelve-target observed comparison of the two families](TWO_FAMILY_PRIMARY_COMPARISON_2026_W1_W7.md)

## Completed HGB wave and two-family Week 8 amendment

A new fixed HGB control wave completed **452 actual NFL fits**, retained all 452 models, and produced **930 aggregate score views**. All 504 registered fit opportunities are accounted for: 52 used the predeclared insufficient-training fallback, with zero failed fits. It compares the same 15,574 historical query cells across all 107 games in 2026 Weeks 1–7. The three fit-history arms share earlier 2022+ feature memory, so H-CURRENT means current-season fitting. It is a new source-matched version of an existing HGB mechanism, with exposed retrospective participant cohorts; it does not reproduce old HGB issuance.

On the primary passing-yard absolute-loss view, H-CURRENT / H-RECENT / H-MULTI MAE is **95.487849 / 70.068471 / 66.117313 yards** (242 supported rows). The multiseason advantage over current-season fitting is 29.370536 yards overall and 5.231099 on the 130-row learned-only overlap. The current-season interception absolute-loss view wins its history comparison; some HGB views lose to empirical controls. In particular, the multiseason carry absolute-loss output is zero throughout its primary cohort and has MAE 6.569905 versus empirical-median 3.283175. Mean-objective MSE and anytime-TD Brier are separate products. Seven-week uncertainty and startup effects prevent a universal history-winner claim. [Full HGB evidence and losses](hgb-history-v1/README.md) · [Independent numerical review](../verification/HGB_HISTORY_INDEPENDENT_QA.json).

Two new research families now retain **20,772 issued Week 8 views plus 60 abstentions** (20,832 total) on the same 1,951 frozen query cells and fourteen games. Empirical capture was 22:51:33 UTC; HGB capture was 23:16:53 UTC. Both precede every kickoff and both miss the first game's 22:45 owner input cutoff: 837 views per family, 1,674 combined, retain the later-horizon flag. No Week 8 outcomes were read or scored. The combined private review bundle was uploaded owner-only and freshly downloaded with an exact hash check; [restoration receipt](PRIVATE_WEEK8_ALL_REVIEW_RESTORATION.json). Original owner forecasts remain preserved. The [1,808-row status matrix](WEEK8_ALL_METHOD_STATUS.md) includes 1,669 blocked legacy source/product references and 126 new family/history/product cells; those references are not 1,669 fitted models.

The frozen HGB v1 code and receipts remain unchanged. Its declared output-row cap was not enforced in code; the actual 96,678 views were below the 2,000,000 cap. A [separate tested future guard patch](hgb-history-v1/RESOURCE_GUARD_FOLLOWUP.json) is prepared with no NFL rerun. No official capture, website publication, scheduler, paid call or production change occurred.

## Earlier empirical checkpoint, preserved

The new empirical-control comparison holds 2026 Weeks 1–7 player-games fixed and uses all 107 games, explicit source zeros and exact GSIS identities. On the primary passing-yard mean view, current-season MAE is 97.9690 yards, prior-plus-current 69.1853, and multiseason 69.5127. The prior-plus-current improvement is 28.7837 yards overall but 9.0874 on the learned-only overlap: startup fallback explains part of the difference. The seven-week interval crosses zero. These are exposed, current-vintage retrospective participant-cohort results for simple empirical controls, not a universal history winner.

Older history improves mean MAE on all ten numeric targets in this diagnostic. It does not win every displayed-point comparison: the current-season interception median has MAE .590909 versus multiseason .628099. Best observed point view/history is prior-plus-current for eight categories, multiseason for passing TDs, and current-season for interceptions. Anytime-TD Brier favors multiseason; unsmoothed zero/one probabilities retain infinite log losses. See the full report for exact products, samples, reversals and coverage.

The rolling diagnostic produced 940,812 retrospective forecast views, of which 928,404 were scored, across 25,904 player-games and 1,194 supplied scheduled games in 2022–2026. It is one empirical family with different products and history regimes. There were zero optimization fits; 71,414 arithmetic series are not separate learners or experiments. The 2022 schedule has 271 eligible games, with no missing 2026 Week 7 game.

Week 8 contains 10,386 newly issued views and 30 abstentions across fourteen games, one empirical family and three histories. Actual capture was October 29 at 5:51:33 p.m. Chicago. All precede kickoff; 837 CAR–GB views are after that game's 5:45 input cutoff and remain labeled at the later horizon. No Week 8 result has been scored. The original owner-selected stream is preserved; missing original complex-model artifacts still block their named forecast cells.

Source inputs, private diagnostic predictions and new Week 8 prediction bytes were uploaded to the existing owner-only, unshared NFL evidence store and downloaded again for exact hash checks. Public GitHub contains safe IDs, aggregate results and code. Private storage locators remain in the private companion index. No paid calls, new collector, recurring capture job, production workflow dispatch or website change occurred. The V2 CI workflow performs code/artifact checks only.

## Final verification and later Week 8 scoring

All 71 unit tests pass. Both automatic GitHub CI checks passed on the core publication. The [empirical grading contract](../../docs/WEEK8_SHADOW_GRADING.md) and [HGB grading contract](../../docs/HGB_WEEK8_SHADOW_GRADING.md) require trusted original capture hashes and qualified final labels; independent invented-label and empty-capture checks pass without reading actual Week 8 outcomes. The current index retains 16,048 evaluation views and twelve separate software receipts. [Retained-owner release handoff](FUTURE_CAPTURE_AND_RELEASE_HANDOFF.md).
