"""Optimizer-only amendment: same declared likelihood/features, fixed600limit.

The unscored120iteration pilot is retained and excluded; no NFL evaluation
score selected this numerical allowance. FTN-derived parameters CC BY-SA4.
"""
import numpy as np
from scipy import optimize, special
from .qb_depth_catchability import DepthHistory, DepthCompletionModel, DEPTHS
VERSION = 'B-QB-DEPTH-CATCHABILITY-v2'

class ConvergedDepthCompletionModel(DepthCompletionModel):
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
                                options=dict(maxiter=600, ftol=1e-10, gtol=1e-6))
        self.beta = fit.x
        self.optimization = dict(success=bool(fit.success), iterations=int(fit.nit),
                                 message=str(fit.message), finite=bool(np.isfinite(fit.x).all()),
                                 training_context_rows=len(n), training_attempts=int(n.sum()))
        if not self.optimization['finite']:
            raise ValueError('Nonfinite depth completion model')
        return self
