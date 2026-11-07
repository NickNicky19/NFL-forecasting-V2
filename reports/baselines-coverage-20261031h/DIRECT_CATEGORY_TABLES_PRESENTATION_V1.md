# Direct category presentation — retained H evidence

Presentation only: no new scores, fits, inference, labels or captures. All figures below come from checkpoint `07fc8a2a`. W/L/D means wins/losses/decided; percentages use W/D.

**TABLE A — ORIGINAL RECORDED SELECTIONS**

2026 regular-season rolling Weeks 5–7: 42/43 source games. Missing: Weeks 1–4, Week 5 Thursday and older original offered-line periods. Fixed-Friday W7 is separate, not pooled. Counts are statistical crossing; bookmaker settlement remains unverified. Category game counts below mean games containing decided selections, not all scheduled games.

| Category | Over W/L/D; hit | Under W/L/D; hit | Combined W/L/D; weighted hit | Unknown O/U/Combined | Total selected (= book unresolved) | Covered period; decided-pick games |
|---|---|---|---|---|---:|---|
| pass_yd | 15 / 11 / 26; **57.69%** | 18 / 20 / 38; **47.37%** | 33 / 31 / 64; **51.56%** | 0/0/0 | 64 | W5–7; 38 |
| pass_td | 17 / 11 / 28; **60.71%** | 32 / 11 / 43; **74.42%** | 49 / 22 / 71; **69.01%** | 0/0/0 | 71 | W5–7; 41 |
| pass_cmp | 12 / 2 / 14; **85.71%** | 22 / 19 / 41; **53.66%** | 34 / 21 / 55; **61.82%** | 0/0/0 | 55 | W5–7; 38 |
| pass_att | 8 / 4 / 12; **66.67%** | 26 / 17 / 43; **60.47%** | 34 / 21 / 55; **61.82%** | 0/0/0 | 55 | W5–7; 38 |
| pass_int | 17 / 18 / 35; **48.57%** | 12 / 3 / 15; **80.00%** | 29 / 21 / 50; **58.00%** | 0/0/0 | 50 | W5–7; 36 |
| rush_yd | 59 / 72 / 131; **45.04%** | 18 / 17 / 35; **51.43%** | 77 / 89 / 166; **46.39%** | 2/0/2 | 168 | W5–7; 42 |
| rush_att | 27 / 20 / 47; **57.45%** | 20 / 17 / 37; **54.05%** | 47 / 37 / 84; **55.95%** | 1/1/2 | 86 | W5–7; 39 |
| rec | 82 / 47 / 129; **63.57%** | 115 / 70 / 185; **62.16%** | 197 / 117 / 314; **62.74%** | 7/7/14 | 328 | W5–7; 42 |
| rec_yd | 93 / 103 / 196; **47.45%** | 40 / 25 / 65; **61.54%** | 133 / 128 / 261; **50.96%** | 9/2/11 | 272 | W5–7; 42 |
| rush_rec_yd | 17 / 28 / 45; **37.78%** | 13 / 16 / 29; **44.83%** | 30 / 44 / 74; **40.54%** | 2/1/3 | 77 | W5–7; 38 |
| nick-chart-ppr-v1 | N/A | N/A | N/A | N/A | N/A | No qualified offered/selection contract |
| anytime_td | N/A | N/A | N/A | N/A | N/A | No qualified offered/selection contract |

Reconciliation: Over 347 W / 316 L / 663 decided; Under 316 W / 215 L / 531 decided; Combined 663 W / 531 L / 1,194 decided. There are 1,226 selections and 32 unknown appearances (21 Over, 11 Under). Selected Over/Under totals equal their decided counts plus their respective unknown counts. Statistical pushes, voids, pending and missing-actual states are zero on this retained panel; all 1,226 bookmaker contracts remain unverified, so these are not settled sportsbook returns.

**TABLE B — ACTUAL FORECASTING METHODS: NUMERICAL LEADERS AND THEIR OWN P1 SELECTIONS**

N=numerical panel:2026 W1–7 retrospective participant/stat-row reconstruction at kickoff, with current/revised source vintages. Error is MAE except anytime-TD Brier. O=offered-threshold panel:2026 W5–7 retrospective known-target-time-v1 replay, actual source-decision eligibility, same target/output/history; not original V2 issuance. P1 selects Over if unrounded point>line, Under if point<line, abstains on equality. Each row uses only that procedure’s own sides. M=H-MULTI;C=H-CURRENT fitting with registered feature memory, not strict current information.

| Category | Procedure/version · history · output · rule | N: error; supported n | O: Over W/L/D; hit | O: Under W/L/D; hit | O: Combined W/L/D; hit | O: selected/outer; coverage | Evidence / selection weeks |
|---|---|---|---|---|---|---|---|
| pass_yd | HGB-L1-v1 · M · absolute-error point · P1 | MAE 66.117313; n=242 | 14 / 18 / 32; **43.75%** | 14 / 34 / 48; **29.17%** | 28 / 52 / 80; **35.00%** | 80/84; 95.24% | Retrospective/current-vintage; W5–7 |
| pass_td | D1-v1 · M · lower_median · P1 | MAE 0.809917; n=242 | 17 / 9 / 26; **65.38%** | 33 / 17 / 50; **66.00%** | 50 / 26 / 76; **65.79%** | 76/84; 90.48% | Retrospective/current-vintage; W5–7 |
| pass_cmp | D1-v1 · M · lower_median · P1 | MAE 5.342975; n=242 | 11 / 12 / 23; **47.83%** | 22 / 31 / 53; **41.51%** | 33 / 43 / 76; **43.42%** | 76/84; 90.48% | Retrospective/current-vintage; W5–7 |
| pass_att | D2-v1 · M · lower_median · P1 | MAE 7.971074; n=242 | 6 / 2 / 8; **75.00%** | 26 / 22 / 48; **54.17%** | 32 / 24 / 56; **57.14%** | 56/84; 66.67% | Retrospective/current-vintage; W5–7 |
| pass_int | C02-v1 · C · lower_median · P1 | MAE 0.566116; n=242 | 9 / 3 / 12; **75.00%** | 41 / 27 / 68; **60.29%** | 50 / 30 / 80; **62.50%** | 80/84; 95.24% | Retrospective/current-vintage; W5–7 |
| rush_yd | D1-v1 · M · lower_median · P1 | MAE 16.688389; n=844 | 23 / 29 / 52; **44.23%** | 92 / 69 / 161; **57.14%** | 115 / 98 / 213; **53.99%** | 213/244; 87.30% | Retrospective/current-vintage; W5–7 |
| rush_att | Earlier-current-selector-v2 · M · selected_point · P1 | MAE 3.049763; n=844 | 14 / 12 / 26; **53.85%** | 43 / 45 / 88; **48.86%** | 57 / 57 / 114; **50.00%** | 114/125; 91.20% | Retrospective/current-vintage; W5–7 |
| rec | C02-v1 · M · lower_median · P1 | MAE 1.245515; n=2118 | 73 / 48 / 121; **60.33%** | 191 / 158 / 349; **54.73%** | 264 / 206 / 470; **56.17%** | 470/511; 91.98% | Retrospective/current-vintage; W5–7 |
| rec | D2-v1 · M · lower_median · P1 | MAE 1.245515; n=2118 | 60 / 33 / 93; **64.52%** | 134 / 103 / 237; **56.54%** | 194 / 136 / 330; **58.79%** | 330/511; 64.58% | Retrospective/current-vintage; W5–7 |
| rec_yd | D2-v1 · M · lower_median · P1 | MAE 16.189330; n=2118 | 43 / 53 / 96; **44.79%** | 121 / 114 / 235; **51.49%** | 164 / 167 / 331; **49.55%** | 331/512; 64.65% | Retrospective/current-vintage; W5–7 |
| rush_rec_yd | HGB-L1-v1 · M · absolute-error point · P1 | MAE 20.125661; n=2118 | 8 / 9 / 17; **47.06%** | 53 / 43 / 96; **55.21%** | 61 / 52 / 113; **53.98%** | 113/124; 91.13% | Retrospective/current-vintage; W5–7 |
| nick-chart-ppr-v1 | D2-v1 · M · lower_median · N/A offer rule | MAE 4.490360; n=2359 (partial chart) | N/A | N/A | N/A | N/A: no qualified offered contract | N retrospective; O unavailable |
| anytime_td | HGB-logloss-v1 · M · event probability · N/A offer rule | Brier 0.143144; n=2118 | N/A | N/A | N/A | N/A: no qualified offered contract | N retrospective; O unavailable |

Both tied receptions leaders are shown:their MAE ties but their offered panels and decisions differ. Carry selector alias is bound through the same registered category-selector-v2/DECISIONS.json and protocol hashes; its displayed O product is selected_point. HGB rush_rec_yd and anytime-TD numerical scores also tie policy views of the same forecasts; those are not new independent learners. Chart error is qualified partial-label research, not proven full chart completeness.

All selected statistical outcomes in Table B are decided; unavailable forecasts remain in the outer denominator. Selected-side fallback counts for cumulative P1 are null, not assumed zero. These different own-pool counts are not matched common-row learner effects. Three selection weeks give insufficient week-cluster uncertainty; native rankings and raw side maxima are exposed comparisons, not selection-adjusted proof or release admission.

**Different selection leaders, separately identified**

The following maxima are descriptive own-pool results, not rows spliced into Table B. P1 output is named. P2 uses the complete saved law (Leaf/C02) or saved parametric law(GLM/D1/D2). Each fraction is wins/decided; losers=decided−wins. All periods are W5–7. Strict means strict current information with H-CURRENT, not ordinary C fitting. F=fallback/prior-only. All ties are retained.

- **pass_yd**
  P1: Over = D2-v1 strict C mean: 26/40 (65.00%); Under = D2-v1 strict C mean: 8/16 (50.00%); Combined = D2-v1 strict C mean: 34/56 (60.71%).
  P2: Over = D1-v1 strict C law: 1/1 (100.00%) **F**; D2-v1 strict C law: 1/1 (100.00%) **F**; Under = GLM-v2 strict C law: 13/28 (46.43%); Combined = D1-v1 strict C law: 1/1 (100.00%) **F**; D2-v1 strict C law: 1/1 (100.00%) **F**.
- **pass_td**
  P1: Over = D2-v1 R lower_median: 7/9 (77.78%); Under = HGB-L2-v1 M squared_error_mean: 26/36 (72.22%); Combined = D2-v1 R lower_median: 37/56 (66.07%).
  P2: Over = D1-v1 strict C law: 1/1 (100.00%) **F**; D2-v1 strict C law: 1/1 (100.00%) **F**; Under = Leaf-v2 M law: 35/55 (63.64%); Combined = D1-v1 strict C law: 1/1 (100.00%) **F**; D2-v1 strict C law: 1/1 (100.00%) **F**.
- **pass_cmp**
  P1: Over = C02-v1 C mean: 2/3 (66.67%); Under = C02-v1 strict C mean: 15/30 (50.00%); D1-v1 strict C mean: 15/30 (50.00%); D2-v1 strict C mean: 11/22 (50.00%); Combined = C02-v1 strict C mean: 46/80 (57.50%).
  P2: Over = C02-v1 strict C law: 25/41 (60.98%); Under = C02-v1 strict C law: 18/39 (46.15%); Combined = C02-v1 strict C law: 43/80 (53.75%); GLM-v2 strict C law: 43/80 (53.75%).
- **pass_att**
  P1: Over = C02-v1 C mean: 1/1 (100.00%); C02-v1 R lower_median: 3/3 (100.00%); D2-v1 M mean: 3/3 (100.00%); Under = C02-v1 strict C lower_median: 26/41 (63.41%); Leaf-v2 strict C lower_median: 26/41 (63.41%); Combined = C02-v1 strict C lower_median: 50/80 (62.50%); Leaf-v2 strict C lower_median: 50/80 (62.50%).
  P2: Over = C02-v1 R law: 3/3 (100.00%); Under = C02-v1 strict C law: 26/41 (63.41%); Leaf-v2 strict C law: 26/41 (63.41%); Combined = C02-v1 strict C law: 50/80 (62.50%); Leaf-v2 strict C law: 50/80 (62.50%).
- **pass_int**
  P1: Over = C02-v1 R lower_median: 1/1 (100.00%); Leaf-v2 M lower_median: 1/1 (100.00%); Leaf-v2 R lower_median: 4/4 (100.00%); Under = C02-v1 strict C mean: 1/1 (100.00%); Leaf-v2 C mean: 1/1 (100.00%); Leaf-v2 strict C mean: 1/1 (100.00%); GLM-v2 C mean: 1/1 (100.00%); GLM-v2 M mean: 1/1 (100.00%); GLM-v2 R mean: 1/1 (100.00%); Combined = C02-v1 C lower_median: 50/80 (62.50%).
  P2: Over = C02-v1 R law: 1/1 (100.00%); Leaf-v2 M law: 1/1 (100.00%); Leaf-v2 R law: 4/4 (100.00%); Under = D1-v1 strict C law: 1/1 (100.00%) **F**; D2-v1 strict C law: 1/1 (100.00%) **F**; Combined = D1-v1 strict C law: 1/1 (100.00%) **F**; D2-v1 strict C law: 1/1 (100.00%) **F**.
- **rush_yd**
  P1: Over = HGB-L1-v1 M absolute_error_point: 12/21 (57.14%); Under = D2-v1 C mean: 52/85 (61.18%); Combined = HGB-L1-v1 M absolute_error_point: 129/226 (57.08%).
  P2: Over = D1-v1 strict C law: 3/4 (75.00%) **F**; Under = D1-v1 strict C law: 2/2 (100.00%) **F**; D2-v1 strict C law: 1/1 (100.00%) **F**; Combined = D1-v1 strict C law: 5/6 (83.33%) **F**.
- **rush_att**
  P1: Over = HGB-carry-QB/RB-v1 C absolute_loss_point: 16/24 (66.67%); Under = D2-v1 C lower_median: 34/57 (59.65%); Combined = D2-v1 C lower_median: 48/79 (60.76%).
  P2: Over = C02-v1 C law: 17/26 (65.38%); Under = D1-v1 strict C law: 1/1 (100.00%) **F**; Combined = D1-v1 strict C law: 1/1 (100.00%) **F**.
- **rec**
  P1: Over = D2-v1 M lower_median: 60/93 (64.52%); Under = D2-v1 M mean: 108/181 (59.67%); Combined = D2-v1 M mean: 198/330 (60.00%).
  P2: Over = C02-v1 R law: 70/114 (61.40%); Under = Leaf-v2 C law: 186/335 (55.52%); Combined = Leaf-v2 C law: 268/470 (57.02%).
- **rec_yd**
  P1: Over = HGB-L1-v1 R absolute_error_point: 70/132 (53.03%); Under = Empirical-v1 R mean: 99/164 (60.37%); Combined = Empirical-v1 R lower_median: 260/469 (55.44%).
  P2: Over = D1-v1 strict C law: 2/3 (66.67%) **F**; Under = GLM-v2 M law: 102/183 (55.74%); Combined = C02-v1 R law: 255/470 (54.26%).
- **rush_rec_yd**
  P1: Over = C02-v1 strict C lower_median: 8/13 (61.54%); D2-v1 M lower_median: 8/13 (61.54%); Under = Empirical-v1 R mean: 32/55 (58.18%); Combined = C02-v1 strict C lower_median: 65/113 (57.52%).
  P2: Over = C02-v1 strict C law: 8/13 (61.54%); Under = C02-v1 strict C law: 57/100 (57.00%); Combined = C02-v1 strict C law: 65/113 (57.52%).

Raw 100% maxima such as 1/1 and 3/3 are not validated champions. The prior-only P2 rushing-yards 5/6 pool covers just 6/244 (2.46%) outer offers; prior-only 1/1 passing pools cover 1/84 (1.19%), and carry 1/1 covers 1/125 (0.80%). No posthoc support gate hides them and no release recommendation follows from them.

On identical 80-row passing-attempt probability masks, H-MULTI Leaf Brier 0.255654 loses to neutral 0.25 and earlier prevalence 0.252687; strict-current Leaf 0.242276 is a different information policy. This matched result is separate from the raw selected-side maxima.

**Exact identity key**

- HGB-L1-v1=`hgb-direct-history-controls-v1:absolute_error_point`;HGB-L2-v1=`hgb-direct-history-controls-v1:squared_error_mean`;HGB-logloss-v1=`hgb-direct-history-controls-v1:log_loss_probability`.
- D1-v1/D2-v1=`v2-qualified-position-defense-information-wave-v1:D1`/`:D2`; these are the retained observed-position-group window versions, not scheduled-window reconstructions.
- C02-v1=`v2-c02-explicit-lag-block-removal-leaf-cdf-v1`;Leaf-v2=`v2-distribution-controls-reconstruction-v2:ordered_leaf_cdf`;GLM-v2=`v2-distribution-controls-reconstruction-v2:regularized_glm_law`.
- Empirical-v1=`empirical-player-history-control-v1`;HGB-carry-QB/RB-v1=`v2-hgb-rush-att-qb-rb-specialization-v1`.
- Earlier-current-selector-v2=`v2-chronological-category-score-memory-selector-v2:EARLIER_AVAILABLE_2026_SCORE_MEMORY`;O alias=`v2-chronological-category-selector:EARLIER_AVAILABLE_2026_SCORE_MEMORY:known-target-time-v1`.
- O fixed procedures append`:known-target-time-v1`;strict variants retain`:strict-current-inputs`. R=H-RECENT. Mean,lower_median and law are distinct products; none are counted as new learners.

[Full championship](FULL_CATEGORY_CHAMPIONSHIP_REPORT.md) · [P1 all methods and sides](probability/w5-w7-cumulative-v1/PRIMARY_P1_WIDE_TABLE.csv) · [P2 all laws and sides](probability/w5-w7-primary-p2-v1/PRIMARY_P2_SIDE_TABLE.csv) · [Category JSON](CATEGORY_DECISIONS.json) · [Original category/weekly/cohort evidence](source-expansion/original-selected-matched-v1/MAIN_CATEGORY_VIEWS.csv).

Full-period research remains unfinished at the existing historical-offer/source and own recovery-gated recipe cells. No prediction, capture, release policy or production state changed for this presentation.
