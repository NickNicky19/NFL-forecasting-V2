# Exact observed D1/D2 older-season executor — code checkpoint

The missing chronological execution integration is implemented and tested with synthetic rows and spy models. **No NFL fit, model prediction, new forecast, new scientific score or older-season backtest ran in this checkpoint.** All 736 exact older D1/D2 season/category/history/output cells remain unclosed. The accepted I results and index are unchanged.

The new [executor](../../nfl_v2/defense_season_executor.py), [CLI](../../tools/run_defense_seasons.py) and [tests](../../tests/test_defense_season_executor.py) reuse the exact existing own20-feature, observed-position-group D1/D2 augmentation, law priors, Leaf-CDF model and native scorer. The old 2026 runner and source helpers are unchanged. This is an execution adapter, not another forecasting family or a reconstruction of original issuance.

| Check | Result |
|---|---|
| New synthetic executor tests | 15 passed |
| Existing season/preflight tests reused | 7 passed |
| Test command | `python -m unittest tests.test_defense_season_executor tests.test_defense_season_preflight -v` |
| Actual NFL fit/predict/apply calls | 0 |
| New scientific forecast/score rows | 0 |
| Default CLI | Metadata-only preflight; no NFL rows/model construction |
| Actual execution admission | Not granted; restoration, input review, reserved output capacity and separate root worker release remain mandatory |

The 22 checks cover all18 weeks with spy models, Week1 startup, strict availability equality exclusion, historical training features at each training game's own cutoff, target/future-outcome mutation invariance, exact24/29-column D1/D2 inputs, four observed group slots, missing target groups, no pre2022/future-year source, duplicate/missing queries, baseline fingerprint mismatches, fake restoration receipts, immutable outputs, failed persistence and public error sanitization. Software fixtures add no NFL observations. [Exact-code receipt](SOFTWARE_CHECKS.json) and [code protocol](FROZEN_PROTOCOL.json) bind this scope.

The observed window stays **four observed qualified opponent/position groups**. An absent position group creates no slot. A present group with an unknown target occupies a slot and contributes explicit incompleteness. This adapter does not implement or relabel the separate four-scheduled-team-game alternative. Qualified player-population totals are not complete official team allowed totals or causal defensive strength.

At every weekly origin, training labels must be available strictly before the earliest scheduled game. A training row's features are evaluated at that row's own kickoff. Query features are evaluated at each target game's kickoff. Source files are restricted to2022 through the evaluation year; common feature memory starts in2022, while strict memory, training, priors and transforms start in the evaluation year. Historical availability remains the inherited kickoff-plus-seven-days assumption applied to current-vintage reconstructed source bytes, not authenticated historical publication.

| Evaluation year | CURRENT fit floor | RECENT fit floor | MULTI fit floor | Strict feature floor |
|---|---:|---:|---:|---:|
| 2022 | 2022 | 2022 proxy only | 2022 | 2022 |
| 2023 | 2023 | 2022 | 2022 | 2023 |
| 2024 | 2024 | 2023 | 2022 | 2024 |
| 2025 | 2025 | 2024 | 2022 | 2025 |

**2022 RECENT here is the legacy source-limited expanding-from2022 proxy. It is not the exact2021-plus2022 prior-year arm.** The separately qualified2021 extension, its retention/admission and54 chart dependencies remain outside this code version. Equivalent source/feature floors share a computational model while retaining separate policy labels. Logical cells and aliases are not extra model fits.

Week1 CURRENT includes its fixed no-NFL startup law: numeric point mass0, anytime-TD Bernoulli.5. Later insufficient-training, all-zero count, single-class and failed-fit states retain the unchanged same-arm role/global prior and declared fallback tags. Cold player histories retain fallback rows. All full-system rows remain; the existing Meter also emits own-learned-only views. Further common-learned/subgroup/paired analysis can reuse the retained forecasts through existing analysis tools; no alternative metrics engine is introduced.

## How execution becomes eligible

`python tools/run_defense_seasons.py --season 2025` is safe now: it prints a metadata plan. It does not release a model worker. The remaining stages are deliberately separate:

1. Complete the existing approved recovery plan, including fresh full download/reassembly and inner-file hashes. An account-capacity statement or a fabricated PASS object does not satisfy the hardcoded reviewed restoration validator.
2. Build a compact baseline metadata map with the `baseline` action after a separate source-bound metadata-worker release. This uses the retained frozen seasonal queries, exact source/helper bytes and a root-pinned index of existing Leaf FIT receipts. It never calls a model. New own-feature fingerprints are labelled **reconstructed metadata**, and every available retained membership/count/cutoff/prior fact must match. It saves compact fingerprints, not another full feature archive.
3. Use `prepare` with a metadata-only input contract binding evaluation year, all18 weeks, exact12 targets, observed window, source hashes, old seasonal protocol hash, frozen query hash, baseline map hash and finite budgets. No NFL row values are read by `prepare`.
4. Obtain independent review of the actual source/query/baseline map and the exact code, plus a root sole-worker release binding that review, the factual restoration receipt and this software receipt. Reserve at least the full private-output budget. `execute` has no permissive boolean override.
5. Run one bounded admitted wave, retain model/query/training/forecast packets with hash readback, then independently verify and register any new scores before ranking them. A reconstruction receives a real new run identity and execution/persistence clocks. No current or historical issuance is backdated.

The baseline adapter was checked against real public FIT receipt schemas: the retained ordinary Leaf receipts contain method, target, policy, sample count, membership hash, cutoff, feature floor, position counts and prior parameters. There are864 such receipts in each2022/2024/2025 original run and864 in the completed2023 replay; the incomplete original2023 run has768 and is not a complete map. The receipts do not contain original full own-training feature matrices. Their absence does not prohibit a new reconstruction: new source/code-bound fingerprints are supported without refitting a baseline. Retained query-feature packets can alternatively be used where qualified. No original feature capture is invented.

The metadata release binds `source_protocol_sha256`, `frozen_queries_sha256`, `retained_fit_index_sha256`, factual restoration hash, exact helper hashes and finite wall/RSS/private-byte limits. The separate fit release binds the frozen execution protocol, baseline map, independent review, exact software receipt, restoration, real reconstruction/sole-worker IDs, fit ceiling and reserved private bytes. A root-pinned fit index maps each `Www-target-policy` key to a safe relative receipt member and hash. No storage locator belongs in the public contract.

The original [I finite readiness plan](../point-prop-diagnostic-20261031i/d1d2-season-execution-readiness/README.md) remains the historical record. Its observed-window ceiling is6,912 logical origins across2022–25 and5,184 computational origins under the legacy2022 proxy. These are planning ceilings, not completed fits or a true2022 RECENT comparison. The pilot budget must be chosen from the retained measured cost and newly reserved capacity; this checkpoint executes no pilot.

The genuine external recovery/input-admission requirements remain. Missing bookmaker lines, original selections or prices **do not block this football-only numerical comparison**. No owner scheduler, capture, collector, production selection or release changes are made.
