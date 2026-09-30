"""Deterministic structural repair. Preserve ambiguous records for review."""
import hashlib
import json
from pathlib import Path
from audit_accuracy import audit

ROOT = Path(__file__).resolve().parents[2]

def repair(data):
    cards = {c['id'] for c in data['cards']}
    seen = set()
    changes = {'renamedDuplicateIds': 0, 'quarantinedOrphanLinks': 0}
    for rule in data['rules']:
        rid = rule.get('id')
        if not rid or rid in seen:
            rule['legacyId'] = rid
            digest = hashlib.sha256(json.dumps(rule, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:20]
            candidate = 'rule_repaired_' + digest
            suffix = 1
            while candidate in seen:
                suffix += 1
                candidate = 'rule_repaired_' + digest + '_' + str(suffix)
            rule['id'] = candidate
            changes['renamedDuplicateIds'] += 1
        seen.add(rule['id'])
        if rule.get('cardId') and rule['cardId'] not in cards:
            rule['unresolvedCardId'] = rule['cardId']
            rule['cardId'] = None
            rule['associationStatus'] = 'needs_review'
            rule['quickSearchEligible'] = False
            changes['quarantinedOrphanLinks'] += 1
    return changes

if __name__ == '__main__':
    data = json.loads((ROOT / 'data.json').read_text(encoding='utf-8'))
    changes = repair(data)
    if any(changes.values()):
        data['version'] += '-accuracy1'
    (ROOT / 'data.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'accuracy_report.json').write_text(json.dumps(audit(data), ensure_ascii=False, indent=2), encoding='utf-8')
    print(changes)
