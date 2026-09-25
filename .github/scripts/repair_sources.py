"""Repair missing rule sourceUrl values without invoking Gemini.

Pass 1 copies a source from an equivalent rule already carrying an official URL.
Pass 2 downloads each known official candidate page once and only assigns a URL
when a rule title has one unique, high-confidence textual match.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data.json"
STATE_FILE = ROOT / "crawler_state.json"
ISSUER_FILE = ROOT / "issuer_registry.json"
CRAWL_REPORT_FILE = ROOT / "crawl_report.json"
REPORT_FILE = ROOT / "source_repair_report.json"
TIMEOUT = float(os.environ.get("SOURCE_REPAIR_TIMEOUT_SECONDS", "20"))
CONCURRENCY = int(os.environ.get("SOURCE_REPAIR_CONCURRENCY", "8"))
MAX_PAGES_PER_BANK = int(os.environ.get("SOURCE_REPAIR_MAX_PAGES_PER_BANK", "120"))


def atomic_json(path, payload):
    path = Path(path)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


class _TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.parts.append(" ".join(data.split()))


def html_text(value):
    parser = _TextParser()
    parser.feed(value)
    return "\n".join(parser.parts)


def utc_now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def normalized_title(value):
    value = re.sub(r"\s+", "", str(value or "")).upper()
    value = re.sub(r"[，。,:：；;、（）()【】\[\]・|｜/\\_-]", "", value)
    return value


def title_family(value):
    value = normalized_title(value)
    return re.sub(r"(?:最高(?:享|送)?|加碼|回饋).*$", "", value) or value


def official_hosts(issuer):
    hosts = set(issuer.get("allowedHosts", []))
    for key in ("cardCatalogUrls", "offerPortalUrls", "registrationPortalUrls"):
        hosts.update(urlsplit(url).hostname for url in issuer.get(key, []) if urlsplit(url).hostname)
    return hosts


def infer_rule_bank(rule, card_bank):
    return rule.get("bank") or card_bank.get(rule.get("cardId")) or ""


def refresh_issuer_inventory(registry, data):
    crawl_report = load_json(CRAWL_REPORT_FILE, {"banks": []})
    reports = {row.get("bank"): row for row in crawl_report.get("banks", [])}
    card_bank = {card.get("id"): card.get("bank", "") for card in data.get("cards", [])}
    for issuer in registry.get("issuers", []):
        bank = issuer.get("name")
        card_ids = {card_id for card_id, value in card_bank.items() if value == bank}
        issuer["discoveredCardCount"] = len(card_ids)
        issuer["discoveredOfferCount"] = sum(
            infer_rule_bank(rule, card_bank) == bank for rule in data.get("rules", []))
        report = reports.get(bank)
        if report:
            issuer["lastScanAt"] = report.get("completedAt", "")
            issuer["lastScanStatus"] = report.get("status", "unknown")
            issuer["unvisitedPageCount"] = len(report.get("unvisited", []))
            issuer["failedPageCount"] = sum(
                page.get("status") in {"fetch_failed", "ai_failed_preserved_old_data", "insufficient_content"}
                for page in report.get("pages", []))
            if report.get("status") == "completed":
                issuer["lastSuccessfulScanAt"] = report.get("completedAt", "")
    registry["lastUpdatedAt"] = utc_now()
    return registry


def copy_equivalent_sources(data, issuer_by_bank):
    card_bank = {card.get("id"): card.get("bank", "") for card in data.get("cards", [])}
    known = defaultdict(set)
    for rule in data.get("rules", []):
        bank = infer_rule_bank(rule, card_bank)
        source = str(rule.get("sourceUrl") or "").strip()
        hosts = official_hosts(issuer_by_bank.get(bank, {}))
        if source and urlsplit(source).hostname in hosts:
            known[(bank, title_family(rule.get("title")))].add(source)
    repaired = 0
    for rule in data.get("rules", []):
        if rule.get("sourceUrl"):
            continue
        bank = infer_rule_bank(rule, card_bank)
        choices = known.get((bank, title_family(rule.get("title"))), set())
        if len(choices) == 1:
            rule["sourceUrl"] = next(iter(choices))
            rule["sourceRepairMethod"] = "equivalent_rule"
            repaired += 1
    return repaired


def candidate_urls(bank, issuer, state, data, card_bank):
    urls = []
    for key in ("cardCatalogUrls", "offerPortalUrls", "registrationPortalUrls"):
        urls.extend(issuer.get(key, []))
    urls.extend(url for url, row in state.get("pages", {}).items() if row.get("bank") == bank)
    urls.extend(rule.get("sourceUrl") for rule in data.get("rules", [])
                if infer_rule_bank(rule, card_bank) == bank and rule.get("sourceUrl"))
    hosts = official_hosts(issuer)
    return list(dict.fromkeys(url for url in urls
                              if url and urlsplit(url).scheme == "https"
                              and urlsplit(url).hostname in hosts))[:MAX_PAGES_PER_BANK]


async def fetch_texts(urls):
    semaphore = asyncio.Semaphore(CONCURRENCY)
    output, failures = {}, {}
    def blocking_fetch(url):
        request = Request(url, headers={"User-Agent": "Mozilla/5.0 KanuSourceRepair/1.0"})
        with urlopen(request, timeout=TIMEOUT) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")

    async def fetch(url):
        async with semaphore:
            try:
                html = await asyncio.to_thread(blocking_fetch, url)
                output[url] = normalized_title(html_text(html))
            except Exception as exc:
                failures[url] = f"{type(exc).__name__}: {exc}"[:300]
    await asyncio.gather(*(fetch(url) for url in urls))
    return output, failures


async def run():
    data = load_json(DATA_FILE, {"cards": [], "rules": []})
    state = load_json(STATE_FILE, {"pages": {}})
    registry = load_json(ISSUER_FILE, {"issuers": []})
    issuer_by_bank = {issuer.get("name"): issuer for issuer in registry.get("issuers", [])}
    card_bank = {card.get("id"): card.get("bank", "") for card in data.get("cards", [])}
    before = sum(not rule.get("sourceUrl") for rule in data.get("rules", []))
    duplicate_repairs = copy_equivalent_sources(data, issuer_by_bank)

    pending_by_bank = defaultdict(list)
    for rule in data.get("rules", []):
        if not rule.get("sourceUrl"):
            pending_by_bank[infer_rule_bank(rule, card_bank)].append(rule)

    page_repairs, all_failures, ambiguous = 0, {}, []
    for bank, pending in pending_by_bank.items():
        issuer = issuer_by_bank.get(bank)
        if not bank or not issuer:
            continue
        urls = candidate_urls(bank, issuer, state, data, card_bank)
        texts, failures = await fetch_texts(urls)
        all_failures.update(failures)
        for rule in pending:
            needle = normalized_title(rule.get("title"))
            if len(needle) < 6:
                continue
            matches = [url for url, text in texts.items() if needle in text]
            if len(matches) == 1:
                rule["sourceUrl"] = matches[0]
                rule["sourceRepairMethod"] = "unique_exact_title_match"
                page_repairs += 1
            elif len(matches) > 1:
                ambiguous.append({"ruleId": rule.get("id"), "bank": bank,
                                  "title": rule.get("title"), "candidates": matches[:10]})

    after = sum(not rule.get("sourceUrl") for rule in data.get("rules", []))
    if after < before:
        data["version"] = datetime.now(timezone.utc).strftime("%Y.%m.%d-v%H%M%S-sourcefix")
        data["lastUpdated"] = utc_now()
        atomic_json(DATA_FILE, data)
    atomic_json(ISSUER_FILE, refresh_issuer_inventory(registry, data))
    previous_report = load_json(REPORT_FILE, {})
    report = {"generatedAt": utc_now(), "beforeMissing": before, "afterMissing": after,
              "repairedFromEquivalentRule": duplicate_repairs,
              "repairedFromUniquePageMatch": page_repairs,
              "cumulativeRepaired": int(previous_report.get(
                  "cumulativeRepaired",
                  int(previous_report.get("beforeMissing", 0)) - int(previous_report.get("afterMissing", 0))))
                  + (before - after),
              "ambiguous": ambiguous, "fetchFailures": all_failures,
              "aiRequests": 0}
    atomic_json(REPORT_FILE, report)
    print(json.dumps({key: report[key] for key in (
        "beforeMissing", "afterMissing", "repairedFromEquivalentRule",
        "repairedFromUniquePageMatch", "aiRequests")}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(run())
