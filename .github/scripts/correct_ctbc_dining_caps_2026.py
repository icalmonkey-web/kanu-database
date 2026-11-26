"""Keep the six sourced CTBC dining caps distinct from fixed point awards."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data.json"
SOURCE = "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/page_food.html"
REGISTER = "https://www.ctbcbank.com/twrbo/zh_tw/onlinecounter_index/cc_service/cc_service_register.html"
LINES = {
    "rule_141a6550938b29d8ba13": (183, 185, 100),
    "rule_77b16b4262cd2c2704ad": (197, 199, 100),
    "rule_26ab533bf77c05b5133c": (211, 213, 200),
    "rule_1e1328f849591e9e8f10": (225, 227, 200),
    "rule_e74497743e60187f7f2a": (239, 241, 200),
    "rule_a7fcac04b54ea87a2f43": (253, 255, 200),
}


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    seen = set()
    for rule in data["rules"]:
        if rule["id"] not in LINES:
            continue
        first, cap_line, cap = LINES[rule["id"]]
        assert rule["id"] not in seen
        assert rule["capAmount"] == cap and rule["rewardType"] == "points"
        seen.add(rule["id"])
        rule["rewardAmount"] = None
        rule["rewardUnit"] = "LINE POINTS"
        rule["quickSearchEligible"] = False
        issues = rule.setdefault("validationIssues", [])
        if "REGISTRATION_CAPACITY_UNVERIFIED" not in issues:
            issues.append("REGISTRATION_CAPACITY_UNVERIFIED")
        rule["registrationUrl"] = REGISTER
        rule["registrationMethods"] = [{
            "type": "WEB", "label": "中國信託活動登錄", "url": REGISTER,
            "activityName": rule["title"],
        }]
        rule["registrationLinkEvidence"] = {
            "sourceUrl": SOURCE,
            "method": "OFFICIAL_PAGE_LINK",
            "urls": [REGISTER],
        }
        rule["sourceFacts"] = {
            "checkedAt": "2026-11-05",
            "sourceUrl": SOURCE,
            "locators": {
                "eligibility": f"L{first}: eligible card and merchant scope",
                "reward": f"L{first+1}: total LINE POINTS rate includes 1% base",
                "capAndRegistration": f"L{cap_line}: quarterly household point cap and quarterly registration; monthly capacity",
                "registrationLink": "official page's immediately-register link targets cc_service_register.html",
            },
            "reviewScope": "Selected public terms only; real-time registration capacity and individual eligibility remain unverified",
        }
    assert seen == set(LINES), f"missing dining rules: {set(LINES) - seen}"
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"corrected {len(seen)} CTBC dining cap records")


if __name__ == "__main__":
    main()
