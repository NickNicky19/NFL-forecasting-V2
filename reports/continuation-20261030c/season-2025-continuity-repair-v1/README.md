# Preserved 2025 carry-specialist recipe repair

The first seasonal adapter used all-position fallback samples for the QB/RB carry specialist. The original recipe restricts those samples to QB/RB. This version restores that contract: unsupported WR/TE rows use zero when no fitted model exists. It also restores the original `absolute_loss_point` product alias.

The repair replays 24,148 source-bound rows, changes 886 fallback annotations and 12 numeric predictions, and produces 176 replacement score views. Every original row, score, model and loss remains retained. No model was fitted or refitted. The new rows retain source run/generation/model provenance and record their actual new reconstruction time and version.

All 432 count-GLM training frames were checked against the original all-zero no-fit contract; none was affected. The remaining older-season engine was separately fixed and reviewed before its fits.

[Exact score-ID supersession mapping](SUPERSESSION_MAPPING.json) links each original score view to its replacement. This is a forecast/fallback procedure repair, not a pure scorer correction or evidence of a new predictive mechanism. Private corrected rows and the patch log have separate safe hashes; no current 2026 Week 8 outcome was read.
