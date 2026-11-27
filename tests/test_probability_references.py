import math
import unittest

from tools.compare_probability_references import auc, loss, reference


class ProbabilityReferenceTests(unittest.TestCase):
    def test_neutral_half_point_and_push_have_different_scores(self):
        p, origin = reference([], 1.5)
        self.assertEqual(origin, "EMPTY_PREFIX_CONSTANT_HALF")
        self.assertEqual(loss(p, "over")[0], .25)
        self.assertEqual(loss(p, "under")[0], .25)
        self.assertEqual(loss(p, "push")[0], .75)
        self.assertTrue(math.isinf(loss(p, "push")[1]))

    def test_exact_signed_threshold_regions_without_smoothing(self):
        p, _ = reference([-3., 0., 1., 1., 4.], 1.)
        self.assertEqual(p, dict(over=.2, under=.4, push=.4))
        p, _ = reference([-3., 0., 1., 1., 4.], 1.5)
        self.assertEqual(p, dict(over=.2, under=.8, push=0.))
        self.assertAlmostEqual(sum(p.values()), 1.)

    def test_auc_ties_and_single_class_do_not_invent_discrimination(self):
        self.assertEqual(auc([(.5, 0), (.5, 1), (.5, 0)]), .5)
        self.assertIsNone(auc([(.2, 0), (.8, 0)]))
        self.assertEqual(auc([(.1, 0), (.8, 1)]), 1.)


if __name__ == "__main__":
    unittest.main()
