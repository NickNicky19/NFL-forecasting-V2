import unittest
from nfl_v2.hgb_control_guards import OutputViewBudget, expected_output_views


class HGBResourceGuardTests(unittest.TestCase):
    def test_views_do_not_count_binary_as_two_numeric_products(self):
        self.assertEqual(expected_output_views([{'target':'pass_yd'},{'target':'anytime_td'}]),9)

    def test_exact_capacity_and_no_partial_charge_on_rejection(self):
        budget=OutputViewBudget(10)
        budget.reserve(7);budget.reserve(3)
        with self.assertRaises(RuntimeError):budget.reserve(1)
        self.assertEqual(budget.reserved,10)

    def test_abstention_rows_still_consume_capacity(self):
        budget=OutputViewBudget(3)
        budget.reserve(3)  # caller counts queries before identity/prediction success
        with self.assertRaises(RuntimeError):budget.reserve(1)

    def test_invalid_allocations_and_unsupported_targets_fail_closed(self):
        for value in (0,-1,True,1.5):
            with self.assertRaises(ValueError):OutputViewBudget(value)
        with self.assertRaises(ValueError):expected_output_views([{'target':'nick-chart-ppr-v1'}])
        with self.assertRaises(ValueError):OutputViewBudget(5).reserve(-1)


if __name__=='__main__':unittest.main()
