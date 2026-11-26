import unittest
from repair_bank_attribution import attribute


class BankAttributionTests(unittest.TestCase):
    def test_unique_official_host_only_and_preserve_eligibility(self):
        registry = {'issuers': [{'name': '甲銀行', 'allowedHosts': ['bank.example']}]}
        data = {'cards': [{'id': 'other', 'bank': '乙銀行'}], 'rules': [
            {'id': 'one', 'sourceUrl': 'https://bank.example/offer', 'associationStatus': 'needs_review'},
            {'id': 'two', 'sourceUrl': 'https://bank.example/offer', 'cardId': 'other'},
            {'id': 'three', 'sourceUrl': 'https://bank.example.evil/offer'},
        ]}
        changes = attribute(data, registry)
        self.assertEqual([row['id'] for row in changes], ['one'])
        self.assertEqual(data['rules'][0]['bank'], '甲銀行')
        self.assertEqual(data['rules'][0]['associationStatus'], 'needs_review')
        self.assertNotIn('bank', data['rules'][1])
        self.assertNotIn('bank', data['rules'][2])


if __name__ == '__main__':
    unittest.main()
