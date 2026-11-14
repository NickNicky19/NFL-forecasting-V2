# 2023 rolling learned-method evaluation

State: **COMPLETE_REPLAY_OF_RETAINED_WEEKLY_PACKETS**. This wave covers 272 regular-season games and 43,922 frozen target opportunities, including missing labels. It creates 3,142 fits and retains 3,142 models; 0 fits failed. Identical history policies reuse 1,152 fit cells without adding fits.

It records 14,770 aggregate score views and 1,592,629 forecast views, including 246,129 retained empirical views replayed with zero fits. Views, models and NFL games are separate counts.

All training labels precede the weekly origin under the conservative seven-day rule. Features refresh before each game; transformations use only the selected earlier training rows. CURRENT fits the evaluation season, RECENT its preceding season plus current games, and MULTI expands from2022. Common-memory arms still use earlier feature history; strict-current additionally removes that older memory and fitted priors. There is no pre2022 warm start.

| Target | Lowest observed procedure/product/history | Native error | Supported rows |
|---|---|---:|---:|
|pass_yd|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-MULTI-COMMON|71.208145|663|
|pass_td|v2-c02-explicit-lag-block-removal-leaf-cdf-v1:common-feature-memory / lower_median / H-MULTI-COMMON|0.788839|663|
|pass_cmp|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-MULTI-COMMON|5.956259|663|
|pass_att|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-MULTI-COMMON|8.657617|663|
|pass_int|empirical-player-history-control-v1 / lower_median / H-CURRENT-EMPIRICAL|0.647059|663|
|rush_yd|v2-c02-explicit-lag-block-removal-leaf-cdf-v1:common-feature-memory / lower_median / H-MULTI-COMMON|16.833255|2129|
|rush_att|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-MULTI-COMMON|3.111790|2129|
|rec|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-MULTI-COMMON|1.281312|5062|
|rec_yd|v2-c02-explicit-lag-block-removal-leaf-cdf-v1:common-feature-memory / lower_median / H-MULTI-COMMON|16.692414|5062|
|rush_rec_yd|hgb-direct-history-controls-v1:absolute_error_point:common-feature-memory / absolute_error_point / H-MULTI-COMMON|20.955738|5062|
|anytime_td|hgb-direct-history-controls-v1:log_loss_probability:common-feature-memory / log_loss_probability / H-MULTI-COMMON|0.142731|5062|
|nick-chart-ppr-v1|v2-qualified-partial-chart-direct-wave-v1:ordered_leaf_cdf:common-feature-memory / lower_median / H-MULTI-COMMON|4.473310|5713|

Numeric entries use MAE; anytime TD uses Brier. This table shows exposed observed minima, not a method-selection policy or a comparison across native units. Mean MSE and genuine-law CRPS/log scores remain separate in the complete score file. Every loss and fallback remains included.

Paired history contrasts retain identical player/game/target rows and report full systems plus paired learned-only intersections. Whole-week bootstrap intervals and game-cluster SE sensitivity follow the shared frozen uncertainty helper; exposed multiplicity and selection limits remain. An older-season result does not answer whether older training improves the same2026 games. Proper-law CRPS/PMF-log-loss contrasts retain infinite losses with undefined differences explicitly.

The cohort is a current-vintage retrospective statistical-row/physical-participation diagnostic, not a reconstructed ex-ante roster or authenticated offers panel. Chart uses the qualified partial sixteen-component contract; positive or missing rare credits remain unknown. Chart medians use exact0.02-grid precision arithmetic; means are never rounded. No2026 model is refitted, no current2026Week8 outcome is read, and no future forecast is created. Historical Week8 games in the evaluation year are included.

Resources: 683.56 active wall seconds, 828.51 CPU seconds, peak RSS 632,557,568 bytes, at most two threads. Private retained artifacts require the separately recorded offhost restoration before durability is claimed.
