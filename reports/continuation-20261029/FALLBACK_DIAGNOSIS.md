# Why the saved simple controls all used priors on scored games

The original live adapter did not connect most Sleeper player IDs to the GSIS
keys used by its historical statistics. That is the demonstrated reason all
**666 scored rows per simple procedure** in the later explicit-label Week 7
panel use position priors. This is a failure to consume player history, not a
comparison of two successfully learned history windows.

## Exact retained evidence

The full 17-file source-tree digest recomputed from commit
`eeddbfe5bfa5fe58420d9c1a09d7e5034f9c2448` is
`1afd948ff2e4fb60a692d3201fc05afff89a2658cdadf89d69f2137374e65ca4`.
It matches **all 24,288 frozen forecast rows**. The retained artifacts also match
that commit's `models.py` and `model_artifacts.py` SHA256 values exactly. This
pins the original behavior; it does not substitute today's source for issuance.

Twenty-two recent/pooled JSON model artifacts were restored and their file
digests matched all associated forecast references. All declare the required
summary columns present. Independently comparing each stored position-prior
mean against every planned simple-control fallback gives **14,267/14,267 exact
float matches**. This arithmetic check executes no fit or prediction function.

The later explicit-label panel has 666 scored category rows and 190 unique
players per simple procedure. Every scored row has a `sleeper:` player ID and
`fallback=position_prior`. Category rows overlap; they are not 666 independent
players or games. Missing and unsupported outcomes remain excluded under the
existing label contract.

## How the mismatch happened

The pinned [live adapter](https://github.com/NickNicky19/NFL-forecasting/blob/eeddbfe5bfa5fe58420d9c1a09d7e5034f9c2448/nfl_lab/live.py#L42)
used `p.get("gsis_id") or "sleeper:"+sid`. It did not apply an exact roster
Sleeper-to-GSIS bridge and did not normalize leading whitespace. Historical
statistics use GSIS keys. The pinned
[feature lookup](https://github.com/NickNicky19/NFL-forecasting/blob/eeddbfe5bfa5fe58420d9c1a09d7e5034f9c2448/nfl_lab/features.py#L27)
groups and matches exact `player_id` strings, so a Sleeper namespace or a
leading-space GSIS string cannot match the canonical historical key.

| Original planned player contexts | Recent 3 | Pooled 8 |
|---|---:|---:|
| All contexts | 736 | 736 |
| Unlinked `sleeper:` IDs, all prior | 596 | 596 |
| Leading-space GSIS IDs, all prior | 42 | 42 |
| Canonical GSIS IDs | 98 | 98 |
| Canonical GSIS contexts using history | 84 | 91 |
| Canonical GSIS contexts still using prior | 14 | 7 |
| Total prior contexts | 652 | 645 |

The 14/7 residual canonical empty windows may reflect missing/sparse history or
availability/slot rules; their precise player-level cause cannot be recovered
without the original history and query feature rows. They are not automatically
classified as rookies, DNP or a universal seven-day-lag bug.

The pinned [recent calculation](https://github.com/NickNicky19/NFL-forecasting/blob/eeddbfe5bfa5fe58420d9c1a09d7e5034f9c2448/nfl_lab/models.py#L187)
uses the provided mean/count windows when present. Invalid or empty provided
windows deliberately use the trained position prior; it does not secretly search
farther back. Therefore absent summary columns are ruled out as this batch's
cause. History is not absent for everyone: 84 recent and 91 pooled canonical
contexts consume it. Reducing the seven-day lag cannot repair incompatible IDs.

The later upstream `17f7eb717198ad286d09fc34c9900c01eb3b43e4` adapter adds an
exact identity crosswalk after the original capture. Existing later production
adapters are separate. This diagnosis does not assert that the original defect
still affects today's live procedure.

## What was repaired in V2

The original V2 module `nfl_v2/identity.py` provides exact binding and pre-fit
namespace/key coverage checks. It excludes invalid, conflicting, ambiguous and
nonunique forward/reverse bridge keys. Whitespace normalization requires a
matching already-qualified exact bridge, its source ID and the separately named
`qualified-gsis-whitespace-v1` policy. Without that evidence it abstains.
Source availability and permitted use remain the caller's responsibility.

Eight meaningful fixtures passed: exact missing-provider bridge, conflicts,
ambiguity, invalid namespaces, namespace versus new-player coverage, startup
without history, explicitly qualified whitespace normalization, and refusal to
normalize without a qualified crosswalk. This is software evidence only.

Use this guard on a **newly registered reconstruction** with qualified identities.
Do not rewrite archived forecast IDs or relax the existing outcome join, erase
the original fallback losses, or call corrected forecasts original pregame
issuance. Existing upstream crosswalk code should be preserved rather than
duplicating an already completed fix.

## Can the public objects supply clean history tests now?

The public `state/training` gzip is an aggregate campaign/report. Its
`row_level_outputs` field explicitly says **“local ignored only; never included
in immutable aggregate receipt.”** The models declare no raw training rows.
The eleven public input manifests do not include the original `648fc…` manifest;
the forecast retains its feature hash, not recoverable feature values. These
objects cannot authenticate the original training/query snapshot.

The supported next action is the integrator's newly acquired permitted
statistics and identities, with a new reconstruction identity, exact chronology,
label support and predeclared startup. Original position priors were fitted from
older football data, so this old fallback cannot be called strict current-season
football information. No clean H-CURRENT/H-RECENT/H-MULTI fit was executed by this
diagnosis worker.

The latest inspected nflverse-data main is
`a78da18ca93f167bd0a2af274df48f539fa4153c`. Its
[LICENSE.md](https://github.com/nflverse/nflverse-data/blob/a78da18ca93f167bd0a2af274df48f539fa4153c/LICENSE.md)
is CC BY 4.0; its README explicitly describes the automated data releases and
nflreadr/manual download route. Attribute nflverse and original provenance, link
the license and indicate transformations. This does not override inherited
restrictions on PFR-derived snaps, FTN or other provider feeds.

This worker performed zero new fits, forecasts or NFL outcome scores and changed
neither upstream nor production. The JSON companion retains exact source/model
hashes, coverage and limitations without raw player rows or private locators.
