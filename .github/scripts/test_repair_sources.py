import unittest

from repair_sources import (
    apply_repaired_source,
    copy_equivalent_sources,
    normalize_existing_source_markers,
    normalized_title,
)


class SourceRepairTests(unittest.TestCase):
    def test_equivalent_rule_copies_one_official_source_without_ai(self):
        data = {
            "cards": [{"id": "c1", "bank": "測試銀行"}],
            "rules": [
                {"id": "known", "cardId": "c1", "title": "指定消費最高5%回饋",
                 "sourceUrl": "https://bank.test/promo"},
                {"id": "missing", "cardId": "c1", "title": "指定消費最高3%回饋",
                 "sourceUrl": ""},
            ],
        }
        issuers = {"測試銀行": {"allowedHosts": ["bank.test"]}}
        self.assertEqual(copy_equivalent_sources(data, issuers), 1)
        self.assertEqual(data["rules"][1]["sourceUrl"], "https://bank.test/promo")

    def test_repair_clears_stale_missing_source_markers(self):
        rule = {
            "sourceUrl": "",
            "evidenceStatus": "MISSING_SOURCE",
            "validationIssues": ["SOURCE_MISSING", "REWARD_NEEDS_REVIEW"],
        }
        apply_repaired_source(rule, "https://bank.test/promo", "test")
        self.assertEqual(rule["sourceUrl"], "https://bank.test/promo")
        self.assertEqual(rule["evidenceStatus"], "SOURCE_FOUND_NEEDS_REVALIDATION")
        self.assertEqual(rule["validationIssues"], ["REWARD_NEEDS_REVIEW"])

    def test_existing_source_markers_are_normalized(self):
        data = {"rules": [{
            "sourceUrl": "https://bank.test/promo",
            "evidenceStatus": "MISSING_SOURCE",
            "validationIssues": ["SOURCE_MISSING"],
        }, {
            "sourceUrl": "",
            "evidenceStatus": "MISSING_SOURCE",
            "validationIssues": ["SOURCE_MISSING"],
        }]}
        self.assertEqual(normalize_existing_source_markers(data), 1)
        self.assertEqual(data["rules"][0]["validationIssues"], [])
        self.assertEqual(data["rules"][1]["validationIssues"], ["SOURCE_MISSING"])

    def test_title_normalization_ignores_spacing_and_punctuation(self):
        self.assertEqual(normalized_title("LINE Pay、指定消費"), normalized_title("LINEPay 指定消費"))


if __name__ == "__main__":
    unittest.main()
