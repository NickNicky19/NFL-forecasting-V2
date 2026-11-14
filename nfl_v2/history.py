"""Bounded, supplied-snapshot history controls; no acquisition or NFL fit on import.

Each origin is an independently supplied, cutoff-qualified snapshot. These simple
empirical controls have no football predictors, pretrained priors, tuning or
calibration. They do not authenticate source facts or historical issuance.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from statistics import fmean
from typing import Sequence

from .scoring import TARGETS, valid_actual

VERSION = "v2-empirical-history-controls-v1"
ARMS = ("H-CURRENT", "H-RECENT", "H-MULTI")
TIERS = {"authentic_pregame_vintage", "qualified_asof_reconstruction",
         "current_vintage_reconstruction"}
POSITIONS = {"QB", "RB", "FB", "WR", "TE"}


def timestamp(value: str) -> datetime:
    """Unknown or timezone-naive clocks never establish availability."""
    if not isinstance(value, str) or not value:
        raise ValueError("explicit timestamp required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return parsed.astimezone(timezone.utc)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class SourceAdmission:
    source_id: str
    evidence_tier: str
    availability_basis: str
    targets: tuple[str, ...]
    complete_statistic_contract: str
    participation_contract: str
    position_contract: str
    license_review_id: str

    def validate(self):
        if self.evidence_tier not in TIERS or not self.targets or not set(self.targets) <= set(TARGETS):
            raise ValueError("unqualified evidence tier/target")
        if not all(isinstance(v, str) and v.strip() for v in (
                self.source_id, self.availability_basis, self.complete_statistic_contract,
                self.participation_contract, self.position_contract, self.license_review_id)):
            raise ValueError("source admission contracts required")


@dataclass(frozen=True)
class Observation:
    observation_id: str
    source_id: str
    game_id: str
    player_id: str
    position: str
    target: str
    season: int
    week: int
    kickoff_utc: str
    available_utc: str
    value: float
    participation: str = "played"
    period: str = "REG"


@dataclass(frozen=True)
class Query:
    query_id: str
    source_id: str
    game_id: str
    player_id: str
    position: str
    target: str
    season: int
    week: int
    kickoff_utc: str
    period: str = "REG"


@dataclass(frozen=True)
class Origin:
    origin_id: str
    cutoff_utc: str
    queries: tuple[Query, ...]
    observations: tuple[Observation, ...]


@dataclass(frozen=True)
class RunManifest:
    experiment_id: str
    evaluation_panel_id: str
    cohort_definition_id: str
    source_admission_ids: tuple[str, ...]
    evaluation_seasons: tuple[int, ...]
    max_origins: int
    max_observations_per_origin: int
    max_queries_per_origin: int
    max_forecast_cells: int
    max_summary_groups: int
    max_candidate_row_checks: int
    training_floor: int = 2022
    fallback_rule: str = "same_arm_position_empirical_then_constant_zero"
    update_rule: str = "recompute_at_each_supplied_origin"
    feature_memory: str = "none_no_football_predictors"
    tuned_or_external_priors: bool = False
    procedure_version: str = VERSION

    def validate(self):
        if not all(isinstance(x, str) and x.strip() for x in (
                self.experiment_id, self.evaluation_panel_id, self.cohort_definition_id)):
            raise ValueError("registered experiment/panel/cohort required")
        if (not self.source_admission_ids or len(set(self.source_admission_ids)) != len(self.source_admission_ids)
                or not self.evaluation_seasons or len(set(self.evaluation_seasons)) != len(self.evaluation_seasons)
                or not set(self.evaluation_seasons) <= set(range(2022, 2027))):
            raise ValueError("explicit unique source and evaluation scope required")
        if any(type(x) is not int or x < 1 for x in (
                self.max_origins, self.max_observations_per_origin,
                self.max_queries_per_origin, self.max_forecast_cells, self.max_summary_groups,
                self.max_candidate_row_checks)):
            raise ValueError("positive finite integer bounds required")
        if (self.training_floor != 2022 or self.procedure_version != VERSION
                or self.fallback_rule != "same_arm_position_empirical_then_constant_zero"
                or self.update_rule != "recompute_at_each_supplied_origin"
                or self.feature_memory != "none_no_football_predictors"
                or self.tuned_or_external_priors is not False):
            raise ValueError("changed method/policy needs a new implementation version")


def _identity(row):
    return row.game_id, row.player_id, row.target


def _common(row, sources):
    if not all(isinstance(x, str) and x.strip() for x in (row.game_id, row.player_id)):
        raise ValueError("exact identity required")
    if (row.period != "REG" or row.position not in POSITIONS or row.target not in TARGETS
            or type(row.season) is not int or not 2022 <= row.season <= 2026
            or type(row.week) is not int or not 1 <= row.week <= 18):
        raise ValueError("unregistered period/role/target/season/week")
    if row.source_id not in sources or row.target not in sources[row.source_id].targets:
        raise ValueError("source/target not admitted")
    return timestamp(row.kickoff_utc)


def _lower_median(values):
    return sorted(values)[(len(values) - 1) // 2]


def run(origins: Sequence[Origin], admissions: Sequence[SourceAdmission],
        manifest: RunManifest, *, strict_current: bool = False) -> dict:
    """Forecast every frozen query for all three arms, or the strict-current arm.

    Callers supply one already-qualified snapshot per origin, *not* a full table
    with future labels. Any future/unavailable/target-game source row fails closed.
    Budgets are validated before forecast calculation. Output retains every query,
    including startup and unseen-player fallbacks. No score or issuance is made.
    """
    manifest.validate()
    if type(strict_current) is not bool:
        raise ValueError("strict_current must be boolean")
    if len(origins) > manifest.max_origins or not origins:
        raise ValueError("origin bound or empty run")
    sources = {}
    for source in admissions:
        source.validate()
        if source.source_id in sources:
            raise ValueError("duplicate source admission")
        sources[source.source_id] = source
    if set(sources) != set(manifest.source_admission_ids):
        raise ValueError("manifest and source admissions differ")
    arms = ("H-CURRENT",) if strict_current else ARMS
    ids, query_ids, all_query_keys, all_games = set(), set(), set(), set()
    cells, groups, row_checks = 0, 0, 0
    # Validation completes before predictions are computed.
    for origin in origins:
        if not origin.origin_id or origin.origin_id in ids:
            raise ValueError("duplicate/missing origin identity")
        ids.add(origin.origin_id)
        cutoff = timestamp(origin.cutoff_utc)
        if (len(origin.observations) > manifest.max_observations_per_origin
                or len(origin.queries) > manifest.max_queries_per_origin or not origin.queries):
            raise ValueError("snapshot/query bound or empty origin")
        if len({q.season for q in origin.queries}) != 1:
            raise ValueError("one evaluation season per origin required")
        target_games, source_keys, observation_ids = set(), set(), set()
        for query in origin.queries:
            kickoff = _common(query, sources)
            if (not query.query_id or query.query_id in query_ids or _identity(query) in all_query_keys
                    or query.season not in manifest.evaluation_seasons
                    or (query.season == 2026 and query.week > 7) or cutoff >= kickoff):
                raise ValueError("query identity/evaluation period/cutoff invalid")
            query_ids.add(query.query_id)
            all_query_keys.add(_identity(query))
            target_games.add(query.game_id)
            all_games.add(query.game_id)
            cells += len(arms) * (1 if query.target == "anytime_td" else 2)
        for observation in origin.observations:
            kickoff = _common(observation, sources)
            available = timestamp(observation.available_utc)
            if (not observation.observation_id or observation.observation_id in observation_ids
                    or _identity(observation) in source_keys or observation.game_id in target_games
                    or observation.season > origin.queries[0].season
                    or not kickoff < available < cutoff or observation.participation != "played"
                    or not valid_actual(observation.target, observation.value)):
                raise ValueError("duplicate/future/target-game/nonparticipant/incomplete outcome")
            observation_ids.add(observation.observation_id)
            source_keys.add(_identity(observation))
        groups += sum(len(arms) * (1 if target == "anytime_td" else 2)
                      for target in {q.target for q in origin.queries})
        # Candidate filtering plus player and position scans: each visits at most N rows.
        row_checks += 3 * len(origin.observations) * len(origin.queries) * len(arms)
    if (cells > manifest.max_forecast_cells or groups > manifest.max_summary_groups
            or row_checks > manifest.max_candidate_row_checks):
        raise ValueError("forecast/empirical-summary budget exceeded")
    result = []
    for origin in origins:
        for query in origin.queries:
            for arm in arms:
                floor = query.season if arm == "H-CURRENT" else (
                    max(2022, query.season - 1) if arm == "H-RECENT" else 2022)
                eligible = [o for o in origin.observations
                            if floor <= o.season <= query.season and o.target == query.target]
                own = [o for o in eligible if o.player_id == query.player_id and o.position == query.position]
                position = [o for o in eligible if o.position == query.position]
                chosen = own or position
                fallback = "none" if own else ("position_empirical" if position else "constant_zero_startup")
                products = ("event_probability",) if query.target == "anytime_td" else ("empirical_mean", "lower_median")
                for product in products:
                    values = [o.value for o in chosen]
                    value = (fmean(values) if product != "lower_median" else _lower_median(values)) if values else 0.0
                    result.append({
                        "origin_id": origin.origin_id, "query_id": query.query_id,
                        "query_source_id": query.source_id,
                        "query_evidence_tier": sources[query.source_id].evidence_tier,
                        "game_id": query.game_id, "player_id": query.player_id,
                        "position": query.position, "target": query.target,
                        "season": query.season, "week": query.week,
                        "cutoff_utc": timestamp(origin.cutoff_utc).isoformat(),
                        "history_regime": arm, "fit_season_floor": floor,
                        "fit_season_ceiling": query.season,
                        "feature_memory": manifest.feature_memory,
                        "information_policy": "strict_current_season_football_information" if strict_current else "fit_window_comparison_no_predictor_memory",
                        "product": product, "forecast": value, "fallback": fallback,
                        "player_n": len(own), "used_n": len(chosen),
                        "training_observation_ids": [o.observation_id for o in chosen],
                        "source_ids": sorted({o.source_id for o in chosen}),
                        "evidence_tiers": sorted({sources[o.source_id].evidence_tier for o in chosen}),
                        "latest_training_available_utc": max((timestamp(o.available_utc).isoformat() for o in chosen), default=None),
                        "status": "forecasted_unscored",
                        "procedure_version": VERSION,
                        "comparison_view": "full_system_including_fallback",
                    })
    return {"procedure_version": VERSION, "manifest_sha256": digest(asdict(manifest)),
            "source_admissions_sha256": digest([asdict(s) for s in admissions]),
            "origin_inputs_sha256": digest([asdict(o) for o in origins]),
            "policy_run_sha256": digest({"strict_current": strict_current,
                                         "manifest": asdict(manifest)}),
            "query_membership_sha256": digest([[o.origin_id, [asdict(q) for q in o.queries]] for o in origins]),
            "origins": len(origins), "unique_queries": len(query_ids),
            "unique_games": len(all_games), "unique_player_game_targets": len(all_query_keys),
            "forecast_cells": len(result), "empirical_summary_groups": groups,
            "candidate_row_checks_bound": row_checks,
            "optimization_fits": 0, "scores": 0, "rows": result}
