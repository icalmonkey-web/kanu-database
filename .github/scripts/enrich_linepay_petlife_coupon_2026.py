"""Correct the CTBC-listed pet coupon using the LINE Pay campaign page."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data.json'
RULE_ID = 'pending_ctbc_linepay_pet_2026_petlife'
LISTING = 'https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_pet.html'
DETAIL = 'https://web-tw-pay.line.me/cms/event/template1.3/fc046dcd-d679-4b2f-930c-0a8e227d8f20'
CHECKED = '2026-11-08T00:41:00+08:00'


def enrich(data):
    rule = next(r for r in data['rules'] if r['id'] == RULE_ID)
    rule.update({
        'bank': 'LINE Pay', 'cardId': '', 'eligibleCardIds': [],
        'eligibleCardScope': 'ALL_ISSUERS',
        'offerDomain': 'PAYMENT', 'paymentProvider': 'LINE Pay',
        'title': 'LINE Pay 好康地圖寵物生活每週 80 元優惠券',
        'activityType': 'DIRECT_PROMOTION', 'scope': 'SPECIFIC',
        'matchedMerchants': ['指定寵物生活店家'],
        'searchKeywords': '寵物生活,LINE Pay,好康地圖,80元優惠券',
        'rewardType': 'coupon', 'rewardUnit': 'TWD', 'rewardAmount': 80,
        'baseRate': 0, 'promoRate': 0,
        'capAmount': None, 'capScope': 'UNKNOWN', 'capPeriod': '',
        'minimumSpend': None, 'spendBasis': 'PER_TRANSACTION',
        'rewardCalculationMode': 'MAX_ONLY', 'rewardTiers': [],
        'needReg': False, 'registrationStart': '', 'registrationEnd': '',
        'registrationUrl': '', 'registrationMethods': [],
        'validFrom': '2026-10-01', 'validUntil': '2026-12-31',
        'sourceUrl': DETAIL, 'listingSourceUrl': LISTING,
        'fundingMethods': ['LINE Pay任一付款方法；雙方均開通時可使用LINE Pay Money餘額'],
        'eligibilityRequirements': [
            '已註冊LINE Pay且同意行銷資訊提供政策',
            '每週到LINE Pay好康地圖領取優惠券，先用先贏',
            '限付款當下活動頁列示的指定寵物生活店家及可折抵商品',
        ],
        'quotaInfo': '優惠券先用先贏；可用張數、折抵門檻與券有效期限以領取及付款當下LINE Pay顯示為準。',
        'benefitSummary': 'LINE Pay好康地圖每週可領寵物生活80元優惠券；此為LINE Pay活動，並非中信卡專屬80元回饋。須先領券，實際折抵資格以LINE Pay付款頁為準。',
        'quickSearchEligible': False,
        'validationIssues': ['COUPON_THRESHOLD_AND_EXPIRY_UNVERIFIED',
                             'ELIGIBLE_MERCHANTS_AND_STOCK_LIVE_UNVERIFIED'],
        'sourceFacts': {'sourceUrl': DETAIL, 'listingSourceUrl': LISTING,
                        'checkedAt': CHECKED,
                        'locators': {'listing': '中信脆萌寵頁/L104-L110',
                                     'payment': 'LINE Pay頁/L0-L6,L42-L44',
                                     'dates': 'LINE Pay頁/L12-L14',
                                     'merchant': 'LINE Pay頁/L16-L24,L38-L44',
                                     'claim': 'LINE Pay頁/L27-L44'}},
        'termEvidence': {'sourceUrl': DETAIL, 'checkedAt': CHECKED,
                         'method': 'manual_official_terms_read',
                         'fields': {
                             key: {'status': 'supported', 'sourceUrl': DETAIL,
                                   'locator': locator}
                             for key, locator in {
                                 'title': 'L6,L31-L34',
                                 'cardEligibility': 'L0-L6,L42-L44；任一付款方法',
                                 'reward': 'L31-L34；80元優惠券',
                                 'rewardType': 'L2,L31-L37；優惠券',
                                 'validFrom': 'L12-L14；GMT+8為2026/10/1',
                                 'validUntil': 'L12-L14；GMT+8為2026/12/31',
                                 'registration': 'L28,L31-L34；LINE Pay會員與領券，非銀行活動登錄',
                             }.items()},
                         'unresolved': ['cap', 'minimumSpend', 'exclusions',
                                        'couponExpiry', 'liveStock']},
        'fetchedAt': CHECKED,
    })
    return rule


def main():
    data = json.loads(DATA.read_text(encoding='utf-8'))
    enrich(data)
    data['version'] = '2026.11.08-v365000-petlife'
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Petlife coupon corrected from LINE Pay official page; live coupon details remain blocked')


if __name__ == '__main__':
    main()
