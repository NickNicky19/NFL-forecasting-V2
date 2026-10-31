# J executor v2: retain attempted fits when evidence persistence fails

An independent synthetic fault exposed a bookkeeping defect in v1: the optimizer-attempt counter could increment, then the first FIT evidence write could fail before the cell entered `GRID_STATUS`. That attempted cell would incorrectly appear `NOT_RUN_AFTER_BOUNDED_STOP`. Forecast acceptance and scoring were already protected: no forecast rows were accepted when their packet failed retention. No NFL run had used this executor, so this correction changes no NFL prediction, numerical loss, sample count or historical conclusion.

Version `v2-J-observed-defense-older-season-executor-v2` fixes that state accounting. The loop announces registration and start before invoking the optimizer. The wrapper records the cell's algorithm state and pending evidence before the first evidence write. A post-fit guard failure also retains the started attempt. A successfully fitted model is not described as retained until persistence/readback succeeds.

| Situation at bounded stop | Recorded state | Fit attempt counted? |
|---|---|---|
| Fit eligible, budget rejects before start | `FIT_REGISTERED_NOT_STARTED` | No |
| Fit started, optimizer/result or first evidence persistence interrupted | `FIT_ATTEMPTED_UNRETAINED` | Yes |
| Model bytes retained, other FIT evidence incomplete | `MODEL_RETAINED_EVIDENCE_INCOMPLETE` | Yes for the original fit |
| Reused result, current cell evidence not retained | `REUSED_RESULT_EVIDENCE_UNRETAINED` | No new fit |
| No-fit prior/fallback, evidence not retained | `NO_FIT_FALLBACK_EVIDENCE_UNRETAINED` | No |
| Model and all FIT evidence retained | `MODEL_AND_CELL_EVIDENCE_RETAINED` | Yes |
| Truly untouched cell | `NOT_RUN_AFTER_BOUNDED_STOP` | No |

Algorithm outcome, evidence state, model retention, computational reuse, model reuse and fallback-only status have separate fields. The public run receipt adds attempted-cell and unretained-attempt counts. A failed fit followed by retained fallback evidence remains a failed fit; aliases do not become new fits. The exact forecasting algorithms, feature chronology, priors, fallbacks, thresholds and admission gates are unchanged.

Four additional synthetic regressions cover the first FIT evidence-write failure, post-fit guard failure, reused/no-fit distinctions and start-event ordering relative to the spy optimizer. All **26 targeted tests pass**:19 executor tests and7 existing preflight tests. These are software fixtures, not26 NFL experiments. [Test log](UNIT_TEST_RESULTS.log), [exact-code receipt](SOFTWARE_CHECKS_V2.json), [protocol](FROZEN_PROTOCOL_V2.json) and [source bindings](SOURCE_BINDINGS_V2.json) retain the executed checks.

The exact v1 executor (`07b821211cd1649342a2b615120d85f165880437e2447fc1b847b64666a5f2e6`), CLI and tests are preserved in [source-v1](source-v1/). The original v1 protocol, software results, full-suite424 check receipt, independent PASS and subsequent limitation receipt remain unchanged. The correction supersedes only the software implementation/default readiness; it neither overwrites earlier records nor invents scientific score corrections.

**Actual new NFL fits, inference, forecasts, scores and closed backtests: all0.** All736 exact older-season D1/D2 output cells still need execution under their registered source/recovery/resource/admission requirements. The separate2022 RECENT extension and scheduled-window procedure are unchanged. Missing lines and original selections do not block football-only numerical evaluation. This code checkpoint does not release a model worker or change production.
