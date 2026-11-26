import unittest

from probe_official_catalog import inspect, listing_text


class OfficialCatalogProbeTests(unittest.TestCase):
    CATALOG = {'catalogId': 'test', 'offers': [
        {'id': 'a', 'matchToken': '商店甲', 'validFrom': '2026-07-01', 'validUntil': '2026-12-31'},
        {'id': 'b', 'matchToken': '商店乙', 'validFrom': '2026-08-01', 'validUntil': '2026-12-31'}]}

    def test_known_listing_and_dates_present(self):
        html = '<body>商店甲 2026/7/1~2026/12/31 活動詳情 商店乙 2026/8/1~2026/12/31 活動詳情 謹慎理財</body>'
        # Real CTBC pages use both padded and unpadded dates; this fixture
        # intentionally checks the latter.
        self.assertEqual(inspect(self.CATALOG, html)['status'], 'KNOWN_ENTRIES_PRESENT')

    def test_hidden_detail_after_footer_does_not_rescue_missing_listing(self):
        html = '<body>商店甲 2026/7/1~2026/12/31 活動詳情 謹慎理財 商店乙 2026/8/1~2026/12/31 活動詳情</body>'
        result = inspect(self.CATALOG, html)
        self.assertIn('b', result['missingKnownOffers'])
        self.assertNotEqual(result['status'], 'KNOWN_ENTRIES_PRESENT')

    def test_changed_date_is_reported(self):
        html = '<body>商店甲 2026/7/1~2026/12/31 活動詳情 商店乙 2026/8/1~2027/3/31 活動詳情 謹慎理財</body>'
        self.assertIn('b', inspect(self.CATALOG, html)['changedDateOffers'])

    def test_page_without_boundary_is_unverified(self):
        html = '<body><script>商店甲 活動詳情 謹慎理財</script>商店甲 2026/7/1~2026/12/31 活動詳情</body>'
        self.assertEqual(listing_text(html)[1], False)
        self.assertEqual(inspect(self.CATALOG, html)['status'], 'UNVERIFIED_LAYOUT')

    def test_detail_only_subplan_does_not_create_false_listing_drift(self):
        catalog = {**self.CATALOG, 'offers': [*self.CATALOG['offers'],
            {'id': 'detail', 'matchToken': '隱藏方案', 'validFrom': '2026-01-01',
             'validUntil': '2026-12-31', 'detailOnly': True}]}
        html = '<body>商店甲 2026/7/1~2026/12/31 活動詳情 商店乙 2026/8/1~2026/12/31 活動詳情 謹慎理財 隱藏方案</body>'
        result = inspect(catalog, html)
        self.assertEqual(result['status'], 'KNOWN_ENTRIES_PRESENT')
        self.assertEqual(result['knownOfferCount'], 2)

    def test_listing_only_action_does_not_require_detail_button(self):
        catalog = {**self.CATALOG, 'offers': [*self.CATALOG['offers'],
            {'id': 'c', 'matchToken': '商店丙', 'validFrom': '2026-10-01',
             'validUntil': '2026-12-31', 'listingActionOnly': True}]}
        html = ('商店甲 2026/7/1~2026/12/31 活動詳情 '
                '商店乙 2026/8/1~2026/12/31 活動詳情 '
                '商店丙 2026/10/1~2026/12/31 立即前往 謹慎理財')
        result = inspect(catalog, html)
        self.assertEqual(result['expectedDetailLabels'], 2)
        self.assertEqual(result['status'], 'KNOWN_ENTRIES_PRESENT')


if __name__ == '__main__':
    unittest.main()
