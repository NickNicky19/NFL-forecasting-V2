# Retained HGB rushing-attempt collapse diagnosis — corrected role labels v2

The original absolute-loss HGB has a reproducible zero-start loss/split degeneracy on this nonnegative, zero-majority pooled training population. This v2 corrects the prior prose’s role-view terminology and preserves its original bytes. This diagnosis restores original artifacts; it is not a new accuracy experiment or a repaired forecast. No Week8 outcome was read. The original forecasts, labels, code and models remain unchanged.

At Week8 the three arms issued112 rushing-attempt predictions each, all for frozen-feed RB queries. The absolute-loss current arm gave111 zeros; recent and multi gave112 zeros. All336 absolute-loss values reproduce from the retained models and original feature snapshots. Raw predictions equal issued projected predictions: **zero cases changed under max(0,raw)**. The corresponding original squared-loss models gave no zeros.

| History | Train rows | Explicit zero targets | Zero fraction | QB/RB-only zero fraction | Absolute-loss issued zeros | Squared-loss issued zeros |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| H-CURRENT | 2,060 | 1,335 | 64.81% | 15.33% | 111/112 | 0/112 |
| H-RECENT | 8,018 | 5,071 | 63.25% | 16.18% | 112/112 | 0/112 |
| H-MULTI | 25,228 | 15,579 | 61.75% | 14.78% | 112/112 | 0/112 |

The broad zero fraction is an enabling condition for the zero intercept, not by itself proof that a strong conditional model must forecast zero for RBs. Original training admitted QB/RB/WR/TE; at the current origin these were211/526/870/453 rows. The526 RB training rows contain genuine supported count outcomes, and the prospective query population is112 RBs. The inherited registered primary rushing population is QB/RB; extended is WR/TE. The original JSON fields primary_RB and extended_QB_WR_TE were ad hoc RB/non-RB subgroup views, not those registered primary/extended labels. Their exact corrected mapping is retained in HGB_RUSH_ATT_ROLE_VIEW_CORRECTION_V2.json; the original bytes and numbers remain preserved. Removing WR/TE would change training specialization; it must be tested as a new procedure on the same queries rather than retroactively deleting difficult evaluation rows.

## Exact retained algorithm trace

All Week8 absolute-loss models have baseline0 and64 trees with two terminal leaves each. The same one-feature split repeats64 times in each model. Each large terminal leaf has value0; only the tiny extreme-history leaf becomes positive. Position one-hot features were available in the20-column inputs but were never consumed by a split in these three models. “Included as an input” therefore did not produce an actual position adjustment.

| History | Repeated split | Training rows in zero leaf / other leaf | First recorded split gain |
| --- | --- | ---: | ---: |
| H-CURRENT | mean3 > 21.8333 | 2,050 / 10 | 2045.048544 |
| H-RECENT | lag4_value > 29.5 | 8,008 / 10 | 8003.012472 |
| H-MULTI | lag2_value > 31.5 | 25,217 / 11 | 25212.765869 |

Independent installed-source review is retained in [HGB_ABSOLUTE_LOSS_SOURCE_REVIEW.json](HGB_ABSOLUTE_LOSS_SOURCE_REVIEW.json). sklearn1.8 absolute error uses gradient−1 at equality. Consequently **every initial training gradient is−1** for all three Week8 arms, including the zero targets. Histogram growth initializes the root node value to0. Its root gain comparison therefore uses root lossG·0=0, while child Newton values use−G/(H+λ). With H=n and λ=10, the candidate split gain becomes nL²/(nL+10)+nR²/(nR+10), favoring an extreme admissible partition rather than discovering a conditional target median from these constant gradients.

The formula reproduces the recorded gains: current2045.048544; recent8003.012472; multi25212.765869. After growth, absolute-loss leaf values are overwritten with0.05×median(y−raw), ignoring L2 in this median update. The large zero-majority leaf receives0. The untouched raw0 predictions there generate the same tied subgradient on the next iteration. This links the observed repeated extreme split, unused position inputs and zero-majority leaf output without inventing a new fitted result. The source-level mechanism and these retained artifacts jointly support the finding; it is not a general claim that L1 boosting always fails.

## Scope, chronology and actual inputs

Forty-eight original procedure/origin slots were inspected across Weeks1–8, three fit histories and two objectives:44 retained fitted models plus four explicit insufficient-training fallback slots. Training frames were not retained as a separate original artifact. They were reconstructed from the original digest-pinned sources and source policy; **all48 training-membership digests match their original receipts**. Independently reconstructed20-column query features match every original query-feature snapshot, including missing slots and availability. Retained-model predictions match every issued original query evaluated by the restoration. Details and all origin/role counts remain in [the aggregate JSON](HGB_RUSH_ATT_COLLAPSE_DIAGNOSIS.json) and [origin CSV](HGB_RUSH_ATT_ORIGIN_ROLE_SUMMARY.csv).

The consumed feature contract is target-specific means/counts over the last3/8 earlier-available roster/stat slots, four ordered target-value/age/missing groups, and QB/RB/WR/TE indicators. Missing roster/stat slots consume a position in the window. These models have no defense, team-carry total, teammate availability, routes, injury or market inputs. H-CURRENT restricts fitting seasons; its feature memory still starts2022. The seven-day availability assumption is retained; Week8current training contains93 current-season games under that assumption. This diagnosis does not establish the actual provider publication time or endorse that lag for live use.

## Empirical comparator equivalence

The original empirical and HGB captures have the same112 rushing-attempt query IDs and common source-file hashes. Their feature origins differ by1510.907930seconds: empirical22:51:31.887165Z versus HGB23:16:42.795095Z. No original game crosses kickoff+7days between those origins, so this assumption admits the same eligible game times. They do not consume equivalent learning inputs: the empirical control uses own-player/same-position RB histories, while HGB trains one nonlinear model on QB/RB/WR/TE with common older ordered feature memory. HGB fits once per weekly origin; its historical queries refresh features per game. Empirical summaries update at their registered query origin. These differences cannot all be attributed to training-history length.

Original empirical lower-median zeros were24/112 current,26/112 recent and24/112 multi; means had15/7/6 respectively. The exact contract and output-only comparison is in [HGB_EMPIRICAL_RUSH_ATT_INPUT_COMPARISON.json](HGB_EMPIRICAL_RUSH_ATT_INPUT_COMPARISON.json). These are forecast-shape diagnostics, not postgame accuracy results.

## Actionable next comparisons

1. Register a new QB/RB-only training specialization with exactly the same features, parameters, history windows and evaluation queries. Keep original all-role HGB and empirical controls. Label the mechanism as training-role specialization; preserve registered WR/TE extended evaluation and its coverage rather than quietly dropping it.
2. Test a separately named count-compatible Poisson-objective point learner against the original squared-mean and absolute-loss points. A Poisson fitting objective authenticates neither a Poisson forecast distribution nor a CDF.
3. Keep fit history separate from feature memory, including an explicitly named2026-only feature-memory policy and honest startup fallbacks. Historically selected parameters still limit any claim of pure current-season information.
4. Before any new capture, predeclare open-game eligibility and actual future issue/persistence clocks. The October30first kickoff has elapsed; a repaired model cannot recover its original issuance. No original method/model ID may be overwritten.

The first diagnostic serialization attempt encountered a NumPy scalar key; the second encountered an infinite retained-tree split threshold. Both failed output attempts are recorded separately, and their zero-byte outputs are preserved. The final JSON uses explicit Infinity strings for such thresholds rather than zero substitution. These were reporting failures, with zero fits, zero new forecasts and zero Week8labels. Private restored-query rows have a safe artifact hash in the aggregate report and require the approved private companion before operational admission.
