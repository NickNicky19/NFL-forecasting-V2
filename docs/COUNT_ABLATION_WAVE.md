# New HGB count ablations

Status: **executed after root authorization and the preceding fit worker completed**. All224cells completed at2026-10-30T00:35:53.932971Z, with188fits/retained models and36explicit no-fit fallback cells. See [results and limitations](../reports/continuation-20261030/count-ablation-wave-v1/RESULTS.md). This code does not acquire sources, inspect Week8 outcomes, schedule jobs or modify old models, predictions, production or registries.

The original rushing-attempt L1 failure is documented in [the retained-artifact diagnosis with corrected role labels](../reports/continuation-20261030/HGB_RUSH_ATT_COLLAPSE_DIAGNOSIS_V2.md). This wave creates two new procedure families:

- `v2-hgb-rush-att-qb-rb-specialization-v1`: absolute-loss rushing-attempt HGB, changing training eligibility to QB/RB while preserving the original20features, loss,64iterations and other settings. All original primary QB/RB and extended WR/TE evaluation queries remain; a change to training does not delete evaluation cases. The conditional forecast is an absolute-loss point, without a fitted distribution/median-law claim.
- `v2-hgb-poisson-count-point-reconstruction-v1`: Poisson-objective HGB intended-mean points for passing TDs, completions, attempts, interceptions, rushing attempts and receptions. Original per-category primary+extended training roles remain. This implements a new corrected-count-point pathway, not authentication or reproduction of old CountA issuance. A Poisson fitting objective supplies **no CDF, PMF, quantile or log-score product** in this adapter.

Each has three fit windows with common2022-start feature memory and a separate current-fit/2026-only feature-memory policy. Strict memory also restricts fallback outcomes to2026. No older outcome, fitted football prior, player encoding or calibration enters that policy. Fixed architecture and settings inherited from exposed research, current-vintage identities, and the retrospective observed-participant historical cohort remain disclosed; this is not a claim of pristine current-only provenance. Procedure identities distinguish common and strict memory; they remain variants of the same family.

The frozen protocol is [FROZEN_PROTOCOL.json](../reports/continuation-20261030/count-ablation-wave-v1/FROZEN_PROTOCOL.json), registered2026-10-30T00:32:44.619473Z. There are224fit opportunities:32QB/RB-L1 and192Poisson-count cells across seven historical weeks and the separately captured future partial week. The5756historical count-query subset comes directly from the original15574query document. The621future count queries are a fixed subset of the preceding wave's1795open-T90queries/13games. The156queries from the already closed CAR–GB game remain excluded in the shared source document, never backfilled under this run.

Future labels and features use the **same supplied asof2026-10-30T00:27:36.688096Z** as the preceding wave. Actual fitting, inference, issuance and persistence occur later and retain their actual clocks. These are partial-week pre-T90 research shadows, not an exactT90 snapshot or a recreation of the old14game capture. The new asof crosses the original kickoff+7day availability boundary for one Week7game versus the old HGB23:16origin. Comparisons against the old capture therefore change available history as well as procedure; the protocol names the crossed game and retains source hashes. Compare new families against controls restored at the same new asof when isolating a learner change.

Only explicit supported targets from positive-physical-event stat rows enter labels. Missing values stay missing; signed production and support checks retain inherited contracts. Historical cohorts are current-vintage retrospective observed stat-row diagnostics, not the full ex-ante player population. Learned fits occur before each week's earliest kickoff, while historical features refresh at each query's kickoff left-limit. The original seven-day source-availability assumption remains unverified publication timing. No target-game outcome, actual future exposure or new injury/market information enters.

The same-position own-player empirical summary is the first fallback, followed by same-position pooled history and literal zero. L1 uses a lower empirical median fallback; Poisson uses an empirical mean fallback. Empty/current-season startup remains explicit. Original known identity blocks stay abstentions. Blocked or unknown-position rows are excluded before the estimator's inference call and before any fallback lookup. Every frozen query remains represented in issued/abstained coverage. All-zero count training creates an explicit no-fit Poisson fallback, not a failed optimizer or an invented probability law.

Bounds are224fit calls,1200wall seconds,1800CPU seconds,1GiBprocess peak memory,two threads,512MiBprivate bytes and2millionoutput rows. The actual planned output is35492rows. Output reservations occur before fitting; byte checks occur before writes; fit calls are charged before fitting; all original/failure versions are preserved. No hyperparameter search occurs. When a bound or persistence deadline stops a run, the remaining grid stays explicitly unrun rather than silently complete. Root must still coordinate the sole worker; a command-line flag is an assertion of that completed coordination, not an operating-system-wide lock.

Software checks, without fitting any model:

```sh
python -m unittest tests.test_count_ablations -v
python tools/run_count_ablations.py check \
  --public-root reports/continuation-20261030/count-ablation-wave-v1
```

The check command writes an immutable exact-code `SOFTWARE_CHECKS.json`; do not repeat it into an existing path. Nine fixture functions cover training specialization with retained extended queries, strict cutoffs and fit windows, strict feature memory, unchanged estimator settings/objectives without fitting, blocked-row inference exclusion,224cell/output arithmetic, fit/byte/output guards, missing/zero/native-metric coverage, strict/common index identities and shared-asof preparation.

After the previous fit worker has actually finished, root can execute once:

```sh
python tools/run_count_ablations.py run \
  --source-root RESTORED_PINNED_SOURCE_DIRECTORY \
  --public-root reports/continuation-20261030/count-ablation-wave-v1 \
  --private-root RESTORED_NEW_PRIVATE_ABLATION_DIRECTORY \
  --sole-worker-confirmed
```

The original HGB helper files remain unchanged. Run outputs include canonical aggregate `SCORES.json`, CSV, every fit/prediction receipt, grid states, failures and a run receipt. Models, input features, original prediction chunks and pending future shadows stay private. Separate primary/extended, per-week, position and learned-only views preserve family, objective, fit history, information policy, fallback and native errors. Multiple views do not multiply independent NFL games. Root registers new canonical scores and rebuilds the result index, obtains approved private-store upload/readback receipts, and asks the independent verifier to recompute representative rows before making any scientific or operational improvement claim.
