"""Incrementally verify that source pages actually contain their offer titles.

Title presence is only discovery evidence, never proof of a reward's terms.
"""
import asyncio
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from repair_sources import html_text, normalized_title, official_hosts, infer_rule_bank, atomic_json

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data.json'
STATE = ROOT / 'source_title_state.json'
REPORT = ROOT / 'source_title_report.json'
REGISTRY = ROOT / 'issuer_registry.json'


def scan_candidates(data, issuers):
    card_banks = {c.get('id'): c.get('bank', '') for c in data.get('cards', [])}
    by_url = defaultdict(list)
    for rule in data.get('rules', []):
        if (rule.get('accuracyReview') or {}).get('status') == 'SOURCE_CHECKED':
            continue
        url = str(rule.get('sourceUrl') or '')
        bank = infer_rule_bank(rule, card_banks)
        try:
            parts = urlsplit(url)
        except ValueError:
            continue
        if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
                or parts.hostname not in official_hosts(issuers.get(bank, {}))):
            continue
        by_url[url].append(rule)
    return by_url


def inspect_title(rule, text):
    title = normalized_title(rule.get('title'))
    if len(title) < 8:
        return 'TITLE_TOO_SHORT'
    return 'TITLE_FOUND' if title in text else 'TITLE_NOT_FOUND_IN_STATIC_HTML'


def fingerprint(rules):
    claims = sorted((str(rule.get('id')), str(rule.get('title'))) for rule in rules)
    return hashlib.sha256(json.dumps(claims, ensure_ascii=False).encode('utf-8')).hexdigest()


def due_urls(groups, state, now, limit):
    pages = state.get('pages', {})
    cutoff = now - timedelta(days=7)
    due = []
    for url in sorted(groups):
        previous = pages.get(url, {})
        try:
            checked = datetime.fromisoformat(previous.get('checkedAt', ''))
        except ValueError:
            checked = None
        if (previous.get('status') == 'FETCH_FAILED' and checked and checked.tzinfo
                and previous.get('fingerprint') == fingerprint(groups[url])
                and checked >= now - timedelta(days=1)):
            continue
        if (previous.get('fingerprint') != fingerprint(groups[url]) or 'claims' not in previous or not checked
                or checked.tzinfo is None or checked < cutoff):
            due.append(url)
    return due[:limit]


async def run(limit=80):
    data = json.loads(DATA.read_text(encoding='utf-8'))
    issuers = {r.get('name'): r for r in json.loads(REGISTRY.read_text(encoding='utf-8')).get('issuers', [])}
    groups = scan_candidates(data, issuers)
    state = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else {}
    state.pop('completedUrls', None)  # Old state had no claim fingerprint or expiry.
    pages = state.setdefault('pages', {})
    now = datetime.now(timezone.utc)
    urls = due_urls(groups, state, now, limit)
    semaphore = asyncio.Semaphore(8)
    results = []

    def fetch(url):
        request = Request(url, headers={'User-Agent': 'Mozilla/5.0 KanuEvidenceCheck/1.0'})
        with urlopen(request, timeout=8) as response:
            final = urlsplit(response.url)
            if final.scheme != 'https' or final.hostname != urlsplit(url).hostname:
                raise ValueError('redirected_to_different_host')
            if 'text/html' not in response.headers.get('content-type', ''):
                raise ValueError('not_html')
            body = response.read(1_000_001)
            if len(body) > 1_000_000:
                raise ValueError('html_too_large')
            return normalized_title(html_text(body.decode('utf-8', 'replace')))

    async def one(url):
        async with semaphore:
            try:
                text = await asyncio.to_thread(fetch, url)
            except Exception as exc:
                results.append({'url': url, 'status': 'FETCH_FAILED', 'reason': type(exc).__name__})
                pages[url] = {'checkedAt': now.isoformat(), 'fingerprint': fingerprint(groups[url]),
                              'status': 'FETCH_FAILED', 'reason': type(exc).__name__}
                return
            claims = [{'ruleId': rule.get('id'), 'title': rule.get('title'),
                       'status': inspect_title(rule, text)} for rule in groups[url]]
            results.append({'url': url, 'status': 'FETCHED', 'rules': dict(Counter(
                claim['status'] for claim in claims)), 'claims': claims})
            pages[url] = {'checkedAt': now.isoformat(), 'fingerprint': fingerprint(groups[url]),
                          'claims': claims}
    await asyncio.gather(*(one(url) for url in urls))
    state['updatedAt'] = now.isoformat()
    recent_claims = [claim for url, page in pages.items() if url in groups
                     and page.get('fingerprint') == fingerprint(groups[url])
                     for claim in page.get('claims', [])]
    report = {'generatedAt': state['updatedAt'], 'totalCandidateUrls': len(groups),
              'scannedThisRun': len(urls), 'recentlyCheckedUrls': sum(
                  page.get('status') != 'FETCH_FAILED' for page in pages.values()),
              'failedUrls': sum(page.get('status') == 'FETCH_FAILED' for page in pages.values()),
              'ruleStatusCounts': dict(sum((Counter(row.get('rules', {})) for row in results), Counter())),
              'cumulativeRuleStatusCounts': dict(Counter(claim['status'] for claim in recent_claims)),
              'results': sorted(results, key=lambda row: row['url']),
              'caution': 'Static HTML title presence is discovery evidence only. Missing text may be dynamically rendered. Neither result validates rate, eligibility, cap, expiry, or registration.'}
    atomic_json(STATE, state)
    atomic_json(REPORT, report)
    return report


if __name__ == '__main__':
    report = asyncio.run(run(int(os.environ.get('SOURCE_TITLE_SCAN_LIMIT', '80'))))
    print(json.dumps({key: value for key, value in report.items() if key != 'results'}, ensure_ascii=False))
