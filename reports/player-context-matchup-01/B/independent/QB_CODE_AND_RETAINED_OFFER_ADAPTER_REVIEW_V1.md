# Independent QB code and retained-offer adapter review

No fits, model restoration/inference, threshold scorer, source collection or upstream edits were performed. This review inspected the frozen producer and retained local schemas. [The executed inventory](RETAINED_QB_OFFER_INVENTORY_V1.json) contains safe counts/hashes; its CLI/`iter_offers` helper does not publish restricted rows or compute selections.

## Retained offer board

| Panel | Retained source ID | CMP offers | ATT offers | Games | Label compatibility with new public QB panel |
|---|---|---:|---:|---:|---|
| 2026 rolling Week 5 | `B_RETAINED_2026_W5_QB_OFFERS` | 28 | 28 | 14 | All 56 exact numeric matches |
| 2026 rolling Week 6 | `B_RETAINED_2026_W6_QB_OFFERS` | 28 | 28 | 14 | All 56 exact numeric matches |
| 2026 rolling Week 7 | `B_RETAINED_2026_W7_QB_OFFERS` | 28 | 28 | 14 | All 56 exact numeric matches |
| 2026 Week 8 full original-provider board | `B_RETAINED_2026_W8_QB_OFFERS` | 28 | 28 | 14 | All 56 exact numeric matches |

These are **224 retained offers**, including originally unselected opportunities. Each has a supported old outcome and exact GSIS/game identity, without duplicate game/player/category/line rows. This is inventory/label parity, **not admission of new predictions at earlier quote times**. Week 5 is missing one of 15 scheduled games; Weeks 1–4 have not been added. Do not shrink the new retrospective Week 8 board automatically to the older B captured-method overlap of 26+26 offers/13 games. Keep that pairwise overlap separate.

The owner-local sources are the existing W5, W6 and rolling W7 `JOINED_ROWS.json.gz` packets (`rows` array), plus the final Week 8 `LOCAL_GRADED_ROWS.json.gz` packet filtered to `panel=ORIGINAL_PROVIDER_T90`, `strategy=original`, no `method_key`, and CMP/ATT. Exact approved private read paths were delivered internally to the root executor and are not republished here.

For retained method controls, W5/W6/rolling W7 `GRADED_METHOD_ROWS.json.gz` uses **`graded[method_tag]`**, not a flat `rows` array. Bind a tag to `FROZEN_SELECTIONS_AND_K.json.gz` → `plans[tag].recipe` and the corresponding public score/selection-freeze receipt. The per-row dictionaries do not independently identify their method. Complete Leaf exact-line probability controls are in the respective `GRADED_COMPLETE_LEAF_LAWS.json.gz` mappings and public complete-law bindings. The older fixed-Friday W7 method comparison v2 is a different horizon from rolling W7 v1; neither replaces the other. Current scoreboard supersession/panel bindings remain authoritative.

## Matching and timing requirements

Use event/game, exact GSIS player, category, full-game/overtime/scoring contract, exact retained decimal line, line source, immutable source head and source server clock as offer identity; retain decision/capture clocks separately. Source-row ordinals locate evidence within a file and are **not** cross-method identity. Do not deduplicate by player name, round a line or silently choose a later snapshot.

For W5–7, the existing known-target-time reconstruction contract uses `source_server_clock` as retrospective decision time. An age measured to the foreknown scheduled kickoff may qualify earlier only when every consumed source, fit label, prior, transform, calibration and routing dependency was eligible by that decision time and the eligible prefix is unchanged. A generic global-source timestamp is insufficient to prove an E0 feature was actually consumed. A nominal weekly fit after the quote needs the exact unchanged earlier-prefix proof or a separate valid reconstruction; it is not original issuance.

Week 8 preserves both `source_server_clock` and the saved `decision_time`. Its early saved forecasts, later provider-labelled thresholds and original operational leans remain different evidence products. Provider labels do not establish authentic bookmaker quote age/executability or venue settlement. Missing prices continue to block unsupported EV/ROI claims.

Before scoring, require exact actual/label-version parity or preserve a versioned correction/overlap; all 224 inspected old/new labels currently match. Preserve unavailable queries, timing/context exclusions, abstentions, pending/unknown/push states and coverage. Compare common rows and full-system coverage separately. Keep the original selected side unchanged; new point/probability choices are newly executed retrospective rules. A saved point is not a probability.

The extractor proposal is deliberately limited: accept four explicit retained input paths and one public derived-input path, verify hashes/schema/identities, return the retained rows in memory to the root-owned scorer, and write **only** a public-safe inventory manifest. The root owns any restricted joined-row persistence and existing scoring integration. No second grader is proposed.

## Frozen QB code findings

**No obvious target-game outcome or realized-mix leakage was found in the inspected producer.** Context/training histories use strict earlier availability; prior-game offense-quality references are built at each prior game's own cutoff. Inference combines predicted context mix and a common predicted attempt law. Binomial thinning of a gamma-Poisson exposure law yields the stated count marginal under the registered assumptions. Context weights/coefficients remain point estimates, as disclosed. This is code inspection, not complete independent re-inference or proof of forecast skill.

Three scope clarifications are appropriate without changing frozen predictions:

- E2 currently takes the last 16 **observed eligible QB-derived team-game groups**, not an explicitly joined scheduled-game spine. Preserve and qualify the frozen “scheduled” wording. Do not claim the older scheduled-window D1/D2 comparison was completed.
- `latest_source_available` is a global eligibility upper bound for E0. Its actual own-history/fit-prior lineage should be separately exposed. E1–E3 and conditional components consume global priors/context; their shared clocks still require per-query cutoff checks.
- P3 is own-only **coefficient training**, with shared derived inputs, exposure and P1 fallback. It is not a strict player-only-information experiment. Its fallback and sparse/no-history views remain explicit.

One specific portable typing defect requires a versioned consumer repair: `CompletionModel.restore` assigns coefficient offsets by iterating `payload['levels'].items()`. JSON object order is not semantic. The frozen producer writes `team → opponent → player_id` and preserves that order, so current pilot bytes are not demonstrated to be corrupted. But a canonical consumer sorting object keys would silently remap coefficients. For example, with team levels `[AAA, DDD]`, opponent `[BBB]`, player `[Q]` and four identity coefficients `[1,2,3,4]`, the active identity sum for AAA/BBB/Q changes from **8 to 6** under the old restore logic after key reordering. No NFL model or observation is used in this counterexample. Preserve original producer/parameters and add explicit source-bound field order plus reordered-object parity in a separate typed adapter before portable operational use. The root has acknowledged that remedy; this review did not edit the active core.

Additional bounded hardening suggestions: reject noninteger/nonfinite context counts in the loader rather than relying solely on the source preflight; retain solver failure/convergence status; verify immutable fit/chunk hashes on resume. All **77** inspected pilot conditional-fit receipts report finite coefficients and successful optimization, so no actual nonconvergence is alleged. Current pilot thread enforcement remains disclosed rather than silently rerun. These software/metadata findings do not erase the earlier negative calibration/ranker, HGB or actual-line evidence, introduce a new blanket release waiting period, or imply scientific/operational admission.
