"""Correct payment and rounding while quarantining ambiguous cap scope."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_pet.html'
OFFERS = {
    'rule_959a861cabb8b515f17f': {
        'merchant': '魚中魚貓狗水族大賣場', 'short': '魚中魚',
        'total': 4, 'bonus': 3, 'minimum': 1500, 'cap': 150,
        'listing': 'L28-L32', 'terms': 'L125-L134', 'key': 'L128', 'rounding': 'L132',
    },
    'rule_b0e3b7c1e8eb9111f052': {
        'merchant': '好狗命寵物幸福生活城', 'short': '好狗命',
        'total': 5, 'bonus': 4, 'minimum': 1800, 'cap': 180,
        'listing': 'L34-L38', 'terms': 'L135-L144', 'key': 'L138', 'rounding': 'L142',
    },
}


def correct(data):
    by_id = {r['id']: r for r in data['rules']}
    for rule_id, item in OFFERS.items():
        r = by_id[rule_id]
        r.update({
            'title': f"{item['short']}單筆滿NT${item['minimum']:,}享LINE POINTS {item['total']}%",
            'sourceUrl': SOURCE, 'validFrom': '2026-01-01', 'validUntil': '2026-12-31',
            'offerDomain': 'CARD', 'paymentProvider': '',
            'fundingMethods': ['中國信託LINE Pay卡直接刷卡或綁定LINE Pay、行動支付、第三方支付'],
            'baseRate': 1, 'promoRate': item['bonus'],
            'rewardType': 'points', 'rewardUnit': 'percent', 'rewardAmount': None,
            'pointValueTwd': None, 'capAmount': item['cap'],
            'capPeriod': 'MONTHLY', 'capScope': 'UNKNOWN',
            'roundingMode': 'ROUND_COMPONENT', 'spendBasis': 'PER_TRANSACTION',
            'minimumSpend': item['minimum'], 'rewardCalculationMode': 'FLAT',
            'rewardTiers': [], 'maxRateRequires': [],
            'eligibilityRequirements': [
                f"於參與活動之{item['merchant']}單筆消費滿NT${item['minimum']:,}",
                '中國信託LINE Pay卡可直接刷卡，亦可綁定LINE Pay、行動支付或第三方支付',
                '需確認店家仍參與活動及本月剩餘回饋額度',
            ],
            'excludedKeywords': ['分期交易', '付款失敗', '訂單退貨'],
            'quotaInfo': f"每人每月上限{item['cap']}點；官方未明示此上限是否包含一般1%，暫停試算。",
            'benefitSummary': f"單筆滿NT${item['minimum']:,}享LINE POINTS {item['total']}%（含基本1%）；每人每月上限{item['cap']}點，上限適用範圍待核。",
            'quickSearchEligible': False,
            'validationIssues': ['CAP_SCOPE_UNVERIFIED', 'MERCHANT_ELIGIBILITY_UNVERIFIED'],
            'sourceFacts': {'sourceUrl': SOURCE, 'checkedAt': '2026-11-08T00:30:00+08:00',
                            'locators': {'listing': item['listing'], 'terms': item['terms']}},
        })
        locators = {
            'title': f"活動標題／{item['listing']}",
            'cardEligibility': f"LINE Pay卡直接或綁定付款／{item['key']}",
            'reward': f"含基本1%的{item['total']}%／{item['key']}",
            'rewardType': f"LINE POINTS／{item['key']}",
            'validFrom': f"列表日期／{item['listing']}",
            'validUntil': f"列表日期／{item['listing']}",
            'minimumSpend': f"單筆NT${item['minimum']:,}／{item['key']}",
            'exclusions': f"分期、付款失敗、退貨／{item['terms']}",
            'rounding': f"加碼點數四捨五入／{item['rounding']}",
        }
        fields = {field: {'status': 'supported', 'sourceUrl': SOURCE, 'locator': locator}
                  for field, locator in locators.items()}
        fields['registration'] = {'status': 'not_applicable', 'sourceUrl': SOURCE,
                                  'locator': f"完整活動注意事項／{item['terms']}",
                                  'reason': '活動未列銀行登錄步驟；LINE Pay綁定是收點資格'}
        r['termEvidence'] = {'sourceUrl': SOURCE, 'checkedAt': '2026-11-08T00:30:00+08:00',
                             'method': 'manual_official_terms_read', 'fields': fields,
                             'unresolved': ['cap']}
    return len(OFFERS)


def main():
    path = ROOT / 'data.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    count = correct(data)
    data['version'] = '2026.11.08-v350000-petpayment'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'corrected {count} CTBC pet offers; cap scope remains blocked')


if __name__ == '__main__':
    main()
