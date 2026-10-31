# 2022 rolling learned-method evaluation

State: **COMPLETE**. This wave covers 271 regular-season games and 43,821 frozen target opportunities, including missing labels. It creates 995 fits and retains 995 models; 0 fits failed. Identical history policies reuse 3,456 fit cells without adding fits.

It records 14,770 aggregate score views and 1,588,206 forecast views, including 245,502 retained empirical views replayed with zero fits. Views, models and NFL games are separate counts.

All training labels precede the weekly origin under the conservative seven-day rule. Features refresh before each game; transformations use only the selected earlier training rows. CURRENT fits the evaluation season, RECENT its preceding season plus current games, and MULTI expands from2022. Common-memory arms still use earlier feature history; strict-current additionally removes that older memory and fitted priors. There is no pre2022 warm start.

| Target | Lowest observed procedure/product/history | Native error | Supported rows |
|---|---|---:|---:|
|pass_yd|empirical-player-history-control-v1 / mean / H-CURRENT-EMPIRICAL|78.081631|633|
|pass_td|hgb-direct-history-controls-v1:absolute_error_point:common-feature-memory / absolute_error_point / H-CURRENT-COMMON|0.887704|633|
|pass_cmp|empirical-player-history-control-v1 / mean / H-CURRENT-EMPIRICAL|6.798419|633|
|pass_att|v2-hgb-poisson-count-point-reconstruction-v1:common-feature-memory / poisson_intended_mean_point / H-CURRENT-COMMON|10.060587|633|
|pass_int|v2-distribution-controls-reconstruction-v2:regularized_glm_law:common-feature-memory / lower_median / H-CURRENT-COMMON|0.665087|633|
|rush_yd|empirical-player-history-control-v1 / lower_median / H-CURRENT-EMPIRICAL|19.430713|2201|
|rush_att|empirical-player-history-control-v1 / mean / H-CURRENT-EMPIRICAL|3.453078|2201|
|rec|empirical-player-history-control-v1 / lower_median / H-CURRENT-EMPIRICAL|1.462505|5094|
|rec_yd|hgb-direct-history-controls-v1:absolute_error_point:common-feature-memory / absolute_error_point / H-CURRENT-COMMON|18.169745|5094|
|rush_rec_yd|hgb-direct-history-controls-v1:absolute_error_point:common-feature-memory / absolute_error_point / H-CURRENT-COMMON|23.884879|5094|
|anytime_td|hgb-direct-history-controls-v1:log_loss_probability:common-feature-memory / log_loss_probability / H-CURRENT-COMMON|0.153940|5094|
|nick-chart-ppr-v1|v2-c02-explicit-lag-block-removal-leaf-cdf-v1:common-feature-memory / lower_median / H-CURRENT-COMMON|5.173704|5718|

Numeric entries use MAE; anytime TD uses Brier. This table shows exposed observed minima, not a method-selection policy or a comparison across native units. Mean MSE and genuine-law CRPS/log scores remain separate in the complete score file. Every loss and fallback remains included.

Paired history contrasts retain identical player/game/target rows and report full systems plus paired learned-only intersections. Whole-week bootstrap intervals and game-cluster SE sensitivity follow the shared frozen uncertainty helper; exposed multiplicity and selection limits remain. An older-season result does not answer whether older training improves the same2026 games. Proper-law CRPS/PMF-log-loss contrasts retain infinite losses with undefined differences explicitly.

The cohort is a current-vintage retrospective statistical-row/physical-participation diagnostic, not a reconstructed ex-ante roster or authenticated offers panel. Chart uses the qualified partial sixteen-component contract; positive or missing rare credits remain unknown. Chart medians use exact0.02-grid precision arithmetic; means are never rounded. No2026 model is refitted, no current2026Week8 outcome is read, and no future forecast is created. Historical Week8 games in the evaluation year are included.

Resources: 422.24 active wall seconds, 436.92 CPU seconds, peak RSS 586,362,880 bytes, at most two threads. Private retained artifacts require the separately recorded offhost restoration before durability is claimed.

**2022 source boundary:** the displayed H-RECENT results are a source-limited 2022-only proxy. The requested preceding-2021 plus earlier-2022 comparison is unsupported by the registered sources and remains incomplete. CURRENT, expanding-from-2022 MULTI and strict-current startup arms intentionally share the same available football data in2022. Identical proxy scores do not show that older history is unhelpful. The separately registered source-boundary amendment and1,152 requested-cell statuses preserve this gap. No pre2022 source is silently introduced.
