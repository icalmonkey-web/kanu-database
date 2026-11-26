"""Idempotently add the remaining 2026 CTBC shopping-page entrances as cautious references."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data.json'
CATALOG = ROOT / 'official_catalogs/ctbc_linepay_shopping_2026h2.json'
MAPPING = ROOT / 'official_catalogs/ctbc_linepay_shopping_2026h2_mapping.json'
SOURCE = 'https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_shopping.html'
STYLE = 'https://web-tw-pay.line.me/cms/event/template1.3/6a7b8614-65f9-4eb5-b2b7-fbd316095a4d'
COUPON = 'https://web-tw-pay.line.me/cms/event/template1.3/6a266356-4082-41d7-9112-429e08150c86'
STAMP = '2026-11-03T13:10:00Z'


def record(key, title, merchant, start, source=SOURCE, **fields):
    row = dict(id=f'review_ctbc_shopping_{key}_2026h2', title=title,
               bank='中國信託' if source == SOURCE else 'LINE Pay',
               cardId='card_中國信託_51' if source == SOURCE else '',
               offerDomain='CARD' if source == SOURCE else 'PAYMENT',
               paymentProvider='', activityType='DIRECT_PROMOTION', scope='SPECIFIC',
               matchedMerchants=[merchant], searchKeywords=merchant,
               rewardType='points', rewardUnit='percent', rewardAmount=None,
               baseRate=0, promoRate=0, capAmount=None, capScope='PROMO',
               capPeriod='CAMPAIGN', registrationCycle='',
               roundingMode='ROUND', spendBasis='PER_TRANSACTION',
               minimumSpend=0, rewardCalculationMode='FLAT', rewardTiers=[],
               needReg=False, registrationStart='', registrationEnd='',
               registrationMethods=[], validFrom=start, validUntil='2026-12-31',
               sourceUrl=source, quickSearchEligible=False, validationIssues=[],
               fetchedAt=STAMP, sourceFacts={'checkedAt': STAMP, 'sourceUrl': source})
    row.update(fields)
    return row


rows = [
    record('coupang_discount', 'Coupang 酷澎活動①：滿額結帳現折', 'Coupang', '2026-09-16',
           rewardType='discount', rewardUnit='twd', minimumSpend=5000,
           capAmount=300, capPeriod='MONTHLY',
           validationIssues=['OFFICIAL_LISTING_DETAIL_RATE_CONFLICT'],
           fundingMethods=['中國信託LINE Pay Visa信用卡（不含簽帳金融卡）'],
           eligibilityRequirements=['酷澎會員於台灣酷澎火箭速配指定商品消費',
                                    '單筆滿 NT$5,000，直接以指定信用卡付款；不得使用 LINE Pay 等第三方支付',
                                    '每月限量，須以結帳頁實際現折為準'],
           excludedKeywords=['火箭跨境', '酷澎商城', 'LINE Pay付款', 'Visa簽帳金融卡'],
           benefitSummary='酷澎指定火箭速配商品單筆滿 NT$5,000，結帳頁最高現折 NT$300；每月限量，實際折扣以結帳顯示為準',
           sourceFacts={'checkedAt': STAMP, 'sourceUrl': SOURCE,
                        'locators': {'eligibility': 'L318-L319', 'thresholdAndDiscount': 'L320',
                                     'exclusions': 'L321-L327'}}),
    record('coupang_points', 'Coupang 酷澎活動②：LINE POINTS 5%', 'Coupang', '2026-09-16',
           baseRate=1, promoRate=4, capAmount=100, capPeriod='QUARTERLY',
           registrationCycle='QUARTERLY', needReg=True,
           fundingMethods=['中國信託LINE Pay Visa卡（含簽帳金融卡）'],
           quotaInfo='每月 6 日 10:00 開放限量登錄 8,000 名；每季每戶加碼上限 100 點，當季是否仍有名額須至官方確認',
           eligibilityRequirements=['火箭速配與火箭跨境交易可參加', '每季重新登錄',
                                    '帳單明細須能辨識指定商家'],
           benefitSummary='酷澎活動②最高 LINE POINTS 5%（一般 1%＋加碼 4%）；加碼每季每戶上限 100 點，須完成當季限量登錄',
           sourceFacts={'checkedAt': STAMP, 'sourceUrl': SOURCE,
                        'locators': {'eligibility': 'L331-L332', 'rate': 'L333',
                                     'capAndRegistration': 'L334'}}),
    record('dietician', '營養師輕食 LINE POINTS 5%', '營養師輕食', '2026-07-13',
           paymentProvider='LINE Pay', baseRate=1, promoRate=4,
           minimumSpend=5000, capAmount=200, capScope='LINE_PAY_ACCOUNT',
           validationIssues=['SCHEDULE_NOT_MACHINE_CHECKED'],
           fundingMethods=['LINE Pay 綁定中國信託LINE Pay信用卡或簽帳金融卡'],
           eligibilityRequirements=['銀行活動列表限定每週六、週日；內文未再次列出週末限制',
                                    '營養師輕食官網單筆實付滿 NT$5,000',
                                    '台灣 LINE 帳號已註冊 LINE Pay，付款前同意行銷資訊提供政策',
                                    '透過 LINE Pay 使用指定卡付款，不適用分期'],
           quotaInfo='加碼點數全活動限量 400,000 點；是否尚有額度須至官方確認',
           benefitSummary='銀行列表列每週六、週日；營養師輕食官網 LINE Pay 綁指定卡單筆滿 NT$5,000，LINE POINTS 5%（一般 1%＋加碼 4%）；加碼每帳號全期上限 200 點且有總量限制',
           sourceFacts={'checkedAt': STAMP, 'sourceUrl': SOURCE,
                        'locators': {'schedule': 'L116', 'thresholdAndRate': 'L389-L390', 'capAndQuota': 'L391',
                                     'eligibility': 'L393-L398', 'calculation': 'L401-L402'}}),
    record('pinkoi', 'Pinkoi 週二／每月 20 日 LINE POINTS 5%', 'Pinkoi', '2026-07-01',
           baseRate=1, promoRate=4, minimumSpend=2000, capAmount=150,
           capPeriod='MONTHLY',
           validationIssues=['SCHEDULE_NOT_MACHINE_CHECKED'],
           fundingMethods=['中國信託LINE Pay卡'],
           eligibilityRequirements=['Pinkoi 官網或 App 於週二或每月 20 日刷指定卡',
                                    '單筆商品及運費合計滿 NT$2,000；門檻不含折扣、P Coins、手續費及禮物卡'],
           benefitSummary='Pinkoi 官網／App 週二與每月 20 日單筆商品及運費滿 NT$2,000，最高 LINE POINTS 5%（一般 1%＋加碼 4%）；加碼每人每月上限 150 點',
           sourceFacts={'checkedAt': STAMP, 'sourceUrl': SOURCE,
                        'locators': {'scheduleAndThreshold': 'L345-L346', 'rateAndCap': 'L347-L348',
                                     'exclusions': 'L346-L350'}}),
    record('style_coupon', '風格選品每週領 80 元 LINE Pay 優惠券', '風格選品', '2026-10-01', STYLE,
           paymentProvider='LINE Pay', rewardType='coupon', rewardUnit='twd',
           rewardAmount=80, benefitSummary='LINE Pay 已註冊用戶可每週領取指定風格選品 80 元優惠券；先領先贏，適用店家及使用門檻以當下官方券面為準',
           eligibilityRequirements=['須於 LINE Pay 領券並符合券面條件', '付款前同意行銷資訊提供政策'],
           sourceFacts={'checkedAt': STAMP, 'sourceUrl': STYLE,
                        'locators': {'period': 'L12-L14', 'mechanism': 'L31-L44'}}),
    record('good_coupon', '購好券精選商店：滿百贈星巴克 50 元券', '購好券', '2026-10-01', COUPON,
           paymentProvider='LINE Pay', rewardType='coupon', rewardUnit='twd',
           rewardAmount=50, minimumSpend=100,
           benefitSummary='LINE Pay App 購好券精選商店單筆實付滿 NT$100，贈星巴克星意禮線上 50 元優惠券；另有三筆各滿 NT$35 的抽獎任務，不能當作保證回饋',
           eligibilityRequirements=['須從 LINE Pay App 購好券精選商店購買，星巴克星意禮不列入精選商店',
                                    '使用 LINE Pay 已綁卡或 LINE Pay Money 付款',
                                    '付款前同意行銷資訊提供政策'],
           sourceFacts={'checkedAt': STAMP, 'sourceUrl': COUPON,
                        'locators': {'period': 'L14-L16', 'merchant': 'L18-L22',
                                     'thresholdAndBenefit': 'L33-L38'}}),
]

data = json.loads(DATA.read_text(encoding='utf-8'))
replacement = {row['id']: row for row in rows}
data['rules'] = [replacement.pop(row['id'], row) for row in data['rules']]
data['rules'].extend(replacement.values())
data['version'] = '2026.11.03-v213000-shopping-complete'
DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
for offer in catalog['offers']:
    if offer['id'] == 'style_shopping':
        offer['detailUrl'] = STYLE
    elif offer['id'] == 'good_coupon':
        offer['detailUrl'] = COUPON
CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

mapping = json.loads(MAPPING.read_text(encoding='utf-8'))
present = {row['offerId'] for row in mapping['mappings']}
add = {
    'coupang': [rows[0]['id'], rows[1]['id']],
    'dietician': [rows[2]['id']], 'pinkoi': [rows[3]['id']],
    'style_shopping': [rows[4]['id']], 'good_coupon': [rows[5]['id']],
}
mapping['mappings'].extend({'offerId': key, 'ruleIds': ids, 'status': 'matched'}
                           for key, ids in add.items() if key not in present)
MAPPING.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f"rules={len(data['rules'])}; shopping mappings={len(mapping['mappings'])}")
