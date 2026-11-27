# Supplied-snapshot history control engine v1

Status: **implemented and software-tested only**. Eleven fictional contract tests pass. No NFL fit, source acquisition, new NFL forecast, scoring result, captured pregame record or deployment is established by these tests. This code is original V2 code and imports only the standard library and V2's independent target validator.

`nfl_v2.history.run(origins, admissions, manifest, strict_current=False)` accepts immutable dataclass records and returns forecast rows plus a receipt. It reads no shell files, network, private paths, model cache or environment credentials. A caller must first restore authorized data and qualify the source. The API validates metadata, not the truth of a claimed availability clock, license, position or participation contract.

## Two controls and exact histories

The numeric controls are a per-player empirical arithmetic mean and a lower empirical median. For even sample size the lower median is the value at sorted index `(n-1)//2`; it is an MAE-minimizing median of that empirical sample and remains distinct from the mean. They are output views of the same empirical sample, not two independent scientific families. For anytime rushing-or-receiving TD, only the mean of binary credited-event indicators is returned as an empirical event probability. There is no Poisson conversion and no authenticated full predictive distribution is emitted.

At each supplied origin, retain observations with the exact target and an eligible season:

| Regime | Training seasons at query season S |
| --- | --- |
| H-CURRENT | S only, with outcome availability strictly before origin |
| H-RECENT | max(2022,S-1) through S, with the same availability gate |
| H-MULTI | 2022 through S, with the same availability gate |

Thus the 2026 core comparison uses earlier 2026 versus 2025+earlier2026 versus 2022–2025+earlier2026, on the same supplied query identities. H-MULTI is explicitly expanding from2022; it never uses pre2022. The engine's H-RECENT has the same floor, so its2022 startup has no2021 warm start. That limitation is recorded rather than pretending it reproduces an unrestricted legacy recent-history recipe. Pre2022 legacy reproduction needs a separate method/version.

The API supports 2022–2025 regular-season weeks1–18 and the fixed2026 weeks1–7 panel. A forecast for2026Week8+ is rejected by this initial version. Historical2025 origins cannot consume2026 rows. Every origin has one evaluation season. The caller freezes the full ex-ante eligibility/cohort and exact game/identity mappings before outcomes; the engine cannot infer those from realized usage. Duplicate player/game/target queries across the panel are rejected, so repeated forecasts cannot be counted as additional independent samples. A separately named horizon panel needs a separate run.

There are no football predictor features in these controls. `feature_memory=none_no_football_predictors` is fixed across core arms, making this a fit-window comparison without changing feature memory. It is not a test of richer historical-feature memory. `strict_current=True` emits only H-CURRENT, labels it `strict_current_season_football_information`, and prohibits tuned/external priors. Because this control has no retrieval, encoding, calibration, external model or older feature input, its numerical forecasts equal core H-CURRENT. That identity is disclosed; the strict arm is not counted as a new learner. Historically tuned constants or added features would require another registered implementation and could invalidate the strict claim.

## Startup, replacement players and coverage

Use eligible observations of the same player and historical position. If none exist, use the same target/position empirical sample within the **same arm**. If that is empty, emit the declared common constant zero. No older fitted position prior is hidden in H-CURRENT. Week1 current-only therefore commonly outputs zero while historical arms have usable data. The zero fallback can dominate full-system startup error and is a weak control, not a state-of-the-art forecast. A constant output is valid for point comparison even when inaccurate; its supported role and error contribution must remain visible.

Every supplied query remains in every core arm, including new players, sparse roles and zero-fallback cases. Output records `fallback`, player_n, used_n, selected observation IDs, source IDs/evidence tiers and latest admitted availability. No missing label is filled with zero. This version chooses explicit zero fallback rather than abstention, so ordinary admitted queries have numeric outputs; invalid or incomplete input causes the entire call to fail before predictions, rather than silently dropping rows. A future abstaining variant must preserve null rows and a registered reason under a new version.

Report full-system scores first, including fallback. Separately form learned-only paired overlap using the same query IDs where each compared arm has `fallback=none`; disclose the reduced population. A smaller filtered error does not replace the full-population result or establish star-only training benefits. Conditional-on-appearance training is the only admitted panel here: each observation must have an independently supported `played` state and a complete explicit target value. The source population must retain its DNP, played-zero, played-missing and unknown records separately; those records cannot be passed as zero-valued training labels to this API. Selection of only positive production is not a valid participation contract.

## Source and chronological admission

Each `SourceAdmission` needs a public-safe source_id, one of authentic_pregame_vintage / qualified_asof_reconstruction / current_vintage_reconstruction, exact supported targets, an availability basis, complete-statistic contract, participation contract, historical-position contract and license review ID. An assumed seven-day availability rule may be supplied only when explicitly named as a reconstruction assumption; a timestamp does not promote it to authenticated publication. Source receipts and revisions must be checked outside this numerical engine.

Each origin supplies a cutoff-qualified snapshot, not a future-containing full outcome table. Every observation must satisfy `kickoff < available < origin.cutoff`; equality at the cutoff is excluded. Missing, naive or impossible clocks fail. Any observation from a target query game fails, even if it belongs to another player, as do duplicate identities and nonparticipants. Target queries contain no outcome field, must kick off strictly after the origin, and require an admitted source for identities/positions. Counts must be nonnegative integers; signed yards and signed chart points are retained. Anytime labels must be0/1 and must reflect rushing-or-receiving credits, not return touchdowns.

The API never substitutes current roster position for an old one; it uses the admitted record's position. Source admissions do not certify historical roster mappings automatically. Queries may use qualified replacement membership, but that pregame membership must be preserved by the caller, not determined from later appearances.

Recompute the empirical summaries at **each supplied origin**. The origin cutoff is both the source snapshot boundary and summary update time. Supplying per-game origins can admit newly available earlier games within a week; a weekly origin has one weekly snapshot. These are different declared policies. No weekly/per-game update change is hidden. A real comparison must choose its origin grid/horizon before inspecting target outcomes and retain its hash. These forecasts carry no fabricated inference/issuance/persistence time; a caller must record actual runtime and persistence clocks when capturing a shadow forecast.

## Mandatory manifest and finite bounds

`RunManifest` requires experiment_id, evaluation_panel_id, cohort_definition_id, admitted source IDs, evaluation seasons and positive integer bounds for origins, observations per origin, queries per origin, forecast cells, summary groups and candidate row checks. There is no tuning or hyperparameter cross-product. The procedure version, training floor, fallback, feature-memory, update rule and no-external-prior contract are fixed and validated. Changing a method policy requires a new implementation/version, not merely a renamed setting.

All inputs and total budgets are checked before forecast calculation. A numeric query produces six core cells (three histories times mean/median); an anytime query produces three probability cells. `max_candidate_row_checks` bounds three full candidate/player/position scans per query/arm. Input/output sizes and median sorting remain finite under the declared row/cell bounds. Callers should size a finite wave from actual data and measured runtime rather than use an arbitrarily tiny cap to label a substantive NFL experiment impossible.

The receipt reports manifest/admission/query-membership/full-origin-input/policy SHA256, origins, unique games/player-game-targets, forecast cells, empirical summary groups, candidate scan bound, zero optimization fits and zero scores. A statistical sample summary is not a boosted-model fit, and forecast rows are not scored NFL outcomes. Retain the exact manifest and admission bytes alongside the receipt; its hash alone cannot restore inputs. Retain qualified prediction/outcome rows in the approved private companion store and publish only safe aggregates/manifests. No local path is a durable restoration claim.

For an actual history result, separately score the rows with the independent evaluator on identical joined outcomes, report every2026week includingWeek7, per-season2022–2025 results, native-unit losses, fallback rates and paired week/game uncertainty. Neither this engine nor its fictional tests establish which history regime wins. Stronger direct, structured, state and provider controls remain required.

## Verification

Run `python -m unittest discover -s tests -p test_history.py -v`.

The twelve tests exercise common query identity and different historical samples; Week1 strict-current startup without an old fallback; cutoff equality/future/target-game rejection; unknown/naive timestamps; missing labels/nonparticipants/count support; signed yards/lower-median behavior; replacement position fallback; same-week origin updates; earlier-season direction and floor; source/budget/scope admission; and binary anytime outputs. They use invented identities, values and clocks, with zero NFL observations.
