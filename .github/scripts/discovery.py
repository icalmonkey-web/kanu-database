"""Bounded, read-only discovery. Exhausting a queue is NOT a coverage claim."""
import re
from collections import deque
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode

RELEVANT = re.compile(r'credit.?card|cc_index|cc_offer|/card[/._-]|discount|promotion|campaign|信用卡|刷卡|登錄|登錄活動|優惠|回饋|下一頁', re.I)
ASSET = re.compile(r'\.(?:jpg|jpeg|png|gif|svg|css|js|zip|mp4|woff2?)(?:$|\?)', re.I)
IRRELEVANT = re.compile(r'login|logout|apply|application|faq|fee|fraud|security|privacy|career|branch|atm|貸款|存款|開戶|申請進度|防詐|繳款', re.I)

def canonical(base, href):
    if not href or href.startswith(('#', 'javascript:', 'mailto:', 'tel:')):
        return None
    p = urlsplit(urljoin(base, href))
    if p.scheme != 'https' or p.username or p.password or not p.hostname or p.port not in (None, 443):
        return None
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
             if not k.lower().startswith(('utm_', 'fbclid', 'gclid'))]
    return urlunsplit(('https', p.netloc.lower(), p.path or '/', urlencode(sorted(query)), ''))

def allowed(url, hosts):
    return urlsplit(url).hostname in hosts

def explore(page, config, analyze, max_pages=150, max_depth=5, max_expansions=8):
    seeds = list(dict.fromkeys(config.get('card_urls', []) + config.get('event_portals', [])))
    hosts = {urlsplit(u).hostname for u in seeds} | set(config.get('allowed_hosts', []))
    queue = deque((u, 0, None) for u in seeds)
    seen = set(seeds)
    report = {'bank': config['bank'], 'coveragePercent': None, 'targetPercent': 95,
              'coverageStatus': 'unverified', 'pages': [], 'unvisited': [],
              'externalCandidates': [], 'limits': {'pages': max_pages, 'depth': max_depth}}
    while queue and len(report['pages']) < max_pages:
        url, depth, parent = queue.popleft()
        record = {'url': url, 'parent': parent, 'depth': depth, 'issues': []}
        report['pages'].append(record)
        print(f"  探索 [{len(report['pages'])}/{max_pages}] {url}")
        if urlsplit(url).path.lower().endswith('.pdf'):
            record['status'] = 'needs_pdf_parser'
            continue
        try:
            response = page.goto(url, wait_until='domcontentloaded', timeout=30000)
            if response and response.status >= 400:
                raise RuntimeError(f'HTTP {response.status}')
            if not allowed(page.url, hosts):
                raise RuntimeError('redirect_outside_allowlist')
            page.wait_for_timeout(1800)
            texts, links = [], {}
            previous = None
            for expansion in range(max_expansions + 1):
                for frame in page.frames:
                    if not allowed(frame.url, hosts):
                        if frame.url.startswith('https:'):
                            record['issues'].append('external_frame:' + frame.url)
                        continue
                    texts.append(frame.locator('body').inner_text(timeout=5000))
                    for item in frame.eval_on_selector_all('a[href], [data-href], [data-url]',
                        "els => els.map(e => ({href:e.getAttribute('href') || e.getAttribute('data-href') || e.getAttribute('data-url'), text:e.textContent || ''}))"):
                        target = canonical(frame.url, item['href'])
                        if target:
                            links[target] = item['text']
                signature = (len(links), len(texts[-1]) if texts else 0)
                page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                page.wait_for_timeout(700)
                # Only explicit read-only pagination controls; never registration/apply buttons.
                button = page.get_by_role('button', name=re.compile(r'^(載入更多|顯示更多|更多活動|下一頁|Load more|Next)$', re.I))
                clickable = button.count() == 1 and button.is_visible() and button.is_enabled()
                if expansion == max_expansions:
                    if clickable or signature != previous:
                        record['issues'].append('dynamic_expansion_limit')
                    break
                if clickable:
                    button.click(timeout=5000)
                    page.wait_for_timeout(1000)
                elif signature == previous:
                    break
                previous = signature
            text = '\n'.join(dict.fromkeys(texts))
            record['characters'] = len(text)
            record['linksFound'] = len(links)
            for target, label in sorted(links.items()):
                if ASSET.search(target) or IRRELEVANT.search(target + ' ' + label) or not RELEVANT.search(target + ' ' + label):
                    continue
                if not allowed(target, hosts):
                    if target not in report['externalCandidates']:
                        report['externalCandidates'].append(target)
                    continue
                if target in seen:
                    continue
                seen.add(target)
                if depth >= max_depth:
                    report['unvisited'].append({'url': target, 'reason': 'depth_limit', 'parent': url})
                else:
                    queue.append((target, depth + 1, url))
            if len(text.strip()) < 150:
                record['status'] = 'insufficient_content'
                record['contentPreview'] = text[:150]
            elif re.search(r'Access Denied|驗證您是人類|verify you are human', text, re.I):
                record['status'] = 'blocked'
            else:
                record['status'] = analyze(url, text)
            if url in seeds and not any(p == url for _, _, p in queue):
                record['issues'].append('entry_has_no_new_children')
        except Exception as exc:
            record['status'] = 'fetch_failed'
            record['error'] = str(exc)[:400]
    report['unvisited'].extend({'url': u, 'reason': 'page_limit', 'parent': p} for u, _, p in queue)
    report['status'] = 'needs_review' if (report['unvisited'] or report['externalCandidates'] or
        any(p['status'] not in ('analyzed', 'unchanged') or p['issues'] for p in report['pages'])) else 'discovery_finished_unverified'
    return report
