import unittest
from datetime import datetime, timezone

from build_field_evidence_queue import build_queue, fresh_field_evidence


class FieldEvidenceQueueTests(unittest.TestCase):
    def test_machine_candidate_does_not_count_as_reviewed_field(self):
        now = datetime(2026, 11, 2, tzinfo=timezone.utc)
        rule = {'id': 'one', 'title': '活動', 'sourceUrl': 'https://bank.test/offer',
                'validFrom': '2026-11-01', 'validUntil': '2026-11-30',
                'sourceClaimEvidence': {'fields': {'title': {'status': 'candidate_present'}}}}
        row = build_queue({'rules': [rule]}, now=now)['queue'][0]
        self.assertEqual(row['supportedFieldCount'], 0)
        self.assertEqual(row['machineCandidateFields'], ['title'])
        self.assertEqual(row['dateBucket'], 'DATE_WINDOW_INCLUDES_TODAY')

    def test_expired_or_wrong_source_evidence_is_rejected(self):
        now = datetime(2026, 11, 2, tzinfo=timezone.utc)
        rule = {'sourceUrl': 'https://bank.test/new', 'termEvidence': {
            'sourceUrl': 'https://bank.test/old', 'checkedAt': now.isoformat(),
            'fields': {'title': {'status': 'supported', 'sourceUrl': 'https://bank.test/old',
                                 'locator': 'section 1'}}}}
        self.assertEqual(fresh_field_evidence(rule, now), set())


if __name__ == '__main__':
    unittest.main()
