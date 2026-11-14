# 2024 rolling learned-method evaluation

State: **COMPLETE**. This wave covers 272 regular-season games and 44,368 frozen target opportunities, including missing labels. It creates 4,294 fits and retains 4,294 models; 0 fits failed. Identical history policies reuse 0 fit cells without adding fits.

It records 14,770 aggregate score views and 1,608,648 forecast views, including 248,616 retained empirical views replayed with zero fits. Views, models and NFL games are separate counts.

All training labels precede the weekly origin under the conservative seven-day rule. Features refresh before each game; transformations use only the selected earlier training rows. CURRENT fits the evaluation season, RECENT its preceding season plus current games, and MULTI expands from2022. Common-memory arms still use earlier feature history; strict-current additionally removes that older memory and fitted priors. There is no pre2022 warm start.

| Target | Lowest observed procedure/product/history | Native error | Supported rows |
|---|---|---:|---:|
|pass_yd|hgb-direct-history-controls-v1:absolute_error_point:common-feature-memory / absolute_error_point / H-RECENT-COMMON|67.689422|664|
|pass_td|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-RECENT-COMMON|0.810241|664|
|pass_cmp|hgb-direct-history-controls-v1:absolute_error_point:common-feature-memory / absolute_error_point / H-RECENT-COMMON|5.660122|664|
|pass_att|v2-hgb-poisson-count-point-reconstruction-v1:common-feature-memory / poisson_intended_mean_point / H-MULTI-COMMON|8.360291|664|
|pass_int|v2-c02-explicit-lag-block-removal-leaf-cdf-v1:common-feature-memory / lower_median / H-CURRENT-COMMON|0.579819|664|
|rush_yd|v2-c02-explicit-lag-block-removal-leaf-cdf-v1:common-feature-memory / lower_median / H-MULTI-COMMON|17.646709|2188|
|rush_att|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-MULTI-COMMON|2.991316|2188|
|rec|v2-c02-explicit-lag-block-removal-leaf-cdf-v1:common-feature-memory / lower_median / H-MULTI-COMMON|1.268748|5094|
|rec_yd|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-MULTI-COMMON|16.383392|5094|
|rush_rec_yd|hgb-direct-history-controls-v1:absolute_error_point:common-feature-memory / absolute_error_point / H-RECENT-COMMON|20.704934|5094|
|anytime_td|v2-distribution-controls-reconstruction-v2:regularized_glm_law:common-feature-memory / event_probability / H-RECENT-COMMON|0.145935|5094|
|nick-chart-ppr-v1|v2-qualified-partial-chart-direct-wave-v1:ordered_leaf_cdf:common-feature-memory / lower_median / H-RECENT-COMMON|4.506137|5742|

Numeric entries use MAE; anytime TD uses Brier. This table shows exposed observed minima, not a method-selection policy or a comparison across native units. Mean MSE and genuine-law CRPS/log scores remain separate in the complete score file. Every loss and fallback remains included.

Paired history contrasts retain identical player/game/target rows and report full systems plus paired learned-only intersections. Whole-week bootstrap intervals and game-cluster SE sensitivity follow the shared frozen uncertainty helper; exposed multiplicity and selection limits remain. An older-season result does not answer whether older training improves the same2026 games. Proper-law CRPS/PMF-log-loss contrasts retain infinite losses with undefined differences explicitly.

The cohort is a current-vintage retrospective statistical-row/physical-participation diagnostic, not a reconstructed ex-ante roster or authenticated offers panel. Chart uses the qualified partial sixteen-component contract; positive or missing rare credits remain unknown. Chart medians use exact0.02-grid precision arithmetic; means are never rounded. No2026 model is refitted, no current2026Week8 outcome is read, and no future forecast is created. Historical Week8 games in the evaluation year are included.

Resources: 892.52 active wall seconds, 1147.81 CPU seconds, peak RSS 724,901,888 bytes, at most two threads. Private retained artifacts require the separately recorded offhost restoration before durability is claimed.
