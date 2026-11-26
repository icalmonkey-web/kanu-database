"""Attribute bankless offers to the issuer of their existing official source host.

This does not establish card eligibility or validate any reward terms.
"""
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from repair_sources import atomic_json

ROOT = Path(__file__).resolve().parents[2]


def attribute(data, registry):
    cards = {card.get('id'): card for card in data.get('cards', [])}
    hosts = defaultdict(set)
    for issuer in registry.get('issuers', []):
        for host in issuer.get('allowedHosts', []):
            hosts[host.lower()].add(issuer.get('name'))
    changes = []
    for rule in data.get('rules', []):
        if rule.get('bank') or not rule.get('sourceUrl'):
            continue
        try:
            url = urlsplit(rule['sourceUrl'])
        except ValueError:
            continue
        if url.scheme != 'https' or url.username or url.password or not url.hostname:
            continue
        matches = hosts.get(url.hostname.lower(), set())
        if len(matches) != 1:
            continue
        bank = next(iter(matches))
        if rule.get('cardId') and cards.get(rule['cardId'], {}).get('bank') != bank:
            continue
        rule['bank'] = bank
        rule['bankAttributionMethod'] = 'official_source_host'
        changes.append({'id': rule.get('id'), 'bank': bank, 'sourceHost': url.hostname})
    return changes


if __name__ == '__main__':
    data_path = ROOT / 'data.json'
    data = json.loads(data_path.read_text(encoding='utf-8'))
    registry = json.loads((ROOT / 'issuer_registry.json').read_text(encoding='utf-8'))
    changes = attribute(data, registry)
    if changes:
        data['version'] = datetime.now(timezone.utc).strftime('%Y.%m.%d-v%H%M%S') + '-bankhosts1'
        atomic_json(data_path, data)
    atomic_json(ROOT / 'bank_attribution_report.json', {'attributed': len(changes),
        'note': 'Bank identified by official source host only; card eligibility and offer terms remain unverified.',
        'changes': changes})
    print('bank attribution:', len(changes))
