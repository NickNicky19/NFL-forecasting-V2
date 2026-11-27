# Executed HGB history controls and genuine Week 8 shadows

This new V2 source-matched reconstruction completed **all 504 registered
category/history/objective/origin cells**: **452 actual NFL fit calls, 452 retained
models, zero failed fits and 52 explicit insufficient-training fallback cells**.
It is a new version of an already studied HGB mechanism, not a claim that HGB
was previously untested. Old HGB losses, source contracts and attempts remain.

The run scored the same **15,574 frozen 2026 regular-season Weeks 1–7 query
cells**, representing **2,394 player-games across 107 games and seven weeks**.
It generated 86,262 reconstructed historical output views and 10,416 separately
captured Week 8 output views. Repeated objectives/histories are not independent
NFL observations. Chart PPR is explicitly blocked.

## What the history comparison says

On these identical current-season games, older fitting history usually improves
the full HGB system, but results depend on target and objective. Startup fallback
explains much of the difference. H-CURRENT still uses the same older permitted
feature memory as the other arms; this isolates **fit history**, not pure
current-season football information.

| Target/product | H-CURRENT | H-RECENT | H-MULTI | Supported primary rows |
|---|---:|---:|---:|---:|
| Passing yards, absolute-loss point MAE | 95.487849 | 70.068471 | 66.117313 | 242 |
| Passing TD, absolute-loss point MAE | 1.030744 | 0.864567 | 0.852635 | 242 |
| Completions, absolute-loss point MAE | 8.143887 | 5.646275 | 5.419172 | 242 |
| Attempts, absolute-loss point MAE | 11.929631 | 8.468885 | 8.027582 | 242 |
| Interceptions, absolute-loss point MAE | **0.594576** | 0.603306 | 0.603306 | 242 |
| Rushing yards, squared-loss point MAE | 20.479070 | **17.265655** | 17.330623 | 844 |
| Carries, squared-loss point MAE | 4.018971 | 3.140197 | **3.128691** | 844 |
| Receptions, absolute-loss point MAE | 1.472293 | 1.293913 | **1.283874** | 2,118 |
| Receiving yards, absolute-loss point MAE | 17.989620 | **16.372991** | 16.425673 | 2,118 |
| Combined yards, absolute-loss point MAE | 23.114385 | 20.221301 | **20.125661** | 2,118 |
| Anytime rushing/receiving TD, Brier | 0.159064 | 0.143198 | **0.143144** | 2,118 |

The table uses each category's observed stronger HGB point objective for
readability. It is **not a pre-2026 objective-selection policy**. Both objectives,
all histories, every week, extended roles, fallback contributions and adverse
results remain in `SCORES.csv`. Valid numeric mean-objective points also compete
on MAE; their MSE/RMSE diagnostics remain separate. No numeric forecast
distribution or offered-line probabilities were invented.

For passing yards, H-MULTI minus H-CURRENT MAE is −29.370536 yards over all 242
supported rows, but only −5.231099 over 130 rows where both procedures actually
used fitted HGB models. Carry mean-objective MAE improves by −0.890281 overall
and −0.207745 over 584 learned-only rows. Reception absolute-loss MAE improves
by −0.188419 overall and −0.032505 over 1,483 learned-only rows. These overlap
diagnostics preserve the full-system result rather than replacing it.

Seven week clusters are weak evidence. Descriptive week-balanced t intervals
for those MAE comparisons cross zero. They are post-fit reporting diagnostics,
unadjusted for repeated research/selection, not qualification certificates.
`ALL_NUMERIC_POINT_MAE_HISTORY_PAIRS.csv` covers every numeric point objective;
`PAIRED_HISTORY_AND_BASELINE.csv` additionally preserves mean-MSE and event-Brier
comparisons against the matched empirical controls.

## Wins and losses against strong simple controls

On the same H-MULTI rows, the absolute-loss passing-yard point lowers MAE by
5.213265 yards versus the empirical lower median. The reception absolute-loss
point lowers MAE by only 0.020658 catches. Anytime-TD HGB lowers Brier by
0.000611 versus the empirical event-frequency control. These are small or
mixed source-matched research comparisons, not wins against the current website.

The absolute-loss carry procedure is a material adverse result: its H-MULTI
model predicts **zero on all 847 planned primary rows**, with supported MAE
6.569905 versus empirical lower-median 3.283175. This poor procedure remains
retained. Its squared-loss counterpart has primary MAE 3.128691. The
absolute-loss rushing-yard procedure also loses its empirical lower median by
9.278715 yards. No failed objective was removed or silently refitted. A causal
explanation for the carry collapse would require a separately registered
ablation; this run does not attribute it merely to role composition.

Older fitting history does not universally win: the interception absolute-loss
point favors H-CURRENT, while its squared-loss mean and TD probability products
tell different stories. Rare-count point MAE is not a probability skill ranking.
Older seasons' row counts were not pooled into the current test population.

## Exact mechanism and chronology

The fixed library uses HGB absolute error and squared error for ten numeric
targets, and HGBClassifier log loss for the TD event. Parameters are 64
iterations, depth 3, minimum leaf 10, learning rate 0.05, L2 10, seed 1701,
maximum 31 leaves/255 bins, no early stopping and at most two native threads.
There was no tuning search, learned preprocessing or fitted categorical encoder.
Count points use a predeclared nonnegative projection; signed yards are retained.

Features are the same in all fit arms: earlier own-target mean/count over three
and eight slots, four ordered target-value/age/missing slots and fixed position
one-hot columns. Missing intervening rows consume slots. All feature memories
start in 2022; availability is the preserved kickoff-plus-seven-days assumption.
No team, injury, market, NGS, weather or target-game workload entered predictors.
Historical source revision/publication limits remain.

Each historical week fits once before that week's earliest kickoff, using only
labels whose assumed availability is strictly earlier. Query features refresh at
each game's kickoff left limit. Training-row features are computed at that
training row's own earlier kickoff. H-CURRENT fits 2026; H-RECENT fits 2025 plus
earlier 2026; H-MULTI fits 2022–2025 plus earlier 2026. Below 40 supported labels
or without two TD classes, the procedure uses the declared same-arm empirical
own/position fallback, then zero. It never hides an older prior inside startup.

The retrospective historical cohort uses observed statistical rows and row
position. It is not an authenticated historical ex-ante roster/offer cohort or a
full pure-current-information system. Primary rushing covers QB/RB; WR/TE
rushing remains separately reported as extended coverage. QB receiving,
combined-yard and TD extensions are also separate. These populations cannot be
silently equated with the older 2026 Weeks 1–6 laboratory panels.

## Genuine Week 8 capture

Week 8 was processed first. Its common actual feature origin was
**23:16:42.795095 UTC** on October 29. All 63 Week 8 model fits and output
persistence completed by **23:16:53.247869 UTC**, before every kickoff. The new
capture contains **10,386 issued views and 30 abstention views** over the original
1,951 frozen query cells/fourteen games. Six absent/ambiguous board contexts
remain abstentions, without fake prior predictions.

CAR–GB's **837 views** are explicitly after the existing 22:45 UTC owner input
deadline. Their shortest actual horizon is about **58 minutes 7 seconds**;
9,549 other views precede their later intended deadlines. These are genuine new
research shadows at their actual clocks, not T-minus-90 issuance, an official
shared capture or website publication. Existing empirical and producer forecasts
were unchanged. There are zero Week 8 outcome scores.

The Week 8 aggregate packet SHA256 is
`9c71eabb7fff13a5cceba6c43246343a10d7f77a3b62184f4ac090959f5a8d67`.
Models, input features and predictions are retained privately with immutable
per-cell hashes and clocks. Off-host upload/restoration is separately attested
by the root executor; local output alone is not a durability claim.

## Verification, resources and resumability

The protocol froze at **23:16:16.219846 UTC**. Six leakage/software fixtures,
including three fictional estimator fits, passed before the first NFL fit.
Execution finished **23:17:32.884884 UTC**: 50.131 wall seconds, 80.762 CPU seconds,
409,804,800 bytes peak RSS and two-thread maximum. The 452 actual NFL fit calls
are distinct from those three fictional fits and from 96,678 forecast views.

Post-run checks covered 966 fit-label/feature cutoff assertions, 82,320 historical
query-feature cutoffs and 4,699 fallback cutoff assertions. Independent reviewer
checks remain separately identified. The frozen v1 source SHA256 remains
`13ad5627152d4aed81540f93088b63716acb98a00bce52089a8ec8cbb619cccf`.

The reviewer identified an operational guard omission: v1 declared but did not
actively enforce the two-million output-row cap; its private counter also omits
the preexisting frozen-query file. Actual output was independently counted as
96,678 views and total retained bytes remain far below 512 MiB. Results are not
invalidated by a hypothetical overrun. A separately versioned future guard
module, four passing fixtures and an application-checked prepared patch preserve
v1 and require no NFL rerun. See `RESOURCE_GUARD_FOLLOWUP.json`.

Portable archive-member names in receipts are scientific labels, not private
filesystem, Drive or object-store locators. `PUBLIC_ARTIFACT_ID_SEMANTICS.json`
also maps their bytes to public-safe `ART-HGB-SHA256` identities. Remote storage
locations and raw player/model records remain private.

The complete grid, failures, score tables and per-cell fit/forecast receipts are
retained. There are no remaining cells in this bounded HGB wave. This does not
complete every legacy history grid, all five methods per category, chart PPR,
market/ROI analysis or production admission. Any later improvement, corrected
resource version or new feature hypothesis needs its own identity and allocation;
do not rerun the completed fits merely to refresh a report.
