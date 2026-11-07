# Frozen older-season subgroup memberships

Before inspecting new seasonal forecasts or loss metrics, V2 froze the same earlier-feature cohort rules for every competitor in 2022–2025. The private files cover all 18 regular-season weeks, including historical Week 8. This step produced no models, forecasts or scores.

| Season | Query cells | Player-games | Games | Unranked query cells |
| --- | ---: | ---: | ---: | ---: |
| 2025 | 45,579 | 6,037 | 272 | 1,540 |
| 2024 | 44,368 | 5,864 | 272 | 1,415 |
| 2023 | 43,922 | 5,801 | 272 | 1,669 |
| 2022 | 43,821 | 5,808 | 271 | 7,855 |

Football ranks use earlier attempts, carries, targets or carries plus targets. Chart ranks use signed qualified chart points, with score-history bands rather than workload bands. Both use the last three earlier-available player-game slots; unknown slots consume the window. Membership is evaluated at the week's earliest kickoff minus 90 minutes under the inherited strict seven-day availability assumption. No source season after the evaluation season is decoded. Starting in 2022 provides no pre-2022 warm start, explaining much of its unranked coverage.

This remains a current-vintage retrospective statistical-row universe, not an authenticated ex-ante population. Common older selector memory is separate from a model's strict-current information policy. Every competitor uses identical membership. Neither realized season totals nor subgroup loss winners determine ranks.

The run took 11.37 seconds and wrote 1,747,796 private bytes with local readback. It read zero forecast values, zero seasonal score values and zero 2026 Week 8 outcomes. The [protocol](FROZEN_PROTOCOL.json), per-season membership receipts and [run receipt](RUN_RECEIPT.json) bind sources, helpers, queries, coverage and missing slots. Root manages offhost restoration separately.
