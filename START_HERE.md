# NFL Forecasting V2

**Executed audit checkpoint, October 29, 2026. The full tournament is incomplete.**

V2 independently reproduced all 33 original method/category score cells in a retained Week 7 packet. Then it graded those original forecasts against a separately versioned later statistics snapshot: **666 explicit target outcomes, 190 player-games and 14 games**, yielding **1,998 method-score rows**. All 8,096 original opportunities remain visible; 7,430 labels are unresolved. No new predictive fits or forecasts were made.

Independent checks passed: 168 comparisons with the original scorecard, 132 primary-role metric checks, 36 scoring/settlement checks, and 1,008 metrics plus 16,192 source-field checks for the later label extension. Eighteen executor tests and 29 independent history-engine checks also passed; these fictional tests add no NFL samples.

Recent and pooled controls tie on all 666 exact-match outcomes and use position-prior fallbacks throughout. The earlier small recent-control lead depends on identity-unverified rows. **Neither result establishes the best training-history regime.** Missing zeros also prevent full-population accuracy or probability-skill claims. Upstream research and production remain unchanged.

- [Answers to all fourteen questions](reports/ANSWERS_01_TO_14.md)
- [Later Week 7 grading and limitations](reports/week7-label-extension-v1/README.md)
- [History comparison](reports/HISTORY_COMPARISON_2026_W1_W7.md)
- [Twelve-category status and reported shorter-panel rankings](reports/TOP5_BY_CATEGORY_PRODUCT.md)
- [Inventory completeness](reports/INVENTORY_COMPLETENESS.md)
- [Testing findings](reports/TESTING_FINDINGS.md)
- [Independent review of the label extension](reports/verification/LABEL_EXTENSION_REVIEW.md)
- [Production handoff](reports/FUTURE_CAPTURE_AND_RELEASE_HANDOFF.md)
- [Resumable queue](TASK_LEDGER.md)

The requested common-row 2026 Weeks 1–7 rankings and H-CURRENT/H-RECENT/H-MULTI comparisons remain unestablished. Earlier Weeks 1–6 reported rankings are retained separately. Missing scores are null with reasons in the [grid](registries/EXPERIMENT_GRID.csv). Its 5,408 entries include provisional source/product references, proposed pathways and composite rolling-season cells; they are not 5,408 distinct methods or a completion denominator.

Run `python -m unittest discover -s tests -v` and `python tools/validate_checkpoint.py`. Read [reproduction instructions](docs/REPRODUCIBILITY.md) before restoring evidence. The original scorer and history engine need only Python 3.12+. Raw evidence stays outside public Git; safe source IDs make the replay inputs recoverable subject continued upstream access. The broader approved private companion store remains unbound.

The [task specification](TASK_SPEC.md), [protocol](config/protocol-v1.json), [adapter contracts](docs/ADAPTER_CONTRACTS.md), [source catalog](docs/SOURCE_CATALOG.md), [request crosswalk](registries/REQUEST_METHOD_CROSSWALK.csv) and [execution events](registries/EXECUTIONS.jsonl) distinguish requests, proposals, fits, forecasts, scores, readiness and deployment. Original scientific registrations remain unchanged. No competing writer, scheduler, collector or wager is authorized.
