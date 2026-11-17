# B retained W5–W7 point comparisons: weekly partition

New per-week evaluations of existing retained grades, not new games, forecasts or fits. All 63 parent cumulative triads reconcile exactly. The source covers 42 games in Weeks 5–7, with one Week 5 game missing. C’s Pinnacle Weeks 2–3 panel and original selections remain separate. Full-system, common-row and learned-only contexts retain all losses.

|Target|Frozen focal recipe|Week|Over W-L/n/%|Under W-L/n/%|Combined W-L/n/%|Selected/eligible|AlwaysOver / always-Under on the same focal mask|
|---|---|---|---|---|---|---|---|
|pass_yd|`hgb-direct-history-controls-v1:absolute_error_point` / H-MULTI / absolute_error_point|5|7-8/15/46.67%|5-8/13/38.46%|12-16/28/42.86%|28/28|always-Over 15/28; always-Under 13/28|
|pass_yd|`hgb-direct-history-controls-v1:absolute_error_point` / H-MULTI / absolute_error_point|6|5-5/10/50.00%|5-12/17/29.41%|10-17/27/37.04%|27/28|always-Over 17/27; always-Under 10/27|
|pass_yd|`hgb-direct-history-controls-v1:absolute_error_point` / H-MULTI / absolute_error_point|7|2-5/7/28.57%|4-14/18/22.22%|6-19/25/24.00%|25/28|always-Over 16/25; always-Under 9/25|
|pass_cmp|`v2-qualified-position-defense-information-wave-v1:D1` / H-MULTI / lower_median|5|4-5/9/44.44%|9-10/19/47.37%|13-15/28/46.43%|28/28|always-Over 14/28; always-Under 14/28|
|pass_cmp|`v2-qualified-position-defense-information-wave-v1:D1` / H-MULTI / lower_median|6|4-4/8/50.00%|6-12/18/33.33%|10-16/26/38.46%|26/28|always-Over 16/26; always-Under 10/26|
|pass_cmp|`v2-qualified-position-defense-information-wave-v1:D1` / H-MULTI / lower_median|7|3-3/6/50.00%|7-9/16/43.75%|10-12/22/45.45%|22/28|always-Over 12/22; always-Under 10/22|

Cumulative focal losses remain HGB-L1 MULTI passing yards 28/80 (35.00%) and D1 MULTI completions 33/76 (43.42%). Their cumulative source masks were stored under common-context aliases; [qualification](FOCAL_COVERAGE_ALIAS_QUALIFICATION_V3.json) preserves those records and adds correct full-board availability. No forecast, prior decided grade or selection rule changed. Known and unknown fallback states remain separate. Weekly views overlap cumulative views and add no independent NFL trials.

[Every originalcontext/method/week score](SCORES.json) · [Focal full-system coverage](FULL_SYSTEM_FOCAL_SCORES.json) · [Constants on full board and focal masks](CONSTANT_CONTROL_SCORES.json) · [Cumulative count reconciliation](WEEK_TO_PARENT_RECONCILIATION.json) · [All-side table](SIDE_TABLE.csv). Native point views include equality abstention rows; no probability/price/EV claim. Single-week uncertainty is game sensitivity, not enough week clusters.

The focal passing-yard error/bias was 61.01/−12.26, 54.78/−15.83 and 64.77/−26.30 yards by week; completion error/bias was 4.86/−1.71, 5.00/−2.62 and 5.36/−0.27. Bias means prediction minus actual. These patterns describe losses, not a proven causal diagnosis or an evaluated repair. Missing forecasts are technical unavailability, not confidence abstention. Prices and bookmaker settlement remain unqualified.

Fallback scope: all issued focal outputs were learned; the unavailable queries retain unknown fallback states (passing yards 0/1/3, completions 0/2/6 by week). Native `fallback_unknown=0` describes issued outputs only, not every query. [Bound qualification](NATIVE_FALLBACK_SCOPE_QUALIFICATION.json).
