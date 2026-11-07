# 2024: startup versus later regular-season numerical forecasts

This is a new split of already completed historical forecasts: Weeks1–4versus5–18, all twelve targets,457exact procedure/history/output/policy cells. No model was fitted or invoked and no full-season score was rerun. The fixed Leaf-CDF exemplar below makes category coverage readable; every procedure, loss and own learned/fallback split remains in the canonical source.

| Category | CURRENT W1–4 | RECENT W1–4 | MULTI W1–4 | CURRENT W5–18 | RECENT W5–18 | MULTI W5–18 | Strict-current early / later |
|---|---|---|---|---|---|---|---|
| anytime_td | 0.201576; n=1181; fallback=618/1213 | 0.138509; n=1181; fallback=88/1213 | 0.138586; n=1181; fallback=88/1213 | 0.151332; n=3913; fallback=60/3987 | 0.149096; n=3913; fallback=60/3987 | 0.149953; n=3913; fallback=60/3987 | 0.204481 / 0.154033 |
| nick-chart-ppr-v1 | 6.141774; n=1330; fallback=696/1367 | 4.513955; n=1330; fallback=95/1367 | 4.498226; n=1330; fallback=95/1367 | 4.545177; n=4412; fallback=68/4497 | 4.503781; n=4412; fallback=68/4497 | 4.516609; n=4412; fallback=68/4497 | 6.533489 / 4.638799 |
| pass_att | 18.279221; n=154; fallback=118/154 | 8.636364; n=154; fallback=7/154 | 8.402597; n=154; fallback=7/154 | 8.774510; n=510; fallback=8/510 | 8.411765; n=510; fallback=8/510 | 8.439216; n=510; fallback=8/510 | 18.188312 / 8.880392 |
| pass_cmp | 12.207792; n=154; fallback=118/154 | 5.896104; n=154; fallback=7/154 | 5.798701; n=154; fallback=7/154 | 5.970588; n=510; fallback=8/510 | 5.664706; n=510; fallback=8/510 | 5.700000; n=510; fallback=8/510 | 12.123377 / 6.062745 |
| pass_int | 0.558442; n=154; fallback=118/154 | 0.532468; n=154; fallback=7/154 | 0.519481; n=154; fallback=7/154 | 0.603922; n=510; fallback=8/510 | 0.609804; n=510; fallback=8/510 | 0.607843; n=510; fallback=8/510 | 0.558442 / 0.601961 |
| pass_td | 0.941558; n=154; fallback=118/154 | 0.714286; n=154; fallback=7/154 | 0.714286; n=154; fallback=7/154 | 0.874510; n=510; fallback=8/510 | 0.839216; n=510; fallback=8/510 | 0.849020; n=510; fallback=8/510 | 0.928571 / 0.888235 |
| pass_yd | 127.474026; n=154; fallback=118/154 | 66.857143; n=154; fallback=7/154 | 65.987013; n=154; fallback=7/154 | 71.705882; n=510; fallback=8/510 | 69.250980; n=510; fallback=8/510 | 69.509804; n=510; fallback=8/510 | 127.974026 / 73.886275 |
| rec | 1.753599; n=1181; fallback=618/1213 | 1.319221; n=1181; fallback=88/1213 | 1.312447; n=1181; fallback=88/1213 | 1.278048; n=3913; fallback=60/3987 | 1.257347; n=3913; fallback=60/3987 | 1.259903; n=3913; fallback=60/3987 | 1.924640 / 1.296703 |
| rec_yd | 19.807790; n=1181; fallback=618/1213 | 16.383573; n=1181; fallback=88/1213 | 16.342083; n=1181; fallback=88/1213 | 16.544595; n=3913; fallback=60/3987 | 16.417071; n=3913; fallback=60/3987 | 16.395860; n=3913; fallback=60/3987 | 21.413209 / 17.048556 |
| rush_att | 4.878906; n=512; fallback=260/515 | 2.980469; n=512; fallback=31/515 | 2.990234; n=512; fallback=31/515 | 3.034606; n=1676; fallback=25/1685 | 3.008353; n=1676; fallback=25/1685 | 2.991647; n=1676; fallback=25/1685 | 5.566406 / 3.124702 |
| rush_rec_yd | 27.526672; n=1181; fallback=618/1213 | 20.997460; n=1181; fallback=88/1213 | 20.970364; n=1181; fallback=88/1213 | 20.875799; n=3913; fallback=60/3987 | 20.798876; n=3913; fallback=60/3987 | 20.817020; n=3913; fallback=60/3987 | 30.593565 / 21.521339 |
| rush_yd | 23.791016; n=512; fallback=260/515 | 18.482422; n=512; fallback=31/515 | 18.365234; n=512; fallback=31/515 | 17.556086; n=1676; fallback=25/1685 | 17.526253; n=1676; fallback=25/1685 | 17.454654; n=1676; fallback=25/1685 | 26.410156 / 18.074582 |

Cells show native MAE, except anytime-TD uses Brier, followed by supported n and issued fallback/forecast counts. Do not compare unlike native units across categories. Nick chart remains the qualified partial-label research contract, not unrestricted full rare-component completeness or website-fantasy parity. The exact Leaf procedure/version, full empirical-median/event reference, membership match, error change and nonzero-denominator skill are in[the machine table](LEAF_STARTUP_COMPARISON.csv).

CURRENT uses only earlier eligible outcomes in the evaluation season for fitting. Common feature memory can still include older2022-start NFL history; strict-current input/prior policy is separate. RECENT uses the preceding season plus earlier evaluation-season outcomes where supported; MULTI expands from2022without pre2022history. No history arm uses target-game or later-season labels for its original fit.

FULL_SYSTEM includes startup fallbacks, sparse cases and missing labels. LEARNED_ONLY/FALLBACK_ONLY are each procedure’s own disjoint masks, not a shared learned population across competitors. Existing adjacent-history common-mask comparisons remain in checkpointD; these new own-mask numbers must not replace them.

Saved target/player/game IDs produce exact scored masks, unique games and players. Tail P90/P95 are explicitly not computed in this sufficient-stat split; weekly quantiles cannot be pooled. Exact maximum absolute error, strict/inclusive precision, signed bias and fallback counts are retained. Chart lower medians use the exact0.02grid for tolerances; that scoring rule is not a prediction improvement.

Every full-system recipe/week n×MAE/MSE/bias sum matches the existing valid weekly scoreboard; source-bound2025specialization repair replaces its losing original version only in the current view. All original and corrected rows remain preserved. Missing historical prop lines or original leans do not block this numerical benchmark. No offered-threshold, original-selection, EV or ROI result is invented.

[All new startup-window numerical views](STARTUP_NUMERICAL_RESULTS.csv) · [Canonical scores](SCORES.json) · [Execution/coverage checks](RUN_RECEIPT.json) · [Frozen procedure/source roster](../FROZEN_PROTOCOL.json).
