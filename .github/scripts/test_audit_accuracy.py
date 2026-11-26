import unittest

from audit_accuracy import audit


class AuditAccuracyTests(unittest.TestCase):
    def test_mixed_percent_and_fixed_point_fields_require_review(self):
        rule = {'id': 'r', 'sourceUrl': 'https://bank.test/offer', 'rewardType': 'points',
                'rewardUnit': 'points', 'baseRate': 1, 'promoRate': 6,
                'rewardAmount': 200, 'capAmount': 200}
        report = audit({'cards': [], 'rules': [rule]})
        self.assertIn('AMBIGUOUS_PERCENT_AND_FIXED_POINT_REWARD', report['rules'][0]['issues'])
        rule['rewardAmount'] = None
        report = audit({'cards': [], 'rules': [rule]})
        self.assertNotIn('AMBIGUOUS_PERCENT_AND_FIXED_POINT_REWARD', report['rules'][0]['issues'])

    def test_fixed_point_evidence_and_unit_spellings_are_handled(self):
        url = 'https://bank.test/offer'
        rule = {'id': 'r', 'sourceUrl': url, 'rewardType': 'points',
                'rewardUnit': 'LINE POINTS', 'baseRate': 1,
                'rewardAmount': 1000, 'capAmount': 1000}
        issues = audit({'cards': [], 'rules': [rule]})['rules'][0]['issues']
        self.assertIn('AMBIGUOUS_PERCENT_AND_FIXED_POINT_REWARD', issues)
        rule['fixedAwardEvidence'] = {'sourceUrl': url, 'locator': 'official section 2'}
        issues = audit({'cards': [], 'rules': [rule]})['rules'][0]['issues']
        self.assertNotIn('AMBIGUOUS_PERCENT_AND_FIXED_POINT_REWARD', issues)
        rule.pop('fixedAwardEvidence')
        rule['rewardUnit'] = 'percent'
        issues = audit({'cards': [], 'rules': [rule]})['rules'][0]['issues']
        self.assertNotIn('AMBIGUOUS_PERCENT_AND_FIXED_POINT_REWARD', issues)

    def test_nonregistration_promo_link_is_flagged_for_review(self):
        rule = {'id': 'r', 'sourceUrl': 'https://bank.test/offer', 'needReg': False,
                'registrationUrl': 'https://merchant.test/shop'}
        report = audit({'cards': [], 'rules': [rule]})
        self.assertIn('REGISTRATION_LINK_WITHOUT_REGISTRATION_REQUIREMENT', report['rules'][0]['issues'])
        rule['registrationUrl'] = ''
        self.assertNotIn('REGISTRATION_LINK_WITHOUT_REGISTRATION_REQUIREMENT',
                         audit({'cards': [], 'rules': [rule]})['rules'][0]['issues'])

    def test_validation_conflicts_are_visible_in_report(self):
        data = {'cards': [], 'rules': [{'id': 'r', 'sourceUrl': 'https://bank.test/offer',
                'validationIssues': ['OFFICIAL_CAP_PERIOD_CONFLICT']}]}
        report = audit(data)
        self.assertIn('VALIDATION_OFFICIAL_CAP_PERIOD_CONFLICT', report['rules'][0]['issues'])
        self.assertEqual(report['issueCounts']['VALIDATION_OFFICIAL_CAP_PERIOD_CONFLICT'], 1)

    def test_generic_network_card_and_invalid_eligible_card_ids_are_flagged(self):
        cards = [{'id': 'card_中國信託_51'}, {'id': 'card_中國信託_241'},
                 {'id': 'card_中國信託_328'}]
        rule = {'id': 'r', 'cardId': 'card_中國信託_51',
                'fundingMethods': ['中國信託 LINE Pay Visa 卡'],
                'eligibleCardIds': ['card_中國信託_241', 'missing-card']}
        issues = audit({'cards': cards, 'rules': [rule]})['rules'][0]['issues']
        self.assertIn('GENERIC_CARD_FOR_NETWORK_SPECIFIC_OFFER', issues)
        self.assertIn('INVALID_ELIGIBLE_CARD_IDS', issues)
        rule['cardId'] = 'card_中國信託_241'
        rule['eligibleCardIds'] = ['card_中國信託_241', 'card_中國信託_328']
        issues = audit({'cards': cards, 'rules': [rule]})['rules'][0]['issues']
        self.assertNotIn('GENERIC_CARD_FOR_NETWORK_SPECIFIC_OFFER', issues)
        self.assertNotIn('INVALID_ELIGIBLE_CARD_IDS', issues)


if __name__ == '__main__':
    unittest.main()
