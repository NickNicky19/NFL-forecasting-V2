# History engine: independent software review

**PASS for the limited supplied-snapshot empirical-control contract. No NFL
history experiment ran, and this review establishes no forecast-skill result.**
The exact source hash and 29 independent fictional checks are recorded in
[HISTORY_ENGINE_CHECKS.json](HISTORY_ENGINE_CHECKS.json); reproduce them with
`python reports/verification/history_review_checks.py`.

The reviewer read `nfl_v2/history.py`, its tests, and the source/adapter contract.
It made no engine edits, fit no model, and inspected no additional NFL outcomes.

## Checked behavior

- All three arms forecast identical frozen query identities. A fictional
  player's prior values 2 (2024), 8 (2025), and 20 (earlier 2026) yield means
  20, 14, and 10 for H-CURRENT, H-RECENT, and H-MULTI. The latter two lower
  medians are 8. These are empirical history controls with no football features,
  learned encodings, calibration, pretrained model, or optimization.
- Replacing the 2024 value by 200 changes only H-MULTI's mean to 76. The
  H-CURRENT and H-RECENT means remain 20 and 14. Strict-current mode consumes
  only the earlier 2026 observation; it has no hidden older fallback.
- With no earlier current-season observations, strict-current mode emits the
  named constant-zero startup fallback for both point products. No record is
  silently dropped. A new FB query is retained with the same named fallback.
- Future/unavailable, cutoff-equality, timezone-naive, target-game, missing-value,
  unknown-participation, unadmitted-source, and duplicate-identity observations
  fail before predictions. Signed numeric yards remain valid.
- Source contract IDs, evidence tiers, admitted targets, evaluation-season
  scope, 2026 Week 1–7 ceiling, and finite origin/row/query/output/candidate-scan
  limits are validated. Concrete output and candidate-scan budget violations
  were independently rejected.

## Found issue, corrected before NFL use

The initial engine returned hashes for the manifest, source-admission prose,
and query membership but no digest of actual observation values. Replacing a
value while keeping its observation ID therefore changed the forecast without
changing any input-binding hash. This was a reproducibility gap.

The executor added `origin_inputs_sha256`, covering the complete canonicalized
origin/query/observation records, plus `policy_run_sha256`, which includes
strict-current mode and the manifest. Independent checks reconstruct the full
input digest separately, confirm changed observation values change it, and
confirm strict-current mode changes the policy digest. The FB population
addition is also verified. These are software corrections, not new accuracy
results.

## Limits and required admission evidence

The engine validates supplied facts; it cannot authenticate them. Source
availability timestamps, complete-statistic contracts, source licenses,
historical position mappings, pregame cohort construction, and a lack of
outcome-driven player selection need recoverable external evidence. A nonempty
source contract string or a SHA-256 value does not establish that evidence.
Queries carry a source and cohort ID but do not independently prove roster or
eligibility publication before cutoff. Those checks remain part of snapshot
admission, before any NFL execution.

Source evidence tiers remain explicitly recorded. Current-vintage reconstruction
cannot be promoted to authentic pregame evidence by using this engine. No
capture/issuance timestamps are fabricated: outputs are `forecasted_unscored`,
without a claim of contemporaneous publication or scoring.

The `empirical_summary_groups` field counts origin × target × arm × product
groups; `forecast_cells` counts individual query products. Neither denotes
optimization fits. Candidate-row checks are an explicit conservative scan
bound, not measured CPU seconds. Real NFL runs still need their sealed finite
resource allocation, actual wall/CPU/memory accounting, environment/code/input
bindings, source admission, matched labels, independent scorer, and approved
durable evidence retention.

This code provides the three core fit-history controls and a strict-current
information policy for that simple mechanism. It does not implement H-DECAY,
H-STATE, strong learned candidates, source acquisition, defense/role/playcalling
features, probabilistic yard/count laws, tuning, selection, scoring, or the
complete tournament. A successful fictional check completes none of those
scientific cells.
