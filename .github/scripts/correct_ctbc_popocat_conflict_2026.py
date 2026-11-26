"""Keep CTBC Popocat's official list/detail contradictions visible and blocked."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DETAIL = 'https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_pet.html'
HOME = 'https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/index.html'
PRIMARY = 'rule_d4ed298d1db9c2c09f54'
OLD = ('rule_7bb19aad5016a4e4ba4c', 'rule_repaired_3485d52d661a15b0cada')


def correct(data):
    by_id = {rule['id']: rule for rule in data['rules']}
    rule = by_id[PRIMARY]
    rule.update({
        'title': '撥撥貓砂官網最高10% LINE POINTS（官方日期與上限待釐清）',
        'sourceUrl': DETAIL, 'validFrom': '2026-04-01', 'validUntil': '2026-12-31',
        'baseRate': 1, 'promoRate': 9, 'rewardType': 'points',
        'rewardUnit': 'percent', 'rewardAmount': None, 'pointValueTwd': None,
        'capAmount': None, 'capPeriod': '', 'capScope': 'UNKNOWN',
        'minimumSpend': 0, 'spendBasis': 'PER_TRANSACTION',
        'roundingMode': 'ROUND_COMPONENT', 'rewardCalculationMode': 'FLAT',
        'rewardTiers': [], 'maxRateRequires': [],
        'paymentProvider': '',
        'fundingMethods': ['中國信託LINE Pay卡於撥撥貓砂官網刷卡'],
        'eligibilityRequirements': [
            '僅撥撥貓砂官方網站網路消費，非實體門市或第三方平台',
            '須成功刷指定信用卡付款；詳情與首頁卡別用語仍待釐清',
            '無最低消費金額門檻',
        ],
        'excludedKeywords': ['實體門市', '其他第三方平台', '付款失敗', '訂單取消', '退貨'],
        'quotaInfo': '詳情頁未列每月上限；首頁稱加碼9%每人每月上限300點。上限與期間衝突待中信確認。',
        'benefitSummary': '官網消費最高10% LINE POINTS（基本1%＋加碼9%）；首頁與詳情的起日及上限不一致，卡別資格亦待核。',
        'sourceFacts': {
            'checkedAt': '2026-11-08T00:25:00+08:00',
            'sourceUrl': DETAIL,
            'locators': {'detail': 'L155-L167', 'home': '首頁L86-L96'},
            'conflictingSourceUrl': HOME,
        },
        'quickSearchEligible': False,
        'validationIssues': [
            'OFFICIAL_HOME_DETAIL_START_DATE_CONFLICT',
            'OFFICIAL_HOME_DETAIL_CAP_CONFLICT',
            'CARD_ELIGIBILITY_LIST_DETAIL_CONFLICT',
        ],
    })
    for old_id in OLD:
        old = by_id[old_id]
        old['duplicateOf'] = PRIMARY
        old['quickSearchEligible'] = False
        issues = old.setdefault('validationIssues', [])
        if 'LEGACY_POPOCAT_OFFICIAL_CONFLICT' not in issues:
            issues.append('LEGACY_POPOCAT_OFFICIAL_CONFLICT')
    return rule


def main():
    path = ROOT / 'data.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    correct(data)
    data['version'] = '2026.11.08-v345000-popocatconflict'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Popocat detail fields corrected; three official contradictions retained; two legacy copies linked')


if __name__ == '__main__':
    main()
