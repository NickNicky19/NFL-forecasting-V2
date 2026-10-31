# Test results: error and explicitly measured accuracy

16,048 evaluation output views and 12 separate software-verification receipts. These are not distinct-method, fit, or independent-NFL-sample counts.

4,964 inherited/replay views and 11,084 separate current-vintage participant-diagnostic views retain different population/evidence identities. No cross-panel winner is inferred.

[Browse category CSVs](categories/README.md) · [Full filterable CSV](TEST_RESULTS_INDEX.csv) · [Complete compact JSON and definitions](TEST_RESULTS_INDEX.json) · [Reporting contract](../../docs/RESULT_REPORTING_CONTRACT.md)

Every evaluation has a stable test ID, exact source link/hash, method, category, product, evidence level, denominator and available errors. Filter the CSV by category, panel, product, population and evidence before comparing. Unknown dates, histories, coverage or scores remain explicit unknowns.

MAE/RMSE are native-unit errors; lower is better. Bias is signed prediction minus outcome. Brier/log loss score probabilities. None becomes an accuracy percentage. Exact-match and tolerance accuracy are supplied fractions with their denominators; reconstructed hit counts are labeled. Probability residual tolerances are not classification or pick accuracy. Software passes have no NFL accuracy.

| Source | Evaluation views | Evidence |
|---|---:|---|
| [reports/inventory/ALL_METHOD_SCORES.json](../inventory/ALL_METHOD_SCORES.json) | 4,832 | REPORTED_NOT_REPRODUCED |
| [reports/replay/REPLAY_SCORES.json](../replay/REPLAY_SCORES.json) | 66 | REPRODUCED_FROM_DATA |
| [reports/week7-label-extension-v1/SCORES.json](../week7-label-extension-v1/SCORES.json) | 66 | NEW_LABEL_RECONSTRUCTION_SCORED |
| [reports/continuation-20261029/history-diagnostic-v1/SEASON_RESULTS_2022_2026.csv](history-diagnostic-v1/SEASON_RESULTS_2022_2026.csv) | 10,154 | NEW_EXPERIMENT |
| [reports/continuation-20261029/hgb-history-v1/SCORES.json](hgb-history-v1/SCORES.json) | 930 | NEW_EXPERIMENT |

| Category | Views | With MAE | With Brier | With numeric precision accuracy |
|---|---:|---:|---:|---:|
| [anytime_td](categories/anytime_td.csv) | 1310 | 1049 | 1193 | 0 |
| [nick-chart-ppr-v1](categories/nick-chart-ppr-v1.csv) | 14 | 12 | 0 | 0 |
| [pass_att](categories/pass_att.csv) | 1168 | 1086 | 28 | 689 |
| [pass_cmp](categories/pass_cmp.csv) | 1124 | 1049 | 22 | 680 |
| [pass_int](categories/pass_int.csv) | 1162 | 1079 | 28 | 690 |
| [pass_td](categories/pass_td.csv) | 1140 | 1058 | 28 | 684 |
| [pass_yd](categories/pass_yd.csv) | 1095 | 1025 | 22 | 680 |
| [rec](categories/rec.csv) | 1843 | 1769 | 24 | 1420 |
| [rec_yd](categories/rec_yd.csv) | 1781 | 1734 | 24 | 1420 |
| [rush_att](categories/rush_att.csv) | 1851 | 1777 | 24 | 1420 |
| [rush_rec_yd](categories/rush_rec_yd.csv) | 1778 | 1731 | 24 | 1420 |
| [rush_yd](categories/rush_yd.csv) | 1782 | 1735 | 24 | 1420 |

The short reference below shows reproduced primary-role results from the original one-game replay. The CSV/JSON retain all views, losing results and the separate later-label panel. These examples are not a pooled ranking.

| Stable test ID | Method / category | n | Primary error | Exact matches | Source |
|---|---|---:|---:|---|---|
| `TEST-d7d08784923eadbc58bb` | lab-v1.1-pooled / anytime_td | 5 | brier 0.647943 | not a binary decision | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-3476f0d9f3d9f17e6f47` | lab-v1.1-recent / anytime_td | 5 | brier 0.647943 | not a binary decision | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-b2ff29c222ec3178b064` | lab-v1.1-tree / anytime_td | 5 | brier 0.784989 | not a binary decision | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-7640663c25119511eecc` | lab-v1.1-pooled / pass_att | 2 | mae 3.87089 | 0/2 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-77e691e2ce9819934e9a` | lab-v1.1-recent / pass_att | 2 | mae 3.87089 | 0/2 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-fe484c63c9899d6180d6` | lab-v1.1-tree / pass_att | 2 | mae 17.3835 | 0/2 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-530b64f68de6312c6c5c` | lab-v1.1-pooled / pass_cmp | 2 | mae 4.85427 | 0/2 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-d19fc4e7221a1158418d` | lab-v1.1-recent / pass_cmp | 2 | mae 4.85427 | 0/2 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-ec430d10095e6837dd94` | lab-v1.1-tree / pass_cmp | 2 | mae 13.8107 | 0/2 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-06ddad410a402f443186` | lab-v1.1-pooled / pass_int | 1 | mae 0.369048 | 0/1 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-dbe69e3493481972ecdc` | lab-v1.1-recent / pass_int | 1 | mae 0.369048 | 0/1 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-6fb3e906c59f07c6d865` | lab-v1.1-tree / pass_int | 1 | mae 0.556963 | 0/1 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-fd52778c66eb65f831ac` | lab-v1.1-pooled / pass_td | 2 | mae 0.744663 | 0/2 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-9b086e4b215b1149459e` | lab-v1.1-recent / pass_td | 2 | mae 0.744663 | 0/2 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-7a48c1d52d7573a713c0` | lab-v1.1-tree / pass_td | 2 | mae 1.52824 | 0/2 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-b153981d818bcfbc265f` | lab-v1.1-pooled / pass_yd | 2 | mae 114.632 | 0/2 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-a78cf6b819c1fccfaff1` | lab-v1.1-recent / pass_yd | 2 | mae 114.632 | 0/2 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-2394df626ccdb4e59938` | lab-v1.1-tree / pass_yd | 2 | mae 218.554 | 0/2 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-e95ea3c84c0741ee5f3e` | lab-v1.1-pooled / rec | 12 | mae 1.83715 | 0/12 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-5283e64c2798aa12de3a` | lab-v1.1-recent / rec | 12 | mae 1.82556 | 0/12 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-bd83d7bdfa4b4ed44c3b` | lab-v1.1-ridge_without_opponent / rec | 12 | mae 2.665 | 0/12 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-d74ae8263c7759d6708c` | lab-v1.1-pooled / rec_yd | 12 | mae 32.1605 | 0/12 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-7994b4cfb0bb50959e4d` | lab-v1.1-recent / rec_yd | 12 | mae 31.84 | 0/12 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-c821af8e58cca3c53b27` | lab-v1.1-ridge_without_team / rec_yd | 12 | mae 37.8834 | 0/12 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-dd73fff1f0cb920c8abd` | lab-v1.1-pooled / rush_att | 5 | mae 5.99028 | 0/5 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-87114ca7ecc2b75f49ee` | lab-v1.1-recent / rush_att | 5 | mae 5.99028 | 0/5 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-ad2f50b1ae5be62d17d0` | lab-v1.1-tree / rush_att | 5 | mae 4.61157 | 0/5 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-272a74e883ea79c21151` | lab-v1.1-pooled / rush_rec_yd | 4 | mae 59.7891 | 0/4 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-2c931b2bbeef3e2e491f` | lab-v1.1-recent / rush_rec_yd | 4 | mae 59.7891 | 0/4 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-42e94a0c90459855eda9` | lab-v1.1-ridge_without_opponent / rush_rec_yd | 4 | mae 72.7379 | 0/4 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-c4ec9a53db428a9c7160` | lab-v1.1-pooled / rush_yd | 5 | mae 23.9462 | 0/5 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-17b098cc255da2f86397` | lab-v1.1-recent / rush_yd | 5 | mae 23.9462 | 0/5 | [frozen result](../replay/REPLAY_SCORES.json) |
| `TEST-e19fef6ce3d3f644d353` | lab-v1.1-tree / rush_yd | 5 | mae 16.5181 | 0/5 | [frozen result](../replay/REPLAY_SCORES.json) |

Original one-game and later Week 7 labels are incomplete and select explicit production. Later anytime-TD labels are all positive. Those probability scores do not establish representative calibration or skill. Training-history conclusions require identical populations and isolated fit-window procedures; unknown legacy history is labeled rather than inferred.

The history diagnostic includes all10,154 frozen season/week/position/fallback views, exact per-view distinct scored/forecast games, source aggregate fields, infinite-score flags and bound protocol/code/prediction provenance. It is a retrospective observed-stat-row/participation cohort, not the full ex-ante website population or authenticated pregame capture. Its seven-week uncertainty and exposure limits remain in the linked report.

The 930 HGB fixed-objective views are separately identified, linked to retained models, protocol/code, and independent per-view game counts. Current-season fitting uses common older feature memory. Losses and startup fallback are retained; these point products are not numeric probability distributions.

Future normalized JSON aggregate evaluations enter through `--additional`; empirical and HGB diagnostics have explicit adapters and independent game censuses. Software receipts use `--software-receipt`. Preserve immutable old artifacts and register corrected/new runs separately.
