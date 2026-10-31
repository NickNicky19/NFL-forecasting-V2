# Window definition: observed position groups, not all calendar games

The executed D1/D2 recipe uses the last four earlier **observed qualified opponent-position groups**. Missing targets or uncertain appearance within an existing group consume a slot. An entire absent position group does not become an unknown calendar-game slot. It is skipped by construction; no missing group becomes zero.

The frozen protocol says: “Missinglast4opponent-positiongamesconsume slots.” The frozen source helper instead indexes observations by `(defense, position, target)`, and the input builder creates an observation only for a nonempty source group. That wording does not adequately distinguish observed position groups from all scheduled team games. This is an explicit research recipe/description limitation, not a silent rename or a claim that four calendar games were tested.

The independent scan found 9,552 scheduled defense-position slots across the admitted 1,194 games, versus 9,546 observed groups. All six absent groups are TE groups:

| Game | Defense |
| --- | --- |
| 2023_05_NYG_MIA | NYG |
| 2023_05_CIN_ARI | ARI |
| 2023_07_PIT_LA | LA |
| 2023_08_KC_DEN | KC |
| 2025_02_NE_MIA | NE |
| 2025_18_NYJ_BUF | BUF |

For example, the completed source calendar contains `2025_18_NYJ_BUF`, but no qualified TE group against BUF exists in that game. A four-calendar-game feature would retain an unknown slot there; the executed feature reaches back to the fourth observed TE group instead. This example requires no public player-level values or identities.

Under common 2022+ feature memory, 77 historical 2026 query windows differ from the calendar-window interpretation: 11 each for anytime TD, chart points, receptions, receiving yards, rushing attempts, combined yards and rushing yards. These are TE query contexts; passing targets have no direct query-window discrepancy. Strict-2026 local query windows and all new future local query windows have zero such differences.

Those counts describe query inputs. Older training inputs can also differ, so it would be wrong to conclude that only 77 predictions could change under a calendar-padding refit, or that unchanged future query windows imply unchanged future predictions. The effect on fitted parameters and errors is unknown without a new registered experiment.

All original inputs, fitted models, predictions, scores, protocol wording and identifiers remain frozen. Independent replay validates the reported errors for the actual observed-group recipe. A future calendar-padding comparison must have a new identity and preserve these results. No additional fit, source acquisition or Week 8 outcome was used in this finding, and these research models have not been deployed.

Source: [independent scan and counts](../DEFENSE_ABSENT_POSITION_WINDOW_FINDING.json). Broader raw-feature and training-metadata verification is reported separately by the independent reviewer.

The [independent scope addendum](../DEFENSE_WINDOW_SCOPE_ADDENDUM.json) completes the training census: 59 source TE player-game contexts have different window membership (38 in 2023, ten in 2025, eleven in 2026), and 308 fit receipts consume affected training rows. Across each of the seven TE targets, the affected training player-games number ten under CURRENT, twenty under RECENT and fifty-five under MULTI; those sets overlap. STRICT has zero. A concrete BUF query at 2026 Week 1 uses observed 2025 Weeks 14–17, whereas four scheduled slots would be Weeks 15–18. Window membership differences need not change numeric features, and no counterfactual forecast or error change has been measured.
