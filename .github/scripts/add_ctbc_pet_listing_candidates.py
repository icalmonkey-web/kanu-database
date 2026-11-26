"""Map the independently read pet listing; keep missing terms quarantined."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / 'official_catalogs/ctbc_linepay_pet_2026.json'
MAPPING = ROOT / 'official_catalogs/ctbc_linepay_pet_2026_mapping.json'
DATA = ROOT / 'data.json'
KNOWN = {
    'fish': 'rule_959a861cabb8b515f17f',
    'good_life': 'rule_b0e3b7c1e8eb9111f052',
    'good_dog': 'rule_8993c54bfe963a2c628a',
    'popocat': 'rule_d4ed298d1db9c2c09f54',
    'wonderpet': 'rule_5597df0306591339c831',
    'petstimes': 'rule_135b9e6c4621fc0c2dc8',
    'ladynpet': 'rule_80b907fa6a35daa916fd',
    'dogcatstar': 'pending_ctbc_linepay_pet_2026_dogcatstar',
    'litomon': 'pending_ctbc_linepay_pet_2026_litomon',
    'heromama': 'pending_ctbc_linepay_pet_2026_heromama',
    'maohao': 'pending_ctbc_linepay_pet_2026_maohao',
    'petlife': 'pending_ctbc_linepay_pet_2026_petlife',
}


def main():
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    data = json.loads(DATA.read_text(encoding='utf-8'))
    assert len(catalog['offers']) == 12
    ids = {rule['id'] for rule in data['rules']}
    assert set(KNOWN.values()) <= ids
    mappings = []
    added = 0
    for offer in catalog['offers']:
        if offer['id'] in KNOWN:
            mappings.append({'offerId': offer['id'], 'ruleId': KNOWN[offer['id']],
                             'status': 'matched'})
            continue
        rule_id = 'pending_ctbc_linepay_pet_2026_' + offer['id']
        mappings.append({'offerId': offer['id'], 'ruleId': rule_id,
                         'status': 'candidate',
                         'reason': '只有官方列表入口與日期；完整卡別、付款、回饋上限、名額及登錄待核，暫停推薦'})
        if rule_id in ids:
            continue
        provider = {'LINE_PAY': 'LINE Pay', 'SHOPBACK': 'ShopBack'}.get(offer['channel'], '')
        data['rules'].append({
            'id': rule_id, 'bank': '中國信託', 'cardId': '',
            'offerDomain': 'PAYMENT' if provider else 'CARD',
            'paymentProvider': provider,
            'title': offer['name'] + '（官方列表；條款待核）',
            'activityType': 'UNKNOWN', 'scope': 'SPECIFIC',
            'eligibleCardScope': 'UNKNOWN',
            'matchedMerchants': [offer['matchToken']],
            'searchKeywords': offer['matchToken'],
            'benefitSummary': '官方列表入口：' + offer['name'] + '。完整資格、回饋、排除與登錄條款待核。',
            'rewardType': 'unknown', 'rewardUnit': 'unknown',
            'rewardAmount': None, 'baseRate': 0, 'promoRate': 0,
            'capAmount': None, 'minimumSpend': 0, 'needReg': False,
            'validFrom': offer['validFrom'], 'validUntil': offer['validUntil'],
            'sourceUrl': catalog['sourceUrl'], 'registrationUrl': '',
            'registrationMethods': [], 'quickSearchEligible': False,
            'validationIssues': ['LISTING_ONLY_TERMS_UNVERIFIED',
                                 'CARD_ELIGIBILITY_UNVERIFIED',
                                 'REGISTRATION_REQUIREMENT_UNVERIFIED'],
            'sourceFacts': {'checkedAt': '2026-11-08T00:20:00+08:00',
                            'sourceUrl': catalog['sourceUrl'],
                            'locators': {'listing': 'L' + str(offer['sourceLineHint'])}},
            'fetchedAt': '2026-11-08T00:20:00+08:00',
        })
        ids.add(rule_id)
        added += 1
    MAPPING.write_text(json.dumps({'catalogId': catalog['catalogId'], 'mappings': mappings},
                                  ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if added:
        data['version'] = '2026.11.08-v340000-petcatalog'
        DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'added {added} listing-only candidates; mapped {len(mappings)} official entries')


if __name__ == '__main__':
    main()
