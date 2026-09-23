import unittest
from update_data import merge_data, enrich_reward_fields, is_real_card_product

class MergeTests(unittest.TestCase):
    def test_model_card_id_is_preserved_for_mapping(self):
        cards, rules = {}, {}
        merge_data('bank', {'cards': [{'id': 'ai1', 'cardName': 'Test卡'}],
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

    def test_audiences_and_services_are_not_cards(self):
        rejected = ['永豐銀行全卡友', 'Tesla卡友', '渣打銀行信用卡',
                    '玉山銀行信用卡暨簽帳金融卡', '聚富定存新台幣高利定存專案',
                    '白金卡以上指定信用卡']
        self.assertTrue(all(not is_real_card_product(name) for name in rejected))
        accepted = ['國泰世華 CUBE 信用卡', '玉山 U Bear卡', '滙豐卓越理財信用卡']
        self.assertTrue(all(is_real_card_product(name) for name in accepted))

if __name__ == '__main__':
    unittest.main()
