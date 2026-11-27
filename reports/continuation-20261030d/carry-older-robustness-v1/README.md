# Does the carry training-role repair hold up in older seasons?

This is a new paired analysis of existing 2022–2025 predictions. It tests the retained QB/RB-only L1 training-role repair against both original broad-training HGB L1 with the same history/information policy and the strongest observed same-season full-primary carry control. Strongest controls were fixed before paired subgroup losses were decoded; they were not reselected inside QB/RB/WR/TE or top-player bands. These are exposed descriptive benchmarks, not a recreated earlier model-selection policy.

The main table fixes the repair to **H-MULTI/common feature memory**, matching the accepted 2026 emphasis. Every current/recent/multi/strict contrast is retained in the linked JSON/CSV; no winning older-history variant is silently substituted. Negative deltas favor the repair. Native MAE is in carries, with candidate-minus-control signs.

| Season | Primary paired n | Repair MAE | Delta vs original HGB L1 | Delta vs strongest control | Strong-control week95 interval |
|---|---:|---:|---:|---:|---|
|2025|2229|2.9071|-3.3793|0.0399|[0.0132, 0.0641]|
|2024|2188|3.0118|-3.4599|0.0205|[-0.0083, 0.0476]|
|2023|2129|3.1431|-3.4185|0.0313|[0.0002, 0.0650]|
|2022|2201|3.5424|-2.5928|0.0893|[-0.0459, 0.2599]|

The original L1 comparison isolates the registered training-role/fallback package at the same policy; the strongest-control comparison can use another history/product/update mechanism and is a practical benchmark. Both are necessary: improvement over a collapsed or weak original does not establish the strongest useful forecast.

| Season | Position/population | Repair MAE | Delta vs original | Delta vs strongest | n |
|---|---|---:|---:|---:|---:|
|2025|QB/primary|1.7903|-1.5455|0.0463|664|
|2025|RB/primary|3.3810|-4.1574|0.0372|1565|
|2025|WR/extended|0.6418|0.4877|0.4958|2480|
|2025|TE/extended|0.6238|0.5318|0.5414|1249|
|2024|QB/primary|1.8254|-1.7168|0.0182|664|
|2024|RB/primary|3.5287|-4.2193|0.0215|1524|
|2024|WR/extended|0.6436|0.4648|0.4710|2405|
|2024|TE/extended|0.5630|0.5098|0.5313|1165|
|2023|QB/primary|1.8471|-1.5993|0.0628|663|
|2023|RB/primary|3.7292|-4.2412|0.0170|1466|
|2023|WR/extended|0.8403|0.6507|0.6569|2448|
|2023|TE/extended|0.8186|0.7272|0.7498|1148|
|2022|QB/primary|2.1260|-1.4140|-0.0404|633|
|2022|RB/primary|4.1142|-3.0687|0.1417|1568|
|2022|WR/extended|1.1982|0.9928|0.9265|2352|
|2022|TE/extended|1.2409|1.1344|1.1516|1174|

WR/TE remain in the extended population, including their structural low counts, nonzero carries and early exits. They are not removed to make the specialization look better. Their fallback/exposure composition differs from QB/RB and is reported separately.

| Season | Primary view | n | Repair MAE | Strong-control MAE | Delta | Repair fallback rows | Fallback contribution within this view |
|---|---|---:|---:|---:|---:|---:|---:|
|2025|full_system|2229|2.9071|2.8672|0.0399|0|0.0000|
|2025|own_learned_only|2229|2.9071|2.8672|0.0399|0|0.0000|
|2025|all_three_common_learned|2157|2.9014|2.8535|0.0479|0|0.0000|
|2025|any_model_fallback|72|3.0794|3.2778|-0.1984|0|0.0000|
|2024|full_system|2188|3.0118|2.9913|0.0205|0|0.0000|
|2024|own_learned_only|2188|3.0118|2.9913|0.0205|0|0.0000|
|2024|all_three_common_learned|2132|3.0218|2.9855|0.0364|0|0.0000|
|2024|any_model_fallback|56|2.6294|3.2143|-0.5849|0|0.0000|
|2023|full_system|2129|3.1431|3.1118|0.0313|0|0.0000|
|2023|own_learned_only|2129|3.1431|3.1118|0.0313|0|0.0000|
|2023|all_three_common_learned|2058|3.1605|3.1118|0.0487|0|0.0000|
|2023|any_model_fallback|71|2.6381|3.1127|-0.4746|0|0.0000|
|2022|full_system|2201|3.5424|3.4531|0.0893|257|0.6333|
|2022|own_learned_only|1944|3.2936|3.1913|0.1023|0|0.0000|
|2022|all_three_common_learned|1812|3.3038|3.1327|0.1711|0|0.0000|
|2022|candidate_fallback_only|257|5.4241|5.4330|-0.0089|257|5.4241|
|2022|any_model_fallback|389|4.6537|4.9454|-0.2917|257|3.5835|

Common-learned rows require the repair, same-policy original and fixed strongest control all to have learned nonfallback forecasts. Own-learned and fallback views have different masks and are not credited as paired history comparisons. Each pair retains exact query/scored membership hashes and shared actual/position checks. Error summaries inside each pair use identical supported rows; unresolved query rows remain in the outer coverage counts.

| Season | Primary cohort | n | Repair MAE | Delta vs original | Delta vs strongest |
|---|---|---:|---:|---:|---:|
|2025|top10|180|4.3642|-10.9275|0.1698|
|2025|top15|270|4.4796|-10.6223|0.0944|
|2025|top20|360|4.1891|-10.5345|0.0697|
|2024|top10|180|4.9938|-11.5951|0.0882|
|2024|top15|270|5.2238|-10.7502|0.0498|
|2024|top20|360|5.0167|-10.2361|0.0667|
|2023|top10|180|4.5665|-10.0590|0.0165|
|2023|top15|270|4.7023|-9.8183|0.0653|
|2023|top20|360|4.6225|-9.4818|0.0392|
|2022|top10|160|5.7030|-8.4524|0.4148|
|2022|top15|240|5.5167|-8.2954|0.4558|
|2022|top20|320|5.3446|-7.8952|0.3498|

Top-player membership reuses the already frozen season-specific prior-carry rankings. It does not select stars by realized production, create authentic historical exante issuance or prove training only on stars helps. Strict-policy forecasts remain a complete information-policy comparison, while these common frozen selectors may use older opportunity history.

The 2025 full specialization source is overlaid with the preserved correction packet: all base specialization rows are discarded, not numerically blended. The 2023 source is the complete 18-week recombination, not the stopped Weeks 1–16 parent. 2022 includes 271 supported games; its H-RECENT arm lacks 2021 and is a source-limited 2022 proxy. The present test compares methods within that actual proxy and does not call it a completed requested older-history contrast.

MAE, signed bias, MSE/RMSE and tails remain native point diagnostics; these absolute-loss point outputs are not authenticated median distributions or genuine conditional-mean products. Paired week bootstrap uses 500 draws / seed 1703 with 18 weekly blocks where supported; game-cluster intervals are sensitivity checks. Intervals do not adjust for previous research exposure, control selection or multiplicity.

[Accepted 2026 strongest-control comparison](../../continuation-20261030b/carry-strong-control-comparison-v1/README.md) remains unchanged: the role repair beat the previous empirical mean on 844 matched QB/RB rows (3.091618 versus 3.128691), while orderedCDF was stronger at 3.059242. Extended WR/TE repair error 0.619436 lost to mean 0.291669 and ordered CDF 0.101583. No 2026 replay was executed here.

Run state **COMPLETE**; completed seasons [2025, 2024, 2023, 2022], remaining []. The saved-row run used 69.29 wall seconds, 69.27 CPU seconds, 254.8 MiB peak RSS and one thread, within the declared 180 second / 1 GiB limit if complete. It produced 1,608 paired aggregate views, zero new univariate score artifacts, zero fits/inferences/forecasts and zero current 2026 Week 8 label reads. Source retention/readiness limits remain those of the original archives; this replay grants no production admission.

Evidence: [frozen protocol](FROZEN_PROTOCOL.json), [run receipt](RUN_RECEIPT.json), [all paired comparisons CSV](PAIR_ANALYSIS.csv). Per-season `PAIR_ANALYSIS_YYYY.json` retains all paired native errors, support, fallback decomposition, exact row hashes and uncertainty. No player-level records or private locators are published.

[Reference tie disclosure](REFERENCE_TIE_DISCLOSURE.json) preserves the originally fixed choice. In 2022 the empirical mean ties across the source-limited current/recent/multi history aliases; this is not three independent winning learners or evidence that older history is useless.

To reproduce from approved retained inputs, supply an explicit private manifest to `tools/analyze_carry_older_pairs.py prepare` and then `run`, with `--public-root` naming a fresh output directory. Each season needs the flat forecast file, public score source and previously frozen cohort membership packet; 2025 additionally needs the entire corrected carry overlay and its score receipt. Public protocol bindings record hashes and safe artifact IDs rather than private paths. The CLI has no fitting or future-capture action. Changed inputs or comparator contracts require a new version.

[Independent review](../CARRY_OLDER_INDEPENDENT_REVIEW.json) passed all 1,608 aggregate identity/delta/fallback checks, 804 common masks, 1,336 bootstrap intervals and all four global control choices. A separate corrected 2025 raw replay verified all 408 paired views and 4,896 native fields plus game sensitivity. It used 23 seconds and 278 MB, with zero fits; it did not repeat the full four-season source scan. The main 2024 and 2022 nominal intervals cross zero, so observed losses are not a significance or permanent-ranking claim.
