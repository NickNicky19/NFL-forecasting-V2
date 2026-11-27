# Independent pre-score review: depth-conditioned catchability

The proposed addition is executable as a **provider-annotation context proxy**. It is distinct from the completed F1/F2 aggregate charting recipe: those models used game-level chart support and three rates across all throws. The new mechanism conditions catchability on the existing five depth bins and integrates conversion using predicted context and attempt exposure.

The independent key join counted **79,489 official eligible QB throws** across retained 2022–2026 sources (2026 Weeks 1–8). All have explicitly known TRUE/FALSE catchable annotations. The UNKNOWN-depth bin has only **11 throws**, all marked FALSE; support and the declared prior remain necessary. Historical first publication is not authenticated; the same current-vintage seven-day reconstruction must apply to training and queries.

There are **255 observed completions marked catchable FALSE** (0/87/88/57/23 in 2022–2026) and **6,196 incompletions marked TRUE**. This establishes that the retained provider annotation and official completion are not an interchangeable event. It does not by itself establish a software defect or a changed codebook. The agreed GLM covariate design is appropriate; a deterministic constraint completion <= charted catchable, or catchable = completion + drop, would not be supported.

The source census used independent raw key joins and depth grouping, not the parent feature builder or scorer. It did not repeat the closed 2,901-row reconstruction or fresh-fit acceptance. Source hashes, field codes, denominators and per-season/week/depth support are in [the receipt](DEPTH_ANNOTATION_SUPPORT_V1.json). Runtime 13.1 seconds, peak RSS 530.8 MB, zero fits and zero downloads, within the registered 536.9 MB limit.

The pre-score design passes its bounded scope: unchanged P1/E1 controls, support-only versus value arms, information-matched direct arms, one fixed 8-game/20-throw recipe, four fits per origin and 26 origins. Strong E3/F2/saved-adjusted/prevalence/constant controls remain necessary. A gain over a weak control alone is insufficient. No new support floor, significance hurdle or calibration search is introduced.

Four offered weeks do not qualify a new primary direction/probability product. New numerical season tests, software checks, profile snapshots and a peer point-direction replay cannot supply missing actual-line weeks or Top Picks qualification. Result acceptance and keep/stop decisions remain pending execution.

Mixed derivatives: FTN Data via nflverse, CC BY-SA 4.0; PBP nflverse/nflfastR, CC BY 4.0. No raw feeds or restricted offer rows are exported.
