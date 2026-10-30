import unittest
from nfl_v2.precision_grid import chart_median_precision,coordinate


class ChartGridPrecisionTests(unittest.TestCase):
    def test_exact_inclusive_and_strict_boundaries_despite_binary_float(self):
        self.assertGreater(abs(4.8-9.8),5)
        r=chart_median_precision([4.8,.02,-1.1],[9.8,1.02,-.1],product_id='lower_median')
        self.assertEqual(r['abs_le_5']['numerator'],3)
        self.assertEqual(r['abs_lt_5']['numerator'],2)
        self.assertEqual(r['abs_le_1']['numerator'],2)
        self.assertEqual(r['abs_lt_1']['numerator'],0)

    def test_mean_and_off_grid_values_never_rounded(self):
        with self.assertRaises(ValueError):chart_median_precision([1.],[1.],product_id='mean')
        for v in [1/3,None,float('nan'),float('inf'),True]:
            with self.assertRaises(ValueError):coordinate(v)

    def test_signed_grid_and_empty_denominator(self):
        self.assertEqual(coordinate(-.02),-1)
        r=chart_median_precision([],[],product_id='lower_median')
        self.assertIsNone(r['abs_le_1']['rate'])
