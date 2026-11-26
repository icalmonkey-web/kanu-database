"""Separate verified CTBC point caps from Samsung's genuine fixed award."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data.json"
LIFE = "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_life.html"
SHOP = "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_shopping.html"
REGISTER = "https://www.ctbcbank.com/twrbo/zh_tw/onlinecounter_index/cc_service/cc_service_register.html"
IDS = {
    "rule_d06f4a5bdc36a2ea8e23": (LIFE, 100, "QUARTERLY", "L376-L378"),
    "rule_c442e0aac014708858e2": (LIFE, 1000, "MONTHLY", "L420-L423"),
    "rule_7d6f97e638c3e5042864": (LIFE, 700, "MONTHLY", "L430-L434"),
    "rule_59a9da0c6ecc1c0d909f": (SHOP, 1000, "CAMPAIGN", "L242-L255"),
}


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    seen = set()
    for rule in data["rules"]:
        if rule["id"] not in IDS:
            continue
        source, cap, period, locator = IDS[rule["id"]]
        assert rule["id"] not in seen
        assert rule["rewardType"] == "points" and rule["capAmount"] == cap
        seen.add(rule["id"])
        rule["rewardUnit"] = "LINE POINTS"
        rule["capPeriod"] = period
        rule["quickSearchEligible"] = False
        issues = rule.setdefault("validationIssues", [])
        issue = "REGISTRATION_CAPACITY_UNVERIFIED" if rule["needReg"] else "LIVE_POINT_POOL_OR_ELIGIBILITY_UNVERIFIED"
        if issue not in issues:
            issues.append(issue)
        if rule["id"] == "rule_59a9da0c6ecc1c0d909f":
            assert rule["rewardAmount"] == 1000
            rule["eligibleWeekdays"] = [4, 5]
            rule["fixedAwardEvidence"] = {
                "sourceUrl": SHOP,
                "locator": "Samsung activity terms L243-L244: spend 50,000 on Thursday/Friday to earn fixed 1,000 points; one award per account",
                "checkedAt": "2026-11-07",
            }
        else:
            rule["rewardAmount"] = None
        if rule["id"] == "rule_d06f4a5bdc36a2ea8e23":
            rule["registrationCycle"] = "QUARTERLY"
            rule["registrationUrl"] = REGISTER
            rule["registrationMethods"] = [{
                "type": "WEB", "label": "中國信託活動登錄", "url": REGISTER,
                "activityName": rule["title"],
            }]
            rule["registrationLinkEvidence"] = {
                "sourceUrl": LIFE, "method": "OFFICIAL_PAGE_LINK", "urls": [REGISTER],
            }
        rule["sourceFacts"] = {
            "checkedAt": "2026-11-07",
            "sourceUrl": source,
            "locators": {
                "officialTerms": locator,
                "rewardClassification": (
                    "L243-L244: fixed 1,000 points on Thursday/Friday; one award per account"
                    if rule["id"] == "rule_59a9da0c6ecc1c0d909f"
                    else locator + ": point cap is not a fixed point award"
                ),
            },
            "reviewScope": "Selected public terms only; individual eligibility, point-pool or registration capacity is unverified",
        }
    assert seen == set(IDS), f"missing rules: {set(IDS) - seen}"
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"corrected {len(seen)} CTBC life and shopping rules")


if __name__ == "__main__":
    main()
