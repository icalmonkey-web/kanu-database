"""Separate CTBC LINE Pay's mutually exclusive 2026 welcome gifts.

Official page read on 2026-11-08; this is a partial terms correction, not
independent approval for transaction recommendations.
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data.json"
SOURCE = "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/gifts.html"
OLD_ID = "rule_681876489680b798102e"
NEW_ID = "ctbc_linepay_first_card_gift_2026h2"


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    rules = data["rules"]
    old = next(r for r in rules if r["id"] == OLD_ID)
    common = {
        "sourceUrl": SOURCE,
        "validFrom": "2026-07-01",
        "validUntil": "2026-12-31",
        "spendBasis": "CUMULATIVE",
        "minimumSpend": 888,
        "rewardType": "points",
        "rewardUnit": "points",
        "baseRate": 0,
        "promoRate": 0,
        "rewardCalculationMode": "FLAT",
        "rewardTiers": [],
        "quickSearchEligible": False,
        "validationIssues": ["APPLICATION_APPROVAL_AND_PERSONAL_ELIGIBILITY_UNVERIFIED",
                             "REGISTRATION_REQUIREMENT_UNVERIFIED"],
        "excludedKeywords": ["預借現金", "基金申購", "退貨", "帳單分期", "學費", "繳稅",
                             "年費", "手續費", "利息", "違約金"],
        "sourceFacts": {"sourceUrl": SOURCE, "checkedAt": "2026-11-08",
                        "locator": "首刷禮活動注意事項第1至7點；頁面第134至143行"},
        "registrationUrl": "",
        "registrationMethods": [],
    }
    old.update(common)
    old.update({
        "title": "LINE Pay信用卡新戶禮：核卡30日內累積滿NT$888贈300點",
        "rewardAmount": 300,
        "eligibilityRequirements": [
            "2026/7/1至12/31申請書收件且2027/1/15前核卡",
            "核卡日起30日內以新卡累積消費滿NT$888；正附卡合併計算",
            "申辦前12個月未持有任何中國信託信用卡正卡",
            "消費前完成LINE Pay帳號綁定；新戶禮與新卡禮不得同領",
            "每戶正卡限領一次；非單筆消費回饋",
        ],
        "benefitSummary": "符合新戶、送件、核卡及核卡後30日累積消費條件，贈LINE POINTS 300點；不得與100點新卡禮同領。",
        "quotaInfo": "每戶正卡限領一次；於符合資格的次次月起回饋。",
    })
    new = next((r for r in rules if r["id"] == NEW_ID), None)
    if new is None:
        new = copy.deepcopy(old)
        new["id"] = NEW_ID
        rules.append(new)
    new.update(common)
    new.update({
        "title": "LINE Pay信用卡新卡禮：核卡30日內累積滿NT$888贈100點",
        "rewardAmount": 100,
        "eligibilityRequirements": [
            "2026/7/1至12/31申請書收件且2027/1/15前核卡",
            "核卡日起30日內以新卡累積消費滿NT$888；正附卡合併計算",
            "首次申辦中國信託LINE Pay信用卡正卡",
            "消費前完成LINE Pay帳號綁定；新卡禮與新戶禮不得同領",
            "每戶正卡限領一次；非單筆消費回饋",
        ],
        "benefitSummary": "符合首次申辦此卡、送件、核卡及核卡後30日累積消費條件，贈LINE POINTS 100點；不得與300點新戶禮同領。",
        "quotaInfo": "每戶正卡限領一次；於符合資格的次次月起回饋。",
    })
    data["version"] = "2026.11.08-v320000-welcomegifts"
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"corrected {OLD_ID}; added or updated {NEW_ID}")


if __name__ == "__main__":
    main()
