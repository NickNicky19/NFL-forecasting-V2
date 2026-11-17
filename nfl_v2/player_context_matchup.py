"""Versioned QB down/depth inputs, count laws and partial pooling.

These procedures are new retrospective research. They neither replace frozen
forecasts nor authenticate historical source publication or offered quotes.
"""
from __future__ import annotations

import bisect
import collections
import gzip
import json
import math
from pathlib import Path

import numpy as np
from scipy import optimize, special, stats

from . import hgb_control
from .distribution_laws import Law, prior
from .distribution_wave_v2 import Design, FittedLawModel, FOREST

VERSION = 'B-player-context-matchup-01-v1'
FIELD_NAMES = ('ydstogo', 'yardline_100', 'game_seconds_remaining', 'score_differential')
CONTEXTS = 25  # four downs plus UNKNOWN; five depth bins including UNKNOWN


def load_inputs(path):
    rows = json.loads(gzip.decompress(Path(path).read_bytes()))
    seen = set()
    for r in rows:
        key = r['game_id'], r['player_id']
        if key in seen:
            raise ValueError('Repeated QB-game input')
        seen.add(key)
        for field in ('context_attempts', 'context_completions'):
            if len(r[field]) != CONTEXTS:
                raise ValueError('Context width')
        a, c = np.asarray(r['context_attempts']), np.asarray(r['context_completions'])
        if np.any(a < 0) or np.any(c < 0) or np.any(c > a):
            raise ValueError('Invalid context counts')
        if int(a.sum()) != r['attempts'] or int(c.sum()) != r['completions']:
            raise ValueError('Context denominator mismatch')
        if r['available'] <= r['kickoff']:
            raise ValueError('Historical availability must follow the game')
    return sorted(rows, key=lambda r: (r['kickoff'], r['game_id'], r['player_id']))


def _sum(rows, key):
    return np.sum([r[key] for r in rows], axis=0, dtype=float) if rows else np.zeros(CONTEXTS)


def _combine_games(rows, identity):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[r[identity], r['game_id']].append(r)
    result = collections.defaultdict(list)
    for (team, gid), group in groups.items():
        result[team].append(dict(game_id=gid, kickoff=group[0]['kickoff'], available=group[0]['available'],
            context_attempts=_sum(group, 'context_attempts'),
            context_completions=_sum(group, 'context_completions'),
            expected_player_completions=_sum(group, 'expected_player_completions'),
            expected_league_completions=_sum(group, 'expected_league_completions')))
    for group in result.values():
        group.sort(key=lambda r: (r['kickoff'], r['game_id']))
    return result


class ContextHistory:
    def __init__(self, rows, window=8, strength=80.):
        self.all_rows = rows
        self.window = int(window)
        self.strength = float(strength)
        self.rows = sorted([r for r in rows if r.get('physical_participation') and r['target_parity']],
                           key=lambda r: (r['available'], r['kickoff'], r['game_id'], r['player_id']))
        self.times = [r['available'] for r in self.rows]
        self.att = np.vstack([np.zeros(CONTEXTS)] + [np.asarray(r['context_attempts'], float) for r in self.rows]).cumsum(axis=0)
        self.comp = np.vstack([np.zeros(CONTEXTS)] + [np.asarray(r['context_completions'], float) for r in self.rows]).cumsum(axis=0)
        self.players = collections.defaultdict(list)
        for r in self.rows:
            self.players[r['player_id']].append(r)
        for group in self.players.values():
            group.sort(key=lambda r: (r['kickoff'], r['game_id']))
        # Expected offense strength for a prior game is computed at that game's
        # own cutoff. Later outcomes cannot revise this difficulty reference.
        augmented = []
        for r in self.rows:
            a, c = self.global_counts(r['kickoff'])
            pooled = (c + 1.) / (a + 2.)
            own = self.player_rows(r['player_id'], r['kickoff'])
            oa, oc = _sum(own, 'context_attempts'), _sum(own, 'context_completions')
            rate = (oc + self.strength * pooled) / (oa + self.strength)
            augmented.append(dict(r, expected_player_completions=np.asarray(r['context_attempts']) * rate,
                                  expected_league_completions=np.asarray(r['context_attempts']) * pooled))
        self.defenses = _combine_games(augmented, 'opponent')
        self.offenses = _combine_games(augmented, 'team')
        base = [dict(player_id=r['player_id'], position='QB', game_id=r['game_id'],
                     available=r['available'], kickoff=r['kickoff'],
                     values=dict(pass_cmp=r['official_completions'], pass_att=r['official_attempts'])) for r in self.rows]
        self.base_history = hgb_control.FeatureHistory(base)
        self._features = {}

    def global_counts(self, cutoff):
        i = bisect.bisect_left(self.times, cutoff)
        return self.att[i], self.comp[i]

    def eligible(self, cutoff, floor=None):
        return [r for r in self.rows[:bisect.bisect_left(self.times, cutoff)]
                if floor is None or r['season'] >= floor]

    def player_rows(self, player_id, cutoff):
        admitted = [r for r in self.players.get(player_id, ()) if r['available'] < cutoff]
        return admitted[-self.window:]  # game-time order after admission

    def group_rows(self, identity, cutoff, defense):
        source = self.defenses if defense else self.offenses
        return [r for r in source.get(identity, ()) if r['available'] < cutoff][-16:]

    def describe(self, query):
        key = query['player_id'], query['game_id'], query['kickoff'], query['team'], query['opponent']
        if key in self._features:
            return self._features[key]
        cutoff = query['kickoff']
        a, c = self.global_counts(cutoff)
        pooled = (c + 1.) / (a + 2.)
        own = self.player_rows(query['player_id'], cutoff)
        oa, oc = _sum(own, 'context_attempts'), _sum(own, 'context_completions')
        league_mix = (a + 1.) / (a.sum() + CONTEXTS)
        mix = (oa + 20. * league_mix) / (oa.sum() + 20.)
        own_rates = (oc + self.strength * pooled) / (oa + self.strength)
        defense = self.group_rows(query['opponent'], cutoff, True)
        da, dc = _sum(defense, 'context_attempts'), _sum(defense, 'context_completions')
        expected = _sum(defense, 'expected_player_completions')
        residual = (dc - expected) / (da + 100.)
        total_residual = float((dc.sum() - expected.sum()) / (da.sum() + 100.))
        offense = self.group_rows(query['team'], cutoff, False)
        ta, tc = _sum(offense, 'context_attempts'), _sum(offense, 'context_completions')
        te = _sum(offense, 'expected_league_completions')
        team_residual = float((tc.sum() - te.sum()) / (ta.sum() + 100.))
        scalars = []
        for name in FIELD_NAMES:
            available = [(r['field_context'][name]['mean'], r['field_context'][name]['n']) for r in own
                         if r['field_context'][name]['mean'] is not None]
            n = sum(n for _, n in available)
            scalars.append(sum(v * n for v, n in available) / n if n else math.nan)
        ages = [(cutoff-r['kickoff'])/86400 for r in own]
        info = dict(mix=mix, pooled=pooled, own_rate=own_rates, own_context_n=oa,
                    opponent_residual=residual, opponent_residual_main=total_residual,
                    opponent_context_n=da, team_residual=team_residual,
                    opponent_games=len(defense), own_games=len(own), own_attempts=float(oa.sum()),
                    own_completions=float(oc.sum()), field_scalars=scalars,
                    last_prior_game=None if not own else own[-1]['game_id'],
                    latest_source_available=self.times[bisect.bisect_left(self.times,cutoff)-1]
                    if bisect.bisect_left(self.times,cutoff) else None,
                    latest_own_game_age_days=None if not ages else min(ages),
                    latest_own_source_age_days=None if not own else (cutoff-own[-1]['available'])/86400,
                    fallback='none' if own else 'no_player_history_role_prior')
        self._features[key] = info
        return info

    def direct_features(self, query, arm):
        base, _ = self.base_history.get(query['player_id'], 'QB', 'pass_cmp', query['kickoff'])
        if arm == 'E0':
            return np.asarray(base, float)
        d = self.describe(query)
        x = list(base) + list(d['mix']) + list(d['own_rate']) + list(np.log1p(d['own_context_n']))
        x += [d['own_games'], d['own_attempts'], d['latest_own_game_age_days'] or math.nan] + d['field_scalars']
        if arm in ('E2', 'E3'):
            x += list(d['opponent_residual']) + list(np.log1p(d['opponent_context_n']))
            x += [d['opponent_residual_main'], d['opponent_games']]
        if arm == 'E3':
            x += list(d['mix'] * d['opponent_residual'])
        return np.asarray(x, float)

    def exposure(self, query):
        own = self.player_rows(query['player_id'], query['kickoff'])
        earlier = self.eligible(query['kickoff'], query['season']-1)
        values = np.asarray([r['official_attempts'] for r in earlier], float)
        if not len(values):
            return None
        global_mean = float(values.mean())
        y = np.asarray([r['official_attempts'] for r in own], float)
        mu = float((y.sum()+4*global_mean)/(len(y)+4))
        variance = float(((y*y).sum()+4*np.mean(values*values))/(len(y)+4)-mu*mu)
        shape = min(200., max(.5, mu*mu/max(.01, variance-mu))) if mu else 200.
        return CountLaw(mu, shape)


class CountLaw:
    """Explicit gamma-Poisson count law; not a Poisson-objective inference."""
    def __init__(self, mean, shape):
        self.mean, self.shape = float(mean), float(shape)
        if not math.isfinite(self.mean) or self.mean < 0 or not math.isfinite(self.shape) or self.shape <= 0:
            raise ValueError('Invalid gamma-Poisson parameters')
        self.p = self.shape/(self.shape+self.mean)

    def cdf(self, x):
        return float(x >= 0) if not self.mean else float(stats.nbinom.cdf(math.floor(x), self.shape, self.p))

    def pmf(self, x):
        return float(x == 0) if not self.mean else float(stats.nbinom.pmf(x, self.shape, self.p))

    def logpmf(self, x):
        return (0. if x == 0 else -math.inf) if not self.mean else float(stats.nbinom.logpmf(x, self.shape, self.p))

    def quantile(self, p):
        return 0 if not self.mean else int(stats.nbinom.ppf(p, self.shape, self.p))

    def parameters(self):
        return dict(kind='gamma_poisson_count', mean=self.mean, shape=self.shape,
                    conditioning='physical-participation panel; not bookmaker nonvoid')


def exact_probabilities(law, line):
    if not math.isfinite(float(line)):
        raise ValueError('Nonfinite threshold')
    k = math.floor(float(line))
    if float(line) == k:
        under, at_or_below = law.cdf(k-1), law.cdf(k)
    else:
        under = at_or_below = law.cdf(k)
    return dict(over=1.-at_or_below, under=under, push=at_or_below-under)


def _conditional_x(description, context):
    x = np.zeros(25+4)
    x[context] = 1.
    a, c = description['own_attempts'], description['own_completions']
    x[25] = math.log((c+1)/(a-c+1))
    x[26] = description['opponent_residual_main']
    x[27] = description['opponent_residual'][context]
    x[28] = description['team_residual']
    return x


class CompletionModel:
    """Shared or penalized player/team/defense conditional binomial model."""
    def __init__(self, personalized=False, penalty=80.):
        self.personalized, self.penalty = bool(personalized), float(penalty)

    def fit(self, rows, history):
        self.levels = {k:sorted({r[k] for r in rows}) for k in ('team','opponent')}
        if self.personalized:
            self.levels['player_id'] = sorted({r['player_id'] for r in rows})
        offset = 29
        self.columns = {}
        for field, levels in self.levels.items():
            self.columns[field] = {v:offset+i for i,v in enumerate(levels)}
            offset += len(levels)
        xx, aa, cc = [], [], []
        for r in rows:
            d = history.describe(r)
            for context, (n,c) in enumerate(zip(r['context_attempts'], r['context_completions'])):
                if not n:
                    continue
                x = np.zeros(offset)
                x[:29] = _conditional_x(d,context)
                for field, levels in self.columns.items():
                    x[levels[r[field]]] = 1.
                xx.append(x);aa.append(n);cc.append(c)
        if not aa:
            return None
        x, n, y = np.asarray(xx), np.asarray(aa), np.asarray(cc)
        penalty = np.full(offset, self.penalty)
        penalty[:25] = 2.  # weak, zero-centered context coefficients
        penalty[25:29] = 10.
        def objective(beta):
            eta=x@beta
            loss=float(np.sum(n*np.logaddexp(0.,eta)-y*eta)+.5*np.dot(penalty*beta,beta))
            gradient=x.T@(n*special.expit(eta)-y)+penalty*beta
            return loss,gradient
        fit=optimize.minimize(objective,np.zeros(offset),jac=True,method='L-BFGS-B',
                              options=dict(maxiter=120,ftol=1e-10,gtol=1e-6))
        self.beta=fit.x
        self.optimization=dict(success=bool(fit.success),iterations=int(fit.nit),message=str(fit.message),
                               finite=bool(np.isfinite(fit.x).all()),training_context_rows=len(n),
                               training_attempts=int(n.sum()))
        if not self.optimization['finite']:
            raise ValueError('Nonfinite fitted completion coefficients')
        return self

    def probabilities(self, query, history):
        d=history.describe(query)
        out=[]
        for context in range(CONTEXTS):
            x=np.zeros(len(self.beta));x[:29]=_conditional_x(d,context)
            for field,levels in self.columns.items():
                index=levels.get(query[field])
                if index is not None:x[index]=1.
            out.append(float(special.expit(x@self.beta)))
        return np.asarray(out)

    def payload(self):
        return dict(kind='conditional_binomial_context_glm',personalized=self.personalized,
                    penalty=self.penalty,levels=self.levels,beta=self.beta.tolist(),
                    optimization=self.optimization)

    @classmethod
    def restore(cls, payload):
        if payload['kind'] != 'conditional_binomial_context_glm':
            raise ValueError('Completion model type')
        result=cls(payload['personalized'],payload['penalty'])
        result.levels=payload['levels'];result.columns={};offset=29
        for field,levels in result.levels.items():
            if field not in ('team','opponent','player_id') or len(levels)!=len(set(levels)):
                raise ValueError('Level identity contract')
            result.columns[field]={v:offset+i for i,v in enumerate(levels)};offset+=len(levels)
        result.beta=np.asarray(payload['beta'],float)
        if result.beta.shape!=(offset,) or not np.isfinite(result.beta).all():
            raise ValueError('Coefficient shape/finite contract')
        result.optimization=payload['optimization']
        return result


def export_forest(model):
    trees=[]
    for estimator,histogram in zip(model.estimator.estimators_,model.hist):
        t=estimator.tree_;coo=histogram.tocoo()
        trees.append(dict(left=t.children_left.tolist(),right=t.children_right.tolist(),
            feature=t.feature.tolist(),threshold=t.threshold.tolist(),
            leaf_histogram=dict(rows=coo.row.tolist(),columns=coo.col.tolist(),values=coo.data.tolist())))
    return dict(kind='typed_ordered_leaf_cdf',forest_config=FOREST,
                design=dict(median=model.design.median.tolist(),mean=model.design.mean.tolist(),scale=model.design.scale.tolist()),
                support=model.support.tolist(),trees=trees)


def restored_forest_law(payload, x, fallback_prior):
    """No pickle deserialization. Restore explicit bounded arrays only."""
    if payload['kind']!='typed_ordered_leaf_cdf' or len(payload['trees'])!=32:
        raise ValueError('Typed forest contract')
    d=payload['design'];median=np.asarray(d['median']);x=np.asarray(x,float)
    if x.shape!=median.shape:
        raise ValueError('Feature order/width')
    design=np.r_[np.where(np.isfinite(x),x,median),~np.isfinite(x)].astype(np.float32)
    support=np.asarray(payload['support'],float);weights=np.zeros(len(support))
    for tree in payload['trees']:
        i=0;visited=0
        while tree['left'][i]!=-1:
            feature=tree['feature'][i]
            if not 0<=feature<len(design):raise ValueError('Tree feature bounds')
            i=tree['left'][i] if design[feature]<=tree['threshold'][i] else tree['right'][i]
            visited+=1
            if visited>8:raise ValueError('Tree depth contract')
        hist=tree['leaf_histogram']
        for row,col,value in zip(hist['rows'],hist['columns'],hist['values']):
            if row==i:weights[col]+=value/32
    return Law('mixture',support=support,weights=weights,prior=fallback_prior,mixture=.05)
