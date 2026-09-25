import json
import tempfile
import unittest
from pathlib import Path

from semantic_reindex import apply_batch, focused_excerpt, load_dataset_or_fail


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

    def test_tiered_reward_keeps_default_separate_from_maximum(self):
        rules = {"a": {"id": "a"}}
        result = {"rules": [{"id": "a", "intentTags": ["海外消費"], "intentEvidence": "一般1%、達標6%",
            "evidenceStatus": "VERIFIED", "validationIssues": [], "quickSearchEligible": True,
            "rewardCalculationMode": "TIERED", "maxRateRequires": ["達指定帳戶等級"],
            "rewardTiers": [
                {"name": "一般", "totalRate": 1, "isDefault": True, "requirements": []},
                {"name": "最高", "totalRate": 6, "isDefault": False, "requirements": ["達指定帳戶等級"]},
            ]}]}
        apply_batch(rules, result, {"a"})
        self.assertEqual(rules["a"]["rewardCalculationMode"], "TIERED")
        self.assertEqual(next(t for t in rules["a"]["rewardTiers"] if t["isDefault"])["totalRate"], 1)
        self.assertEqual(max(t["totalRate"] for t in rules["a"]["rewardTiers"]), 6)

    def test_insurance_coverage_is_never_cashback(self):
        rules = {"a": {"id": "a", "title": "海外旅遊保險專屬活動", "quotaInfo": "保額319萬元",
                       "rewardType": "cash", "rewardAmount": 3190000, "capAmount": 3190000}}
        result = {"rules": [{"id": "a", "intentTags": ["海外消費"], "intentEvidence": "旅遊保險",
                              "evidenceStatus": "VERIFIED", "validationIssues": [],
                              "quickSearchEligible": True, "rewardType": "cash"}]}
        apply_batch(rules, result, {"a"})
        self.assertEqual(rules["a"]["rewardType"], "insurance_benefit")
        self.assertIsNone(rules["a"]["rewardAmount"])
        self.assertFalse(rules["a"]["quickSearchEligible"])
        self.assertIn("NOT_SPENDING_REWARD", rules["a"]["validationIssues"])

    def test_empty_dataset_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "data.json"
            target.write_text(json.dumps({"cards": [], "rules": []}), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                load_dataset_or_fail(target)


if __name__ == "__main__":
    unittest.main()
