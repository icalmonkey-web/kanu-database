"""Correct official CTBC pet offer caps mistaken for fixed LINE POINTS."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data.json"
SOURCE = "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_pet.html"
OFFERS = {
    "rule_959a861cabb8b515f17f": (150, 1500, "MONTHLY", 128, 30),
    "rule_b0e3b7c1e8eb9111f052": (180, 1800, "MONTHLY", 138, 36),
    "rule_5597df0306591339c831": (140, 2000, "CAMPAIGN", 171, 54),
    "rule_135b9e6c4621fc0c2dc8": (360, 2700, "PER_TRANSACTION", 203, 62),
    "rule_80b907fa6a35daa916fd": (30, 300, "PER_TRANSACTION", 235, 70),
}


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    seen = set()
    for rule in data["rules"]:
        if rule["id"] not in OFFERS:
            continue
        cap, threshold, period, detail_line, listing_line = OFFERS[rule["id"]]
        assert rule["id"] not in seen
        assert rule["rewardType"] == "points"
        assert rule["capAmount"] == cap and rule["minimumSpend"] == threshold
        seen.add(rule["id"])
        rule["rewardAmount"] = None
        rule["rewardUnit"] = "LINE POINTS"
        rule["capPeriod"] = period
        rule["quickSearchEligible"] = False
        issues = rule.setdefault("validationIssues", [])
        issue = "LIVE_POINT_POOL_UNVERIFIED" if period != "MONTHLY" else "MERCHANT_ELIGIBILITY_UNVERIFIED"
        if issue not in issues:
            issues.append(issue)
        rule["sourceFacts"] = {
            "checkedAt": "2026-11-07",
            "sourceUrl": SOURCE,
            "locators": {
                "listing": f"L{listing_line}: campaign dates and headline rate",
                "conditions": f"L{detail_line}: card/payment, minimum purchase and percentage",
                "cap": f"L{detail_line if period == 'MONTHLY' else detail_line + 2}: point cap is not a fixed award",
            },
            "reviewScope": "Selected public terms; personal eligibility and live merchant or point-pool availability remain unverified",
        }
    assert seen == set(OFFERS), f"missing pet rules: {set(OFFERS) - seen}"
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"corrected {len(seen)} CTBC pet cap records")


if __name__ == "__main__":
    main()
