"""Typed output adapter for an already bound B Leaf/D1/D2 origin.

No fitting, source acquisition, calibration, ranking, selection, or persistence.
Callers authenticate the exact model, ordered features, priors and origin first.
This preserves the registered point/fallback calculation; it is not a new law.
"""
from __future__ import annotations

import math
import numpy as np

from .hgb_control import POSITIONS


def point_outputs(*, model, raw_features, feature_columns, fit, queries, priors):
    """Return each valid row's own mean and lower median, never a probability.

    Query actuals are deliberately unused. Eligibility is not inferred from a
    forecast. An operational consumer must separately qualify source freshness,
    current origin, offers, population, rights and owner admission.
    """
    if list(feature_columns) != fit['feature_columns']:
        raise ValueError('ordered feature contract mismatch')
    x = np.asarray(raw_features, dtype=float)
    if x.shape != (len(queries), len(feature_columns)):
        raise ValueError('feature/query dimensions mismatch')
    if model is not None:
        if model.family != 'ordered_leaf_cdf' or model.target != fit['target']:
            raise ValueError('model output contract mismatch')
        if len(model.design.median) != x.shape[1]:
            raise ValueError('model feature dimensions mismatch')
    admitted = []
    out = [None] * len(queries)
    for i, q in enumerate(queries):
        if q['target'] != fit['target']:
            raise ValueError('query target mismatch')
        if q.get('blocked_reason') or q.get('position') not in POSITIONS:
            out[i] = dict(mean=None, lower_median=None, fallback=None,
                          status='UNAVAILABLE_BLOCKED_QUERY')
            continue
        cutoff = q['cutoff']
        if not isinstance(cutoff, (int, float)) or not math.isfinite(cutoff):
            raise ValueError('finite query cutoff required')
        for k in ('latest_training_label_available',
                  'latest_training_consumed_feature_available'):
            t = fit.get(k)
            if t is not None and t >= cutoff:
                raise ValueError('training dependency at/after query cutoff')
        t = q.get('latest_consumed_feature_available')
        if t is not None and t >= cutoff:
            raise ValueError('feature dependency at/after query cutoff')
        if q['position'] not in priors:
            raise ValueError('missing exact same-arm role prior')
        if not math.isfinite(float(x[i, 3])) or x[i, 3] < 0:
            raise ValueError('invalid observed-history support')
        admitted.append(i)
    learned = [i for i in admitted if model is not None and x[i, 3] > 0]
    inferred = dict(zip(learned, model.predict(
        x[learned], [queries[i]['position'] for i in learned], priors))) if learned else {}
    for i in admitted:
        q = queries[i]
        if i in inferred:
            law, detail = inferred[i]
            fallback = 'none'
        else:
            law = priors[q['position']]
            detail = dict(fallback_prior=law.parameters())
            fallback = ('fixed_no_NFL_startup' if not fit['training_n'] else
                        'cold_start_role_prior' if x[i, 3] <= 0 else 'no_model_role_prior')
        out[i] = dict(mean=float(law.mean), lower_median=float(law.quantile(.5)),
                      fallback=fallback, law_reference=detail,
                      status='TYPED_POINT_OUTPUT_NOT_OFFER_ELIGIBILITY')
    return out
