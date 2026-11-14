"""Scoped admission holds; failed forecasts remain in the immutable score audit.

These controls do not turn missingness, a zero prediction or a losing method
into a software defect. Each hold names a demonstrated exact procedure/target.
"""

HGB_CARRY_HOLD = 'B-AUDIT-C-F1-ORIGINAL-HGB-L1-CARRY-v1'
_ORIGINAL_L1 = (
    'hgb-direct-history-controls-v1:absolute_error_point',
    'v2-hgb-direct-history-controls-v1:absolute_error_point',
)
_ORIGINAL_SOURCE = 'reports/continuation-20261029/hgb-history-v1/SCORES.json'
_FIXED_AVAILABILITY_L1 = 'v2-availability-abc-shadow-v1:hgb_direct:absolute_error_point'
_FAILED_CARRY_MODELS = frozenset({
    '4333f846a06ff945536379969920ce16ae00086df0e9922a0a9dc58290c29b53',
    '24027cd7da3d84cf16f8c2f42f3012d79e44572208ba41ee708cbc9784976360',
    'b9e7ec24ce3fd672bed9bed7d2d80ea00a303ba39dd8211004cb596f2e30dc9a',
})


def recommendation_hold(row):
    """Return a specific hold, not a universal qualification/readiness decision.

    Do not match comparator IDs: a repaired procedure may legitimately retain
    the collapsed original as its losing comparator. History/output aliases do
    not rehabilitate that original procedure; separately named repairs survive.
    """
    source = row.get('source_aggregate_fields') or {}
    target = row.get('category') or row.get('target') or source.get('category') or source.get('target')
    if target != 'rush_att':
        return None
    for layer in (row, source):
        for key in ('model_sha256', 'model_version', 'model_artifact_id',
                    'fixed_model_artifact_id', 'base_model_sha256'):
            model = layer.get(key) or ''
            if isinstance(model, str) and model.removeprefix('MODEL-') in _FAILED_CARRY_MODELS:
                return HGB_CARRY_HOLD
        for key in ('procedure_id', 'actual_procedure', 'forecast_procedure_id', 'base_procedure_id'):
            name = layer.get(key) or ''
            if name.startswith('B::'):
                name = name[3:]
            elif name.startswith('B:'):
                name = name[2:]
            if any(name == p or name.startswith(p + ':') for p in _ORIGINAL_L1):
                return HGB_CARRY_HOLD
            # This exact frozen experiment's A/B arms reuse the three models
            # above. Its normalized grade projection omitted their hashes.
            # The separately refitted C arm has different model identities.
            arm = row.get('availability_arm') or source.get('availability_arm')
            information = row.get('information_policy') or source.get('information_policy')
            if arm is None and information in ('AVAILABILITY-A', 'AVAILABILITY-B'):
                arm = information[-1]
            if (name == _FIXED_AVAILABILITY_L1 or
                    name.startswith(_FIXED_AVAILABILITY_L1 + ':')) and arm in ('A', 'B'):
                return HGB_CARRY_HOLD
    artifact = row.get('source_artifact') or source.get('source_artifact')
    objective = source.get('objective') or row.get('objective')
    if artifact == _ORIGINAL_SOURCE and objective == 'absolute_error_point':
        return HGB_CARRY_HOLD
    return None
