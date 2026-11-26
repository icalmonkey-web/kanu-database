"""Correct four CTBC fashion offers against the issuer's live detail page."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data.json"
SOURCE = "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_fashion.html"
OFFERS = {
    "rule_9b4fdf62817e99e7418a": (150, "L245-L250"),
    "rule_ea7cdd2e0b8e36a8b01a": (300, "L261-L267"),
    "rule_fe3b235a35f6c2330652": (200, "L273-L287"),
    "rule_8be1d7ac2cc79e568969": (1000, "L305-L315"),
}


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    seen = set()
    for rule in data["rules"]:
        if rule["id"] not in OFFERS:
            continue
        cap, locator = OFFERS[rule["id"]]
        assert rule["id"] not in seen
        assert rule["rewardType"] == "points" and rule["capAmount"] == cap
        seen.add(rule["id"])
        rule["rewardAmount"] = None
        rule["rewardUnit"] = "LINE POINTS"
        rule["quickSearchEligible"] = False
        issues = [issue for issue in rule.get("validationIssues") or []
                  if issue != "AMBIGUOUS_PERCENT_AND_FIXED_POINT_REWARD"]
        if rule["id"] == "rule_9b4fdf62817e99e7418a":
            rule["eligibleWeekdays"] = [0]
            rule["capPeriod"] = "UNKNOWN"
            issues.append("WATSONS_BONUS_CAP_PERIOD_UNVERIFIED")
        elif rule["id"] == "rule_ea7cdd2e0b8e36a8b01a":
            rule["fundingMethods"] = ["中國信託 LINE Pay 實體卡直接刷卡"]
            rule["paymentProvider"] = ""
            rule["benefitSummary"] = "指定線上商城單筆滿 2,200 元現折 100 元、滿 3,800 元現折 180 元，另享最高 6% LINE POINTS；限實體卡直接刷卡。"
            issues.append("DISCOUNT_TIERS_AND_EXCLUSIONS_NOT_MACHINE_CHECKED")
        elif rule["id"] == "rule_fe3b235a35f6c2330652":
            issues.append("LIVE_POINT_POOL_UNVERIFIED")
        else:
            issues.extend(["LIVE_POINT_POOL_UNVERIFIED", "OFFICIAL_MERCHANT_LINK_CONFLICT"])
        rule["validationIssues"] = list(dict.fromkeys(issues))
        rule["sourceFacts"] = {
            "checkedAt": "2026-11-07",
            "sourceUrl": SOURCE,
            "locators": {"officialDetail": locator,
                         "capNotFixedAward": locator + ": numeric value is a point cap"},
            "reviewScope": "Selected public terms only; store/payment exclusions, live quota or source-link conflict remain unresolved",
        }
    assert seen == set(OFFERS), f"missing fashion rules: {set(OFFERS) - seen}"
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"corrected {len(seen)} CTBC fashion records")


if __name__ == "__main__":
    main()
