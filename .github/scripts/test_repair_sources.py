import unittest

from repair_sources import copy_equivalent_sources, normalized_title


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

    def test_title_normalization_ignores_spacing_and_punctuation(self):
        self.assertEqual(normalized_title("LINE Pay、指定消費"), normalized_title("LINEPay 指定消費"))


if __name__ == "__main__":
    unittest.main()
