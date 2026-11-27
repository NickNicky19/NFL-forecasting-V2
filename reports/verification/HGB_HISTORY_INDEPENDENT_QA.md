# Independent HGB history and shadow review

**PASS for retained-row arithmetic, source-prefix reconstruction, fitted-model replay and the stated fit-history comparison.** The reviewer performed **zero refits**, generated no replacement forecasts and read no actual Week 8 labels. This review does not establish historical source vintages, a pure-current-information experiment or production readiness.

The [independent audit](check_hgb_control.py) and [receipt](HGB_HISTORY_INDEPENDENT_QA.json) bind the frozen code, protocol, six source files, query membership, training frames, retained models and forecast packets. The reviewed code SHA-256 is `13ad5627152d4aed81540f93088b63716acb98a00bce52089a8ec8cbb619cccf`.

## Verification scope

- **504 registered fit opportunities:** 452 actual fitted models, all retained, 52 explicit insufficient-training fallback cells and zero failed fits. Only digest-verified self-produced pickles were loaded, for inference; the reviewer never called `fit`.
- **17,525 query-target cells:** 15,574 historical and 1,951 future. Separate raw CSV calculations checked 368,025 feature values/availability conditions and 3,024 training-frame facts.
- **96,678 retained output views:** 87,652 fitted-model inference replays, independently reconstructed fallback cells and 290,034 forecast bindings.
- **930 historical summaries:** 15,060 metric/count checks; largest absolute metric difference **1.82e-12**. The [per-view game census](HGB_VIEW_GAME_COUNTS.json) binds the protocol, run receipt and all 504 forecast-packet receipts. Subsets receive their actual game counts.

Training labels satisfy `source kickoff + 7 days < weekly fit origin`; each training row's features use its own earlier kickoff cutoff. Historical query features refresh before each game, while model fitting occurs once before the week's earliest kickoff. All arms use identical historical query identities. No target-game outcome enters those feature prefixes. This verifies the assumed availability policy, not the actual historical publication clocks or revisions.

The fixed budget allowed 504 fits, zero searches and two threads. Reported use was 50.13 seconds wall time, 80.76 CPU seconds and 409,804,800 peak RSS bytes. The frozen loop **does not enforce its declared `max_forecast_rows=2,000,000`**. Its actual 96,678 outputs are below that limit. Preserve this code version and add an explicit guard under a new version before reuse; the gap does not alter the retained numerical results.

## Roles, zeros and history meaning

Passing models train on qualified QB rows. Rushing models train on the union of primary **QB/RB** and separately reported extended **WR/TE** roles. Receiving, combined-yard and TD models train on primary **RB/WR/TE** plus extended **QB** rows. The role rules are identical across history arms. Verified participants' explicit zero outcomes remain source values; absent/unverified participants are not filled with zeros.

The primary rushing evaluation contains **844 QB/RB outcomes** and excludes WR/TE structural zeros. Broad zero-heavy training roles can still influence a pooled objective, making specialization a useful later test. They do not justify deleting an observed loss.

**H-CURRENT is current-season fitting with common older feature memory starting in 2022, not strict current-season football information.** H-RECENT fits eligible 2025–2026 labels; H-MULTI fits eligible 2022–2026 labels. Common feature memory supports a fit-window comparison within this registered policy. Startup fallbacks and both-fitted comparisons remain separately visible.

The historical population uses current-vintage observed-stat rows, retrospective positions and physical-activity proof. It is not an ex-ante starter/offer population. QB backup appearances and valid zero production remain included. Publication timing and revisions are unverified beyond the seven-day assumption. The feature set contains prior-target means/counts, ordered values/age/missingness and position indicators; no qualified routes/snaps, injury, market, defensive-personnel or playcalling additions. Exact chart PPR remains blocked.

## Measured wins and losses

The [independent paired results](HGB_PAIRED_COMPARISONS.json) retain 63 primary HGB-versus-empirical views and 42 within-HGB history contrasts on identical 2026 Weeks 1–7 identities. Numeric products below use MAE; TD uses Brier. Negative differences favor HGB.

| H-RECENT product | n | HGB error | Same-arm empirical error | Difference |
|---|---:|---:|---:|---:|
| Passing yards, absolute-loss point | 242 | 70.068471 | 73.933884 | −3.865413 |
| Passing yards, squared-loss mean | 242 | 70.393338 | 69.185345 | +1.207993 |
| Receptions, absolute-loss point | 2,118 | 1.293913 | 1.286119 | +0.007794 |
| Rushing attempts, absolute-loss point | 844 | 6.529621 | 3.188389 | +3.341232 |
| Rushing attempts, squared-loss mean | 844 | 3.140197 | 3.201420 | −0.061223 |
| Anytime rushing/receiving TD probability | 2,118 | 0.143198272 | 0.146980070 | −0.003781797 |

The absolute-loss carry model's zero-heavy/all-zero fitted predictions replay correctly. Its adverse MAE is a retained **negative result**, not a scoring failure. Broad zero-heavy training roles and the regularized objective deserve a registered follow-up. A fitted absolute-loss point need not beat an empirical median.

Fallback composition matters: the squared-loss carry procedure's full-system −0.061223 improvement becomes **+0.028766** on 798 learned/own-history overlap rows. For receptions the corresponding full-system −0.013175 becomes **+0.016662** on 1,995 overlap rows. Both views are retained.

Within HGB passing-yard absolute-loss forecasts, H-MULTI minus H-CURRENT changes full-system MAE by **−29.370536** on 242 outcomes and **−5.231099** on 130 both-fitted rows. For interception absolute-loss forecasts the full-system older-history difference instead is **+0.008730**. TD Brier changes by **−0.015919779** on 2,118 outcomes and **−0.004094736** on 1,483 both-fitted rows. Older history does not win every product. These exposed-game comparisons do not supply an untouched selection evaluation or significance guarantee.

Redacted TD row `c605f06d9a6392b9` independently gives HGB/empirical Brier **0.008123364 / 0.095537190**; row `26d0c36784679a06` gives **0.550819515 / 0.308641975**. Better aggregate H-RECENT TD Brier coexists with 857 row wins and 1,261 losses; row-win frequency is not probability accuracy. HGB versus empirical also changes representation/update policy, so this cross-family comparison is not a pure learner ablation.

## Week 8 retention and release limits

The HGB packet retains **10,386 issued views plus 30 abstentions**, covering 1,951 frozen queries and 14 games. Feature origin is **2026-10-29T23:16:42.795095Z**; persistence completed **23:16:53.247869Z**, before all scheduled kickoffs. **837 CAR/GB views are later than the owner's 22:45 input cutoff** and remain tagged late; 9,549 precede their owner input cutoffs. These are new research shadows, not earlier forecasts, official captures or website output.

Compressed Week 8 SHA-256 is `9c71eabb7fff13a5cceba6c43246343a10d7f77a3b62184f4ac090959f5a8d67`. A fresh downloaded private archive independently hashes to `6e9f23cf62a1e025f65ae90211899239890a035283e944a8d8d909aa6d21d1bd`, matching the [restoration receipt](../continuation-20261029/hgb-history-v1/PRIVATE_RESTORATION.json); its 1,046 members retain models, features and prediction chunks. The executor separately checked owner-only permission; this reviewer does not claim ACL access.

No Week 8 error was calculated. Absolute/squared-loss outputs are separate point objectives, not numeric probability laws; binary HGB probabilities are uncalibrated. The separate [HGB future-grader review](HGB_FUTURE_GRADER_REVIEW.md) passes 42 invented checks and the actual capture with empty labels only. Eventual qualified labels and actual grading remain pending. Historical wins and local future retention do not authorize production integration.
