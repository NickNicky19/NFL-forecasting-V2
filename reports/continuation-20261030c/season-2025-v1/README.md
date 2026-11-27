# 2025 rolling learned-method evaluation

State: **COMPLETE**. This wave covers 272 regular-season games and 45,579 frozen target opportunities, including missing labels. It creates 4,294 fits and retains 4,294 models; 0 fits failed. Identical history policies reuse 0 fit cells without adding fits.

It records 14,770 aggregate score views and 1,652,071 forecast views, including 255,363 retained empirical views replayed with zero fits. Views, models and NFL games are separate counts.

All training labels precede the weekly origin under the conservative seven-day rule. Features refresh before each game; transformations use only the selected earlier training rows. CURRENT fits the evaluation season, RECENT its preceding season plus current games, and MULTI expands from2022. Common-memory arms still use earlier feature history; strict-current additionally removes that older memory and fitted priors. There is no pre2022 warm start.

| Target | Lowest observed procedure/product/history | Native error | Supported rows |
|---|---|---:|---:|
|pass_yd|hgb-direct-history-controls-v1:squared_error_mean:common-feature-memory / squared_error_mean / H-MULTI-COMMON|68.686969|664|
|pass_td|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-MULTI-COMMON|0.844880|664|
|pass_cmp|v2-hgb-poisson-count-point-reconstruction-v1:common-feature-memory / poisson_intended_mean_point / H-RECENT-COMMON|5.827708|664|
|pass_att|v2-hgb-poisson-count-point-reconstruction-v1:common-feature-memory / poisson_intended_mean_point / H-MULTI-COMMON|8.488384|664|
|pass_int|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-CURRENT-COMMON|0.557229|664|
|rush_yd|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-MULTI-COMMON|16.717362|2229|
|rush_att|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-RECENT-COMMON|2.867205|2229|
|rec|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-MULTI-COMMON|1.179448|5294|
|rec_yd|v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf:common-feature-memory / lower_median / H-MULTI-COMMON|15.309218|5294|
|rush_rec_yd|hgb-direct-history-controls-v1:absolute_error_point:common-feature-memory / absolute_error_point / H-MULTI-COMMON|19.710794|5294|
|anytime_td|hgb-direct-history-controls-v1:log_loss_probability:common-feature-memory / log_loss_probability / H-MULTI-COMMON|0.142770|5294|
|nick-chart-ppr-v1|v2-qualified-partial-chart-direct-wave-v1:ordered_leaf_cdf:common-feature-memory / lower_median / H-MULTI-COMMON|4.365366|5937|

Numeric entries use MAE; anytime TD uses Brier. This table shows exposed observed minima, not a method-selection policy or a comparison across native units. Mean MSE and genuine-law CRPS/log scores remain separate in the complete score file. Every loss and fallback remains included.

Paired history contrasts retain identical player/game/target rows and report full systems plus paired learned-only intersections. Whole-week bootstrap intervals and game-cluster SE sensitivity follow the shared frozen uncertainty helper; exposed multiplicity and selection limits remain. An older-season result does not answer whether older training improves the same2026 games. Proper-law CRPS/PMF-log-loss contrasts retain infinite losses with undefined differences explicitly.

The cohort is a current-vintage retrospective statistical-row/physical-participation diagnostic, not a reconstructed ex-ante roster or authenticated offers panel. Chart uses the qualified partial sixteen-component contract; positive or missing rare credits remain unknown. Chart medians use exact0.02-grid precision arithmetic; means are never rounded. No2026 model is refitted, no current2026Week8 outcome is read, and no future forecast is created. Historical Week8 games in the evaluation year are included.

Resources: 962.12 active wall seconds, 1245.47 CPU seconds, peak RSS 757,710,848 bytes, at most two threads. Private retained artifacts require the separately recorded offhost restoration before durability is claimed.

The current report applies the separately retained [original-recipe continuity repair](../season-2025-continuity-repair-v1/FROZEN_PROTOCOL.json). It replaces 176 score views from 24,148 carry-specialist forecast rows: 886 fallback annotations changed and 12 numeric predictions changed. All 4,294 fitted models and all original scores/rows remain retained. The audit found zero affected all-zero GLM count cells among 432 checked frames. This is a fallback/procedure repair, not a new fit or a pure scoring correction.

Same-history C02 reversals against the retained ordered control are in [the source-bound season comparison](C02_SAME_HISTORY_SEASON_REVERSALS.csv). For example, current-season-fit interception medians favor C02 in 2026(.566116 versus.611570 MAE) but favor the ordered control in 2025(.557229 versus C02.567771). Multiseason receptions similarly reverse: C02 wins2026(1.245515 versus1.254958) and loses 2025(1.188704 versus1.179448). Each comparison holds rows fixed within its season; the two seasons contain different games and do not by themselves answer the fixed2026 training-history question.
