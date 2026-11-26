"""Audit every offer without equating schema checks with factual accuracy."""
import json
import math
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlsplit
from build_field_evidence_queue import REQUIRED_FIELDS, fresh_field_evidence

ROOT = Path(__file__).resolve().parents[2]

def audit(data, now=None):
    now = now or datetime.now(timezone.utc)
    cards = {c.get('id') for c in data.get('cards', [])}
    ids = set()
    rows = []
    counts = {}
    for rule in data.get('rules', []):
        issues = []
        rid = rule.get('id')
        if not rid or rid in ids:
            issues.append('DUPLICATE_OR_MISSING_ID')
        ids.add(rid)
        if rule.get('cardId') and rule['cardId'] not in cards:
            issues.append('ORPHAN_CARD')
        eligible_ids = rule.get('eligibleCardIds')
        if eligible_ids is not None:
            if (not isinstance(eligible_ids, list) or not eligible_ids
                    or any(not isinstance(card_id, str) for card_id in eligible_ids)
                    or len(eligible_ids) != len(set(eligible_ids))
                    or rule.get('cardId') not in eligible_ids
                    or any(card_id not in cards for card_id in eligible_ids)):
                issues.append('INVALID_ELIGIBLE_CARD_IDS')
        # A generic LINE Pay card cannot prove a Visa/JCB-specific offer's eligible product.
        if rule.get('cardId') == 'card_中國信託_51':
            scope_text = ' '.join(str(x) for x in [rule.get('title') or '',
                *(rule.get('fundingMethods') or []), *(rule.get('eligibilityRequirements') or [])])
            if 'Visa' in scope_text or 'JCB' in scope_text:
                issues.append('GENERIC_CARD_FOR_NETWORK_SPECIFIC_OFFER')
        if rule.get('unresolvedCardId') or rule.get('associationStatus') == 'needs_review':
            issues.append('UNRESOLVED_CARD_ASSOCIATION')
        for validation_issue in sorted(set(rule.get('validationIssues') or [])):
            issues.append('VALIDATION_' + str(validation_issue))
        try:
            u = urlsplit(rule.get('sourceUrl') or '')
            if u.scheme != 'https' or not u.hostname or u.username or u.password:
                issues.append('MISSING_OR_UNSAFE_SOURCE')
        except ValueError:
            issues.append('MISSING_OR_UNSAFE_SOURCE')
        for field in ('baseRate', 'promoRate', 'rewardAmount', 'capAmount', 'minimumSpend'):
            value = rule.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
                issues.append('INVALID_' + field.upper())
        fixed_proof = rule.get('fixedAwardEvidence') or {}
        has_fixed_proof = (fixed_proof.get('sourceUrl') == rule.get('sourceUrl')
                           and isinstance(fixed_proof.get('locator'), str)
                           and bool(fixed_proof['locator'].strip()))
        if (rule.get('rewardType') == 'points'
                and str(rule.get('rewardUnit') or '').lower() not in ('percent', '%')
                and (rule.get('baseRate') or rule.get('promoRate'))
                and isinstance(rule.get('rewardAmount'), (int, float))
                and not isinstance(rule.get('rewardAmount'), bool)
                and rule['rewardAmount'] > 0 and not has_fixed_proof):
            issues.append('AMBIGUOUS_PERCENT_AND_FIXED_POINT_REWARD')
        if not rule.get('validUntil'):
            issues.append('MISSING_CAMPAIGN_END')
        if not rule.get('fetchedAt'):
            issues.append('MISSING_FETCH_DATE')
        if rule.get('rewardCalculationMode') not in ('FLAT', 'TIERED', 'MAX_ONLY'):
            issues.append('UNKNOWN_CALCULATION')
        if rule.get('rewardCalculationMode') == 'MAX_ONLY':
            issues.append('MAXIMUM_ONLY')
        if rule.get('capAmount') is not None and rule.get('capScope') not in ('PROMO', 'TOTAL', 'NONE'):
            issues.append('UNKNOWN_CAP_SCOPE')
        if rule.get('needReg') and not (rule.get('registrationStart') and rule.get('registrationEnd')):
            issues.append('UNSTRUCTURED_REGISTRATION_WINDOW')
        if not rule.get('needReg') and (rule.get('registrationUrl') or any(
                method.get('type') in ('WEB', 'APP', 'PHONE') and '登錄' in str(method.get('label') or '')
                for method in (rule.get('registrationMethods') or []) if isinstance(method, dict))):
            issues.append('REGISTRATION_LINK_WITHOUT_REGISTRATION_REQUIREMENT')
        review = rule.get('accuracyReview') or {}
        if len(fresh_field_evidence(rule, now)) != len(REQUIRED_FIELDS):
            issues.append('MISSING_FIELD_TERM_EVIDENCE')
        # AI's legacy evidenceStatus=VERIFIED is intentionally not accepted here.
        if (review.get('status') != 'SOURCE_CHECKED' or not review.get('checkedAt') or not review.get('fields')
                or review.get('method') != 'official_terms_read' or not review.get('evidence')
                or rule.get('sourceUrl') not in (review.get('evidenceSources') or [])):
            issues.append('NO_INDEPENDENT_TERM_REVIEW')
        else:
            try:
                checked = datetime.fromisoformat(review['checkedAt'].replace('Z', '+00:00'))
                if checked.tzinfo is None or not 0 <= (now - checked).total_seconds() <= 14 * 86400:
                    issues.append('STALE_TERM_REVIEW')
                if review.get('sourceUrl') != rule.get('sourceUrl') or review.get('issues') or rule.get('validationIssues'):
                    issues.append('TERM_REVIEW_CONFLICT')
                snapshot = review.get('termsSnapshot')
                if not isinstance(snapshot, dict) or not snapshot:
                    issues.append('MISSING_REVIEW_SNAPSHOT')
                elif any(rule.get(field) != value for field, value in snapshot.items()):
                    issues.append('REVIEWED_TERMS_CHANGED')
            except (ValueError, TypeError):
                issues.append('INVALID_REVIEW_DATE')
        for issue in issues:
            counts[issue] = counts.get(issue, 0) + 1
        rows.append({'id': rid, 'bank': rule.get('bank'), 'title': rule.get('title'), 'issues': issues})
    return {'generatedAt': now.isoformat(), 'targetAccuracy': .98, 'measuredAccuracy': None,
            'coveragePercent': None, 'acceptanceStatus': 'NOT_ESTABLISHED',
            'reason': '需要獨立官方基準清單及逐欄核對；結構通過率、測試通過率都不是優惠準確率。',
            'totalRules': len(rows), 'issueCounts': counts, 'rules': rows}

def main():
    data = json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))
    report = audit(data)
    (ROOT / 'accuracy_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'rules'}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
