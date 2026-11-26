"""Quarantine existing point rules with an unresolved percentage and numeric award."""

import json
from pathlib import Path

from update_data import quarantine_ambiguous_point_cap


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data.json"


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    changed = []
    for rule in data["rules"]:
        before = (tuple(rule.get("validationIssues") or []), rule.get("quickSearchEligible"))
        quarantine_ambiguous_point_cap(rule)
        after = (tuple(rule.get("validationIssues") or []), rule.get("quickSearchEligible"))
        if after != before:
            changed.append(rule["id"])
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"quarantined {len(changed)} ambiguous point-award records")


if __name__ == "__main__":
    main()
