import unittest

from evaluate_official_baseline import compare


class OfficialBaselineTests(unittest.TestCase):
    def test_wrong_rate_is_reported_and_never_certified(self):
        baseline = {'baselineId': 'one', 'scope': 'test', 'sourceUrl': 'https://bank.test',
                    'offers': [{'id': 'offer', 'fields': {'promoRate': 3.5}}]}
        mapping = {'baselineId': 'one', 'mappings': [{'offerId': 'offer', 'ruleId': 'rule', 'tierIndex': 0}]}
        data = {'rules': [{'id': 'rule', 'promoRate': 1, 'rewardTiers': [{'promoRate': 2}]}]}
        report = compare(baseline, mapping, data)
        self.assertFalse(report['rows'][0]['fieldChecks']['promoRate']['matches'])
        self.assertEqual(report['acceptanceStatus'], 'NOT_ESTABLISHED')
        self.assertIsNone(report['marketAccuracyPercent'])


if __name__ == '__main__':
    unittest.main()
