# B passing opportunity and defense source block

This new component reuses the five already-retained 2022–2026 PBP snapshots and accepted game/QB identities. It adds passing opportunity decomposition and basic as-of profiles for all 32 defenses; it does not repeat the closed catchability, raw-source acceptance or personalization experiments. No model was fit and no forecast or NFL game was scored by this extraction.

The exact seven-day reconstruction remains unchanged: source availability is kickoff plus seven days, admitted only when strictly earlier than the query cutoff. Eligible records are then windowed by game time and deterministic game identity. This is current/revised-source reconstruction, not authenticated historical publication. The 941 historical QB queries are conditional retrospective statistical rows, not authenticated pregame expected starters. Current queries require a separately qualified pregame identity/role universe; no such current universe is supplied here.

| Quantity | Definition and denominator | Limits |
|---|---|---|
| Team offensive-opportunity proxy | Nondeleted, non-two-point PBP rows with reported rush attempt, pass attempt or provider QB dropback | Excludes snaps/no-plays without those credited/provider flags; not all offensive snaps or designed play calls |
| Provider dropback | Explicit `qb_dropback=1` on qualified rows | Sacks and scrambles remain separate; no invented designed-pass or pressure labels |
| Credited attempt | `pass_attempt=1`, `sack=0`, explicit nondeleted/non-two-point | Includes supported credited `no_play` attempts and spikes; not the raw PBP pass-attempt flag including sacks |
| Completion | Explicit `complete_pass=1` on a credited attempt | Missing annotation stays unknown and is excluded from the known-completion denominator; explicit zero is valid |
| Own QB opportunity | Passing-event rows attributed to the accepted QB identity: dropback, sack or credited attempt | Not all offensive opportunities while that QB was on the field; own dropback fraction is not a playcalling estimate |
| Own QB share | Own dropbacks/credited attempts divided by same past-game full team totals | QB-stint descriptive share, not authenticated starter probability or target-game exposure |
| Context | Marginal down 1/2/3/4/unknown, distance 0–3/4–6/7–10/11+/unknown, field backed-up/own-half/opponent-half/red-zone/unknown | Not a full sparse cross-product; no realized future mix enters query features |
| Defense | All supported opposing team opportunities; last 16 unique eligible team-games | Not restricted to profiled players. Raw or earlier-league-shrunk values are not opponent-quality-adjusted talent estimates |

Own QB rates/volumes shrink toward earlier eligible QB-game aggregates (QB-stint units); team offense/defense shrink toward earlier eligible team-game aggregates. Scalar rates use 100 pseudo-opportunities and game means use four pseudo-games. Empty history retains explicit prior-only status, source age null and zero support. A missing earlier prior remains null. Context cells retain raw numerators/denominators and undefined zero-denominator states; they are not advertised as precise standalone estimates. The model consuming them must declare its imputation/regularization and preserve support.

Known observed zero, unknown flag and undefined ratio are separate. Unassigned/unprofiled passer opportunities remain in the full team bucket. Sacks are not pressures. Charted throwaways, catchability, alignment and routes are not newly supplied or fabricated by this block. Existing depth/FTN annotations remain separately bound.

`OpportunityHistory.feature_groups(query)` returns named `R1_support`, `R2_player_values`, `R3_defense_values`. Root selects a finite nonredundant set before fits; existing down/depth completion residuals need not be added twice. All source/profile derivatives are descriptive inputs, not probabilities for a prop, forecasts, selections, fit counts, evidence of predictive improvement or releases.

The machine receipt binds the exact registration, source hashes, code, resource use, profile counts and artifacts. Run command: `python tools/prepare_passing_opportunity_profiles.py --source-root <retained-source-root> --out reports/profile-increment-to-release-01/B/source-profiles`. Raw source locations are deliberately not public evidence routes.

V2 preserves V1 and corrects a discovered denominator boundary before any fit/scoring: 325 credited attempts occur outside provider dropbacks. Conditional attempt conversion now counts only attempts-on-dropback; total credited attempts remain separately retained. All 2,901 accepted QB attempt/completion identities reconcile. V2 supplies 941 historical QB profiles and 832 defense profiles (32 teams ×26 origins). Eight boundary/chronology/current-query software tests pass; these are not new NFL observations. Cumulative extraction used79.36s wall/79.21s CPU/482.1MB peak RSS, within the finite registered allowance. The field/use schema identifies likely existing/support duplicates so the experiment can freeze only genuinely new inputs.
