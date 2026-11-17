"""Frozen usage-only T -> QB attempts -> fixed-conversion count experiment.

No acquisition, fitting, or target-game reads occur on import. Historical source
admission is delegated to the retained OpportunityHistory (+7 days, strict <).
T is its documented offensive-opportunity proxy, not dropbacks or all NFL snaps.
"""
from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
from scipy import optimize, special, stats

from .player_context_matchup import CountLaw
from .distribution_laws import Law

VERSION = 'B-INFORMATION-SKILL-OPPORTUNITY-v1'
TEAM_FEATURES = ('intercept', 'log_offense_O_vs_pool', 'log_defense_O_vs_pool')
SHARE_FEATURES = ('intercept', 'offense_ATT_per_O_logit_contrast',
                  'log_T_vs_earlier_offense_O', 'latest_QB_team_ATT_share_logit_change')
TAIL_TOL = 1e-12
MEAN_TAIL_TOL = 1e-9
MAX_GRID = 5000
INITIAL_SHAPE = 20.
INITIAL_ETA = float(special.logit((INITIAL_SHAPE - .5) / 199.5))
OPTIONS = dict(maxiter=300, ftol=1e-10, gtol=1e-6)


class SupportError(ValueError):
    """Qualified earlier information is insufficient; caller uses full parent."""


class IntegrationError(ValueError):
    """Frozen numerical precision/resource guard failed; no renormalization."""


def _logit(p):
    if not math.isfinite(p) or not 0 < p < 1:
        raise SupportError('NONINTERIOR_EARLIER_RATE')
    return float(special.logit(p))


def _sum(rows, field):
    return float(math.fsum(r['counts'][field] for r in rows))


def _team_map(history):
    # The map is an identity index only. Counts may be consumed solely through
    # strictly admitted earlier QB rows below; never look up the query's game.
    return {(r['game_id'], r['team']): r for r in history.team_rows}


def build_design(history, query):
    """Only canonical identity/time/team/opponent fields are read from query.

    Team design can be used on all team rows without requiring an own-QB row.
    Share x[2] is a placeholder: build_share_matrix inserts historical observed
    conditional exposure, while mixed_law integrates future T itself.
    """
    cutoff = float(query.get('cutoff', query['kickoff']))
    kickoff = float(query['kickoff'])
    if not math.isfinite(cutoff) or not math.isfinite(kickoff) or cutoff > kickoff:
        raise SupportError('INVALID_QUERY_CUTOFF')
    team, opponent = query['team'], query['opponent']
    if not isinstance(team, str) or not isinstance(opponent, str):
        raise SupportError('MISSING_CANONICAL_TEAM')
    prior = history.rows(cutoff)
    offense = history.rows(cutoff, team=team)
    defense = history.rows(cutoff, defense=opponent)
    support = dict(cutoff=cutoff, query_team=team, query_opponent=opponent,
                   team_games=len(offense), defense_games=len(defense), pooled_team_games=len(prior),
                   offense_game_ids=[r['game_id'] for r in offense],
                   defense_game_ids=[r['game_id'] for r in defense],
                   latest_team_source=max((r['available'] for r in offense), default=None),
                   latest_defense_source=max((r['available'] for r in defense), default=None),
                   latest_pooled_source=max((r['available'] for r in prior), default=None),
                   latest_ratio_rule='PREFIT_JEFFREYS_HALF_OVER_ONE_LATEST_GAME_ONLY',
                   source_tier='CURRENT_VINTAGE_SEVEN_DAY_RECONSTRUCTION',
                   personnel_information=False)
    result = dict(team_x=None, team_offset=None, muoffset=None, share_x=None,
                  share_offset=None, T_reference=None, Tref=None, team_eligible=False,
                  share_eligible=False, eligible=False, fallback_reason=None, support=support)
    if not prior:
        result['fallback_reason'] = 'NO_EARLIER_TEAM_SUPPORT'
        return result
    pooled_T = _sum(prior, 'opportunities') / len(prior)
    if pooled_T <= 0:
        result['fallback_reason'] = 'NONPOSITIVE_POOLED_TEAM_OPPORTUNITY'
        return result
    offense_T = (_sum(offense, 'opportunities') + 4 * pooled_T) / (len(offense) + 4)
    defense_T = (_sum(defense, 'opportunities') + 4 * pooled_T) / (len(defense) + 4)
    result.update(team_x=[1., math.log(offense_T / pooled_T), math.log(defense_T / pooled_T)],
                  team_offset=math.log(pooled_T), muoffset=math.log(pooled_T),
                  T_reference=offense_T, Tref=offense_T, team_eligible=True)
    support.update(pooled_team_O_mean=pooled_T, earlier_offense_O_reference=offense_T,
                   offense_O_total=_sum(offense, 'opportunities'),
                   defense_O_total=_sum(defense, 'opportunities'),
                   team_volume_pseudo_games=4)
    player = query.get('player_id')
    own = history.rows(cutoff, player=player) if isinstance(player, str) and player else []
    support.update(own_games=len(own), own_game_ids=[r['game_id'] for r in own],
                   latest_own_source=max((r['available'] for r in own), default=None))
    if not own:
        result['fallback_reason'] = 'NO_EARLIER_OWN_QB_HISTORY'
        return result
    teammap = _team_map(history)

    def matched_team(row):
        counterpart = teammap.get((row['game_id'], row['team']))
        if (counterpart is None or counterpart['kickoff'] != row['kickoff'] or
                counterpart['available'] != row['available'] or counterpart['available'] >= cutoff):
            raise SupportError('INCOMPATIBLE_PRIOR_QB_TEAM_IDENTITY_OR_CLOCK')
        a, t = row['counts']['credited_attempts'], counterpart['counts']['opportunities']
        if a < 0 or a > t:
            raise SupportError('PRIOR_QB_ATT_OUTSIDE_TEAM_OPPORTUNITIES')
        return counterpart
    try:
        paired = [(r, matched_team(r)) for r in own]
        # Pool over the same conditional QB-game universe, with each QB row's
        # actual team opportunity denominator retained (including backups).
        pooled_qb = [r for r in history.qb_rows if r['available'] < cutoff]
        pool_pairs = [(r, matched_team(r)) for r in pooled_qb]
        pool_A = _sum(pooled_qb, 'credited_attempts')
        pool_QBT = math.fsum(t['counts']['opportunities'] for _, t in pool_pairs)
        pool_team_ATT = math.fsum(t['counts']['credited_attempts'] for _, t in pool_pairs)
        if pool_QBT <= 0 or pool_team_ATT <= 0:
            raise SupportError('ZERO_POOLED_QB_DENOMINATOR')
        pool_fraction, pool_share = pool_A / pool_QBT, pool_A / pool_team_ATT
        own_A = _sum(own, 'credited_attempts')
        own_T = math.fsum(t['counts']['opportunities'] for _, t in paired)
        own_team_ATT = math.fsum(t['counts']['credited_attempts'] for _, t in paired)
        own_fraction = (own_A + 100 * pool_fraction) / (own_T + 100)
        own_share = (own_A + 100 * pool_share) / (own_team_ATT + 100)
        pooled_team_T = _sum(prior, 'opportunities')
        pooled_team_ATT = _sum(prior, 'credited_attempts')
        team_rate = pooled_team_ATT / pooled_team_T
        offense_rate = (_sum(offense, 'credited_attempts') + 100 * team_rate) / (_sum(offense, 'opportunities') + 100)
        last, last_team = paired[-1]
        last_A, last_team_A = last['counts']['credited_attempts'], last_team['counts']['credited_attempts']
        if last_team_A <= 0 or not 0 <= last_A <= last_team_A:
            raise SupportError('INVALID_LATEST_QB_TEAM_ATT_DENOMINATOR')
        latest_share = (last_A + .5) / (last_team_A + 1.)
        share_x = [1., _logit(offense_rate) - _logit(team_rate), 0.,
                   _logit(latest_share) - _logit(own_share)]
        offset = _logit(own_fraction)
        support.update(pooled_QB_A=pool_A, pooled_QB_game_team_O=pool_QBT,
                       pooled_QB_game_team_ATT=pool_team_ATT, pooled_QB_fraction=pool_fraction,
                       pooled_QB_team_ATT_share=pool_share, own_A=own_A, own_game_team_O=own_T,
                       own_game_team_ATT=own_team_ATT, own_fraction=own_fraction, own_share=own_share,
                       pooled_team_ATT=pooled_team_ATT, pooled_team_O=pooled_team_T,
                       offense_ATT_per_O=offense_rate, latest_QB_A=last_A,
                       latest_game_team_ATT=last_team_A, latest_game_id=last['game_id'],
                       latest_game_team=last['team'], latest_share_raw=last_A / last_team_A,
                       latest_share_Jeffreys=latest_share, share_pseudo_opportunities=100)
        result.update(share_x=share_x, share_offset=offset, share_eligible=True,
                      eligible=True, fallback_reason=None)
    except SupportError as exc:
        result['fallback_reason'] = str(exc)
    return result


def build_share_matrix(designs, exposure):
    """Conditional training only; query inference integrates unknown exposure."""
    n = np.asarray(exposure, dtype=float)
    if len(designs) != len(n) or np.any(~np.isfinite(n)) or np.any(n < 0):
        raise ValueError('Invalid conditional opportunity exposures')
    x = np.asarray([d['share_x'] for d in designs], dtype=float)
    ref = np.asarray([d['T_reference'] for d in designs], dtype=float)
    if x.shape != (len(n), 4) or np.any(ref <= 0):
        raise ValueError('Invalid share design')
    x[:, 2] = np.log(np.where(n > 0, n, ref) / ref)
    return x


def _arrays(x, offset, y, width):
    x, y = np.asarray(x, float), np.asarray(y, float)
    offset = np.broadcast_to(np.asarray(offset, float), y.shape).copy()
    if (x.shape != (len(y), width) or y.ndim != 1 or not len(y) or
            not np.isfinite(x).all() or not np.isfinite(y).all() or
            not np.isfinite(offset).all() or np.any(y < 0) or np.any(y != np.floor(y))):
        raise ValueError('Invalid fitted count design')
    return x, offset, y


def team_objective(theta, x, offset, y):
    """Penalized NB NLL and exact analytic gradient; no fitting side effects."""
    beta, eta = np.asarray(theta[:-1], float), float(theta[-1])
    s = special.expit(eta); shape = .5 + 199.5 * s
    logmu = offset + x @ beta
    logden = np.logaddexp(math.log(shape), logmu)
    ll = (special.gammaln(y + shape) - special.gammaln(shape) - special.gammaln(y + 1) +
          shape * (math.log(shape) - logden) + y * (logmu - logden))
    penalty = np.array([1., 10., 10.])
    value = -float(ll.sum()) + .5 * float(penalty @ (beta * beta)) + .5 * (eta - INITIAL_ETA) ** 2
    dmu = (shape + y) * special.expit(logmu - math.log(shape)) - y
    dr = (-special.digamma(y + shape) + special.digamma(shape) - math.log(shape) - 1 +
          logden + (shape + y) * np.exp(-logden))
    gradient = np.r_[x.T @ dmu + penalty * beta,
                     float(dr.sum()) * 199.5 * s * (1 - s) + eta - INITIAL_ETA]
    return value, gradient


def share_objective(beta, x, offset, n, y):
    eta = offset + x @ beta
    penalty = np.array([1., 10., 10., 10.])
    value = float(np.sum(n * np.logaddexp(0., eta) - y * eta) + .5 * penalty @ (beta * beta))
    gradient = x.T @ (n * special.expit(eta) - y) + penalty * beta
    return value, gradient


def _metadata(fit, initial_value, final_value, rows):
    return dict(success=bool(fit.success), status=int(fit.status), message=str(fit.message),
                iterations=int(fit.nit), function_evaluations=int(fit.nfev),
                gradient_evaluations=int(getattr(fit, 'njev', 0)), rows=int(rows),
                initial_penalized_objective=float(initial_value), final_penalized_objective=float(final_value),
                max_absolute_gradient=float(np.max(np.abs(fit.jac))),
                finite=bool(np.isfinite(fit.x).all() and math.isfinite(final_value)),
                solver='L-BFGS-B', options=dict(OPTIONS), retry=False)


def fit_team(x, offset, y):
    x, offset, y = _arrays(x, offset, y, 3)
    initial = np.r_[np.zeros(3), INITIAL_ETA]
    initial_value = team_objective(initial, x, offset, y)[0]
    fit = optimize.minimize(team_objective, initial, args=(x, offset, y), jac=True,
                            method='L-BFGS-B', options=OPTIONS)
    final = team_objective(fit.x, x, offset, y)[0]
    return dict(kind='opportunity_team_NB_v1', beta=fit.x[:3].tolist(), eta=float(fit.x[3]),
                shape=float(.5 + 199.5 * special.expit(fit.x[3])), feature_order=list(TEAM_FEATURES),
                optimization=_metadata(fit, initial_value, final, len(y)))


def fit_share(x, offset, n, y):
    x, offset, y = _arrays(x, offset, y, 4)
    n = np.asarray(n, float)
    if n.shape != y.shape or np.any(~np.isfinite(n)) or np.any(n != np.floor(n)) or np.any(n < y):
        raise ValueError('QB credited ATT must be within its documented team opportunities')
    initial = np.zeros(4)
    initial_value = share_objective(initial, x, offset, n, y)[0]
    fit = optimize.minimize(share_objective, initial, args=(x, offset, n, y), jac=True,
                            method='L-BFGS-B', options=OPTIONS)
    final = share_objective(fit.x, x, offset, n, y)[0]
    return dict(kind='opportunity_QB_binomial_v1', beta=fit.x.tolist(),
                feature_order=list(SHARE_FEATURES),
                optimization=_metadata(fit, initial_value, final, len(y)))


def restore_team(state):
    if state.get('kind') != 'opportunity_team_NB_v1' or state.get('feature_order') != list(TEAM_FEATURES):
        raise ValueError('Team model schema mismatch')
    beta = np.asarray(state['beta'], float)
    if beta.shape != (3,) or not np.isfinite(beta).all() or not math.isfinite(state['eta']):
        raise ValueError('Invalid team model coefficients')
    shape = .5 + 199.5 * special.expit(state['eta'])
    if abs(shape - state['shape']) > 1e-12:
        raise ValueError('Team shape binding mismatch')
    return beta, float(shape)


def restore_share(state):
    if state.get('kind') != 'opportunity_QB_binomial_v1' or state.get('feature_order') != list(SHARE_FEATURES):
        raise ValueError('Share model schema mismatch')
    beta = np.asarray(state['beta'], float)
    if beta.shape != (4,) or not np.isfinite(beta).all():
        raise ValueError('Invalid share model coefficients')
    return beta


class OpportunityMixture:
    """Infinite-T law integrated with explicit bounded omitted mass/mean.

    Retained T weights are never renormalized. PMFs beyond the retained grid
    raise a numerical support limitation, not a fabricated impossible event.
    """
    def __init__(self, team_mean, team_shape, share_base_logit, volume_slope, T_reference, conversion=1.):
        values = tuple(float(v) for v in (team_mean, team_shape, share_base_logit, volume_slope, T_reference, conversion))
        if not all(map(math.isfinite, values)) or values[0] < 0 or values[1] <= 0 or values[4] <= 0 or not 0 <= values[5] <= 1:
            raise IntegrationError('Invalid opportunity mixture parameters')
        (self.team_mean, self.team_shape, self.share_base_logit, self.volume_slope,
         self.T_reference, self.conversion) = values
        self.p = self.team_shape / (self.team_shape + self.team_mean)
        if not self.team_mean:
            grid = 0
        else:
            first = stats.nbinom.isf(TAIL_TOL, self.team_shape, self.p)
            if not math.isfinite(first) or first > MAX_GRID:
                raise IntegrationError('FROZEN_MAX_TEAM_GRID_EXCEEDED')
            grid = max(1, int(math.ceil(first)))
            while True:
                mass = float(stats.nbinom.sf(grid, self.team_shape, self.p))
                moment = self.team_mean * float(stats.nbinom.sf(grid - 1, self.team_shape + 1, self.p))
                if mass <= TAIL_TOL and moment <= MEAN_TAIL_TOL:
                    break
                grid += max(1, grid // 10)
                if grid > MAX_GRID:
                    raise IntegrationError('FROZEN_MAX_TEAM_GRID_EXCEEDED')
        self.grid_max = grid
        self.t = np.arange(grid + 1)
        self.log_weights = stats.nbinom.logpmf(self.t, self.team_shape, self.p) if self.team_mean else np.array([0.])
        self.weights = np.exp(self.log_weights)
        log_ratio = np.zeros(len(self.t)); positive = self.t > 0
        log_ratio[positive] = np.log(self.t[positive] / self.T_reference)
        self.q = special.expit(self.share_base_logit + self.volume_slope * log_ratio)
        self.theta = self.q * self.conversion
        self.omitted_team_mass = 0. if not self.team_mean else float(stats.nbinom.sf(grid, self.team_shape, self.p))
        self.omitted_mean_bound = 0. if not self.team_mean else self.team_mean * float(stats.nbinom.sf(grid - 1, self.team_shape + 1, self.p))
        self.mean = float(np.sum(self.weights * self.t * self.theta))
        self.retained_mass = float(self.weights.sum())
        self.variance_retained = float(np.sum(self.weights * (self.t * self.theta * (1 - self.theta) + (self.t * self.theta) ** 2)) - self.mean ** 2)

    def cdf(self, x):
        if x == math.inf:
            return 1.
        if x < 0:
            return 0.
        if not math.isfinite(x):
            raise ValueError('Nonfinite CDF argument')
        return float(self.weights @ stats.binom.cdf(math.floor(x), self.t, self.theta))

    def logpmf(self, x):
        if not math.isfinite(x) or x < 0 or x != math.floor(x):
            return -math.inf
        if x > self.grid_max:
            if self.conversion == 0 or self.team_mean == 0:
                return -math.inf
            raise IntegrationError('EVENT_BEYOND_RETAINED_GRID_NOT_A_STRUCTURAL_ZERO')
        return float(special.logsumexp(self.log_weights + stats.binom.logpmf(x, self.t, self.theta)))

    def pmf(self, x):
        value = self.logpmf(x)
        return 0. if value == -math.inf else math.exp(value)

    def quantile(self, probability):
        if not 0 < probability < 1:
            raise ValueError('Open quantile probability required')
        if self.cdf(self.grid_max) < probability:
            raise IntegrationError('QUANTILE_UNRESOLVED_WITHIN_FROZEN_TAIL_BOUND')
        low, high = -1, self.grid_max
        while high - low > 1:
            middle = (low + high) // 2
            if self.cdf(middle) >= probability:
                high = middle
            else:
                low = middle
        return int(high)

    def joint_pmf(self, team_opportunities, attempts, completions):
        t, a, c = team_opportunities, attempts, completions
        if any(not math.isfinite(v) or v < 0 or v != math.floor(v) for v in (t, a, c)) or c > a or a > t:
            return 0.
        q = float(special.expit(self.share_base_logit + self.volume_slope * (math.log(t / self.T_reference) if t else 0.)))
        return float(stats.nbinom.pmf(t, self.team_shape, self.p) * stats.binom.pmf(a, t, q) * stats.binom.pmf(c, a, self.conversion))

    def parameters(self):
        return dict(kind='opportunity_team_binomial_mixture_v1', team_mean=self.team_mean,
                    team_shape=self.team_shape, share_base_logit=self.share_base_logit,
                    volume_slope=self.volume_slope, T_reference=self.T_reference, conversion=self.conversion,
                    grid_max=self.grid_max, omitted_team_mass=self.omitted_team_mass,
                    omitted_mean_bound=self.omitted_mean_bound, tail_tolerance=TAIL_TOL,
                    mean_tail_tolerance=MEAN_TAIL_TOL, renormalized=False,
                    support='INFINITE_TEAM_OPPORTUNITIES; BOUNDED_NUMERICAL_TAIL; C<=A<=T',
                    mean=self.mean)


def mixed_law(team_state, share_state, design, conversion=1.):
    if not design.get('eligible'):
        raise SupportError(design.get('fallback_reason') or 'INELIGIBLE_EARLIER_DESIGN')
    if any(not state['optimization'].get('success') or not state['optimization'].get('finite') for state in (team_state, share_state)):
        raise SupportError('FROZEN_OPTIMIZER_FAILED_USE_FULL_PARENT')
    team_beta, shape = restore_team(team_state)
    share_beta = restore_share(share_state)
    logmean = float(design['team_offset'] + np.asarray(design['team_x']) @ team_beta)
    if logmean > math.log(np.finfo(float).max):
        raise IntegrationError('NONFINITE_PREDICTED_TEAM_MEAN')
    x = np.asarray(design['share_x'], float).copy(); x[2] = 0.
    base = float(design['share_offset'] + x @ share_beta)
    return OpportunityMixture(math.exp(logmean), shape, base, share_beta[2], design['T_reference'], conversion)


def _payload(law):
    if isinstance(law, Law) and law.kind == 'mixture':
        return dict(kind='leaf_mixture', support=law.support.tolist(), weights=law.weights.tolist(),
                    prior=_payload(law.prior), mixture=law.b)
    return law.parameters()


class ThinnedLeafLaw:
    """Exact finite empirical-binomial mixture plus exactly thinned prior."""
    def __init__(self, support, weights, prior, mixture, conversion, source):
        self.support, self.weights = np.asarray(support, float), np.asarray(weights, float)
        self.prior, self.mixture, self.conversion, self.source = prior, float(mixture), float(conversion), source
        if (len(self.support) != len(self.weights) or np.any(self.support < 0) or
                np.any(self.support != np.floor(self.support)) or not np.isfinite(self.support).all() or
                not np.isfinite(self.weights).all() or np.any(self.weights < 0) or
                abs(float(self.weights.sum()) - 1) > 1e-10 or not 0 <= self.mixture <= 1 or not 0 <= self.conversion <= 1):
            raise ValueError('Invalid empirical count-thinning contract')
        self.mean = (1 - self.mixture) * float(self.weights @ self.support) * self.conversion + self.mixture * self.prior.mean

    def cdf(self, x):
        if x < 0:
            return 0.
        return ((1 - self.mixture) * float(self.weights @ stats.binom.cdf(math.floor(x), self.support, self.conversion)) +
                self.mixture * self.prior.cdf(x))

    def logpmf(self, x):
        if not math.isfinite(x) or x < 0 or x != math.floor(x):
            return -math.inf
        logweights = np.full(len(self.weights), -math.inf)
        positive = self.weights > 0
        logweights[positive] = np.log(self.weights[positive])
        empirical = float(special.logsumexp(logweights + stats.binom.logpmf(x, self.support, self.conversion)))
        return float(np.logaddexp(math.log1p(-self.mixture) + empirical if self.mixture < 1 else -math.inf,
                                 math.log(self.mixture) + self.prior.logpmf(x) if self.mixture > 0 else -math.inf))

    def pmf(self, x):
        value = self.logpmf(x)
        return 0. if value == -math.inf else math.exp(value)

    def quantile(self, probability):
        if not 0 < probability < 1:
            raise ValueError('Open quantile probability required')
        low, high = -1, 1
        while self.cdf(high) < probability:
            high = 2 * high + 1
        while high - low > 1:
            middle = (low + high) // 2
            if self.cdf(middle) >= probability:
                high = middle
            else:
                low = middle
        return int(high)

    def parameters(self):
        return dict(kind='exact_binomial_thinned_leaf_v1', source=self.source, conversion=self.conversion)


def thin_law(law, conversion):
    p = float(conversion)
    if not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError('Invalid fixed conversion probability')
    if isinstance(law, Mapping):
        law = restore_law(law)
    if isinstance(law, CountLaw):
        return CountLaw(law.mean * p, law.shape)
    if isinstance(law, OpportunityMixture):
        return OpportunityMixture(law.team_mean, law.team_shape, law.share_base_logit,
                                  law.volume_slope, law.T_reference, law.conversion * p)
    if not isinstance(law, Law):
        raise ValueError('Unsupported source attempt-law type')
    if law.kind == 'zero':
        return Law('zero')
    if law.kind == 'geometric':
        mean = law.mean * p
        return Law('geometric', q=mean / (1 + mean))
    if law.kind == 'poisson':
        return Law('poisson', mean=law.mean * p)
    if law.kind == 'mixture':
        return ThinnedLeafLaw(law.support, law.weights, thin_law(law.prior, p), law.b, p, _payload(law))
    raise ValueError('Attempt thinning requires a qualified nonnegative count law')


def restore_law(payload):
    kind = payload.get('kind')
    if kind == 'gamma_poisson_count':
        return CountLaw(payload['mean'], payload['shape'])
    if kind == 'opportunity_team_binomial_mixture_v1':
        law = OpportunityMixture(*(payload[k] for k in ('team_mean', 'team_shape', 'share_base_logit',
                                                       'volume_slope', 'T_reference', 'conversion')))
        if payload.get('renormalized') is not False or abs(law.mean - payload['mean']) > 1e-10 or law.grid_max != payload['grid_max']:
            raise ValueError('Saved opportunity mixture binding mismatch')
        return law
    if kind == 'exact_binomial_thinned_leaf_v1':
        return thin_law(restore_law(payload['source']), payload['conversion'])
    if kind == 'leaf_mixture':
        prior = restore_law(payload['prior'])
        return Law('mixture', support=payload['support'], weights=payload['weights'],
                   prior=prior, mixture=payload.get('mixture', .05))
    if kind in ('zero', 'geometric', 'poisson'):
        return Law(kind, mean=payload.get('mean'), q=payload.get('q', 0.))
    raise ValueError('Unsupported safe JSON count-law schema: ' + str(kind))
