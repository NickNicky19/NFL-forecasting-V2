# Numerical category champions — bounded verified library

All twelve targets; fixed 2026 REG Weeks 1–7, 107 games. Prior seasons are separately complete 2022–2025 REG Weeks 1–18 evaluations (2022:271 games; others:272). New work recomputed **220 paired contrasts** from retained rows: full-system, common-both-learned and any-fallback views. No fits, new forecasts or new NFL observations. 35 current leader rows include the receptions tie.

The winners below are **best among verified comparable tested procedures**, on an exposed current-vintage retrospective participant panel. They are not actual offered-line probability or Over/Under winners. Current 2026 has seven week clusters, so no week-bootstrap interval is reported; game-cluster intervals are descriptive sensitivity checks, not selection-adjusted evidence.

## Current displayed-point MAE and anytime-TD Brier

| Category | Best observed exact output/history | Error | Runner-up error | Paired delta | n / games | Scored fallback | Prior seasons for exact leader |
|---|---|---:|---:|---:|---|---|---|
| anytime_td | HGB binary log-loss / H-MULTI / log_loss_probability | 0.143144 | 0.143755 | -0.000611 | 2118 / 107 | 0/2118 | 2025,2024,2023,2022 |
| nick-chart-ppr-v1 | D2 Leaf-CDF / H-MULTI / lower_median | 4.490360 | 4.494362 | -0.004002 | 2359 / 107 | 111/2359 | FIT_REQUIRED |
| pass_att | D2 Leaf-CDF / H-MULTI / lower_median | 7.971074 | 8.004132 | -0.033058 | 242 / 107 | 6/242 | FIT_REQUIRED |
| pass_cmp | D1 Leaf-CDF / H-MULTI / lower_median | 5.342975 | 5.413223 | -0.070248 | 242 / 107 | 6/242 | FIT_REQUIRED |
| pass_int | C02 Leaf-CDF / H-CURRENT / lower_median | 0.566116 | 0.590909 | -0.024793 | 242 / 107 | 115/242 | 2025,2024,2023,2022 |
| pass_td | D1 Leaf-CDF / H-MULTI / lower_median | 0.809917 | 0.822314 | -0.012397 | 242 / 107 | 6/242 | FIT_REQUIRED |
| pass_yd | HGB absolute-error / H-MULTI / absolute_error_point | 66.117313 | 66.772727 | -0.655414 | 242 / 107 | 0/242 | 2025,2024,2023,2022 |
| rec | D2 Leaf-CDF / H-MULTI / lower_median (tie) | 1.245515 | 1.246459 | -0.000944 | 2118 / 107 | 105/2118 | FIT_REQUIRED |
| rec | C02 Leaf-CDF / H-MULTI / lower_median (tie) | 1.245515 | 1.246459 | -0.000944 | 2118 / 107 | 105/2118 | 2025,2024,2023,2022 |
| rec_yd | D2 Leaf-CDF / H-MULTI / lower_median | 16.189330 | 16.198772 | -0.009443 | 2118 / 107 | 105/2118 | FIT_REQUIRED |
| rush_att | D1 Leaf-CDF / H-MULTI / lower_median | 3.058057 | 3.059242 | -0.001185 | 844 / 107 | 33/844 | FIT_REQUIRED |
| rush_rec_yd | HGB absolute-error / H-MULTI / absolute_error_point | 20.125661 | 20.212465 | -0.086804 | 2118 / 107 | 0/2118 | 2025,2024,2023,2022 |
| rush_yd | D1 Leaf-CDF / H-MULTI / lower_median | 16.688389 | 16.704976 | -0.016588 | 844 / 107 | 33/844 | FIT_REQUIRED |

Receptions: D2 and C02 tie at 1.2455146364494807. The runner-up column is the **next distinct score**, D1 1.246458923512748. Their exact-zero head-to-head MAE difference is retained; their individual errors and precision numerators differ. Chart PPR has35 unresolved labels among2394 issued participant rows; scoring uses2359, never zero-filled. Primary rushing is RB; extended QB/WR/TE panels remain separate in the retained source results.

## Mean MSE and whole-distribution CRPS

| Category | Genuine-mean MSE leader / error | Whole-distribution CRPS leader / error |
|---|---|---|
| nick-chart-ppr-v1 | Empirical / H-RECENT / mean · 39.131594 | D1 Leaf-CDF / H-MULTI / lower_median · 3.178365 |
| pass_att | HGB squared-error / H-MULTI / squared_error_mean · 117.049484 | C02 Leaf-CDF / H-MULTI / lower_median · 5.854494 |
| pass_cmp | HGB squared-error / H-MULTI / squared_error_mean · 48.895351 | D1 Leaf-CDF / H-MULTI / lower_median · 3.898686 |
| pass_int | HGB squared-error / H-RECENT / squared_error_mean · 0.517752 | Pooled GLM law / H-MULTI / lower_median · 0.366766 |
| pass_td | Empirical / H-MULTI / empirical_mean · 1.162517 | C02 Leaf-CDF / H-MULTI / lower_median · 0.585096 |
| pass_yd | D2 Leaf-CDF / H-MULTI / mean · 7206.410794 | D2 Leaf-CDF / H-MULTI / lower_median · 47.273627 |
| rec | HGB squared-error / H-MULTI / squared_error_mean · 3.213584 | D1 Leaf-CDF / H-MULTI / lower_median · 0.890269 |
| rec_yd | Empirical / H-RECENT / empirical_mean · 589.509893 | Leaf-CDF / H-MULTI / lower_median · 11.593831 |
| rush_att | HGB squared-error / H-MULTI / squared_error_mean · 18.231617 | D2 Leaf-CDF / H-MULTI / lower_median · 2.160427 |
| rush_rec_yd | Pooled GLM law / H-MULTI / mean · 809.528329 | D1 Leaf-CDF / H-MULTI / lower_median · 14.344216 |
| rush_yd | D2 Leaf-CDF / H-MULTI / mean · 598.293095 | D2 Leaf-CDF / H-MULTI / lower_median · 11.824689 |

CRPS here replays original retained per-row proper-score summaries and verifies their aggregate; it does not independently regenerate PMFs. Point MAE/MSE/Brier are recalculated from saved predictions and outcomes. CRPS is not a probability score at an offered bookmaker line. The full machine-readable tables retain every exact procedure/version, metric, bias, tails, precision numerator/denominator, coverage, fallback, comparator and uncertainty.

## Older seasons and reversals

| Category | 2025 MAE/Brier minimum | 2024 minimum | 2023 minimum | 2022 available-source minimum |
|---|---|---|---|---|
| anytime_td | HGB binary log-loss / H-MULTI · 0.142770 (n=5294) | Pooled GLM law / H-RECENT · 0.145935 (n=5094) | HGB binary log-loss / H-MULTI · 0.142731 (n=5062) | HGB binary log-loss / H-CURRENT · 0.153940 (n=5094) |
| nick-chart-ppr-v1 | Leaf-CDF / H-MULTI · 4.365366 (n=5937) | Leaf-CDF / H-RECENT · 4.506137 (n=5742) | Leaf-CDF / H-MULTI · 4.473310 (n=5713) | C02 Leaf-CDF / H-CURRENT · 5.173704 (n=5718) |
| pass_att | HGB Poisson-objective point / H-MULTI · 8.488384 (n=664) | HGB Poisson-objective point / H-MULTI · 8.360291 (n=664) | Leaf-CDF / H-MULTI · 8.657617 (n=663) | HGB Poisson-objective point / H-CURRENT · 10.060587 (n=633) |
| pass_cmp | HGB Poisson-objective point / H-RECENT · 5.827708 (n=664) | HGB absolute-error / H-RECENT · 5.660122 (n=664) | Leaf-CDF / H-MULTI · 5.956259 (n=663) | Empirical / H-CURRENT · 6.798419 (n=633) |
| pass_int | Leaf-CDF / H-CURRENT · 0.557229 (n=664) | C02 Leaf-CDF / H-CURRENT · 0.579819 (n=664) | Empirical / H-CURRENT · 0.647059 (n=663) | Pooled GLM law / H-CURRENT · 0.665087 (n=633) |
| pass_td | Leaf-CDF / H-MULTI · 0.844880 (n=664) | Leaf-CDF / H-RECENT · 0.810241 (n=664) | C02 Leaf-CDF / H-MULTI · 0.788839 (n=663) | HGB absolute-error / H-CURRENT · 0.887704 (n=633) |
| pass_yd | HGB squared-error / H-MULTI · 68.686969 (n=664) | HGB absolute-error / H-RECENT · 67.689422 (n=664) | Leaf-CDF / H-MULTI · 71.208145 (n=663) | Empirical / H-CURRENT · 78.081631 (n=633) |
| rec | Leaf-CDF / H-MULTI · 1.179448 (n=5294) | C02 Leaf-CDF / H-MULTI · 1.268748 (n=5094) | Leaf-CDF / H-MULTI · 1.281312 (n=5062) | Empirical / H-CURRENT · 1.462505 (n=5094) |
| rec_yd | Leaf-CDF / H-MULTI · 15.309218 (n=5294) | Leaf-CDF / H-MULTI · 16.383392 (n=5094) | C02 Leaf-CDF / H-MULTI · 16.692414 (n=5062) | HGB absolute-error / H-CURRENT · 18.169745 (n=5094) |
| rush_att | Leaf-CDF / H-RECENT · 2.867205 (n=2229) | Leaf-CDF / H-MULTI · 2.991316 (n=2188) | Leaf-CDF / H-MULTI · 3.111790 (n=2129) | Empirical / H-CURRENT · 3.453078 (n=2201) |
| rush_rec_yd | HGB absolute-error / H-MULTI · 19.710794 (n=5294) | HGB absolute-error / H-RECENT · 20.704934 (n=5094) | HGB absolute-error / H-MULTI · 20.955738 (n=5062) | HGB absolute-error / H-CURRENT · 23.884879 (n=5094) |
| rush_yd | Leaf-CDF / H-MULTI · 16.717362 (n=2229) | C02 Leaf-CDF / H-MULTI · 17.646709 (n=2188) | C02 Leaf-CDF / H-MULTI · 16.833255 (n=2129) | Empirical / H-CURRENT · 19.430713 (n=2201) |

The 2022 RECENT arm still lacks qualified2021 inputs: equal values are the declared available-2022 proxy, not a completed prior-year experiment. MULTI expands from2022; no pre2022 training is introduced. CURRENT fitting retains older feature memory unless the exact strict-information procedure says otherwise.

Fixed current recipes are compared on older seasons only when their exact procedure/history/output exists. D1/D2 have no prior-season fits; those cells remain FIT_REQUIRED. Their current observed first places stay visible, while the separate `best_current_with_prior_season_procedure` field identifies the best current recipe with a complete older season. That coverage qualification does not make it production-ready.

- anytime_td, 2025: fixed-current ordering persists; HGB binary log-loss / H-MULTI / log_loss_probability 0.142770 versus Empirical / H-MULTI / event_probability 0.147193; delta -0.004423, nominal whole-week95% [-0.006608, -0.002289].
- pass_int, 2025: fixed-current ordering persists; C02 Leaf-CDF / H-CURRENT / lower_median 0.567771 versus Empirical / H-CURRENT / lower_median 0.602410; delta -0.034639, nominal whole-week95% [-0.077943, 0.012923].
- pass_yd, 2025: fixed-current ordering persists; HGB absolute-error / H-MULTI / absolute_error_point 69.016834 versus Leaf-CDF / H-MULTI / lower_median 70.393072; delta -1.376238, nominal whole-week95% [-2.229347, -0.428340].
- rush_rec_yd, 2025: fixed-current ordering persists; HGB absolute-error / H-MULTI / absolute_error_point 19.710794 versus Leaf-CDF / H-RECENT / lower_median 19.746694; delta -0.035901, nominal whole-week95% [-0.171523, 0.097011].
- anytime_td, 2024: fixed-current ordering persists; HGB binary log-loss / H-MULTI / log_loss_probability 0.146578 versus Empirical / H-MULTI / event_probability 0.148881; delta -0.002303, nominal whole-week95% [-0.005506, 0.000899].
- pass_int, 2024: fixed-current ordering persists; C02 Leaf-CDF / H-CURRENT / lower_median 0.579819 versus Empirical / H-CURRENT / lower_median 0.606928; delta -0.027108, nominal whole-week95% [-0.061917, 0.004370].
- pass_yd, 2024: fixed-current ordering persists; HGB absolute-error / H-MULTI / absolute_error_point 68.104974 versus Leaf-CDF / H-MULTI / lower_median 68.692771; delta -0.587797, nominal whole-week95% [-1.505680, 0.308703].
- rush_rec_yd, 2024: fixed-current ordering persists; HGB absolute-error / H-MULTI / absolute_error_point 20.715302 versus Leaf-CDF / H-RECENT / lower_median 20.844916; delta -0.129614, nominal whole-week95% [-0.254386, -0.024769].
- anytime_td, 2023: fixed-current ordering persists; HGB binary log-loss / H-MULTI / log_loss_probability 0.142731 versus Empirical / H-MULTI / event_probability 0.149711; delta -0.006980, nominal whole-week95% [-0.009868, -0.004174].
- pass_int, 2023: fixed-current ordering reverses; C02 Leaf-CDF / H-CURRENT / lower_median 0.669683 versus Empirical / H-CURRENT / lower_median 0.647059; delta 0.022624, nominal whole-week95% [-0.039572, 0.079008].
- pass_yd, 2023: fixed-current ordering reverses; HGB absolute-error / H-MULTI / absolute_error_point 72.184732 versus Leaf-CDF / H-MULTI / lower_median 71.208145; delta 0.976587, nominal whole-week95% [-0.535408, 2.770564].
- rush_rec_yd, 2023: fixed-current ordering persists; HGB absolute-error / H-MULTI / absolute_error_point 20.955738 versus Leaf-CDF / H-RECENT / lower_median 21.054129; delta -0.098391, nominal whole-week95% [-0.195309, -0.008905].
- anytime_td, 2022: fixed-current ordering persists; HGB binary log-loss / H-MULTI / log_loss_probability 0.153940 versus Empirical / H-MULTI / event_probability 0.175648; delta -0.021709, nominal whole-week95% [-0.034994, -0.010649].
- pass_int, 2022: fixed-current ordering persists; C02 Leaf-CDF / H-CURRENT / lower_median 0.671406 versus Empirical / H-CURRENT / lower_median 0.728278; delta -0.056872, nominal whole-week95% [-0.119130, 0.000104].
- pass_yd, 2022: fixed-current ordering persists; HGB absolute-error / H-MULTI / absolute_error_point 79.814617 versus Leaf-CDF / H-MULTI / lower_median 89.265403; delta -9.450786, nominal whole-week95% [-24.834630, -0.453701].
- rush_rec_yd, 2022: fixed-current ordering persists; HGB absolute-error / H-MULTI / absolute_error_point 23.884879 versus Leaf-CDF / H-RECENT / lower_median 24.319984; delta -0.435106, nominal whole-week95% [-1.163497, 0.024008].

All same-season winners/runner-ups, losses and full/common-learned/fallback paired uncertainty are retained in per-season `PAIRED_COMPARISONS.csv/json`; `SEASON_CHAMPIONS_NUMERICAL.csv` separates MAE, mean MSE and CRPS winners. Pooled micro averages use sum(n×loss)/sum(n), while season-balanced values average **exactly2022,2023,2024,2025** with equal season weight. Missing-season recipes are omitted from that comparison with an explicit gap, rather than compared using unequal available-year pools. Current2026 stays separate.

## Release conclusion and boundaries

No category is newly eligible for release from these numerical comparisons alone. The incumbent remains unproven on a matched full-period panel; archived R0 wins8/10 supported numeric categories on its narrower13-game Week7 panel, whose horizon differs. Current source-vintage/kickoff reconstruction is not T-minus90 original issuance. Exact model/input recovery, deterministic runtime/fallback/rollback parity, appropriate later confirmation and retained-owner admission remain required. No merge, deployment or selection change occurred.

Readable role/top-player and offered-line side/price scorecards are separate products. A numerical leader is not automatically an Over/Under leader. See the parent championship report for original/retrospective offer coverage and selected-side numerators.

[Current champions](CATEGORY_CHAMPIONS_NUMERICAL.csv) · [All913 procedure/product/season representatives](ALL_VALID_REPRESENTATIVES.csv) · [Season champions](SEASON_CHAMPIONS_NUMERICAL.csv) · [Fixed-current recipes on older seasons](FIXED_CURRENT_RECIPES_PRIOR_SEASONS.csv) · [Four-season aggregates](FIXED_RECIPE_FOUR_SEASON_AGGREGATES.csv) · [Exact missing recipe cells](EXACT_RECIPE_GAPS.csv) · [Frozen protocol](FROZEN_PROTOCOL.json)
