"""Depth-conditioned FTN history addition; no current-game charting at inference.

FTN Data via nflverse, CC BY-SA 4.0 for charting-derived arrays/models.
Catchability is its own annotation, not a completion or a complement of drops.
"""
import math
import numpy as np
from scipy import optimize, special
from . import player_context_matchup as ctx

VERSION = 'B-QB-DEPTH-CATCHABILITY-v1'
DEPTHS = ('BEHIND_LOS', 'YARDS_0_9', 'YARDS_10_19', 'YARDS_20_PLUS', 'UNKNOWN')


class DepthHistory:
    def __init__(self, rows, chart, window=8, strength=20.):
        self.rows = sorted((r for r in rows if r['physical_participation']),
                           key=lambda r: (r['kickoff'], r['game_id'], r['player_id']))
        self.chart = {(r['game_id'], r['player_id']): r for r in chart}
        if len(self.chart) != len(chart):
            raise ValueError('Duplicate depth-chart identity')
        self.window, self.strength, self.cache = window, strength, {}

    def describe(self, q):
        key = q['player_id'], q['game_id'], q['kickoff']
        if key in self.cache:
            return self.cache[key]
        eligible = [r for r in self.rows if r['available'] < q['kickoff']]
        own = [r for r in eligible if r['player_id'] == q['player_id']][-self.window:]
        def total(rr, flag=None, field=None):
            return np.sum([self.chart[r['game_id'], r['player_id']]['eligible_throws'] if flag is None
                           else self.chart[r['game_id'], r['player_id']]['flags'][flag][field]
                           for r in rr], axis=0) if rr else np.zeros(5)
        n = total(own)
        known = total(own, 'is_catchable_ball', 'known')
        positive = total(own, 'is_catchable_ball', 'positive')
        pool_known = total(eligible, 'is_catchable_ball', 'known')
        pool_positive = total(eligible, 'is_catchable_ball', 'positive')
        baseline = (pool_positive + 1.) / (pool_known + 2.)
        shrunk = (positive + self.strength * baseline) / (known + self.strength)
        age, support = [], []
        for j in range(5):
            observed = [r for r in own if self.chart[r['game_id'], r['player_id']]['flags']['is_catchable_ball']['known'][j] > 0]
            latest = max((r['available'] for r in observed), default=None)
            days = None if latest is None else (q['kickoff'] - latest) / 86400.
            age.append(days)
            support.append([known[j] / n[j] if n[j] else 0., math.log1p(known[j]),
                            math.log1p(days) if days is not None else 0., float(known[j] == 0),
                            float(pool_known[j] == 0)])
        d = dict(eligible_throws=n.tolist(), known=known.tolist(), positive=positive.tolist(),
                 pooled_known=pool_known.tolist(), pooled_positive=pool_positive.tolist(),
                 raw=[positive[j] / known[j] if known[j] else None for j in range(5)],
                 baseline=baseline.tolist(), shrunk=shrunk.tolist(), support=support,
                 source_age_days=age, own_games=len(own),
                 latest_consumed_available=max((r['available'] for r in eligible), default=None),
                 latest_own_game=max((r['kickoff'] for r in own), default=None),
                 fallback='none' if known.sum() else 'earlier_depth_prior_no_own_chart_annotations')
        self.cache[key] = d
        return d

    def direct(self, q, history, values):
        d = self.describe(q)
        extra = list(np.asarray(d['support']).reshape(-1))
        if values:
            extra += list(special.logit(np.asarray(d['shrunk'])))
        return np.r_[history.direct_features(q, 'E1'), extra]


class DepthCompletionModel:
    """Same P1 binomial objective/effects, plus support and optional catchability.

Future contexts are integrated with the existing predicted 25-state mixture;
actual target-game attempts and charted exposures are never inference inputs.
"""
    def __init__(self, values=False, penalty=20.):
        self.values, self.penalty = bool(values), float(penalty)

    def numeric(self, q, history, chart, j):
        d = chart.describe(q)
        extra = list(d['support'][j % 5])
        if self.values:
            extra.append(float(special.logit(d['shrunk'][j % 5])))
        return np.r_[ctx._conditional_x(history.describe(q), j), extra]

    def fit(self, rows, history, chart):
        self.levels = {k: sorted({r[k] for r in rows}) for k in ('team', 'opponent')}
        self.width = 29 + 5 + int(self.values)
        offset = self.width
        self.columns = {}
        for field, levels in self.levels.items():
            self.columns[field] = {v: offset + i for i, v in enumerate(levels)}
            offset += len(levels)
        xx, aa, cc = [], [], []
        for r in rows:
            for j, (n, c) in enumerate(zip(r['context_attempts'], r['context_completions'])):
                if not n:
                    continue
                x = np.zeros(offset)
                x[:self.width] = self.numeric(r, history, chart, j)
                for field, levels in self.columns.items():
                    x[levels[r[field]]] = 1.
                xx.append(x); aa.append(n); cc.append(c)
        x, n, y = np.asarray(xx), np.asarray(aa), np.asarray(cc)
        penalty = np.full(offset, self.penalty)
        penalty[:25] = 2.; penalty[25:self.width] = 10.
        def objective(beta):
            eta = x @ beta
            return (float(np.sum(n * np.logaddexp(0., eta) - y * eta) + .5 * np.dot(penalty * beta, beta)),
                    x.T @ (n * special.expit(eta) - y) + penalty * beta)
        fit = optimize.minimize(objective, np.zeros(offset), jac=True, method='L-BFGS-B',
                                options=dict(maxiter=120, ftol=1e-10, gtol=1e-6))
        self.beta = fit.x
        self.optimization = dict(success=bool(fit.success), iterations=int(fit.nit),
                                 message=str(fit.message), finite=bool(np.isfinite(fit.x).all()),
                                 training_context_rows=len(n), training_attempts=int(n.sum()))
        if not self.optimization['finite']:
            raise ValueError('Nonfinite depth completion model')
        return self

    def probabilities(self, q, history, chart):
        out = []
        for j in range(25):
            x = np.zeros(len(self.beta)); x[:self.width] = self.numeric(q, history, chart, j)
            for field, levels in self.columns.items():
                i = levels.get(q[field])
                if i is not None:
                    x[i] = 1.
            out.append(float(special.expit(x @ self.beta)))
        return np.asarray(out)

    def payload(self):
        return dict(kind='depth_catchability_conditional_binomial_v1', values=self.values,
                    penalty=self.penalty, levels=self.levels, beta=self.beta.tolist(),
                    optimization=self.optimization, depth_order=list(DEPTHS),
                    coefficient_group_order=['team', 'opponent'])

    @classmethod
    def restore(cls, payload):
        if payload['kind'] != 'depth_catchability_conditional_binomial_v1' or payload['depth_order'] != list(DEPTHS):
            raise ValueError('Depth model contract')
        m = cls(payload['values'], payload['penalty']); m.width = 34 + int(m.values)
        if set(payload['levels']) != {'team', 'opponent'} or payload['coefficient_group_order'] != ['team', 'opponent']:
            raise ValueError('Named coefficient-group order')
        m.levels = payload['levels']; m.columns = {}; offset = m.width
        for field in payload['coefficient_group_order']:
            levels = m.levels[field]
            if len(set(levels)) != len(levels):
                raise ValueError('Duplicate coefficient identity')
            m.columns[field] = {v: offset + i for i, v in enumerate(levels)}; offset += len(levels)
        m.beta = np.asarray(payload['beta'], float); m.optimization = payload['optimization']
        if m.beta.shape != (offset,) or not np.isfinite(m.beta).all():
            raise ValueError('Depth coefficient shape/finite')
        return m
