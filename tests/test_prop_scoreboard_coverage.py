import copy
import json
from pathlib import Path
import unittest
from tools.check_prop_scoreboard_coverage import validate, validate_csv


def fictional_panel(empty_under=False):
    rows, metadata = [], []
    # Unequal side denominators distinguish pooled accuracy from mean side accuracy.
    counts = {"over": (1, 0), "under": (0, 0 if empty_under else 3),
              "Combined": (1, 0 if empty_under else 3)}
    for alias, time in ((False, "one_week"), (True, "same_week_season_alias")):
        for side, (wins, losses) in counts.items():
            identity = time+side
            n = wins+losses
            states = dict(WIN=wins, LOSS=losses, PUSH=0, ABSTAIN=0, DNP=0,
                          PENDING=0, UNKNOWN_PARTICIPATION=0, MISSING_ACTUAL=0)
            metrics = dict(WIN=wins, LOSS=losses, PUSH=0,
                           status_counts=states,
                           bookmaker_settlement_status_counts={"UNRESOLVED_CONTRACT": n},
                           denominators=dict(decided=n, outer_rows=n,
                                             supported_threshold_outcomes=n, unresolved=0),
                           hit_rate=wins/n if n else None,
                           returns=dict(ROI=None, net=None, drawdown=None))
            rows.append(dict(record_id=identity, strategy="fixed", target="rec", side=side,
                             actual_preselected_side=side, cohort_id="ALL", K=None, rank_scope=None,
                             time_panel_id=time, horizon_id="before_kickoff", forecast_rows=n, n=n,
                             query_membership_sha256="fictional-"+side,
                             season_alias_of_week_view=alias, week="alias" if alias else 7,
                             settlement_status="UNRESOLVED_CONTRACT", selection_metrics=metrics,
                             selection_loss_rate=losses/n if n else None))
            metadata.append(dict(record_id=identity, source_record_id=identity,
                                 query_membership_sha256="fictional-"+side,
                                 season_alias_of_week_view=alias,
                                 alias_of_record_id="one_week"+side if alias else None))
    unavailable = [dict(strategy="fixed", target="unqualified", side=side, time_panel_id=time,
                        state="UNAVAILABLE", reason="missing contract", WIN=None, LOSS=None,
                        PUSH=None, hit_rate=None, n=None, selection_count=None, selection_loss_rate=None)
                   for side in ("over", "under", "Combined")
                   for time in ("one_week", "same_week_season_alias")]
    manifest = dict(source_scores={"sha256": "fictional-source-hash"}, audit_views=6,
                    default_predicate={"season_alias_of_week_view": False}, default_views=3,
                    aliases_retained_not_pooled=3, unsupported_cell_count=6,
                    unsupported_targets=["unqualified"])
    return manifest, rows, dict(source_score_sha256="fictional-source-hash", rows=metadata), unavailable


class PropScoreboardCoverageTests(unittest.TestCase):
    def test_unequal_side_support_validates_pooled_rate(self):
        self.assertEqual(validate(*fictional_panel())["default_weekly_views"], 3)

    def test_unweighted_combined_hit_rate_is_rejected(self):
        args = fictional_panel()
        args[1][2]["selection_metrics"]["hit_rate"] = .5  # (100% + 0%)/2, wrong for 1/4.
        with self.assertRaisesRegex(ValueError, "rate or denominator"):
            validate(*args)

    def test_actual_side_labels_cannot_be_swapped(self):
        args = fictional_panel()
        args[1][0]["actual_preselected_side"] = "under"
        with self.assertRaisesRegex(ValueError, "selected-side identity"):
            validate(*args)

    def test_coherent_side_win_loss_swap_still_fails_combined_reconciliation(self):
        args = fictional_panel()
        for i in (0, 3):  # Keep the alias identical and each side internally valid.
            r = args[1][i]
            r["selection_metrics"].update(WIN=0, LOSS=1, hit_rate=0.)
            r["selection_metrics"]["status_counts"].update(WIN=0, LOSS=1)
            r["selection_loss_rate"] = 1.
        with self.assertRaisesRegex(ValueError, "Combined W/L/push"):
            validate(*args)

    def test_empty_under_does_not_borrow_other_side_denominator(self):
        args = fictional_panel(empty_under=True)
        validate(*args)
        args[1][1]["selection_metrics"]["hit_rate"] = 0.
        with self.assertRaisesRegex(ValueError, "null rate"):
            validate(*args)

    def test_season_alias_cannot_link_another_side(self):
        args = fictional_panel()
        args[2]["rows"][3]["alias_of_record_id"] = "one_weekunder"
        with self.assertRaisesRegex(ValueError, "Season alias changes"):
            validate(*args)

    def test_missing_supported_side_cell_is_rejected_even_at_same_row_count(self):
        args = fictional_panel()
        args[1][1]["cohort_id"] = "other"
        args[1][4]["cohort_id"] = "other"
        with self.assertRaisesRegex(ValueError, "Missing Over/Under/Combined"):
            validate(*args)

    def test_unavailable_contract_cannot_claim_zero_loss(self):
        args = fictional_panel()
        args[3][0]["LOSS"] = 0
        with self.assertRaisesRegex(ValueError, "fake zero"):
            validate(*args)

    def test_statistical_win_does_not_authenticate_bookmaker_return(self):
        args = fictional_panel()
        args[1][0]["selection_metrics"]["returns"]["ROI"] = 1.
        with self.assertRaisesRegex(ValueError, "Unverified bookmaker"):
            validate(*args)


class FullProviderPoolCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.manifest = json.loads((root / "reports/championship-20261030f/CURRENT_PROP_SCOREBOARD_VIEW.json").read_text())
        cls.scores = json.loads((root / cls.manifest["source_scores"]["path"]).read_text())
        cls.metadata = json.loads((root / cls.manifest["metadata"]["path"]).read_text())
        cls.unsupported = json.loads((root / cls.manifest["unsupported_cells"]["path"]).read_text())
        cls.comparisons = json.loads((root / "reports/championship-20261030f/offer-expansion/full-pool-v1/COMPARISON_ANNOTATIONS.json").read_text())

    def args(self):
        return copy.deepcopy((self.manifest, self.scores, self.metadata, self.unsupported))

    def test_full_pool_has_every_actual_selected_side_and_no_alias_samples(self):
        result = validate(self.manifest, self.scores, self.metadata, self.unsupported)
        self.assertEqual((result["score_views"], result["group_cells"], result["retained_aliases"]), (4980, 1660, 0))

    def test_full_pool_csv_binds_every_field_and_paired_annotation(self):
        self.assertEqual(validate_csv(self.manifest["records_csv"], self.scores, self.metadata,
                                     self.manifest["source_scores"]["sha256"], self.manifest["scope"], self.comparisons), 4980)

    def test_full_pool_rejects_unweighted_combined_percentage(self):
        args = self.args()
        args[1][2]["selection_metrics"]["hit_rate"] = sum(args[1][i]["selection_metrics"]["hit_rate"] for i in (0, 1))/2
        with self.assertRaisesRegex(ValueError, "rate or denominator"):
            validate(*args)

    def test_full_pool_empty_side_rate_is_null(self):
        args = self.args()
        next(r for r in args[1] if not r["n"])["selection_metrics"]["hit_rate"] = 0.
        with self.assertRaisesRegex(ValueError, "null rate"):
            validate(*args)

    def test_full_pool_rejects_fake_supported_contract(self):
        args = self.args()
        args[3][0]["wins"] = 0
        with self.assertRaisesRegex(ValueError, "fake zero"):
            validate(*args)

    def test_full_pool_rejects_metadata_scope_drift(self):
        args = self.args()
        args[2]["rows"][0]["unique_players"] += 1
        with self.assertRaisesRegex(ValueError, "metadata scope"):
            validate(*args)

    def test_full_pool_does_not_turn_point_outputs_into_probabilities(self):
        args = self.args()
        args[1][0]["selection_metrics"]["probability_scores"]["brier"] = .1
        with self.assertRaisesRegex(ValueError, "probability/numerical"):
            validate(*args)



if __name__ == "__main__":
    unittest.main()
