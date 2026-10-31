# D1/D2: executed opponent-information comparison

Website improvement remains unestablished. A separate [server-retained R0 reference](../server-retained-R0-v1/RUN_RECEIPT.json) wins eight of ten numeric categories on its matched 13-game Week 7 panel; passing-yard MAE is 58.18724 versus 72.39038 for the fixed V2 reference there. Those bytes were retained by October 23 at 17:49:53 UTC, before the later games’ T-minus-90 deadlines. This does **not** establish the internal October 22 capture time, provider input vintage, or current website procedure. Its smaller panel does not replace the full 2026 Weeks 1–7 benchmark below, but the adverse practical comparison must remain visible.

The historical wave completed all 672 registered cells: 556 new fits/retained models and 116 explicit no-fit fallbacks. It reused the same 17,968 query identities across 107 games in 2026 Weeks 1–7 and generated 268,336 retained prediction views, summarized by 3,216 canonical score views. Original controls were not refitted. The run took 309.97 wall / 368.67 CPU seconds, two threads and 1,883,930,624 bytes peak RSS, within the registered budget.

D1 adds four prior opponent-position qualified-population raw-total/coverage inputs. D2 keeps D1 and adds five matched-exposure shrunk-rate/deviation/support/age inputs. The original 20 own-history/position features, 32-tree learner, fit origins, training members, exact priors and cold-start route stayed fixed. Adding features changes feature competition and random split behavior even under a fixed seed; this is a versioned information ablation, not a causal defensive-talent estimate or a new model family.

## Native point results

Numeric errors are MAE; TD probabilities use Brier. Each row selects the best observed D1/D2 history/product after exposure to 2026, and compares with the strongest preceding family representative. This is descriptive research selection, not an earlier-frozen next-week routing policy. Positive change is worse. All policies/products, extended populations, weeks, learned overlap, failures/fallbacks and adverse results remain in the canonical score artifact.

| Target | n | Candidate group / policy / product | Error | Same-policy ordered control | Previous strongest | Change vs previous strongest |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| anytime_td | 2118 | D1 / H-MULTI-COMMON / event_probability | 0.144642 | 0.144737 | 0.143144 | +0.001498 |
| nick-chart-ppr-v1 | 2359 | D2 / H-MULTI-COMMON / lower_median | 4.490360 | 4.502391 | 4.496515 | -0.006155 |
| pass_att | 242 | D2 / H-MULTI-COMMON / lower_median | 7.971074 | 8.004132 | 8.004132 | -0.033058 |
| pass_cmp | 242 | D1 / H-MULTI-COMMON / lower_median | 5.342975 | 5.454545 | 5.419172 | -0.076197 |
| pass_int | 242 | D1 / H-CURRENT-COMMON / lower_median | 0.595041 | 0.611570 | 0.566116 | +0.028926 |
| pass_td | 242 | D1 / H-MULTI-COMMON / lower_median | 0.809917 | 0.830579 | 0.822314 | -0.012397 |
| pass_yd | 242 | D2 / H-MULTI-COMMON / lower_median | 66.855372 | 66.772727 | 66.117313 | +0.738059 |
| rec | 2118 | D2 / H-MULTI-COMMON / lower_median | 1.245515 | 1.254958 | 1.245515 | +0.000000 |
| rec_yd | 2118 | D2 / H-MULTI-COMMON / lower_median | 16.189330 | 16.198772 | 16.198772 | -0.009443 |
| rush_att | 844 | D1 / H-MULTI-COMMON / lower_median | 3.058057 | 3.059242 | 3.059242 | -0.001185 |
| rush_rec_yd | 2118 | D1 / H-MULTI-COMMON / lower_median | 20.236072 | 20.213881 | 20.125661 | +0.110411 |
| rush_yd | 844 | D1 / H-MULTI-COMMON / lower_median | 16.688389 | 16.750000 | 16.750000 | -0.061611 |

## Proper distributions and genuine means

CRPS is the predeclared proper law score for numeric targets, with PMF negative log loss, interval width/coverage and zero mass retained. TD uses Brier. These law/mean rows are views of fitted procedures, not additional learners. Count points from a Poisson fitting objective elsewhere are not assigned a PMF here.

| Target | Best law group/policy | Law metric | Law error | Previous strongest | Change | Intended-mean MSE change vs previous strongest |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| anytime_td | D1 / H-MULTI-COMMON | brier | 0.144642 | 0.143905 | +0.000738 | — |
| nick-chart-ppr-v1 | D1 / H-MULTI-COMMON | CRPS | 3.178365 | 3.181649 | -0.003284 | +0.223980 |
| pass_att | D2 / H-MULTI-COMMON | CRPS | 5.859598 | 5.854494 | +0.005104 | +0.185241 |
| pass_cmp | D1 / H-MULTI-COMMON | CRPS | 3.898686 | 3.940321 | -0.041635 | +1.847765 |
| pass_int | D1 / H-MULTI-COMMON | CRPS | 0.370776 | 0.366766 | +0.004011 | +0.004482 |
| pass_td | D2 / H-RECENT-COMMON | CRPS | 0.593387 | 0.585096 | +0.008291 | +0.036924 |
| pass_yd | D2 / H-MULTI-COMMON | CRPS | 47.273627 | 47.490447 | -0.216821 | -29.214523 |
| rec | D1 / H-MULTI-COMMON | CRPS | 0.890269 | 0.890788 | -0.000519 | +0.044326 |
| rec_yd | D1 / H-MULTI-COMMON | CRPS | 11.601290 | 11.593831 | +0.007459 | +3.578274 |
| rush_att | D2 / H-MULTI-COMMON | CRPS | 2.160427 | 2.161969 | -0.001542 | +0.282443 |
| rush_rec_yd | D1 / H-MULTI-COMMON | CRPS | 14.344216 | 14.356796 | -0.012580 | +3.052108 |
| rush_yd | D2 / H-MULTI-COMMON | CRPS | 11.824689 | 11.876423 | -0.051734 | -4.685578 |

Numeric startup laws can have impossible events and genuinely infinite log loss. Canonical NLLnull with positiveinfinite_NLLcount means INFINITE, never zero loss or successful missing evidence. Chart laws retain signed 0.02 support; median1/5/10point tolerances use exact integer coordinates. Genuine means are unrounded and ranked separately byMSE/RMSE. The 35 unknown current chart labels remain in forecast coverage.

Defense summaries describe qualified observed-position rows, not complete official team totals. Missing target/appearance/exposure rows keep relevant group observations incomplete and consume the four-game window. A nonnull shrunk rate can be the earlier league prior alone when local support is absent; local exposure/game counts are explicit inputs and audits. Same-history feature memory is fixed across the three fitting-window arms; STRICTrestricts own/opponent/league information to 2026 but retains historically chosen architecture and retrospective query eligibility.

Every primary canonical comparison pairs the exact same supported queries with the original same-policy ordered control and retains absolute/relative changes, game-cluster sensitivity and weekly differences. Seven exposed week clusters do not meet the registered eight-week interval threshold; sensitivity intervals do not correct selection or multiplicity. Strongest-reference uncertainty cannot be manufactured from aggregate errors.

[Point minima ](OBSERVED_POINT_MINIMA.csv) · [Proper-law minima ](OBSERVED_PROPER_LAW_MINIMA.csv) · [Genuine means ](OBSERVED_GENUINE_MEAN_MINIMA.csv) · [All full-policy comparisons ](CATEGORY_COMPARISON.json) · [Canonical scores ](SCORES.json) · [Historical receipt ](HISTORICAL_RUN_RECEIPT.json) · [Protocol ](FROZEN_PROTOCOL.json) · [Prior art/pathway gaps ](PRIOR_ART_AND_PATHWAY_GAPS.md)

Future Week 8 results remain unscored; any new shadow capture is separately recorded with actual issuance/persistence clocks, original 00:27 fit membership, new fixed query-information asof and all 2229 query cells across 13 remaining games. Production/owner integration remains unchanged.

The [window-definition finding](WINDOW_DEFINITION_FINDING.md) qualifies the recipe: “four games” means four observed qualified-position groups in the frozen code, not every calendar team game. Six absent TE groups create 77 historical query-window differences under common memory. No source, forecast, model or score is overwritten; calendar-padding performance remains untested.
