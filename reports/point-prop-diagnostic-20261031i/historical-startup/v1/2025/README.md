# 2025: startup versus later regular-season numerical forecasts

This is a new split of already completed historical forecasts: Weeks1–4versus5–18, all twelve targets,457exact procedure/history/output/policy cells. No model was fitted or invoked and no full-season score was rerun. The fixed Leaf-CDF exemplar below makes category coverage readable; every procedure, loss and own learned/fallback split remains in the canonical source.

| Category | CURRENT W1–4 | RECENT W1–4 | MULTI W1–4 | CURRENT W5–18 | RECENT W5–18 | MULTI W5–18 | Strict-current early / later |
|---|---|---|---|---|---|---|---|
| anytime_td | 0.204505; n=1238; fallback=644/1258 | 0.153817; n=1238; fallback=105/1258 | 0.151859; n=1238; fallback=105/1258 | 0.142662; n=4056; fallback=58/4115 | 0.142236; n=4056; fallback=58/4115 | 0.141584; n=4056; fallback=58/4115 | 0.205923 / 0.145287 |
| nick-chart-ppr-v1 | 6.131507; n=1387; fallback=721/1414 | 4.479683; n=1387; fallback=114/1414 | 4.458255; n=1387; fallback=114/1414 | 4.378848; n=4550; fallback=68/4623 | 4.342448; n=4550; fallback=68/4623 | 4.337051; n=4550; fallback=68/4623 | 6.566316 / 4.476462 |
| pass_att | 19.487179; n=156; fallback=117/156 | 9.198718; n=156; fallback=9/156 | 9.134615; n=156; fallback=9/156 | 8.781496; n=508; fallback=10/508 | 8.517717; n=508; fallback=10/508 | 8.401575; n=508; fallback=10/508 | 19.378205 / 8.913386 |
| pass_cmp | 12.711538; n=156; fallback=117/156 | 6.025641; n=156; fallback=9/156 | 6.076923; n=156; fallback=9/156 | 6.169291; n=508; fallback=10/508 | 5.921260; n=508; fallback=10/508 | 5.877953; n=508; fallback=10/508 | 12.596154 / 6.222441 |
| pass_int | 0.557692; n=156; fallback=117/156 | 0.570513; n=156; fallback=9/156 | 0.615385; n=156; fallback=9/156 | 0.557087; n=508; fallback=10/508 | 0.572835; n=508; fallback=10/508 | 0.574803; n=508; fallback=10/508 | 0.557692 / 0.578740 |
| pass_td | 1.038462; n=156; fallback=117/156 | 0.788462; n=156; fallback=9/156 | 0.788462; n=156; fallback=9/156 | 0.927165; n=508; fallback=10/508 | 0.877953; n=508; fallback=10/508 | 0.862205; n=508; fallback=10/508 | 1.038462 / 0.944882 |
| pass_yd | 135.326923; n=156; fallback=117/156 | 75.230769; n=156; fallback=9/156 | 75.634615; n=156; fallback=9/156 | 72.606299; n=508; fallback=10/508 | 69.834646; n=508; fallback=10/508 | 68.783465; n=508; fallback=10/508 | 135.423077 / 76.222441 |
| rec | 1.717286; n=1238; fallback=644/1258 | 1.249596; n=1238; fallback=105/1258 | 1.251212; n=1238; fallback=105/1258 | 1.169132; n=4056; fallback=58/4115 | 1.160010; n=4056; fallback=58/4115 | 1.157544; n=4056; fallback=58/4115 | 1.895800 / 1.200197 |
| rec_yd | 19.281906; n=1238; fallback=644/1258 | 15.594507; n=1238; fallback=105/1258 | 15.491115; n=1238; fallback=105/1258 | 15.372288; n=4056; fallback=58/4115 | 15.233974; n=4056; fallback=58/4115 | 15.253698; n=4056; fallback=58/4115 | 21.286753 / 15.752219 |
| rush_att | 4.731801; n=522; fallback=269/524 | 2.938697; n=522; fallback=49/524 | 2.971264; n=522; fallback=49/524 | 2.872876; n=1707; fallback=24/1715 | 2.845343; n=1707; fallback=24/1715 | 2.852958; n=1707; fallback=24/1715 | 5.408046 / 2.937317 |
| rush_rec_yd | 26.241519; n=1238; fallback=644/1258 | 19.903069; n=1238; fallback=105/1258 | 19.906300; n=1238; fallback=105/1258 | 19.858235; n=4056; fallback=58/4115 | 19.698964; n=4056; fallback=58/4115 | 19.686391; n=4056; fallback=58/4115 | 28.633279 / 20.293146 |
| rush_yd | 22.392720; n=522; fallback=269/524 | 17.011494; n=522; fallback=49/524 | 17.009579; n=522; fallback=49/524 | 16.686585; n=1707; fallback=24/1715 | 16.650849; n=1707; fallback=24/1715 | 16.628002; n=1707; fallback=24/1715 | 24.959770 / 17.234329 |

Cells show native MAE, except anytime-TD uses Brier, followed by supported n and issued fallback/forecast counts. Do not compare unlike native units across categories. Nick chart remains the qualified partial-label research contract, not unrestricted full rare-component completeness or website-fantasy parity. The exact Leaf procedure/version, full empirical-median/event reference, membership match, error change and nonzero-denominator skill are in[the machine table](LEAF_STARTUP_COMPARISON.csv).

CURRENT uses only earlier eligible outcomes in the evaluation season for fitting. Common feature memory can still include older2022-start NFL history; strict-current input/prior policy is separate. RECENT uses the preceding season plus earlier evaluation-season outcomes where supported; MULTI expands from2022without pre2022history. No history arm uses target-game or later-season labels for its original fit.

FULL_SYSTEM includes startup fallbacks, sparse cases and missing labels. LEARNED_ONLY/FALLBACK_ONLY are each procedure’s own disjoint masks, not a shared learned population across competitors. Existing adjacent-history common-mask comparisons remain in checkpointD; these new own-mask numbers must not replace them.

Saved target/player/game IDs produce exact scored masks, unique games and players. Tail P90/P95 are explicitly not computed in this sufficient-stat split; weekly quantiles cannot be pooled. Exact maximum absolute error, strict/inclusive precision, signed bias and fallback counts are retained. Chart lower medians use the exact0.02grid for tolerances; that scoring rule is not a prediction improvement.

Every full-system recipe/week n×MAE/MSE/bias sum matches the existing valid weekly scoreboard; source-bound2025specialization repair replaces its losing original version only in the current view. All original and corrected rows remain preserved. Missing historical prop lines or original leans do not block this numerical benchmark. No offered-threshold, original-selection, EV or ROI result is invented.

[All new startup-window numerical views](STARTUP_NUMERICAL_RESULTS.csv) · [Canonical scores](SCORES.json) · [Execution/coverage checks](RUN_RECEIPT.json) · [Frozen procedure/source roster](../FROZEN_PROTOCOL.json).
