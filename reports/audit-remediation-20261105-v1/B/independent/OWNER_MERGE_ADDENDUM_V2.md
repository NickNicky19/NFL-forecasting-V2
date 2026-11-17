# Owner-merged presence repair: pinned follow-up

The earlier [missingness review](README.md) remains evidence about `fe369c74` and PR 1. It must no longer be read as a claim that the same path persists in the separately merged owner revision `a478db86e2702d9fa632a23bfaf9c575a67ea902`.

At that immutable revision, the actual compaction/grading functions pass 12 fictional fixtures: explicit null and missing components remain unresolved, valid zero remains zero, signed yards remain signed, and half-point/whole-point boundaries remain correct. NaN and boolean outcomes are rejected as unknown. The merged `nfl-data-presence-strict-v3` contract also leaves absent legacy fields unknown; it does not inherit PR 1's earlier sparse-absence zero assumption.

Three actual producer fixtures confirm unknown TD projections serialize as null and known zero TD components serialize as zero. Nine actual UI-guard fixtures pass. These are software checks, not NFL accuracy or probability-calibration observations.

Receipts: [actual Python functions](OWNER_MERGED_PRESENCE_A478_REVIEW_V2.json) and [actual UI guard](OWNER_MERGED_A478_UI_GUARD_V2.json). No historical grades or previous receipts changed. Historical contamination still requires recoverable precompaction source presence. A later owner source/run was already reported during this check; this revision is the pin tested, not a claim of perpetual latest HEAD. Capture, served bytes and browser rendering remain separate owner-controlled verification.
