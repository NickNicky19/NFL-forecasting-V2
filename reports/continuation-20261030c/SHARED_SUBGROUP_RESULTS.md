# Shared subgroup results: gains, reversals and limits

**A smaller benchmark error has not established a website improvement.** On a separate matched 13-game Week 7 panel, the server-retained R0 reference wins eight of ten numeric categories; passing-yard MAE is 58.18724 versus 72.39038 for the fixed V2 reference. The retained bytes were available by October 23 at 17:49:53 UTC, before the later games’ T-minus-90 deadlines. This does not establish the internal October 22 capture time, provider input vintage, or today’s website method. That smaller panel is not pooled into the full 2026 benchmark. [Source and scope](server-retained-R0-v1/RUN_RECEIPT.json).

The subgroup work below adds zero NFL fits, forecasts or 2026 Week 8 outcomes. It replays retained predictions on the same frozen memberships for every competitor. Numeric changes are candidate-minus-control MAE; anytime TD uses Brier. Negative values favor the candidate. They are native-unit errors, not generic accuracy percentages or a cross-category contest.

## C02: 2026 gains do not establish a persistent winner

The fixed 2026 C02 recipes improve the overall interception, reception and chart-point minima against the earlier 2026 controls. Those gains also hold in the top-player groups. However, transferring the same C02 history/product choices to 2025 loses overall native error to the strongest same-season existing control in all twelve categories. This is a fixed-recipe comparison, not a claim that every C02 variant loses every 2025 test. The same-season reference was chosen from the already known full-primary table and then held fixed within every subgroup. Neither selection is an earlier live policy.

| Target | 2026 Δ previous control: full | Top 20 | 2025 Δ fixed 2026 control: full | 2025 Δ strongest same-season: full | Top 20 |
| --- | ---: | ---: | ---: | ---: | ---: |
| anytime_td | +0.0008 | +0.0042 | +0.0006 | +0.0006 | -0.0001 |
| nick-chart-ppr-v1 | -0.0034 | -0.1174 | +0.0147 | +0.0238 | +0.0488 |
| pass_att | +0.1033 | -0.0286 | +0.3840 | +0.4694 | +0.0028 |
| pass_cmp | +0.1469 | +0.1436 | +0.0555 | +0.1964 | +0.0096 |
| pass_int | -0.0248 | -0.0214 | -0.0346 | +0.0105 | +0.0083 |
| pass_td | +0.0000 | +0.0357 | +0.0060 | +0.0452 | +0.0444 |
| pass_yd | +1.5480 | -0.8100 | +2.9847 | +3.3145 | +0.9345 |
| rec | -0.0080 | -0.0714 | +0.0077 | +0.0093 | +0.0222 |
| rec_yd | +0.0170 | -0.1857 | +0.0625 | +0.0625 | +0.0861 |
| rush_att | +0.0498 | +0.0500 | +0.0247 | +0.0381 | +0.0222 |
| rush_rec_yd | +0.1331 | -1.1436 | +0.1103 | +0.1103 | -1.0056 |
| rush_yd | +0.0616 | -0.3071 | +0.0633 | +0.0633 | -0.0083 |

In 2025, passing-yard C02 MAE is 72.0015 against the stronger control’s 68.6870. The interception recipe beats the fixed 2026 reference by 0.0346 but loses 0.0105 against the stronger 2025 control. Comparing only the former would hide a real loss. Combined yards loses 0.1103 overall while improving 1.8584 in the top 10 and 1.0056 in the top 20. Such subgroup reversals do not by themselves justify a future routing rule.

[2026 C02 tables](shared-subgroup-comparator-correction-v1/README.md) · [2025 corrected compact tables](season-2025-subgroups-compact-v3/README.md) · [2025 full/learned/band CSV](season-2025-subgroups-compact-v3/TOP_PLAYER_AND_ROLE_SCORECARD.csv)

## D1/D2: opponent information helps some views and hurts others

For each group and category, its history/product was fixed from its already exposed full-primary result before subgroup replay. Both groups face the same strongest previous control and their exact same-policy original Leaf control. D1’s completion gain reverses among top players; both chart gains reverse in the top 20. Rushing-yard gains persist across overall and top-player views. The carry gain is about one absolute-error unit in total across 844 primary rows, so its tiny average must not be presented as a reliable universal advantage.

| Target | D1 Δ strongest: full | Top 20 | D2 Δ strongest: full | Top 20 |
| --- | ---: | ---: | ---: | ---: |
| anytime_td | +0.0015 | +0.0046 | +0.0015 | +0.0040 |
| nick-chart-ppr-v1 | -0.0022 | +0.0431 | -0.0062 | +0.0717 |
| pass_att | +0.0000 | -0.0143 | -0.0331 | -0.0071 |
| pass_cmp | -0.0762 | +0.1222 | -0.0059 | +0.1150 |
| pass_int | +0.0289 | -0.0143 | +0.0372 | +0.0500 |
| pass_td | -0.0124 | +0.0071 | +0.0165 | +0.0643 |
| pass_yd | +0.9984 | -0.3243 | +0.7381 | -0.3671 |
| rec | +0.0009 | +0.0786 | +0.0000 | +0.0643 |
| rec_yd | +0.0009 | -0.2571 | -0.0094 | -0.2786 |
| rush_att | -0.0012 | -0.0143 | +0.0047 | +0.0214 |
| rush_rec_yd | +0.1104 | -0.9222 | +0.1137 | -0.9864 |
| rush_yd | -0.0616 | -0.2571 | -0.0450 | -0.4357 |

D1 completion MAE improves 0.0762 overall but worsens 0.2558 in the top 10 and 0.1222 in the top 20. D1 rushing-yard error improves 0.0616 overall, 0.4286 in the top 10 and 0.2571 in the top 20. D2 receiving-yard improvement is larger among top players than overall. Passing-yard and combined-yard overall losses reverse among the top players. All losses and ties remain visible.

The frozen defense implementation uses four **observed qualified-position groups**, not four calendar team games. Six entirely absent TE groups are not padded; 77 historical query windows differ from a calendar interpretation, and older training contexts can also differ. Missing targets inside an observed group do consume slots. Original scores, models and forecasts remain unchanged; no calendar-padding refit or causal defensive-talent claim is made. [Exact wording, counts and scope](qualified-defense-information-v1/WINDOW_DEFINITION_FINDING.md).

[D1/D2 compact tables](defense-subgroups-compact-v3/README.md) · [D1/D2 full/learned/band CSV](defense-subgroups-compact-v3/TOP_PLAYER_AND_ROLE_SCORECARD.csv) · [Separate proper-law/mean results](qualified-defense-information-v1/EXECUTED_RESULTS.md)

## Membership, fallback and evidence coverage

Football ranks use earlier attempts, carries, targets or carries plus targets. Chart ranks use earlier signed chart points, with score-history bands rather than workload bands. Top 10/15/20 and the disjoint 1–10, 11–15, 16–20 and remainder bands are common to competitors. Unknown history remains unranked; unknown outcomes remain in forecast coverage. The universe is retrospective statistical rows with physical-participation qualification, not an authenticated ex-ante offer or starter list. The assumed seven-day source delay and common older selector memory remain disclosed.

Full-system results retain startup and role-prior fallbacks. Own-learned rows can differ between procedures. The compact common-learned mask is the selected candidate and its two registered controls, with exact query identities; it is not a three-history overlap or the older broad all-family/all-policy mask. Chart median precision uses exact signed 0.02 coordinates; means remain unrounded. Proper-law and genuine-mean products are kept in their separately scored full-method artifacts.

Current 2026 panels cover 107 games in Weeks 1–7. Seven exposed week clusters do not meet the registered eight-week bootstrap threshold, even when many player rows exist. The 2025 compact panel covers all 18 weeks, 272 games and 6,037 player-games; its 500-replicate whole-week bootstrap is available where a view has at least eight observed weeks. Game-cluster sensitivity is separate. None of these intervals corrects selection or multiplicity.

Independent reviewers replayed all 797 corrected 2025 compact score views and 1,594 pairs, and all 1,484 D1/D2 compact score views and 2,968 pairs, including native errors, precision, masks and uncertainty. The original 2026 C02 comparison-only correction also reproduced its entire 7,458-row univariate array exactly. [2025 review](SEASON_2025_COMPACT_SUBGROUP_INDEPENDENT_REVIEW.json) · [D1/D2 review](DEFENSE_COMPACT_SUBGROUP_INDEPENDENT_REVIEW.json).

## Preserved limitations and versions

- The original 2025 broad v2 artifact contains 8,027 score views. Its 1,844 requested all-selected-controls/all-four-policy shared-mask views are invalidated because empirical aliases were unresolved. The original comparisons retain 4,999 unresolved empirical references. Full and own-learned point metrics are not thereby forecast changes; bounded independent replay validated 908 full-system views and all 45,579 selector profiles. That is not a complete replay of the broad matrix.
- Compact v3 is a different, explicitly narrower panel with corrected empirical aliases and a selected-candidate-plus-two-control mask. It does **not** repair or authenticate every v2 view. All original v2 bytes and the stopped v1 preparation/replay attempt remain preserved. [Registry source version note](../../registries/RESULT_ARTIFACTS.json) · [bounded v2 review](SEASON_2025_SUBGROUP_BOUNDED_INDEPENDENT_REVIEW.json).
- Older 2022–2024 method forecasts and full-season scores are separate executed artifacts. Their subgroup memberships were frozen, but this compact report does not claim that the optional older-year subgroup matrices have been replayed. Requested 2022 recent history includes 2021, which is unsupported by these sources; its available 2022-only proxy is not evidence against older training.
- No actual offers, prices or frozen bet-selection rules are evaluated here. Subgroup error gains do not establish Over/Under hit rate, ROI, or permission to publish to the website.

[Public artifact matrix](COMPACT_SUBGROUP_ARTIFACT_MATRIX.json) · [Full checkpoint](README.md)
