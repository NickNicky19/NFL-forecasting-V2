import unittest

from nfl_v2.identity import GSIS_TRIM_POLICY, history_join_audit, resolve_gsis_identity, unique_gsis_bridge


class IdentityTests(unittest.TestCase):
    def test_exact_bridge_recovers_missing_provider_gsis(self):
        result = resolve_gsis_identity(None, ["00-0012345"])
        self.assertEqual(result.player_id, "00-0012345")
        self.assertEqual(result.state, "QUALIFIED_EXACT_BRIDGE")

    def test_conflict_and_ambiguity_abstain(self):
        self.assertIsNone(resolve_gsis_identity("00-0012345", ["00-0054321"]).player_id)
        self.assertEqual(resolve_gsis_identity(None, ["00-0012345", "00-0054321"]).state,
                         "AMBIGUOUS_BRIDGE")

    def test_invalid_namespace_does_not_become_gsis(self):
        self.assertEqual(resolve_gsis_identity("sleeper:12345").state, "INVALID_GSIS_BINDING")

    def test_provider_whitespace_normalization_is_explicit(self):
        result = resolve_gsis_identity(" 00-0012345", ["00-0012345"],
                                       bridge_source_id="fixture-source-v1", normalization_policy=GSIS_TRIM_POLICY)
        self.assertEqual(result.player_id, "00-0012345")
        self.assertEqual(result.state, "QUALIFIED_EXACT_BRIDGE_WHITESPACE_NORMALIZED")

    def test_whitespace_without_qualified_crosswalk_abstains(self):
        self.assertEqual(resolve_gsis_identity(" 00-0012345").state,
                         "WHITESPACE_REQUIRES_QUALIFIED_EXACT_BRIDGE")

    def test_bridge_requires_forward_and_reverse_uniqueness(self):
        result = unique_gsis_bridge([("a", "00-0012345"), ("b", "00-0012345"),
                                     ("c", "00-0054321"), ("c", "00-0054321"),
                                     ("d", "00-0098765"), ("d", "00-0098766")], source_id="fixture-source-v1")
        self.assertEqual(result, {"c": "00-0054321"})

    def test_join_audit_distinguishes_namespace_failure_and_new_player(self):
        result = history_join_audit(["00-0012345"], ["sleeper:12345", "00-0054321", "00-0012345"])
        self.assertEqual(result["exact_history_key_matches"], 1)
        self.assertEqual(result["incompatible_namespace_query_rows"], 1)
        self.assertEqual(result["unmatched_query_rows"], 2)

    def test_current_season_startup_is_not_namespace_failure(self):
        result = history_join_audit([], ["00-0012345"])
        self.assertEqual(result["state"], "NO_TRAINING_HISTORY_STARTUP")
        self.assertEqual(result["incompatible_namespace_query_rows"], 0)


if __name__ == "__main__":
    unittest.main()
