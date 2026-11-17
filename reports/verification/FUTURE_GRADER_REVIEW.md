# Independent future-grader review

**PASS after one semantic input-validation correction. No Week 8 outcome source
was opened and no actual Week 8 error or accuracy result was produced.**

Reviewed `nfl_v2/shadow_grading.py`, its CLI, the label contract and tests.
The [independent check](check_future_grader.py) uses separately constructed
invented labels plus the real retained capture with an **empty** label packet.
The corrected receipt is [FUTURE_GRADER_REVIEW.json](FUTURE_GRADER_REVIEW.json);
the initial failed validation finding remains in
[FUTURE_GRADER_REVIEW_INITIAL.json](FUTURE_GRADER_REVIEW_INITIAL.json).

## Real retained bytes, no outcome labels

At **2026-10-29T23:14:49.514653Z**, before the first scheduled kickoff, the
reviewer loaded the original capture, trusted receipt and protocol and supplied
an explicitly empty label packet in memory. It verified:

- 10,416 original output views, 1,951 frozen queries and 30 abstention views;
- **zero scored forecasts**, zero scored player-games and zero scored games;
- all 1,951 query states remain `pending_no_label` and whole-week completion is
  false;
- all **63 aggregate procedure/product views** have n=0 and null MAE/MSE/RMSE/
  bias; all private signed/absolute errors and actuals are null;
- capture, protocol and receipt input hashes are unchanged after the check.

No synthetic zero outcome, zero error, perfect accuracy, future grade directory
or actual NFL scorecard was created. The real-capture check exercised the trusted
compressed/uncompressed/protocol/query hash chain and complete arm/product
matrix without consuming outcomes.

## Invented-fixture checks

Forty independent checks cover manually known count errors, strict versus
inclusive one-count tolerance, Brier, finite and infinite log loss, common
scored-cohort hashes across arms, missing/DNP/unknown/pending handling,
official pre-kickoff cancellation, and rejection of wrong contracts/sources,
unfinished numeric outcomes, fractional count outcomes and future source clocks.
The fixture has invented identities and 2020 dates; it is not NFL evidence.

One initial validation gap was reproduced: an internally rehashed fictional
capture could mark a query `blocked_reason=UNKNOWN_IDENTITY` while its output
still said `ISSUED_SHADOW` with a numeric prediction, and the grader accepted it.
The producer corrected the issued-state validation to reject nonnull query
block reasons or row abstention reasons. The independent malformed-capture
regression now fails closed. The actual trusted Week 8 capture did not contain
that contradiction and was never modified.

The reviewed corrected grader has SHA-256
`8515b932db7cc9652e240aee4fd5177dbef64931a878e262b8f5f132cf1046d4`.
Its producer's expanded thirteen-test suite is a separate software result;
neither suite adds NFL observations or prediction skill.

## Contract and limits

Numeric labels require exact frozen query/player/game/category identity,
matching target contract, qualified source admission, completed game, final
state, verified appearance and finite supported actual value. Omitted labels,
unverified finality, played-missing outcomes, DNP, abstentions and cancellation
remain distinct coverage states. A cancellation may be published before
kickoff but cannot supply a numeric zero. Binary event log losses retain
positive infinity explicitly rather than clipping a wrong zero probability.

All source/finality declarations still require independent source evidence.
The grader checks their syntax, chronology and bindings; a contract ID or
`game_completed=true` assertion does not prove official truth, source licensing
or the actual final revision. A future execution must restore approved original
forecast bytes and retain qualified raw label evidence, input/output hashes,
source clocks, revisions and a new immutable grading run. The private error
output needs its own approved-store restoration receipt.

Conditional-on-appearance scores are not all-player forecasts or sportsbook
settlement. No odds, pick selection, ROI, forecast regeneration, method fitting,
production publication, or scheduled acquisition occurs in this review.
