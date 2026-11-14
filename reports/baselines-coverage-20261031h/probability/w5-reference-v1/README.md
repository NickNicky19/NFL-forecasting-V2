# Week 5 probability references

This newly supported week changes which categories beat the neutral reference. H-MULTI Leaf and C02 beat neutral Brier 0.25 for **passing attempts and interceptions**, while passing touchdowns loses. In Weeks 6–7, passing touchdowns and interceptions beat neutral while passing attempts loses. On Week 5 each procedure beats the earlier same-position prevalence reference in six of ten categories; both lose passing attempts, completions, interceptions and passing yards. These are descriptive weekly reversals, not an earlier-executable method selector.

| Category | Matched n | Neutral | Earlier prevalence | Leaf | C02 | GLM |
|---|---:|---:|---:|---:|---:|---:|
| pass_att | 28 | 0.250000 | 0.236222 | 0.239436 | 0.247687 | 0.298532 |
| pass_cmp | 28 | 0.250000 | 0.253215 | 0.254828 | 0.257972 | 0.326932 |
| pass_int | 28 | 0.250000 | 0.236110 | 0.243052 | 0.243771 | 0.239640 |
| pass_td | 28 | 0.250000 | 0.285571 | 0.267262 | 0.259834 | 0.277074 |
| pass_yd | 28 | 0.250000 | 0.272469 | 0.276786 | 0.276583 | 0.326127 |
| rec | 155 | 0.250000 | 0.295051 | 0.260106 | 0.260108 | 0.282371 |
| rec_yd | 156 | 0.250000 | 0.277262 | 0.260906 | 0.260129 | 0.269486 |
| rush_att | 38 | 0.250000 | 0.311717 | 0.269509 | 0.268037 | 0.356692 |
| rush_rec_yd | 38 | 0.250000 | 0.280469 | 0.271757 | 0.271681 | 0.286667 |
| rush_yd | 79 | 0.250000 | 0.302428 | 0.259981 | 0.262458 | 0.286419 |

Only Week 5 was newly evaluated here; the completed Weeks 6–7 baseline files were not regenerated. The new source panel covers 14/15 games and 617 original thresholds, with 606 supported qualified outcomes. Exact candidate masks and history/strict arms remain separate. `FULL` means all qualified saved-law/outcome rows, not all offered opportunities; outer coverage and all exclusions are retained in the linked table.

B0 is the threshold-local Over=.5/Under=.5/Push=0 reference, not an authenticated market or global CDF. Its Brier is .25 on decisive outcomes and .75 on pushes, with infinite log loss on a push. B1 uses unsmoothed earlier same-position, same-target official full-game outcomes at the exact offered line; kickoff+7d availability must be strictly before each decision clock. CURRENT uses2026, RECENT2025–26, MULTI2022–26. Existing strict candidates receive a2026-only baseline without older priors/features/calibration. Empty prefixes explicitly use B0. No result-dependent calibration or source-lag repair occurs.

Per-region calibration bins and decisive-event AUC are diagnostic outputs, not fitted calibration or a new selection rule. True-zero probabilities retain infinite log losses. Game-cluster paired intervals are descriptive and unadjusted for selection/multiplicity; one week cannot support the registered whole-week uncertainty method. Conditional modeled appearance is distinct from bookmaker nonvoid settlement. No prices, EV, ROI, CLV or betting profitability are established.

[All methods/history/strict arms](PRIMARY_BASELINE_TABLE.csv) · [Outer coverage](MASK_AND_OUTER_COVERAGE.csv) · [Canonical scores](SCORES.json) · [Paired errors and uncertainty](PAIRED_REFERENCE_COMPARISONS.csv) · [Calibration/discrimination diagnostics](CALIBRATION_AND_DISCRIMINATION.json) · [Frozen protocol](FROZEN_PROTOCOL.json) · [Resource/evidence receipt](RUN_RECEIPT.json).
