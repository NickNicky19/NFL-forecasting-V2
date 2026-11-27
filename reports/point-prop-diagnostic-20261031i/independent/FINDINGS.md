# Independent point/prop diagnostic findings

The weak results reproduce. HGB absolute-error H-MULTI passing yards wins 28/80 selected directions, including 14/48 selected Unders. D1 H-MULTI lower-median completions wins 33/76. The retained engine uses the offered threshold correctly; this audit found no rounding, selected-side grouping or prediction-versus-actual grading error in these cases.

## Same offered rows, different products

| Category / focal procedure | Qualified / outer thresholds | Focal MAE | Signed bias | Saved raw-control MAE | Saved adjusted-control MAE | Focal Over W/L | Focal Under W/L | Focal Combined W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Passing yards / HGB absolute-error H-MULTI | 80/84 | 60.082677 | -17.851730 | 51.504625 | 53.762250 | 14/18 | 14/34 | 28/52 |
| Completions / D1 lower-median H-MULTI | 76/84 | 5.052632 | -1.605263 | 4.770526 | 4.465132 | 11/12 | 22/31 | 33/43 |

These are the exact common qualified offer rows for each focal and its retained raw/adjusted controls. The two category masks differ. The controls retain their saved precision and incomplete model metadata; they are not authenticated reconstructions of the current served website or a known provider algorithm.

On passing yards, raw-control minus HGB MAE is -8.578052 yards, with a descriptive game-cluster normal 95% sensitivity interval [-15.577013,-1.579091]. On completions, adjusted-control minus D1 MAE is -0.587500 completions, interval [-1.021055,-0.153945]. These intervals have only three exposed weeks behind them and do not adjust for selecting among many tested procedures.

The passing-yard point averages 11.089230 yards below the retained line, while actual production averages 6.762500 yards above it. The completions point averages 0.973684 below the line, while actual completions average 0.631579 above. These differences reproduce the negative signed bias. They describe this panel; they do not justify an outcome-chosen offset or inverted selection rule.

The retained mean alternatives do not provide a demonstrated repair. HGB squared-error mean has MAE 60.231811 and 31/80 correct directions on the same 80 passing-yard rows, versus 60.082677 and 28/80 for absolute loss. The paired MAE difference is +0.149135, with game sensitivity interval [-1.482507,1.780776]. D1 completions mean has MAE 5.149491 versus lower-median 5.052632 on the same 76 rows; both select 33/76 correct directions. Its paired MAE difference is +0.096859, interval [-0.067263,0.260982]. This does not isolate a universally superior functional or establish that mean/median choice alone caused the failures.

The full Weeks 1–7 participant-panel MAE ranking remains a different comparison. A numerical champion on that panel is not automatically the best threshold-direction procedure on the qualified Weeks 5–7 offers. No probability distribution, confidence score, EV or sportsbook return is inferred from either focal point output.

## Population selection does not tell a simple causal story

The following holds each focal's original saved kickoff forecast fixed and restricts the same 42 source-covered games:

| Focal | Broad qualified QB player-games: n / MAE / bias | Offered-player subset: n / MAE / bias | Earlier-decision-qualified subset: n / MAE / bias |
|---|---|---|---|
| HGB passing yards | 94 /65.141912 /-5.004075 | 84 /59.923517 /-14.299728 | 80 /60.082677 /-17.851730 |
| D1 completions | 94 /5.393617 /-0.585106 | 84 /4.952381 /-1.690476 | 76 /5.052632 /-1.605263 |

Restricting to offered players lowers MAE here, while making bias more negative. It would be incorrect to report that the offered-player restriction raised MAE or that backup zeros caused these losses. The ten additional unoffered QB player-games have no frozen pregame replacement-role classification in this diagnostic. HGB has no fallback in these subsets. D1 has one fallback in the broad 94-row view and none in either offered subset. Fallback therefore does not explain the qualified focal failures.

HGB is a direct absolute-error fit. D1's lower median is extracted from its ordered empirical leaf law, whose partitions use squared-error fitting plus the original 5% prior. These functional and learner differences remain explicit. D1 uses the four observed opponent-position groups, not the separately requested scheduled-team-game windows.

## What was independently checked

[The numerical verification receipt](POINT_OFFER_INDEPENDENT_REVIEW_V1.json) binds the frozen protocol and unchanged score bytes. Separately written calculations checked 3,024 retained recipe/offer rows against original frozen plans and grades, 188 focal broad-population rows against the original forecast packets, all 69 numerical/gap/precision views, 189 side views, 63 side partitions, 68 paired MAE contrasts, 189 game-bootstrap intervals and eight privately retained worked win/loss examples. Reconstructed model points use `ranking_point`; the inherited `prediction` field is the adjusted-site control, and `raw_prediction` is the raw control. Source identity, line, label, decision clock and fallback membership match on paired rows.

An initial verifier equality check included the diagnostic wrapper's `recipe` key when comparing a worked example to its source row. The source example intentionally has no wrapper key. The verifier was corrected to compare every underlying row field; its initial checker bytes are retained. No source calculation changed.

The I side arrays initially inherited a generic source-vintage string that could incorrectly describe reconstructed V2 points as original/server-retained points. This is a metadata defect, separate from the verified calculations. The original bytes must remain retained and the corrected, source-bound default projection must be verified before those rows are presented as current evidence. No original V2 issuance is authenticated by this diagnostic.

## Earlier-source claims

[The A–E coverage review](SOURCE_COVERAGE_INDEPENDENT_REVIEW.json) independently checked 23 pinned public code/document byte and Git-blob bindings across nine requested periods. Normalized quote time is explicitly NULL; `last_updated` is a naive collection clock; the offer driver sets a reconstructed kickoff query cutoff. None of these establishes a pregame quote or original selection clock.

A newly identified readable ZIP is reported as 11,137,356 bytes, with 204,431 prediction/actual CSV rows and 258,748 direction CSV rows. These remain public-receipt claims; the private CSV headers, inner member bytes and approved restoration route have not been independently recovered. Existing normalized 2022,2023,2024 and 2026 capsule references total 9,401,788 distinct container bytes. A reported absence of named-book pairs in 2022 does not prove absence of single-sided lines; the inspected 2025 study exclusion does not prove all 2025 offers are absent.

No new authenticated original-selection or timing-qualified earlier-offer panel was established. Existing football predictions and labels remain useful for saved-row analysis, with their exact library, history and recovery limitations. The next source dependency is the exact owner-approved export and metadata/contract restoration, followed by a separately named diagnostic if timing remains unqualified. Missing original issuance must not be manufactured from reconstructed directions.

No fits, model inference, new forecasts, Week 8 outcome reading, production changes or external owner actions were performed by this independent verifier.

## Resolved reporting corrections

[The corrected default metadata passes](REPORTING_METADATA_INDEPENDENT_REVIEW_V2.json). All 189 side-row vintage labels now distinguish reconstructed V2 points from retained saved controls; the 69 numerical rows also receive their explicit information tier. The canonical score SHA remains `474039013174339b056a65ca046d1dfa1290887d820eda724a07fb9bb16c70c7`.

The independent review also found two context-coverage errors caused by deduplication: the focal numerical records were first emitted on conditional comparator masks, so their canonical outer counts were 76 and 80. Their later full-system aliases initially copied those denominators and incorrectly showed 100% coverage. The retained V1 extension is superseded by V2 for current reporting: D1 completions is 76/84, with eight unavailable forecasts; HGB passing yards is 80/84, with four unavailable. All 178 context mappings now reconcile. The conditional source-record denominators and every point, metric and selection count remain unchanged.

[Exact paired-mask bindings](PAIRED_MASK_BINDINGS_V1.json) connect all 68 existing MAE comparisons to their candidate and focal subset point records, with membership, identity/label/cutoff hashes and support. Full-system, common-mask and known-nonfallback contexts remain different views of retained observations, not additional fits or independent NFL games.

The privately retained 92,891-byte diagnostic derivative and eight worked examples were verified locally. This review does not claim a completed off-host backup or access to the newly reported owner ZIP. Final root index/report/pointer bindings are checked separately after sealing.

## Startup, history and execution readiness

The four older-season startup waves pass independent checks of all 10,968 recipe/window/origin identities, sample counts, outcome membership and learned/fallback partitions. All 3,656 full-system window losses reproduce from the previously retained weekly summaries. A separate balanced raw replay covers 63 of 457 recipes per season, all twelve targets and 1,512 numerical/precision views across four seasons; this is not a claim that every conditional raw loss was independently recomputed. The [2022](STARTUP_2022_INDEPENDENT_REVIEW.json), [2023](STARTUP_2023_INDEPENDENT_REVIEW.json), [2024](STARTUP_2024_INDEPENDENT_REVIEW.json) and [2025](STARTUP_2025_INDEPENDENT_REVIEW.json) receipts retain the exact scope. The 2022 source covers 271 games, while the other three cover 272 each. These are reused observations, not new NFL games.

On the fixed 2025 Leaf passing-yard control, early CURRENT MAE is 135.326923 with 117 fallback forecasts among 156, versus MULTI 75.634615 with nine fallbacks. Later CURRENT is 72.606299 versus MULTI 68.783465, both with ten fallbacks among 508. Conversely the same 2025 interception median favors CURRENT: early 0.557692 versus MULTI 0.615385, later 0.557087 versus 0.574803. The common full-system rows support these target-specific comparisons; the procedures' own learned-only subsets do not establish a common-learned history effect. The 2022 RECENT arm remains the original source-limited proxy, with no authenticated 2021 extension silently inserted.

The separate current-season wave also passes all 3,936 identity/count/membership and disjoint-origin checks, all 656 full-period native count/loss checks and all 252 unchanged registered policy choices. An independently calculated raw subset covers 107 recipes, including all 36 policies and chart lower medians, in 642 views. Windows are Weeks 1–4 and 5–7, and no Week 8 rows were read. The current-score selector consumes H-MULTI football forecasts and does not become strict-current information merely because its score memory uses 2026.

An extra precision check found nine full-period tolerance-numerator disagreements in the three chart-policy outputs. The original startup adapter passed destination product `point_choice_policy` to a helper that applies exact 0.02-grid arithmetic only to underlying `lower_median` products. Counts and numerical losses agree; the fixed 620 recipe outputs are unaffected. [The original finding](CURRENT_STARTUP_V2_PRECISION_FINDING.json) and [preserved-version review](STARTUP_2026_INDEPENDENT_REVIEW_V2_PRESERVED.json) remain audit evidence. The corrected precision version and current default must be verified separately; changing tolerance arithmetic is a scoring correction, not predictive improvement.

[The eighteen corrected precision versions now pass](CURRENT_STARTUP_PRECISION_V3_INDEPENDENT_REVIEW.json) against that separately calculated raw witness. Fifteen records change 32 precision counters; all 21 full-period chart-policy precision sums agree with the accepted selector references. Every native loss, sample count, membership and fallback field remains unchanged. The original 3,936-record score array remains byte-identical. Current default inclusion and the append index are checked separately.

All 4,608 declared full-system empirical comparisons pass exact target, history, season, window, outcome-label-index and membership-mask checks. [The comparison review](STARTUP_COMPARISON_ANNOTATIONS_INDEPENDENT_REVIEW.json) verifies candidate/comparator orientation and explicit absence of a newly computed paired interval. Different registered feature memory makes these procedure-plus-information references, not isolated learner-effect tests.

[The D1/D2 readiness audit](DEFENSE_READINESS_INDEPENDENT_REVIEW.json) verifies the seasonal adapter's source filtering and scheduled absent-group behavior with a separately written synthetic boundary fixture. It closes zero NFL fit cells. The 5,184 computationally unique requests and 13,248 planned output-week views are per window procedure, not completed fits; the 2022 RECENT alias still denotes the proxy. Exact older D1/D2 execution, recoverable archives and owner integration remain separate dependencies.

## Final append-index verification

[The final I index V3 passes](FINAL_INDEX_V3_INDEPENDENT_REVIEW.json): 557,815 retained records in 407 JSON shards and 58 CSV parts. All 450 H shard/CSV files were rehashed unchanged, preserving 542,633 prior records. All 15,182 appended records match canonical source identities and the new CSV cells; 14,991 numerical views expose their exact precision numerators, denominators and rates. Zero-support precision stays N/A. The audit retains all eighteen original chart scoring versions, while the current startup default uses exactly eighteen replacements and 3,936 views. The default preserves all 4,608 eligible startup empirical comparisons, including the six corrected full-system records.

Two unpublished staging indexes remain retained. V1 lost nested-only precision in its searchable fields despite keeping the original source counts; V2 exposed the precision but omitted six valid references on the corrected versions. Both are reporting defects, separate from forecast or loss changes. V3 resolves them without altering the accepted H prefix or canonical score bytes. An initial independent CSV checker also assumed software verification rows had forecasting procedure IDs; its failed checker bytes and receipt remain retained, and the final verifier correctly treats those software identities as null.

The two software-version records, overlapping recipe/output/window views and repeated shared outcomes are not additional fitted models, NFL games or original selections. Final publication and current pointer/report bindings are separate from this local byte/calculation verification and remain the primary executor's responsibility.
