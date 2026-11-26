import unittest
from update_data import merge_data, enrich_reward_fields, source_claim_issues

class MergeTests(unittest.TestCase):
    def test_ambiguous_percentage_points_are_quarantined_idempotently(self):
        rule = {'rewardType': 'points', 'rewardUnit': 'LINE POINTS',
                'baseRate': 1, 'promoRate': 4, 'rewardAmount': 100,
                'capAmount': 100, 'quickSearchEligible': True,
                'sourceUrl': 'https://bank.test/offer'}
        for _ in range(3):
            rule = enrich_reward_fields(rule, rule['sourceUrl'])
        self.assertEqual(rule['validationIssues'].count('AMBIGUOUS_PERCENT_AND_FIXED_POINT_REWARD'), 1)
        self.assertFalse(rule['quickSearchEligible'])

    def test_unequal_point_amount_is_quarantined_but_percent_unit_is_not(self):
        url = 'https://bank.test/offer'
        rule = {'rewardType': 'points', 'rewardUnit': 'points', 'promoRate': 5,
                'rewardAmount': 20, 'capAmount': 100, 'sourceUrl': url}
        enrich_reward_fields(rule, url)
        self.assertIn('AMBIGUOUS_PERCENT_AND_FIXED_POINT_REWARD', rule['validationIssues'])
        percent_rule = {'rewardType': 'points', 'rewardUnit': 'percent',
                        'promoRate': 5, 'rewardAmount': 5, 'sourceUrl': url}
        enrich_reward_fields(percent_rule, url)
        self.assertNotIn('AMBIGUOUS_PERCENT_AND_FIXED_POINT_REWARD', percent_rule.get('validationIssues', []))

    def test_sourced_fixed_point_award_keeps_its_amount(self):
        url = 'https://bank.test/offer'
        rule = {'rewardType': 'points', 'baseRate': 1, 'promoRate': 0,
                'rewardAmount': 1000, 'capAmount': 1000,
                'sourceUrl': url,
                'fixedAwardEvidence': {'sourceUrl': url, 'locator': 'official terms section 2'}}
        rule = enrich_reward_fields(rule, url)
        self.assertEqual(rule['rewardAmount'], 1000)
        self.assertNotIn('AMBIGUOUS_PERCENT_AND_FIXED_POINT_REWARD', rule.get('validationIssues', []))

    def test_changed_page_preserves_curated_schedule_and_captures_ai_candidate(self):
        url = 'https://bank.test/list'
        key = 'None_指定週二活動_' + url
        old = {'bank': 'bank', 'title': '指定週二活動', 'sourceUrl': url,
               'eligibleWeekdays': [2], 'capPeriod': 'WEEKLY', 'promoRate': 5,
               'sourceFacts': {'sourceUrl': url, 'locators': {'schedule': 'L12'}},
               'quickSearchEligible': True}
        rules = {key: old}
        merge_data('bank', {'rules': [{'title': '指定週二活動', 'eligibleWeekdays': [3],
                                     'capPeriod': 'MONTHLY', 'promoRate': 8}]},
                   {}, rules, url, '指定週二活動 週三最高8%')
        self.assertIs(rules[key], old)
        self.assertEqual(old['eligibleWeekdays'], [2])
        self.assertEqual(old['capPeriod'], 'WEEKLY')
        self.assertEqual(old['promoRate'], 5)
        self.assertFalse(old['quickSearchEligible'])
        self.assertIn('SOURCE_CHANGED_AFTER_CURATED_SNAPSHOT', old['validationIssues'])
        self.assertEqual(old['sourceRecheckCandidate']['fields']['eligibleWeekdays'], [3])
        self.assertEqual(old['sourceRecheckCandidate']['fields']['capPeriod'], 'MONTHLY')

    def test_missing_page_text_fails_closed(self):
        rules = {}
        merge_data('bank', {'rules': [{'title': '網購最高8%回饋', 'promoRate': 8,
                                     'quickSearchEligible': True}]}, {}, rules,
                   'https://bank.test/offer')
        rule = next(iter(rules.values()))
        self.assertIn('SOURCE_PAGE_TEXT_UNAVAILABLE', rule['validationIssues'])
        self.assertIn('SOURCE_CLAIM_UNCONFIRMED', rule['validationIssues'])
        self.assertFalse(rule['quickSearchEligible'])

    def test_ai_claim_missing_from_rendered_page_is_quarantined(self):
        rules = {}
        merge_data('bank', {'rules': [{'title': '網購最高8%回饋', 'promoRate': 8,
                                     'quickSearchEligible': True}]}, {}, rules,
                   'https://bank.test/offer', '網購最高 3% 回饋')
        rule = next(iter(rules.values()))
        self.assertIn('SOURCE_RATE_UNCONFIRMED', rule['validationIssues'])
        self.assertFalse(rule['quickSearchEligible'])

    def test_matching_headline_is_still_not_reviewed(self):
        rules = {}
        merge_data('bank', {'rules': [{'title': '指定網購最高3%回饋', 'promoRate': 3}]}, {}, rules,
                   'https://bank.test/offer', '指定網購最高 3% 回饋')
        rule = next(iter(rules.values()))
        self.assertEqual(rule['sourceClaimStatus'], 'TITLE_AND_RATES_PRESENT_NOT_TERM_REVIEWED')
        self.assertNotIn('accuracyReview', rule)

    def test_changed_page_revokes_prior_review_instead_of_silent_reference(self):
        url = 'https://bank.test/offer'
        key = 'None_指定網購最高3%回饋_' + url
        rules = {key: {'title': '指定網購最高3%回饋', 'sourceUrl': url,
                       'accuracyReview': {'status': 'SOURCE_CHECKED', 'checkedAt': '2026-11-01'}}}
        merge_data('bank', {'rules': [{'title': '指定網購最高3%回饋', 'promoRate': 3}]},
                   {}, rules, url, '指定網購最高 3% 回饋，條款已更新')
        rule = rules[key]
        self.assertEqual(rule['accuracyReview']['status'], 'RECHECK_REQUIRED')
        self.assertFalse(rule['quickSearchEligible'])
        self.assertIn('SOURCE_CHANGED_AFTER_REVIEW', rule['validationIssues'])
        self.assertIn('promoRate', rule['accuracyReview']['changedFields'])
        self.assertIsNone(rule['accuracyReview']['reviewedValues']['promoRate'])

    def test_recheck_retains_original_reviewed_values(self):
        url = 'https://bank.test/offer'
        key = 'None_指定網購回饋_' + url
        rules = {key: {'title': '指定網購回饋', 'sourceUrl': url,
                       'promoRate': 3, 'accuracyReview': {
                           'status': 'SOURCE_CHECKED', 'checkedAt': '2026-11-01'}}}
        for rate in (4, 5):
            merge_data('bank', {'rules': [{'title': '指定網購回饋', 'promoRate': rate}]},
                       {}, rules, url, f'指定網購回饋最高{rate}%')
        review = rules[key]['accuracyReview']
        self.assertEqual(review['reviewedValues']['promoRate'], 3)
        self.assertIn('promoRate', review['changedFields'])
        self.assertFalse(rules[key]['quickSearchEligible'])

    def test_points_without_cash_value_do_not_turn_into_percent_cash(self):
        rule = enrich_reward_fields({'rewardType':'points','rewardUnit':'points',
                                     'rewardAmount':0,'baseRate':1,'promoRate':2},'https://bank.test/offer')
        self.assertEqual(rule['rewardType'],'points')

    def test_percentage_points_keep_reward_semantics_across_refreshes(self):
        rule = {'rewardType': 'points', 'rewardUnit': 'percent',
                'rewardAmount': None, 'baseRate': 0.5, 'promoRate': 5,
                'capAmount': 150, 'sourceUrl': 'https://bank.test/offer'}
        for _ in range(2):
            rule = enrich_reward_fields(rule, rule['sourceUrl'])
        self.assertEqual(rule['rewardType'], 'points')
        self.assertEqual(rule['rewardUnit'], 'percent')
        self.assertIsNone(rule['rewardAmount'])
        self.assertEqual(rule['capAmount'], 150)

    def test_insurance_issue_is_not_duplicated_on_refresh(self):
        rule = {'title': '旅遊平安險保障額度 319 萬',
                'validationIssues': ['NOT_SPENDING_REWARD', 'NOT_SPENDING_REWARD']}
        for _ in range(3):
            rule = enrich_reward_fields(rule, 'https://bank.test/insurance')
        self.assertEqual(rule['validationIssues'].count('NOT_SPENDING_REWARD'), 1)
        self.assertFalse(rule['quickSearchEligible'])

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

    def test_existing_card_gets_official_image_without_changing_id(self):
        cards = {}
        base_card = {
            'cardName': 'Test卡', 'entityType': 'CARD_PRODUCT',
            'classificationConfidence': .95, 'classificationEvidence': '官方產品頁'
        }
        merge_data('bank', {'cards': [{**base_card, 'id': 'first', 'imageUrl': ''}], 'rules': []},
                   cards, {}, 'https://bank.test/card')
        original_id = next(iter(cards.values()))['id']
        merge_data('bank', {'cards': [{
            **base_card, 'id': 'second', 'imageUrl': 'https://bank.test/assets/test-card.png'
        }], 'rules': []}, cards, {}, 'https://bank.test/card')
        card = next(iter(cards.values()))
        self.assertEqual(card['id'], original_id)
        self.assertEqual(card['imageUrl'], 'https://bank.test/assets/test-card.png')

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

    def test_list_page_cannot_borrow_another_campaign_rate(self):
        from update_data import source_claim_issues
        rule = {'title': '活動甲網路消費優惠', 'promoRate': 8}
        text = '活動甲網路消費優惠，詳細條款請見活動頁。' + '其他活動說明。' * 80 + '活動乙指定通路最高8%回饋。'
        self.assertIn('SOURCE_RATE_UNCONFIRMED', source_claim_issues(rule, text))
        self.assertEqual(source_claim_issues(rule, '活動甲網路消費優惠，最高8%回饋。'), [])

    def test_registration_link_evidence_must_come_from_observed_anchor(self):
        source = 'https://bank.example/offer'
        rule = {'title': '指定通路回饋活動', 'registrationUrl': 'https://bank.example/register',
                'registrationLinkEvidence': {'method': 'observed_page_anchor', 'urls': ['https://evil.example']}}
        rules = {}
        merge_data('甲銀行', {'rules': [rule]}, {}, rules, source,
                   '指定通路回饋活動', [('https://bank.example/register', '立即登錄')])
        evidence = next(iter(rules.values()))['registrationLinkEvidence']
        self.assertEqual(evidence['urls'], ['https://bank.example/register'])
        rules = {}
        merge_data('甲銀行', {'rules': [dict(rule)]}, {}, rules, source, '指定通路回饋活動', [])
        self.assertNotIn('registrationLinkEvidence', next(iter(rules.values())))

    def test_machine_source_locators_are_candidates_not_official_review(self):
        from update_data import source_claim_evidence
        rule = {'title': '指定網購消費活動', 'promoRate': 3, 'baseRate': 0}
        found = source_claim_evidence(rule, '指定網購消費活動最高3%回饋',
                                      'https://bank.test/offer', '2026-11-02T00:00:00Z')
        self.assertEqual(found['fields']['title']['status'], 'candidate_present')
        self.assertEqual(found['fields']['promoRate']['status'], 'candidate_present')
        self.assertEqual(found['fields']['baseRate']['status'], 'not_reviewed')
        self.assertNotIn('supported', str(found))
        missing = source_claim_evidence(rule, None, 'https://bank.test/offer', 'now')
        self.assertEqual(missing['fields']['title']['status'], 'source_unavailable')

    def test_official_quarterly_cap_conflict_stops_recommendation(self):
        source = 'https://bank.test/offer'
        cards = {'c': {'id': 'card1', 'bank': 'bank', 'cardName': 'Test卡'}}
        previous = {'cardId': 'card1', 'title': '餐飲優惠', 'sourceUrl': source,
                    'capPeriod': 'QUARTERLY', 'registrationCycle': 'QUARTERLY',
                    'capEvidence': {'sourceUrl': source, 'locator': '第3點'}}
        rules = {'card1_餐飲優惠_' + source: previous}
        merge_data('bank', {'rules': [{'cardId': 'card1', 'title': '餐飲優惠',
                                     'capPeriod': 'MONTHLY'}]}, cards, rules, source)
        merged = next(iter(rules.values()))
        self.assertIn('OFFICIAL_CAP_PERIOD_CONFLICT', merged['validationIssues'])
        self.assertFalse(merged['quickSearchEligible'])

        rules = {'card1_餐飲優惠_' + source: previous}
        merge_data('bank', {'rules': [{'cardId': 'card1', 'title': '餐飲優惠',
                                     'capPeriod': 'QUARTERLY'}]}, cards, rules, source)
        merged = next(iter(rules.values()))
        self.assertEqual(merged['registrationCycle'], 'QUARTERLY')
        self.assertEqual(merged['capEvidence']['locator'], '第3點')

if __name__ == '__main__':
    unittest.main()
