# Frozen conditional QB packet: first qualified forward grades

The packet issued **November 13, 2026 at 00:09:55.109350 UTC** (November 12,
6:09:55 p.m. America/Chicago) now has qualified final numerical outcomes for
**three appearing QBs in one game**. Six arm-specific forecasts are scored;
these are three player-games, not six independent NFL observations.

| Exact forecast output | Scored player-games | MAE | MSE | Bias | Count-law NLL | Count-law CRPS |
|---|---:|---:|---:|---:|---:|---:|
| B0 unchanged reference mean | 3 | 8.585768 | 82.663787 | −0.421555 | 2.663761 | 4.818846 |
| B2 FTN-augmented mean | 3 | 8.689825 | 83.254548 | −0.665061 | 2.643458 | 4.821153 |
| B0 lower median | 3 | 8.666667 | 92.000000 | +0.666667 | Same B0 law | Same B0 law |
| B2 lower median | 3 | 8.666667 | 86.000000 | 0.000000 | Same B2 law | Same B2 law |

B2 mean absolute error is **0.104057 higher** than its own B0 reference on
these three cases. NLL improves by 0.020302 while CRPS worsens by 0.002307.
This one-game result does not establish general superiority, equivalence,
calibration, or a release candidate. No information block was refitted or
selected using these outcomes. The completed historical negative finding
remains unchanged.

## Appearance, observed zero and unavailable records

| Frozen query | Final qualified evidence | Treatment |
|---|---|---|
| Jayden Daniels, WAS | 23 completions / 33 attempts; explicit game appearance | Score both frozen conditional forecasts |
| J.J. McCarthy, NYG | 23 completions / 36 attempts; explicit game appearance | Score both frozen conditional forecasts |
| Jameis Winston, NYG | Explicit 0 completions / 0 attempts in both sources; 2 credited rushing attempts; explicit game appearance | Score both forecasts at observed zero |
| Marcus Mariota, WAS | Exact ESPN game/team/athlete roster explicitly says `didNotPlay=true`; no weekly statistical record | Preserve both issued forecasts as nonappearance; actual remains null, not zero |
| Jaxson Dart, NYG | Original packet withheld both outputs under its source-listed IR state; final source row absent | Preserve two unavailable outputs; actual appearance/statistic remains unknown, not inferred DNP or zero |

The original packet contains ten query/product records: eight issued
conditional forecasts and two IR-unavailable records. Of the eight issued
forecasts, six have qualified numerical grades and two are explicit DNP.
No issued forecast has unresolved appearance in this final-source check.
The unavailable IR query has unknown actual appearance; it is not an
unresolved scored prediction. Postgame ESPN `active=false` is not used as
pregame health evidence or as an appearance filter.

Winston's zero is important: physical appearance is different from a starting
or passing role. The source explicitly supplies zero completions and attempts,
with actual rushing participation. The zero was **not** inferred from mere
participation, absence of a passing row, or another component statistic.
He remains in the conditional panel even though his large numerical error is
unfavorable. No eventual-starter filter is applied retrospectively.

## Source, forecast and grading clocks

The exact event is `401873052` / `2026_10_WAS_NYG`, scheduled November 13 at
01:15 UTC. Current final ESPN event status is `STATUS_FINAL`, `post`,
`completed=true`. Fresh nflverse weekly 2026 counts and exact ESPN
competition/team/athlete passing statistics agree for all three scored QBs.
The canonical GSIS-to-ESPN bridge reuses the already retained October 29
identity snapshot; names are not used as fuzzy join keys. Both teams,
opponents, season, week, credited counts and game identifiers are checked.

These are current final-source observations obtained November 14. They are
valid later grading evidence; they do not authenticate earlier FTN publication
vintages, source-update times, starter status or historical quoted lines.
NFLverse and ESPN are separate corroborating provider interfaces; independent
upstream statistical lineage is not claimed. Direct league gamebooks were
not fetched.

The frozen native source was generated November 12 at 21:45:01 UTC and
received at 23:59:28.439603 UTC. Forecasts were actually issued at
00:09:55.109350 and durably persisted at 00:09:55.118115 UTC. Exact GitHub
capture readback was completed at 00:11:30.591191 UTC, before kickoff.
The original packet expired for recommendation use at kickoff, but remains
valid for later conditional numerical grading. Its hash is unchanged:

`f9889584338bf7b85f5de3889fbc78f73fee97e2052faea7cc91a28fb203c7bb`

The original packet's mixture/prior law field is supplemented by its already
bound, output-preserving complete empirical-law capsule. Neither its points,
probability law, features, query membership nor issue clock is changed by
this grading package. Historical training features retain the declared
current-vintage seven-day reconstruction; that history-admission policy is
not a requirement to wait seven days before grading a qualified final outcome.

## What this adds, and what it does not

- **Adds:** one genuinely subsequent numerical season-week, three appearing
  player-games / one NFL game, six arm-specific numerical grades, and two
  explicit issued-DNP records. Four canonical score views preserve mean and
  lower-median identity. Their NLL/CRPS fields refer to two shared count laws,
  not four independent probability models.
- **Does not add:** actual-line selections, Over/Under wins, a Top Picks
  board, an offered-line tested week, venue settlement or calibrated
  confidence. `Over`, `Under` and `Combined` records are **N/A**, because the
  original packet had no exact offer or selected side. Later lines are not
  attached to manufacture original picks.
- **Does not qualify:** a new primary numerical, probability, direction or
  ranking product. This exact current-query/late-horizon packet has one
  numerical forward week and one game cluster. No inferential superiority
  interval is reported. The count laws' wide 90% intervals contain all three
  observations; this is interval coverage on three cases, not 90% prop accuracy.
- **Does not change:** C's common admission, original website deployment,
  source/producer permissions, model ownership, selectors or jobs. Status
  remains **LOCAL_NOT_C_ADMITTED**; the historical mean-direction recipe
  remains closed for no useful gain.

## Verification and reproduction

[Source and grading receipt](SOURCE_AND_GRADING_RECEIPT_V1.json) binds source
URLs, successful-response hashes, observations, the original packet and law
capsule, exact scorer/law code, all states and the finite acquisition budget.
[Derived labels](DERIVED_LABELS_V1.json) contain qualified nflverse statistical
derivatives; [graded forecasts](GRADED_FORECASTS_V1.json) preserve all ten
frozen query/product states; [SCORES.json](SCORES.json) has four canonical
views for root's existing result-index registration.

Each scored probability law is checked separately against direct empirical
mass plus geometric-tail calculations. Mean, actual mass, log score and
CRPS agree; discrete CRPS uses a finite CDF sum and its exact unbounded
geometric tail. Numeric errors use the existing `nfl_v2.scoring` contract.
No fit, new forecast, source collector, scheduler or ranking function runs.

Acquisition was bounded to **15 HTTP attempts: 12 successful responses,
3 HTTP 404 responses, 5,030,611 successful-response bytes**. The 404s for
missing Mariota statistics / Dart game records remain documented; none is
turned into an observed zero. Raw provider responses remain in the approved
owner-local cache and are not published. The one attempted grading adapter
failed before any score write because it compared two equivalent ISO8601
clock strings literally. The corrected adapter compares their timezone-aware
instants. [Development receipt](OFFLINE_GRADING_DEVELOPMENT_V1.json) and the
[original failed adapter](ORIGINAL_FAILED_ADAPTER_SOURCE_V1.py.gz) preserve
that verifier-only failure; no source, model or prediction changed.

Reproduce using the owner-provided bound cache and stable identity snapshot,
with a new empty output directory:

```sh
python reports/wave-closure-next-comparison-20261114/B/forward-grading/grade_frozen_packet_v1.py \
  --cache OWNER_LOCAL_BOUND_FINAL_SOURCE_CACHE \
  --identity OWNER_LOCAL_RETAINED_STABLE_IDENTITY_SNAPSHOT \
  --out NEW_EMPTY_OUTPUT_DIRECTORY
```

Reproduction has real new execution clocks; original issue/source/persistence
clocks remain bound and unmodified. No raw-cache export or private locator is
required in the public package.

FTN-dependent forecasts/laws/scores: **CC-BY-SA-4.0, FTN Data via nflverse**.
Qualified nflverse weekly statistical derivatives: **CC-BY-4.0**. Raw ESPN
responses are retained owner-locally; public evidence is limited to source
hashes/URLs, narrow derived checks and aggregate conclusions.
