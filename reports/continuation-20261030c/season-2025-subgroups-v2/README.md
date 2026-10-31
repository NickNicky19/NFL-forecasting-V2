# 2025: fixed 2026 C02 recipes on shared subgroups

These tables reuse retained forecasts and the cohort memberships frozen before seasonal loss decoding. No fits, new forecasts, or 2026 Week 8 outcomes are added. Every row keeps the same C02 history/product chosen from the already exposed 2026 full-primary result. It compares (1) the fixed pre-C02 2026 control and (2) the strongest observed same-season full-primary existing control. References were fixed before subgroup scoring and are not reselected within bands. Neither view is an earlier live policy. Numeric errors use MAE; anytime TD uses Brier. Negative change favors C02; parentheses give identical supported paired rows.

| Target | C02 full error | Δ fixed-2026 control: full | Top 10 | Top 15 | Top 20 | High prior band | Δ strongest same-season: full | Top 20 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| anytime_td | 0.1434 | +0.0006 (5294) | +0.0025 (180) | +0.0004 (270) | -0.0001 (360) | -0.0000 (566) | +0.0006 (5294) | -0.0001 (360) |
| nick-chart-ppr-v1 | 4.3892 | +0.0147 (5937) | +0.0632 (180) | +0.0451 (270) | +0.0558 (360) | +0.0146 (908) | +0.0238 (5937) | +0.0488 (360) |
| pass_att | 8.9578 | +0.3840 (664) | +0.0278 (180) | +0.0444 (270) | +0.0528 (360) | +0.1210 (124) | +0.4694 (664) | +0.0028 (360) |
| pass_cmp | 6.0241 | +0.0555 (664) | +0.1291 (180) | +0.0814 (270) | +0.0486 (360) | +0.1597 (124) | +0.1964 (664) | +0.0096 (360) |
| pass_int | 0.5678 | -0.0346 (664) | -0.0278 (180) | -0.0778 (270) | -0.0694 (360) | -0.0484 (124) | +0.0105 (664) | +0.0083 (360) |
| pass_td | 0.8901 | +0.0060 (664) | +0.0167 (180) | -0.0111 (270) | +0.0000 (360) | +0.0726 (124) | +0.0452 (664) | +0.0444 (360) |
| pass_yd | 72.0015 | +2.9847 (664) | +0.3774 (180) | +0.4105 (270) | +0.6872 (360) | +0.7065 (124) | +3.3145 (664) | +0.9345 (360) |
| rec | 1.1887 | +0.0077 (5294) | +0.0667 (180) | +0.0074 (270) | -0.0083 (360) | +0.0039 (515) | +0.0093 (5294) | +0.0222 (360) |
| rec_yd | 15.3717 | +0.0625 (5294) | +0.3556 (180) | +0.2481 (270) | +0.0861 (360) | +0.0680 (515) | +0.0625 (5294) | +0.0861 (360) |
| rush_att | 2.9053 | +0.0247 (2229) | -0.0056 (180) | +0.0148 (270) | +0.0417 (360) | +0.0367 (409) | +0.0381 (2229) | +0.0222 (360) |
| rush_rec_yd | 19.8211 | +0.1103 (5294) | -1.8584 (180) | -1.2035 (270) | -1.0056 (360) | -0.6290 (566) | +0.1103 (5294) | -1.0056 (360) |
| rush_yd | 16.7806 | +0.0633 (2229) | +0.1167 (180) | +0.0000 (270) | -0.0083 (360) | +0.0024 (409) | +0.0633 (2229) | -0.0083 (360) |

## Learned-only and common membership

Own-learned rows can differ by procedure. The common-learned view intersects all selected references and all four C02 policies; it includes strict models explicitly. Common older cohort-selector memory means this selected system is not a pure-current-information claim.

| Target | Own-learned full Δ vs fixed control | Shared-learned full Δ vs fixed control | Shared-learned top 20 Δ |
| --- | ---: | ---: | ---: |
| anytime_td | +0.0006 (5135) | +0.0005 (4432) | +0.0008 (317) |
| nick-chart-ppr-v1 | +0.0151 (5759) | +0.0129 (4954) | +0.0975 (317) |
| pass_att | +0.3953 (645) | +0.5392 (510) | +0.0507 (296) |
| pass_cmp | +0.1589 (645) | +0.2186 (510) | +0.0314 (296) |
| pass_int | -0.0391 (537) | -0.0392 (510) | -0.0743 (296) |
| pass_td | +0.0062 (645) | +0.0020 (510) | +0.0000 (296) |
| pass_yd | +2.3665 (645) | +2.3725 (510) | +0.2553 (296) |
| rec | +0.0080 (5135) | +0.0045 (4432) | -0.0345 (319) |
| rec_yd | +0.0645 (5135) | +0.0397 (4432) | +0.0752 (319) |
| rush_att | +0.0255 (2157) | +0.0183 (1854) | +0.0406 (320) |
| rush_rec_yd | -0.0258 (5135) | -0.0572 (4432) | -1.0174 (317) |
| rush_yd | +0.0654 (2157) | +0.0777 (1854) | -0.0250 (320) |

The [compact scorecard](FIXED_2026_RECIPE_SUBGROUP_SCORECARD.csv) also retains disjoint ranks 1–10, 11–15, 16–20, remainder, unranked players, every prior workload/score band, primary/extended populations, fallbacks and whole-week paired bootstrap intervals. Football ranks use earlier opportunities; chart ranks use signed chart points, not workload. The source remains a retrospective statistical-row/physical-participation diagnostic, with assumed seven-day availability, not authenticated historical offers or starters.

All 18 regular-season weeks, including historical Week 8, are evaluated. Bootstrap intervals resample whole weeks, 500 replicates with fixed seed, where at least eight clusters exist. They are descriptive exposed-sample intervals, without selection or multiplicity adjustment. Canonical scores retain mean/median identity, genuine-law diagnostics and exact chart median precision; this compact table projects displayed points only.

[Canonical C02 cohort scores](SCORES.json) · [Compressed paired matrix](PAIRED_COMPARISONS.json.gz) · [Exact encoding receipt](PAIRED_COMPARISONS_ENCODING_RECEIPT.json) · [Protocol](FROZEN_PROTOCOL.json) · [Run receipt](RUN_RECEIPT.json)

No website improvement follows from this older-season diagnostic. The separate server-retained R0 reference wins eight of ten numeric categories on a matched 13-game 2026 Week 7 panel; its server availability does not establish internal capture/input vintage or today’s website method.
