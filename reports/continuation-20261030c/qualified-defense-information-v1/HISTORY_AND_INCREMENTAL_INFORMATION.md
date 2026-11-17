# Same-row history and incremental rate information

The group/product below is fixed at its already reported overall point minimum. Each history contrast holds the supported 2026 Weeks 1–7 queries fixed. Common feature memory uses earlier 2022+ records while fitting windows change. Negative multi-minus-current values favor older fitting. Numeric targets use MAE; anytime TD uses Brier. These exposed diagnostic choices are not a later-validated selection rule.

| Target / group | Full paired n | Multi−current error | Core common-learned n | Multi−current learned error | D2−D1 full error, multi |
| --- | ---: | ---: | ---: | ---: | ---: |
| anytime_td / D1 | 2118 | -0.019089 | 1456 | -0.002198 | +0.000007 |
| nick-chart-ppr-v1 / D2 | 2359 | -0.670386 | 1617 | -0.078763 | -0.004002 |
| pass_att / D2 | 242 | -5.582645 | 127 | -0.094488 | -0.033058 |
| pass_cmp / D1 | 242 | -3.508264 | 127 | -0.212598 | +0.070248 |
| pass_int / D1 | 242 | +0.012397 | 127 | +0.023622 | -0.004132 |
| pass_td / D1 | 242 | -0.165289 | 127 | -0.031496 | +0.028926 |
| pass_yd / D2 | 242 | -24.983471 | 127 | -3.779528 | -0.260331 |
| rec / D2 | 2118 | -0.190746 | 1456 | -0.045330 | -0.000944 |
| rec_yd / D2 | 2118 | -1.679887 | 1456 | -0.368819 | -0.010387 |
| rush_att / D1 | 844 | -0.887441 | 576 | -0.222222 | +0.005924 |
| rush_rec_yd / D1 | 2118 | -2.813503 | 1456 | -0.353709 | +0.003305 |
| rush_yd / D1 | 844 | -3.184834 | 576 | -0.746528 | +0.016588 |

Older fitting improves these selected point views for 11 of 12 targets, both overall and on the shared learned-only intersection; interceptions reverses. Startup and fallback explain part of the larger overall advantage. Passing-yard MAE improves 24.9835 yards overall and 3.7795 yards on 127 common learned rows. Those are different explicitly named populations. Averages over different evaluation seasons do not answer this 2026 question.

The core learned mask intersects current, recent and multiseason fitting. [All 544 history contrasts](HISTORY_PAIRED.csv) retain recent−current, multi−recent and strict−common-current views. Strict changes the complete information policy, with 2026-only own-player, opponent and league inputs and priors. It is separate from the isolated fitting-window effect. [The 272 fallback decompositions](FALLBACK_DECOMPOSITION.csv) preserve loss sums and their contributions to overall error.

The additional rate group is not uniformly helpful: at multiseason fitting it improves six selected point targets and worsens six. It improves passing-yard MAE 0.2603 relative to D1, but both lose to the strongest preceding point reference. It worsens rushing-attempt MAE 0.0059. [The 528 paired information contrasts](INFORMATION_GROUP_PAIRED.csv) keep native points, genuine-mean MSE and proper-law CRPS separate. These are comparison sidecars, not additional models or univariate rankings.

Comparisons preserve game-cluster sensitivity and weekly differences. Seven exposed weeks leave the registered week interval unavailable. No Week 8 outcomes, routing rule, offers, prices or production changes enter this analysis. The source-window review separately qualifies observed-position groups versus calendar team games.
