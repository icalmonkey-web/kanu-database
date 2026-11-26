import unittest
from datetime import datetime, timedelta, timezone

from verify_source_titles import due_urls, fingerprint, inspect_title


class SourceTitleTests(unittest.TestCase):
    def test_static_html_absence_does_not_claim_invalid_offer(self):
        self.assertEqual(inspect_title({'title': '指定通路加碼優惠'}, '其他活動'),
                         'TITLE_NOT_FOUND_IN_STATIC_HTML')

    def test_changed_claim_is_rechecked_even_when_recent(self):
        now = datetime.now(timezone.utc)
        url = 'https://bank.example/offer'
        old = [{'id': 'a', 'title': '舊活動標題'}]
        new = [{'id': 'a', 'title': '新活動標題'}]
        state = {'pages': {url: {'checkedAt': now.isoformat(), 'fingerprint': fingerprint(old)}}}
        self.assertEqual(due_urls({url: new}, state, now, 10), [url])

    def test_unchanged_claim_expires_after_seven_days(self):
        now = datetime.now(timezone.utc)
        url = 'https://bank.example/offer'
        rules = [{'id': 'a', 'title': '活動標題'}]
        state = {'pages': {url: {'checkedAt': (now - timedelta(days=8)).isoformat(),
                               'fingerprint': fingerprint(rules), 'claims': []}}}
        self.assertEqual(due_urls({url: rules}, state, now, 10), [url])
        state['pages'][url]['checkedAt'] = now.isoformat()
        self.assertEqual(due_urls({url: rules}, state, now, 10), [])


if __name__ == '__main__':
    unittest.main()
