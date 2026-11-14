# Permanent test results: current index

47,398 records: 47,379 evaluation views and 19 software receipts. Views are not distinct methods or independent NFL samples.

[Filterable CSV parts](CSV_FILES.md) · [Sharded JSON manifest](INDEX_MANIFEST.json) · [Previous immutable checkpoint](../../continuation-20261030/results-index/README.md)

All earlier IDs and losses remain. New registrations retain procedure/history/product, exact panel/population and cohort, dates, denominators, native errors, defined tolerance accuracy, fallback/coverage, uncertainty and recoverable source links. Inspect source aggregate fields for exact cohort and source semantics. Unknowns remain null with reasons. Numeric errors do not become percentage accuracy. Software checks add no NFL observations.

Compare identical games, source vintages, information cutoffs, products and membership. Historical participant panels, original future captures, later partial-week captures and offered-price panels stay distinct. No hindsight-selected winner is credited as a live selector.

CSV comparison columns show the explicit comparator, paired denominator, candidate-minus-comparator error and relative change. Negative change favors the candidate. A relative change is not accuracy. Null comparisons remain UNESTABLISHED with a reason, including unmatched historical website references. Fallback rate uses the declared forecast-row denominator. Precision columns preserve their exact numerator/denominator and strict/inclusive definitions. Scoring corrections are labeled separately from prediction changes.

| Category | Evaluation views |
|---|---:|
| [anytime_td](categories/anytime_td.csv) | 2,918 |
| [nick-chart-ppr-v1](categories/nick-chart-ppr-v1.csv) | 3,147 |
| [pass_att](categories/pass_att.csv) | 2,965 |
| [pass_cmp](categories/pass_cmp.csv) | 2,921 |
| [pass_int](categories/pass_int.csv) | 2,959 |
| [pass_td](categories/pass_td.csv) | 2,937 |
| [pass_yd](categories/pass_yd.csv) | 2,659 |
| [rec](categories/rec.csv) | 5,533 |
| [rec_yd](categories/rec_yd.csv) | 5,001 |
| [rush_att](categories/rush_att.csv) | 6,203 |
| [rush_rec_yd](categories/rush_rec_yd.csv) | 4,998 |
| [rush_yd](categories/rush_yd.csv) | 5,138 |

Register each new immutable `SCORES.json` or software receipt in `registries/RESULT_ARTIFACTS.json`, run `python tools/build_test_index_v2.py`, and run `python tools/check_result_index_coverage.py`. Each JSON shard stays below12MiB; the old checkpoint is preserved.
