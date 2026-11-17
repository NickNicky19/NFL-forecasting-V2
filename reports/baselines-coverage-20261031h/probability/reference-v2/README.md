# Actual-line probability references: what the models beat

**The stronger comparison changes the conclusion:** on the same rolling Weeks 6–7 H-MULTI offers, Leaf and C02 improve Brier over GLM in nine of ten categories, but each beats the neutral 50/50 reference in only two: passing touchdowns and interceptions. Each beats the earlier same-position prevalence reference in eight categories, losing passing attempts and completions. These are observed differences on two exposed weeks, not established future superiority.

| Category | Paired n | Neutral Brier | Earlier prevalence | Leaf Brier | C02 Brier | GLM Brier |
|---|---:|---:|---:|---:|---:|---:|
| pass_att | 52 | 0.250000 | 0.261553 | 0.264387 | 0.272847 | 0.360829 |
| pass_cmp | 52 | 0.250000 | 0.281845 | 0.289413 | 0.297675 | 0.353967 |
| pass_int | 52 | 0.250000 | 0.250597 | 0.248148 | 0.249898 | 0.247129 |
| pass_td | 52 | 0.250000 | 0.237526 | 0.226881 | 0.223789 | 0.232310 |
| pass_yd | 52 | 0.250000 | 0.298638 | 0.287957 | 0.292684 | 0.323927 |
| rec | 315 | 0.250000 | 0.277368 | 0.254335 | 0.254456 | 0.266086 |
| rec_yd | 314 | 0.250000 | 0.277225 | 0.260122 | 0.259786 | 0.274466 |
| rush_att | 76 | 0.250000 | 0.314116 | 0.284134 | 0.280570 | 0.421870 |
| rush_rec_yd | 75 | 0.250000 | 0.313554 | 0.278108 | 0.279114 | 0.313837 |
| rush_yd | 147 | 0.250000 | 0.266078 | 0.259132 | 0.259451 | 0.284021 |

For passing attempts (52 matched offers), Leaf Brier is **0.264387**, worse than neutral **0.250000** and earlier prevalence **0.261553**, even though it beats GLM **0.360829**. Leaf minus neutral is +0.014387; its game-cluster sensitivity 95% interval is [−0.015123, +0.043897]. The difference from earlier prevalence is +0.002835, interval [−0.025923, +0.031593].

For passing touchdowns (52 offers), Leaf improves 0.250000→0.226881 against neutral; difference −0.023119, interval [−0.047364, +0.001127]. Against earlier prevalence 0.237526, its difference is −0.010644, interval [−0.043528, +0.022240]. These intervals show how limited two weeks remain. The registered week-based interval is unavailable with only two clusters; game intervals are descriptive sensitivity analyses without multiplicity or selection adjustment.

The constant reference assigns Over=0.5, Under=0.5, Push=0 at each threshold. Its half multiclass Brier is 0.25 for decisive outcomes, 0.75 for pushes; push log loss is infinite. It is a threshold-local neutral reference, not a global CDF or an authenticated bookmaker forecast. No statistical pushes occur on the retained evaluated panel.

The prevalence reference counts earlier positively verified participants at the same position and exact target, evaluating their official full-game outcomes against the query line. Every consumed kickoff+7-day availability time must be strictly before the actual decision clock. H-CURRENT uses 2026, H-RECENT uses 2025–2026, H-MULTI starts in 2022. Strict-current candidate rows use a separate 2026-only reference with no older football priors, features or calibration. Empty history explicitly falls back to the neutral reference; it never borrows older seasons. No smoothing was added, so genuine zero-probability log losses remain infinite.

Same-position historical participants may differ from offered stars, promoted roles or replacements. This simple reference measures whether additional forecasting complexity improves the offered-event score; it does not isolate a causal player or defense effect. Current-season fitting with older feature memory remains different from strict-current information. The machine tables preserve both, every history, weekly reversals and all supported parametric law subsets; no method or sparse case was removed after scoring.

`FULL` means the entire **qualified saved-law/outcome comparison mask**, not every offered opportunity. [Outer coverage](MASK_AND_OUTER_COVERAGE.csv) retains the source universe, law admission failures and unavailable outcomes. For example, a 52-row cumulative passing comparison is drawn from a larger original source offer universe. LEARNED and PRIOR views partition that mask using explicit retained-law origins; baseline empty-prefix fallback is a separate field.

Fixed ten-bin per-region reliability diagrams and decisive-outcome rank AUC are [separate diagnostics](CALIBRATION_AND_DISCRIMINATION.json). The AUC uses only actual nonpush outcomes and over/(over+under); it does not replace the three-region proper score. Constant forecasts have AUC 0.5 if both classes occur and N/A for a single class. These diagnostics do not fit or validate a calibrator.

This wave evaluates probabilities only: it adds no selected-side, price-aware, top-K or settlement strategy. Existing G original selections and P1/P2 scorecards remain unchanged. Authenticated price/status evidence is absent, so market probabilities, EV, ROI and CLV remain unestablished. No point-to-probability transformation, model inference, fit, capture or Week 8 outcome read occurred.

[All histories and strict arms](CUMULATIVE_PRIMARY_BASELINE_TABLE.csv) · [Canonical scores](SCORES.json) · [All paired differences and uncertainty](PAIRED_REFERENCE_COMPARISONS.csv) · [Frozen protocol](FROZEN_PROTOCOL.json) · [Resource/evidence receipt](RUN_RECEIPT.json).

The first preparation attempt failed on a path-type typo before reading prior values or G losses and produced no scores. Its original source, protocol and failure receipt remain in `../reference-v1/`; this successful independently identified version preserves them.
