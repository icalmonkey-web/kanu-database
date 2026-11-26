"""Reconcile CTBC LINE Pay general 1% and credit-only overseas 2.8%."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/notice.html'
GENERAL = 'rule_0f8c8cd7c63feebcc3e1'
OVERSEAS = 'rule_02d342bf71118f6a54cd'
COPIES = {'ctbc_lp_general': GENERAL,
          'rule_repaired_f66c0b62fda271b17663': OVERSEAS}


def correct(data):
    rules = {rule['id']: rule for rule in data['rules']}
    common = {'sourceUrl': SOURCE, 'validUntil': '2026-12-31',
              'rewardType': 'points', 'rewardUnit': 'percent',
              'rewardAmount': None, 'roundingMode': 'ROUND',
              'spendBasis': 'PER_TRANSACTION', 'minimumSpend': 0,
              'capAmount': None, 'capScope': 'NONE', 'needReg': False,
              'registrationUrl': '', 'registrationMethods': [],
              'quickSearchEligible': False, 'rewardCalculationMode': 'FLAT',
              'rewardTiers': [], 'maxRateRequires': [],
              'sourceFacts': {'sourceUrl': SOURCE, 'checkedAt': '2026-11-08',
                              'locator': '回饋計劃第1至6、13至14點；頁面第21至48行'}}
    general = rules[GENERAL]
    general.update(common)
    general.update({
        'title': 'LINE Pay卡國內外一般消費1% LINE POINTS',
        'cardId': 'card_中國信託_51',
        'eligibleCardIds': ['card_中國信託_51', 'card_中國信託_241',
                            'card_中國信託_242', 'card_中國信託_324',
                            'card_中國信託_327', 'card_中國信託_328'],
        'eligibleCardScope': 'SELECTED_CARDS',
        'cardAssociationEvidence': {'sourceUrl': SOURCE,
            'locator': '115年LINE Pay聯名卡回饋計劃第1點、表格；頁面第42至52行'},
        'baseRate': 1, 'promoRate': 0, 'validFrom': '2026-01-01',
        'eligibilityRequirements': ['適用LINE Pay信用卡、鼎極卡及簽帳金融卡',
                                    '消費及回饋時維持綁定臺灣LINE Pay帳號'],
        'excludedKeywords': ['官方不回饋交易項目', '分期付款交易'],
        'benefitSummary': '國內外一般消費每筆1% LINE POINTS，按元計算後四捨五入；不回饋交易項目依中信官網。',
        'validationIssues': ['OFFICIAL_EXCLUSION_LIST_NOT_MACHINE_VERIFIED',
                             'CARD_BINDING_STATUS_NOT_MACHINE_VERIFIED'],
    })
    overseas = rules[OVERSEAS]
    overseas.update(common)
    overseas.update({
        'title': 'LINE Pay信用卡國外實體商店2.8% LINE POINTS',
        'cardId': 'card_中國信託_241',
        'eligibleCardIds': ['card_中國信託_241', 'card_中國信託_242',
                            'card_中國信託_324', 'card_中國信託_327'],
        'eligibleCardScope': 'SELECTED_CARDS',
        'cardAssociationEvidence': {'sourceUrl': SOURCE,
            'locator': '國外實體店加碼限信用卡與表格；頁面第24、42至48行'},
        'baseRate': 1, 'promoRate': 1.8, 'validFrom': '2026-07-01',
        'eligibilityRequirements': [
            '僅限LINE Pay信用卡，不含簽帳金融卡',
            '請款時消費地或商店國別碼須為國外且為面對面交易',
            '實體卡、Apple Pay、Google Pay、Samsung Pay在實體商店支付可適用',
            '消費及回饋時維持綁定臺灣LINE Pay帳號',
        ],
        'excludedKeywords': ['網路交易', '條碼支付', '第三方支付',
                             '官方不回饋交易項目', '分期付款交易'],
        'benefitSummary': '國外面對面實體商店信用卡消費合計2.8% LINE POINTS（一般1%＋加碼1.8%）；簽帳金融卡僅一般1%。',
        'validationIssues': ['OFFICIAL_EXCLUSION_LIST_NOT_MACHINE_VERIFIED',
                             'FOREIGN_MERCHANT_CODE_NOT_MACHINE_VERIFIED',
                             'CARD_BINDING_STATUS_NOT_MACHINE_VERIFIED'],
    })
    checked_at = '2026-11-08T00:15:00+08:00'
    evidence_locators = {
        GENERAL: {
            'title': '回饋計劃標題與消費類別表；L17、L39-L45',
            'cardEligibility': 'LINE Pay 信用卡、鼎極卡及簽帳金融卡；L49-L52',
            'reward': '國內外一般消費1%；L39-L45',
            'rewardType': 'LINE POINTS；L49-L57',
            'validFrom': '115年回饋計劃自2026/1/1起；L63',
            'validUntil': '115年回饋計劃至2026/12/31止；L63',
            'rounding': '每筆不足1點四捨五入；L26、L53',
        },
        OVERSEAS: {
            'title': '國外實體商店消費表；L39-L48',
            'cardEligibility': '國外實體店2.8%限信用卡，簽帳金融卡1%；L24、L42-L48',
            'reward': '一般1%加海外實體1.8%，合計2.8%；L24、L46-L48',
            'rewardType': 'LINE POINTS；L24-L26',
            'validFrom': '加碼期間2026/7/1起；L38-L44',
            'validUntil': '加碼期間2026/12/31止；L38-L44',
            'rounding': '刷卡金額乘回饋率後四捨五入；L26-L28',
        },
    }
    for rule in (general, overseas):
        rule['termEvidence'] = {
            'sourceUrl': SOURCE, 'checkedAt': checked_at,
            'method': 'manual_official_terms_read',
            'fields': {field: {'status': 'supported', 'sourceUrl': SOURCE, 'locator': locator}
                       for field, locator in evidence_locators[rule['id']].items()},
            'unresolved': ['cap', 'minimumSpend', 'registration', 'exclusions'],
        }
    for old_id, primary_id in COPIES.items():
        old = rules[old_id]
        old['duplicateOf'] = primary_id
        old['quickSearchEligible'] = False
        issues = old.setdefault('validationIssues', [])
        if 'LEGACY_BASE_REWARD_DUPLICATE' not in issues:
            issues.append('LEGACY_BASE_REWARD_DUPLICATE')
    return general, overseas


def main():
    path = ROOT / 'data.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    correct(data)
    data['version'] = '2026.11.08-v330000-linepaybase'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('corrected general 1% and overseas credit-only 2.8%; linked 2 legacy copies')


if __name__ == '__main__':
    main()
