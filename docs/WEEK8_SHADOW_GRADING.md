# Grade immutable Week8 shadows after final outcomes

State: **software implemented and tested on invented fixtures only**. No actual Week8 outcome was read and no Week8 NFL score was produced to prepare this module. It neither acquires outcomes nor runs a model. There is no scheduler, production write, wager, price or ROI calculation.

Once games finish and a permitted source supplies qualified final statistics and participation, use the original captured forecast gzip, its pinned capture receipt and frozen protocol. Restore exact bytes through the approved private companion and authenticate their retained hashes. Do not regenerate predictions. Preserve the original actual issuance, feature cutoff, persistence, horizon, later-than-owner-cutoff flags, history regimes, output functionals and abstentions.

`nfl_v2.shadow_grading` accepts only the captured `v2-week8-empirical-history-shadow-v2` schema. It verifies the trusted capture-receipt SHA256, compressed and uncompressed forecast SHA256, exact protocol bytes, frozen query-membership SHA256, original row/query census and complete three-history/product matrix. Captured numeric forecasts must have valid support and have been issued/persisted before their game's kickoff. The grader retains the original forecasts unchanged.

## Label packet contract

Create a separately versioned private JSON packet with schema `v2-qualified-shadow-labels-v1`, a public-safe `label_version_id`, `source_admissions` and `labels`. IDs must be short public-safe identifiers, not URLs, storage paths, credentials or private locators. No actual label belongs in this public document or repository.

Each source admission supplies:

- `source_id` and `source_tier`, one of `authentic_final_snapshot`, `qualified_asof_reconstruction`, or `current_vintage_final_snapshot`.
- `identity_contract_id`, `statistic_contract_id`, `participation_contract_id`, `finality_contract_id` and `availability_basis_id` pointing to the reviewed source mappings/contracts.

These declarations require actual source evidence outside the grader. Passing software validation does not authenticate provider truth, original publication, license or final revision. Do not admit legacy trimmed-cache omissions as zeros. Explicit complete source zeros are valid only after qualified participation and target support are established.

Each label supplies the exact frozen `query_id`, `player_id`, `game_id` and `target`; its `contract_id`; explicit `actual` (number or null); `state`; boolean `game_completed`; `finality`; admitted `source_id`; optional public-safe `revision_id` or null; and aware `available_utc` and `observed_utc` clocks. Player IDs must match exactly, including null/unknown captured identity; no name, alias or whitespace guessing occurs. A numeric label additionally requires a nonmissing captured player identity.

Allowed states are `played`, `DNP`, `unknown`, `missing`, `played_missing`, `pending`, and `canceled`. Allowed finality values are `final`, `pending`, `unverified`, and `canceled`. Numeric labels require **played, game_completed=true and finality=final**. Noncancellation labels must satisfy **kickoff < available <= observed <= grading-asof** with explicit timezones. A qualified official cancellation uses **state=canceled, finality=canceled, actual=null** and may have **game_completed=false** and a pre-kickoff availability clock, provided **available <= observed <= grading-asof**. It resolves game status and never receives a numeric score. Ordinary pending labels retain the strict post-kickoff clock rule; before then, omit their label records and coverage remains pending automatically. The grading-asof itself cannot be in the future. Unfinalized or future numeric labels fail the packet, rather than silently scoring live statistics. Duplicate query labels, conflicting IDs/contracts, unknown sources and invalid values also fail closed. Corrections require a new label version and fresh grading directory, preserving old scores and source bytes.

Targets use these exact grading contracts, mapped explicitly from the captured target identity without editing the old forecast:

| Target | Required contract_id |
| --- | --- |
| pass_yd | `nfl-official-full-game-pass_yd-v1` |
| pass_td | `nfl-official-full-game-pass_td-v1` |
| pass_cmp | `nfl-official-full-game-pass_cmp-v1` |
| pass_att | `nfl-official-full-game-pass_att-v1` |
| pass_int | `nfl-official-full-game-pass_int-v1` |
| rush_yd | `nfl-official-full-game-rush_yd-v1` |
| rush_att | `nfl-official-full-game-rush_att-v1` |
| rec | `nfl-official-full-game-rec-v1` |
| rec_yd | `nfl-official-full-game-rec_yd-v1` |
| rush_rec_yd | `nfl-official-full-game-rush_rec_yd-v1` |
| anytime_td | `nfl-full-game-rushing-or-receiving-at-least-one-td-v1` |

Numeric contracts are official full-game credited statistics including overtime. Signed yards are retained; counts must be nonnegative integers. Combined yards need complete supported rushing and receiving primitives, not a missing-as-zero sum. Anytime labels are exactly0/1 for at least one **rushing or receiving** touchdown, excluding return/recovery touchdowns; count totals are not probabilities. Chart PPR was not captured by this adapter and is rejected, rather than substituted with old fantasy totals.

The capture did not contain a separately named scoring-contract field. The table is this grading adapter's explicit mapping from its already frozen target/product/source contract, bound by the grading code and score receipt. It is not a retroactive rewrite or claim that the old rows contained these strings. A changed statistical/scoring definition requires another grading version and cannot be called an improvement of the old predictions.

## Coverage, scores and paired comparisons

Every captured forecast row remains in the private error output. An original ABSTAIN stays an abstention. Missing game/query labels remain pending. DNP and canceled records are reported separately and receive no conditional-on-appearance numeric error; unknown, missing and played-missing values remain unresolved. No absence becomes DNP or zero. Finality for one game does not close another game. `whole_week_complete=false` while any frozen query lacks qualified terminal resolution; a true value means all **frozen queries**, not every player/statistic in the NFL, has qualified terminal evidence.

`SCORES.json` contains separate target/history/product views, native MAE/MSE/RMSE/bias/tails and registered strict/inclusive1/5/10 precision, n, distinct scored games, full forecast/abstention/unresolved coverage and source/contract provenance. Anytime primary is Brier, with prevalence and binary log loss. Zero probability assigned to an occurring event retains `log_loss="Infinity"` and an explicit infinite-loss count. Probability residual tolerances are not pick hit rates or classification accuracy. No point output is presented as a full predictive distribution.

Each aggregate retains `frozen_prediction_query_cohort_sha256` and `scored_query_cohort_sha256`, plus capture/protocol/receipt/label-packet hashes and actual capture clocks. Compare history arms only when target, contract, product, label binding and scored cohort match. Means/medians are views of one empirical mechanism; neither they nor repeated histories multiply independent games. The grader estimates no uncertainty or selection gain: paired loss, game/week dependence, selection exposure and the limited population must be reviewed separately.

The public output is aggregate only. Private `player-errors.json.gz` includes all forecast/error/participation states, original prediction and captured context, label source/revision clocks and explicit unresolved reasons. It must live outside the public repository and get a separate approved private-store upload/readback receipt. The grading receipt's initial local-readback status does not establish off-host durability.

## One-time postgame command

Use actual restored input paths and fresh output directories, replacing the uppercase placeholders below. This is a manual, offline operation after qualified final labels exist; do not add or dispatch a capture scheduler.

```sh
python tools/grade_week8_shadow.py \
  --forecasts PRIVATE_CAPTURE_GZIP \
  --capture-receipt PINNED_CAPTURE_RECEIPT_JSON \
  --capture-protocol PINNED_CAPTURE_PROTOCOL_JSON \
  --expected-forecast-sha256 VERIFIED_CAPTURE_SHA256 \
  --expected-capture-receipt-sha256 VERIFIED_RECEIPT_SHA256 \
  --labels QUALIFIED_PRIVATE_LABEL_PACKET_JSON \
  --run-id NEW_IMMUTABLE_GRADING_RUN_ID \
  --public-output reports/NEW_IMMUTABLE_GRADING_RUN_ID \
  --private-output NEW_PRIVATE_DIRECTORY_OUTSIDE_REPOSITORY
```

Default asof is the actual processing time. An optional earlier `--asof-utc` can reproduce a genuine earlier label snapshot, but never authenticates or backdates label availability. Inputs are never overwritten; existing output directories fail closed. First verify the qualified label source/identity/finality semantics independently, then inspect the grading receipt and preserve partial coverage. Later games or corrections use new immutable runs linked to the original.

To update the aggregate index after review, use:

```sh
python tools/build_test_index.py --additional reports/NEW_IMMUTABLE_GRADING_RUN_ID/SCORES.json
```

That preserves the old source artifacts and stable view identities. Do not merge histories, choose a retrospective forecast horizon or treat the new scores as a release/website deployment. No live model switch follows automatically.

## Software validation

Run `python -m unittest discover -s tests -p test_shadow_grading.py -v`.

Thirteen invented-fixture tests cover pending coverage; zero/signed labels and tolerance boundaries; Brier; compressed/receipt/protocol/query integrity; duplicate capture/label rows; wrong IDs/contracts; unfinished/future/naive clocks; invalid count/event support; DNP/unknown/missing; official pre-kickoff cancellation distinct from an unfinished game; abstentions; identical history cohort hashes without merged views; infinite log loss; fresh output directories; private/public separation; index-compatible aggregates; and unchanged input bytes. These are software checks with **zero NFL outcomes**.
