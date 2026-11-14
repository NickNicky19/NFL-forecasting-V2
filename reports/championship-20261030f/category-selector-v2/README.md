# Chronological category-selection policy: prior-season versus current score memory

All twelve categories, fixed2026 regular-season Weeks1–7/107games. This is an exposed historical reconstruction using120 exact H-MULTI output recipes with complete2025and2026 weekly evidence. It adds no fits, new forecasts or independently observed games. It is **not an original issued policy or fresh prospective confirmation**. Method-selection performance is separate from static-method rankings and from Over/Under pick selection.

**Result:** earlier available current-season score memory beats frozen2025best in4categories and loses8. Pooled2025+available2026 memory improves passingyards, loses passingattempts/completions and ties the other9categories. No universal memory winner is established.

| Category | n | Frozen2025best | Earlier2026score-memory | Delta vs frozen | Pooledprior+current | Delta vs frozen |
|---|---:|---:|---:|---:|---:|---:|
| anytime_td | 2118 | 0.143144 | 0.145145 | +0.002000 | 0.143144 | +0.000000 |
| nick-chart-ppr-v1 | 2359 | 4.502391 | 4.589546 | +0.087156 | 4.502391 | +0.000000 |
| pass_att | 242 | 8.406754 | 8.132009 | -0.274745 | 8.481153 | +0.074399 |
| pass_cmp | 242 | 5.576454 | 5.433347 | -0.143108 | 5.661762 | +0.085308 |
| pass_int | 242 | 0.603306 | 0.629985 | +0.026679 | 0.603306 | +0.000000 |
| pass_td | 242 | 0.830579 | 0.863636 | +0.033058 | 0.830579 | +0.000000 |
| pass_yd | 242 | 68.732925 | 66.729270 | -2.003655 | 68.332033 | -0.400892 |
| rec | 2118 | 1.254958 | 1.259207 | +0.004249 | 1.254958 | +0.000000 |
| rec_yd | 2118 | 16.198772 | 16.572238 | +0.373466 | 16.198772 | +0.000000 |
| rush_att | 844 | 3.059242 | 3.049763 | -0.009479 | 3.059242 | +0.000000 |
| rush_rec_yd | 2118 | 20.125661 | 20.469324 | +0.343662 | 20.125661 | +0.000000 |
| rush_yd | 844 | 16.750000 | 17.047393 | +0.297393 | 16.750000 | +0.000000 |

Native errors are MAE except anytime rushing-or-receiving TD, which uses Brier. Rows and categories are not independent trials. With only seven current week clusters, the registered minimum for week-bootstrap uncertainty is unmet; no significant or universal winner is claimed. Exact common membership is checked for all3000 recipe/week cells across2025+2026, including actual **values**, not merely equal row counts.

## What the policies actually knew

At each weekly earliest-game fitting origin, an entire scoring week becomes eligible only after its **last game kickoff+7days is strictly earlier than that origin**. Current score memory is empty inWeeks1and2, then[1] atWeek3,[1,2] atWeek4,…,[1–5] atWeek7. It never uses Week6 or7 outcomes to choose a Week7 procedure. The fixedprior policy uses only the complete2025 score panel. The pooled policy weights2025andeligible2026 by their actual supported outcome counts.

Current-memory startup uses the named base Leaf-CDF H-MULTI lower median (or event law for anytimeTD). All candidate forecasts themselves are H-MULTI with older feature memory. Thus this is **current-season performance memory for choosing among historically trained forecasts**, not a strict current-football-information model. Ties within1e−12 use the frozen stable target/procedure/product ID ordering; no hindsight weekly winner or posthoc support gate is used.

The passing-yard current-memory sequence uses Leaf-CDF forWeeks1–4, then HGB absolute-error forWeeks5–7, yielding66.729270 MAE. Frozen2025best uses HGB squared-error throughout, yielding68.732925. Its improvement is about2.003655yards (2.92%), with seven week clusters and prior research exposure. The static hindsight current HGB absolute-error score66.117313 remains a separate descriptive result.

Rushing-attempt current-memory3.049763 improves the fixed2025base Leaf-CDF3.059242 by0.009479carries. That composite-policy result is separate from the static D1observed score3.058057 and lacks untouched prospective confirmation. Adverse results remain visible: chartPPR4.589546 versus4.502391, anytimeTD Brier0.145145 versus0.143144, combinedyards20.469324 versus20.125661.

## Scope, retention and next action

The roster excludes46current exact recipes lacking complete corresponding2025orcurrent weekly evidence. In particular, D1/D2have no older-season evaluation and are not silently replaced with base Leaf-CDF. Mean/median views are selectable output recipes, not separately counted model families. Current statistical outcomes are current-vintage with inherited availability assumptions, and query features use registered kickoff cutoffs; none is relabelled T-minus90 or originally issued.

All inference/model/prediction evidence is reused. Source values and joins are checked from retained raw files; no new private row-level backlog is created. The preserved selector-v1failure was a chart-procedure reference-prefix error before any policy metrics; corrected selector-v2uses the exact registered chart/base mechanism. Main numerical-v1Infinity serialization failure is separately retained.

No production action is recommended solely from this policy comparison. The next qualified test is later frozen category assignments using compatible captured forecasts, source cutoffs and retained-owner admission, with current/frozen/pooled controls all preserved. No official capture, scheduler, merge, deployment or website selection was changed.

[Frozen protocol/roster/source scores](FROZEN_PROTOCOL.json) · [Every earlier-only weekly decision](DECISIONS.csv) · [Policy scores and precision counts](POLICY_COMPARISON.csv) · [Paired weekly loss differences](POLICY_PAIRED_COMPARISONS.csv) · [Exact membership/label admission](EXACT_MASK_ADMISSION.json) · [Execution receipt](RUN_RECEIPT.json)
