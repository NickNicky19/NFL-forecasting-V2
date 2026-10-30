"""Explicit matched-comparison fields for the public result projection.

An absent paired comparison is unknown. Equal sample counts alone never
authenticate matching rows, vintages, cutoffs or products.
"""
from __future__ import annotations

import math


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def error_change(candidate, comparator):
    if not finite(candidate) or not finite(comparator) or min(candidate, comparator) < 0:
        raise ValueError('finite nonnegative paired errors required')
    delta = candidate - comparator
    return dict(absolute_error_change=delta,
                relative_error_change=delta / comparator if comparator else None,
                relative_error_missing_reason=None if comparator else 'zero_comparator_error_denominator')


def comparison_fields(record, annotation=None):
    source = record.get('source_aggregate_fields') or {}
    change_kind = source.get('correction_kind')
    fields = dict(comparison_status='UNESTABLISHED', comparator_procedure_id=None,
                  comparator_history_regime=None, comparator_product_id=None,
                  comparison_metric=None, comparator_error=None, paired_n=None,
                  absolute_error_change=None, relative_error_change=None,
                  relative_error_missing_reason='no_authenticated_matched_comparison',
                  comparison_missing_reason='Retained paired rows and an explicit comparator binding are required.',
                  comparison_membership_sha256=None, comparison_uncertainty=None,
                  prediction_or_scoring_change='scoring_correction' if change_kind else source.get('prediction_change_kind', 'prediction_evaluation'),
                  cutoff=source.get('cutoff', source.get('feature_cutoff_policy')),
                  cutoff_status='source_declared' if source.get('cutoff', source.get('feature_cutoff_policy')) else 'inspect_frozen_source_protocol',
                  fallback_rate=None, fallback_rate_denominator=None,
                  live_website_comparison_status='UNESTABLISHED',
                  live_website_comparison_missing_reason='No matching archived website forecast, label and horizon binding for this view.')
    if record.get('kind') == 'software_verification':
        fields.update(comparison_status='NOT_APPLICABLE_SOFTWARE', prediction_or_scoring_change='software_verification',
                      comparison_missing_reason='Software fixtures have no NFL forecast error comparison.')
        return fields
    fallback = record.get('fallback_rows')
    denominator = record.get('forecast_or_offered_rows')
    if fallback is not None and denominator and 0 <= fallback <= denominator:
        fields.update(fallback_rate=fallback / denominator, fallback_rate_denominator=denominator)
    annotation = annotation or record.get('reporting_comparison') or source.get('comparison')
    if not annotation:
        return fields
    if annotation.get('status') == 'UNESTABLISHED':
        fields['comparison_missing_reason'] = annotation.get('reason', annotation.get('missing_reason', fields['comparison_missing_reason']))
        return fields
    if annotation.get('status') != 'PAIRED_RETAINED_ROWS':
        raise ValueError('comparison requires an explicit retained-row binding')
    if not annotation.get('membership_sha256') or not annotation.get('comparator_procedure_id'):
        raise ValueError('comparison membership and comparator identity required')
    metric = annotation.get('metric')
    if metric not in {'mae', 'mse', 'rmse', 'brier', 'crps', 'nll', 'log_loss'}:
        raise ValueError('unsupported comparison metric')
    paired_n = annotation.get('paired_n')
    if not isinstance(paired_n, int) or isinstance(paired_n, bool) or paired_n <= 0:
        raise ValueError('positive paired denominator required')
    candidate = annotation.get('candidate_error')
    original = (record.get('metrics') or {}).get(metric)
    if paired_n != record.get('n') or not finite(original) or not finite(candidate) or not math.isclose(candidate, original, abs_tol=1e-10, rel_tol=1e-10):
        raise ValueError('comparison is not this exact scored view')
    fields.update(comparison_status='PAIRED_RETAINED_ROWS',
                  comparator_procedure_id=annotation['comparator_procedure_id'],
                  comparator_history_regime=annotation.get('comparator_history_regime'),
                  comparator_product_id=annotation.get('comparator_product_id'),
                  comparison_metric=metric, comparator_error=annotation['comparator_error'], paired_n=paired_n,
                  comparison_missing_reason=None, comparison_membership_sha256=annotation['membership_sha256'],
                  comparison_uncertainty=annotation.get('uncertainty'),
                  cutoff=annotation.get('cutoff_policy', fields['cutoff']))
    fields.update(error_change(candidate, annotation['comparator_error']))
    if fields['prediction_or_scoring_change'] == 'scoring_correction':
        fields['comparison_status'] = 'SCORING_CORRECTION_NOT_PREDICTIVE_GAIN'
    return fields
