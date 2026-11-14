# Interception label evidence — independent source verification

**All 46 selected W5–9 participant records with absent website `pass_int` fields are explicitly reported as zero interceptions thrown by both the current NFLverse weekly table and the matching ESPN game-athlete passing-stat record.** No zero was assigned from participation, attempts, a missing field or a generic sparse-provider contract. The other 40 selected records retain their explicit positive values, which match both sources. All 61 selected games have source-final status.

The full 144-opportunity real-line board also matches both sources: 71 absent website interception fields correspond to explicitly reported zeros; all 73 positive reported values agree. Of the 58 unselected opportunities, 25 have absent website fields with explicit zero source values and 33 retain positive values. Those unselected rows are coverage/control evidence, not issued selections. All 72 full-board games are source-final.

The actual count is **quarterback interceptions thrown**: NFLverse `passing_interceptions` and ESPN's unique `passing` category's `interceptions` field, whose definition is “The number of passes thrown that were intercepted by the opposing team.” Defensive `interceptions` are never used. The verifier also reconciles official credited pass attempts and completions across both representations, so a merely matching zero or name is insufficient.

Identity uses exact retained Sleeper→GSIS→ESPN mappings, canonical event/season/week and team/opponent compatibility. The retained bridge is used for stable identifiers, not to infer historical roster status or who started. Name matching is not used. Source-final game status is queried separately. Explicit zero is retained as a count; null, absent, non-finite, boolean or non-integer values fail admission. Source conflicts fail the check rather than receive a guessed outcome.

These are **current-vintage final-stat label corrections**, observed November12, 2026. They do not establish what an old compacted Sleeper absence originally meant, what data existed before a historical forecast, a pregame selection/quote clock, an original-site deployment, a verified venue settlement or improved forecast skill. The sources are the named NFLverse and ESPN representations; no direct NFL-league gamebook/API fetch or fully independent upstream data lineage is claimed. Original picks, missing grade states and source bytes must remain preserved when the owner appends corrected label/grade versions.

| Week | Selected rows | Selected absent fields now supported as explicit zero |
|---|---:|---:|
| 5 | 20 | 14 |
| 6 | 17 | 9 |
| 7 | 15 | 8 |
| 8 | 16 | 6 |
| 9 | 18 | 9 |
| Total | 86 | 46 |

[Selected evidence receipt](OFFICIAL_INTERCEPTION_EVIDENCE_V1.json) · [Full-board source receipt](FULL_BOARD_OFFICIAL_EVIDENCE_V1.json) · [Exact current weekly source/hash](CURRENT_WEEKLY_SOURCE_RECEIPT_V1.json) · [Projection and limits](SOURCE_PROJECTION_AND_LIMITS_V1.json) · [Portable read-only verifier](verify_official_interceptions_v1.py).

Private correction maps and raw responses remain owner-local outside public Git. Public artifacts contain aggregate counts, bindings and hashes only. The verifier performs zero fits, model calls, grading calls, source scheduler changes or production writes. Root owns the independent side/combined regrade and registration; C retains common admission. This receipt adds no NFL games or previously unobserved evaluation weeks.
