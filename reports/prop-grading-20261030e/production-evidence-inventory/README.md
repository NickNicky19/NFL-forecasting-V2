# Production selection and grading evidence inventory

The first supported original-selection panel is the retained **2026 Week 7, thirteen-game slice**: 285 recorded numeric-stat leans, including 279 qualified outcomes and six appearance-unknown cases. Its original selections produced **183 wins, 96 losses, no statistical pushes: 65.59% of 279 decided cases**. Over was 85–49 on 135 selected cases, with one unresolved; Under was 98–47 on 150 selected cases, with five unresolved. These different pools do not establish a universal better side. [Every category and actual side](../actual-side-projection-v2/README.md), [first scorecard](../first-scorecard-v1/SCORES.json), [independent projection review](../ACTUAL_SIDE_K_COHORT_INDEPENDENT_REVIEW.json).

The full source feed contains 1,419 ordinary-stat rows for those games: 462 provider-labelled finite thresholds (441 DraftKings-labelled and 21 Sleeper-labelled), plus 957 site-generated thresholds. The 285 original selections are 20.08% of that full feed and 61.69% of the provider-labelled threshold pool. These are distinct denominators. The four controls were evaluated on the same conditional 285-case panel. Neither denominator is an authenticated priced-offer universe; no probabilities, prices, ROI or bookmaker settlement were established.

## Exact inspected scope

Read-only production inspection pins main to [`1ec93e068a91abd51c990937d1019e4a831694b4`](https://github.com/NickNicky19/nicks-expert-nfl-picks/tree/1ec93e068a91abd51c990937d1019e4a831694b4), committed October 30 at 18:33:05 UTC. The two additional inspected trees are pre-phase-1 `210e34329d6e5b42b4e8f1af768b63db75ec10c5` and pre-phase-2 `3149663447b29f95f06c7259b84da3bd4a21cab0`. All three recursive tree responses were untruncated: 1,162, 74 and 99 entries. This is a bounded reachable-source inspection, not a census of private sessions, deleted history or every branch.

Twenty-one individual files at that main pin and the original `pull/build.py` at `c8120e3cb26a908b8d5a99329b0f28ae49473ea1` were retained outside Git. Each retained source byte sequence independently matches its expected Git blob SHA-1, in addition to its SHA-256. One transport-added trailing newline was removed only where the resulting bytes exactly matched the Git blob. Public manifests contain hashes and public repository paths; source payloads and player-level rows remain private. [Source manifest CSV](SOURCE_FILE_MANIFEST.csv), [JSON](SOURCE_FILE_MANIFEST.json), [scope and counts](INVENTORY.json).

| Located evidence | Seasons/weeks | Scope and qualification |
|---|---|---|
| Forward capture gzip versions | 2026 W6: 338; W7: 93 | File versions, not independent games or issued predictions; only the qualified W7 panel above has been graded in this wave. |
| Classic capture versions | 2026 W7: 2; W8: 7 | W8 listing metadata only; no W8 outcome payload read. |
| Mutable forecast archives | 2026 W4–W8 | W4–W7 source archives inspected; W8 archive unopened. These cannot by themselves authenticate original issuance. |
| Past-week website files | 2026 W1–W7 | Code identifies these as finished-week statistics and closing lines, not original selected forecasts. |
| Grading-history bodies | 4 files | Metadata only; current track record and grading-history payloads not decoded. |
| New weekly selected-ranking graph | 22 bodies/receipts | Active forecast-only body inspected at the pinned main; distinct from old R0 history. |

No 2025 original-selection archive was located within these three inspected trees. That is a scope limitation, not proof that such evidence never existed. Repeated versions, side views, controls and season aliases add no independent NFL observations.

## What the recorded line and side mean

The original producer prefers a DraftKings-labelled ESPN threshold, then a Sleeper Picks threshold, and otherwise keeps a generated half-point threshold. It records a lean only when adjusted point minus threshold exceeds the category's fixed margin in either direction. Top flags add separate eligibility and ranking filters: two earlier games, injury availability, supported last-four-game snap share, projected fantasy-point eligibility, a category minimum line, a projection/line range and a standardized forecast gap. Snap share is not route participation. These original Top flags are distinct from all recorded leans and from V2's newly registered K subsets.

[`books.py`](https://github.com/NickNicky19/nicks-expert-nfl-picks/blob/1ec93e068a91abd51c990937d1019e4a831694b4/pull/books.py#L48) retains ESPN open/current **target lines**, not player-prop cash prices. Its primary athlete-ID bridge has a normalized-name/team fallback; independent exact identity qualification remains necessary. The [Sleeper adapter](https://github.com/NickNicky19/nicks-expert-nfl-picks/blob/1ec93e068a91abd51c990937d1019e4a831694b4/pull/books.py#L145) retains one threshold and side payout multipliers, without the complete side-specific quote clock, jurisdiction or settlement contract. A retained Sleeper observation may have a different threshold from the preferred DraftKings line. It cannot be attached to that other line as a price or used to de-vig it.

The exact [original producer](https://github.com/NickNicky19/nicks-expert-nfl-picks/blob/c8120e3cb26a908b8d5a99329b0f28ae49473ea1/pull/build.py#L201) rounds provider projection and adjusted projection to two decimals **before** retention. Consequently, the available control is `SAVED_POINT_DIRECTION_RETAINED_PRECISION`, with no additional V2 rounding. Strict internal unrounded P1 is unavailable; lost precision is not reconstructed.

The W7 source has an internal recorded capture of October 22 at 17:55:30 UTC and a generated clock of 17:55:26. The qualified independent server-bound evidence establishes retention **by October 23 at 17:49:53 UTC**. It does not authenticate the earlier internal clock or provider-input vintage. The admitted thirteen-game subset excludes the earlier game. See the [source registration](../evidence-inventory/FROZEN_PANEL_PROTOCOL.json) and [join protocol](../evidence-inventory/panel-join-v1/FROZEN_JOIN_PROTOCOL.json).

## Grading and source-contract findings

Production [`grade.py`](https://github.com/NickNicky19/nicks-expert-nfl-picks/blob/1ec93e068a91abd51c990937d1019e4a831694b4/pull/grade.py#L18) explicitly uses statistical grading, version `statistical-v3-identity-20261025`. It separates hit, miss, equality push, DNP and unresolved; the hit denominator is wins plus losses. DNP needs explicit attributed evidence; absent participation stays unknown. Statistical equality does not establish a venue refund, and a known DNP does not establish a book void rule.

Three practical qualifications matter:

- Started legacy archive entries missing `line_from` can acquire a closing line through [`assemble` and `apply_book`](https://github.com/NickNicky19/nicks-expert-nfl-picks/blob/1ec93e068a91abd51c990937d1019e4a831694b4/pull/build.py#L380), which can also recalculate a lean. A mutable archive after that repair is insufficient to prove the original pregame selection. V2 uses the separately retained forward packet.
- After positive participation proof, production's legacy [`stat_value`](https://github.com/NickNicky19/nicks-expert-nfl-picks/blob/1ec93e068a91abd51c990937d1019e4a831694b4/pull/scoring.py#L79) interprets omitted fields as zero. That requires a verified complete compact-source contract. Participation alone does not prove every omitted target is zero. This is a code-traceable contract gap, not a finding that every current live row is wrong. V2 used its qualified explicit-label join and preserved six unknown appearances.
- Website `fpts` uses its original scoring contract, including fumbles lost at −2 and additional special-team/recovery/blocked-kick awards. It differs from Nick's chart contract. Neither website fantasy points nor its threshold can stand in for chart-PPR. Anytime TD also needs its own event-offer/selection contract; both remain unavailable in this numeric panel.

[`compare_lines.py`](https://github.com/NickNicky19/nicks-expert-nfl-picks/blob/1ec93e068a91abd51c990937d1019e4a831694b4/tools/compare_lines.py#L1) is a retrospective average/matchup-versus-closing-line procedure and expressly warns that historical provider projections can be revised. It does not authenticate original saved provider forecasts. No collection script was run. [All findings, evidence lines and owner actions](CONTRACT_FINDINGS.csv).

## Current source graph and next supported panel

At the inspected main pin, the newer forecast-only selected-ranking body `fd85f83d43d59b17707c987717fa18476cfecf786d0ba7d4f00568ca08c64949` is prepared October 30 at 18:33:04.741011 UTC for W8: 12 Over entries and 12 Under entries, comprising 21 selected forecasts and three explicitly labelled current-baseline fallbacks. No actuals or grading fields were present in that inspected body. Documentation requires source-row identity, content hashes, actual publication/readback clocks and preservation of started-game selections; it explicitly separates the old R0 Record stream. This read checks repository evidence, not the currently served website or later settlement.

The first bounded scorecard has now been executed and independently checked, rather than left as a proposal. The next supported historical expansion is a metadata-only qualification of individual W6/W7 retained capture versions and their server-bound clocks, frozen side/line identities and explicit-label coverage before any additional grading. W4–W6 mutable archives or historical closing lines alone do not qualify an original selection. Genuine future evaluation belongs to retained owner-controlled capture and later qualified final labels; V2 has not published or modified that stream.

Reconstructed top-player/workload memberships were assembled after the games; their ranking cutoff is also later than the internal recorded capture clock. They are diagnostic cohorts, not authentic original star lists. Newly registered K6/10/20 lists rank saved point–line gaps within each category and the original 285-case panel; they are exposed retrospective subsets, not original issued K selections or a live selection policy.

## Read-only storage diagnosis

The connected Drive profile matches the approved companion folder's single owner permission. The supported profile and normalized metadata actions expose no account quota measurement. A `files.get` request for `storageQuota` returned a 400 invalid-field response; it was not an upload or capacity retry. No quota, usage or available-byte amount can be inferred from those tools. This identity match does not override the separately observed provider `storageQuotaExceeded` rejection or admit any blocked fitting wave. [Public-safe diagnostic](DRIVE_READ_ONLY_DIAGNOSTIC.json).

There were zero production writes, workflow dispatches, collector calls, new model fits, new forecasts, upload retries or current W8 outcome reads in this inventory. It establishes evidence availability and contract limits; release and production fixes remain with the retained owner.
