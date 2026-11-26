import unittest
import json
from pathlib import Path

from evaluate_official_catalog import evaluate


class OfficialCatalogTests(unittest.TestCase):
    def test_ctbc_pet_listing_tracks_all_twelve_entries_safely(self):
        root = Path(__file__).resolve().parents[2]
        catalog = json.loads((root / 'official_catalogs/ctbc_linepay_pet_2026.json').read_text(encoding='utf-8'))
        mapping = json.loads((root / 'official_catalogs/ctbc_linepay_pet_2026_mapping.json').read_text(encoding='utf-8'))
        data = json.loads((root / 'data.json').read_text(encoding='utf-8'))
        report = evaluate(catalog, mapping, data)
        self.assertEqual((report['officialOffers'], report['matchedRecords'],
                          report['candidateRecords'], report['missingRecords']), (12, 12, 0, 0))
        pending = [r for r in data['rules'] if r['id'].startswith('pending_ctbc_linepay_pet_2026_')]
        self.assertEqual(len(pending), 5)
        for rule in pending:
            self.assertFalse(rule['quickSearchEligible'])
        listing_only = [r for r in pending if 'LISTING_ONLY_TERMS_UNVERIFIED' in r['validationIssues']]
        self.assertEqual(len(listing_only), 0)
        for rule in listing_only:
            self.assertEqual(rule['rewardType'], 'unknown')
            self.assertEqual(rule['eligibleCardScope'], 'UNKNOWN')
        for rule in pending:
            if rule['id'] not in ('pending_ctbc_linepay_pet_2026_maohao',
                                  'pending_ctbc_linepay_pet_2026_petlife'):
                self.assertEqual(len(rule['termEvidence']['fields']), 11)
        maohao = next(r for r in pending if r['id'] == 'pending_ctbc_linepay_pet_2026_maohao')
        self.assertEqual(len(maohao['termEvidence']['fields']), 8)
        petlife = next(r for r in pending if r['id'] == 'pending_ctbc_linepay_pet_2026_petlife')
        self.assertEqual(len(petlife['termEvidence']['fields']), 7)
        self.assertEqual(petlife['bank'], 'LINE Pay')

    def test_ctbc_fashion_listing_candidates_are_present_but_not_approved(self):
        root = Path(__file__).resolve().parents[2]
        catalog = json.loads((root / 'official_catalogs/ctbc_linepay_fashion_2026.json').read_text(encoding='utf-8'))
        mapping = json.loads((root / 'official_catalogs/ctbc_linepay_fashion_2026_mapping.json').read_text(encoding='utf-8'))
        data = json.loads((root / 'data.json').read_text(encoding='utf-8'))
        report = evaluate(catalog, mapping, data)
        self.assertEqual((report['officialOffers'], report['matchedRecords'],
                          report['candidateRecords'], report['missingRecords']), (25, 4, 21, 0))
        candidates = {row['id']: row for row in data['rules']
                      if row['id'].startswith('pending_ctbc_linepay_fashion_2026_')}
        self.assertEqual(len(candidates), 21)
        for rule in candidates.values():
            self.assertFalse(rule['quickSearchEligible'])
            self.assertEqual(rule['rewardType'], 'unknown')
            self.assertEqual(rule['eligibleCardScope'], 'UNKNOWN')
            self.assertIn('LISTING_ONLY_TERMS_UNVERIFIED', rule['validationIssues'])

    def test_ctbc_life_inventory_exposes_missing_november_offers(self):
        root = Path(__file__).resolve().parents[2]
        catalog = json.loads((root / 'official_catalogs/ctbc_linepay_life_2026.json').read_text(encoding='utf-8'))
        mapping = json.loads((root / 'official_catalogs/ctbc_linepay_life_2026_mapping.json').read_text(encoding='utf-8'))
        data = json.loads((root / 'data.json').read_text(encoding='utf-8'))
        report = evaluate(catalog, mapping, data)
        self.assertEqual(report['officialOffers'], 31)
        self.assertEqual(report['matchedRecords'] + report['candidateRecords'] + report['missingRecords'], 31)
        self.assertIn('adidas_nov', {row['offerId'] for row in report['rows']})
        self.assertIn('greattree', {row['offerId'] for row in report['rows']})

    def test_ctbc_travel_inventory_keeps_kkday_subplans_separate(self):
        root = Path(__file__).resolve().parents[2]
        catalog = json.loads((root / 'official_catalogs/ctbc_linepay_travel_2026.json').read_text(encoding='utf-8'))
        mapping = json.loads((root / 'official_catalogs/ctbc_linepay_travel_2026_mapping.json').read_text(encoding='utf-8'))
        data = json.loads((root / 'data.json').read_text(encoding='utf-8'))
        report = evaluate(catalog, mapping, data)
        self.assertEqual(len([o for o in catalog['offers'] if not o.get('detailOnly')]), 28)
        self.assertEqual(report['officialOffers'], 29)
        ids = {row['offerId'] for row in report['rows']}
        self.assertIn('kkday_member_day', ids)
        self.assertIn('kkday_weekly', ids)

    def test_missing_and_partial_records_do_not_count_as_presence(self):
        catalog = {'catalogId': 'test', 'scope': 'one page', 'observedAt': '2026-11-02',
                   'sourceUrl': 'https://bank.test/page', 'offers': [
                       {'id': 'a', 'name': 'A', 'matchToken': 'A', 'channel': 'CARD', 'sourceLineHint': 1,
                        'validFrom': '2026-01-01', 'validUntil': '2026-12-31'},
                       {'id': 'b', 'name': 'B', 'matchToken': 'B', 'channel': 'CARD', 'sourceLineHint': 2,
                        'validFrom': '2026-01-01', 'validUntil': '2026-12-31'}]}
        mapping = {'catalogId': 'test', 'mappings': [{'offerId': 'a', 'ruleId': 'r',
                                                   'status': 'matched'}]}
        data = {'rules': [{'id': 'r', 'sourceUrl': 'https://bank.test/other',
                           'validFrom': '2026-01-01', 'validUntil': '2026-12-31'}]}
        report = evaluate(catalog, mapping, data)
        self.assertEqual((report['matchedRecords'], report['candidateRecords'],
                          report['missingRecords']), (0, 1, 1))
        self.assertIsNone(report['marketCoveragePercent'])
        self.assertIsNone(report['fullTermsVerifiedPercent'])

    def test_multi_part_activity_needs_every_mapped_part(self):
        catalog = {'catalogId': 'test', 'scope': 'one page', 'observedAt': '2026-11-02',
                   'sourceUrl': 'https://bank.test/page', 'offers': [
                       {'id': 'food', 'name': 'foodpanda', 'matchToken': 'foodpanda',
                        'channel': 'CARD', 'sourceLineHint': 1,
                        'validFrom': '2026-01-01', 'validUntil': '2026-12-31'}]}
        mapping = {'catalogId': 'test', 'mappings': [{'offerId': 'food',
                   'ruleIds': ['first', 'second'], 'status': 'matched'}]}
        first = {'id': 'first', 'title': 'foodpanda first',
                 'sourceUrl': 'https://bank.test/page',
                 'validFrom': '2026-01-01', 'validUntil': '2026-12-31'}
        self.assertEqual(evaluate(catalog, mapping, {'rules': [first]})['matchedRecords'], 0)
        self.assertEqual(evaluate(catalog, mapping, {'rules': [first]})['candidateRecords'], 1)
        partial = evaluate(catalog, mapping, {'rules': [first]})['rows'][0]
        self.assertEqual(partial['missingRuleIds'], ['second'])
        second = {**first, 'id': 'second', 'title': 'foodpanda second'}
        self.assertEqual(evaluate(catalog, mapping, {'rules': [first, second]})['matchedRecords'], 1)

    def test_mapping_alone_does_not_count_as_candidate_record(self):
        catalog = {'catalogId': 'test', 'scope': 'one page', 'observedAt': '2026-11-02',
                   'sourceUrl': 'https://bank.test/page', 'offers': [
                       {'id': 'one', 'name': 'A', 'matchToken': 'A', 'channel': 'CARD',
                        'sourceLineHint': 1, 'validFrom': '2026-01-01',
                        'validUntil': '2026-12-31'}]}
        mapping = {'catalogId': 'test', 'mappings': [
            {'offerId': 'one', 'ruleId': 'deleted_rule', 'status': 'candidate'}]}
        report = evaluate(catalog, mapping, {'rules': []})
        self.assertEqual((report['matchedRecords'], report['candidateRecords'],
                          report['missingRecords']), (0, 0, 1))
        self.assertEqual(report['rows'][0]['missingRuleIds'], ['deleted_rule'])

    def test_official_detail_page_is_valid_catalog_evidence(self):
        catalog = {'catalogId': 'test', 'scope': 'one page', 'observedAt': '2026-11-03',
                   'sourceUrl': 'https://bank.test/list', 'offers': [
                       {'id': 'one', 'name': 'LOPIA', 'matchToken': 'LOPIA', 'channel': 'LINE_PAY',
                        'sourceLineHint': 10, 'detailUrl': 'https://pay.test/detail',
                        'validFrom': '2026-10-01', 'validUntil': '2026-12-31'}]}
        mapping = {'catalogId': 'test', 'mappings': [
            {'offerId': 'one', 'ruleId': 'r', 'status': 'matched'}]}
        data = {'rules': [{'id': 'r', 'title': 'LOPIA', 'sourceUrl': 'https://pay.test/detail',
                          'validFrom': '2026-10-01', 'validUntil': '2026-12-31'}]}
        self.assertEqual(evaluate(catalog, mapping, data)['matchedRecords'], 1)


if __name__ == '__main__':
    unittest.main()
