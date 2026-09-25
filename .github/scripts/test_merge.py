import unittest
from update_data import merge_data, enrich_reward_fields

class MergeTests(unittest.TestCase):
    def test_model_card_id_is_preserved_for_mapping(self):
        cards, rules = {}, {}
        merge_data('bank', {'cards': [{'id': 'ai1', 'cardName': 'Test卡', 'entityType': 'CARD_PRODUCT',
                   'classificationConfidence': .95, 'classificationEvidence': '官方產品頁'}],
                   'rules': [{'cardId': 'ai1', 'title': '活動'}]}, cards, rules, 'https://bank.test/card')
        self.assertEqual(next(iter(cards.values()))['id'], next(iter(rules.values()))['cardId'])

    def test_unknown_card_is_not_assigned_to_first_card(self):
        rules = {}
        merge_data('bank', {'rules': [{'cardId': 'missing', 'title': '活動'}]},
                   {'x': {'bank': 'bank', 'id': 'real'}}, rules, 'https://bank.test/card')
        self.assertIsNone(next(iter(rules.values()))['cardId'])

    def test_cap_is_not_cash_reward_and_old_timestamp_is_preserved(self):
        rule = enrich_reward_fields({'capAmount': 500, 'fetchedAt': 'old'}, 'https://bank.test')
        self.assertIsNone(rule['rewardAmount'])
        self.assertEqual(rule['fetchedAt'], 'old')

    def test_cash_cap_is_not_presented_as_fixed_cash_reward(self):
        rule = enrich_reward_fields({
            'baseRate': 1, 'promoRate': 2, 'rewardType': 'cash',
            'rewardAmount': 150, 'capAmount': 150
        }, 'https://bank.test')
        self.assertEqual(rule['rewardType'], 'percent')
        self.assertEqual(rule['rewardAmount'], 2)

    def test_only_ai_classified_product_is_merged(self):
        cards, rules = {}, {}
        result = {'cards': [
            {'id': 'good', 'cardName': '真卡', 'entityType': 'CARD_PRODUCT',
             'classificationConfidence': .95, 'classificationEvidence': '官網產品頁'},
            {'id': 'bad', 'cardName': '全卡友', 'entityType': 'AUDIENCE',
             'classificationConfidence': .99, 'classificationEvidence': '適用對象'}], 'rules': []}
        merge_data('bank', result, cards, rules, 'https://bank.test')
        self.assertEqual([c['cardName'] for c in cards.values()], ['真卡'])

    def test_rule_naming_unicard_is_not_attached_to_ubear(self):
        cards = {
            'u': {'id': 'ubear', 'bank': '玉山銀行', 'cardName': '玉山 U Bear卡'},
            'uni': {'id': 'unicard', 'bank': '玉山銀行', 'cardName': 'E.SUN Unicard'},
        }
        rules = {}
        merge_data('玉山銀行', {'rules': [{
            'cardId': 'ubear', 'title': '玉山Unicard UP選方案',
            'quotaInfo': 'LINE Pay最高4.5%'
        }]}, cards, rules, 'https://bank.test/unicard')
        rule = next(iter(rules.values()))
        self.assertIsNone(rule['cardId'])
        self.assertEqual(rule['associationStatus'], 'needs_review')

    def test_product_rule_cannot_claim_bank_wide_without_audience_copy(self):
        cards = {'u': {'id': 'ubear', 'bank': '玉山銀行', 'cardName': '玉山 U Bear卡'}}
        rules = {}
        merge_data('玉山銀行', {'rules': [{
            'cardId': 'ubear', 'title': '指定網購3%',
            'eligibleCardScope': 'ALL_BANK_CARDS'
        }]}, cards, rules, 'https://bank.test/ubear')
        self.assertEqual(next(iter(rules.values()))['eligibleCardScope'], 'SPECIFIC_CARD')

if __name__ == '__main__':
    unittest.main()
