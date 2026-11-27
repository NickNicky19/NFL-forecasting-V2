# Independent empirical-history diagnostic review

**PASS for the retained diagnostic rows and stated retrospective cohort.**
Older training improves several simple-control results on identical 2026 rows;
the effect is not universal. These results do not identify the full tournament's
best method or an operationally ready replacement.

The reviewer did not rerun the benchmark, construct a competing forecast run,
fit a learner, or acquire additional NFL outcomes. Its
[independent audit script](check_empirical_diagnostic.py) reads retained rows,
reconstructs raw-source labels and selected earlier-history prefixes, and uses
separately written Decimal arithmetic. Counts/hashes and results are in
[EMPIRICAL_HISTORY_DIAGNOSTIC_REVIEW.json](EMPIRICAL_HISTORY_DIAGNOSTIC_REVIEW.json).

## What passed

- Six frozen source-file hashes and the 940,812-row prediction-gzip hash match
  the registration/receipt. Every retained row's cutoff matches an independently
  parsed Eastern-time schedule kickoff. All **940,812** stored latest-training
  availability clocks are strictly earlier than the query cutoff when present.
- All **86,262 retained 2026 forecast views** were checked against independently
  reconstructed source actuals, participation, historical position, category
  cohort, week and kickoff. Blank values stay missing; values are not taken from
  the earlier zero-trimmed production cache.
- **258 deterministic query samples** cover categories, weeks, positions and
  available fallback types. Independent raw prefix scans check own-history,
  same-position fallback, zero startup, history floors, counts, latest source
  clocks and mean/lower-median/event-probability values: **11,448 checks**.
  The samples are QA examples, not additional forecast evidence.
- All **1,154 public 2026 summary views** match independent aggregation of the
  retained rows: **19,840 support/error/tolerance/probability metric checks**.
  Maximum absolute floating-point difference is 1.82e-12.
- All **42 primary-role history contrasts** match common identities, outcomes,
  full-system and learned-only loss differences, and week-balanced means:
  **210 checks**. The matched-row sets do not change between history arms.

## Current-season examples and adverse results

Passing-yard lower-median MAE is **101.710744 CURRENT**, **73.933884 RECENT**,
and **71.330579 MULTI**, on the same **242 QB outcomes**. MULTI minus CURRENT is
−30.380165 yards across the full system. On the **156 learned-only common
outcomes**, that difference is −16.25 yards. Startup/fallback therefore affects
the apparent gain substantially and remains visible.

Interception lower-median MAE goes the other way: **0.590909 CURRENT** versus
**0.619835 RECENT** and **0.628099 MULTI**. MULTI's learned-only difference is
also adverse, +0.025641 interceptions. Older history is not a universal winner.

Receptions lower-median MAE on **2,118 common skill-player outcomes** is
1.522191 / 1.286119 / 1.304533 for CURRENT / RECENT / MULTI. Their learned-only
RECENT advantage is smaller (−0.088762 catches on 1,397 common outcomes).
Anytime-TD Brier is 0.189909 / 0.146980 / 0.143755 on the same 2,118 outcomes;
unlike the sparse production-label panel, the raw source contains explicit
non-events. Zero-probability mistakes retain infinite-log-loss counts.

Opaque QA example `7848445bbdb77746` is an anytime-TD RECENT win: its Brier
loss is 0.221453287197232 against CURRENT's 1.0. Example `f2b6ca9f9df51150` is
a MULTI loss: 0.01 against CURRENT's zero. These examples verify both directions,
not a retrospective pick-selection rule.

## Weeks, zeros and population boundaries

The 2026 game counts are **16,16,16,16,15,14,14**, totaling **107**. Every
supported diagnostic target has query and scored-game presence in all fourteen
Week 7 games. This does not fill unsupported legacy-method Week 7 cells or the
chart-PPR label contract. Prior-year game counts are 271 in 2022 and 272 in
2023–2025; subtracting four lots of 272 from the five-season total would invent
a missing 2026 game.

Explicit zero labels are retained after positive official physical-event proof.
Examples among unique 2026 query targets are 1,926 anytime-TD non-events, 128
zero-interception outcomes, 841 zero-reception outcomes, eight zero-attempt QB
outcomes and signed negative yards. Those eight zero-attempt QB outcomes show
that this is an observed-QB cohort, not a pregame starting-QB selection. Source
row existence alone does not establish appearance; unverified participants stay
in missing/fallback coverage.

Primary rushing here means **QB plus RB**, which differs from the legacy RB-only
panels. Extended views are separate disjoint roles, not the primary-plus-extended
union. Historical row positions and the existence of statistical rows define
the cohort retrospectively. Consequently this is not an ex-ante roster/offer
population, a full-system strict-current-information experiment, or an archived
historical forecast reconstruction. It cannot be pooled with the old 93-game
research panel to produce a common-population ranking.

## Source timing and durability

The lookup uses only raw basic statistics eligible under the registered
kickoff-plus-seven-days assumption, strictly before each origin. The verifier
found no target-game or later-outcome contribution in sampled predictions.
Publication times, historical revisions and official label truth were not
independently reacquired. The seven-day policy is a disclosed assumption, not
proof that current-season features were maximally fresh.

The independently inspected fresh downloaded companion archive has SHA-256
`6146ee7b7465dc6f9c7c1be5b4344574fd4e1cc03b20906d74baee68280af192`.
Its single retained prediction member has **7,561,537 bytes** and SHA-256
`52d0c4476ac8a3d45b6128fd092b94c73bf6f9a5c9408f2878df8e33e03a513f`,
matching the run's retained bytes. This verifies recoverable downloaded bytes;
Drive ownership/privacy is separately attested by the executor's private-store
receipt. Public-safe artifact ID: `V2-PRIVATE-DIAGNOSTIC-0001`.

Seven week clusters and exposed development data cannot certify permanent
superiority or calibrated uncertainty. The week t intervals are exploratory,
with dependence/selection limitations preserved. Scientific confirmation,
strong learned controls, qualified current-role features, chart labels and
production admission remain separate work.
