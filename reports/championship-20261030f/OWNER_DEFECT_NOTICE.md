# Owner notification: preserve original decisions and qualify omitted zeros

The user explicitly requested this audit and owner notification. V2 keeps production and both upstream repositories read-only. The inspected production main remains `1ec93e068a91abd51c990937d1019e4a831694b4`.

Two code-traceable findings need the retained production owner's review:

1. [Started legacy entries can receive a closing line](https://github.com/NickNicky19/nicks-expert-nfl-picks/blob/1ec93e068a91abd51c990937d1019e4a831694b4/pull/build.py#L380) when `line_from` is absent; `apply_book` can also recalculate the lean. Consequently a mutable post-start archive does not authenticate its original pregame line/side. Owner action: keep the original forecast/line/side/decision provenance immutable, append closing diagnostics separately, and version any repair. Do not overwrite history to recover a missing original.
2. [Grading after participation proof calls `stat_value`](https://github.com/NickNicky19/nicks-expert-nfl-picks/blob/1ec93e068a91abd51c990937d1019e4a831694b4/pull/grade.py#L179), whose [legacy component mapping](https://github.com/NickNicky19/nicks-expert-nfl-picks/blob/1ec93e068a91abd51c990937d1019e4a831694b4/pull/scoring.py#L79) defaults omitted fields to zero. Participation alone does not establish that an omitted target is zero. Owner action: verify and retain the exact compact-source completeness/zero contract, or keep the omitted target unresolved. Preserve played-zero, missing-target and DNP as different states.

These are provenance/source-contract findings, not a claim that every served row is wrong. A synthetic example of the second risk is a player with proven participation but an absent receiving-yard field: zero is justified only if the exact source declares that omission means a complete zero. V2 used separately qualified explicit labels and preserved unknown appearances.

[Previously published audit, source pins and limitations](https://github.com/NickNicky19/NFL-forecasting-V2/blob/4c2d3b25/reports/prop-grading-20261030e/production-evidence-inventory/README.md). No owner-only repair, workflow dispatch, merge, deployment, lease change or collector has been made by V2.

The original research session's newer original-lean report at `18f5b67d46cf19f94ddb3106307a5fe2f75a89b6` is acknowledged as separate evidence. Its archive clock/label-contract limits must remain visible; its results are not silently merged with V2's server-proven Week 7 panel. Original receiving-target/CDF research and the retained publisher keep their ownership.
