# H executed findings — publication interruption checkpoint

Recorded 2026-10-31 04:06:15 UTC. Accepted `d1aa4cea` and all earlier published evidence remain unchanged.

**New time coverage:** Week 5 now has 617 retained provider-labelled thresholds across **14 of 15 games**, with 606 qualified outcomes. Original picks won **218/393 (55.47%)**. Thursday lacks authenticated pregame capture in the inspected sources.

Across the separate rolling Weeks 5–7 panels, original recorded selections now total **663/1,194 (55.53%)** across 42 games:

| Selected side | Selected | Wins | Losses | Decided | Hit rate |
|---|---:|---:|---:|---:|---:|
| Over | 684 | 347 | 316 | 663 | 52.34% |
| Under | 542 | 316 | 215 | 531 | 59.51% |
| Combined | 1,226 | 663 | 531 | 1,194 | 55.53% |

Thirty-two selected records remain unresolved. These are statistical crossings, not verified sportsbook settlement or profitability. The older fixed-Friday Week 7 panel is excluded from these cumulative counts. The original result is not attributed to V2 candidates.

On those same original-selected opportunities, saved adjusted directions equal every decided original side. Raw directions win 655/1,192, versus original 661/1,192 on that exact common mask; always Under wins 632/1,194 (52.93%). Filtering and learner effects remain separate.

## Probability skill against useful references

On **80 identical passing-attempt offers out of 84 outer opportunities**, multiseason Leaf Brier is **0.255654**, worse than both neutral **0.250000** and earlier-estimated prevalence **0.252687**, despite improving GLM **0.339025**. The strict-current Leaf alternative is **0.242276**. Strict-current changes the information policy; this is not a pure fit-window conclusion.

Across the ten numeric categories with matching offered thresholds, multiseason Leaf/C02 beat neutral in only two (passing TD and interceptions), and beat earlier prevalence in seven (passing attempts, completions and interceptions reverse). Calibration and discrimination remain separate: passing-attempt AUC is 0.518449 for multiseason Leaf and 0.609131 for strict-current on those 80 decisive cases. No calibrator was fitted using evaluated outcomes. Three exposed weeks remain insufficient for the registered whole-week interval. Market probabilities/prices are unavailable.

## Actual upcoming capture and owner admission

Fresh HTTP/consumer-function checks at 03:38:58 UTC reproduced all **1,945 existing served values**: **1,789 future-game forecasts across 13 games**, plus **156 frozen forecasts**. There are **zero new MAE-profile rows**. These are existing October 28 forecasts, not a new capture. Eleven compatibility/rollback checks passed; the current closed consumer rejects count medians and an extra separate-mean field. Those releases require an owner-controlled compatible wire version.

The latest inspected parent, run 41104520104, ran outside its morning window and skipped enqueue. Exit 78 also preserved the existing handover, durability and publication guards. [Diagnosis and owner action were delivered/read back](https://github.com/NickNicky19/NFL-forecasting-V2/pull/1#issuecomment-6538524680). Acknowledgement/new execution/admission is unobserved. The next configured October 31 morning slot remains future at this check; configuration is not execution. The prepared owner policy is V2.1, with no new blanket waiting period or universal incumbent-win prerequisite. Production and the retained lease remain unchanged.

## Publication and recoverability limits

The managed workspace went offline while the full H package was being assembled. Before the interruption, producers reported **28 canonical sources / 104,238 evaluation views**, zero estimator fits/model-inference calls/new original captures. Independent checks completed for the new source/method/baseline/three-week P1 evidence and served-function parity. Final 414-view P2, metadata and appended-index checks remain pending.

**This file preserves executed findings and known hashes; it does not claim the uncommitted canonical arrays or private derivatives have been published or fully restored.** The current published permanent index remains [the accepted G index](../completion-20261031g/results-index-v1/INDEX_MANIFEST.json). Resume by verifying retained files and finishing publication, without rerunning completed NFL fits or source grading.

W1–4 original-source gaps, historical offers/prices, missing exact-recipe seasonal work and the existing 53-part private restoration gate remain explicit. No raw restricted records, private locators, new scheduler, merge, deployment or wagers are introduced.

Machine-readable interruption state:

```json
{
  "schema": "v2-interruption-checkpoint-v1",
  "recorded_at_utc": "2026-10-31 04:06:15 UTC",
  "accepted_parent": "d1aa4cead94472cf5706ee91f4faf7a7ecfee6e9",
  "state": "EXECUTED_H_FINDINGS_FULL_CANONICAL_PUBLICATION_PENDING_WORKSPACE",
  "current_remote_results_index": "reports/completion-20261031g/results-index-v1/INDEX_MANIFEST.json",
  "new_time_coverage": {
    "season": 2026,
    "week": 5,
    "games_supported": 14,
    "games_intended": 15,
    "thresholds": 617,
    "qualified_actuals": 606,
    "unknown_actuals": 11,
    "source_choice": "Latest authoritative server-retained snapshot before each game T90; frozen before new grading",
    "missing_game_reason": "Thursday predated this production repository's server existence; no original capture authenticated in inspected sources"
  },
  "original_rolling_w5_w7": {
    "games": 42,
    "intended_games": 43,
    "offers": 1936,
    "qualified_actuals": 1881,
    "selected": 1226,
    "wins": 663,
    "losses": 531,
    "decided": 1194,
    "unresolved": 32,
    "over": {
      "selected": 684,
      "wins": 347,
      "losses": 316,
      "decided": 663
    },
    "under": {
      "selected": 542,
      "wins": 316,
      "losses": 215,
      "decided": 531
    },
    "evidence": "Original recorded sides, statistical crossing; prices/bookmaker settlement unavailable. FixedFridayW7 excluded."
  },
  "probability_passing_attempts": {
    "period": [
      5,
      6,
      7
    ],
    "qualified_mask_n": 80,
    "outer_offers": 84,
    "half_scaled_categorical_brier": {
      "multiseason_leaf": 0.2556543135953243,
      "neutral": 0.25,
      "earlier_prevalence_rounded_6dp": 0.252687,
      "GLM_rounded_6dp": 0.339025,
      "strict_current_leaf": 0.24227600311371122
    },
    "decisive_auc": {
      "multiseason_leaf": 0.5184490306441526,
      "strict_current_leaf": 0.6091307066916823
    },
    "scope": "Same supported offer masks. Strict-current changes information policy, not just fit-window length. Descriptive exposed3week evidence; no evaluation-outcome calibration."
  },
  "matched_original_selected_controls": {
    "original_wins": 663,
    "original_decided": 1194,
    "adjusted_direction_exactly_matches_original_decided": 1194,
    "raw_wins": 655,
    "raw_decided": 1192,
    "original_on_raw_common_decided_wins": 661,
    "always_under_wins": 632,
    "always_under_decided": 1194
  },
  "actual_served_readback": {
    "checked_at_utc": "2026-10-31T03:38:58Z",
    "payload_sha256": "369fec9caec012cb292284006a60bb25727d6d9d853f00560dbffe57f1ea1fa4",
    "rows": 1945,
    "future_rows": 1789,
    "future_games": 13,
    "frozen_rows": 156,
    "new_MAE_profile_rows": 0,
    "exact_served_function_values_checked": 1945,
    "compatibility_and_rollback_checks": 11,
    "scope": "HTTP bytes and actual consumer functions, not browser DOM or new inference; no NFL outcome values used"
  },
  "owner_failure": {
    "run_id": 41104520104,
    "due": false,
    "observed_chicago": "2026-10-30T13:10:19.451402-05:00",
    "enqueue": "SKIPPED",
    "exit_code": 78,
    "reasons": [
      "QUALIFIED_HOSTED_HANDOVER_NOT_ACCEPTED",
      "PRIVATE_DURABILITY_NOT_VERIFIED",
      "EXACT_PUBLICATION_REVIEW_ABSENT"
    ],
    "notice": "https://github.com/NickNicky19/NFL-forecasting-V2/pull/1#issuecomment-6538524680",
    "owner_acknowledgement": "NOT_OBSERVED",
    "prepared_policy": "research-informed-stat-point-mae-v2.1",
    "new_capture_or_admission_observed": false
  },
  "local_scientific_inventory": {
    "canonical_sources_reported": 28,
    "views_reported": 104238,
    "estimator_fit_calls": 0,
    "new_point_model_inference_calls": 0,
    "new_original_pregame_captures": 0,
    "publication": "Canonical arrays, helper changes and appended index not yet committed; this status is not their recoverability attestation",
    "independent_scope": "W5source/control/admission/method/fullLeaf; earlier-only baselines; three-week P1/proper aggregation; served-function parity. Final414P2/metadata/index review pending."
  },
  "safe_known_source_hashes": [
    {
      "logical_path": "source-expansion/SCORES.json",
      "sha256": "1c6f2f227fa6a387abab864345a64c3494a1cec979f1b808bcd2fcf8d223a1f1"
    },
    {
      "logical_path": "actual-method-w5/method-comparison-v1/SCORES.json",
      "sha256": "9cc60343d64ccaeca705d7fbf9a354cd66a30c476711d8c5e0b668df5507dd40"
    },
    {
      "logical_path": "actual-method-w5/complete-leaf-law-v1/SCORES.json",
      "sha256": "f24a531b17bd856bf8c8ea31730c8c8b72c6c9dfea988eea0f8955d06cbcc81f"
    },
    {
      "logical_path": "probability/reference-v2/SCORES.json",
      "sha256": "eccb187962988abc8e97db13c2659397de3a1ac583a699bd2d591d8e289a79af"
    },
    {
      "logical_path": "probability/w5-reference-v1/SCORES.json",
      "sha256": "aaa15ef851a4f03e5bd2f66a4a72914011b53b3b29e9495533954a7e5c776eb9"
    },
    {
      "logical_path": "probability/w5-w7-cumulative-v1/SCORES.json",
      "sha256": "3953322da1dbca626ee660f96456d78d2afa2151e3dbf1393d4ce12a5e632717"
    },
    {
      "logical_path": "probability/w5-w7-primary-p2-v1/SCORES.json",
      "sha256": "b942419990ac1acaf9c223d684d6ac5cf9c9debc4f2d948dc7507fe75a3ebf5c"
    }
  ],
  "remaining": [
    "Recover actual workspace access and verify all retained bytes before continuing publication; do not refit completed studies",
    "Finish pending P2/metadata review, consolidate all category decisions, append permanent index and run final CI",
    "W1–4 original captures, historical authenticated offers/prices and exact-recipe fit/recovery dependencies remain",
    "Preserve existing owner scheduler/lease/provisional policy; mandatory own operational checks remain, no new blanket waiting period"
  ]
}
```
