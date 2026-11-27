# Later provider snapshot consistency check

**55 of59 explicit retained labels matched;4 remain identity-unverified;0 numerical mismatches among comparable labels.** This is a second calculation against a later snapshot from the **same Sleeper provider family**, not independent NFL statistical truth. No additional outcomes were scored and no missing label was filled.

The earlier605-row outcome packet contains59 explicit labels and546 nulls, all59 for ESPN game401873010. The comparator is production commit `911a81a31f822de58e0f9c04ded070f8c9752670`, file `data/cache/stat-keys-fgm-v1/stats_2026_07.json`, Git blob `ca299a9b470fe3a28441b03dd00ab9e16fbdde12` (63,956 bytes). Its exact retained content hash and the earlier packet hashes are in `LABEL_SOURCE_CROSSCHECK.json`. Raw comparator and detailed joined records remain outside this public V2 repository.

Production `output/data/weeks/2026_w07.json`, blob `39c2ea99affa4ae747a284ce93f9395592b1ebd4`, identifies game401873010 as NE at CHI, kickoff October23 00:15UTC, completed. All55 comparable cache rows have the corresponding team/opponent pair. This corroborates identity using the production schedule view; that view itself derives from ESPN and does not independently verify every statistical label or final revision.

| Target | Matched | Identity unverified |
| --- | ---: | ---: |
| pass_yd | 2 | 0 |
| pass_td | 2 | 0 |
| pass_cmp | 2 | 0 |
| pass_att | 2 | 0 |
| pass_int | 1 | 0 |
| rush_yd | 8 | 0 |
| rush_att | 8 | 0 |
| rec | 10 | 2 |
| rec_yd | 10 | 2 |
| rush_rec_yd | 4 | 0 |
| anytime_td | 6 | 0 |

The four unmatched labels belong to two unprefixed GSIS-looking identifiers, one containing leading whitespace. They do not match the cache's Sleeper identity namespace. No fuzzy name, matching-statistic, whitespace-only or guessed alias join was made. An exact admitted GSIS/Sleeper crosswalk is required before counting them as cross-verified. Their earlier replay values are preserved at their prior evidence level.

The nine primitive category labels were compared only when their exact source field existed. Signed combined yards were recomputed only when both rushing and receiving yard primitives existed. The six comparable anytime labels are all event1, independently supported by at least one positive rush_td or rec_td credit; absence of the other primitive is unnecessary to prove event1. Event0 would require an actual complete zero contract or both explicit zeros, and was not inferred. The cache also supplies positive gp/off_snp evidence for the55 comparable label rows; this is sufficient positive participation evidence, not a complete DNP denominator.

The comparator is **website-normalized**, not a raw independent feed. At the pinned version, `pull/sources.py:week_stats` calls Sleeper `/stats/nfl/{season}/{week}` with regular-season and position parameters. `pull/build.py:61–81` normalizes it through `trim_stats`, whose line65 keeps a statistic only when `s.get(k)` is truthy; line66 omits rows without retained truthy fields. Therefore an omitted field can mean a removed explicit zero or an unavailable field. A missing row is not DNP. V2 must not import the legacy website's `stat_value(... or0)` rule to authenticate those omitted labels.

The earlier packet was observed October23 17:57:28.190038UTC; the retained later production cache was inspected October29. Neither packet establishes provider revision time. Agreement on55 values shows no observed change in that comparable subset; it is not proof that no later official correction exists. The4 unjoined rows and546 earlier nulls remain unresolved by this check. Chart-PPR primitives and rare scoring attribution were outside this59-label comparison.

Evidence labels: **VERIFIED_FROM_CODE** for source/normalization and missing-zero semantics; **REPRODUCED_FROM_DATA** for55 matches and identity counts; **UNKNOWN/BLOCKED** for the exact4-row identity crosswalk and independent official statistical/revision verification.
