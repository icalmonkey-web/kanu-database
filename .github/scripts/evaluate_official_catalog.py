"""Report presence gaps against independently read official activity lists.

This is scoped record presence, never a claim of factual accuracy or market recall.
"""
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from repair_sources import atomic_json

ROOT = Path(__file__).resolve().parents[2]
CATALOGS = ROOT / 'official_catalogs'


def evaluate(catalog, mapping, data):
    if catalog['catalogId'] != mapping['catalogId']:
        raise ValueError('catalog_mapping_id_mismatch')
    offers = {row['id']: row for row in catalog['offers']}
    if len(offers) != len(catalog['offers']):
        raise ValueError('duplicate_official_offer')
    links = {row['offerId']: row for row in mapping['mappings']}
    if len(links) != len(mapping['mappings']) or set(links) - set(offers):
        raise ValueError('duplicate_or_unknown_mapping')
    rules = {row['id']: row for row in data['rules']}
    rows = []
    for offer in catalog['offers']:
        link = links.get(offer['id'])
        rule_ids = link.get('ruleIds', [link['ruleId']] if 'ruleId' in link else []) if link else []
        if not rule_ids or len(rule_ids) != len(set(rule_ids)):
            if link:
                raise ValueError('empty_or_duplicate_rule_mapping')
        mapped_rules = [rules.get(rule_id) for rule_id in rule_ids]
        present_count = sum(rule is not None for rule in mapped_rules)
        missing_rule_ids = [rule_id for rule_id, rule in zip(rule_ids, mapped_rules) if rule is None]
        dates_match = bool(mapped_rules and all(rule and all(rule.get(key) == offer[key]
                           for key in ('validFrom', 'validUntil')) for rule in mapped_rules))
        allowed_sources = {catalog['sourceUrl'], offer.get('detailUrl')}
        same_source = bool(mapped_rules and all(rule and rule.get('sourceUrl') in allowed_sources
                                                for rule in mapped_rules))
        token = offer.get('matchToken', '')
        title_match = bool(mapped_rules and token and all(rule and token.casefold() in
                           ' '.join([rule.get('title', ''), *(rule.get('matchedMerchants') or [])]).casefold()
                           for rule in mapped_rules))
        status = ('missing' if not present_count else
                  'matched' if link and link['status'] == 'matched' and dates_match and title_match
                  and same_source else 'candidate')
        rows.append({'offerId': offer['id'], 'name': offer['name'], 'channel': offer['channel'],
                     'sourceLineHint': offer['sourceLineHint'], 'ruleIds': rule_ids,
                     'presentRuleCount': present_count, 'missingRuleIds': missing_rule_ids,
                     'status': status, 'datesMatch': dates_match, 'sameSource': same_source,
                     'titleMatch': title_match,
                     'reason': link.get('reason') if link else None})
    matched = sum(row['status'] == 'matched' for row in rows)
    observed = date.fromisoformat(catalog['observedAt'])
    age = datetime.now(ZoneInfo('Asia/Taipei')).date() - observed
    fresh = timedelta(0) <= age <= timedelta(days=14)
    return {'catalogId': catalog['catalogId'], 'scope': catalog['scope'],
            'observedAt': catalog['observedAt'], 'sourceUrl': catalog['sourceUrl'],
            'catalogFresh': fresh,
            'officialOffers': len(rows), 'matchedRecords': matched,
            'candidateRecords': sum(row['status'] == 'candidate' for row in rows),
            'missingRecords': sum(row['status'] == 'missing' for row in rows),
            'scopedListingMatchPercent': round(100 * matched / len(rows), 2) if rows else None,
            'fullTermsVerifiedPercent': None,
            'marketAccuracyPercent': None, 'marketCoveragePercent': None,
            'acceptanceStatus': 'NOT_ESTABLISHED', 'rows': rows}


if __name__ == '__main__':
    data = json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))
    live_path = ROOT / 'official_catalog_live_report.json'
    live_rows = {}
    if live_path.exists():
        live = json.loads(live_path.read_text(encoding='utf-8'))
        for row in live.get('catalogs', []):
            checked = datetime.fromisoformat(row['checkedAt'])
            if timedelta(0) <= datetime.now(timezone.utc) - checked <= timedelta(hours=24):
                live_rows[row['catalogId']] = row
    reports = []
    for mapping_path in sorted(CATALOGS.glob('*_mapping.json')):
        catalog_path = mapping_path.with_name(mapping_path.name.replace('_mapping.json', '.json'))
        report = evaluate(json.loads(catalog_path.read_text(encoding='utf-8')),
                          json.loads(mapping_path.read_text(encoding='utf-8')), data)
        live_row = live_rows.get(report['catalogId'])
        report['liveListingStatus'] = live_row['status'] if live_row else 'NOT_RECHECKED_IN_24H'
        report['liveCheckedAt'] = live_row.get('checkedAt') if live_row else None
        report['liveMissingKnownOffers'] = live_row.get('missingKnownOffers', []) if live_row else []
        report['liveChangedDateOffers'] = live_row.get('changedDateOffers', []) if live_row else []
        report['liveListingMatchPercent'] = (report['scopedListingMatchPercent']
                                             if report['liveListingStatus'] == 'KNOWN_ENTRIES_PRESENT'
                                             else None)
        reports.append(report)
    report = {'generatedAt': datetime.now(timezone.utc).isoformat(), 'catalogs': reports,
              'acceptanceStatus': 'NOT_ESTABLISHED', 'marketAccuracyPercent': None,
              'marketCoveragePercent': None,
              'limitations': 'Static catalog presence is not live coverage. Check liveListingStatus for source drift; neither report proves full terms, current quota, or market recall.'}
    atomic_json(ROOT / 'official_catalog_report.json', report)
    print(json.dumps([{'catalogId': row['catalogId'], 'officialOffers': row['officialOffers'],
                       'matchedRecords': row['matchedRecords'], 'candidateRecords': row['candidateRecords'],
                       'missingRecords': row['missingRecords']} for row in reports], ensure_ascii=False))
