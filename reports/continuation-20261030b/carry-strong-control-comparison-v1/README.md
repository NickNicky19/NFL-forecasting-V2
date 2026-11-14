# Carry improvements against strong matched controls

This independently replays the same2026Weeks1–7query/actual identities:844supported primaryQB/RB outcomes and1516disjoint WR/TE outcomes. All2394original opportunities remain, including34missing labels. No model was fitted, no future forecast was produced and no Week8outcome was read.

| Retained method / H-MULTI | Primary n | Primary MAE | WR/TE n | WR/TE MAE |
| --- | ---: | ---: | ---: | ---: |
| collapsed_l1 | 844 | 6.569905 | 1516 | 0.098945 |
| prior_best_mean | 844 | 3.128691 | 1516 | 0.291669 |
| primary_role_l1 | 844 | 3.091618 | 1516 | 0.619436 |
| ordered_cdf_median | 844 | 3.059242 | 1516 | 0.101583 |
| empirical_median | 844 | 3.283175 | 1516 | 0.114116 |

The primary-roleL1repair improves MAE by0.037073(1.185%)against the strongest prior HGB intended-mean control3.128691, with a game-cluster sensitivity range for candidate-minus-control of[-0.084497,+0.010352]. The much larger reduction against collapsedL1is not the relevant strongest-control gain. OrderedCDFmedian3.059242improves by0.069449(2.220%)versus the prior mean and by0.032376(1.047%)versus the repair. The latter sensitivity range also crosses zero. These exposed results are not a future routing policy.

WR/TE losses remain visible: repairedL1MAE0.619436is worse than the prior intended mean0.291669, orderedCDF0.101583and collapsed/empirical median0.098945. A near-zero median can be an appropriate rare-count point without establishing expected carries or a probability law. Native MAE comparisons preserve functional identities; intended-meanMSEand probability/distribution quality remain separate products.

The empiricalMULTImedian is included as a declared matching-history control, not falsely labeled the best empirical setting. The previously observed empiricalRECENTmean reference3.201420is retained separately in the earlier category summary. The selected strongest prior HGBmean3.128691already beats both.

## Learned cases and fallback coverage

| Method | Own learned primary n | Own learned MAE | All-five common learned n | Common learned MAE | Scored fallback n |
| --- | ---: | ---: | ---: | ---: | ---: |
| collapsed_l1 | 844 | 6.569905 | 809 | 6.711990 | 0 |
| prior_best_mean | 844 | 3.128691 | 809 | 3.128384 | 0 |
| primary_role_l1 | 844 | 3.091618 | 809 | 3.091733 | 0 |
| ordered_cdf_median | 811 | 3.038224 | 809 | 3.040791 | 33 |
| empirical_median | 809 | 3.250927 | 809 | 3.250927 | 35 |

Own-learned subsets differ by procedure and must not be compared as if they were paired. The all-five intersection uses identical supported query IDs. Empty fallback views retain n0/null errors, never zero MAE. [SCORES.json](SCORES.json) preserves all40full/own/common/fallback views; [PAIRED_CONTRASTS.csv](PAIRED_CONTRASTS.csv) preserves30same-row contrasts with wins/losses/ties, signed and relative differences, per-week changes and game-cluster sensitivity.

Only seven exposed weeks are available, so the registered eight-week interval is not estimated. Game-cluster sensitivity is descriptive, not a selection- or multiplicity-adjusted significance claim. The [comparison annotation projection](COMPARISON_ANNOTATIONS.json) binds all40source record IDs to strongest-prior-mean paired comparisons or an explicit empty-view reason. Negative relative_error_deltafavors the candidate; original relative_mae_improvementhas the opposite sign and is named accordingly. Original canonical scores were not rewritten.

Exact source/receipt/prediction hashes, formula/config identities and private retained comparison rows are bound in [RUN_RECEIPT.json](RUN_RECEIPT.json). The independent verifier separately checked71820original-source join fields and890score/contrast checks. This is a current-vintage retrospective participant diagnostic, not authentic historical ex-ante population recovery, untouched confirmation, deployed website performance or priced wagering evidence.
