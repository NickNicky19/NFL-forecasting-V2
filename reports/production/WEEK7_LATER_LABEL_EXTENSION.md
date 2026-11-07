# Week7 later explicit-label extension v1

**666 supported explicit labels were reconstructed across all14 Week7 games**, covering190 player-games. All8,096 original player/game/target opportunities remain in the private output:7,430 retain nulls with reasons. This is a separately versioned later-label reconstruction, **not recovery of the original outcome capture, an independent NFL truth source or a new model fit**. No forecast or accuracy score was created by this operation.

Run ID: `v2-week7-later-explicit-labels-20261029-v1`. Original forecast packet:24,288 rows, three model views,736 player-games,14 games,11 targets. The666 later labels can join1,998 original forecast rows;22,290 forecast rows remain unresolved. Three model views of a label are not three independent NFL observations. The full original population remains the coverage denominator. Exact source/input/output hashes, actual reconstruction observation time and counts appear in `WEEK7_LATER_LABEL_EXTENSION.json`.

| Target | Explicit supported labels | Null opportunities |
| --- | ---: | ---: |
| pass_yd | 16 | 720 |
| pass_td | 13 | 723 |
| pass_cmp | 16 | 720 |
| pass_att | 16 | 720 |
| pass_int | 8 | 728 |
| rush_yd | 89 | 647 |
| rush_att | 90 | 646 |
| rec | 157 | 579 |
| rec_yd | 156 | 580 |
| rush_rec_yd | 56 | 680 |
| anytime_td | 49 | 687 |

Each of the14 games has30–64 supported label cells. This is partial per-game/category coverage, not complete Week7 grading. Of736 original player-games,288 have matched source identity/team/opponent, a completed scheduled game and positive gp/off_snp participation evidence;190 have at least one complete explicit target. The original cohort includes current-active roster eligibility, which is not itself pregame appearance proof or a category-appropriate subset. Do not derive favorable skill claims by ignoring this population issue.

## Exact source and mapping

Both comparator files were read at production commit `911a81a31f822de58e0f9c04ded070f8c9752670`:

- `data/cache/stat-keys-fgm-v1/stats_2026_07.json`, Git blob `ca299a9b470fe3a28441b03dd00ab9e16fbdde12`:450 normalized records across28 team/opponent directions.
- `output/data/weeks/2026_w07.json`, Git blob `39c2ea99affa4ae747a284ce93f9395592b1ebd4`:14 distinct ESPN game IDs, each with state post/completed true. Each team plays exactly one game in this weekly identity panel.

The original forecast identity must have an exact `sleeper:` prefix and agree with its retained sleeper_id. The `espn:` game ID, kickoff, forecast team/opponent pair and source team/opponent pair must all agree with the completed-game schedule. Conflicting original context, namespace ambiguity and missing source records remain null. No name matching, value matching, whitespace repair or guessed GSIS alias is performed.

Positive finite integer gp or off_snp proves appearance for this partial conditional panel. Missing or nonpositive participation evidence remains unknown; absence from the snapshot is never DNP. The nine primitive targets use only finite explicit corresponding fields, with nonnegative integral support for counts and signed production retained for yards. Combined rushing+receiving yards requires both explicit finite components. Anytime TD requires a valid positive rushing or receiving TD credit to prove event1; event0 requires both components explicitly zero. Return touchdowns do not enter the event. Chart PPR is outside this eleven-target packet and is not substituted with generic provider fantasy points.

## Missingness and evidence limits

Null reasons are preserved separately:

| Reason | Opportunity cells |
| --- | ---: |
| Player absent from normalized snapshot | 3,135 |
| Primitive omitted, not assumed zero | 2,031 |
| Unverified identity namespace | 1,540 |
| Participation not established | 253 |
| Incomplete anytime-event components | 239 |
| Incomplete signed combined-yard components | 232 |

The production source pipeline calls Sleeper's regular-season weekly endpoint, then `pull/build.py:trim_stats` retains only truthy fields from its allowlist. Explicit zero and unavailable fields therefore become indistinguishable in this normalized cache. The49 anytime labels are all positive events; this source cannot establish the missing event-zero denominator. Explicit-only numeric grading is likewise selected by realized production and can favor or disadvantage a method differently from full participant grading. Any follow-on scores must state this selection, retain coverage, and must not claim full-system forecast skill, calibrated event probability or a conclusive training-history result.

The later cache/schedule are from the same provider/website lineage used in existing research. They do not independently authenticate official final NFL statistics, revisions, complete played-zero records, original label availability or historical forecast issuance. Provider revision clocks are absent. The reconstruction clock is the actual time this run processed the supplied retained bytes; it is never backdated to a game or old capture. This extension does not turn reconstructed later values into historical pregame features.

## Reproduction and downstream use

`tools/reconstruct_week7_labels.py` is original V2 standard-library code. It reads only supplied forecast/statistics/schedule bytes, checks duplicate JSON keys and bounded sizes, groups original model views into immutable opportunity keys, performs the stated joins/mapping, and writes a private full-population label list plus aggregate report. It refuses to overwrite existing outputs. It makes no network requests, fits, predictions or score calculations.

Supply `--forecasts`, `--stats`, `--schedule`, a new `--run-id`, the pinned `--source-commit`, private `--output` and public-safe `--report`. `--observed-at` defaults to actual processing time; an exact replay must retain the original run's observation clock and input hashes rather than fabricate earlier availability. Use a new output destination for replay; do not overwrite a failed/earlier run. Source fixtures/records belong in approved private storage, not this public repository.

The primary executor may independently score this packet under a new scoring run ID and the existing frozen forecast definitions, preserving the earlier59-label replay unchanged. Report the full8,096 opportunity denominator and distinguish exact-prefix later-label support from any future crosswalk/source repair. An independent official or retained raw complete-source packet is still needed to resolve zero/missing distinctions and the namespace gaps.

Evidence labels: **VERIFIED_FROM_CODE** for source normalization and V2 join/mapping; **NEW_EXPERIMENT** for this separately versioned label reconstruction; **UNKNOWN/BLOCKED** for omitted zeros, ambiguous identities, independent official/revision truth and all unresolved cells. Code checks and retained hashes do not convert those unknowns into successes.
