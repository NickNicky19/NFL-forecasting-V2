"""Readable aggregate-only report from the sealed no-fit source audit."""
import argparse
import collections
import json
from pathlib import Path


def main(root):
    root=Path(root);load=lambda name:json.loads((root/name).read_bytes())
    p=load('FROZEN_PROTOCOL.json');r=load('AUDIT_RECEIPT.json')
    fits=load('ORIGINAL_FIT_TRAINING_FEATURE_CHANGES.json')
    sources=load('SOURCE_TRAINING_FEATURE_CHANGES.json');queries=load('QUERY_FEATURE_CHANGES.json')
    lines=['# Four scheduled games: executed source audit, fits blocked\n',
      f"The separate scheduled-window implementation changes **{r['changed_raw_feature_contexts']:,} of {r['unique_target_floor_training_contexts']:,} eligible source target/feature-floor training contexts**. All768 original D1/D2 training memberships were reproduced exactly; **308 fit receipts consume changed raw features**. No model was fitted or queried, no forecast was issued and no error was rescored. These counts describe feature changes, not predictive improvements.\n",
      'The original observed-group recipe and all of its models, scores and captures remain immutable. It selects the last four nonempty qualified opponent-position groups. The alternative selects the last four eligible regular-season team games in the admitted schedule. An absent position group consumes a slot with unknown target and exposure; zero row counts describe coverage, not zero football production. The existing group with an unknown target also consumes a slot. D1 keeps its four columns; D2 keeps its nine columns, including the explicitly scheduled-kickoff age. League compatible-rate priors remain unchanged.\n',
      'The admitted schedule contains1,194 games through2026Week7:271in2022,272each in2023–2025 and107in2026. It omits the canceled2022BUF–CIN game. This is an exact source-schedule definition, not a general policy claiming all cancellations are scheduled playable games.\n',
      '| Consumed original contexts | Receipt count | Receipts with changed raw inputs | Repeated changed training-row uses | Total training-row uses |',
      '|---|---:|---:|---:|---:|']
    for future in (False,True):
        for group in ('D1','D2'):
            rr=[x for x in fits if x['future_reference']==future and x['information_group']==group]
            lines.append(f"|{'Original Week8 training only' if future else '2026 Weeks1–7 training'} {group}|{len(rr)}|{sum(x.get('any_raw_feature_changed',0)>0 for x in rr)}|{sum(x.get('any_raw_feature_changed',0)for x in rr):,}|{sum(x.get('contexts',0)for x in rr):,}|")
    lines+=['', 'Repeated uses count the same player-game again when it enters another origin/policy/group; they are not independent NFL outcomes. The385 changed eligible target/floor contexts represent55 distinct eligible player-games across seven TE targets (35in2023,10in2025,10in2026 per target). Four additional observed-position source contexts in the independent calendar census lack an eligible target label and do not enter these model training frames. Unknown-label query rows remain in the separate query audit.',
      '', '| Query context | Feature floor | Group | Changed raw-feature cells | Changed window cells |', '|---|---:|---|---:|---:|']
    for period in ('2026_W1_W7','OLD_FUTURE_CONTEXT_ONLY'):
        for floor in (2022,2026):
            for group in ('D1','D2'):
                rr=[x for x in queries if x['period']==period and x['feature_floor']==floor and x['information_group']==group]
                lines.append(f"|{period}|{floor}|{group}|{sum(x.get('any_raw_feature_changed',0)for x in rr)}|{sum(x.get('window_changed',0)for x in rr)}|")
    lines+=['', 'The historical77 cells are11 TE player-games across rushing yards, carries, receptions, receiving yards, combined yards, anytime rush/receive TD and chart PPR. They are shared by the three common-memory fit arms, rather than77 new NFL games. STRICT2026 windows and the original future local query windows do not change. That does not establish unchanged future forecasts:42 original future training receipts have changed training inputs. Any counterfactual prediction or error remains unknown until a separately admitted new fit executes.',
      '', 'All comparisons retain original fixed source/query identities, label definitions, learner, training membership, priors, own-player features and fallback. Historical features remain a kickoff-left-limit reconstruction with assumed seven-day availability; this is not authenticated T-minus-90 issuance. CommonH-CURRENT is current-season fitting with older feature memory. STRICT uses2026for own/opponent/league features, priors and transformations, while the architecture and retrospective cohort were already exposed.',
      '', 'The frozen protocol binds strongest compatible full-primary point, genuine-mean and proper-law controls from the accepted current leader table. Candidate-versus-observed-window and same-policy original Leaf controls are mandatory too. Top10/15/20, disjoint1–10/11–15/16–20/remainder and role/opportunity bands reuse the exact retained memberships; chart bands measure signed score history. Selectors and competitor identities are fixed across methods. Full-system, own-learned, paired-learned/common-history intersection and fallback contributions remain separate. No after-the-fact band-specific routing is authorized.',
      '', '**All672 historical and96 possible future fit cells are blocked.** Root must first verify approved durable source/code/model/prediction retention, independent prefit review and sole-worker capacity. A future capture also needs a new actual query cutoff, open-deadline check and real issue/persistence times; the original16:59cutoff is only an old-context audit reference. The CLI exposes `prepare` and `audit`; its fit-permission guard always rejects. No current2026Week8 outcome is decoded.',
      '', f"The bounded audit used{r['resource']['wall_seconds']:.2f}wall seconds,{r['resource']['cpu_seconds']:.2f}CPU seconds and{r['resource']['peak_rss_bytes']/1048576:.1f}MiB peak RSS, one thread. The registered audit limits are240wall/300CPU seconds and1GiB; the future fit allocation is at most768calls,1,200wall/1,800CPU seconds,2GiB RAM,1GiB new private output and two threads, with no search. This is a budget, not capacity approval.",
      '', 'Reproduce with the supplied admitted roots (private locators are intentionally absent):',
      '', '```bash',
      'python tools/audit_scheduled_defense.py audit \\',
      '  --original-public "$TASK_ORIGINAL_PUBLIC" --original-private "$TASK_ORIGINAL_PRIVATE" \\',
      '  --source-root "$TASK_SOURCE_ROOT" --public-root "$TASK_NEW_PUBLIC"',
      '```',
      '', 'Use a fresh output directory for a new version. The sealed protocol and code hashes must match; existing audit artifacts are never overwritten. `ScheduledQualifiedDefenseHistory.at` implements the same feature interface used by the retained augment helper, so feature extraction is executable without changing the old helper. New NFL-fit orchestration/admission remains pending, rather than silently reusing an old run ID.',
      '', 'Evidence: [frozen protocol](FROZEN_PROTOCOL.json), [768blocked cells](BLOCKED_FIT_GRID.json), [all source-feature changes](SOURCE_TRAINING_FEATURE_CHANGES.json), [all original training-cell changes](ORIGINAL_FIT_TRAINING_FEATURE_CHANGES.json), [query changes](QUERY_FEATURE_CHANGES.json), [audit receipt](AUDIT_RECEIPT.json). Sparse counter fields omitted from an aggregate mean zero occurrences, not missing errors or unscored forecasts.',
      '', 'This audit answers which raw inputs change. It cannot answer whether the scheduled-window alternative is more accurate, justify deployment, or erase the original observed-group recipe and its losses.']
    (root/'README.md').write_text('\n'.join(lines)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--public-root',required=True,type=Path)
    main(parser.parse_args().public_root)
