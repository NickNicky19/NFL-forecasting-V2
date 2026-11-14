# Three-week probability baseline and selected-side checkpoint

**Beating GLM did not establish useful probability skill.** On the same W5–7 H-MULTI offered-event masks, Leaf/C02 improve Brier over GLM in nine of ten categories, yet beat the neutral reference only for passing touchdowns and interceptions. They beat the chronological same-position prevalence reference in seven categories; passing attempts, completions and interceptions lose. The initial W1–7 numerical championship is unchanged.

| Category | Matched n / outer offers | Neutral Brier | Earlier prevalence | Leaf | C02 | GLM |
|---|---:|---:|---:|---:|---:|---:|
| pass_att | 80/84 | 0.250000 | 0.252687 | 0.255654 | 0.264041 | 0.339025 |
| pass_cmp | 80/84 | 0.250000 | 0.271825 | 0.277308 | 0.283779 | 0.344505 |
| pass_int | 80/84 | 0.250000 | 0.245527 | 0.246365 | 0.247754 | 0.244508 |
| pass_td | 80/84 | 0.250000 | 0.254341 | 0.241014 | 0.236405 | 0.247977 |
| pass_yd | 80/84 | 0.250000 | 0.289479 | 0.284047 | 0.287048 | 0.324697 |
| rec | 470/511 | 0.250000 | 0.283200 | 0.256239 | 0.256320 | 0.271457 |
| rec_yd | 470/512 | 0.250000 | 0.277238 | 0.260382 | 0.259900 | 0.272813 |
| rush_att | 114/125 | 0.250000 | 0.313316 | 0.279259 | 0.276392 | 0.400144 |
| rush_rec_yd | 113/124 | 0.250000 | 0.302428 | 0.275972 | 0.276614 | 0.304700 |
| rush_yd | 226/244 | 0.250000 | 0.278784 | 0.259429 | 0.260502 | 0.284860 |

The expanded passing-attempt panel is 80/84 outer offers: Leaf Brier 0.255654, C02 0.264041 and GLM 0.339025 versus neutral 0.250000 and prior prevalence 0.252687. Interceptions reverses against prior prevalence: Leaf 0.246365 and C02 0.247754 lose to 0.245527, despite both beating neutral. Passing touchdowns improves against both references: C02 0.236405 and Leaf 0.241014 versus neutral 0.250000 and prior prevalence 0.254341.

Weekly changes remain visible: in W5, Leaf/C02 beat neutral for attempts and interceptions, while passing touchdowns loses; in W6–7, touchdowns and interceptions beat neutral while attempts loses. These are already exposed observations. Three weeks do not support the registered whole-week bootstrap. Paired game-cluster sensitivity intervals are descriptive and unadjusted for multiplicity/selection; point estimates are not permanent superiority claims.

The complete [probability table](PRIMARY_PROBABILITY_TABLE.csv) retains CURRENT, RECENT, MULTI and strict-current candidates. CURRENT fitting with older feature memory is distinct from strict-current information. B1 uses exactly earlier same-position football outcomes with kickoff+7d strictly before the actual decision clock; CURRENT/strict uses2026 only, RECENT2025–26, MULTI2022–26. Empty prefixes explicitly use neutral; no old fallback is hidden. This reference has population limitations for offered stars and changed roles. FULL/LEARNED/PRIOR scores and common-learned law comparisons remain separate; no small prior-only case is promoted as a full-population winner.

B0 is a threshold-local Over=.5/Under=.5/Push=0 reference, not a global CDF or authenticated market. Brier is .25 on decisive outcomes and .75 on pushes; true zero-mass log losses remain infinite. Per-region calibration diagrams and decisive-outcome AUC are separate diagnostics, not fitted calibration. All probabilities condition on modeled appearance; bookmaker nonvoid/settlement and prices remain unverified.

## Selected-side continuity example

The following uses the same registered C02 H-MULTI lower-median P1 recipe. It compares the prior W6–7 period with W5–7; different calendar coverage is explicit. It does not claim a controlled learner improvement or retrospectively choose a winner.

| Category | W6–7 combined wins/decided | W5–7 predicted Over wins/decided | W5–7 predicted Under wins/decided | W5–7 combined wins/decided |
|---|---:|---:|---:|---:|
| pass_att | 27/52 | 5/6 | 40/74 | 45/80 |
| pass_cmp | 21/52 | 10/19 | 25/61 | 35/80 |
| pass_int | 24/52 | 0/2 | 42/78 | 42/80 |
| pass_td | 32/52 | 11/17 | 39/63 | 50/80 |
| pass_yd | 17/52 | 13/29 | 16/51 | 29/80 |
| rec | 181/315 | 73/121 | 191/349 | 264/470 |
| rec_yd | 172/314 | 64/130 | 184/340 | 248/470 |
| rush_att | 37/76 | 14/25 | 44/89 | 58/114 |
| rush_rec_yd | 41/75 | 9/16 | 55/97 | 64/113 |
| rush_yd | 79/147 | 27/59 | 94/167 | 121/226 |

[Every primary P1 method/strategy with Over, Under and Combined](PRIMARY_P1_WIDE_TABLE.csv) retains exact counts, abstentions, unavailable forecasts and unresolved states. Combined rates use summed decided counts. [Raw own-pool side maxima](RAW_PRIMARY_P1_SIDE_MAXIMA.csv) retain every tied observed maximum, including small or low-coverage pools, without a posthoc minimum-support veto. They are separate from the common-mask probability comparison and an earlier-executable selector. No top-player and top-pick cohorts are mixed here; existing weekly cohort/K products remain under their original identities.

P1 fallback counts remain null in this count-only cumulative projection: the parent fallback_issued field counts the admitted pool, not selected-side fallback. Distinct players also remain null because players repeat across weeks. Native initial W1–7 scores, all weekly forecasts/grades and original website wins/losses are preserved. Overlapping matched-control-mask variants and the fixed-Friday W7 panel are excluded from this cumulative method sum.

[Canonical aggregate scores](SCORES.json) · [All paired B0/B1 and common-law contrasts](PAIRED_COMPARISONS.csv) · [Whole-offer coverage](MASK_AND_OUTER_COVERAGE.csv) · [Frozen source/code contract](FROZEN_PROTOCOL.json) · [Execution receipt](RUN_RECEIPT.json). This final wave reuses cached loss vectors and original weekly counts only: zero model fits, inference, probability regeneration, source grading, captures or new NFL observations. Production is unchanged.
