import unittest

from semantic_reindex import apply_batch, focused_excerpt


class SemanticReindexTests(unittest.TestCase):
    def test_focused_excerpt_uses_matching_evidence(self):
        rule = {"title": "海外消費回饋", "matchedMerchants": []}
        text = "前文 " * 300 + "海外消費最高3%回饋" + " 後文" * 300
        self.assertIn("海外消費最高3%回饋", focused_excerpt(text, rule))

    def test_only_expected_ids_are_updated(self):
        rules = {"a": {"id": "a"}, "b": {"id": "b"}}
        result = {"rules": [
            {"id": "a", "intentTags": ["海外消費"], "intentEvidence": "國外消費3%",
             "evidenceStatus": "VERIFIED", "validationIssues": [], "quickSearchEligible": True},
            {"id": "b", "intentTags": ["惡意"], "intentEvidence": "猜測",
             "evidenceStatus": "VERIFIED", "validationIssues": [], "quickSearchEligible": True},
        ]}
        changed, rows = apply_batch(rules, result, {"a"})
        self.assertEqual(changed, 1)
        self.assertEqual(rows[0]["id"], "a")
        self.assertNotIn("intentTags", rules["b"])

    def test_unverified_rule_does_not_receive_intent_tags(self):
        rules = {"a": {"id": "a"}}
        result = {"rules": [{"id": "a", "intentTags": ["海外消費"], "intentEvidence": "不確定",
                              "evidenceStatus": "UNVERIFIED", "validationIssues": [],
                              "quickSearchEligible": True}]}
        apply_batch(rules, result, {"a"})
        self.assertEqual(rules["a"]["intentTags"], [])


if __name__ == "__main__":
    unittest.main()
