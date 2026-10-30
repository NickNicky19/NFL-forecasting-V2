import unittest
import csv
import io

from nfl_v2.comparison_reporting import comparison_fields, error_change


class ComparisonReportingTests(unittest.TestCase):
    def record(self):
        return dict(kind='forecast_evaluation_view', n=4, metrics={'mae': 3.},
                    fallback_rows=1, forecast_or_offered_rows=5)

    def annotation(self):
        return dict(status='PAIRED_RETAINED_ROWS', membership_sha256='fixture-only',
                    comparator_procedure_id='fictional-control', metric='mae',
                    candidate_error=3., comparator_error=4., paired_n=4)

    def test_signed_change_and_explicit_fallback_denominator(self):
        out = comparison_fields(self.record(), self.annotation())
        self.assertEqual(out['absolute_error_change'], -1.)
        self.assertEqual(out['relative_error_change'], -.25)
        self.assertEqual(out['fallback_rate'], .2)
        self.assertEqual(out['fallback_rate_denominator'], 5)

    def test_no_pairing_inferred_from_equal_sample_counts(self):
        self.assertEqual(comparison_fields(self.record())['comparison_status'], 'UNESTABLISHED')
        self.assertEqual(comparison_fields(self.record(), {'status':'UNESTABLISHED','reason':'no_supported_labels'})['comparison_missing_reason'], 'no_supported_labels')
        for update in ({'membership_sha256': None}, {'paired_n': 3}, {'candidate_error': 1.}):
            with self.assertRaises(ValueError):
                comparison_fields(self.record(), dict(self.annotation(), **update))

    def test_zero_control_keeps_absolute_change_without_relative_invention(self):
        out = error_change(2., 0.)
        self.assertEqual(out['absolute_error_change'], 2.)
        self.assertIsNone(out['relative_error_change'])

    def test_correction_is_not_prediction_change(self):
        row = self.record()
        row['source_aggregate_fields'] = {'correction_kind': 'exact_grid_precision'}
        out = comparison_fields(row, self.annotation())
        self.assertEqual(out['comparison_status'], 'SCORING_CORRECTION_NOT_PREDICTIVE_GAIN')
        row['source_aggregate_fields'] = {'prediction_change_kind': 'new_refit_predictions'}
        self.assertEqual(comparison_fields(row, self.annotation())['prediction_or_scoring_change'], 'new_refit_predictions')

    def test_infinite_or_negative_error_never_becomes_relative_skill(self):
        for pair in ((float('inf'), 1.), (1., float('nan')), (-1., 2.)):
            with self.assertRaises(ValueError):
                error_change(*pair)

    def test_paired_unpaired_and_software_csv_columns_are_stable(self):
        rows=[comparison_fields(self.record()),comparison_fields(self.record(),self.annotation()),
              comparison_fields({'kind':'software_verification'})]
        target=io.StringIO();writer=csv.DictWriter(target,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(target.getvalue())))),3)
