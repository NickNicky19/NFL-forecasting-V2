# Independent QA: new Week 8 research shadows

**PASS for immutable input binding, declared empirical calculations and recorded
pregame persistence.** The first-game shadows missed the owner's input cutoff;
the late status is correctly retained. No Week 8 outcomes were read or scored.

The [independent checker](check_week8_shadow.py) does not call the capture
adapter or benchmark engine. It reads already retained snapshots, reconstructs
the one-to-one identity bridge and selected arithmetic prefixes, and writes
only aggregate QA. Detailed counts/hashes are in
[WEEK8_SHADOW_INDEPENDENT_QA.json](WEEK8_SHADOW_INDEPENDENT_QA.json).

- Verified all **eight source hashes**, frozen feed/board hashes, full query
  membership hash, capture/protocol/helper-code hashes, compressed forecast
  hash and uncompressed readback hash.
- Reconstructed all **1,951 query bindings**, including qualified bijective
  Sleeper–GSIS mappings, registry presence, board position/team/opponent and
  schedule kickoff. **13,657 query checks** pass. No names or future outcomes
  resolve identities. Six missing/ambiguous board contexts retain abstention.
- All queries retain all three history arms and their registered products:
  numeric empirical mean/lower median, or one anytime-TD empirical probability.
  There are **10,386 issued output views and 30 abstention views**. They are
  one empirical method family, not 10,416 independent methods or NFL outcomes.
- **62,496 clock checks** pass. Feature origin is
  **2026-10-29T22:51:31.887165Z**; persistence completed
  **22:51:33.833766Z**, before every issued target kickoff. Issuance is bracketed
  by the real inference window. No row contains an actual/outcome/label field.
- **424 raw-prefix checks** independently verify sampled means, lower medians,
  anytime probabilities, own-history and position fallback, used counts,
  history-year membership and strict earlier availability across all three arms.
  The 959 source rows unavailable at the origin were independently excluded.
  No 2026 Week 8 outcome enters any inspected prefix.

**837 CAR–GB output views are later than the owner's T-minus-90-minute input
cutoff.** The earliest horizon is approximately **83 minutes 26 seconds**.
Those rows say `LATER_THAN_OWNER_INPUT_CUTOFF`; the remaining 9,549 issued
views are before their owner cutoffs. Pregame persistence does not turn the
late first-game rows into timely owner-qualified T-minus-90 forecasts.

Blocked identities have null predictions, fallback and support counts, with an
explicit abstention reason. No unknown identity receives a disguised historical
player forecast. All anytime probabilities are in [0,1]; numeric outputs retain
their actual mean/median recipes. The public procedure matrix matches every
retained output view exactly.

This is new research shadow issuance using the existing frozen feed population.
It is not official shared capture, proof of game-day appearance, new complex
challenger admission, website publication or predictive skill. The current
identity snapshots are real retained inputs; older statistics remain a
current-vintage reconstruction under an assumed seven-day lag. The chart-PPR
and complex-method gaps remain explicit.

The checker also independently inspected the executor's fresh downloaded private
companion, safe artifact ID **V2-PRIVATE-WEEK8-0001**. Archive SHA-256 is
`3bf5ea98796c59f71d5974e10bbc2f88dcfebfe15a51c4403f2642a1d25e57b0`;
all ten checked query/prediction/feed/board/identity/code/protocol/receipt members
match their bindings. The restored prediction gzip is 329,556 bytes, SHA-256
`b825c8fc436c71939d45d56f387a1e6a304a29072963f97c0f11d07e6770b7f6`.
Private-store ownership and sharing permissions are separately attested by the
executor's private-store receipt; a digest alone does not prove them. This
postcapture restoration does not change issuance times or late-owner-cutoff tags.
No production scheduler, owner lease, original forecast or website was changed.
