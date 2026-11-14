# Preserved pre-fit script versions

The pre-fit receipt and its committed original executable remain unchanged. `review_anytime_prefit_v1.py` is restored byte-for-byte to commit `636424ee`, SHA-256 `662c92d2f9dc7d226a9fe17ec485f201583d44260f8ee8b7f237cb0c88a0e525`.

After the completed pre-fit check, its source-location literals were replaced with required `--source-root` and `--source2026` arguments so the reproduction wrapper need not prescribe private cache locations. This changes path configuration only: raw sample selection, input hashes, calculations, assertions and receipt-writing logic are identical. That version is preserved separately as `review_anytime_prefit_v2.py`, SHA-256 `baa782604de505679ad308d9b9de60e6486e4c8538e572a21e06a1c54e5c0d8a`. It was not rerun to create a new evidence timestamp.

The historical pre-fit receipt `PREFIT_INDEPENDENT_REVIEW_V1.json` retains SHA-256 `ac4776af29174250365360d4d1f5041b465d4d466abecaf1fc0aaaaa3ff18256`. The CLI reproduction example in the pre-fit README applies to **V2**. Neither script change alters the producer, frozen inputs, model recipe, forecasts or grades.
