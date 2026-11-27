# Independent review: later Week 7 explicit-label extension

**PASS for the narrow source reconstruction and score arithmetic.** The
extension increases recoverable Week 7 coverage without recovering missing
zeros, complete official outcomes, or a valid full-population history test.
Existing one-game replay results remain separate and unchanged.

The reviewer independently read the pinned normalized statistics, completed
schedule, original forecast bytes, and newly reconstructed labels. The
[independent script](check_label_extension.py) imports neither the root scorer
nor its label-builder functions. It independently joins exact identities and
recomputes the eligible labels, followed by 50-digit Decimal loss calculations.
Aggregates, hashes, and redacted examples are in
[LABEL_EXTENSION_REVIEW.json](LABEL_EXTENSION_REVIEW.json).

## Verification scope and results

- **8,096 original player-game-target opportunities:** all reconstructed actual
  values and participation states match the independent source join, across
  16,192 field checks. Exact Sleeper IDs, original embedded Sleeper IDs,
  team/opponent pairs, and kickoff times must agree with the completed schedule.
  Ambiguous/unbound identities remain unresolved. Label source/statistics hashes
  also match the independently hashed supplied source bytes.
- **24,288 original forecasts:** all internal feature-cutoff/issuance/kickoff
  chronology checks pass. There are no duplicate model/player/game/target keys.
  No forecast value is reconstructed, changed, or backdated.
- **666 explicit outcomes**, **190 player-games**, **14 games** support
  **1,998 method-score rows**. Repeated procedure forecasts are not additional
  independent NFL outcomes. The other **7,430 opportunity labels remain null**.
  At least one label in every game does not establish complete Week 7 coverage.
- **66 method/category/population summary cells** match independently computed
  n, MAE, MSE/RMSE, bias, P90/P95/max errors, exact/tolerance rates and, where
  applicable, Brier/log loss and prevalence: **1,008 metric checks** pass.
  Maximum absolute floating-point discrepancy is 3.64e-12 on large metrics,
  within the declared relative/absolute comparison tolerances.
- **1,332 scored method rows use fallback.** The extension does not erase
  fallback contribution or imply every scored result is a learned-player result.

Primary-role passing-yard baseline MAE is **63.878284072249585** on 16 supported
QB outcomes. Primary-role reception MAE is **1.582480982183138** on 157 explicit
reception outcomes. These are examples from the reconstructed selected-label
panel, not comparable replacements for full Weeks 1–6 or Weeks 1–7 leaderboards.

## Sparse-zero and probability limits

Every supported primitive value is nonzero. Signed negative production is
retained: five receiving-yard and three rushing-yard labels are negative.
The underlying normalization drops zero/falsey fields, so omission cannot prove
zero receptions, touchdowns, interceptions, carries, or yards. The independently
recomputed label logic leaves omitted primitives and incomplete combined yards
null. No new source-completeness contract was inferred from a cache file.

All **49 anytime-TD labels are positive**; the primary-role subset has 46
positive labels and no supported negative events. Its baseline Brier score
**0.637885522692441** describes that selected positive-event subset. It cannot
support representative probability skill, reliability, calibration, prevalence,
or sportsbook return claims. No offers, odds or pick selections were scored.

The later view requires exact qualified namespace bindings. Relative to the
original 605-record one-game label batch, 55 explicit values agree exactly,
546 remain null, and four formerly explicit labels (two receptions and two
receiving-yard labels) are null under this stricter later-source identity
qualification. Their reason is `unverified_identity_namespace`; they are not
silently overwritten or treated as source-statistic corrections. No numeric
disagreement occurs on the 55 supported overlapping labels.

On this later-label panel the paired recent and pooled baseline losses are
identical. That is an observation about the retained recipes and fallbacks,
not evidence for equal H-CURRENT/H-RECENT/H-MULTI performance. Those regimes
have not been isolated with a common fitted learner on this panel.

## A reproduced win and loss

Opaque example `0dad213a36286cb5`, receiving yards: the retained
ridge-without-team challenger has absolute loss **1.893184099253055**, versus
recent baseline **11.998906147451322**. Challenger minus recent is
**−10.105722048198267**, a win.

Opaque example `46f73409791db5a3`, receptions: ridge-without-opponent has
absolute loss **0.6778240159056614**, versus recent **0.204878582367097**.
The difference is **+0.4729454335385644**, a loss. Both examples are arithmetic
checks on retained original points, not selection policies or independent fits.

## Evidence boundary

The values come from a later same-provider production-normalized snapshot,
matched to completed ESPN schedule records. This verifies reproducible source
mapping and arithmetic; it does not independently authenticate official NFL
truth, provider revision timestamps, complete played-zero coverage, or original
historical outcome capture. One evaluation week and outcome-dependent missingness
do not justify a generalization claim or ordinary week-cluster interval.

This review creates **zero fits and zero new forecasts**. It does not combine
the reconstructed sparse-label panel with the original one-game replay or the
separate Weeks 1–6 research panel. Reproduce with
`python reports/verification/check_label_extension.py APPROVED_PRIVATE_INPUT_DIR`;
the directory must supply the original approved source bytes listed in the
script. No private locator, credential, download, or production action is implied.
