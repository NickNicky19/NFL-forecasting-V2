import unittest
from nfl_v2.availability_c_guard import cumulative_preflight
class GuardTests(unittest.TestCase):
    def test_actual_planned_cumulative_bound(self):
        ab=dict(actual_fit_calls=0,output_views=67854,resource=dict(wall_seconds=12,cpu_seconds=13))
        a=dict(max_cumulative_forecast_rows=110000,max_cumulative_active_wall_seconds=900,max_cumulative_active_cpu_seconds=1200)
        self.assertEqual(cumulative_preflight(ab,33927,a),(888,1187))
        with self.assertRaises(ValueError):cumulative_preflight(ab,50000,a)
    def test_exhausted_and_unexpected_ab_fit(self):
        a=dict(max_cumulative_forecast_rows=110000,max_cumulative_active_wall_seconds=900,max_cumulative_active_cpu_seconds=1200)
        with self.assertRaises(ValueError):cumulative_preflight(dict(actual_fit_calls=1),0,a)
        with self.assertRaises(ValueError):cumulative_preflight(dict(actual_fit_calls=0,output_views=0,resource=dict(wall_seconds=901,cpu_seconds=1)),0,a)
