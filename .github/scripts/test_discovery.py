import unittest
from discovery import canonical, allowed, explore

class Body:
    def inner_text(self, **kwargs):
        return '信用卡活動內容' * 50

class Button:
    def count(self):
        return 0

class Page:
    def __init__(self):
        self.url = ''
        self.frames = [self]
    def goto(self, url, **kwargs):
        self.url = url
        return type('Response', (), {'status': 200})()
    def wait_for_timeout(self, ms):
        pass
    def locator(self, selector):
        return Body()
    def evaluate(self, script):
        pass
    def get_by_role(self, *args, **kwargs):
        return Button()
    def eval_on_selector_all(self, *args):
        links = {'https://bank.test/cards': ['/card/list'],
                 'https://bank.test/card/list': ['/card/detail', '/card/terms.pdf', 'https://other.test/card/promo'],
                 'https://bank.test/card/detail': ['/cards']}
        return [{'href': u, 'text': '信用卡優惠'} for u in links.get(self.url, [])]

class DiscoveryTests(unittest.TestCase):
    def test_canonical_and_host_safety(self):
        self.assertEqual(canonical('https://bank.test/card/', '../x?utm_source=a&page=2#top'), 'https://bank.test/x?page=2')
        self.assertIsNone(canonical('https://bank.test/', 'javascript:alert(1)'))
        self.assertIsNone(canonical('https://bank.test/', 'https://user:pass@bank.test/'))
        self.assertFalse(allowed('https://bank.test.evil.test/', {'bank.test'}))

    def test_recursive_discovery_analyzes_entry_and_flags_pdf(self):
        visited = []
        report = explore(Page(), {'bank': 'test', 'card_urls': ['https://bank.test/cards']},
                         lambda u, t: visited.append(u) or 'analyzed')
        self.assertEqual(len(visited), 3)
        self.assertEqual(len(report['pages']), 4)
        self.assertIn('needs_pdf_parser', [p['status'] for p in report['pages']])
        self.assertEqual(report['externalCandidates'], ['https://other.test/card/promo'])
        self.assertIsNone(report['coveragePercent'])

    def test_budget_is_reported_not_silently_dropped(self):
        report = explore(Page(), {'bank': 'test', 'card_urls': ['https://bank.test/cards']},
                         lambda u, t: 'analyzed', max_pages=1)
        self.assertEqual(report['unvisited'][0]['reason'], 'page_limit')
        self.assertEqual(report['status'], 'needs_review')

if __name__ == '__main__':
    unittest.main()
