import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

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

    def test_issuer_registry_drives_enabled_credit_card_banks(self):
        with patch.dict("os.environ", {"FORCE_FULL_SCAN": "1"}):
            configs = fast_update.load_issuer_configs()
        names = {config["bank"] for config in configs}
        self.assertIn("星展銀行", names)
        self.assertIn("樂天信用卡", names)
        self.assertIn("台中銀行", names)
        self.assertIn("王道銀行", names)
        self.assertIn("將來銀行", names)
        self.assertIn("LINE Bank", names)
        self.assertIn("美國運通", names)

    def test_payment_provider_registry_drives_separate_payment_sources(self):
        with patch.dict("os.environ", {"FORCE_FULL_SCAN": "1"}):
            configs = fast_update.load_issuer_configs()
        payment_configs = [row for row in configs if row.get("source_type") == "PAYMENT"]
        names = {row["bank"] for row in payment_configs}
        self.assertEqual(
            names,
            {"LINE Pay", "全支付", "悠遊付", "街口支付", "icash Pay", "台灣 Pay"},
        )
        self.assertTrue(all(row["product_types"] == ["PAYMENT"] for row in payment_configs))

    def test_payment_status_counts_only_payment_domain_offers(self):
        registry = {"providers": [{"name": "LINE Pay"}]}
        reports = [{"bank": "LINE Pay", "sourceType": "PAYMENT", "status": "completed",
                    "completedAt": "now", "unvisited": [], "pages": []}]
        rules = {
            "payment": {"offerDomain": "PAYMENT", "paymentProvider": "LINE Pay"},
            "card": {"offerDomain": "CARD", "paymentProvider": "LINE Pay"},
        }
        updated = fast_update.update_payment_scan_status(registry, reports, rules)["providers"][0]
        self.assertEqual(updated["discoveredOfferCount"], 1)
        self.assertEqual(updated["lastScanStatus"], "completed")

    def test_scan_frequency_skips_low_frequency_issuer_until_due(self):
        now = datetime(2026, 9, 25, tzinfo=timezone.utc)
        issuer = {"scanFrequency": "weekly", "lastSuccessfulScanAt": "2026-09-24T00:00:00Z"}
        self.assertFalse(fast_update.issuer_scan_due(issuer, now))
        issuer["lastSuccessfulScanAt"] = "2026-09-10T00:00:00Z"
        self.assertTrue(fast_update.issuer_scan_due(issuer, now))

    def test_issuer_registry_has_unique_names_and_required_fields(self):
        registry = json.loads(fast_update.ISSUER_FILE.read_text(encoding="utf-8"))
        issuers = registry["issuers"]
        names = [issuer["name"] for issuer in issuers]
        self.assertEqual(len(names), len(set(names)))
        required = {"issuesCreditCards", "cardCatalogUrls", "offerPortalUrls",
                    "registrationPortalUrls", "allowedHosts", "captureModes",
                    "lastSuccessfulScanAt", "discoveredCardCount",
                    "discoveredOfferCount", "unvisitedPageCount", "failedPageCount"}
        for issuer in issuers:
            self.assertFalse(required - set(issuer), issuer["name"])

    def test_next_bank_has_registration_sources_and_announcement_discovery(self):
        registry = json.loads(fast_update.ISSUER_FILE.read_text(encoding="utf-8"))
        issuer = next(row for row in registry["issuers"] if row["name"] == "將來銀行")
        self.assertIn("DEBIT", issuer["productTypes"])
        self.assertTrue(issuer["registrationPortalUrls"])
        self.assertIn("www.nextbank.com.tw", issuer["allowedHosts"])
        self.assertRegex("announcement/event1249", issuer["eventLinkPattern"])

    def test_issuer_status_records_counts_and_failures(self):
        registry = {"issuers": [{"name": "測試銀行"}]}
        reports = [{"bank": "測試銀行", "status": "needs_review", "completedAt": "now",
                    "unvisited": [{"url": "x"}], "pages": [{"status": "fetch_failed"}]}]
        cards = {"c": {"id": "c1", "bank": "測試銀行"}}
        rules = {"r": {"id": "r1", "cardId": "c1", "bank": "測試銀行"}}
        updated = fast_update.update_issuer_scan_status(registry, reports, cards, rules)["issuers"][0]
        self.assertEqual(updated["discoveredCardCount"], 1)
        self.assertEqual(updated["discoveredOfferCount"], 1)
        self.assertEqual(updated["unvisitedPageCount"], 1)
        self.assertEqual(updated["failedPageCount"], 1)

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
