import unittest
from pipeline_crawler import build_sample_rule_from_markdown

class PipelineGuardrailsTests(unittest.TestCase):
    def test_headline_does_not_invent_base_or_cap_scope(self):
        r = build_sample_rule_from_markdown('銀行','https://bank.test/offer','最高 5% 上限 300 元')
        self.assertEqual((r.baseRate,r.promoRate),(0,0))
        self.assertIsNone(r.capScope)
        self.assertIsNone(r.capPeriod)
        self.assertEqual(r.evidenceStatus,'UNVERIFIED')
        self.assertFalse(r.quickSearchEligible)

    def test_positive_merchant_mention_is_not_exclusion(self):
        r = build_sample_rule_from_markdown('銀行','https://bank.test/offer','全聯購物回饋最高 5%')
        self.assertNotIn('全聯',r.excludedKeywords)
