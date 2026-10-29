"""Fictional chronology/contract tests. Zero NFL observations or accuracy claims."""
import unittest
from dataclasses import replace

from nfl_v2.history import (Observation, Origin, Query, RunManifest,
                            SourceAdmission, run)


def admission():
    return SourceAdmission("fictional", "current_vintage_reconstruction",
                           "invented fixture timestamps, not observed NFL availability",
                           ("rush_yd", "rec", "anytime_td"), "fixture complete explicit values",
                           "fixture verified played", "fixture historical positions",
                           "fictional-no-feed")


def manifest(**changes):
    fields = dict(experiment_id="fictional-history-test", evaluation_panel_id="frozen-fixture",
                  cohort_definition_id="predeclared-fixture", source_admission_ids=("fictional",),
                  evaluation_seasons=(2022, 2023, 2024, 2025, 2026), max_origins=10,
                  max_observations_per_origin=20, max_queries_per_origin=20,
                  max_forecast_cells=120, max_summary_groups=120, max_candidate_row_checks=10000)
    fields.update(changes)
    return RunManifest(**fields)


def observed(identity, season, week, kickoff, available, value, **changes):
    fields = dict(observation_id=identity, source_id="fictional", game_id=identity,
                  player_id="p", position="RB", target="rush_yd", season=season,
                  week=week, kickoff_utc=kickoff, available_utc=available, value=value)
    fields.update(changes)
    return Observation(**fields)


def query(**changes):
    fields = dict(query_id="q", source_id="fictional", game_id="future", player_id="p",
                  position="RB", target="rush_yd", season=2026, week=2,
                  kickoff_utc="2026-09-13T18:00:00Z")
    fields.update(changes)
    return Query(**fields)


def origin(observations=(), queries=None, **changes):
    fields = dict(origin_id="origin", cutoff_utc="2026-09-13T16:30:00Z",
                  queries=queries if queries is not None else (query(),),
                  observations=tuple(observations))
    fields.update(changes)
    return Origin(**fields)


OLD = observed("old", 2024, 1, "2024-09-08T18:00:00Z", "2024-09-10T00:00:00Z", 10)
RECENT = observed("recent", 2025, 1, "2025-09-07T18:00:00Z", "2025-09-09T00:00:00Z", 40)
CURRENT = observed("current", 2026, 1, "2026-09-06T18:00:00Z", "2026-09-08T00:00:00Z", 100)


class HistoryContractTests(unittest.TestCase):
    def execute(self, o, **kwargs):
        return run((o,), (admission(),), manifest(), **kwargs)

    def test_identical_queries_change_only_fit_history(self):
        result = self.execute(origin((OLD, RECENT, CURRENT)))
        means = {r["history_regime"]: r for r in result["rows"] if r["product"] == "empirical_mean"}
        self.assertEqual({r["query_id"] for r in result["rows"]}, {"q"})
        self.assertEqual(means["H-CURRENT"]["forecast"], 100)
        self.assertEqual(means["H-RECENT"]["forecast"], 70)
        self.assertEqual(means["H-MULTI"]["forecast"], 50)
        self.assertEqual(means["H-MULTI"]["training_observation_ids"], ["old", "recent", "current"])
        self.assertEqual(result["optimization_fits"], 0)
        self.assertEqual(result["scores"], 0)

    def test_week_one_startup_and_strict_current_have_no_old_fallback(self):
        q = query(week=1, kickoff_utc="2026-09-06T18:00:00Z")
        o = origin((OLD, RECENT), (q,), cutoff_utc="2026-09-06T16:30:00Z")
        rows = self.execute(o, strict_current=True)["rows"]
        self.assertTrue(all(r["forecast"] == 0 and r["used_n"] == 0 for r in rows))
        self.assertTrue(all(r["fallback"] == "constant_zero_startup" for r in rows))
        self.assertTrue(all(not r["source_ids"] for r in rows))
        self.assertEqual({r["history_regime"] for r in rows}, {"H-CURRENT"})
        core = self.execute(o)["rows"]
        self.assertEqual([r["forecast"] for r in core if r["history_regime"] == "H-RECENT"], [40, 40])

    def test_available_boundary_and_target_game_rejected_before_prediction(self):
        bad = replace(CURRENT, available_utc="2026-09-13T16:30:00Z")
        for row in (bad, replace(CURRENT, game_id="future"),
                    replace(CURRENT, available_utc="2026-09-13T17:00:00Z")):
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.execute(origin((row,)))

    def test_unknown_naive_or_impossible_clock_rejected(self):
        for clock in ("", None, "2026-09-08T00:00:00", CURRENT.kickoff_utc):
            with self.subTest(clock=clock), self.assertRaises(ValueError):
                self.execute(origin((replace(CURRENT, available_utc=clock),)))
        with self.assertRaises(ValueError):
            self.execute(origin(cutoff_utc="2026-09-13T18:00:00Z"))

    def test_nonparticipant_missing_invalid_counts_and_duplicate_identity_rejected(self):
        for row in (replace(CURRENT, participation="DNP"), replace(CURRENT, value=None),
                    replace(CURRENT, value=float("nan")), replace(CURRENT, target="rec", value=-1)):
            with self.subTest(row=row), self.assertRaises(ValueError):
                self.execute(origin((row,)))
        with self.assertRaises(ValueError):
            self.execute(origin((CURRENT, replace(CURRENT, observation_id="other"))))

    def test_signed_yards_and_lower_median_not_component_averaging(self):
        negative = replace(CURRENT, value=-4)
        second = replace(CURRENT, observation_id="other", game_id="other", value=10)
        rows = self.execute(origin((negative, second)))["rows"]
        current = {r["product"]: r["forecast"] for r in rows if r["history_regime"] == "H-CURRENT"}
        self.assertEqual(current, {"empirical_mean": 3, "lower_median": -4})

    def test_unseen_player_uses_same_arm_position_then_zero(self):
        rows = self.execute(origin((OLD, CURRENT), (query(player_id="replacement"),)))["rows"]
        self.assertEqual({r["fallback"] for r in rows}, {"position_empirical"})
        self.assertTrue(all(r["player_n"] == 0 for r in rows))
        rows = self.execute(origin((CURRENT,), (query(player_id="replacement", position="WR"),)))["rows"]
        self.assertTrue(all(r["forecast"] == 0 and r["fallback"] == "constant_zero_startup" for r in rows))

    def test_rolling_origin_updates_even_within_week(self):
        first = origin((), (query(query_id="first", week=1, kickoff_utc="2026-09-06T18:00:00Z"),),
                       origin_id="first", cutoff_utc="2026-09-06T16:30:00Z")
        # A later same-week game can use an earlier game only after admitted availability.
        later_q = query(query_id="later", game_id="later", week=1, kickoff_utc="2026-09-08T18:00:00Z")
        later = origin((CURRENT,), (later_q,), origin_id="later", cutoff_utc="2026-09-08T16:30:00Z")
        result = run((first, later), (admission(),), manifest(), strict_current=True)
        self.assertEqual([r["forecast"] for r in result["rows"]], [0, 0, 100, 100])

    def test_no_2026_history_in_2025_and_expanding_floor(self):
        q25 = query(season=2025, kickoff_utc="2025-09-14T18:00:00Z")
        o25 = origin((OLD, RECENT), (q25,), cutoff_utc="2025-09-14T16:30:00Z")
        rows = self.execute(o25)["rows"]
        current = [r for r in rows if r["history_regime"] == "H-CURRENT"]
        self.assertTrue(all(r["forecast"] == 40 for r in current))
        with self.assertRaises(ValueError):
            self.execute(origin((replace(OLD, season=2021),)))
        with self.assertRaises(ValueError):
            self.execute(origin((CURRENT,), (q25,), cutoff_utc="2025-09-14T16:30:00Z"))

    def test_invalid_scope_admission_or_budget_fails_closed(self):
        for m in (manifest(max_forecast_cells=5), manifest(max_summary_groups=5),
                  manifest(training_floor=2021), manifest(tuned_or_external_priors=True)):
            with self.subTest(m=m), self.assertRaises(ValueError):
                run((origin(),), (admission(),), m)
        with self.assertRaises(ValueError):
            run((origin(),), (replace(admission(), availability_basis=""),), manifest())
        with self.assertRaises(ValueError):
            self.execute(origin(queries=(query(week=8),)))
        with self.assertRaises(ValueError):
            self.execute(origin(queries=(query(source_id="not-admitted"),)))
        with self.assertRaises(ValueError):
            run((origin((OLD, RECENT, CURRENT)),), (admission(),), manifest(max_candidate_row_checks=1))

    def test_anytime_is_empirical_binary_probability_only(self):
        one = replace(CURRENT, target="anytime_td", value=1)
        zero = replace(CURRENT, target="anytime_td", value=0, game_id="zero", observation_id="zero")
        result = self.execute(origin((one, zero), (query(target="anytime_td"),)))
        self.assertEqual(result["forecast_cells"], 3)
        self.assertTrue(all(r["forecast"] == .5 and r["product"] == "event_probability" for r in result["rows"]))

    def test_receipt_binds_values_policy_and_extended_fullback_role(self):
        original = self.execute(origin((CURRENT,)))
        changed = self.execute(origin((replace(CURRENT, value=101),)))
        self.assertNotEqual(original['origin_inputs_sha256'], changed['origin_inputs_sha256'])
        strict = run((origin((CURRENT,)),), (admission(),), manifest(), strict_current=True)
        self.assertNotEqual(original['policy_run_sha256'], strict['policy_run_sha256'])
        fb = self.execute(origin((replace(CURRENT, position='FB'),), (query(position='FB'),)))
        self.assertTrue(all(r['position']=='FB' for r in fb['rows']))


if __name__ == "__main__":
    unittest.main()
