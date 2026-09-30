import unittest
from audit_accuracy import audit
from repair_accuracy import repair

class AccuracyTests(unittest.TestCase):
    def test_ai_verified_does_not_count_as_independent_review(self):
        r = audit({'cards': [], 'rules': [{'id': 'x', 'evidenceStatus': 'VERIFIED'}]})
        self.assertIsNone(r['measuredAccuracy'])
        self.assertIn('NO_INDEPENDENT_TERM_REVIEW', r['rules'][0]['issues'])

    def test_repair_is_idempotent_and_preserves_ambiguous_records(self):
        data = {'cards': [], 'rules': [{'id': 'x', 'cardId': 'missing'}, {'id': 'x'}]}
        self.assertEqual(repair(data), {'renamedDuplicateIds': 1, 'quarantinedOrphanLinks': 1})
        self.assertEqual(repair(data), {'renamedDuplicateIds': 0, 'quarantinedOrphanLinks': 0})
        self.assertEqual(len(data['rules']), 2)
        self.assertEqual(data['rules'][0]['unresolvedCardId'], 'missing')
        self.assertFalse(data['rules'][0]['quickSearchEligible'])
