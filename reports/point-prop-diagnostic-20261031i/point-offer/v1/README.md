# Why the numerical leaders struggled at the offered lines

Both focal procedures lose to the retained saved-point controls on identical eligible offers in numerical error as well as selected-side accuracy. This is observed adverse evidence; it is not explained away as an acceptable tradeoff. Neither inverted picks nor a new model was tested. The comparison is to retained raw/adjusted fields, not an authenticated complete current-served overlay track record.

| Focal procedure | Same-offer n | MAE | Bias(prediction−actual) | Saved raw MAE | Saved adjusted MAE |
|---|---:|---:|---:|---:|---:|
| HGB direct L1 v1 / pass_yd / H-MULTI / absolute_error_point | 80 | 60.082677 | -17.851730 | 51.504625 | 53.762250 |
| D1 Leaf-CDF v1 / pass_cmp / H-MULTI / lower_median | 76 | 5.052632 | -1.605263 | 4.770526 | 4.465132 |

HGB passing yards has28/80correct directions: Over14/32andUnder14/48. D1 completions has33/76. The shared full source universe contains 84offers per target; HGB has 80eligible saved points and D1 has 76. Missing/unqualified points remain unavailable, not zero predictions or hidden abstentions.

The primary numerical benchmark covered 2026 W1–7and a broad retrospective QBparticipant population. The offered panel is the qualified W5–7 subset. Within the same 42covered games, the original unchanged focal forecasts show:

| Target | Population diagnostic | Supported n | MAE | Bias |
|---|---|---:|---:|---:|
| pass_yd | BROAD_SAME_42_GAME_QB_PARTICIPANTS | 94 | 65.141912 | -5.004075 |
| pass_yd | SAME_KICKOFF_FORECASTS_OFFERED_PLAYER_SUBSET | 84 | 59.923517 | -14.299728 |
| pass_yd | SAME_KICKOFF_FORECASTS_DECISION_ELIGIBLE_SUBSET | 80 | 60.082677 | -17.851730 |
| pass_cmp | BROAD_SAME_42_GAME_QB_PARTICIPANTS | 94 | 5.393617 | -0.585106 |
| pass_cmp | SAME_KICKOFF_FORECASTS_OFFERED_PLAYER_SUBSET | 84 | 4.952381 | -1.690476 |
| pass_cmp | SAME_KICKOFF_FORECASTS_DECISION_ELIGIBLE_SUBSET | 76 | 5.052632 | -1.605263 |

Offered-player selection **improves MAE in this same-game diagnostic**, while negative bias increases. Therefore these results do not show that selected players were simply harder to predict. They also do not prove that backups, an L1 objective, a role change or a coding defect caused the residual bias. The kickoff population views are separate from the actual earlier-decision reconstruction. On each admitted focal row, the original kickoff saved point and label equal the point and label in the qualified earlier-decision row; no new vector or prediction was computed.

For HGB passing yards, mean forecast−line is−11.089230yards while mean actual−line is+6.762500, giving bias−17.851730. Median forecast−line is−5.247851and median actual−line+13.000000. For D1 completions, corresponding means are−0.973684and+0.631579, giving bias−1.605263; medians are−0.5and+1.0. This is a measured directional mismatch on the retained panel. It does not identify a remedy or establish profitable opposite picks.

## Every registered comparator on the focal common rows

The finite roster includes directL1/L2, empirical mean/median, Leaf/C02/D1/D2, GLM, strict-current alternatives, the existing earlier-score selector and saved raw/adjusted fields. Mean/median views share models where appropriate and are not new learners. Different input groups, strict-information policies and point functionals remain named; these are procedure comparisons, not a clean learner-only causal ablation.

| Target | Exact procedure/history/output | Paired n / own n / outer | MAE | Bias | Median forecast−line | Predicted Over W/L/decided; hit rate | Predicted Under W/L/decided; hit rate | Combined W/L/decided; hit rate |
|---|---|---:|---:|---:|---:|---:|---:|
| pass_cmp | Saved adjusted point (retained precision) / ARCHIVED / saved_precision_point | 76/76/84 | 4.465132 | -1.388553 | -0.675000 | 17/8/25; 68.00% | 26/25/51; 50.98% | 43/33/76; 56.58% |
| pass_cmp | Saved raw point (retained precision) / ARCHIVED / saved_precision_point | 76/76/84 | 4.770526 | -1.115263 | -0.490000 | 14/13/27; 51.85% | 21/28/49; 42.86% | 35/41/76; 46.05% |
| pass_cmp | Empirical v1 / H-MULTI / lower_median | 76/80/84 | 5.960526 | -2.328947 | -0.500000 | 15/18/33; 45.45% | 16/27/43; 37.21% | 31/45/76; 40.79% |
| pass_cmp | Empirical v1 / H-MULTI / mean | 76/80/84 | 5.870399 | -2.395698 | -0.591667 | 11/14/25; 44.00% | 20/31/51; 39.22% | 31/45/76; 40.79% |
| pass_cmp | HGB direct L1 v1 / H-MULTI / absolute_error_point | 76/80/84 | 5.092798 | -1.696465 | -0.690211 | 12/12/24; 50.00% | 22/30/52; 42.31% | 34/42/76; 44.74% |
| pass_cmp | HGB direct L2 v1 / H-MULTI / squared_error_mean | 76/80/84 | 5.202710 | -1.999354 | -0.924790 | 9/10/19; 47.37% | 24/33/57; 42.11% | 33/43/76; 43.42% |
| pass_cmp | C02 Leaf-CDF v1 / H-MULTI / lower_median | 76/80/84 | 5.144737 | -1.934211 | -0.500000 | 10/9/19; 52.63% | 25/32/57; 43.86% | 35/41/76; 46.05% |
| pass_cmp | C02 Leaf-CDF v1 / H-MULTI / mean | 76/80/84 | 5.262902 | -2.363201 | -1.324511 | 6/6/12; 50.00% | 28/36/64; 43.75% | 34/42/76; 44.74% |
| pass_cmp | C02 Leaf-CDF v1 [strict-current] / H-CURRENT / lower_median | 76/80/84 | 4.802632 | -0.855263 | -0.500000 | 21/16/37; 56.76% | 18/21/39; 46.15% | 39/37/76; 51.32% |
| pass_cmp | C02 Leaf-CDF v1 [strict-current] / H-CURRENT / mean | 76/80/84 | 4.697893 | -0.361957 | +0.327957 | 27/19/46; 58.70% | 15/15/30; 50.00% | 42/34/76; 55.26% |
| pass_cmp | v2-chronological-category-selector:EARLIER_AVAILABLE_2026_SCORE_MEMORY / H-MULTI / selected_point | 76/80/84 | 5.059654 | -1.802005 | -0.500000 | 8/10/18; 44.44% | 24/34/58; 41.38% | 32/44/76; 42.11% |
| pass_cmp | Leaf-CDF v2 / H-MULTI / lower_median | 76/80/84 | 5.105263 | -1.815789 | -0.500000 | 8/10/18; 44.44% | 24/34/58; 41.38% | 32/44/76; 42.11% |
| pass_cmp | Leaf-CDF v2 [strict-current] / H-CURRENT / lower_median | 76/80/84 | 4.802632 | -0.907895 | -0.500000 | 20/17/37; 54.05% | 17/22/39; 43.59% | 37/39/76; 48.68% |
| pass_cmp | GLM law v2 / H-MULTI / lower_median | 76/80/84 | 5.447368 | -2.263158 | -1.500000 | 6/9/15; 40.00% | 25/36/61; 40.98% | 31/45/76; 40.79% |
| pass_cmp | D1 Leaf-CDF v1 / H-MULTI / lower_median | 76/76/84 | 5.052632 | -1.605263 | -0.500000 | 11/12/23; 47.83% | 22/31/53; 41.51% | 33/43/76; 43.42% |
| pass_cmp | D1 Leaf-CDF v1 / H-MULTI / mean | 76/76/84 | 5.149491 | -1.962766 | -1.008894 | 7/8/15; 46.67% | 26/35/61; 42.62% | 33/43/76; 43.42% |
| pass_cmp | D2 Leaf-CDF v1 / H-MULTI / lower_median | 56/56/84 | 5.285714 | -2.357143 | -0.500000 | 9/9/18; 50.00% | 15/23/38; 39.47% | 24/32/56; 42.86% |
| pass_cmp | D2 Leaf-CDF v1 [strict-current] / H-CURRENT / mean | 56/56/84 | 4.788713 | -0.752261 | +0.485275 | 21/13/34; 61.76% | 11/11/22; 50.00% | 32/24/56; 57.14% |
| pass_yd | Saved adjusted point (retained precision) / ARCHIVED / saved_precision_point | 80/80/84 | 53.762250 | -11.383250 | -5.645000 | 22/13/35; 62.86% | 19/26/45; 42.22% | 41/39/80; 51.25% |
| pass_yd | Saved raw point (retained precision) / ARCHIVED / saved_precision_point | 80/80/84 | 51.504625 | -9.661625 | -0.865000 | 24/13/37; 64.86% | 19/24/43; 44.19% | 43/37/80; 53.75% |
| pass_yd | Empirical v1 / H-MULTI / lower_median | 80/80/84 | 62.237500 | -26.812500 | -6.500000 | 20/11/31; 64.52% | 21/28/49; 42.86% | 41/39/80; 51.25% |
| pass_yd | Empirical v1 / H-MULTI / mean | 80/80/84 | 60.586739 | -25.488811 | -11.682941 | 16/11/27; 59.26% | 21/32/53; 39.62% | 37/43/80; 46.25% |
| pass_yd | HGB direct L1 v1 / H-MULTI / absolute_error_point | 80/80/84 | 60.082677 | -17.851730 | -5.247851 | 14/18/32; 43.75% | 14/34/48; 29.17% | 28/52/80; 35.00% |
| pass_yd | HGB direct L2 v1 / H-MULTI / squared_error_mean | 80/80/84 | 60.231811 | -19.686177 | -8.072196 | 14/15/29; 48.28% | 17/34/51; 33.33% | 31/49/80; 38.75% |
| pass_yd | C02 Leaf-CDF v1 / H-MULTI / lower_median | 80/80/84 | 59.875000 | -21.625000 | -10.500000 | 13/16/29; 44.83% | 16/35/51; 31.37% | 29/51/80; 36.25% |
| pass_yd | C02 Leaf-CDF v1 / H-MULTI / mean | 80/80/84 | 60.607659 | -24.799933 | -14.473606 | 10/11/21; 47.62% | 21/38/59; 35.59% | 31/49/80; 38.75% |
| pass_yd | C02 Leaf-CDF v1 [strict-current] / H-CURRENT / lower_median | 80/80/84 | 58.362500 | -4.437500 | +2.000000 | 26/17/43; 60.47% | 15/22/37; 40.54% | 41/39/80; 51.25% |
| pass_yd | C02 Leaf-CDF v1 [strict-current] / H-CURRENT / mean | 80/80/84 | 56.915138 | +2.432515 | +10.343849 | 33/21/54; 61.11% | 11/15/26; 42.31% | 44/36/80; 55.00% |
| pass_yd | v2-chronological-category-selector:EARLIER_AVAILABLE_2026_SCORE_MEMORY / H-MULTI / selected_point | 80/80/84 | 60.082677 | -17.851730 | -5.247851 | 14/18/32; 43.75% | 14/34/48; 29.17% | 28/52/80; 35.00% |
| pass_yd | Leaf-CDF v2 / H-MULTI / lower_median | 80/80/84 | 59.412500 | -17.412500 | -5.500000 | 14/18/32; 43.75% | 14/34/48; 29.17% | 28/52/80; 35.00% |
| pass_yd | Leaf-CDF v2 [strict-current] / H-CURRENT / lower_median | 80/80/84 | 58.387500 | -4.412500 | +2.000000 | 26/17/43; 60.47% | 15/22/37; 40.54% | 41/39/80; 51.25% |
| pass_yd | GLM law v2 / H-MULTI / lower_median | 80/80/84 | 61.737500 | -17.712500 | -7.500000 | 13/19/32; 40.62% | 13/35/48; 27.08% | 26/54/80; 32.50% |
| pass_yd | D1 Leaf-CDF v1 / H-MULTI / lower_median | 76/76/84 | 57.368421 | -13.894737 | -7.000000 | 11/17/28; 39.29% | 15/33/48; 31.25% | 26/50/76; 34.21% |
| pass_yd | D1 Leaf-CDF v1 / H-MULTI / mean | 76/76/84 | 57.795810 | -16.779239 | -8.980794 | 9/15/24; 37.50% | 17/35/52; 32.69% | 26/50/76; 34.21% |
| pass_yd | D2 Leaf-CDF v1 / H-MULTI / lower_median | 56/56/84 | 57.821429 | -16.321429 | -4.000000 | 11/13/24; 45.83% | 9/23/32; 28.12% | 20/36/56; 35.71% |
| pass_yd | D2 Leaf-CDF v1 [strict-current] / H-CURRENT / mean | 56/56/84 | 56.672532 | +4.744214 | +11.067749 | 26/14/40; 65.00% | 8/8/16; 50.00% | 34/22/56; 60.71% |

W/L means wins/losses, not wins/decided; the machine table publishes selected count, decided denominator, hit rate and every status separately. Combined hit rate uses summed wins/(summed wins+losses). Empty buckets are N/A. Means and medians are not silently substituted. Saved controls preserve their retained precision; unavailable internal digits are not invented.

## Matched uncertainty and fallback scope

| Target | Comparator minus focal MAE | Paired n | Difference | Game-cluster95% sensitivity |
|---|---|---:|---|
| pass_cmp | Saved adjusted point (retained precision) minus focal | 76 | -0.587500 | [-1.0210548197416272, -0.15394518025837284] |
| pass_cmp | Saved raw point (retained precision) minus focal | 76 | -0.282105 | [-0.6292063902900173, 0.06499586397422769] |
| pass_yd | Saved adjusted point (retained precision) minus focal | 80 | -6.320427 | [-14.805083331918327, 2.164229494636958] |
| pass_yd | Saved raw point (retained precision) minus focal | 80 | -8.578052 | [-15.577012912949971, -1.5790909243313926] |

Negative differences favor the saved comparator. These are exposed, selection-unadjusted paired comparisons; three weeks are insufficient for the registered whole-week interval. Full-system and both-known-learned intersections are retained separately in[all paired comparisons](PAIRED_MAE_COMPARISONS.csv). Saved-point model/fallback metadata is unknown, so their learned-only comparison is not applicable. Sparse and fallback cases are retained in each method’s own full-system score and coverage.

Identical recipe/mask scores are deduplicated. A canonical record can retain its first-emitted conditional-view denominator because identical point/loss masks are deduplicated. The[context coverage extensionV2](CONTEXT_COVERAGE_EXTENSION_V2.json) supplies each view’s own denominator, including84for both focal OWNviews. Canonical100%conditional support must not be presented as complete outer-offer coverage. Error and selected-state counts are unchanged.

## Identity, units, chronology and functional audit

The actual method point is `ranking_point` in retained joined grades and frozen plan `point`. The joined `prediction` field is the saved adjusted-site reference; using it as the model point would be an adapter error. Original forecast packets use their own `prediction` as the model point. Exact game/player/category/line/actual/decision-clock equality is asserted for common comparisons, and saved point-versus-line directions are asserted unchanged. Official signed yards and integer completion actuals are preserved; forecasts and lines are not rounded.

HGB is a direct absolute-error point fit. D1 lower median is extracted from squared-error forest response partitions plus the registered5%prior; it is not a direct absolute-loss model. The original feature rules, training eligibility, query cutoffs, fallback and seven-day source assumption remain unchanged. Current-vintage football reconstruction is not authenticated historical source publication; original server-retained thresholds/context do not authenticate original V2issuance.

The shared side aggregator inherited an overly broad original-point source label. The[bound metadata correction](CURRENT_REPORTING_ANNOTATIONS_I_V1.json) corrects189side labels and supplies69missing point labels without changing a canonical score, point, side or outcome. The[default diagnostic view](DEFAULT_DIAGNOSTIC_VIEW.json) requires that correction. Raw/adjusted saved references and reconstructed V2points retain distinct evidence tiers.

Worked win/loss cases for both selected sides are retained privately with original stable identity, point, line, actual, grade and clock/source references. They were chosen by the preregistered first chronological case per bucket for explanation only. No raw player/offer row or private locator is published. The92,891-byte derivative is retained in the isolated private workspace with its hash; no new upload/restoration receipt is claimed. Its pinned parent rows and deterministic source support reconstruction. Any approved companion-store restoration must be recorded separately.

## Next supported action

The evidence supports investigating current role/opportunity information, source freshness and point-functional/population specialization on unchanged comparable rows; it does not establish which mechanism will repair these losses. Any changed prediction, calibration, role routing or inverted selection needs a separately registered earlier-chosen procedure and later evaluation. Current production and original forecasts remain unchanged. Missing exact historical cells and recovery gates remain separate; no new fit or capture was admitted by this diagnostic.

[Complete machine scorecard](MATCHED_FOCAL_SCORECARD_V2.csv) · [Canonical scores](SCORES.json) · [Frozen roster/masks](FROZEN_PROTOCOL.json) · [Execution receipt](RUN_RECEIPT.json) · [Population bindings](POPULATION_COMPARISON_BINDINGS.json).
