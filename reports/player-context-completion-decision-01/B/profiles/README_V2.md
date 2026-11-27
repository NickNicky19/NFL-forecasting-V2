# Reusable as-of QB profiles

**941 of 941 declared historical QB queries now have profiles: 664 in full 2025 and 277 in 2026 Weeks 1–8.** Twenty-six profiles have no own-player history and retain the declared role-prior fallback. None were discarded. These are reusable descriptions and existing component replays, not 941 new NFL tests or issued recommendations.

[Machine index](PROFILE_INDEX_V1.json) binds every profile to canonical player/event/team/opponent, cutoff, source hash and immutable week chunk. [Schema](PROFILE_SCHEMA_V1.json), [current guard amendment](PROFILE_CURRENT_QUERY_GUARD_AMENDMENT_V3.json), [execution receipt](PROFILE_EXECUTION_RECEIPT_V1.json), [parity receipt](PROFILE_PARITY_RECEIPT_V1.json) and [deterministic examples](DETERMINISTIC_EXAMPLES_V1.json) identify the checked scope.

The historical query universe is the **retained official QB-stat-row reconstruction**. It is not an authenticated historical pregame roster. Profiles use only earlier admitted observations; their target-game outcomes and participation are not read. The separate current-query adapter accepts an explicitly supplied universe and requires canonical identity/team/role assertions, source ID/SHA and retention clock at or before the cutoff. No genuine current query universe was supplied here. Current capture, consumer admission and served use are all unestablished.

## What is usable

| Section | Quantity and support | Actually consumed by |
|---|---|---|
| Attempt exposure | Last-eight own official pass-attempt totals, prior-season/earlier-current league moments and the existing gamma-Poisson law | Existing `COMMON_EXPOSURE`; all 941 means match retained outputs exactly |
| Down/depth mix | 25 exhaustive down/depth counts divided by own attempts, with earlier league shrinkage and support | Existing E1/E2/E3 and conditional completion models |
| Completion conversion | Completions per context attempt, raw and shrunk, with zero/undefined states | Existing direct and conditional completion models |
| Field summaries | Earlier throw-weighted distance, field position, clock and score means, each with its observed denominator | Existing E1/E2/E3; these do not forecast future game script |
| Opponent response | Distinct context residuals versus the earlier offense reference, plus own-mix interactions | Existing E2/E3; no pure defensive-talent claim |
| Depth charting | FTN catchable/drop/contested counts with separate known denominators; raw, pooled and own-shrunk catchability, ages and no-known flags | New C1/D1 use the exact frozen `DepthHistory.support`; C2/D2 additionally use logit of its shrunk catchability. Drop/contested are descriptive here |
| Pass destination | Earlier left/middle/right/UNKNOWN thrown-ball destination fractions | Descriptive; no receiver-alignment claim |

All 941 attached depth descriptions match the new mechanism's exact `DepthHistory.describe` output, including its five support fields per depth. The explicit `pooled_known_zero` marker means **no known annotations**, not a measured zero catchability rate. A positive known denominator and zero positives is separately labeled `KNOWN_ZERO`.

## Missing or incomplete mechanisms

| Field | Disposition and exact dependency |
|---|---|
| QB-stint/dropback opportunity | Not in the accepted retained game-input schema; needs a separately qualified transformation of sacks/scrambles/designed dropbacks and stint membership |
| Starter/limited/replacement probabilities | Not estimated; supplied QB role/team does not establish these probabilities |
| Future down/distance/clock/game-script law | Not modeled by these historical summaries; the frozen model integrates its declared predicted attempt and down/depth mixture only |
| QB-to-receiver choice | Existing known/unknown receiver support is not a receiver-choice or route model; C owns the qualified receiving export |
| Alignment/all routes/separation | No such fields invented. C owns source qualification; destination is not alignment, and snaps are not routes |
| Authentic historical observation clocks | Unavailable; current/revised sources retain the strict kickoff-plus-seven-day reconstruction and expanding earlier-2022 feature memory |

The empirical-Bayes intervals describe the declared pseudo-count estimates, conditional on shared priors. They do not establish predictive coverage, independent NFL trials or full parameter uncertainty.

## Deterministic examples

Examples were selected by prior support, not target outcomes or comparative scores.

| Case | Identity and as-of evidence | Result |
|---|---|---|
| Ordinary | `2025_01_ARI_NO / 00-0035228`, eight prior games, latest own source January 12, 2025 | 289 past attempts; frozen exposure mean 33.00753; source age 237.816 days at the query |
| Sparse | `2025_01_MIN_CHI / 00-0039923`, no own eligible games | Profile retained; role-prior exposure mean 26.77259; own raw context rates remain undefined |
| Known zero | Ordinary profile's fourth-down/20+ cell | Zero completions from two attempts is raw zero; shrunk completion estimate 0.21756 remains separately labeled |
| Missing chart source | Ordinary identity passed without a depth mapping | Charting is `UNAVAILABLE_SOURCE`; aggregate flags are not substituted |
| Missing current membership | Ordinary identity passed through the current-universe interface without evidence | Explicit `UNAVAILABLE_PROFILE`, rather than infer membership from its eventual stat row |

The 23,525 profile-context cells include 1,036 known-zero conversion rates and 10,638 undefined zero-denominator rates. These are repeated derived cells, not additional games or observations.

## Execution and reuse

The profile build used 16.70 CPU seconds, 16.71 wall seconds and 246 MB peak RSS, with no fits, score calculations, raw-feed downloads or private offer transfer. The prior profile/forecast parity checks were reused; raw reconstruction and representative fits were not repeated.

`nfl_v2.qb_context_profiles.QBProfileAdapter` is the reusable interface. Call `build_many` with explicit queries and the correct universe label. Duplicate identities fail. Invalid current identity/source/clock evidence returns an unavailable-profile record. Target outcomes are unnecessary and ignored. Three meaningful adapter tests pass; [the software amendment](PROFILE_SOFTWARE_AMENDMENT_V2.json) preserves the earlier two-test bytes and identifies the added chart-zero boundary check.

The build script refuses to overwrite frozen profile output. Reproduction should use a clean output version; reading or rendering the existing profiles is not a reason to regenerate them.

## Current-query guard closure

Two synthetic boundary checks found and corrected handling gaps in the newly written, unadmitted adapter: explicit null membership evidence raised an exception, and a nonfinite cutoff could leak into an unavailable record as nonstandard JSON. Both now produce strict-JSON unavailable records with exact reasons. The earlier source/test bytes and counterexamples remain in the versioned receipts. All 941 frozen historical profiles are available historical-universe records with null query evidence; neither corrected branch was traversed. No model, saved forecast, grade or historical profile byte changed, and no production use was found. These fixtures are not NFL accuracy observations.

## Attribution and retention

nflverse/nflfastR PBP/player-stat-derived sections are CC BY 4.0. FTN Data via nflverse charting-derived sections are CC BY-SA 4.0; retain that attribution/share-alike condition when reusing the combined profile. No raw feed, restricted offer, private locator or protected A model is included. Existing exact-raw recovery limitations remain separate from these retained derived profiles. A profile alone qualifies no primary forecast, probability, EV, Top Picks policy or production release.
