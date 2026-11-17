# Empirical history diagnostic: same2026 games, separate five-season robustness

**In this deliberately simple, retrospectively observed-participant diagnostic, older training reduced2026 mean-view MAE in all ten numeric targets.** H-RECENT had the lowest observed MAE for eight numeric target/product winners, H-MULTI for passing-TD lower medians, and H-CURRENT for interception lower medians. H-MULTI had the lowest anytime-TD Brier. These are observed control results within this source/cohort, not the tournament winners or an ex-ante forecast policy. The comparison holds each target's2026W1–7 query/outcome rows fixed across histories.

Protocol was registered before inspecting numeric target values at2026-10-29 22:42:32UTC; source/code/budget registration precedes numeric decoding. Run completed22:45:26UTC. Prior research exposure is preserved: this was a new diagnostic, not an untouched confirmation panel. Independent raw-slice/scorer review was requested and remains a separate receipt.

## Primary2026W1–7 results

Numeric values below are native-unit MAE; mean and lower median are views of the same empirical control, not independent method families. A lower sample median is used for even samples. No count-mean, probability or distribution identity is silently changed.

| Target / primary roles | Scored common n | CURRENT mean | RECENT mean | MULTI mean | CURRENT median | RECENT median | MULTI median |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| pass_yd / QB | 242 | 97.9690 | 69.1853 | 69.5127 | 101.7107 | 73.9339 | 71.3306 |
| pass_td / QB | 242 | 1.0941 | 0.8835 | 0.8645 | 1.1074 | 0.8388 | 0.8223 |
| pass_cmp / QB | 242 | 8.3675 | 5.7419 | 5.9625 | 8.6033 | 5.9132 | 6.1322 |
| pass_att / QB | 242 | 12.6261 | 8.5947 | 8.8577 | 13.0909 | 8.8512 | 9.0909 |
| pass_int / QB | 242 | 0.6405 | 0.6270 | 0.6395 | 0.5909 | 0.6198 | 0.6281 |
| rush_yd / QB,RB | 844 | 20.9655 | 17.4309 | 17.8259 | 20.8081 | 16.8637 | 17.1114 |
| rush_att / QB,RB | 844 | 4.0139 | 3.2014 | 3.3295 | 4.0960 | 3.1884 | 3.2832 |
| rec / RB,WR,TE | 2118 | 1.5400 | 1.3092 | 1.3617 | 1.5222 | 1.2861 | 1.3045 |
| rec_yd / RB,WR,TE | 2118 | 19.4632 | 16.8540 | 17.5981 | 19.0477 | 16.2502 | 16.6213 |
| rush_rec_yd / RB,WR,TE | 2118 | 24.7594 | 20.8741 | 21.7861 | 24.3782 | 20.3890 | 20.8451 |

Anytime rushing-or-receiving TD (RB/WR/TE): **2,118 identical scored outcomes**; Brier CURRENT **0.18991**, RECENT **0.14698**, MULTI **0.14375**. These are empirical binary-event means, not expected TD counts. Log-loss, prevalence and prevalence-reference Brier are retained in CSV; zero-probability mistakes produce honest infinite-log-loss counts rather than evaluation-time clipping. The observed prevalence reference is a retrospective diagnostic, not a pregame fitted baseline.

The best displayed-point value above was observed after evaluation; no claim is made that a policy could have selected it before the games. A fitted mean can beat the lower median under empirical MAE, as it does for passing yards, attempts and completions here. Mean-view MSE/RMSE remains separately reported. No cross-category ranking compares yard errors to rare-count errors.

## Paired history differences and startup

Negative differences favor older history. These use the same outcome keys, not different season populations. Seven week clusters are insufficient for a strong accuracy or switching claim. The reported95% week t intervals are exploratory, have no multiplicity/selection correction, and are not a certification of calibrated uncertainty.

| Target / view | Older arm | Common n | All-system mean loss difference | Learned-only common n | Learned-only difference |
| --- | --- | ---: | ---: | ---: | ---: |
| pass_yd / empirical_mean | H-RECENT | 242 | -28.78366 | 156 | -9.08741 |
| pass_yd / empirical_mean | H-MULTI | 242 | -28.45627 | 156 | -10.73079 |
| pass_int / lower_median | H-RECENT | 242 | 0.02893 | 156 | 0.01923 |
| pass_int / lower_median | H-MULTI | 242 | 0.03719 | 156 | 0.02564 |
| rush_yd / lower_median | H-RECENT | 844 | -3.94431 | 548 | -1.45255 |
| rush_yd / lower_median | H-MULTI | 844 | -3.69668 | 548 | -0.69708 |
| rec / lower_median | H-RECENT | 2118 | -0.23607 | 1397 | -0.08876 |
| rec / lower_median | H-MULTI | 2118 | -0.21766 | 1397 | -0.05870 |
| anytime_td / event_probability | H-RECENT | 2118 | -0.04293 | 1397 | -0.05320 |
| anytime_td / event_probability | H-MULTI | 2118 | -0.04615 | 1397 | -0.05485 |

For passing yards, RECENT improves pooled MAE by28.784 yards, but by9.087 yards on the156 rows where both controls have player history. Rushing-yard lower-median improvement is3.944 yards overall and1.453 yards on548 learned-only rows. Reception lower-median improvement is0.236 receptions overall and0.089 on1,397 learned-only rows. Startup and sparse-player fallback explain part of the improvement and remain in the headline diagnostic. Interception lower medians are an adverse result for longer history: RECENT/MULTI worsen2026 MAE by0.02893/0.03719, despite their probability/mean products being different questions.

CURRENT uses same-season earlier eligible outcomes. RECENT uses the preceding season plus earlier current season, with floor2022. MULTI expands from2022. Numeric forecasts use the player's same-position empirical sample; if empty, same-history target/position sample; if empty, an explicit common zero. No older fitted prior hides inside CURRENT. With kickoff+7day strict availability, CURRENT has no eligible season outcomes in Week1;37 primary QB queries,126 primary rushing queries and320 RB/WR/TE queries per relevant target receive zero. CURRENT fallback rates are35.5% for passing,35.2% for primary rushing and34.3% for receiving/combined/ATD, versus roughly2.5–6.0% with older history. No predictor features or calibration are present, so this isolates empirical sample windows, but the retrospective cohort prevents a full-system strict-current-information claim.

## Calendar and missing-cell closure

The supplied games.csv contains271 regular-season games in2022,272 each in2023–2025 and107 in2026W1–7, totaling1,194. Every game in that supplied scope has statistical and QB/RB/WR/TE query rows. The arithmetic using four272-game seasons was incorrect because the supplied2022 calendar has271. This audit does not invent an omitted/canceled game or certify original schedule closure beyond the supplied calendar.

2026 weekly game counts are16,16,16,16,15,14,14. Weeks1–6 therefore contain93 games, and Week7 adds14, exactly107. Week7 was executed, not reduced away.

| 2026 week | Games | Primary QB query/scored | Primary rushing query/scored | RB/WR/TE query/scored |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 16 | 37/37 | 126/126 | 320/316 |
| 2 | 16 | 39/39 | 134/134 | 320/319 |
| 3 | 16 | 36/36 | 126/125 | 326/318 |
| 4 | 16 | 34/34 | 125/124 | 324/318 |
| 5 | 15 | 36/36 | 122/121 | 306/300 |
| 6 | 14 | 29/29 | 107/107 | 284/278 |
| 7 | 14 | 31/31 | 107/107 | 272/269 |

All passing target fields share the QB support above; carries share primary rushing support; receiving yards, combined yards and ATD share the RB/WR/TE support. Missing rows are unknown participation, not zero error. Week7 has31/31 passing,107/107 primary rushing, and269/272 supported RB/WR/TE rows per corresponding target: the three unsupported role rows remain null across all histories. All exact season/week/target cells and null counts are in EVALUATION_COVERAGE.csv. Nonzero signed yards or positive physical action credits establish played; zero-only stat rows without another physical event remain unknown.

## Five-season robustness and reversals

All2022–2025 regular-season weeks1–18 and2026 weeks1–7 were evaluated at per-game origins. The initial2026 panel is fixed. An earlier historical season never sees a later season; all histories floor at2022, so2022 recent/multi startup has no2021 warm start. Pooled micro errors and explicitly equal-season mean metric summaries are separate files; neither answers the current-season question by itself. The2026 column above answers it within this diagnostic cohort.

| 2025 primary target / view | Common n | CURRENT MAE or Brier | RECENT | MULTI |
| --- | ---: | ---: | ---: | ---: |
| pass_yd / empirical_mean | 664 | 82.73164 | 72.96474 | 74.80364 |
| pass_td / lower_median | 664 | 0.95331 | 0.90512 | 0.88404 |
| pass_int / lower_median | 664 | 0.60241 | 0.59337 | 0.59337 |
| rush_yd / lower_median | 2229 | 18.53297 | 17.39300 | 17.57290 |
| rec / lower_median | 5294 | 1.31054 | 1.21420 | 1.25236 |
| anytime_td / event_probability | 5294 | 0.16719 | 0.15065 | 0.14719 |

Interception lower medians illustrate a reversal: RECENT/MULTI MAE0.59337 beats CURRENT0.60241 in2025, while CURRENT0.59091 beats RECENT0.61983/MULTI0.62810 on the fixed2026 rows. Historical strength does not guarantee the same current winner. Full2022–2026 season/week, position, fallback, native-unit precision and tails are retained; chart PPR remains blocked rather than replaced with generic fantasy totals.

## Scope, resources and remaining work

This run constructed71,414 empirical prefix series, with2,065,058 repeated entries including shared position summaries. Those are arithmetic summaries, **zero optimization fits**, not71,414 independent scientific methods or NFL experiments. There are940,812 forecast rows and169,754 fixed category/query cells; two point views and three histories do not multiply the25,904 unique player-games or1,194 games.25,528 player-games have positive physical-event proof and376 remain unknown. Run resources:21.19s wall,21.19s CPU,424.6MB peak RSS, one thread,7,561,537 compressed private prediction bytes.

Source qualification consumed official basic statistics, exact GSIS IDs, historical row positions, teams/opponents and schedule times. It did not consume EPA/CPOE derived models, PFR snaps, odds, current roster mappings, actual weather, generic fantasy totals or target-game script. games.csv time is interpreted America/New_York with DST. Each label is admitted to training only at kickoff+7days strictly before the query kickoff. This is an explicit reconstruction assumption, not authenticated source publication; per-game lookups preserve equal-boundary exclusion.

Weekly statistical rows and appearance proof are retrospective: this panel excludes unrecorded ex-ante opportunities and has no complete DNP/offered-prop denominator. Do not compare it directly with earlier Sleeper59/666-label replay populations or pooled report leaders. Extended WR/TE rushing and QB receiving/combined/ATD populations are separately retained; primary tables do not hide them or mix structural zeros into the same score. No injury/role, defense, playcalling, current-context, market, state or learned retrieval mechanism is being tested by these controls.

The six raw source files have a verified private companion artifact ID **V2-PRIVATE-SOURCE-0001**, as confirmed by the primary executor; no private locator is published. Exact prediction rows were initially local and are being persisted separately by the primary executor. A source-store acknowledgement alone is not a prediction-store readback or operational model admission. RUN_RECEIPT preserves the actual initial local-storage state; later restoration receipts must be linked, not silently rewritten.

Next supported work is independent raw-slice/scorer verification, a complete approved prediction/outcome restoration receipt, stronger unchanged-learner comparisons under the same paired cohort and an independently frozen ex-ante eligibility/source-vintage panel. This run does not finish all legacy procedure/history cells or qualify production. No additional experiment is launched while independent checks are pending.
