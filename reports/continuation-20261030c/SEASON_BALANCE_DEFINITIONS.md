# Cross-season aggregate definitions

Each row is one fixed normalized recipe/product/history policy across its explicitly listed supported seasons. Pooled micro loss is `sum(n_s * loss_s) / sum(n_s)`. Season-balanced loss is the arithmetic mean of the supported seasonal losses; season-balanced RMSE is the square root of season-balanced MSE. It is not the mean of seasonal RMSE. Every2022–2025 season is full18weeks;2026 stays fixed atWeeks1–7. Missing seasons are not zero. The requested2022RECENT arm is excluded and its available-data proxy has a separate identity.

Different histories may have different supported-year sets; compare season columns before using any aggregate. Neither pooled figure answers the training-history effect on the same2026games. Selection is exposed; these are descriptive fixed-recipe summaries, not live weekly selector results. Explicit source rows and all per-season errors remain in the JSON.
