import json
import tempfile
import unittest
from pathlib import Path

import fast_update
from fast_update import atomic_json, normalized_content, parse_html, stable_hash


class FastPipelineTests(unittest.TestCase):
    def test_time_budget_is_shorter_than_workflow_timeout(self):
        self.assertLess(fast_update.CRAWL_BUDGET_SECONDS, 90 * 60)

    def test_ai_audit_removes_non_cards_and_unlinks_their_rules(self):
        old = {
            "cards": [
                {"id": "real", "bank": "銀行", "cardName": "真卡"},
                {"id": "audience", "bank": "銀行", "cardName": "全卡友"},
            ],
            "rules": [{"cardId": "audience", "title": "活動", "sourceUrl": "https://bank.test/promo"}],
        }
        cards, rules = fast_update.old_maps(old, {"real"})
        self.assertEqual([card["id"] for card in cards.values()], ["real"])
        self.assertIsNone(next(iter(rules.values()))["cardId"])
        self.assertEqual(next(iter(rules.values()))["associationStatus"], "needs_review")

    def test_dynamic_time_and_cookie_noise_do_not_change_hash(self):
        first = "優惠活動 更新 2026-09-24 10:21:33 Cookie 隱私權政策，請接受\n回饋 5%"
        second = "優惠活動 更新 2026-09-24 11:59:02 Cookie 隱私權政策，請接受\n回饋 5%"
        self.assertEqual(stable_hash(first), stable_hash(second))

    def test_actual_reward_change_changes_hash(self):
        self.assertNotEqual(stable_hash("指定消費回饋 3%"), stable_hash("指定消費回饋 5%"))

    def test_parser_ignores_script_and_extracts_links(self):
        text, links = parse_html('<script>fake card</script><main>信用卡 5%</main><a href="/promo">活動</a>')
        self.assertNotIn("fake card", text)
        self.assertIn("信用卡 5%", text)
        self.assertEqual(links, [("/promo", "活動")])

    def test_atomic_json_never_leaves_partial_file(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "checkpoint.json"
            atomic_json(target, {"bank": "測試銀行", "rules": [1, 2]})
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["rules"], [1, 2])
            self.assertEqual(list(Path(folder).glob("*.tmp")), [])

    def test_only_newer_checkpoint_is_restored(self):
        with tempfile.TemporaryDirectory() as folder:
            previous = fast_update.CHECKPOINT_DIR
            fast_update.CHECKPOINT_DIR = Path(folder)
            try:
                atomic_json(Path(folder) / "new.json", {
                    "bank": "測試銀行", "savedAt": "2026-09-24T12:00:00Z",
                    "cards": [{"id": "c1", "bank": "測試銀行", "cardName": "測試卡"}],
                    "rules": [{"id": "r1", "cardId": "c1", "title": "新活動", "sourceUrl": "https://bank.test/new"}],
                    "pages": {"https://bank.test/new": {"bank": "測試銀行", "hash": "abc"}}
                })
                cards, rules, state = {}, {}, {"pages": {}}
                count = fast_update.restore_newer_checkpoints(
                    {"lastUpdated": "2026-09-24T10:00:00Z"}, state, cards, rules)
                self.assertEqual(count, 1)
                self.assertEqual(next(iter(cards.values()))["cardName"], "測試卡")
                self.assertEqual(next(iter(rules.values()))["title"], "新活動")
                self.assertIn("https://bank.test/new", state["pages"])
            finally:
                fast_update.CHECKPOINT_DIR = previous


if __name__ == "__main__":
    unittest.main()
