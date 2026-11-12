# B source qualification — pregame QB depth rank

The source-backed new block is **reported QB depth rank**, with a same-team change from an eligible earlier QB-game snapshot where supported. This is different from the completed lagged attempts, context, profile, defense and timing experiments. It does not supply a probability of starting or a teammate-health model. The root owns the predictive experiment and its fit authorization.

Two actual nflverse depth-chart Parquet assets were restored once outside the publication tree. Their combined size is **6,049,756 bytes**. No injury source was downloaded again: C already owns prospective nflverse injury snapshots. No fit, inference, forecast or NFL scoring was performed by this source-qualification task.

| Actual asset | SHA-256 | Source rows | Source-loaded timestamps | Coverage |
| --- | --- | ---: | ---: | --- |
| depth_charts_2025.parquet | `14f74185b3c2c48df234ced284ba3596bda3333d0b2a8df40841f68cd34539fa` | 554,215 | 221 | 2025-08-03 10:09:07 UTC through 2026-03-14 07:32:09 UTC; 32 teams |
| depth_charts_2026.parquet | `8633b61b70c35eaf919c8aef9934c8802723de4dfb6aeb7f354dfc09237a5ced` | 780,140 | 292 | 2026-03-22 06:38:42 UTC through 2026-11-12 15:57:12 UTC; 32 teams |

The [source dictionary](https://nflreadr.nflverse.com/articles/dictionary_depth_charts.html) defines `dt` as the ISO8601 time the record **was loaded**, and `pos_rank` as rank within `pos_slot`. The [availability schedule](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html) states that 2025-and-later updates append new timestamped snapshots. Actual rows include the earlier snapshots; this conclusion is not based on documentation alone.

This supports **current-vintage reconstruction using source-authored load clocks**. It does not independently authenticate every original historical HTTP response or establish that no earlier row was later revised. A file downloaded now is not relabeled original pregame issuance. Exact metadata, receipt clocks and hashes are in [SOURCE_METADATA_RECEIPTS_V1.json](SOURCE_METADATA_RECEIPTS_V1.json).

The data repository's actual [LICENSE.md](https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md) is CC-BY-4.0: Git blob `0fb847eb09afc05734c2f1aa34bc3ebd995a072a`; decoded SHA-256 `2a82ac9bbc3e3ee066908381e8d373896db5a6025d083fbd59692fe9ccfb9111`. Attribution to nflverse and the depth-chart source is retained. This report publishes no raw player rows and makes no independent legal finding about upstream ESPN rights.

| Proposed information | Classification | Actual scope or limitation |
| --- | --- | --- |
| Earlier QB/team attempts, conditional completion, down/depth mix, support and timing | Already tested / equivalent information | Reuse the completed B studies; no new source was needed for these |
| Source-reported QB slot rank at the decision cutoff | Genuinely new, source-authored historical reconstruction | Actual 2025/2026 appended snapshots; not an authenticated starter/health probability |
| Same-team rank change versus an eligible earlier QB-game | Genuinely new, sparse historical reconstruction | Undefined when no qualified same-team prior exists; ordinal difference remains separate from any probability |
| Weekly roster status | Existing identity/source limitation | The retained 2026 W1–8 file has 19,860 rows, but no original report/effective clock or depth rank. Its `depth_chart_position` is a position label |
| C current roster | Existing current-query identity support | 959 records, six identity/status fields; no event-effective or original injury-report clock |
| QB/OL/pass-catcher medical availability | C-owned prospective observations; full historical block not qualified here | Reuse C's retained snapshots; `date_modified` means updated information and must not be substituted for the depth `dt` contract |
| Target-game starter, final participation or realized workload | Excluded future information | Never used to create the new rank input or priority membership |

Strict admission takes the latest **team** snapshot with `dt < cutoff`, then an exact team/GSIS QB row. The only inspected offensive formation is source label `3WR 1TE`, with QB slot 9. There are no repeated GSIS/team/clock rows, conflicting ranks or multiple QB slots in either restored season. Missing GSIS rows remain unavailable: 87 in the 2025 QB source and 312 in 2026; no name match is invented.

Preserving empty team updates matters. The source contains one 2025 and twelve 2026 team snapshots with no QB row. The frozen source reader retains these clocks before filtering positions, so an empty update cannot silently reuse an older QB rank. The inspected query coverage is unchanged after that guard. This is a source-reader boundary correction made before any fit; it is not a measured historical forecasting defect or accuracy gain.

On the retained, **stat-row-conditioned** 2026 QB query universe, all 277 W1–8 rows have one exact earlier source rank. Weekly query counts are 37, 39, 36, 34, 36, 29, 31 and 35. Source age ranges from 0.346 to 12.554 hours. Rank-1 counts are 31, 29, 30, 29, 27, 26, 27 and 28; backup ranks remain visible. The 2025 retained panel has 663/664 supported rows, with one unavailable W17 identity in the latest team snapshot. This is source coverage, not actual-offer coverage or a proven pregame universe. Root must show offered-player results separately and must not attribute backup numerical gains to prop improvement.

[SOURCE_CLOCK_AND_COVERAGE_V1.json](SOURCE_CLOCK_AND_COVERAGE_V1.json) contains exact source fields, per-week counts, rank support, missingness, source-clock qualifications and training-support diagnostics. [qb_depth_source_v1.py](qb_depth_source_v1.py) is a read-only, hash-bound loader and independent raw-source check. It exposes canonical rank records and complete team-update clocks for the separately owned feature implementation; it is not another model or grader. Decode with the pinned isolated `fastparquet 2026.9.0` environment used in this run. The first unavailable decoder imports and their isolated resolution are recorded; no unsafe model loading occurred.

The historical rank experiment is feasible under the declared reconstruction tier. This source task establishes no gain, release eligibility or actual consumer use. C-owned medical availability, authenticated original source vintages, current event-effective roles and genuine future offered-line capture retain their separate evidence requirements.
