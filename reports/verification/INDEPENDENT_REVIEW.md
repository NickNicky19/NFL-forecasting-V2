# Independent read-only verification

The retained one-game arithmetic passes the checks below. This review found and
the executor corrected one input-validation defect. It does not establish the
best history window, complete Weeks 1–7 coverage, source truth, or live readiness.

The reviewing agent performed no fits, issued no forecasts, and changed no
upstream, production, scheduler, or shared ledger. Its only writes are in this
verification directory. Exact reviewed code hashes are retained in
[PRIMARY_COMPARISON.json](PRIMARY_COMPARISON.json).

## Recomputed evidence

The standard-library [independent replay](independent_replay.py) imports no V2
scorer or upstream research code. It decodes the supplied retained prediction
and label bytes, joins exact game/player/target identities, restricts primary
roles identically, and computes losses using 50-digit Decimal arithmetic.

- 24,288 forecast rows span 14 games and 736 distinct player IDs. They are not
  24,288 independent outcomes.
- The retained label batch contains 605 target records for **one game** and
  55 player IDs. Only 59 player-game-target outcomes are nonmissing, across
  16 player-games. Primary roles retain 52 supported target outcomes.
- There are no duplicate exact forecast identities or label identities. All
  forecasts satisfy their internal feature-cutoff ≤ issuance < kickoff clocks.
- All 33 primary-role method/category summaries match the executor's separately
  computed summary artifact: **132 n/MAE/MSE/bias checks**. Maximum absolute
  floating-point discrepancy is 2.274e-13. Eleven recent/pooled comparisons
  and eleven additional challenger/recent comparisons were independently
  calculated. These are summary/QA counts, not new experiments or fits.
- Thirty-six hand-worked contract checks pass: the signed chart-score example,
  missing components, invalid touchdown counts, exact/inclusive tolerances,
  quantiles, Over/Under/push complement, mirrored Brier/log loss, refund-on-push
  expected net, and win/loss/push/void/unknown/DNP settlement behavior.

Recent versus pooled reception MAE is 1.825562142287194 versus
1.837147513271493 (n=12); receiving-yard MAE is 31.840046255089155 versus
32.160548557789007 (n=12). Other primary baseline categories tie on the retained
rows. Distinct legacy recipes and their shared fallbacks are not isolated
H-CURRENT/H-RECENT/H-MULTI fit-window experiments.

The anytime-TD primary-role batch has only five supported labels, **all positive**;
its Brier score 0.647942977150304 cannot estimate representative prevalence,
calibration, or full-population skill. Missing zero labels must remain missing.
All quoted losses are conditional on the narrow retained explicit-label subset.
One game/week cannot support a useful cluster interval or general superiority.

## Independently checked win and loss

Opaque example `dc43e26628f09f11`, receptions: the retained
ridge-without-opponent challenger absolute loss is 4.388143292820415, versus
recent loss 4.3975607088164517; challenger minus recent is
−0.0094174159960367, a small win.

Opaque example `8eb8e46f1358a971`, same target/procedure on another player-game:
challenger loss is 1.8673607946577317 versus recent 0.3317051991750786;
the difference is +1.5356555954826531, a loss. Exact raw identities remain in
the supplied source evidence. These redacted examples preserve adverse results;
their opaque hashes are not private artifact locators.

## Scorer defect and correction

The initial `anytime_td` helper accepted fractional counts and a positive count
paired with an invalid negative count: `anytime_td(.5,0)` and
`anytime_td(1,-1)` returned one. The executor now validates every nonmissing
component as a finite nonnegative integer before accepting a positive event.
Both reproductions and the valid-positive/missing-counterpart case now pass.
This is input validation, not a forecast accuracy improvement.

The exact chart example is 10+8−1−0.4+6+5+4+6−1+6+24 = **66.6**. It includes
signed rushing yards, all three credited two-point conversions, one unique
fumble lost, one offensive recovery TD, and three separate return TD types.
This verifies arithmetic on explicitly constructed components, not real-event
source mapping or absence of overlapping provider aggregates.

## Chronology and leakage boundary

The public Git path history reports addition commit
`ae2f893d6fa731b0199df11b5bdb4dc083c1072c`, with author and committer dates
2026-10-22T12:51:57Z and exact forecast blob
`83d457f968d080ec91d68e830e58b24108554c52`. The retained forecast gzip has
SHA-256 `955425791a79b9f279f8a6cf94d55efa9f80825227d49e1eccf026614b5f75a7`.
The retained producer receipt cites that commit and remote readback at
12:51:59.543487Z, zero late rows. Those dates precede the first target kickoff,
2026-10-23T00:15Z. The Git commit is unsigned and has no parents.

This corroborates a retained **recorded-pregame** batch, with consistent
internal/publication clocks and byte identity. Git author/committer dates and
producer receipts do not independently attest server push time or provider
publication/vintage. Source hashes alone do not prove training exclusion or
source correctness. No training inputs/models were independently refitted or
fully audited here. Those leakage/source-truth aspects remain **UNKNOWN**.

The production weekly JSON inspected separately contains final statistics and
thresholds. It does not by itself authenticate pregame forecasts, bookmaker
prices, jurisdiction, capture time, or original pick membership. Missing
statistics are not zeros. Public production sparse-zero scoring and old PPR
arithmetic must not be reused as the chart-label contract.

## Settlement example

For masses P(0)=0.5, P(1)=0.3, P(2)=0.2: at line 0.5 the Over/Under
probabilities are 0.5/0.5 and push is zero. At line 1 they are 0.2/0.5,
with push 0.3; they sum to one. At decimal odds 4, refund-on-push expected net
is 0.2×3−0.5 = **0.1 units**. Conditional-on-decisive probabilities must be
multiplied by decisive mass 0.7 before comparing with this unconditional EV.
This synthetic contract test establishes no observed betting return.

Run `python reports/verification/independent_replay.py FORECAST_GZIP OUTCOME_WRAPPERS --output reports/verification/INDEPENDENT_REPLAY.json`,
then `python reports/verification/check_primary.py` after the executor's replay.
The first two arguments require approved original source bytes; no download,
credential, scheduler, or private-store access is assumed by these scripts.
