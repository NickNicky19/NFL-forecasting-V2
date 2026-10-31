# Grade the original HGB Week8 shadows

State: software tested with invented labels and an empty-label readback of the real retained capture. No actual Week8 outcome was read or scored. This module performs no fitting, inference, acquisition, scheduling or production write.

Use `nfl_v2.hgb_shadow_grading` and `tools/grade_hgb_week8_shadow.py` for the original `v2-hgb-direct-history-controls-v1` packet. The empirical grader accepts another schema and must not be used by rewriting or reissuing this packet. Absolute-loss points, squared-loss intended means and TD log-loss probabilities keep their original objectives and separate procedure identities. Absolute-loss point forecasts are not authenticated distribution medians. There is no numeric forecast law, bookmaker offer, ROI or website-release claim.

The grader checks trusted compressed-capture, capture-receipt, protocol and binding-manifest hashes; the original full query document and its frozen Week8 membership; execution and run protocol bindings; all three history arms/objectives; original fit and chunk-persistence receipts; exact original chunk rows; retained model and query-feature byte hashes; fitting, feature availability, issuance and persistence clocks; and original abstentions. Model pickles are hashed and decompressed within bounds, **never unpickled or executed**. The original post-prediction issuance clock is retained; a separately unrecorded inference-start clock is not invented. Late owner-input-cutoff status remains explicit even when a forecast precedes kickoff.

First restore original capture artifacts and metadata through the approved private companion, verifying retained receipts. Collect the original metadata bindings once into a fresh private file:

```sh
python tools/grade_hgb_week8_shadow.py prepare-bindings \
  --metadata-root RESTORED_ORIGINAL_HGB_PUBLIC_METADATA_DIRECTORY \
  --output NEW_PRIVATE_BINDINGS_JSON
```

Independently check and retain the emitted binding hash. A newly generated hash alone does not authenticate historical metadata. For the October29 retained capture the independently reviewable bindings hash is `319272d2cce01ed3573817bc5021af70753a50947fa6b7809f5acf32850f0a0b`, capture SHA256 is `9c71eabb7fff13a5cceba6c43246343a10d7f77a3b62184f4ac090959f5a8d67`, protocol SHA256 is `8ea88fc4b558d57f46003aaba20cb10af604998f9a7c17c76eb2fb130215794e`, and original capture-receipt SHA256 is `fca1f0db76e81559fcd7a7669d1d416f2b3842e2c5d027e17ea1921d327d131f`. Preserve these bytes; do not regenerate forecasts or fit models to obtain a passing packet.

After games finish, obtain a separately versioned, permitted qualified-final label packet. The exact label/source/identity/finality/availability contract is shared with [the empirical grader documentation](WEEK8_SHADOW_GRADING.md#label-packet-contract). Labels must match frozen query, player, game and target IDs and exact target contracts. Explicit zero and signed yards are supported; missing values, nonparticipants and unknown states never become zero. Final numeric values require played, completed games and final labels available after kickoff and no later than grading-asof. Official nonnumeric cancellation may precede kickoff. Pending or missing games remain coverage. Supplied source declarations require independent review; software cannot authenticate NFL truth or provider publication times.

```sh
python tools/grade_hgb_week8_shadow.py grade \
  --forecasts ORIGINAL_HGB_CAPTURE_GZIP \
  --capture-receipt ORIGINAL_CAPTURE_RECEIPT_JSON \
  --capture-protocol ORIGINAL_FROZEN_PROTOCOL_JSON \
  --frozen-queries ORIGINAL_HGB_FROZEN_QUERY_DOCUMENT_JSON \
  --capture-bindings VERIFIED_PRIVATE_BINDINGS_JSON \
  --artifact-root RESTORED_ORIGINAL_HGB_PRIVATE_ARTIFACT_DIRECTORY \
  --expected-forecast-sha256 TRUSTED_CAPTURE_HASH \
  --expected-capture-receipt-sha256 TRUSTED_RECEIPT_HASH \
  --expected-protocol-sha256 TRUSTED_PROTOCOL_HASH \
  --expected-bindings-sha256 TRUSTED_BINDINGS_HASH \
  --labels QUALIFIED_PRIVATE_LABEL_PACKET_JSON \
  --run-id NEW_IMMUTABLE_HGB_GRADING_ID \
  --public-output reports/NEW_IMMUTABLE_HGB_GRADING_ID \
  --private-output NEW_PRIVATE_DIRECTORY_OUTSIDE_REPOSITORY
```

Fresh outputs include aggregate `SCORES.json` and `GRADING_RECEIPT.json`, plus private `player-errors.json.gz` retaining every original forecast, abstention and unresolved row. Obtain a separate approved private-store persistence/readback receipt. Partial weeks retain null errors for unscored views, full query coverage and `whole_week_complete=false`. Terminal status refers only to all frozen queries. Preserve all prior versions when source corrections arrive.

Review source semantics and results independently, register the new canonical score artifact, then add it with `python tools/build_test_index.py --additional reports/NEW_IMMUTABLE_HGB_GRADING_ID/SCORES.json`. Query-cohort hashes allow paired comparisons only on identical scored rows, contracts and label bindings. Keep HGB objectives and history arms separate; repeated views are not independent NFL games. Research capture and historical rank grant no production release authority.

Run `python -m unittest tests.test_hgb_shadow_grading -v`. The nine test functions cover empty and partial coverage, signed/zero/count/event math, HGB objective identity, trusted hashes and retained model/chunk binding, complete history matrices, wrong IDs and target outcomes in captures, blocked issuance and abstentions, invalid/future/unfinalized labels, DNP/unknown/missing/cancellation states, chronology/support, cohort hashes, immutable outputs and public/private separation. All test labels are fictional and add zero NFL outcomes.
