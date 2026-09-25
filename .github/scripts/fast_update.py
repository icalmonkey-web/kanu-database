"""Fast, resumable bank crawler.

Static HTML is fetched with httpx first. JavaScript rendering is used only when
the static response has too little useful text. Banks run concurrently, while
Gemini calls are deliberately serialized through one quota-aware ModelPool.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import tempfile
from collections import deque
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import httpx
from google import genai
from playwright.async_api import async_playwright

import update_data as legacy
from discovery import ASSET, IRRELEVANT, RELEVANT, allowed, canonical
from model_pool import ModelPool


ROOT = Path(__file__).resolve().parents[2]
DATA_FILE = ROOT / "data.json"
STATE_FILE = ROOT / "crawler_state.json"
REPORT_FILE = ROOT / "crawl_report.json"
ISSUER_FILE = ROOT / "issuer_registry.json"
CHECKPOINT_DIR = ROOT / "checkpoints"
PAGE_TIMEOUT = float(os.environ.get("PAGE_TIMEOUT_SECONDS", "25"))
CRAWL_BUDGET_SECONDS = float(os.environ.get("CRAWL_BUDGET_SECONDS", "4200"))
AI_TIMEOUT_MILLISECONDS = int(os.environ.get("AI_TIMEOUT_MILLISECONDS", "45000"))
AI_MIN_INTERVAL_SECONDS = float(os.environ.get("AI_MIN_INTERVAL_SECONDS", "3"))
BANK_CONCURRENCY = int(os.environ.get("BANK_CONCURRENCY", "4"))
MAX_PAGES = int(os.environ.get("MAX_PAGES_PER_BANK", "60"))
MAX_DEPTH = int(os.environ.get("MAX_CRAWL_DEPTH", "3"))
MIN_STATIC_TEXT = int(os.environ.get("MIN_STATIC_TEXT", "350"))
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"

DYNAMIC_NOISE = [
    r"\b20\d{2}[-/.]\d{1,2}[-/.]\d{1,2}[ T]\d{1,2}:\d{2}(?::\d{2})?\b",
    r"\b\d{1,2}:\d{2}(?::\d{2})?\b",
    r"(?:nonce|requestId|traceId|timestamp|cacheBuster)[\s:=\"']+[A-Za-z0-9_.:-]+",
    r"(?:cookie|隱私權|privacy)[^\n]{0,160}(?:同意|接受|accept)",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


class TextLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.links: list[tuple[str, str]] = []
        self._skip = 0
        self._href: str | None = None
        self._label: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip += 1
        if tag == "a":
            self._href = attrs.get("href") or attrs.get("data-href") or attrs.get("data-url")
            self._label = []

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self._skip:
            self._skip -= 1
        if tag == "a" and self._href:
            self.links.append((self._href, " ".join(self._label)))
            self._href, self._label = None, []

    def handle_data(self, data):
        if self._skip:
            return
        value = " ".join(data.split())
        if value:
            self.text.append(value)
            if self._href:
                self._label.append(value)


def parse_html(html: str) -> tuple[str, list[tuple[str, str]]]:
    parser = TextLinkParser()
    parser.feed(html)
    return "\n".join(parser.text), parser.links


def normalized_content(text: str) -> str:
    value = text.replace("\u200b", " ").replace("\ufeff", " ")
    for pattern in DYNAMIC_NOISE:
        value = re.sub(pattern, " ", value, flags=re.I)
    lines = []
    for line in value.splitlines():
        line = re.sub(r"\s+", " ", line).strip()
        if line and line not in lines[-3:]:
            lines.append(line)
    return "\n".join(lines)


def stable_hash(text: str) -> str:
    return hashlib.sha256(normalized_content(text).encode("utf-8")).hexdigest()


def load_json(path: Path, default):
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return default


def load_json_or_fail(path: Path, required_list_key: str | None = None):
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Refusing crawler run: invalid {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Refusing crawler run: {path.name} root must be an object")
    if required_list_key and (not isinstance(payload.get(required_list_key), list) or not payload[required_list_key]):
        raise RuntimeError(f"Refusing crawler run: {path.name}.{required_list_key} is missing or empty")
    return payload


def issuer_scan_due(issuer, now=None):
    if os.environ.get("FORCE_FULL_SCAN", "0") == "1":
        return True
    frequency = str(issuer.get("scanFrequency", "daily")).lower()
    days = {"daily": 1, "weekly": 7, "monthly": 30}.get(frequency, 1)
    raw_last_scan = issuer.get("lastSuccessfulScanAt") or issuer.get("lastScanAt")
    if not raw_last_scan:
        return True
    try:
        last_scan = datetime.fromisoformat(str(raw_last_scan).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return True
    current = now or datetime.now(timezone.utc)
    return current - last_scan >= timedelta(days=days)


def load_issuer_configs():
    registry = load_json_or_fail(ISSUER_FILE, "issuers")
    issuers = registry.get("issuers", [])
    if not issuers:
        return legacy.PORTAL_CONFIGS
    configs = []
    for issuer in issuers:
        product_types = issuer.get("productTypes") or (["CREDIT"] if issuer.get("issuesCreditCards") else [])
        if (not issuer.get("enabled", False)
                or not set(product_types) & {"CREDIT", "DEBIT", "CHARGE"}
                or not issuer_scan_due(issuer)):
            continue
        configs.append({
            "bank": issuer["name"],
            "card_urls": issuer.get("cardCatalogUrls", []),
            "event_portals": issuer.get("offerPortalUrls", []) + issuer.get("registrationPortalUrls", []),
            "allowed_hosts": issuer.get("allowedHosts", []),
            "event_link_pattern": issuer.get("eventLinkPattern", ""),
            "product_types": product_types,
        })
    return configs


def update_issuer_scan_status(registry, reports, cards, rules):
    report_by_bank = {row.get("bank"): row for row in reports}
    for issuer in registry.get("issuers", []):
        bank = issuer.get("name")
        report = report_by_bank.get(bank)
        bank_card_ids = {card.get("id") for card in cards.values() if card.get("bank") == bank}
        issuer["discoveredCardCount"] = len(bank_card_ids)
        issuer["discoveredOfferCount"] = sum(
            1 for rule in rules.values()
            if rule.get("bank") == bank or rule.get("cardId") in bank_card_ids
        )
        if report:
            issuer["lastScanAt"] = report.get("completedAt", utc_now())
            issuer["lastScanStatus"] = report.get("status", "unknown")
            issuer["unvisitedPageCount"] = len(report.get("unvisited", []))
            issuer["failedPageCount"] = sum(
                page.get("status") in {"fetch_failed", "ai_failed_preserved_old_data", "insufficient_content"}
                for page in report.get("pages", [])
            )
            if report.get("status") == "completed":
                issuer["lastSuccessfulScanAt"] = report.get("completedAt", utc_now())
    registry["lastUpdatedAt"] = utc_now()
    return registry


def checkpoint_name(bank: str) -> Path:
    slug = hashlib.sha256(bank.encode("utf-8")).hexdigest()[:12]
    return CHECKPOINT_DIR / f"{slug}.json"


class FetchResult:
    def __init__(self, url, text="", links=None, status="ok", etag="", modified="", error="",
                 renderer="httpx", static_hash="", rendered_hash=""):
        self.url, self.text, self.links, self.status = url, text, links or [], status
        self.etag, self.modified, self.error, self.renderer = etag, modified, error, renderer
        self.static_hash, self.rendered_hash = static_hash, rendered_hash


async def fetch_page(client, context, url: str, prior: dict) -> FetchResult:
    headers = {}
    if prior.get("etag"):
        headers["If-None-Match"] = prior["etag"]
    if prior.get("lastModified"):
        headers["If-Modified-Since"] = prior["lastModified"]
    try:
        response = await client.get(url, headers=headers, timeout=PAGE_TIMEOUT, follow_redirects=True)
        if response.status_code == 304:
            return FetchResult(url, links=[tuple(row) for row in prior.get("links", [])], status="not_modified")
        response.raise_for_status()
        text, raw_links = parse_html(response.text)
        static_digest = stable_hash(text)
        links = [(canonical(str(response.url), href), label) for href, label in raw_links]
        links = [(href, label) for href, label in links if href]
        # Only a page previously proven usable without a browser may safely skip
        # Playwright on its static hash. A stable JS app shell does not prove its
        # API-backed content is unchanged.
        if prior.get("renderer") == "httpx" and prior.get("staticHash") == static_digest:
            return FetchResult(str(response.url), links=links, status="not_modified_static_hash",
                etag=response.headers.get("etag", ""), modified=response.headers.get("last-modified", ""),
                renderer="httpx", static_hash=static_digest)
        if len(normalized_content(text)) >= MIN_STATIC_TEXT:
            return FetchResult(str(response.url), text, links,
                etag=response.headers.get("etag", ""), modified=response.headers.get("last-modified", ""),
                static_hash=static_digest, rendered_hash=static_digest)
    except Exception as exc:
        static_error = f"{type(exc).__name__}: {exc}"
    else:
        static_error = "insufficient_static_content"

    page = await context.new_page()
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT * 1000)
        if response and response.status >= 400:
            raise RuntimeError(f"HTTP {response.status}")
        await page.wait_for_timeout(800)
        text = await page.locator("body").inner_text(timeout=5000)
        raw_links = await page.locator("a[href]").evaluate_all(
            "els => els.map(e => [e.href, e.textContent || ''])")
        links = [(canonical(page.url, href), label) for href, label in raw_links]
        links = [(href, label) for href, label in links if href]
        return FetchResult(page.url, text, links, renderer="playwright",
            static_hash=locals().get("static_digest", ""), rendered_hash=stable_hash(text))
    except Exception as exc:
        return FetchResult(url, status="fetch_failed", error=f"{static_error}; {type(exc).__name__}: {exc}")
    finally:
        await page.close()


def old_maps(old: dict, audited_ids=None):
    rejected_ids = {
        card.get("id") for card in old.get("cards", [])
        if audited_ids is not None and card.get("id") not in audited_ids
    }
    cards = {
        f"{c.get('bank')}_{legacy.normalize_card_name(c.get('cardName'))}": c
        for c in old.get("cards", [])
        if audited_ids is None or c.get("id") in audited_ids
    }
    rules = {f"{r.get('cardId')}_{r.get('title', '')}_{r.get('sourceUrl', '')}": r for r in old.get("rules", [])}
    for rule in rules.values():
        if rule.get("cardId") in rejected_ids:
            rule["cardId"] = None
            rule["associationStatus"] = "needs_review"
    return cards, rules


def restore_newer_checkpoints(old: dict, state: dict, cards: dict, rules: dict) -> int:
    """Restore locally/downloaded checkpoints only when newer than data.json."""
    restored = 0
    baseline = str(old.get("lastUpdated", ""))
    if not CHECKPOINT_DIR.exists():
        return restored
    for path in CHECKPOINT_DIR.glob("*.json"):
        checkpoint = load_json(path, {})
        if not checkpoint.get("bank") or str(checkpoint.get("savedAt", "")) <= baseline:
            continue
        bank = checkpoint["bank"]
        card_ids = {card.get("id") for card in checkpoint.get("cards", [])}
        cards.update({f"{c.get('bank')}_{legacy.normalize_card_name(c.get('cardName'))}": c
                      for c in checkpoint.get("cards", [])})
        for key in [key for key, rule in rules.items()
                    if rule.get("bank") == bank or rule.get("cardId") in card_ids]:
            del rules[key]
        rules.update({f"{r.get('cardId')}_{r.get('title', '')}_{r.get('sourceUrl', '')}": r
                      for r in checkpoint.get("rules", [])})
        state.setdefault("pages", {}).update(checkpoint.get("pages", {}))
        restored += 1
    return restored


TIME_BUDGET_EXHAUSTED = object()


class AiGate:
    def __init__(self, minimum_interval=AI_MIN_INTERVAL_SECONDS):
        self.lock = asyncio.Lock()
        self.minimum_interval = max(0.0, minimum_interval)
        self.last_request_at = 0.0

    async def run(self, function, *args):
        async with self.lock:
            loop = asyncio.get_running_loop()
            wait = self.minimum_interval - (loop.time() - self.last_request_at)
            if wait > 0:
                await asyncio.sleep(wait)
            try:
                return await asyncio.to_thread(function, *args)
            finally:
                self.last_request_at = loop.time()


async def analyze_changed_page(ai_gate, bank, product_types, text, url, deadline):
    if asyncio.get_running_loop().time() >= deadline:
        return TIME_BUDGET_EXHAUSTED
    return await ai_gate.run(legacy.extract_with_gemini, bank, text[:14000], url, True, product_types)


async def crawl_bank(config, client, browser, state, state_lock, ai_gate, merge_lock, cards, rules, deadline):
    bank = config["bank"]
    seeds = list(dict.fromkeys(config.get("card_urls", []) + config.get("event_portals", [])))
    hosts = {urlsplit(url).hostname for url in seeds} | set(config.get("allowed_hosts", []))
    queue, seen = deque((url, 0, None) for url in seeds), set(seeds)
    report = {"bank": bank, "status": "running", "pages": [], "unvisited": [], "startedAt": utc_now()}
    context = await browser.new_context(user_agent=USER_AGENT, locale="zh-TW", viewport={"width": 1440, "height": 900})
    try:
        while queue and len(report["pages"]) < MAX_PAGES:
            if asyncio.get_running_loop().time() >= deadline:
                report["unvisited"].extend(
                    {"url": pending_url, "reason": "workflow_time_budget", "parent": pending_parent}
                    for pending_url, _, pending_parent in queue
                )
                queue.clear()
                break
            url, depth, parent = queue.popleft()
            prior = state.setdefault("pages", {}).get(url, {})
            row = {"url": url, "parent": parent, "depth": depth, "renderer": "none"}
            report["pages"].append(row)
            if urlsplit(url).path.lower().endswith(".pdf"):
                row.update(status="needs_pdf_parser", renderer="none")
                continue
            result = await fetch_page(client, context, url, prior)
            row["renderer"] = result.renderer
            if result.status == "fetch_failed":
                row.update(status="fetch_failed", error=result.error[:500])
                continue
            if not allowed(result.url, hosts):
                row.update(status="redirect_outside_allowlist", redirectedTo=result.url)
                continue
            links = result.links or [tuple(item) for item in prior.get("links", [])]
            configured_link_pattern = str(config.get("event_link_pattern") or "")
            for target, label in links:
                if (not target or ASSET.search(target) or IRRELEVANT.search(target + " " + label)
                        or not (RELEVANT.search(target + " " + label)
                                or (configured_link_pattern and re.search(
                                    configured_link_pattern, target + " " + label, re.I)))):
                    continue
                if not allowed(target, hosts) or target in seen:
                    continue
                seen.add(target)
                if depth >= MAX_DEPTH:
                    report["unvisited"].append({"url": target, "reason": "depth_limit", "parent": url})
                else:
                    queue.append((target, depth + 1, url))

            if result.status in {"not_modified", "not_modified_static_hash"}:
                row["status"] = "unchanged_304" if result.status == "not_modified" else "unchanged_static_hash"
                async with state_lock:
                    prior.update(bank=bank, links=links, lastSeenAt=utc_now())
                    # A 304 validates the prior representation but does not turn a
                    # previously dynamic page into a static one.
                    if result.status == "not_modified_static_hash":
                        prior["renderer"] = "httpx"
                    if result.static_hash:
                        prior["staticHash"] = result.static_hash
                continue
            cleaned = normalized_content(result.text)
            digest = result.rendered_hash or stable_hash(result.text)
            prior_digest = prior.get("renderedHash") or prior.get("hash")
            if prior_digest == digest:
                row["status"] = "unchanged_hash"
            elif len(cleaned) < 150:
                row["status"] = "insufficient_content"
            else:
                extracted = await analyze_changed_page(
                    ai_gate, bank, config.get("product_types", ["CREDIT"]), cleaned, result.url, deadline)
                if extracted is TIME_BUDGET_EXHAUSTED:
                    row["status"] = "workflow_time_budget"
                    report["unvisited"].extend(
                        {"url": pending_url, "reason": "workflow_time_budget", "parent": pending_parent}
                        for pending_url, _, pending_parent in queue
                    )
                    queue.clear()
                    break
                if extracted is None:
                    row["status"] = "ai_failed_preserved_old_data"
                    continue
                async with merge_lock:
                    stale = [key for key, rule in rules.items() if rule.get("bank") == bank and rule.get("sourceUrl") == result.url]
                    for key in stale:
                        del rules[key]
                    legacy.merge_data(bank, extracted, cards, rules, result.url)
                row["status"] = "analyzed"
            async with state_lock:
                state["pages"][url] = {"hash": digest, "staticHash": result.static_hash,
                    "renderedHash": digest, "renderer": result.renderer, "bank": bank, "etag": result.etag,
                    "lastModified": result.modified, "links": links, "lastSeenAt": utc_now()}

        report["unvisited"].extend({"url": url, "reason": "page_limit", "parent": parent} for url, _, parent in queue)
        report["status"] = "needs_review" if report["unvisited"] or any(
            page.get("status") in {"fetch_failed", "ai_failed_preserved_old_data", "insufficient_content"}
            for page in report["pages"]) else "completed"
        report["completedAt"] = utc_now()
        async with merge_lock:
            bank_card_ids = {c.get("id") for c in cards.values() if c.get("bank") == bank}
            checkpoint = {"bank": bank, "savedAt": utc_now(),
                "cards": [c for c in cards.values() if c.get("bank") == bank],
                "rules": [r for r in rules.values() if r.get("bank") == bank or r.get("cardId") in bank_card_ids],
                "pages": {url: value for url, value in state["pages"].items() if value.get("bank") == bank},
                "report": report}
            atomic_json(checkpoint_name(bank), checkpoint)
        print(f"✅ {bank}: {len(report['pages'])} pages, checkpoint saved")
        return report
    finally:
        await context.close()


async def run():
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    old = load_json_or_fail(DATA_FILE, "cards")
    if not isinstance(old.get("rules"), list) or not old["rules"]:
        raise RuntimeError("Refusing crawler run: data.json.rules is missing or empty")
    state = load_json_or_fail(STATE_FILE)
    if "pages" not in state:
        state["pages"] = {url: {"hash": digest} for url, digest in state.pop("pageHashes", {}).items()}
    issuer_registry = load_json_or_fail(ISSUER_FILE, "issuers")
    issuer_configs = load_issuer_configs()
    if not issuer_configs:
        print("NOOP: no issuer is due for scanning; existing data remains unchanged and AI was not called.")
        return
    preferred = [name for name in os.environ.get("GEMINI_MODELS", "").split(",") if name]
    legacy.MODEL_POOL = ModelPool(
        genai.Client(api_key=api_key, http_options={"timeout": AI_TIMEOUT_MILLISECONDS}),
        preferred + legacy.CANDIDATE_MODELS,
    )
    audited_ids = await asyncio.to_thread(legacy.audit_existing_cards, old.get("cards", []))
    cards, rules = old_maps(old, audited_ids)
    restored = restore_newer_checkpoints(old, state, cards, rules)
    if restored:
        print(f"Restored {restored} newer bank checkpoints")
    semaphore, state_lock, merge_lock = asyncio.Semaphore(BANK_CONCURRENCY), asyncio.Lock(), asyncio.Lock()
    ai_gate = AiGate()

    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}) as client, async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=["--no-sandbox"])
        deadline = asyncio.get_running_loop().time() + CRAWL_BUDGET_SECONDS
        async def limited(config):
            async with semaphore:
                return await crawl_bank(
                    config, client, browser, state, state_lock, ai_gate, merge_lock,
                    cards, rules, deadline,
                )
        reports = await asyncio.gather(*(limited(config) for config in issuer_configs))
        await browser.close()

    ai_failed_pages = sum(
        1 for report in reports for page in report.get("pages", [])
        if page.get("status") == "ai_failed_preserved_old_data"
    )
    if ai_failed_pages:
        atomic_json(REPORT_FILE, {"generatedAt": utc_now(), "banks": reports,
            "summary": {"banks": len(reports), "needsReview": len(reports),
                        "aiRequests": legacy.MODEL_POOL.requests,
                        "status": "ai_unavailable_data_preserved", "aiFailedPages": ai_failed_pages}})
        raise RuntimeError(
            f"AI unavailable for {ai_failed_pages} changed page(s); existing data was preserved and nothing was published"
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    active_rules = []
    for rule in rules.values():
        end = legacy.parse_explicit_date(rule.get("validUntil")) or legacy.parse_explicit_date(rule.get("regDeadline"))
        if not end or end >= now:
            active_rules.append(legacy.enrich_reward_fields(rule, rule.get("sourceUrl", "")))
    output = dict(old)
    output.update(cards=list(cards.values()), rules=active_rules,
        version=datetime.now(timezone.utc).strftime("%Y.%m.%d-v%H%M%S"), lastUpdated=utc_now())
    if len(output["cards"]) < max(1, int(len(old["cards"]) * 0.8)):
        raise RuntimeError(f"Refusing publish: card count collapsed {len(old['cards'])} -> {len(output['cards'])}")
    if len(output["rules"]) < max(1, int(len(old["rules"]) * 0.7)):
        raise RuntimeError(f"Refusing publish: rule count collapsed {len(old['rules'])} -> {len(output['rules'])}")
    state["lastRunAt"] = utc_now()
    atomic_json(DATA_FILE, output)
    atomic_json(STATE_FILE, state)
    atomic_json(REPORT_FILE, {"generatedAt": utc_now(), "banks": reports,
        "summary": {"banks": len(reports), "needsReview": sum(r["status"] != "completed" for r in reports),
                    "aiRequests": legacy.MODEL_POOL.requests}})
    atomic_json(ISSUER_FILE, update_issuer_scan_status(issuer_registry, reports, cards, rules))
    print(f"DONE banks={len(reports)} cards={len(output['cards'])} rules={len(output['rules'])} AI={legacy.MODEL_POOL.requests}")


if __name__ == "__main__":
    asyncio.run(run())
