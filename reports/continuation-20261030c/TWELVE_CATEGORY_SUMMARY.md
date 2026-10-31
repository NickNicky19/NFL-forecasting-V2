# Twelve-category seasonal results

Older seasons are internally matched rolling-origin comparisons. Their games differ from the fixed 2026 test panel, so this table does not answer the 2026 training-window question. Numeric cells are MAE; anytime TD uses Brier. These are observed minima among the executed V2 library, not earlier-frozen selection policies. Historical query features use the registered kickoff cutoff, not a reconstructed T-minus-90 product; subgroup selectors and future eligibility have separately stated clocks.

| Target | 2025 minimum | 2024 minimum | 2023 minimum | 2022 available-data minimum |
|---|---|---|---|---|
| pass_yd | 68.686969 · HGB-L2 · H-MULTI (n=664) | 67.689422 · HGB-L1 · H-RECENT (n=664) | 71.208145 · Leaf-CDF · H-MULTI (n=663) | 78.081631 · Empirical mean · H-CURRENT (n=633) |
| pass_td | 0.844880 · Leaf-CDF · H-MULTI (n=664) | 0.810241 · Leaf-CDF · H-RECENT (n=664) | 0.788839 · C02 · H-MULTI (n=663) | 0.887704 · HGB-L1 · H-CURRENT (n=633) |
| pass_cmp | 5.827708 · HGB-count · H-RECENT (n=664) | 5.660122 · HGB-L1 · H-RECENT (n=664) | 5.956259 · Leaf-CDF · H-MULTI (n=663) | 6.798419 · Empirical mean · H-CURRENT (n=633) |
| pass_att | 8.488384 · HGB-count · H-MULTI (n=664) | 8.360291 · HGB-count · H-MULTI (n=664) | 8.657617 · Leaf-CDF · H-MULTI (n=663) | 10.060587 · HGB-count · H-CURRENT (n=633) |
| pass_int | 0.557229 · Leaf-CDF · H-CURRENT (n=664) | 0.579819 · C02 · H-CURRENT (n=664) | 0.647059 · Empirical lower_median · H-CURRENT (n=663) | 0.665087 · GLM-law · H-CURRENT (n=633) |
| rush_yd | 16.717362 · Leaf-CDF · H-MULTI (n=2229) | 17.646709 · C02 · H-MULTI (n=2188) | 16.833255 · C02 · H-MULTI (n=2129) | 19.430713 · Empirical lower_median · H-CURRENT (n=2201) |
| rush_att | 2.867205 · Leaf-CDF · H-RECENT (n=2229) | 2.991316 · Leaf-CDF · H-MULTI (n=2188) | 3.111790 · Leaf-CDF · H-MULTI (n=2129) | 3.453078 · Empirical mean · H-CURRENT (n=2201) |
| rec | 1.179448 · Leaf-CDF · H-MULTI (n=5294) | 1.268748 · C02 · H-MULTI (n=5094) | 1.281312 · Leaf-CDF · H-MULTI (n=5062) | 1.462505 · Empirical lower_median · H-CURRENT (n=5094) |
| rec_yd | 15.309218 · Leaf-CDF · H-MULTI (n=5294) | 16.383392 · Leaf-CDF · H-MULTI (n=5094) | 16.692414 · C02 · H-MULTI (n=5062) | 18.169745 · HGB-L1 · H-CURRENT (n=5094) |
| rush_rec_yd | 19.710794 · HGB-L1 · H-MULTI (n=5294) | 20.704934 · HGB-L1 · H-RECENT (n=5094) | 20.955738 · HGB-L1 · H-MULTI (n=5062) | 23.884879 · HGB-L1 · H-CURRENT (n=5094) |
| nick-chart-ppr-v1 | 4.365366 · Leaf-CDF · H-MULTI (n=5937) | 4.506137 · Leaf-CDF · H-RECENT (n=5742) | 4.473310 · Leaf-CDF · H-MULTI (n=5713) | 5.173704 · C02 · H-CURRENT (n=5718) |
| anytime_td | 0.142770 · HGB-probability · H-MULTI (n=5294) | 0.145935 · GLM-law · H-RECENT (n=5094) | 0.142731 · HGB-probability · H-MULTI (n=5062) | 0.153940 · HGB-probability · H-CURRENT (n=5094) |

2025: the same-history C02 gains for current-season interceptions, receptions and chart PPR reverse against Leaf-CDF. In 2024 anytime-TD GLM RECENT Brier0.145935 beats fixed-2026 HGB MULTI0.146578; their current-season ordering is opposite. See each seasonal fixed-choice/reversal file for exact matching and all adverse results.

2022 has no admitted2021 data. Its RECENT values are explicitly source-limited proxies, not the completed preceding-year comparison. Complete requested history effects cannot be inferred from their equality.

[All seasonal rows](SEASON_RESULTS_2022_2026.csv) · [Method/year inventory](METHOD_YEAR_INVENTORY.csv) · [Shared subgroup summaries](SHARED_SUBGROUP_RESULTS.md) · [Opponent-information experiment](qualified-defense-information-v1/EXECUTED_RESULTS.md) · [Permanent results index](results-index/README.md).
