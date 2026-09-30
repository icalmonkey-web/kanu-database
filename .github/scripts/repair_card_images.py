"""Bounded official catalog image repair; no AI and no guessed image URLs."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
import requests

ROOT = Path(__file__).resolve().parents[2]

def normalize(value):
    return re.sub(r'[^a-z0-9\u4e00-\u9fff]', '', str(value).lower())

class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'img':
            src = a.get('data-src') or a.get('data-original') or a.get('src')
            label = a.get('alt') or a.get('title') or ''
            if src and label:
                self.rows.append((src, label))

def fetch(job):
    bank, url, hosts = job
    try:
        response = requests.get(url, timeout=12, headers={'User-Agent': 'Mozilla/5.0'}, allow_redirects=True)
        response.raise_for_status()
        if urlsplit(response.url).hostname not in hosts:
            return bank, url, [], 'redirect outside official hosts'
        parser = Images()
        parser.feed(response.text)
        rows = []
        for src, label in parser.rows:
            image = urljoin(response.url, src)
            parsed = urlsplit(image)
            if parsed.scheme == 'https' and parsed.hostname and not parsed.username and not parsed.password:
                rows.append((image, label))
        return bank, url, rows, ''
    except requests.RequestException as exc:
        return bank, url, [], type(exc).__name__

def main():
    data = json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))
    registry = json.loads((ROOT / 'issuer_registry.json').read_text(encoding='utf-8'))
    cache_path = ROOT / 'card_image_state.json'
    cache = json.loads(cache_path.read_text(encoding='utf-8')) if cache_path.exists() else {}
    now = datetime.now(timezone.utc)
    missing_banks = {c.get('bank') for c in data['cards'] if not c.get('imageUrl')}
    jobs = []
    seen = set()
    for issuer in registry['issuers']:
        bank = issuer['name']
        if bank not in missing_banks:
            continue
        urls = issuer.get('cardCatalogUrls', [])
        hosts = {urlsplit(u).hostname for u in urls} | set(issuer.get('allowedHosts', []))
        for u in urls[:3]:
            if u not in seen:
                jobs.append((bank, u, hosts))
                seen.add(u)
        # Product source pages are also useful when catalog images have no alt.
        product_pages = [r.get('sourceUrl', '') for r in data['rules']
                         if r.get('bank') == bank and r.get('cardId')
                         and re.search(r'card|credit|ubear|unicard', r.get('sourceUrl', ''), re.I)]
        for u in dict.fromkeys(product_pages):
            if len(jobs) >= 120:
                break
            if u not in seen and urlsplit(u).hostname in hosts and urlsplit(u).scheme == 'https':
                jobs.append((bank, u, hosts))
                seen.add(u)
    candidates, pages = {}, []
    due = []
    for job in jobs:
        bank, url, hosts = job
        prior = cache.get(url, {})
        try:
            recent = (now - datetime.fromisoformat(prior['checkedAt'])).total_seconds() < 7 * 86400
        except (KeyError, ValueError, TypeError):
            recent = False
        if recent:
            candidates.setdefault(bank, []).extend((image, label, url) for image, label in prior.get('images', []))
            pages.append({'bank': bank, 'url': url, 'cached': True, 'error': prior.get('error', '')})
        else:
            due.append(job)
    with ThreadPoolExecutor(max_workers=4) as pool:
        for bank, url, rows, error in pool.map(fetch, due):
            candidates.setdefault(bank, []).extend((image, label, url) for image, label in rows)
            pages.append({'bank': bank, 'url': url, 'candidates': len(rows), 'error': error})
            cache[url] = {'checkedAt': now.isoformat(), 'images': rows, 'error': error}
    added = []
    for card in data['cards']:
        if card.get('imageUrl'):
            continue
        name = normalize(card.get('cardName'))
        bank = normalize(card.get('bank'))
        short = name.replace(bank, '') if bank else name
        if len(short) < 3:
            continue
        matches = [(image, label, url) for image, label, url in candidates.get(card.get('bank'), [])
                   if short in normalize(label) and not re.search(r'優惠|活動|banner|logo|icon', label, re.I)]
        unique = {image: (label, url) for image, label, url in matches}
        if len(unique) != 1:
            continue
        image, (label, url) = next(iter(unique.items()))
        card.update(imageUrl=image, imageSourceUrl=url, imageEvidence=label)
        added.append({'id': card['id'], 'cardName': card['cardName'], 'imageUrl': image})
    report = {'generatedAt': datetime.now(timezone.utc).isoformat(), 'added': added,
              'withImage': sum(bool(c.get('imageUrl')) for c in data['cards']),
              'missing': [{'id': c['id'], 'bank': c.get('bank'), 'cardName': c.get('cardName')}
                          for c in data['cards'] if not c.get('imageUrl')], 'pages': pages}
    if added:
        (ROOT / 'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'card_image_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'added': len(added), 'withImage': report['withImage'], 'missing': len(report['missing'])}))

if __name__ == '__main__':
    main()
