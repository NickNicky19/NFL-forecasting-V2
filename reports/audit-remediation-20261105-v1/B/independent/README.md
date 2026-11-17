# Independent missingness review

The explicit-null website defect remains reproducible at production commit `fe369c7462e4e4f290727b2d03b696d28ef5454b`. The observed PR 1 head, `81c3fc2a612ced916f4c54814f978c509058bca5`, contains a working repair for the tested path and remains unmerged. No upstream files were changed.

The probe extracts and executes the actual pinned `trim_stats`, `participation`, `_prop_result`, `result`, `tally`, `combine_tallies`, and `player_props` functions, with the full pinned scoring module. It does not import the collector/build entrypoint or access a live feed. Test rows are fictional.

| Fixture | Current production | PR 1 head |
|---|---|---|
| Played player, `rec=null`, selected Under 0.5 | Incorrect actual 0 / hit | Unknown / unresolved |
| Played player, rushing yards 55 and receiving yards null, selected Under 60.5 | Incorrect actual 55 / hit | Unknown / unresolved |
| Explicit receptions zero, selected Under 0.5 | Actual 0 / hit | Actual 0 / hit; zero retained |
| Rushing 55 plus receiving 0, selected Over 60.5 | Actual 55 / miss | Actual 55 / miss |
| Signed rushing yards −2, selected Under −0.5 | Actual −2 / hit | Actual −2 / hit |
| Passing TD 2, selected Over 1.5 | Hit | Hit |
| Completions 20, selected Under 19.5 | Miss | Miss |
| Receptions 4, selected Over 4 | Push | Push |

These eight software fixtures produce 5 wins / 7 decided in production, versus 3 wins / 5 decided plus two unresolved with the repair. They are **not NFL performance or an accuracy penalty estimate**. Counts and selected-side arithmetic independently reconcile. PR 1 still discloses a legacy sparse-absence zero assumption; preserving explicit null does not authenticate every absent field as a reported zero.

The actual missing-TD producer also yields `proj=null, td_chance=0` in production, versus two nulls in PR 1. The current actual UI guard passes six independent fixtures and returns unknown for every affected row inspected: **124 of 473 Anytime TD entries** in the retained November 5 23:32:08 UTC board have a missing projection and serialized zero. This updates the snapshot count, preserving the audit's earlier 123/475 observation. No browser rendering was claimed.

## B original Week 8 scope

B's inspected grades use retained NFLverse CSV outcomes, ESPN finality, exact identity mapping and B's `Labels.label`/threshold engine. They do not consume the website's compacted stats for actuals.

All **415 decided original selections** have recoverable explicit numeric source components: 439 required component cells, including 46 explicitly encoded zeros. All saved actuals match those source values; 42 actual outcomes are zero with explicit raw support. The original selected pool retains 12 unresolved participation records separately.

| Selected side | Wins | Losses | Decided | Hit rate |
|---|---:|---:|---:|---:|
| Over | 109 | 128 | 237 | 45.99% |
| Under | 96 | 82 | 178 | 53.93% |
| Combined | 205 | 210 | 415 | 49.40% |

The same decided pool contains 224 Under outcomes out of 415 (53.98%). This is an original-selected-pool control, not a prospective Under policy. One real retained win and loss in each selected-side bucket were independently checked with decimal inequalities; public receipts contain safe record hashes rather than private player rows.

No correction to those 415 B grades is supported by this missingness finding. This is a bounded source-presence review, not certification of every B source, season, chart component, identity or grade. The original adverse results remain unchanged.

## Exact remaining dependencies

The website owner controls integration of its existing presence-aware repair and regression tests. Historical website corrections additionally require **original precompaction raw statistics**, preserving player/game/statistic identity and explicit key presence/null/zero, joined to the original line/side and outcome/grade version. Compacted missing keys cannot recover that distinction. No corrected NFL win count is claimed.

The audit's C dormant NaN helper finding is separate: its appendix reports a failing legacy helper and a protected current primary grader, with no established canonical contamination. This B review does not duplicate C's owned repair or turn that report into a new B defect.

Machine-readable evidence: [current path and B scope](MISSINGNESS_CURRENT_PATH_AND_B_SCOPE_V1.json), [TD UI guard](CURRENT_TD_UI_GUARD_REVIEW_V1.json). Scripts are alongside the receipts and take explicit source/output paths. No models, fits, new NFL grades, workflow dispatch, collectors, production writes or external messages were used.
