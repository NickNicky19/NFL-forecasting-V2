# Market evidence and retained-owner handoff

The completed panel supports original recorded line-direction grading, with the exact uncertainty and coverage limits in the scorecard. It does not support settled sportsbook returns, line-probability quality, EV, de-vigging or CLV. All saved probabilities/prices are null. DraftKings-labelled thresholds are not priced quotes; Sleeper side multipliers are contest observations and may accompany another threshold. They are never treated as decimal odds or attached to a different preferred line.

The approved existing producer/export must retain these fields before the corresponding claim can be evaluated:

| Claim | Exact required retained evidence |
|---|---|
| Original direction outcome | Actual selected side, original line, exact event/player/statistic/scoring/period identity, pregame selection/retention evidence and qualified outcome. Prices are not required. |
| Authentic offer eligibility | Book/jurisdiction, original threshold/side, source update and receipt clocks, OPEN status/quote-age policy, actual decision time, matching forecast issuance/information cutoffs and target parity. |
| Probability score | A qualified original or separately reconstructed law at that decision; nonvoid conditioning, over/under/push mass and separate supported void probability. Counts use CDF/PMF mass; no probabilities from a point alone. |
| Cash EV / flat-unit returns | Each chosen side's actual decimal price, payout/refund contract, participation/early-exit/injury and statistical-correction rules, settlement evidence and a frozen one-side selection policy. No assumed −110. |
| Market-only / hybrid comparison | Matched same-book/same-line/same-time sides for the stated normalization. Integer-line de-vig probabilities may be conditional on a decisive result and cannot silently become nonvoid probabilities with zero push mass. An independent reference for book B excludes B through its full feature path. |
| CLV | Exact immutable entry decision plus a qualified later pregame quote. Same-contract price movement needs the original threshold/book/event/player/statistic/period/rules; different main-line movement is a separate statistic. Missing closes stay null. Polling output is last observed eligible pregame quote unless a stronger close claim is proved. |

The [consumer contract](CONSUMER_CONTRACT_V1.json) separates forecast/version, line/side/book/price, quote age/status, probability conditioning, EV, original history and later CLV/outcome. An expired offer loses current actionable-EV status while retaining its original recommendation/EV-as-of-decision history. This is a prepared schema, not a published feature or working market feed.

Under refund settlement, unconditional placed-unit EV is `p_win*(decimal_odds−1)−p_loss`. Nonvoid probabilities produce EV per nonvoid unit; conversion to placed-unit EV needs supported `P(nonvoid)`. Push mass remains present. Mirrored binary sides are not independent probability competitions. Synthetic fixtures check these equations; there are no real priced EV results in this checkpoint.

Strict P1 needs an internal unrounded point or an explicit precision contract. The original producer rounded before saving, so the current proxy is saved-point direction at retained precision. Future owner exports can add an unrounded field alongside the existing display point without rewriting old records. P2 needs genuine line probabilities; P3 needs those probabilities and each side's own available price. Both remain unavailable for this original packet.

Existing V2 kickoff-information reconstructions cannot be paired with earlier quotes as if issued earlier. A new earlier-cutoff reconstruction would need its own identity, source-vintage disclosure and matching features/fallback/tuning inputs. Current point-MAE winners are not automatically offered-line winners. No football-versus-market/hybrid or price-aware category winner is established.

The newer owner-controlled Week 8 selected stream and old R0 Record history remain separate. Existing 14-game and later 13-game V2 future packets retain their original timestamps, hashes and timing flags. The first Week 8 kickoff has elapsed, but the registered statistics snapshot contains zero Week 8 rows. New qualified labels/finality/participation must be admitted before grading it. No later prediction or closing line can replace an earlier capture.

Larger fitting remains blocked by actual full recovery: the specifically unrun strict-HGB cells, selective scheduled-window wave and qualified 2021 RECENT extension retain their existing gates. Current-role, opportunity, defense, pace/playcalling, calibration and distinct candidate tests remain in the original 60-pathway queue. Missing originals/route/market/rare-chart sources block their own cells. No new collector, shared schedule, Odds API usage, paid proxy, secret, wager, merge or deployment is introduced. Official capture, publication, adapter admission and served-value verification stay with the retained owner.
