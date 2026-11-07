# Exact chart-PPR source qualification

**A source-specific partial-label reconstruction is now supportable.** Twelve primitives map directly to the restored weekly statistics. Four rare touchdown credits can be proved zero when **both** complete-source touchdown supersets explicitly equal zero. Positive or unknown aggregates stay unresolved. This establishes a label contract, not a forecasting gain or independent proof of NFL source truth.

The [initial schema audit](CHART_PPR_SOURCE_QUALIFICATION_V1.json), [field counts](CHART_PPR_COMPONENT_FIELD_COUNTS.csv), [RDS/CSV parity](CHART_RDS_CSV_PARITY.json) and [source-specific partial-label policy](CHART_PPR_PARTIAL_LABEL_POLICY_V2.json) retain the evidence and its progression. The original initial policy remains linked from v2; its inherited component-status strings were corrected after version qualification, without changing the zero theorem or running a dependent model.

## Sixteen required primitives

| Chart primitive | Source mapping | Qualification |
|---|---|---|
| Passing yards | `passing_yards`, stat 15/16 signed yards | Direct |
| Passing TD | `passing_tds`, stat 16 | Direct |
| Interceptions thrown | `passing_interceptions`, stat 19 | Direct; chart weight −1 |
| Rushing yards | `rushing_yards`, stat 10–13 signed yards | Direct |
| Rushing TD | `rushing_tds`, stat 11/13 | Direct |
| Receptions | `receptions`, stat 21/22 | Direct; two-point stat 104 excluded |
| Receiving yards | `receiving_yards`, stat 21–24 signed yards | Direct; preserves official lateral yards |
| Receiving TD | `receiving_tds`, stat 22/24 | Direct |
| Fumbles lost | `fumbles_lost_total`, stat 106 | Direct; count once, do not add overlapping unit totals |
| Passing two-point conversions | `passing_2pt_conversions`, stat 77 | Two points to credited passer |
| Rushing two-point conversions | `rushing_2pt_conversions`, stat 75 | Two points to credited rusher |
| Receiving two-point conversions | `receiving_2pt_conversions`, stat 104 | Two points to credited receiver, no ordinary reception |
| Offensive fumble-recovery TD | Subset of recovery stat 56/58/60/62 | Zero theorem only; positive attribution pending |
| Kick-return TD | Kickoff return stat 46/48, including lateral scorer | Zero theorem only; positive attribution pending |
| Punt-return TD | Punt return stat 34/36, including lateral scorer | Zero theorem only; positive attribution pending |
| Field-goal-return TD | Miscellaneous TD stat 64 with field-goal context, or relevant fumble-chain credit | Zero theorem only; positive exceptional credit pending |

`special_teams_tds` is broader than the chart's listed return components: the inspected source includes stat 108, whose helper explicitly identifies an **own-kickoff-recovery TD**. Stat 64 alone does not distinguish blocked punt versus field-goal context. `fumble_recovery_tds` includes own/opponent and lateral recovery scores without an offense-only split. These aggregates must never replace positive chart primitives wholesale. Generic provider fantasy PPR also fails parity: its interception/fumble penalties and touchdown groups differ from this chart.

## The zero proof and its evidence tier

Let F and S be the nonnegative complete-source counts `fumble_recovery_tds` and `special_teams_tds`. Recovery IDs 56/58/60/62 enter F. Kickoff 46/48, punt 34/36 and special-play miscellaneous TD 64 enter S; relevant fumble-chain scoring credits enter F. Therefore, under complete official credit and special-play classification, every listed rare chart component C satisfies **0 ≤ C ≤ F + S**. If **F = S = 0**, each C is zero. Extra types included in the supersets cause conservative unresolved rows when positive; they cannot create a false zero.

This is an inference from two **explicit** complete-source zeros, never a missing-value fill. It depends on the provider's complete full-week event-credit contract and correct special-play classification. The source functions also permit filtered `custom_pbp` inputs with identical output shape, so headers alone were insufficient. The RDS companions identify full-week player statistics, carry no `custom_pbp` marker, and match every cell of the retained CSVs. The reviewer has not independently replayed every underlying play or authenticated official NFL revisions. A later contradictory source/credit finding must invalidate affected labels through a new version.

For 2022–2025 the retained producer is **nflfastR 5.2.0.9015**; for 2026 it is **6.0.0**. The exact `calculate_stats.R` and tidy-stat helper bytes are identical at development-version commit [2cf16e4d101f93984d4027e5cb3950a3eff91807](https://github.com/nflverse/nflfastR/tree/2cf16e4d101f93984d4027e5cb3950a3eff91807) and tag [v6.0.0](https://github.com/nflverse/nflfastR/tree/v6.0.0). The code-blob hashes are recorded in the policy. These traces explicitly include lateral punt/kickoff scorers and distinct credited two-point events.

## Actual restoration and coverage

The executor registered a **16 MiB** RDS-only allocation. Five exact-digest, pre-kickoff companions totaling **4,309,114 bytes** were restored outside public Git. Release metadata was checked before download; payload hashes were checked before decoding. The 2026 asset predates the first Week 8 kickoff and contains only Weeks 1–7. All **12,498,900 CSV cells** across all five files match their RDS counterparts; the largest numeric difference is **5.69e−14** from CSV floating-point formatting. Source attributes were inspected separately from data conversion. Free readers rdata 1.1.0 (MIT) and xarray 2026.9.0 (Apache-2.0) have recorded wheel hashes in the [dependency manifest](CHART_RDS_READER_DEPENDENCIES.json).

| REG source panel | All player-stat rows | Both rare aggregates explicitly zero | Positive/unknown rare attribution |
|---|---:|---:|---:|
| 2022 | 17,981 | 17,942 | 39 |
| 2023 | 17,806 | 17,773 | 33 |
| 2024 | 18,130 | 18,091 | 39 |
| 2025 | 18,540 | 18,495 | 45 |
| 2026 Weeks 1–7 | 7,447 | 7,439 | 8 |

These are source-row coverage counts across all positions, not a frozen forecasting population, appearance certificate or number of independent NFL observations. **All 164 positive/unknown rows, including eight in 2026, remain present with null chart labels until attributed.** Any future chart diagnostic must separately freeze its population, participation rules and relevant primary/extended/return-only roles, retain missing-label coverage, and compare procedures on identical supported rows. Signed production stays signed.

The original [RDS probe receipt](CHART_RDS_SOURCE_PROBE_RECEIPT.json) and private source bytes require approved offhost restoration before dependent fits. No play-by-play bulk download, chart fit, new chart forecast or Week 8 outcome read occurred in this qualification.

## Completing positive rare credits

An executable next source pass needs immutable `play_stats_{season}.rds` event credits (game/play/stat/GSIS player/team) joined to aligned PBP game/play, scoring player/team, possession, special-play and kick type, recovery/lateral and nullified/deleted-play fields. Credit the official touchdown scorer, who may be the lateral recipient rather than the initial returner/recoverer. Match official credited events once, exclude two-point events and prevent overlap with ordinary rushing/receiving TD credits. Do not deduplicate legitimate repeated fumble credits merely by player/game: retain source credit/event identity.

Kick/punt IDs give direct event candidates. Recovery scores need offense/unit attribution; miscellaneous stat 64 needs field-goal context and exceptional-case checks. Compare ordinary, negative-yard, unique-fumble, two-point, recovery and return examples by hand, then reconcile complete-event zeros and all rare positives. nflverse-pbp publishes a CC BY 4.0 license and nflfastR an MIT license; inherited restricted feeds remain excluded. For 2026 recover an archived pre-Week-8 snapshot or an approved strict Weeks 1–7 export. **Do not download a mutable current-season event payload that may contain Week 8 outcomes.** No source bulk allocation is inferred from this report.
