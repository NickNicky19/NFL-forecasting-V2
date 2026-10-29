# Every test: accuracy and error reporting

Every new forecasting evaluation must save an immutable public-safe aggregate
result and enter the linked test-results index. A method fit, implementation
check, forecast issuance, and scored NFL evaluation remain different records.
Existing frozen sources are never overwritten to update the index.

Each scored view supplies `procedure_id`, version/run identity through its
immutable artifact, `target`, `product_id`, `evaluation_panel_id`, `population`,
explicit seasons/weeks, history and feature-memory policy, evidence tier, scored
`n`, distinct scored games, offered/forecast rows, fallback counts, compatible
metrics, uncertainty, and the recoverable source artifact. Missing fields stay
null with a reason; filenames or prose do not prove dates or coverage.

Numeric forecasts report MAE and preferably MSE/RMSE, signed prediction-minus-
actual bias, P90/P95/max absolute errors, and support/failure/fallback coverage.
Units remain visible. Means, medians, empirical points, and threshold/event
probabilities retain their product identities. Primary displayed-point loss is
MAE; anytime-TD probability primary is Brier, with log loss and prevalence where
supported. Source-reported NLL and CRPS retain their actual definitions rather
than being relabeled unsupported probability laws.

Accuracy means an explicitly defined fraction: exact matches or forecasts
within a registered strict/inclusive tolerance, with numerator and scored
denominator. Supply `exact_rate`, `abs_lt_1`, `abs_le_1`, `abs_lt_5`, `abs_le_5`,
`abs_lt_10`, `abs_le_10` only when actually calculated on that same scored view.
The index preserves reported rates and reconstructs integer numerators from
rate × declared n only when consistent; it labels those as derived aggregate
counts, not a fresh row replay. Rounded rates with unrecoverable counts retain
null numerators and a reason. Unreported precision stays unknown.

Never turn MAE, RMSE, Brier, interval coverage, software pass counts, or a
relative error reduction into generic percent prediction accuracy. Probability
residual tolerances are diagnostic and are not binary classification or pick
accuracy. Actual Over/Under hit rates require a separately registered frozen
decision rule, compatible offers, wins/losses/pushes/voids and a stated
denominator. Error units across categories do not define a shared contest.

Use `python tools/build_test_index.py --additional reports/NEW_IMMUTABLE_RUN/SCORES.json`
to include a future aggregate score list. Existing 4,832 reported views, 66
original replay views and 66 later-label views remain linked separately. IDs
derive from immutable source path and evaluation identity; row ordering and
score formatting do not change them. A correction needs a new run artifact and
a correction link; duplicate evaluation identities fail validation.

Software checks use a separate receipt with `tests_run` and status, or the
explicit fictional/hand-contract check-count fields supported by the adapter.
Include it with `--software-receipt reports/NEW_IMMUTABLE_RUN/SOFTWARE_TESTS.json`.
Software records have no NFL denominator, probability accuracy or target error.
Verification counts involving old data are QA, not additional NFL experiments.
The default index includes retained hand-contract, fictional-history and result-
index software receipts when present; additional receipts append to those.
Positive-infinite log losses are retained through an explicit metric-status
field and null numerical value, never silently replaced by a finite score.
Source counts of infinite NLL rows are carried separately.

The generator validates safe repository-relative artifact paths, method/panel/
product identity, finite metrics, nonnegative losses where mathematically
required, sample counts, precision rates and count consistency. Original
source-specific limitations remain in the linked frozen artifacts. The index
does not independently authenticate source truth, as-of vintages or complete
method/request history. Restricted player rows, raw feeds, credentials and
private storage locators must never enter its public inputs or outputs.

Review [the readable index](../reports/continuation-20261029/TEST_RESULTS_INDEX.md),
filter the CSV by category/panel/product/population/evidence, and inspect the
linked original row before comparison. Output views and alias projections are
not independent learners, fits or NFL observations.

The frozen empirical history diagnostic is included once automatically when its
`history-diagnostic-v1/SEASON_RESULTS_2022_2026.csv` exists. Its 10,154 views use
the separate kind `NEW_EXPERIMENT_CURRENT_VINTAGE_PARTICIPANT_DIAGNOSTIC` and
retain season/week, population, position and fallback dimensions. This is a
retrospective current-vintage statistical-row/participation panel; it must never
be pooled with the issued/replayed forecast panels to declare a winner.
Season/week coverage comes from the bound run receipt. Exact distinct scored
and forecast games come from the independent retained-row game census, whose
prediction hash must match that receipt. The CSV hash must also match the frozen
run output. Missing, duplicate or extra census views fail the build.

Each diagnostic record preserves all original aggregate fields and the
protocol, code, query-membership and prediction hashes, in addition to shared
error/precision fields. Optional position/fallback dimensions do not change
older stable IDs when absent. The compact complete JSON, full CSV and separate
[category CSVs](../reports/continuation-20261029/categories/README.md) contain the
same result views; category exports exclude software receipts. Category counts
are output-view counts, never method or independent-sample counts. Explicit
infinite-score status, coverage and provenance remain available in every export.

Every future scored run writes a new canonical `SCORES.json`, registers that
artifact in `registries/RESULT_ARTIFACTS.json`, and rebuilds the index using
`--additional` or the registered default build. Registered scored JSON artifacts
enter automatically; empirical/HGB special schemas use their named adapters.
The V2 CI workflow checks unit tests, artifact schemas, source
hash freshness and registration/index coverage. It has no schedule, capture,
paid acquisition, NFL model fitting or production-write step. Its estimator API
tests fit only small fictional fixtures. Newly issued forecasts
remain registered as forecasted-unscored with pending-outcome reasons.
