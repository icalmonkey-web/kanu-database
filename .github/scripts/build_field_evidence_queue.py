"""Queue every rule missing fresh field-level official evidence.

This report is a worklist, not a claim that missing fields are false or that
source-title matches prove an offer's terms.
"""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from repair_sources import atomic_json

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_FIELDS = ('title', 'cardEligibility', 'reward', 'rewardType', 'validFrom',
                   'validUntil', 'cap', 'minimumSpend', 'registration',
                   'exclusions', 'rounding')


def parse_date(value):
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except (TypeError, ValueError):
        return None


def date_bucket(rule, today):
    start, end = parse_date(rule.get('validFrom')), parse_date(rule.get('validUntil'))
    if end and end < today:
        return 'EXPIRED'
    if start and start > today:
        return 'UPCOMING'
    if start and end:
        return 'DATE_WINDOW_INCLUDES_TODAY'
    return 'DATE_WINDOW_UNCONFIRMED'


def fresh_field_evidence(rule, now):
    record = rule.get('termEvidence') or {}
    if record.get('method') != 'manual_official_terms_read' or record.get('sourceUrl') != rule.get('sourceUrl'):
        return set()
    try:
        checked = datetime.fromisoformat(str(record['checkedAt']).replace('Z', '+00:00'))
    except (KeyError, TypeError, ValueError):
        return set()
    if checked.tzinfo is None or not 0 <= (now - checked).total_seconds() <= 14 * 86400:
        return set()
    return {field for field in REQUIRED_FIELDS if
            (record.get('fields', {}).get(field) or {}).get('status') in {'supported', 'not_applicable'}
            and (record['fields'][field].get('sourceUrl') == rule.get('sourceUrl'))
            and record['fields'][field].get('locator')
            and (record['fields'][field].get('status') != 'not_applicable' or record['fields'][field].get('reason'))}


def build_queue(data, state=None, now=None):
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo('Asia/Taipei')).date()
    pages = (state or {}).get('pages', {})
    rows = []
    for rule in data.get('rules', []):
        bucket = date_bucket(rule, today)
        supported = fresh_field_evidence(rule, now)
        source = rule.get('sourceUrl') or ''
        claims = pages.get(source, {}).get('claims', [])
        title_candidate = next((claim.get('status') for claim in claims
                                if claim.get('ruleId') == rule.get('id')), None)
        machine = rule.get('sourceClaimEvidence') or {}
        score = (100 if bucket == 'DATE_WINDOW_INCLUDES_TODAY' else 25 if bucket == 'DATE_WINDOW_UNCONFIRMED' else 0)
        score += 30 if rule.get('quickSearchEligible') is not False else 0
        score += 20 if source else 0
        score += 10 if rule.get('cardId') and not rule.get('unresolvedCardId') else 0
        rows.append({'id': rule.get('id'), 'bank': rule.get('bank'), 'title': rule.get('title'),
                     'dateBucket': bucket, 'sourceUrl': source, 'priority': score,
                     'missingFields': [field for field in REQUIRED_FIELDS if field not in supported],
                     'supportedFieldCount': len(supported), 'titleLocatorCandidate': title_candidate,
                     'machineCandidateFields': sorted(field for field, item in
                         (machine.get('fields') or {}).items() if item.get('status') == 'candidate_present')})
    rows.sort(key=lambda row: (-row['priority'], row['bank'] or '', row['id'] or ''))
    counts = Counter(row['dateBucket'] for row in rows)
    return {'generatedAt': now.isoformat(), 'totalRules': len(rows),
            'dateBucketCounts': dict(counts),
            'rulesMissingAnyFieldEvidence': sum(bool(row['missingFields']) for row in rows),
            'fieldEvidenceCoverageIsAccuracy': False,
            'requiredFields': list(REQUIRED_FIELDS), 'queue': rows}


if __name__ == '__main__':
    data = json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))
    state_path = ROOT / 'source_title_state.json'
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else {}
    report = build_queue(data, state)
    atomic_json(ROOT / 'field_evidence_queue.json', report)
    print(json.dumps({key: value for key, value in report.items() if key != 'queue'}, ensure_ascii=False))
