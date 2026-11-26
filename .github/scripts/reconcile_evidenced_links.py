"""Restore card links only when title names exactly one distinctive product."""
import json
import re
from collections import defaultdict
from pathlib import Path
from audit_accuracy import audit

ROOT = Path(__file__).resolve().parents[2]
IGNORE = {'CARD', 'CREDIT', 'BANK', 'VISA', 'MASTER', 'JCB', 'PLATINUM', 'WALLET', 'PAY', 'PAYMENT'}

def tokens(card):
    name = str(card.get('cardName') or '').upper()
    words = set(re.findall(r'[A-Z][A-Z0-9@+-]{3,}', name)) - IGNORE
    cleaned = re.sub(r'信用卡|聯名卡|御璽卡|鈦金卡|世界卡|白金卡|商務卡|銀行|國泰世華|玉山|永豐|台新|富邦|卡', '', name)
    if len(cleaned) >= 4: words.add(cleaned)
    return {w for w in words if len(w) >= 4}

def reconcile(data):
    cards = data.get('cards', [])
    by_id = {c.get('id'): c for c in cards}
    results = []
    for rule in data.get('rules', []):
        old = str(rule.get('unresolvedCardId') or '')
        if not old or rule.get('cardId'):
            continue
        title = re.sub(r'\s+', '', str(rule.get('title') or '').upper())
        old_token = re.sub(r'^CARD_', '', old.upper())
        matches = []
        for card in cards:
            aliases = tokens(card)
            # Require both an exact legacy identifier suffix and a product name
            # in the activity title; no bank-first-card or portal URL fallback.
            if any(alias in title and (alias in old_token or old_token.endswith(alias)) for alias in aliases):
                matches.append(card)
        unique = list({c['id']:c for c in matches}.values())
        if len(unique) != 1:
            continue
        card = unique[0]
        if rule.get('bank') and rule['bank'] != card.get('bank'):
            continue
        rule['cardId'] = card['id']
        rule['bank'] = card.get('bank')
        rule['associationStatus'] = 'title_and_legacy_id_match'
        rule['cardLinkEvidence'] = {'legacyId':old,'title':rule.get('title'),'cardName':card.get('cardName')}
        rule.pop('unresolvedCardId', None)
        rule['quickSearchEligible'] = bool(rule.get('sourceUrl')) and rule.get('quickSearchEligible') is not False
        results.append({'id':rule.get('id'),'cardId':card['id'],'legacyId':old})
    return results

if __name__ == '__main__':
    path = ROOT/'data.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    results = reconcile(data)
    if results:
        data['version'] += '-cardlinks1'
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2),encoding='utf-8')
    (ROOT/'card_link_repair_report.json').write_text(json.dumps({'repaired':len(results),'matches':results},ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'accuracy_report.json').write_text(json.dumps(audit(data),ensure_ascii=False,indent=2),encoding='utf-8')
    print('evidenced card links:',len(results))
