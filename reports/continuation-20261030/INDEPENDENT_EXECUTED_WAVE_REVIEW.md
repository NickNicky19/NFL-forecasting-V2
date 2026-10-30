# Independent executed-wave review

**Native errors, source prefixes, fitted-model replays and sampled distribution mathematics pass the checks below. An exact-grid chart-median precision defect requires the append-only correction described below.** The reviewer performed **zero fits/refits**, issued no new forecasts and opened **no actual Week 8 outcome source**. These are bounded verifications of new, exposed-history reconstructions and genuine partial-week shadows, not a complete legacy-method census, untouched confirmation or production release.

## Numerical scope

| Executed source-matched wave | Independently checked score views | Historical forecast-row/source joins | Independent metric/count checks | Largest native metric difference |
|---|---:|---:|---:|---:|
| Ordered Leaf-CDF and regularized GLM laws | 2,736 | 230,032 | 66,192 | 1.82e−12 |
| HGB count/role ablations | 424 | 32,600 | 7,208 | 6.58e−14 |
| Direct partial-chart laws | 208 | 38,304 | 4,992 | 6.40e−14 |
| Empirical chart controls, 2022–2026 | 630 | 155,424 rows, 466,272 value/clock checks | 10,080 | 3.91e−14 |

All means, MAE/MSE/RMSE, bias, tail errors, exact and strict/inclusive tolerance rates were independently recalculated from retained predictions and raw-source labels. The checks implement the frozen IEEE-754 error-subtraction convention, including threshold boundaries; decimal-string subtraction alone is a different convention. Probability comparisons use Brier and PMF log loss. Distribution-score aggregates, infinite-loss counts, intervals and zero mass were also recomputed. Tolerance rates are actual threshold numerators/denominators; no `1−MAE` accuracy percentage is used.

### Exact-grid median precision finding

Reproducing that float implementation exposed a separate mathematical precision issue. Genuine chart medians and labels lie exactly on the 0.02-point grid. Float subtraction can move an exact 1-, 5- or 10-point difference across a strict/inclusive boundary. The [independent grid audit](CHART_EXACT_GRID_PRECISION_AUDIT.json) checks **1,007 median score views**; **478** have at least one changed tolerance rate. On **95,279 unique scored median prediction rows**, disagreements number 72 for `<1`, 62 for `≤1`, 32 for `<5`, 60 for `≤5`, 14 for `<10` and 11 for `≤10`. Views reuse rows, so these counts do not represent new NFL observations.

The audit verifies integral coordinates using `Decimal(str(value))*50` and compares integer differences with 50/250/500. It excludes **all mean products** and supplies exact numerator/denominator projections bound to original score hashes. Original forecasts and score files remain intact; native MAE/RMSE/bias and probability-law results are unchanged. Append a corrected precision-only projection/version and retain the old diagnostics as affected, rather than claiming predictive improvement or refitting models.

Each corresponding [score review](DISTRIBUTION_INDEPENDENT_SCORE_REVIEW.json), [count review](COUNT_ABLATION_INDEPENDENT_SCORE_REVIEW.json), [chart review](CHART_INDEPENDENT_SCORE_REVIEW.json) and [empirical-chart review](CHART_EMPIRICAL_INDEPENDENT_REVIEW.json) pins the run/protocol and retains redacted wins and losses. Exact scored/forecast game counts for every direct score view are retained in the matching `*_VIEW_GAME_COUNTS.json` files, rather than assigning 107 games to every subset.

## Chronology, features and actual models

The independent raw-prefix audit checked **all 704 distribution, 224 count and 64 chart training memberships**, their source seasons and strict availability clocks. It rebuilt **694,760 / 255,080 / 113,120 query feature values**, respectively, including ordered missing slots and position indicators. Every historical training row's feature cutoff is its own kickoff; training labels obey the registered strict `kickoff + seven days < weekly fit origin` assumption. Query features refresh at the registered per-game cutoff. This verifies the implemented reconstruction rule, not actual historical provider publication/revision clocks.

All four policy cohorts remain identical within each compatible category/product comparison. Common-memory H-CURRENT fits only 2026 labels but retains older 2022-start features. The separately identified strict arm limits football outcomes in labels/features/priors/transforms to 2026; fixed architecture/settings remain inherited from earlier exposed research, and retrospective identity/participant/source-vintage limits remain. Strict versus common current is an information-policy comparison, not merely fit-window length.

The [distribution-law review](DISTRIBUTION_LAW_INDEPENDENT_REVIEW.json) verifies all **596 retained model hashes**, and independently reconstructs **1,386 sampled laws**: 976 from existing core-estimator inference and 410 priors. **12,964 law-summary checks** match separately implemented PMF sums and direct log mass within 1.99e−13, including signed support, quantiles, zero mass, CRPS and genuine endpoint/infinite-loss behavior. No production `Law` scoring method supplies the independent expected answers. These uncalibrated laws are mathematical assumptions whose empirical calibration still needs interpretation; they are not authenticated by their fitting-objective names.

All **188 count models** were replayed on their retained feature matrices, checking **30,292 fitted predictions and 5,192 fallback predictions**. Their fixed objectives/settings and 64 iterations agree with the registration. This uses trusted, digest-verified self-produced pickles for inference only.

The [chart-law review](CHART_LAW_INDEPENDENT_REVIEW.json) verifies all **56 chart model hashes**, reconstructs 126 sampled laws and checks 1,164 quantities. Integer score×50 coordinates preserve PMF mass; points, quantiles, interval widths and CRPS divide by 50, while discrete log mass is unchanged. The largest difference is 2.31e−12 in grid coordinates. No component medians were added to produce a fantasy median, and no component joint law is claimed.

## Adverse results and genuine improvements

The original broad-role HGB absolute-loss carry loss remains unchanged. Its constant-sign gradients at zero and median leaf updates explain a degenerate zero-heavy forecast; it was not a scorer or clipping defect. The new QB/RB training specialization is separately registered and changes the mechanism. On the same **844 primary QB/RB outcomes**, its H-RECENT MAE is **3.112707**, versus the original **6.529621**. On the separately retained **1,516 extended WR/TE rows**, its MAE is **0.571292**, an adverse change from the original 0.098945. Specialization is not a universal win, and extended structural zeros cannot dilute the primary comparison.

The new H-RECENT Leaf-CDF passing-yard median has MAE **67.355372** on 242 QB outcomes, compared with the new GLM law's **73.615702**. For primary receptions, their median MAEs are **1.253541 / 1.364495** on 2,118 outcomes. TD probability Brier instead is **0.145894457 / 0.144105448**, favoring GLM in this comparison. These are measured, product-specific descriptive results, not significance certificates or a universal method/history winner.

Worked chart examples retain both directions: opaque row `9f88ac167e4e51dc` has Leaf-CDF versus empirical absolute error **15.20 / 22.88**, while `df541bc380fc6840` has **6.80 / 0.88**. The direct H-RECENT chart medians score **4.499958** for Leaf-CDF and **4.573311** for GLM on the same 2,359 supported outcomes. Coverage below is essential to interpreting those figures.

## Exact chart contract and missing coverage

The [source qualification](CHART_PPR_SOURCE_QUALIFICATION.md) restores five pre-Week-8 RDS companions, verifies all **12,498,900 CSV cells**, and traces the actual producer-version recipes. Twelve direct primitives plus a conditional rare-zero proof define a **partial** chart label. Both nonnegative recovery/special-team supersets must explicitly be zero under the stated full-week provider contract. Positive supersets are never substituted as chart credits. This is a source-specific completeness assumption, not a replay of every official play.

The reviewer independently recomputed all **25,904 retained label values** and checked every one of their **414,464 component values** against raw source fields and the four-component zero rule. The [component-packet receipt](CHART_COMPONENT_PACKET_INDEPENDENT_REVIEW.json) records the exact hash. Among the registered 2,394 current QB/RB/WR/TE queries, **2,359 labels are supported, 34 have unverified appearance and one has unresolved rare TD attribution**. All remain in coverage. Seven other rare-positive current source rows lie outside that preregistered four-role diagnostic, making eight unresolved rare-positive source rows overall; all 164 across the five-season source remain unresolved. FB/other-returner extensions need their own population contract and cannot be inferred from this four-role panel.

The empirical chart controls retain all 155,424 forecasts across 2022–2026, and 120 independently rebuilt season/history/product/position examples match their actual prefix means/medians. Labels, chronology and all 630 score views pass. Scoring-contract correction is not itself a predictive improvement, and lower partial-panel error cannot establish full rare-event performance.

The separate [chart-cohort review](CHART_COHORT_INDEPENDENT_REVIEW.json) rebuilds all **2,394 historical and 434 future profiles**, with **14,140 raw-prefix profile checks, 5,656 rank/membership checks and 22,344 metric/cohort-hash checks** across all **1,176 score views**. It reproduces the common all-competitor learned intersection of **1,487 rows** and leaves two blocked future queries unranked. Prior signed chart-score history is explicitly a score-history selector, not snaps/routes/workload. Missing slots consume the three-slot window. Old-memory cohort membership around a strict model is a diagnostic view, not a pure-current selected system. The precision amendment above also covers these cohort median diagnostics.

## Failures, recovery and future capture

Distribution v1 stopped on `priors[None]` when blocked missing-board queries entered law inference before abstention filtering. The reviewer confirmed the concrete mechanism. Its **57 fitted models and 56 persisted packets / 6,224 views remain retained**. The original 6,966 counter reserved views before failed inference; the additive correction separates this from actual forecasts. Recovery v2 excludes blocked queries before inference, reuses those 57 models and original 6,224 forecasts/clocks, and fits only 539 remaining models. The 704-cell grid includes 108 explicit fallback cells; no failed version or consumed resources are erased.

The new future captures cover **13 games**, excluding the first CAR–GB game whose 00:15 UTC kickoff had elapsed. Each issued row's actual issue/persistence precedes its owner T−90 cutoff; old full-week captures remain unchanged.

| New shadow package | Issued views | Abstention views | Query scope |
|---|---:|---:|---|
| Distribution recovery | 25,464 | 80 | 1,795 frozen query cells, 13 games |
| Count ablations | 2,884 | 8 | 621 count query cells, 13 games |
| Direct chart laws | 6,912 | 32 | 434 deduplicated player-games, 13 games |

The shared new feature origin is 00:27:36 UTC. It crosses the seven-day availability boundary for the prior NE–CHI game relative to the original HGB 23:16 origin. Thus future new-versus-old comparisons also change the available information, while the historical common-memory role ablation holds origins fixed. No new package is backdated to the old owner cutoff or counted as a full fourteen-game capture.

All future actuals remain null. This review does not grade Week 8, authenticate offers/prices, select wagers, claim calibrated live probabilities or change the website. The executor separately retains approved private source/model packages and restoration receipts. Subsequent outcome grading needs qualified final labels and a schema-specific reviewed adapter. Seven evaluated 2026 weeks do not satisfy the inherited eight-week minimum for a week-bootstrap inference; paired losses and game dependence remain visible without an invented significance result.
