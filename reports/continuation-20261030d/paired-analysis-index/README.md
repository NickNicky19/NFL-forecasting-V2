# Permanent derived-comparison index

[All 18,708 comparisons as CSV](PAIRED_ANALYSES.csv) · [JSON](PAIRED_ANALYSES.json) · [Bound source/row manifest](ANALYSIS_MANIFEST.json).

This index contains 17,100 adjacent-history views and 1,608 carry-robustness views from retained predictions. **17,658 have supported paired losses; 1,050 have no supported paired rows and retain null errors.** It adds zero fits, inferences, forecasts, univariate evaluation views or unique NFL observations. Its registration is separate from the permanent univariate score index.

Each record identifies candidate/product/history, comparator contrast, target, season, population, fallback view, cohort, identical membership hash, sample size, native error, comparator error, absolute/relative loss change, uncertainty status and recoverable source row. A negative change favors the candidate. MSE, MAE and TD Brier keep their different units. Current seven-week intervals remain insufficient under the registered eight-week minimum; game-cluster sensitivity is separate.

Registered precision numerators/denominators remain in the linked source score versions and the [default univariate index](../current-ranking-v2/current-valid-results/README.md). The new paired subsets do not invent per-mask precision percentages. The carry source additionally retains full paired native metrics and fallback contributions. These analyses do not rank actual offers or create a selected-side hit rate.

The [analysis registry](../../../registries/ANALYSIS_ARTIFACTS.json), `tools/check_analysis_index_coverage.py` and CI bind all input/output hashes, row coverage, supported/null states and the separation from new observations. Reproduction uses the original retained prediction inputs and frozen analysis protocols; completed fits are reused.
