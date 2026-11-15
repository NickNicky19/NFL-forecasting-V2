"""Deterministic, optimizer-free checks for the frozen pass-mix increment."""
import copy
import math
import unittest

import numpy as np
from scipy import special, stats

from nfl_v2 import qb_pass_mix_information as mix
from nfl_v2.player_context_matchup import ContextHistory, CountLaw, exact_probabilities
from nfl_v2.qb_depth_catchability import DepthHistory


def source_row(game="past", player="Q1", kickoff=0., available=10.,
               team="T1", opponent="D1", counts=None):
    counts = [6, 4] + [0] * 23 if counts is None else list(counts)
    completed = [n // 2 for n in counts]
    return dict(game_id=game, player_id=player, season=2025, week=1,
                team=team, opponent=opponent, kickoff=kickoff, available=available,
                physical_participation=True, target_parity=True, position="QB",
                attempts=sum(counts), completions=sum(completed),
                official_attempts=sum(counts), official_completions=sum(completed),
                context_attempts=counts, context_completions=completed,
                field_context={k: dict(mean=None, n=0) for k in
                               ("ydstogo", "yardline_100", "game_seconds_remaining", "score_differential")},
                pass_destination_counts={"left": sum(counts)})


def query(**updates):
    value = dict(game_id="query", player_id="Q1", season=2026, week=1,
                 team="T1", opponent="D1", kickoff=20., position="QB")
    value.update(updates)
    return value


def histories(rows):
    history = ContextHistory(rows, 8, 20.)
    chart = []
    for r in rows:
        depths = np.asarray(r["context_attempts"]).reshape(5, 5).sum(axis=0).tolist()
        chart.append(dict(game_id=r["game_id"], player_id=r["player_id"],
                          eligible_throws=depths,
                          flags={name: dict(known=depths, positive=[0] * 5) for name in
                                 ("is_catchable_ball", "is_drop", "is_contested_ball")}))
    return history, DepthHistory(rows, chart, 8, 20.), mix.PassMixHistory(history)


def conversion_payload():
    width = len(mix.CONVERSION_FEATURE_ORDER)
    return dict(kind="pass_mix_augmented_C2_conversion_v1", version=mix.VERSION,
                values=True, penalty=20., feature_order=list(mix.CONVERSION_FEATURE_ORDER),
                coefficient_group_order=list(mix.GROUP_ORDER),
                levels={"team": ["T1"], "opponent": ["D1"]},
                beta=np.linspace(-.08, .09, width + 2).tolist(),
                optimization=dict(success=True, synthetic_manual_coefficients=True))


def composition_payload(enriched=True):
    order = mix.ENRICHED_MIX_FEATURES if enriched else mix.ORIGINAL_MIX_FEATURES
    return dict(kind="multinomial_context_composition_v1", version=mix.VERSION,
                enriched=enriched, reference_context=24, feature_order=list(order),
                beta=np.linspace(-.1, .12, 24 + len(order)).tolist(),
                optimization=dict(success=True, synthetic_manual_coefficients=True))


class PassMixInformationTests(unittest.TestCase):
    def test_exact_counts_shrinkage_and_prior_game_expected_composition(self):
        # Two QBs in one game count as one team/defense game. Neither has prior
        # information at that game's cutoff, so its expected mix is uniform.
        rows = [source_row(), source_row(player="Q2", counts=[2, 1] + [0] * 23)]
        _, _, profiles = histories(rows)
        d = profiles.describe(query())
        actual = np.asarray([8., 5.] + [0.] * 23)
        league = (actual + 1.) / 38.
        qb_static = (np.asarray([6., 4.] + [0.] * 23) + 20 * league) / 30.
        team_shrunk = (actual + 20 * league) / 33.
        expected = np.full(25, 13. / 25.)
        np.testing.assert_allclose(d["league_mix"], league, rtol=0, atol=1e-15)
        np.testing.assert_allclose(d["base_mix"], qb_static, rtol=0, atol=1e-15)
        np.testing.assert_array_equal(d["team_counts"], actual)
        np.testing.assert_allclose(d["opponent_expected"], expected, rtol=0, atol=1e-15)
        np.testing.assert_allclose(d["team_logratio"], np.log(team_shrunk / qb_static), atol=1e-15)
        np.testing.assert_allclose(d["opponent_logratio"],
                                   np.log((actual + 100 * league) / (expected + 100 * league)), atol=1e-15)
        self.assertEqual(d["team_trace"]["games"], 1)
        self.assertEqual(len(d["opponent_expectation_bindings"][0]["components"]), 2)
        self.assertTrue(all(c["latest_expected_source"] is None
                            for c in d["opponent_expectation_bindings"][0]["components"]))

    def test_known_zero_and_no_history_are_distinct(self):
        _, _, profiles = histories([source_row()])
        observed = profiles.describe(query())
        self.assertEqual(observed["team_counts"][2], 0.)
        self.assertEqual(observed["team_trace"]["status"], "OBSERVED_HISTORY_SHRUNK")
        absent = profiles.describe(query(player_id="UNSEEN", team="UNSEEN", opponent="UNSEEN"))
        self.assertEqual(absent["team_trace"]["status"], "ABSENT_HISTORY_PRIOR_ONLY")
        self.assertEqual(absent["fallback"]["team"], "LEAGUE_PRIOR_ONLY")
        self.assertIsNone(absent["team_trace"]["latest_source_available"])
        np.testing.assert_allclose(absent["team_logratio"], 0., atol=1e-15)
        np.testing.assert_allclose(absent["opponent_logratio"], 0., atol=1e-15)
        self.assertEqual(absent["opponent_expected_attempts"], 0.)

    def test_strict_admission_then_game_time_last_sixteen(self):
        rows = [source_row(game=f"g{i:02d}", kickoff=float(i),
                           available=150. - i if i % 2 else 30. + i,
                           counts=[i + 1] + [0] * 24) for i in range(18)]
        rows += [source_row(game="exact_boundary", kickoff=19., available=200.),
                 source_row(game="old_late_observation", kickoff=-100., available=201.)]
        _, _, profiles = histories(list(reversed(rows)))
        d = profiles.describe(query(kickoff=200.))
        self.assertEqual(d["team_trace"]["game_ids"], [f"g{i:02d}" for i in range(2, 18)])
        self.assertEqual(d["team_attempts"], sum(range(3, 19)))
        self.assertLess(d["latest_consumed_source"], 200.)

    def test_team_opponent_and_cutoff_are_part_of_query_identity(self):
        _, _, profiles = histories([source_row()])
        first = profiles.describe(query())
        changed_team = profiles.describe(query(team="OTHER"))
        changed_defense = profiles.describe(query(opponent="OTHER"))
        self.assertEqual(first["team_trace"]["games"], 1)
        self.assertEqual(changed_team["team_trace"]["games"], 0)
        self.assertEqual(changed_defense["opponent_trace"]["games"], 0)
        self.assertEqual(profiles.describe(query(kickoff=10.))["team_trace"]["games"], 0)
        for clock in (None, True, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                profiles.describe(query(kickoff=clock))

    def test_duplicate_identity_rejected(self):
        history, _, _ = histories([source_row()])
        history.rows.append(copy.deepcopy(history.rows[0]))
        with self.assertRaises(ValueError):
            mix.PassMixHistory(history)

    def test_target_and_future_completion_mutation_keeps_full_design(self):
        rows = [source_row(), source_row(game="query", kickoff=20., available=30.),
                source_row(game="future", kickoff=40., available=50.)]
        h, chart, profiles = histories(rows)
        mutated = copy.deepcopy(rows)
        for r in mutated:
            if r["available"] >= 20.:
                r["context_completions"] = list(r["context_attempts"])
                r["completions"] = r["official_completions"] = r["official_attempts"]
        hh, cc, pp = histories(mutated)
        converter = mix.AugmentedConversion.restore(conversion_payload())
        changed_query = query(official_attempts=999, official_completions=999,
                              actual=999, realized_mix=[999] * 25)
        for enriched in (False, True):
            a, x = mix.composition_design(query(), profiles, enriched)
            b, y = mix.composition_design(changed_query, pp, enriched)
            np.testing.assert_array_equal(a, b)
            np.testing.assert_array_equal(x, y)
        np.testing.assert_array_equal(converter.matrix(query(), h, chart, profiles),
                                      converter.matrix(changed_query, hh, cc, pp))
        np.testing.assert_array_equal(converter.probabilities(query(), h, chart, profiles),
                                      converter.probabilities(changed_query, hh, cc, pp))

    def test_named_payload_restore_and_vector_single_inference(self):
        history, chart, profiles = histories([source_row()])
        converter = mix.AugmentedConversion.restore(conversion_payload())
        restored = mix.AugmentedConversion.restore(converter.payload())
        q = query()
        matrix = converter.matrix(q, history, chart, profiles)
        np.testing.assert_array_equal(matrix, np.vstack([
            converter.numeric(q, history, chart, j, profiles) for j in range(25)]))
        full = np.column_stack((matrix, np.ones((25, 2))))
        scalar = np.asarray([special.expit(np.dot(row, converter.beta)) for row in full])
        np.testing.assert_allclose(converter.probabilities(q, history, chart, profiles), scalar, atol=1e-15)
        np.testing.assert_array_equal(converter.probabilities(q, history, chart, profiles),
                                      restored.probabilities(q, history, chart, profiles))
        for key in ("feature_order", "coefficient_group_order"):
            wrong = conversion_payload(); wrong[key].reverse()
            with self.assertRaises(ValueError):
                mix.AugmentedConversion.restore(wrong)
        wrong = conversion_payload(); wrong["levels"]["team"] = ["T1", "T1"]
        with self.assertRaises(ValueError):
            mix.AugmentedConversion.restore(wrong)
        for enriched in (False, True):
            model = mix.CompositionModel.restore(composition_payload(enriched))
            again = mix.CompositionModel.restore(model.payload())
            offset, x = mix.composition_design(q, profiles, enriched)
            logits = offset + np.r_[model.beta[:24], 0.] + x @ model.beta[24:]
            expected = special.softmax(logits)
            np.testing.assert_allclose(model.probabilities(q, profiles), expected, atol=1e-15)
            np.testing.assert_array_equal(model.probabilities(q, profiles), again.probabilities(q, profiles))
            wrong = composition_payload(enriched); wrong["feature_order"] = ["WRONG"] * len(wrong["feature_order"])
            with self.assertRaises(ValueError):
                mix.CompositionModel.restore(wrong)

    def test_positive_mass_cdf_push_and_exact_nb_thinning(self):
        history, chart, profiles = histories([source_row()])
        converter = mix.AugmentedConversion.restore(conversion_payload())
        mixer = mix.CompositionModel.restore(composition_payload())
        probability = float(mixer.probabilities(query(), profiles) @
                            converter.probabilities(query(), history, chart, profiles))
        mean, shape = 30., 8.
        law = CountLaw(mean * probability, shape)
        # Independent exact sum over the coherent A~NB, C|A~Binomial law.
        aa = np.arange(0, 350)
        for c in (0, 8, 19, 30):
            marginal = float(np.dot(stats.nbinom.pmf(aa, shape, shape / (shape + mean)),
                                    stats.binom.pmf(c, aa, probability)))
            self.assertAlmostEqual(law.pmf(c), marginal, places=12)
        self.assertEqual(law.shape, shape)
        self.assertAlmostEqual(sum(law.pmf(k) for k in range(250)), 1., places=10)
        cdf = [law.cdf(k) for k in range(-1, 100)]
        self.assertTrue(all(a <= b for a, b in zip(cdf, cdf[1:])))
        self.assertEqual(cdf[0], 0.)
        self.assertAlmostEqual(sum(exact_probabilities(law, 18).values()), 1., places=12)
        self.assertAlmostEqual(exact_probabilities(law, 18)["push"], law.pmf(18), places=12)
        self.assertEqual(exact_probabilities(law, 18.5)["push"], 0.)
        self.assertEqual(CountLaw(0., shape).pmf(0), 1.)

    def test_multinomial_gradient_without_optimizer(self):
        for width in (1, 3):
            beta = np.linspace(-.12, .09, 24 + width)
            offset = np.log(np.vstack((np.arange(1, 26), np.arange(25, 0, -1))) / 325.)
            x = np.sin(np.arange(2 * 25 * width).reshape(2, 25, width) / 11.)
            y = np.zeros((2, 25)); y[0, [0, 3, 24]] = [6, 4, 1]; y[1, [1, 12]] = [3, 5]
            penalty = np.r_[np.full(24, 20.), np.full(width, 10.)]
            loss, gradient = mix.composition_objective(beta, offset, x, y, penalty)
            self.assertTrue(math.isfinite(loss))
            finite = []
            for j in range(len(beta)):
                plus, minus = beta.copy(), beta.copy(); plus[j] += 1e-5; minus[j] -= 1e-5
                finite.append((mix.composition_objective(plus, offset, x, y, penalty)[0] -
                               mix.composition_objective(minus, offset, x, y, penalty)[0]) / 2e-5)
            np.testing.assert_allclose(gradient, finite, rtol=1e-5, atol=1e-6)

    def test_conditional_conversion_gradient_without_optimizer(self):
        width = len(mix.CONVERSION_FEATURE_ORDER) + 2
        beta = np.linspace(-.09, .13, width)
        x = np.cos(np.arange(4 * width).reshape(4, width) / 13.)
        n = np.asarray([0., 3., 5., 10.]); y = np.asarray([0., 0., 4., 10.])
        penalty = np.r_[np.full(25, 2.), np.full(width - 27, 10.), [20., 20.]]
        loss, gradient = mix.conditional_binomial_objective(beta, x, n, y, penalty)
        self.assertTrue(math.isfinite(loss))
        finite = []
        for j in range(width):
            plus, minus = beta.copy(), beta.copy(); plus[j] += 1e-5; minus[j] -= 1e-5
            finite.append((mix.conditional_binomial_objective(plus, x, n, y, penalty)[0] -
                           mix.conditional_binomial_objective(minus, x, n, y, penalty)[0]) / 2e-5)
        np.testing.assert_allclose(gradient, finite, rtol=1e-5, atol=1e-6)


if __name__ == "__main__":
    unittest.main()
