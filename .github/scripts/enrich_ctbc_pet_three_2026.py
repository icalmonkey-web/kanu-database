"""Read three CTBC pet LINE Pay detail sections into existing list candidates."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_pet.html'
CHECKED = '2026-11-08T00:32:00+08:00'
ITEMS = {
    'pending_ctbc_linepay_pet_2026_dogcatstar': {
        'merchant': '汪喵星球', 'minimum': 1000, 'cap': 40, 'pool': 684000,
        'listing': 'L75-L79', 'detail': 'L262-L293', 'main': 'L267-L269',
        'qualification': 'L271-L280',
    },
    'pending_ctbc_linepay_pet_2026_litomon': {
        'merchant': '怪獸部落', 'minimum': 500, 'cap': 30, 'pool': 336000,
        'listing': 'L83-L87', 'detail': 'L294-L325', 'main': 'L299-L301',
        'qualification': 'L303-L312',
    },
    'pending_ctbc_linepay_pet_2026_heromama': {
        'merchant': 'HeroMama', 'minimum': 300, 'cap': 30, 'pool': 210000,
        'listing': 'L91-L95', 'detail': 'L326-L357', 'main': 'L331-L333',
        'qualification': 'L335-L344',
    },
}


def enrich(data):
    by_id = {r['id']: r for r in data['rules']}
    for rule_id, x in ITEMS.items():
        r = by_id[rule_id]
        merchant = x['merchant']
        r.update({
            'bank': '中國信託', 'cardId': 'card_中國信託_51',
            'eligibleCardIds': ['card_中國信託_51', 'card_中國信託_241',
                                'card_中國信託_242', 'card_中國信託_324',
                                'card_中國信託_327', 'card_中國信託_328'],
            'eligibleCardScope': 'SELECTED_CARDS',
            'cardAssociationEvidence': {'sourceUrl': SOURCE,
                'locator': '信用卡或簽帳金融卡綁定 LINE Pay／' + x['qualification']},
            'offerDomain': 'PAYMENT', 'paymentProvider': 'LINE Pay',
            'fundingMethods': ['LINE Pay綁定中國信託LINE Pay信用卡或簽帳金融卡'],
            'title': f'{merchant}官網：LINE Pay單筆滿NT${x["minimum"]:,}最高5% LINE POINTS',
            'activityType': 'DIRECT_PROMOTION', 'scope': 'SPECIFIC',
            'matchedMerchants': [merchant], 'searchKeywords': merchant,
            'baseRate': 1, 'promoRate': 4, 'rewardType': 'points',
            'rewardUnit': 'percent', 'rewardAmount': None, 'pointValueTwd': None,
            'capAmount': x['cap'], 'capPeriod': 'PER_TRANSACTION',
            'capScope': 'PROMO', 'roundingMode': 'ROUND_COMPONENT',
            'spendBasis': 'PER_TRANSACTION', 'minimumSpend': x['minimum'],
            'rewardCalculationMode': 'FLAT', 'rewardTiers': [], 'maxRateRequires': [],
            'needReg': False, 'registrationUrl': '', 'registrationMethods': [],
            'registrationStart': '', 'registrationEnd': '', 'regDeadline': '',
            'validFrom': '2026-01-01', 'validUntil': '2026-12-31',
            'sourceUrl': SOURCE,
            'eligibilityRequirements': [
                f'於{merchant}官方網站以LINE Pay單筆結帳滿NT${x["minimum"]:,}',
                '台灣LINE帳號已註冊LINE Pay並綁定中信LINE Pay信用卡或簽帳金融卡',
                '付款前已同意LINE Pay行銷資訊提供政策',
                '須確認活動點數池尚有餘額',
            ],
            'excludedKeywords': ['任何分期付款', 'LINE POINTS折抵金額',
                                 'LINE Pay優惠券折抵金額', '取消交易', '退款'],
            'quotaInfo': f'加碼4%單筆上限{x["cap"]}點；活動總量{x["pool"]:,}點，按合資格交易順序，額滿為止。',
            'benefitSummary': f'{merchant}官網LINE Pay單筆滿NT${x["minimum"]:,}享最高5% LINE POINTS（基本1%＋加碼4%）；加碼單筆上限{x["cap"]}點，總池額滿即止。',
            'quickSearchEligible': False,
            'validationIssues': ['LIVE_CAMPAIGN_POOL_UNVERIFIED',
                                 'PAYMENT_PERSONAL_STATUS_UNVERIFIED'],
            'sourceFacts': {'sourceUrl': SOURCE, 'checkedAt': CHECKED,
                            'locators': {'listing': x['listing'], 'detail': x['detail']}},
            'fetchedAt': CHECKED,
        })
        locators = {
            'title': '官方列表及詳情／' + x['listing'] + '、' + x['detail'],
            'cardEligibility': '信用卡及簽帳金融卡綁定 LINE Pay／' + x['qualification'],
            'reward': '基本1%與加碼4%／' + x['main'],
            'rewardType': 'LINE POINTS／' + x['main'],
            'validFrom': '官方列表日期／' + x['listing'],
            'validUntil': '官方列表日期／' + x['listing'],
            'cap': '加碼單筆及總池上限／' + x['main'],
            'minimumSpend': '單筆消費門檻／' + x['main'],
            'exclusions': '分期、折抵與取消交易／' + x['detail'],
            'rounding': '實付金額四捨五入／' + x['qualification'],
        }
        fields = {name: {'status': 'supported', 'sourceUrl': SOURCE, 'locator': locator}
                  for name, locator in locators.items()}
        fields['registration'] = {'status': 'not_applicable', 'sourceUrl': SOURCE,
            'locator': '完整活動注意事項／' + x['detail'],
            'reason': '沒有銀行活動登錄；LINE Pay註冊、綁卡與行銷同意另列資格'}
        r['termEvidence'] = {'sourceUrl': SOURCE, 'checkedAt': CHECKED,
                             'method': 'manual_official_terms_read', 'fields': fields}
    return len(ITEMS)


def main():
    path = ROOT / 'data.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    count = enrich(data)
    data['version'] = '2026.11.08-v355000-petthree'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'enriched {count} CTBC pet list candidates; live pools still blocked')


if __name__ == '__main__':
    main()
