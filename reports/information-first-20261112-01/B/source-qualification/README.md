# B — qualified FTN two-flag source, current-vintage diagnostic tier

**The source gate passes for a lagged interception-worthy/throwaway information test.** Exact retained PBP/FTN game-play joins cover all **80,439 eligible QB credited attempts** across **2,939 QB-games**. Existing 2,901 context rows are unchanged; a new W9-only supplement adds38rows with official target/team parity and supported participation. No fit, forecast, score or original pick was produced here.

| Season | Actual regular weeks | QB-games | Eligible / charted attempts | IWP positives | Throwaway positives |
|---|---|---:|---:|---:|---:|
| 2022 | 1–18 | 633 | 18022 / 18022 | 935 | 682 |
| 2023 | 1–18 | 663 | 18272 / 18272 | 737 | 742 |
| 2024 | 1–18 | 664 | 17777 / 17777 | 589 | 697 |
| 2025 | 1–18 | 664 | 17412 / 17412 | 549 | 717 |
| 2026 | 1–9 | 315 | 8956 / 8956 | 283 | 404 |

All regular-season charting keys match exact PBP keys; no duplicate PBP or FTN game/play identity was accepted. Passer/team/opponent identity is inherited from credited PBP and reconciled official QB rows. The game-play join does not infer receiver alignment or routes. Postseason chart rows remain outside the regular-season panel and are counted separately in the source receipt.

The eligible denominator is **officially credited pass attempts**, with sacks, two-point attempts, deleted plays and unknown safety flags excluded. Spikes, throwaways and the previously reconciled stat-credited no-play attempt remain. The flags are known only for literal TRUE/FALSE on a matched eligible attempt. Blank/unmatched is unknown. Zero eligible attempts yields an undefined rate; it does not invent zero quality. Every actual eligible attempt in this panel has both flags known, so the new support counts duplicate existing attempt coverage here. B1 must identify that information equivalence rather than call it new football information.

`is_interception_worthy` and `is_throw_away` are provider annotations, distinct from actual interceptions and completion outcomes. Existing B fitted catchability/drop/contested studies stay closed. Screens/play action, read progression and pass-rusher counts are not added to this first block. The documented primary-read code0 is only present from2023;2022missing primary reads cannot be backfilled. Pass-rusher/blitzer counts are not pressure labels; an unconsumed raw2026blitzer count52 requires separate validation if that field is later used.

**Timing:** old2022–25and old2026W1–8 bytes are reused. Only the missing W9 extension uses current2026PBP/FTN bytes, downloaded once (13,308,194bytes). This holds the prior source vintage fixed and prevents a hidden revision effect. The new W9 charting is postgame information and must never enter its own W9 pregame features. Historical feature admission retains the baseline's strict kickoff+7day proxy.

The official documentation says charting starts in2022and is charted within48hours. That statement is not proof of a particular row's original publication. `date_pulled` is the time nflverse retrieved from FTN; it is **not** authenticated initial availability. Current files include later revisions. This supports only the explicitly permitted current-vintage chronological diagnostic tier, not authentic historical issuance or a live promotion. FTN participation is a separate feed, available from2023after the postseason, and cannot supply an in-season route/participation predictor.

**Rights:** charting is **CC-BY-SA4.0, attribution “FTN Data via nflverse.”** New charting-derived inputs, augmented model parameters, predictions and dependent result/plot/report derivatives must retain that attribution/share-alike notice and describe the transformations. PBP/stat-only context inputs and unchanged B0 models remain in their separate CC-BY4.0 lane; code retains existing repository terms. No raw feed, restricted offer, private locator or credential is published. Public availability does not authorize other subscriber FTN products.

The W9 schedule extension initially encountered the old helper's intentional W8 cap; the failure/source code is preserved and only this new helper's W9 scope was extended before any fit/output. All38new context records pass official count parity. Three zero-attempt QBs have positive official carries, so participation is supported without assuming that a stat row proves every metric.

[Exact joins/denominators](SOURCE_JOIN_AND_DENOMINATOR_RECEIPT_V1.json) · [Field, timing and license receipt](SOURCE_FIELD_LICENSE_AND_TIMING_QUALIFICATION_V1.json) · [Reproducible source preparation](prepare_ball_quality_sources_v1.py) · [W9 context supplement](QB_CONTEXT_W9_EXTENSION_V1.json.gz) · [Two-flag QB-game counts](FTN_BALL_QUALITY_QB_GAME_INPUTS_V1.json.gz).
