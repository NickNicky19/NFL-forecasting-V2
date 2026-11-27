# Original selections: actual Over, Under and Combined

These are statistical threshold results on the same original 285 preselected cases from thirteen Week 7 games. The original full forecast feed has 1,419 ordinary-stat rows: 462 provider-labelled finite thresholds (441 DK, 21 Sleeper) and 957 site-generated thresholds. Original selection coverage is 285/1,419=20.08%; within the provider-labelled threshold pool it is 285/462=61.69%. The four controls were evaluated only on the conditional 285-case pool, not all 1,419. Provider labels do not authenticate quote clocks, prices, jurisdiction or settlement.

Every table groups the actual chosen side. Combined counts are the sum of Over and Under; percentages are calculated from summed wins/decided cases, never averaged across sides. Statistical pushes, unknown participation and missing labels remain separate. All book settlement is unresolved and all probabilities, Brier/log loss, EV, returns and ROI are unavailable. The saved-point control uses retained source precision; strict unrounded P1 is unavailable because the original producer rounded before retention.

| Category | Actual Over: selected; W/L/P; decided; hit; unknown | Actual Under: selected; W/L/P; decided; hit; unknown | Combined |
|---|---|---|---|
|ALL|135 selected; 85W/49L/0P; 134 decided; 63.43%; 1 unknown|150 selected; 98W/47L/0P; 145 decided; 67.59%; 5 unknown|285 selected; 183W/96L/0P; 279 decided; 65.59%; 6 unknown|
|pass_yd|8 selected; 6W/2L/0P; 8 decided; 75.00%; 0 unknown|12 selected; 8W/4L/0P; 12 decided; 66.67%; 0 unknown|20 selected; 14W/6L/0P; 20 decided; 70.00%; 0 unknown|
|pass_td|10 selected; 5W/5L/0P; 10 decided; 50.00%; 0 unknown|12 selected; 9W/3L/0P; 12 decided; 75.00%; 0 unknown|22 selected; 14W/8L/0P; 22 decided; 63.64%; 0 unknown|
|pass_cmp|4 selected; 4W/0L/0P; 4 decided; 100.00%; 0 unknown|11 selected; 8W/3L/0P; 11 decided; 72.73%; 0 unknown|15 selected; 12W/3L/0P; 15 decided; 80.00%; 0 unknown|
|pass_att|4 selected; 2W/2L/0P; 4 decided; 50.00%; 0 unknown|10 selected; 7W/3L/0P; 10 decided; 70.00%; 0 unknown|14 selected; 9W/5L/0P; 14 decided; 64.29%; 0 unknown|
|pass_int|7 selected; 5W/2L/0P; 7 decided; 71.43%; 0 unknown|4 selected; 4W/0L/0P; 4 decided; 100.00%; 0 unknown|11 selected; 9W/2L/0P; 11 decided; 81.82%; 0 unknown|
|rush_yd|29 selected; 15W/13L/0P; 28 decided; 53.57%; 1 unknown|10 selected; 6W/3L/0P; 9 decided; 66.67%; 1 unknown|39 selected; 21W/16L/0P; 37 decided; 56.76%; 2 unknown|
|rush_att|10 selected; 7W/3L/0P; 10 decided; 70.00%; 0 unknown|7 selected; 4W/3L/0P; 7 decided; 57.14%; 0 unknown|17 selected; 11W/6L/0P; 17 decided; 64.71%; 0 unknown|
|rec|25 selected; 20W/5L/0P; 25 decided; 80.00%; 0 unknown|56 selected; 35W/17L/0P; 52 decided; 67.31%; 4 unknown|81 selected; 55W/22L/0P; 77 decided; 71.43%; 4 unknown|
|rec_yd|33 selected; 17W/16L/0P; 33 decided; 51.52%; 0 unknown|24 selected; 15W/9L/0P; 24 decided; 62.50%; 0 unknown|57 selected; 32W/25L/0P; 57 decided; 56.14%; 0 unknown|
|rush_rec_yd|5 selected; 4W/1L/0P; 5 decided; 80.00%; 0 unknown|4 selected; 2W/2L/0P; 4 decided; 50.00%; 0 unknown|9 selected; 6W/3L/0P; 9 decided; 66.67%; 0 unknown|
|nick-chart-ppr-v1|Unavailable: no matching chart-threshold selection contract|Unavailable|Unavailable|
|anytime_td|Unavailable: no qualified event-offer/selection contract in numeric panel|Unavailable|Unavailable|

These ten categories are the supported source slice; the two unsupported targets have null counts/rates in [UNAVAILABLE_CELLS.json](UNAVAILABLE_CELLS.json), outside canonical scores. Supported empty sides, such as always-Under’s Over bucket, have zero selected cases and N/A rates. They are not an error-free forecast.

| Strategy | Actual Over | Actual Under | Combined |
|---|---|---|---|
|original|135 selected; 85W/49L/0P; 134 decided; 63.43%; 1 unknown|150 selected; 98W/47L/0P; 145 decided; 67.59%; 5 unknown|285 selected; 183W/96L/0P; 279 decided; 65.59%; 6 unknown|
|SAVED_POINT_DIRECTION_RETAINED_PRECISION|135 selected; 85W/49L/0P; 134 decided; 63.43%; 1 unknown|150 selected; 98W/47L/0P; 145 decided; 67.59%; 5 unknown|285 selected; 183W/96L/0P; 279 decided; 65.59%; 6 unknown|
|alwaysOver|285 selected; 132W/147L/0P; 279 decided; 47.31%; 6 unknown|0 selected; 0W/0L/0P; 0 decided; N/A; 0 unknown|285 selected; 132W/147L/0P; 279 decided; 47.31%; 6 unknown|
|alwaysUnder|0 selected; 0W/0L/0P; 0 decided; N/A; 0 unknown|285 selected; 147W/132L/0P; 279 decided; 52.69%; 6 unknown|285 selected; 147W/132L/0P; 279 decided; 52.69%; 6 unknown|

[Every method/category/actual-side/cohort/time view](ALL_ACTUAL_SIDE_VIEWS.csv) · [Cohort/category/side CSV](COHORT_BY_CATEGORY_SIDE.csv) · [All top-K views CSV](TOPK_BY_CATEGORY.csv) · [Unique-player/game and explicit time-alias supplement](METADATA_SUPPLEMENT.json).

The 285 original selections cover 136 unique players and 136 player-games across thirteen games in one week; 130 player-games have a qualified outcome and six remain appearance-unknown. Blank CSV metric/price cells represent null unavailable values, not zeros. The 2026 season view is an exact alias of this partial Week 7 slice, not a season-to-date or full-season evaluation. Each season-alias record explicitly points to its weekly record. Do not pool those aliases, strategies, overlapping cohorts or summary rows into additional NFL observations. The underlying population remains 285 player-game-target selections, including six unknown appearance cases; unique players and player-games differ from selection counts and are supplied for every view.

Previously saved Top flags remain original recorded subsets, with no replacements for the excluded earlier game. Reconstructed top-player/workload groups use earlier-availability profiles but were actually assembled after the games; they are diagnostic groups, not authentic original star lists. The ranking cutoff is later than the internal recorded capture clock, so it does not establish information available at that internal decision. Missing memberships remain an explicit cohort.

The new K 6/10/20 subsets are separately frozen per category, with Combined, Over-only and Under-only candidate pools. They rank absolute saved-point minus line gaps at retained precision with stable identity ties. Unknown outcomes, DNP and missing labels do not affect membership. They are NEW_RETRO_SUBSET within the already selected 285 cases, not original issued K, all offers, a full fourteen-game week or an evaluated live policy. No raw gaps are ranked across categories.

Game-cluster bootstrap intervals use 500 draws/seed 1703 when at least eight decided games contribute; otherwise they are unavailable. There is one supported week, so week intervals remain unavailable. These exposed descriptive sensitivity intervals are not adjusted for selection or multiplicity. Different selected-side pools do not establish a universal better side.

No outcomes were rejoined, no threshold was regraded and no model or forecast changed in this projection. All figures reuse the retained 1,140 strategy-grade rows. [Frozen protocol](FROZEN_PROTOCOL.json), [side-count reconciliation](ACTUAL_SIDE_RECONCILIATION.json) and [run receipt](RUN_RECEIPT.json) bind the sources and views.
