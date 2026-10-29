# Two-family observed comparison: fixed 2026 Weeks 1–7

HGB has the lower observed family-minimum MAE/Brier in seven of eleven supported targets. The empirical family is lower for passing TDs, interceptions, rushing yards and receiving yards. This is an exposed comparison of **two families**, not five independent learners or a frozen future selector. Exact chart PPR remains blocked. These minima choose among the registered products and three history regimes after observing their errors.

Both families use the same source-matched primary player-game identities and labels. Every one of 63 family/objective/history contrasts was checked against the [independent saved-row reconciliation](../verification/HGB_PAIRED_COMPARISONS.json). Here `primary`, `week=ALL`, `position=ALL` includes full startup/fallback contribution, with no learned-only filtering. It covers all 107 games in 2026 Weeks 1–7, but supported rows remain target/position-specific; the underlying cohort is retrospective observed participation, with current-vintage sources and assumed seven-day availability. Their representations and refit/update rules differ, so this is a procedure comparison rather than a pure learner ablation.

[Point/Brier CSV](TWO_FAMILY_PRIMARY_COMPARISON_2026_W1_W7.csv) · [Separate intended-mean MSE/RMSE CSV](TWO_FAMILY_MEAN_MSE_2026_W1_W7.csv) · [HGB methods, losses and startup comparison](hgb-history-v1/README.md)

| Target | Rows | Empirical best observed product / history | MAE or Brier | HGB best observed objective / history | MAE or Brier | Lower observed family |
|---|---:|---|---:|---|---:|---|
| pass_yd | 242 | empirical_mean / H-RECENT | 69.185345 | absolute_error_point / H-MULTI | 66.117313 | HGB |
| pass_td | 242 | lower_median / H-MULTI | 0.822314 | absolute_error_point / H-MULTI | 0.852635 | empirical |
| pass_cmp | 242 | empirical_mean / H-RECENT | 5.741918 | absolute_error_point / H-MULTI | 5.419172 | HGB |
| pass_att | 242 | empirical_mean / H-RECENT | 8.594731 | absolute_error_point / H-MULTI | 8.027582 | HGB |
| pass_int | 242 | lower_median / H-CURRENT | 0.590909 | absolute_error_point / H-CURRENT | 0.594576 | empirical |
| rush_yd | 844 | lower_median / H-RECENT | 16.863744 | squared_error_mean / H-RECENT | 17.265655 | empirical |
| rush_att | 844 | lower_median / H-RECENT | 3.188389 | squared_error_mean / H-MULTI | 3.128691 | HGB |
| rec | 2118 | lower_median / H-RECENT | 1.286119 | absolute_error_point / H-MULTI | 1.283874 | HGB |
| rec_yd | 2118 | lower_median / H-RECENT | 16.250236 | absolute_error_point / H-RECENT | 16.372991 | empirical |
| rush_rec_yd | 2118 | lower_median / H-RECENT | 20.389046 | absolute_error_point / H-MULTI | 20.125661 | HGB |
| nick-chart-ppr-v1 | — | blocked: exact component contract | — | blocked | — | unestablished |
| anytime_td | 2118 | event_probability / H-MULTI | 0.143755 | log_loss_probability / H-MULTI | 0.143144 | HGB |

Numeric targets use native-unit MAE, including fitted mean outputs when they win empirical MAE. The TD row uses Brier, never expected TD count. Different category units and populations cannot form a raw-error accuracy league. The CSV retains all ties within 1e-12; tied views are not additional learners.

## Intended means: separate MSE/RMSE product

These minima compare only empirical means with squared-error HGB means. A fitted mean label does not establish calibration. RMSE is in native units; MSE is in squared units. Neither is mixed into the displayed-point MAE ranking.

| Target | Empirical history | MSE | RMSE | HGB mean history | MSE | RMSE |
|---|---|---:|---:|---|---:|---:|
| pass_yd | H-RECENT | 7513.802455 | 86.682192 | H-MULTI | 7238.579423 | 85.079841 |
| pass_td | H-MULTI | 1.162517 | 1.078201 | H-MULTI | 1.205187 | 1.097810 |
| pass_cmp | H-RECENT | 55.680232 | 7.461919 | H-MULTI | 48.895351 | 6.992521 |
| pass_att | H-RECENT | 129.481237 | 11.378982 | H-MULTI | 117.049484 | 10.818941 |
| pass_int | H-MULTI | 0.548712 | 0.740751 | H-RECENT | 0.517752 | 0.719550 |
| rush_yd | H-RECENT | 609.887963 | 24.695910 | H-MULTI | 603.571220 | 24.567686 |
| rush_att | H-RECENT | 19.688715 | 4.437197 | H-MULTI | 18.231617 | 4.269850 |
| rec | H-RECENT | 3.237495 | 1.799304 | H-MULTI | 3.213584 | 1.792647 |
| rec_yd | H-RECENT | 589.509893 | 24.279825 | H-MULTI | 598.188577 | 24.457894 |
| rush_rec_yd | H-RECENT | 813.992245 | 28.530549 | H-MULTI | 818.036247 | 28.601333 |

No universal history regime is established. All products share older feature memory, H-CURRENT has startup fallback, and only seven current-season week clusters support uncertainty. These exposed minima need later selection-policy evaluation; legacy W1–6 CDF/provider scores are a different panel. Week 8 shadows are retained but unscored, and neither family is deployed. Chart rare components, richer role/defense/playcalling groups, authenticated offers and broad legacy adapters remain separate dependencies.
