"""Explicit identity binding for new reconstructions; original rows stay immutable.

The caller must qualify bridge source/timing before calling this module. These
functions never match names, fetch sources, rewrite archived IDs or fit models.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from collections.abc import Iterable

GSIS = re.compile(r"00-\d{7}\Z")
GSIS_TRIM_POLICY = "qualified-gsis-whitespace-v1"


@dataclass(frozen=True)
class IdentityBinding:
    player_id: str | None
    state: str


def resolve_gsis_identity(provider_gsis: str | None,
                          qualified_bridge_gsis: Iterable[str] = (), *,
                          bridge_source_id: str | None = None,
                          normalization_policy: str | None = None) -> IdentityBinding:
    """Resolve one already source-qualified bridge, abstaining on conflicts.

    Missing or ambiguous identity is explicit. The caller may issue an honestly
    named cold-start fallback, but must not present its features as player history.
    """
    raw_bridge = {str(value) for value in qualified_bridge_gsis if value is not None}
    bridge = {value.strip() for value in raw_bridge}
    raw_direct = str(provider_gsis) if provider_gsis is not None else None
    direct = raw_direct.strip() if raw_direct is not None else None
    normalized = bridge != raw_bridge or direct != raw_direct
    if any(not GSIS.fullmatch(value) for value in bridge) or (direct is not None and not GSIS.fullmatch(direct)):
        return IdentityBinding(None, "INVALID_GSIS_BINDING")
    if len(bridge) > 1:
        return IdentityBinding(None, "AMBIGUOUS_BRIDGE")
    linked = next(iter(bridge), None)
    if direct is not None and linked is not None and direct != linked:
        return IdentityBinding(None, "CONFLICTING_PROVIDER_BRIDGE")
    if normalized and (not bridge_source_id or normalization_policy != GSIS_TRIM_POLICY or linked is None):
        return IdentityBinding(None, "WHITESPACE_REQUIRES_QUALIFIED_EXACT_BRIDGE")
    if linked is not None:
        return IdentityBinding(linked, "QUALIFIED_EXACT_BRIDGE_WHITESPACE_NORMALIZED" if normalized else "QUALIFIED_EXACT_BRIDGE")
    if direct is not None:
        return IdentityBinding(direct, "PROVIDER_GSIS_WHITESPACE_NORMALIZED" if normalized else "PROVIDER_GSIS")
    return IdentityBinding(None, "UNLINKED_COLD_START")


def unique_gsis_bridge(rows: Iterable[tuple[str, str]], *, source_id: str) -> dict[str, str]:
    """Retain only one-to-one canonical keys from a caller-qualified snapshot.

    Duplicate identical bindings are harmless. Conflicting or invalid forward
    and reverse bindings are excluded; this function never resolves them by name.
    Source availability and permitted use remain the caller's responsibility.
    """
    if not source_id:
        raise ValueError("qualified bridge source ID required")
    forward: dict[str, set[str]] = {}
    reverse: dict[str, set[str]] = {}
    for sid, gsis in rows:
        sid, gsis = str(sid), str(gsis)
        forward.setdefault(sid, set()).add(gsis)
        reverse.setdefault(gsis, set()).add(sid)
    return {sid: next(iter(ids)) for sid, ids in forward.items()
            if len(ids) == 1 and GSIS.fullmatch(next(iter(ids)))
            and len(reverse[next(iter(ids))]) == 1}


def history_join_audit(history_player_ids: Iterable[str], query_player_ids: Iterable[str]) -> dict:
    """Count namespace and exact-key coverage before any statistical fitting.

    No-history startup is separate from mismatched namespaces. Counts measure
    query rows, not unique players or independently scored NFL observations.
    """
    history = {str(value) for value in history_player_ids}
    queries = [str(value) for value in query_player_ids]
    matches = sum(value in history for value in queries)
    history_all_gsis = bool(history) and all(GSIS.fullmatch(value) for value in history)
    incompatible = sum(not GSIS.fullmatch(value) for value in queries) if history_all_gsis else 0
    return {
        "history_unique_players": len(history), "query_rows": len(queries),
        "exact_history_key_matches": matches, "unmatched_query_rows": len(queries) - matches,
        "incompatible_namespace_query_rows": incompatible,
        "state": "NO_TRAINING_HISTORY_STARTUP" if not history else
                 "NAMESPACE_MISMATCH_PRESENT" if incompatible else "CANONICAL_KEYS_AUDITED",
    }
