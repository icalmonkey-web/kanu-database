"""Separate ShopBack cash and CTBC points for the Maohao listing offer."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_pet.html'
RULE_ID = 'pending_ctbc_linepay_pet_2026_maohao'
CHECKED = '2026-11-08T00:36:00+08:00'


def enrich(data):
    r = next(rule for rule in data['rules'] if rule['id'] == RULE_ID)
    r.update({
        'title': '毛好多 ShopBack 專區：商家4%與中信卡2%分別回饋',
        'sourceUrl': SOURCE, 'validFrom': '2026-07-01', 'validUntil': '2026-12-31',
        'cardId': 'card_中國信託_241',
        'eligibleCardIds': ['card_中國信託_241'],
        'eligibleCardScope': 'SELECTED_CARDS',
        'cardAssociationEvidence': {'sourceUrl': SOURCE,
            'locator': 'ShopBack活動辦法限LINE Pay Visa信用卡／L381-L383'},
        'offerDomain': 'PAYMENT', 'paymentProvider': 'ShopBack',
        'fundingMethods': ['中國信託LINE Pay Visa信用卡直接線上刷卡，不使用LINE Pay支付'],
        'activityType': 'REG_PROMOTION', 'scope': 'SPECIFIC',
        'matchedMerchants': ['毛好多'], 'searchKeywords': '毛好多,ShopBack',
        'rewardType': 'mixed_benefit', 'rewardUnit': 'mixed',
        'rewardAmount': None, 'baseRate': 0, 'promoRate': 0,
        'benefitComponents': [
            {'provider': 'ShopBack', 'type': 'merchant_cashback_percent', 'rate': 4,
             'locator': '毛好多表列商家回饋率／L400'},
            {'provider': '中國信託', 'type': 'line_points_percent', 'rate': 2,
             'locator': '毛好多表列卡產品回饋率／L400'},
        ],
        'capAmount': None, 'capScope': 'UNKNOWN', 'capPeriod': '',
        'minimumSpend': 0, 'spendBasis': 'PER_TRANSACTION',
        'roundingMode': 'ROUND_COMPONENT',
        'rewardCalculationMode': 'MAX_ONLY', 'rewardTiers': [],
        'needReg': True, 'registrationCycle': 'ONCE',
        'registrationStart': '', 'registrationEnd': '', 'regDeadline': '',
        'registrationUrl': '', 'registrationMethods': [],
        'eligibilityRequirements': [
            '先註冊或登入ShopBack會員，點官方活動的「立即登錄」完成一次持卡人登錄',
            '從本活動專區連至毛好多後使用中國信託LINE Pay Visa信用卡直接線上刷卡',
            '商家回饋須符合ShopBack毛好多商家頁審核條件',
        ],
        'excludedKeywords': ['LINE Pay付款', '其他第三方支付', '超商取貨付款',
                             '分期付款', '退換貨不符商家條款'],
        'quotaInfo': '商家回饋4%由ShopBack提供、卡產品點數2%由中信提供；商家回饋於請款後45天，卡點數與加碼另依官方時間。登錄開放窗口與商家細則待核。',
        'benefitSummary': '毛好多最高6%為ShopBack商家現金回饋4%＋中信卡LINE POINTS 2%，兩種回饋分開入帳；須先登錄並從ShopBack專區導購，LINE Pay付款不適用。',
        'quickSearchEligible': False,
        'validationIssues': ['REGISTRATION_WINDOW_UNVERIFIED',
                             'SHOPBACK_MERCHANT_TERMS_UNVERIFIED',
                             'MIXED_CASH_AND_POINTS_NOT_SINGLE_REWARD'],
        'sourceFacts': {'sourceUrl': SOURCE, 'checkedAt': CHECKED,
                        'locators': {'listing': 'L97-L102', 'conditions': 'L372-L390',
                                     'merchantRate': 'L400', 'period': 'L465'}},
        'fetchedAt': CHECKED,
    })
    locators = {
        'title': '毛好多列表與回饋表／L97-L102、L400',
        'cardEligibility': 'LINE Pay Visa信用卡限定／L381-L383',
        'reward': 'ShopBack商家4%＋中信卡點數2%／L400',
        'rewardType': '商家現金回饋與LINE POINTS分列／L384、L390、L400',
        'validFrom': '活動2026/7/1起／L381、L465',
        'validUntil': '活動2026/12/31止／L381、L465',
        'registration': '會員、一次登錄與專區導購／L373-L383',
        'rounding': '卡點數與商家現金回饋分別四捨五入／L389-L390',
    }
    r['termEvidence'] = {'sourceUrl': SOURCE, 'checkedAt': CHECKED,
        'method': 'manual_official_terms_read',
        'fields': {key: {'status': 'supported', 'sourceUrl': SOURCE, 'locator': locator}
                   for key, locator in locators.items()},
        'unresolved': ['cap', 'minimumSpend', 'exclusions']}
    return r


def main():
    path = ROOT / 'data.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    enrich(data)
    data['version'] = '2026.11.08-v360000-maohao'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Maohao composite reward and registration corrected; activation remains blocked')


if __name__ == '__main__':
    main()
