# Actual website consumer readback

At2026-10-31T03:38:58Z the served pointer, forecast payload and two JavaScript assets were byte-identical to the root’s earlier readback. The served board hash also matches the pointer. The current payload contains1,945 forecasts:1,789 future-game values across13 games and156 frozen values for the elapsed first game. No new stat_point_mae_v2 forecast was present. These are existing October28 forecasts, not a new capture.

The audit executed the exact served overlay validate/card/load functions and the exact selectedPropForecast function extracted from the served app. All1,945 values and displayed strings reproduce at a valid-window fixture clock, and all1,945 are renderable at the actual audit clock. The full app, browser DOM and outcome/statistic logic were not run. This verifies consumer-function parity; it is not a browser screenshot or forecast-accuracy test.

| Category | Rows | Future renderable | Frozen | Games |
|---|---:|---:|---:|---:|
| anytime_td | 428 | 395 | 33 | 14 |
| rec | 401 | 369 | 32 | 14 |
| rec_yd | 401 | 369 | 32 | 14 |
| rush_rec_yd | 291 | 267 | 24 | 14 |
| rush_att | 112 | 102 | 10 | 14 |
| rush_yd | 112 | 102 | 10 | 14 |
| pass_att | 40 | 37 | 3 | 14 |
| pass_cmp | 40 | 37 | 3 | 14 |
| pass_int | 40 | 37 | 3 | 14 |
| pass_td | 40 | 37 | 3 | 14 |
| pass_yd | 40 | 37 | 3 | 14 |
| nick-chart-ppr-v1 | 0 | 0 | 0 | 0 |

The wire carries673 numeric count means,844 yardage medians and428 rushing-or-receiving touchdown probabilities. Every method_id is P2_SELECTED. Payload preparation/package clocks, per-row issuance/persistence clock counts, per-game coverage and declared fallback reasons are retained in [the aggregate execution result](CONSUMER_EXECUTION_RESULT.json). No chart-PPR wire product is present.

## Closed contract and rollback checks

Eleven checks passed. The current consumer rejects a count median in its count-mean contract and rejects an extra expected_mean row field. Missing selected rows, expired pregame rows, disabled overlays, mismatched hashes and missing assets preserve fallback behavior. Valid-through-kickoff original forecasts remain frozen after kickoff. Those rejection and rollback examples are labelled software fixtures; no future forecast was changed.

A proposed count-median release therefore needs an owner-controlled compatible producer/consumer wire version. Renaming a mean as a median or adding fields to this closed schema would not pass the current served consumer. This is a demonstrated compatibility requirement, not a new blanket waiting period or a forecast-quality verdict. Admission, publication and any producer changes remain with the retained owner.

## Outcome access and source limits

The audit acquired data/week.json only to hash its bytes and project season/week, player/event identity, category keys and kickoff clocks. The lexical parser skipped141,946 unapproved scalar values without decoding them; no NFL statistic scalar or Week8 outcome was used. A source download and a source hash are distinct from historical-input vintage authentication or football-label verification.

[Frozen checks](FROZEN_PROTOCOL.json) · [Actual HTTP receipts and hashes](FRESH_SERVED_ACQUISITION.json) · [Pinned render inputs and exact function-slice hash](RENDER_INPUT_BINDING.json) · [Metadata-only board receipt](BOARD_METADATA_PROJECTION_RECEIPT.json) · [Every category](CATEGORY_RENDER_STATUS.csv). Portable helpers load privately acquired production bytes; no unlicensed production JavaScript is copied into V2.

No fit, model inference, new forecast/capture, selection change, new scheduler, wager, merge or deployment occurred. The network skill confirmed current unrestricted enforced HTTP policy; the first local socket attempt required the supported explicit network permission, after which the public read succeeded with the normal proxy and TLS verification.
