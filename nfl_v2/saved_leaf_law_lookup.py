"""Restore a retained discrete law by histogram lookup, without estimator calls."""
from __future__ import annotations
import math
import numpy as np
from .distribution_laws import Law


def from_payload(params):
    values=dict(params)
    if values['kind']=='mixture':values['prior']=from_payload(values['prior'])
    return Law(**values)


def lookup(support,histograms,leaf_ids,prior_parameters,*,expected_trees=32,mixture=.05):
    if len(histograms)!=expected_trees or len(leaf_ids)!=expected_trees:raise ValueError('saved leaf/tree cardinality mismatch')
    support=np.asarray(support,dtype=float)
    if len(support)==0 or not np.isfinite(support).all()or np.any(np.diff(support)<=0):raise ValueError('invalid retained support')
    weights=np.zeros(len(support),dtype=float)
    for matrix,leaf in zip(histograms,leaf_ids):
        if isinstance(leaf,bool)or int(leaf)!=leaf or not 0<=int(leaf)<matrix.shape[0]or matrix.shape[1]!=len(support):raise ValueError('invalid saved leaf id or histogram shape')
        row=matrix[int(leaf)];row=row.toarray()if hasattr(row,'toarray')else np.asarray(row);row=np.asarray(row,dtype=float).ravel()
        if not np.isfinite(row).all()or np.any(row<0)or not math.isclose(float(row.sum()),1.,abs_tol=1e-10):raise ValueError('saved leaf row not a probability distribution')
        weights+=row/expected_trees
    law=Law('mixture',support=support,weights=weights,prior=from_payload(prior_parameters),mixture=mixture)
    payload=dict(kind='mixture',support=law.support.tolist(),weights=law.weights.tolist(),prior=prior_parameters,mixture=mixture)
    return law,payload
