# Reproduce the checkpoint

The scoring/history package needs Python3.12+standard library. Tests: `python -m unittest discover -s tests -v`. Fictional chronology tests are software evidence, not NFL fits.

Original source IDs are in `registries/PUBLIC_REPLAY_SOURCE_IDS.json`: pinned public Git blobSHAs for the retained compressed forecast,605small outcome objects and original scorecard. `tools/restore_retained.py --private-dir PRIVATE_DIRECTORY` uses existing authorized `gh api` access and verifies blobSHA1/declared sizes plus forecastSHA256. It writes outside the repository only. This command was not run successfully from the selected shell because its inherited proxy is unreachable; this checkpoint actually restored equivalent bytes using the connected GitHub read tools. Do not change proxy/credentials to bypass a denied source. Source rights/zero semantics remain binding.

After authorized restoration:

```
python tools/replay_retained.py --private-dir PRIVATE_DIRECTORY --output reports/replay
python reports/verification/independent_replay.py PRIVATE_DIRECTORY/forecast.json.gz PRIVATE_DIRECTORY/outcomes-base64.json --output reports/verification/INDEPENDENT_REPLAY.json
python reports/verification/check_primary.py
```

`check_primary.py` compares retained aggregate artifacts and takes no CLI flags; raw source arguments belong to `independent_replay.py` only. No numeric result should be invented if bytes are unavailable. Replay recomputes scores, not original forecast issuance or model fit history. Runtime receipt timing will differ across reruns; frozen original checkpoint receipts should be preserved in a new output version instead of overwritten. Use a new output directory for subsequent replays. The current verification helper reads the canonical retained aggregate paths; run a new replay/verification in an isolated checkout rather than replacing old checkpoint bytes.

Original V2reconciliation is `tools/reconcile_checkpoint.py --staging-dir NEW_STAGING_DIRECTORY`; it refuses to overwrite canonical registries or an existing directory; it consumes the pinned public aggregate projection plus replay outputs and keeps reported versus reproduced rows separate. Source-local provisional labels are not canonical methods. Historical amendments and additional software-only engine cells are appended in the checkpoint registries; retain them on regeneration, rather than replacing the immutable registries with a smaller projection. The importer is a projection helper, not an unattended production writer.

`nfl_v2/history.py` implements software-tested empirical controls from admitted supplied snapshots with mandatory finite manifests, not an executed NFL tournament. See HISTORY_ENGINE.md. Source facts, complete-label populations, historical rosters and durable private input retention require external qualification. No automatically acquired/paid/secret-bearing data, capture scheduler or model publication exists here.

Recoverability: the replay originals remain in pinned upstream public Git objects subject continued access/retention; V2publishes source IDs, code, aggregate scores and byte manifests. The broader private experiment/model/quote corpus was not restored. There is no approved durable V2private companion store binding; do not claim this checkpoint preserves unshared private experiments or permanently archives player rows. New large dependent studies remain queued until that binding and source panels are actually admitted.

## Separately versioned later Week7 labels

Restore with `tools/restore_retained.py --private-dir PRIVATE_DIRECTORY --include-later-week7` to obtain the pinned later statistics and full completed-game schedule alongside the original forecast. Then:

```
python tools/reconstruct_week7_labels.py --forecasts PRIVATE_DIRECTORY/forecast.json.gz --stats PRIVATE_DIRECTORY/production-stats-2026-w07.json --schedule PRIVATE_DIRECTORY/production-week-2026-w07.json --output PRIVATE_DIRECTORY/outcomes-week7-later-explicit.json --report NEW_REPORT_PATH --source-commit 911a81a31f822de58e0f9c04ded070f8c9752670 --run-id NEW_LABEL_RUN_ID
python tools/score_label_extension.py --private-dir PRIVATE_DIRECTORY --output NEW_SCORE_DIRECTORY
python reports/verification/check_label_extension.py
```

Both builder and scorer refuse existing output versions. The separate verifier's retained paths may need an isolated checkout matching its expected filenames; read its main block before running. The builder's actual processing clock/new runID will differ on a new reconstruction; reproduce retained metadata explicitly only for byte-replay, never as a new historical capture. Original forecasts are never reissued. Keep old59-label scores alongside the new666explicit-label version; the latter leaves7,430keys unresolved. Their55shared explicit labels are not additional independent outcomes.
