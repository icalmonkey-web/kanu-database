"""Map an independently read CTBC fashion listing without inventing offer terms."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "official_catalogs" / "ctbc_linepay_fashion_2026.json"
MAPPING = CATALOG.with_name("ctbc_linepay_fashion_2026_mapping.json")
DATA = ROOT / "data.json"
KNOWN = {
    "watsons": "rule_9b4fdf62817e99e7418a",
    "vacanza": "rule_ea7cdd2e0b8e36a8b01a",
    "sisley": "rule_8be1d7ac2cc79e568969",
    "kafen": "rule_fe3b235a35f6c2330652",
}


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    data = json.loads(DATA.read_text(encoding="utf-8"))
    assert len(catalog["offers"]) == 25
    ids = {rule["id"] for rule in data["rules"]}
    assert set(KNOWN.values()) <= ids
    mappings = []
    added = 0
    for offer in catalog["offers"]:
        if offer["id"] in KNOWN:
            mappings.append({"offerId": offer["id"], "ruleId": KNOWN[offer["id"]],
                             "status": "matched"})
            continue
        rule_id = "pending_ctbc_linepay_fashion_2026_" + offer["id"]
        mappings.append({
            "offerId": offer["id"], "ruleId": rule_id, "status": "candidate",
            "reason": "僅官方列表入口與日期已記錄；卡別、付款、回饋上限、名額及登錄條款待逐欄核對，暫停推薦",
        })
        if rule_id in ids:
            continue
        provider = {"LINE_PAY": "LINE Pay", "SHOPBACK": "ShopBack"}.get(offer["channel"], "")
        data["rules"].append({
            "id": rule_id, "bank": "中國信託", "cardId": "",
            "offerDomain": "CARD" if offer["channel"] == "CARD" else "PAYMENT",
            "paymentProvider": provider,
            "title": offer["name"] + "（官方列表；條款待核）",
            "activityType": "UNKNOWN", "scope": "SPECIFIC",
            "eligibleCardScope": "UNKNOWN",
            "matchedMerchants": [offer["matchToken"]],
            "searchKeywords": offer["matchToken"],
            "benefitSummary": "官方列表入口：" + offer["name"] + "。完整資格、回饋、排除與登錄條款待逐項核對。",
            "rewardType": "unknown", "rewardUnit": "unknown",
            "rewardAmount": None, "baseRate": 0, "promoRate": 0,
            "capAmount": None, "minimumSpend": 0, "needReg": False,
            "validFrom": offer["validFrom"], "validUntil": offer["validUntil"],
            "sourceUrl": catalog["sourceUrl"], "registrationUrl": "",
            "registrationMethods": [], "quickSearchEligible": False,
            "validationIssues": ["LISTING_ONLY_TERMS_UNVERIFIED",
                                 "CARD_ELIGIBILITY_UNVERIFIED",
                                 "REGISTRATION_REQUIREMENT_UNVERIFIED"],
            "sourceFacts": {
                "checkedAt": catalog["observedAt"] + "T00:00:00+08:00",
                "sourceUrl": catalog["sourceUrl"],
                "locators": {"listing": "L" + str(offer["sourceLineHint"])},
            },
            "fetchedAt": catalog["observedAt"] + "T00:00:00+08:00",
        })
        ids.add(rule_id)
        added += 1
    MAPPING.write_text(json.dumps({"catalogId": catalog["catalogId"], "mappings": mappings},
                                  ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"added {added} listing-only candidates; mapped {len(mappings)} official entries")


if __name__ == "__main__":
    main()
