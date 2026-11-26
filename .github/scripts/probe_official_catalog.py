"""Probe the current official listing; never certify coverage from a stale fixture.

This detects changes for the currently inventoried CTBC pages. A human still has
to read new entries and their detailed terms before editing the catalog.
"""
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests

from repair_sources import atomic_json

ROOT = Path(__file__).resolve().parents[2]
CATALOGS = ROOT / 'official_catalogs'
REPORT = ROOT / 'official_catalog_live_report.json'


class ListingText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'noscript'}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'noscript'} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def listing_text(html):
    parser = ListingText()
    parser.feed(html)
    text = ' '.join(parser.parts)
    # Both CTBC pages list the visible activity entrances before the first
    # credit-risk footer. Hidden detail panels follow that footer.
    marker = text.find('謹慎理財')
    return re.sub(r'\s+', ' ', text[:marker if marker >= 0 else len(text)]).strip(), marker >= 0


def inspect(catalog, html):
    listing, found_boundary = listing_text(html)
    rows = []
    listing_offers = [offer for offer in catalog['offers'] if not offer.get('detailOnly')]
    for offer in listing_offers:
        token = offer['matchToken']
        occurrences = [m.start() for m in re.finditer(re.escape(token), listing, re.I)]
        date_token = offer['validFrom'].replace('-', '/') + '~' + offer['validUntil'].replace('-', '/')
        # The dates must appear near the activity name, not somewhere else on
        # the page. Minor spacing around the range separator is allowed.
        def date_pattern(value):
            year, month, day = map(int, value.split('-'))
            return rf'{year}\s*/\s*0?{month}\s*/\s*0?{day}'
        date_re = re.compile(date_pattern(offer['validFrom']) +
                             r'\s*[~～−–-]\s*' + date_pattern(offer['validUntil']))
        nearby = any(date_re.search(listing[pos:pos + 240]) for pos in occurrences)
        rows.append({'offerId': offer['id'], 'tokenPresent': bool(occurrences),
                     'datesNearToken': nearby, 'expectedDateRange': date_token})
    missing = [r['offerId'] for r in rows if not r['tokenPresent']]
    changed = [r['offerId'] for r in rows if r['tokenPresent'] and not r['datesNearToken']]
    # The count is only a drift signal; it is not used to assert that all live
    # offers have been discovered. CTBC buttons and linked detail labels vary.
    detail_labels = len(re.findall('活動詳情', listing))
    expected_detail_labels = sum(not offer.get('listingActionOnly') for offer in listing_offers)
    status = ('UNVERIFIED_LAYOUT' if not found_boundary or detail_labels < expected_detail_labels
              else 'POSSIBLE_DRIFT' if missing or changed or detail_labels != expected_detail_labels
              else 'KNOWN_ENTRIES_PRESENT')
    return {'catalogId': catalog['catalogId'], 'status': status,
            'knownOfferCount': len(rows), 'listingDetailLabels': detail_labels,
            'expectedDetailLabels': expected_detail_labels,
            'listingBoundaryFound': found_boundary, 'missingKnownOffers': missing,
            'changedDateOffers': changed, 'rows': rows,
            'note': '只偵測既有入口及列表數量變動；無法自行識別新活動的全部條款或證明收錄率。'}


def run(fetch=requests.get):
    reports = []
    for path in sorted(CATALOGS.glob('*.json')):
        if path.name.endswith('_mapping.json'):
            continue
        catalog = json.loads(path.read_text(encoding='utf-8'))
        try:
            response = fetch(catalog['sourceUrl'], timeout=25)
            response.raise_for_status()
            result = inspect(catalog, response.text)
            result['checkedAt'] = datetime.now(timezone.utc).isoformat()
        except (requests.RequestException, ValueError) as exc:
            result = {'catalogId': catalog['catalogId'], 'status': 'FETCH_FAILED',
                      'checkedAt': datetime.now(timezone.utc).isoformat(),
                      'error': str(exc)[:300],
                      'knownOfferCount': sum(not offer.get('detailOnly') for offer in catalog['offers']),
                      'note': '本輪未能核對官網清單，不可將靜態清單視為當日有效。'}
        reports.append(result)
    report = {'generatedAt': datetime.now(timezone.utc).isoformat(), 'catalogs': reports,
              'allKnownListingsRechecked': all(r['status'] == 'KNOWN_ENTRIES_PRESENT' for r in reports),
              'marketCoveragePercent': None, 'acceptanceStatus': 'NOT_ESTABLISHED'}
    atomic_json(REPORT, report)
    return report


if __name__ == '__main__':
    result = run()
    print(json.dumps([{'catalogId': r['catalogId'], 'status': r['status'],
                       'missingKnownOffers': r.get('missingKnownOffers', []),
                       'changedDateOffers': r.get('changedDateOffers', [])}
                      for r in result['catalogs']], ensure_ascii=False))
