import unittest
from fast_update import summarize_reports


class ScanSummaryTests(unittest.TestCase):
    def test_one_incomplete_bank_prevents_completed_summary(self):
        reports = [
            {'status': 'completed', 'pages': [{'status': 'analyzed'}], 'unvisited': []},
            {'status': 'needs_review', 'pages': [{'status': 'fetch_failed'}],
             'unvisited': [{'reason': 'page_limit'}]},
        ]
        result = summarize_reports(reports, ai_requests=4)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['needsReview'], 1)
        self.assertEqual(result['pageGaps'], {'fetch_failed': 1, 'page_limit': 1})

    def test_pdf_or_redirect_gap_prevents_completed_summary(self):
        reports = [{'status': 'completed', 'pages': [{'status': 'needs_pdf_parser'},
                   {'status': 'redirect_outside_allowlist'}], 'unvisited': []}]
        self.assertEqual(summarize_reports(reports)['status'], 'partial')


if __name__ == '__main__':
    unittest.main()
