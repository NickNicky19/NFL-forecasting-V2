"""Typed restoration for the retained HGB binary recipe, not a new learner.

Only a newly trained, locally trusted sklearn model is exported. Restoration
reads ordinary JSON and never imports or deserializes a model pickle.
"""
import math

from .hgb_control import FEATURES, PARAMS

VERSION = 'B-HGB-ANYTIME-CURRENT-SHADOW-v1'
RECIPE = 'hgb-direct-history-controls-v1:log_loss_probability'


def export_model(model):
    if list(model.classes_) != [0., 1.]:
        raise ValueError('Binary class orientation')
    trees = []
    for stage in model._predictors:
        if len(stage) != 1:
            raise ValueError('Binary tree contract')
        nodes = []
        for node in stage[0].nodes:
            if node['is_leaf']:
                nodes.append(dict(leaf=True, value=float(node['value'])))
            else:
                if node['is_categorical']:
                    raise ValueError('Unregistered categorical split')
                threshold = float(node['num_threshold'])
                if math.isnan(threshold):
                    raise ValueError('Invalid split')
                nodes.append(dict(leaf=False, feature=int(node['feature_idx']),
                    threshold=threshold if math.isfinite(threshold) else None,
                    threshold_kind='FINITE' if math.isfinite(threshold) else 'POS_INF' if threshold > 0 else 'NEG_INF',
                    missing_left=bool(node['missing_go_to_left']), left=int(node['left']), right=int(node['right'])))
        trees.append(nodes)
    return dict(version=VERSION, recipe=RECIPE, feature_order=list(FEATURES), parameters=PARAMS,
        baseline_logit=float(model._baseline_prediction[0, 0]), trees=trees,
        output='RAW_BINARY_EVENT_PROBABILITY_NOT_CALIBRATED_CONFIDENCE', classes=[0, 1])


def restore_probability(payload, features, feature_names):
    if tuple(feature_names) != FEATURES or payload['feature_order'] != list(FEATURES):
        raise ValueError('Named feature order mismatch')
    if len(features) != len(FEATURES) or payload['recipe'] != RECIPE:
        raise ValueError('Feature/recipe contract')
    score = payload['baseline_logit']
    for tree in payload['trees']:
        index = 0
        for _ in range(len(tree)):
            node = tree[index]
            if node['leaf']:
                score += node['value']
                break
            value = features[node['feature']]
            if value is None or math.isnan(float(value)):
                go_left = node['missing_left']
            else:
                if not math.isfinite(float(value)):
                    raise ValueError('Nonfinite supplied feature')
                threshold = node['threshold'] if node['threshold_kind'] == 'FINITE' else math.inf if node['threshold_kind'] == 'POS_INF' else -math.inf
                go_left = float(value) <= threshold
            index = node['left'] if go_left else node['right']
        else:
            raise ValueError('Invalid cyclic tree')
    probability = 1 / (1 + math.exp(-score)) if score >= 0 else math.exp(score) / (1 + math.exp(score))
    if not 0 <= probability <= 1:
        raise ValueError('Invalid event probability')
    return probability
