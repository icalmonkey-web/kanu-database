"""Compare a separately curated official fixture with selected app records.

Matching fields in one narrow fixture never establishes market accuracy or recall.
"""
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from repair_sources import atomic_json

ROOT = Path(__file__).resolve().parents[2]
BASELINE_DIR = ROOT / 'official_baselines'
DATA = ROOT / 'data.json'
REPORT = ROOT / 'official_baseline_report.json'


def compare(baseline, mapping, data):
    if baseline.get('baselineId') != mapping.get('baselineId'):
        raise ValueError('baseline_mapping_id_mismatch')
    offers = {row['id']: row for row in baseline['offers']}
    rules = {row['id']: row for row in data['rules']}
    mapped_ids = [row['offerId'] for row in mapping['mappings']]
    if len(mapped_ids) != len(set(mapped_ids)) or any(offer_id not in offers for offer_id in mapped_ids):
        raise ValueError('duplicate_or_unknown_baseline_mapping')
    rows = []
    for link in mapping['mappings']:
        expected = offers[link['offerId']]
        rule = rules.get(link['ruleId'])
        tier_index = link.get('tierIndex')
        tiers = rule.get('rewardTiers') or [] if rule else []
        tier = tiers[tier_index] if isinstance(tier_index, int) and 0 <= tier_index < len(tiers) else {}
        checks = {}
        for field, evidence in expected['fields'].items():
            value = evidence['value'] if isinstance(evidence, dict) else evidence
            actual = tier.get(field, rule.get(field)) if rule else None
            checks[field] = {'expected': value, 'actual': actual,
                             'matches': actual == value and rule is not None,
                             'sourceLineHint': evidence.get('sourceLineHint') if isinstance(evidence, dict) else None,
                             'sourceSection': evidence.get('sourceSection') if isinstance(evidence, dict) else None}
        rows.append({'offerId': expected['id'], 'ruleId': link['ruleId'],
                     'rulePresent': rule is not None, 'fieldChecks': checks,
                     'conditionsAssessed': False})
    matched = sum(check['matches'] for row in rows for check in row['fieldChecks'].values())
    total = sum(len(row['fieldChecks']) for row in rows)
    observed = date.fromisoformat(baseline['observedAt']) if baseline.get('observedAt') else None
    today = datetime.now(ZoneInfo('Asia/Taipei')).date()
    fresh = bool(observed and timedelta(0) <= today - observed <= timedelta(days=14))
    return {'baselineId': baseline['baselineId'], 'scope': baseline['scope'],
            'sourceUrl': baseline['sourceUrl'], 'baselineOffers': len(offers),
            'observedAt': baseline.get('observedAt'), 'baselineFresh': fresh,
            'unmappedOfficialOffers': sorted(set(offers) - set(mapped_ids)),
            'mappedOffers': len(rows), 'structuredFieldsMatched': matched,
            'structuredFieldsCompared': total, 'rows': rows,
            'acceptanceStatus': 'NOT_ESTABLISHED', 'marketAccuracyPercent': None,
            'marketCoveragePercent': None,
            'limitations': 'Only selected structured fields were compared. Eligibility, exclusions, all official offers, and independent blind sampling are not assessed.'}


if __name__ == '__main__':
    data = json.loads(DATA.read_text(encoding='utf-8'))
    reports = []
    for mapping_path in sorted(BASELINE_DIR.glob('*_mapping.json')):
        baseline_path = mapping_path.with_name(mapping_path.name.replace('_mapping.json', '.json'))
        baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
        mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
        reports.append(compare(baseline, mapping, data))
    report = {'generatedAt': datetime.now(timezone.utc).isoformat(),
              'baselineCount': len(reports), 'baselines': reports,
              'acceptanceStatus': 'NOT_ESTABLISHED', 'marketAccuracyPercent': None,
              'marketCoveragePercent': None,
              'limitations': 'Curated fixtures cover only named sources and selected fields; conditions and whole-market recall remain unmeasured.'}
    atomic_json(REPORT, report)
    print(json.dumps({'baselineCount': len(reports), 'baselineIds': [r['baselineId'] for r in reports],
                      'acceptanceStatus': report['acceptanceStatus']}, ensure_ascii=False))
