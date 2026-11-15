"""Frozen lagged context-choice profiles and conditional completion increment.

PBP-only profiles use the retained seven-day reconstruction. FTN-dependent
conversion parameters retain FTN Data via nflverse CC-BY-SA-4.0 attribution.
No query outcome, realized query mixture or participation is read here.
"""
from __future__ import annotations

import collections
import math

import numpy as np
from scipy import optimize, special

from .qb_depth_catchability_v2 import ConvergedDepthCompletionModel

VERSION = "B-INFORMATION-SKILL-PASS-MIX-v1"
CONTEXTS = 25
REFERENCE_CONTEXT = 24
GROUP_ORDER = ("team", "opponent")
ORIGINAL_MIX_FEATURES = ("log_static_QB_mix_over_league_mix",)
ENRICHED_MIX_FEATURES = ORIGINAL_MIX_FEATURES + (
    "team_context_choice_logratio", "opponent_adjusted_context_choice_logratio")
PARENT_NUMERIC_ORDER = tuple(f"context_{i:02d}" for i in range(CONTEXTS)) + (
    "own_completion_logit", "opponent_conversion_residual_main",
    "opponent_conversion_residual_context", "team_conversion_residual",
    "depth_known_fraction", "depth_known_log1p", "depth_source_age_log1p",
    "depth_own_known_missing", "depth_pooled_known_missing",
    "depth_catchability_logit")
CONVERSION_FEATURE_ORDER = PARENT_NUMERIC_ORDER + ENRICHED_MIX_FEATURES[1:]


def _counts(value, name):
    result = np.asarray(value, dtype=float)
    if (result.shape != (CONTEXTS,) or not np.isfinite(result).all()
            or np.any(result < 0) or np.any(result != np.floor(result))):
        raise ValueError("Invalid nonnegative context counts: " + name)
    return result


def _mix(value, name):
    result = np.asarray(value, dtype=float)
    if (result.shape != (CONTEXTS,) or not np.isfinite(result).all()
            or np.any(result <= 0) or not math.isclose(float(result.sum()), 1., abs_tol=1e-10)):
        raise ValueError("Invalid positive context composition: " + name)
    return result


def _clock(value, name):
    if value is None or isinstance(value, bool):
        raise ValueError("Explicit finite clock required: " + name)
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Explicit finite clock required: " + name)
    return value


class PassMixHistory:
    """Profiles aggregate full admitted QB-game contexts before last16 games.

    Each defense expectation uses that earlier game's own static QB mixer.
    It is never recomputed using the later query's QB or league composition.
    """
    def __init__(self, history):
        self.history = history
        self.cache = {}
        groups = {field: collections.defaultdict(list) for field in GROUP_ORDER}
        seen = set()
        for row in history.rows:
            identity = row["game_id"], row["player_id"]
            if identity in seen:
                raise ValueError("Duplicate canonical QB-game context")
            seen.add(identity)
            available = _clock(row.get("available"), "historical available")
            kickoff = _clock(row.get("kickoff"), "historical kickoff")
            if not kickoff < available:
                raise ValueError("Historical context available before completed game")
            actual = _counts(row["context_attempts"], "historical attempts")
            earlier_mix = _mix(history.describe(row)["mix"], "prior-game QB mix")
            bound = dict(game_id=row["game_id"], player_id=row["player_id"],
                         kickoff=kickoff, available=available,
                         attempts=actual, expected=float(actual.sum()) * earlier_mix,
                         expected_static_QB_mix=earlier_mix,
                         expectation_cutoff=kickoff,
                         expectation_latest_source=history.describe(row)["latest_source_available"])
            for field in GROUP_ORDER:
                groups[field][row[field], row["game_id"]].append(bound)
        self.games = {}
        for field in GROUP_ORDER:
            by_identity = collections.defaultdict(list)
            for (identity, game_id), components in groups[field].items():
                kickoffs = {row["kickoff"] for row in components}
                if len(kickoffs) != 1:
                    raise ValueError("Conflicting canonical game times")
                by_identity[identity].append(dict(
                    game_id=game_id, kickoff=components[0]["kickoff"],
                    available=max(row["available"] for row in components),
                    attempts=np.sum([row["attempts"] for row in components], axis=0),
                    expected=np.sum([row["expected"] for row in components], axis=0),
                    components=components))
            for games in by_identity.values():
                games.sort(key=lambda row: (row["kickoff"], row["game_id"]))
            self.games[field] = by_identity

    def _eligible_games(self, field, identity, cutoff):
        # Admit first, then take last games in game-time order.
        return [row for row in self.games[field].get(identity, ())
                if row["available"] < cutoff][-16:]

    @staticmethod
    def _sum(games, name):
        return (np.sum([row[name] for row in games], axis=0)
                if games else np.zeros(CONTEXTS))

    @staticmethod
    def _trace(games, cutoff):
        source = max((row["available"] for row in games), default=None)
        game = max((row["kickoff"] for row in games), default=None)
        return dict(game_ids=[row["game_id"] for row in games], games=len(games),
                    latest_source_available=source, latest_game_kickoff=game,
                    source_age_days=None if source is None else (cutoff-source)/86400.,
                    game_age_days=None if game is None else (cutoff-game)/86400.,
                    status="OBSERVED_HISTORY_SHRUNK" if games else "ABSENT_HISTORY_PRIOR_ONLY",
                    freshness="AGE_RECORDED_NO_NEW_STALENESS_CUTOFF")

    def describe(self, query):
        cutoff = _clock(query.get("kickoff"), "query cutoff")
        key = (query["player_id"], query["game_id"], cutoff,
               query["team"], query["opponent"])
        if key in self.cache:
            return self.cache[key]
        prior = self.history.describe(query)
        base = _mix(prior["mix"], "query static QB mix")
        attempts, _ = self.history.global_counts(cutoff)
        league = _mix((np.asarray(attempts, float)+1.) /
                      (float(np.sum(attempts))+CONTEXTS), "query league mix")
        team = self._eligible_games("team", query["team"], cutoff)
        opponent = self._eligible_games("opponent", query["opponent"], cutoff)
        team_counts = self._sum(team, "attempts")
        opponent_counts = self._sum(opponent, "attempts")
        opponent_expected = self._sum(opponent, "expected")
        team_prior = 20. * league
        defense_prior = 100. * league
        team_mix = (team_counts+team_prior)/(float(team_counts.sum())+20.)
        team_ratio = np.log(team_mix/base)
        opponent_ratio = np.log((opponent_counts+defense_prior) /
                                (opponent_expected+defense_prior))
        if not np.isfinite(team_ratio).all() or not np.isfinite(opponent_ratio).all():
            raise ValueError("Nonfinite lagged context-choice profile")
        source_times = [row["available"] for row in team+opponent]
        if prior["latest_source_available"] is not None:
            source_times.append(prior["latest_source_available"])
        latest = max(source_times, default=None)
        if latest is not None and not latest < cutoff:
            raise ValueError("Nonprior source reached context-choice query")
        result = dict(version=VERSION, base_mix=base, league_mix=league,
                      team_logratio=team_ratio, opponent_logratio=opponent_ratio,
                      team_counts=team_counts, team_attempts=float(team_counts.sum()),
                      team_prior_mass=20., team_prior_counts=team_prior,
                      team_shrunk_mix=team_mix,
                      opponent_counts=opponent_counts,
                      opponent_expected=opponent_expected,
                      opponent_attempts=float(opponent_counts.sum()),
                      opponent_expected_attempts=float(opponent_expected.sum()),
                      opponent_prior_mass=100., opponent_prior_counts=defense_prior,
                      team_trace=self._trace(team, cutoff),
                      opponent_trace=self._trace(opponent, cutoff),
                      opponent_expectation_bindings=[dict(
                          game_id=game["game_id"],
                          components=[dict(player_id=row["player_id"],
                                           credited_attempt_denominator=float(row["attempts"].sum()),
                                           static_QB_mix=row["expected_static_QB_mix"],
                                           expectation_cutoff=row["expectation_cutoff"],
                                           latest_expected_source=row["expectation_latest_source"])
                                      for row in game["components"]])
                          for game in opponent],
                      cutoff=cutoff, latest_consumed_source=latest,
                      own_history_status=prior["fallback"],
                      fallback=dict(team="none" if team else "LEAGUE_PRIOR_ONLY",
                                    opponent="none" if opponent else "ADJUSTED_RATIO_PRIOR_ONLY"),
                      source_policy="CURRENT_VINTAGE_KICKOFF_PLUS_7D_STRICT_RECONSTRUCTION",
                      population="RETAINED_QUALIFIED_QB_CONTEXT_HISTORY_NOT_ALL_ROUTES_OR_PERSONNEL")
        self.cache[key] = result
        return result


def composition_design(query, profiles, enriched):
    d = profiles.describe(query)
    base, league = _mix(d["base_mix"], "base"), _mix(d["league_mix"], "league")
    columns = [np.log(base/league)]
    if enriched:
        columns += [d["team_logratio"], d["opponent_logratio"]]
    design = np.column_stack(columns)
    if not np.isfinite(design).all():
        raise ValueError("Nonfinite composition design")
    return np.log(base), design


def composition_objective(beta, offset, x, y, penalty):
    """Pure frozen multinomial loss/gradient, shared by fit and verification."""
    n = y.sum(axis=1)
    intercepts = np.r_[beta[:REFERENCE_CONTEXT], 0.]
    eta = offset + intercepts + np.einsum("njk,k->nj", x, beta[REFERENCE_CONTEXT:])
    normalizer = special.logsumexp(eta, axis=1)
    probability = np.exp(eta-normalizer[:, None])
    residual = n[:, None]*probability-y
    loss = float(np.sum(n*normalizer-np.sum(y*eta, axis=1))
                 + .5*np.dot(penalty*beta, beta))
    gradient = np.r_[residual[:, :REFERENCE_CONTEXT].sum(axis=0),
                     np.einsum("nj,njk->k", residual, x)] + penalty*beta
    return loss, gradient


def conditional_binomial_objective(beta, x, n, y, penalty):
    """Pure frozen conditional-binomial loss/gradient used by the real fit."""
    eta = x@beta
    return (float(np.sum(n*np.logaddexp(0., eta)-y*eta)
                  + .5*np.dot(penalty*beta, beta)),
            x.T@(n*special.expit(eta)-y)+penalty*beta)


class CompositionModel:
    def __init__(self, enriched=False):
        self.enriched = bool(enriched)
        self.feature_order = (ENRICHED_MIX_FEATURES if self.enriched else ORIGINAL_MIX_FEATURES)

    def fit(self, rows, profiles):
        if not rows:
            return None
        prepared = [composition_design(row, profiles, self.enriched) for row in rows]
        offset = np.asarray([value[0] for value in prepared])
        x = np.asarray([value[1] for value in prepared])
        y = np.asarray([_counts(row["context_attempts"], "composition label") for row in rows])
        n = y.sum(axis=1)
        if not n.sum():
            return None
        width = REFERENCE_CONTEXT + len(self.feature_order)
        penalty = np.r_[np.full(REFERENCE_CONTEXT, 20.), np.full(len(self.feature_order), 10.)]

        def objective(beta):
            return composition_objective(beta, offset, x, y, penalty)

        fit = optimize.minimize(objective, np.zeros(width), jac=True, method="L-BFGS-B",
                                options=dict(maxiter=300, ftol=1e-10, gtol=1e-6))
        self.beta = fit.x
        self.optimization = dict(success=bool(fit.success), iterations=int(fit.nit),
                                 message=str(fit.message), finite=bool(np.isfinite(fit.x).all()),
                                 training_games=len(rows), training_attempts=int(n.sum()))
        if not self.optimization["finite"]:
            raise ValueError("Nonfinite composition coefficients")
        return self

    def probabilities(self, query, profiles):
        offset, x = composition_design(query, profiles, self.enriched)
        eta = offset + np.r_[self.beta[:REFERENCE_CONTEXT], 0.] + x@self.beta[REFERENCE_CONTEXT:]
        return _mix(np.exp(eta-special.logsumexp(eta)), "predicted context mixture")

    def payload(self):
        return dict(kind="multinomial_context_composition_v1", version=VERSION,
                    enriched=self.enriched, reference_context=REFERENCE_CONTEXT,
                    feature_order=list(self.feature_order), beta=self.beta.tolist(),
                    optimization=self.optimization)

    @classmethod
    def restore(cls, payload):
        if (payload["kind"] != "multinomial_context_composition_v1"
                or payload["version"] != VERSION
                or payload["reference_context"] != REFERENCE_CONTEXT
                or type(payload["enriched"]) is not bool):
            raise ValueError("Composition parameter contract")
        result = cls(payload["enriched"])
        if payload["feature_order"] != list(result.feature_order):
            raise ValueError("Composition feature order")
        result.beta = np.asarray(payload["beta"], dtype=float)
        if (result.beta.shape != (REFERENCE_CONTEXT+len(result.feature_order),)
                or not np.isfinite(result.beta).all()):
            raise ValueError("Composition coefficient shape/finite")
        result.optimization = payload["optimization"]
        return result


class AugmentedConversion(ConvergedDepthCompletionModel):
    """Unchanged C2 learner plus the two frozen per-context profile values."""
    def __init__(self):
        super().__init__(values=True, penalty=20.)
        self.width = len(CONVERSION_FEATURE_ORDER)

    def numeric(self, query, history, chart, context, profiles):
        parent = super().numeric(query, history, chart, context)
        d = profiles.describe(query)
        return np.r_[parent, d["team_logratio"][context], d["opponent_logratio"][context]]

    def matrix(self, query, history, chart, profiles):
        x = np.asarray([self.numeric(query, history, chart, j, profiles) for j in range(CONTEXTS)])
        if x.shape != (CONTEXTS, self.width) or not np.isfinite(x).all():
            raise ValueError("Augmented conversion numeric design")
        return x

    def fit(self, rows, history, chart, profiles):
        self.levels = {field: sorted({row[field] for row in rows}) for field in GROUP_ORDER}
        offset = self.width
        self.columns = {}
        for field in GROUP_ORDER:
            self.columns[field] = {value: offset+i for i, value in enumerate(self.levels[field])}
            offset += len(self.levels[field])
        xx, aa, cc = [], [], []
        for row in rows:
            attempts = _counts(row["context_attempts"], "conversion attempts")
            completions = _counts(row["context_completions"], "conversion completions")
            if np.any(completions > attempts):
                raise ValueError("Completion greater than attempts")
            numeric = self.matrix(row, history, chart, profiles)
            for j, (n, c) in enumerate(zip(attempts, completions)):
                if not n:
                    continue
                x = np.zeros(offset)
                x[:self.width] = numeric[j]
                for field in GROUP_ORDER:
                    x[self.columns[field][row[field]]] = 1.
                xx.append(x); aa.append(n); cc.append(c)
        if not aa:
            return None
        x, n, y = np.asarray(xx), np.asarray(aa), np.asarray(cc)
        penalty = np.full(offset, self.penalty)
        penalty[:CONTEXTS] = 2.
        penalty[CONTEXTS:self.width] = 10.

        def objective(beta):
            return conditional_binomial_objective(beta, x, n, y, penalty)

        fit = optimize.minimize(objective, np.zeros(offset), jac=True, method="L-BFGS-B",
                                options=dict(maxiter=600, ftol=1e-10, gtol=1e-6))
        self.beta = fit.x
        self.optimization = dict(success=bool(fit.success), iterations=int(fit.nit),
                                 message=str(fit.message), finite=bool(np.isfinite(fit.x).all()),
                                 training_context_rows=len(n), training_attempts=int(n.sum()))
        if not self.optimization["finite"]:
            raise ValueError("Nonfinite augmented conversion coefficients")
        return self

    def probabilities(self, query, history, chart, profiles):
        numeric = self.matrix(query, history, chart, profiles)
        x = np.zeros((CONTEXTS, len(self.beta)))
        x[:, :self.width] = numeric
        for field in GROUP_ORDER:
            column = self.columns[field].get(query[field])
            if column is not None:
                x[:, column] = 1.
        return special.expit(x@self.beta)

    def payload(self):
        return dict(kind="pass_mix_augmented_C2_conversion_v1", version=VERSION,
                    values=True, penalty=self.penalty, feature_order=list(CONVERSION_FEATURE_ORDER),
                    coefficient_group_order=list(GROUP_ORDER), levels=self.levels,
                    beta=self.beta.tolist(), optimization=self.optimization)

    @classmethod
    def restore(cls, payload):
        if (payload["kind"] != "pass_mix_augmented_C2_conversion_v1"
                or payload["version"] != VERSION or payload["values"] is not True
                or payload["penalty"] != 20.
                or payload["feature_order"] != list(CONVERSION_FEATURE_ORDER)
                or payload["coefficient_group_order"] != list(GROUP_ORDER)
                or set(payload["levels"]) != set(GROUP_ORDER)):
            raise ValueError("Augmented conversion parameter contract")
        result = cls()
        result.levels, result.columns = {}, {}
        offset = result.width
        for field in GROUP_ORDER:
            levels = payload["levels"][field]
            if len(levels) != len(set(levels)):
                raise ValueError("Duplicate coefficient identity")
            result.levels[field] = list(levels)
            result.columns[field] = {value: offset+i for i, value in enumerate(levels)}
            offset += len(levels)
        result.beta = np.asarray(payload["beta"], dtype=float)
        if result.beta.shape != (offset,) or not np.isfinite(result.beta).all():
            raise ValueError("Augmented conversion coefficient shape/finite")
        result.optimization = payload["optimization"]
        return result
