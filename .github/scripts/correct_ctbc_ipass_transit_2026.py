"""Reconcile four legacy copies of the CTBC LINE Pay iPASS transit offer."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/index.html'
PRIMARY = 'rule_b252bd65776f66527221'
LEGACY = ('rule_icash_transit', 'rule_ipass_transit', 'lp-ipass-transport')


def correct(data):
    by_id = {r['id']: r for r in data['rules']}
    main = by_id[PRIMARY]
    main.update({
        'title': 'LINE Pay卡一卡通大眾交通：每月累積滿NT$100得1點',
        'sourceUrl': SOURCE, 'validFrom': '2026-01-01', 'validUntil': '2026-12-31',
        'cardId': 'card_中國信託_241',
        'eligibleCardIds': ['card_中國信託_241', 'card_中國信託_328'],
        'eligibleCardScope': 'SELECTED_CARDS',
        'cardAssociationEvidence': {'sourceUrl': SOURCE,
            'locator': '一卡通1%回饋注意事項第2、3點；頁面第163至165行'},
        'rewardType': 'points', 'rewardUnit': 'percent', 'rewardAmount': None,
        'baseRate': 0, 'promoRate': 1, 'capAmount': None, 'capScope': 'NONE',
        'spendBasis': 'CUMULATIVE', 'minimumSpend': 100,
        'roundingMode': 'FLOOR', 'rewardCalculationMode': 'FLAT',
        'rewardTiers': [], 'maxRateRequires': [], 'needReg': False,
        'registrationUrl': '', 'registrationMethods': [],
        'eligibilityRequirements': [
            '以已綁定LINE Pay卡之一卡通功能支付大眾交通工具',
            '信用卡及簽帳金融卡均適用；正附卡及信用卡／簽帳金融卡分開計算',
            '當月份累積消費每滿NT$100得LINE POINTS 1點',
            '回饋時須為有效卡且簽帳金融卡指定付款帳戶可正常交易',
        ],
        'excludedKeywords': ['高鐵', '計程車', 'Hami Pay', 'Fitbit Pay', '其他行動支付之一卡通交易'],
        'quotaInfo': '每月累積滿NT$100得1點，無上限；依通路回傳時間認列。',
        'benefitSummary': 'LINE Pay卡一卡通搭乘指定大眾交通，每月累積每滿NT$100得1點；非每筆固定贈點。',
        'sourceFacts': {'sourceUrl': SOURCE, 'checkedAt': '2026-11-08',
            'locator': '一卡通1%回饋注意事項第1至5點；頁面第161至167行'},
        'quickSearchEligible': False,
        'validationIssues': ['TRANSIT_CARD_AND_PAYMENT_ELIGIBILITY_NOT_MACHINE_CHECKED'],
    })
    for legacy_id in LEGACY:
        rule = by_id[legacy_id]
        rule['duplicateOf'] = PRIMARY
        rule['quickSearchEligible'] = False
        issues = rule.setdefault('validationIssues', [])
        if 'LEGACY_TRANSIT_DUPLICATE' not in issues:
            issues.append('LEGACY_TRANSIT_DUPLICATE')
    return main


def main():
    path = ROOT / 'data.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    correct(data)
    data['version'] = '2026.11.08-v325000-ipasstransit'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'corrected {PRIMARY}; linked {len(LEGACY)} legacy copies')


if __name__ == '__main__':
    main()
