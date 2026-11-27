# B — exact website interception population and presence audit

**The reported 46 missing outcomes are reproduced exactly.** At actual website main `689bc6ff11c7424d5384324e5a7d25dc6e0fad9a`, W5–9 contain 86 saved QB interception leans with verified participation, including 46 absent `pass_int` fields and 40 explicit positive values. There are no explicit zeros or null `pass_int` entries in this selected source population. Participation does not establish a zero. Root's independent official-source regrade is a separate version.

Current served `track_record.json` matches main bytes exactly and publishes **33 wins, seven losses, 40 decided, 46 unresolved** for these W5–9 category leans. That 82.5% is the observed result on the known-label subset; it is not whole-board accuracy. The source gap must be reported alongside it. The three separate Top Picks interception selections are all Overs and are currently unresolved.

| Week | Eligible DK-tagged board | Saved Over / Under | Selected | Abstained | Explicit positive | Absent statistic | Current published W–L / decided |
|---|---:|---:|---:|---:|---:|---:|---|
| 5 | 30 | 15 / 5 | 20 | 10 | 6 | 14 | 5–1 / 6 |
| 6 | 28 | 13 / 4 | 17 | 11 | 8 | 9 | 6–2 / 8 |
| 7 | 28 | 9 / 6 | 15 | 13 | 7 | 8 | 7–0 / 7 |
| 8 | 28 | 12 / 4 | 16 | 12 | 10 | 6 | 7–3 / 10 |
| 9 | 30 | 16 / 2 | 18 | 12 | 9 | 9 | 8–1 / 9 |

The complete saved prop population contains 197 pass-int props: **144 DK-tagged real-line rows and 53 internal/reference thresholds**. The real-line board has 144 unique QB-games across 72 games; the 86 selected leans cover 61 games. All 144 real-line rows have finite saved raw and adjusted projections and source=model, including all 58 unselected rows. Preserve those 58 missing saved leans as archive-policy abstentions, not failed technical forecasts. [Availability check](FORECAST_AVAILABILITY_V1.json). Selected thresholds are 85 at 0.5 and one at 1.5. No price, venue settlement or authenticated jurisdiction was supplied.

Ten independent checks per selected row—860 total—validate QB role, exact source player/team/opponent, game membership, source season/week, preserved original statistics, positive participation, real-line/non-late status and valid side/threshold. Finality comes separately from same-head `output/data/weeks` game records: the compact forecast archives do not themselves retain final-state fields. All 72 source games are explicitly post/completed in those weekly records. Raw rows, lines and source records remain owner-local. [Counts/hashes and exact source bindings](WEBSITE_POPULATION_AND_PRESENCE_V1.json).

The active main grader `statistical-presence-strict-v5-20261106` preserves absent, explicit null, invalid, reported zero and reported positive states. It requires participation and then returns unresolved when the individual statistic is missing. This checked path has no missing-to-zero defect. It has a source-evidence gap; qualified official reported values can close that gap with appended grading versions without changing any forecast or side. No blanket sparse-zero rule follows.

The substantive PR #1 head `81c3fc2a612ced916f4c54814f978c509058bca5` is a different, unmerged contract. Its presence version is `nfl-data-presence-v2`, while main uses `nfl-data-presence-strict-v3`. Its unversioned `component({'gp':1,'pass_att':30}, 'pass_int')` still produces an explicitly labeled inferred legacy zero; main produces unknown. Explicit null remains unknown in both. Same ASTs in selected grade functions do not imply runtime parity, because `_bound_stats` consults the differing version constant. The PR report's source patterns also omit strict-v3 cache files. Do not substitute this older branch/report generator for the active main grader or call it proof of current contamination. [Actual code comparison](EXECUTING_CODE_COMPARISON_V1.json), [bounded actual-function fixtures](PASS_INT_PRESENCE_FIXTURES_V1.json).

Twelve content-addressed published grading-history objects were retained and inspected. A full earlier v3 W5–8 record preserves 9/20, 8/17, 13/15 and 8/16 category outcomes; earlier partial records remain separate. No complete old v3 W9 interception grade was located. A counterfactual old-grader execution must not be presented as an originally published W5–9 record. Main's separate `original_recorded_leans_report.json` is an older W4–8 report bound to snapshot `1ec93...`; its old table cannot stand for this current W5–9 population. Both that older report and the current track record were retrieved as exact served bytes. [Served readback](SERVED_GRADING_READBACK_V1.json).

Archive `saved_at` clocks are after games; `late:false` is insufficient pregame issuance evidence. These remain saved-side/saved-line records with timing limitations. The quote tag does not authenticate original bookmaker observation time, and recovering final outcomes does not authenticate forecast chronology. No numerical point is relabeled as probability or confidence; exact model/fallback identity is not invented where the legacy archive omits it. Five calendar weeks of mixed saved category records do not automatically qualify a newly bound exact procedure or change production admission.

This package performs no fitting, forecasting, source mutation, live grading change, common-evaluator replacement or production write. Root independently recomputes original/corrected side counts using qualified official outcomes; C admits the scoped contribution and the original website owner controls any append-only grading publication.

Independent Decimal replay of only the explicit current source values reproduces every published W5–9 aggregate and the separate Over/Under totals, with all 46 absent fields retained unknown. [Published-side arithmetic](PUBLISHED_V5_SIDE_ARITHMETIC_V1.json). This is an independent check of the existing measurement, not a new forecasting experiment.

## Independent corrected measurement verification

The second verifier uses only standard-library Decimal arithmetic, without importing the root grader. It reproduces all eight owner-local strategy hashes and all 144 week/side/full aggregate views from the immutable 144-row board, unchanged 86 saved sides/lines, and qualified dual-source final labels. All input memberships and selected sides/lines match.

The corrected record is **Over 33–32/65; Under 14–7/21; combined 47–39/86 (54.65%)**. Same-case constant Over is **40–46/86**, and constant Under is **46–40/86**; the stored policy leads the latter by only one win, not a demonstrated superiority claim. The separate full-144 controls are 73–71 Over and 71–73 Under. The three native Top Over flags become **0–3/3**. Changes are 32 unknowns→loss, 14 unknowns→win, with all original 33 wins and seven losses unchanged. These are source-supported measurement corrections, not better forecasts. [Independent corrected-grade receipt](INDEPENDENT_CORRECTED_GRADE_REVIEW_V1.json), [portable verifier](verify_corrected_interception_grades_v1.py).

## Limited impact on the separate frozen selector replay

The three native interception Top Over flags are **not** the three unresolved records in each prior complete-selector replay. Native flags occur in W5/W6 as 2/1; replay unknowns occur in W6/W8 as 1/2. Their populations cannot be substituted.

The earlier published independent receipt identifies one exact W6 control unknown (Penix interception Over0.5). Its player/event/side/line identity matches a native flag and the new explicit final zero, so this one record becomes a loss. Prior unchanged/common-membership accounting supports its presence in the candidate policy too. This is one directly read public control example plus one scoped candidate-membership inference, not renewed access to all 192 private canonical rows.

The complete canonical row file matching `c88fc8d3...` was not located in the bounded retained search; the owner's public delivery contains the commitment and schema, not the full rows. The two W8 unknown identities remain unresolved in this impact check. No ranker was run, no policy totals were rewritten, no fifth week was added and no native three-pick list was substituted. The original website owner should append a corrected grading version against its frozen canonical manifest; B then independently checks those exact rows and C retains the evidence. [Scoped impact receipt](FROZEN_SELECTOR_INT_IMPACT_V1.json).
