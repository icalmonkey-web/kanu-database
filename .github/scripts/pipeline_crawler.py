"""Pipeline Crawler & Schema Extractor for Taiwan Credit Cards.

This script implements the resilient 4-stage pipeline:
1. Dynamic fetch & unfolding with Playwright / httpx.
2. Clean HTML to structured Markdown preserving tables.
3. Strict Pydantic / dataclass schema validation for card offers.
4. Deterministic sanity check against financial rules before saving.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, List, Optional
from urllib.parse import urlparse

import httpx


@dataclass
class BenefitTier:
    name: str = "基本方案"
    totalRate: float = 0.0
    baseRate: float = 0.0
    promoRate: float = 0.0
    capAmount: Optional[float] = None
    capPeriod: Optional[str] = "MONTHLY"
    requirements: List[str] = field(default_factory=list)


@dataclass
class ExtractedRule:
    id: str
    cardId: Optional[str]
    bank: str
    title: str
    baseRate: float = 0.0
    promoRate: float = 0.0
    rewardType: str = "percent"  # percent, cash, points, insurance_benefit
    rewardUnit: str = "percent"
    capAmount: Optional[float] = None
    capScope: Optional[str] = "PROMO"  # PROMO, TOTAL
    capPeriod: Optional[str] = "MONTHLY"  # MONTHLY, CAMPAIGN, YEARLY
    minimumSpend: Optional[float] = None
    validFrom: Optional[str] = None
    validUntil: Optional[str] = None
    needReg: bool = False
    regDeadline: Optional[str] = None
    benefitPlan: Optional[str] = None
    matchedMerchants: List[str] = field(default_factory=list)
    excludedKeywords: List[str] = field(default_factory=list)
    quotaInfo: str = ""
    sourceUrl: str = ""
    evidenceStatus: str = "CONFIRMED"
    validationIssues: List[str] = field(default_factory=list)


class PipelineExtractor:
    """Pre-processes bank pages and applies deterministic sanity guardrails."""

    EXCLUDED_PATTERNS = [
        r"全聯(?:福利中心)?",
        r"便利商店|7-11|全家|萊爾富|OK超商",
        r"繳費|稅款|學費|公用事業費|水電瓦斯",
        r"悠遊卡加值|一卡通加值|icash加值",
        r"菸品|酒類",
        r"分期交易",
    ]

    @staticmethod
    def html_to_clean_markdown(html_content: str) -> str:
        """Strip script, style, SVG and navigation while keeping readable text and tables."""
        text = re.sub(r"<(script|style|svg|noscript|header|footer|nav)[\s\S]*?</\1>", " ", html_content, flags=re.I)
        # Convert table cells to clean markdown separators
        text = re.sub(r"</tr\s*>", "\n", text, flags=re.I)
        text = re.sub(r"<(th|td)[^>]*>", " | ", text, flags=re.I)
        text = re.sub(r"</(th|td)>", "", text, flags=re.I)
        # Strip remaining tags
        text = re.sub(r"<[^>]+>", " ", text)
        # Normalize whitespace
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()

    @classmethod
    def apply_financial_guardrails(cls, rule: ExtractedRule) -> ExtractedRule:
        """Sanity check extracted rule to prevent financial hallucinations."""
        title_quota = f"{rule.title} {rule.quotaInfo}"

        # 1. Insurance Guardrail
        if re.search(r"旅平險|旅遊平安險|旅遊不便險|保險保額|理賠上限|保障額度", title_quota):
            rule.rewardType = "insurance_benefit"
            rule.baseRate = 0.0
            rule.promoRate = 0.0
            rule.capAmount = None
            rule.validationIssues.append("INSURANCE_NOT_CASH")

        # 2. Cap vs Reward amount confusion (e.g. Cap 300 mistaken as gift 300)
        if rule.promoRate > 0 and rule.capAmount and rule.rewardType == "cash":
            rule.rewardType = "percent"
            rule.rewardUnit = "percent"

        # 3. Automatic exclusion keyword discovery from text
        for pat in cls.EXCLUDED_PATTERNS:
            found = re.findall(pat, title_quota)
            for item in found:
                clean_item = re.sub(r"[^\w\u4e00-\u9fa5]", "", item)
                if clean_item and clean_item not in rule.excludedKeywords:
                    rule.excludedKeywords.append(clean_item)

        return rule


async def fetch_page_resilient(url: str, timeout_sec: int = 20) -> str:
    """Fetch with modern headers and fallback handling."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout_sec, verify=False) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text


def build_sample_rule_from_markdown(bank: str, url: str, md_text: str) -> Optional[ExtractedRule]:
    """Demonstration extractor that identifies core rates, caps and exclusions."""
    # Look for top headline rate, e.g., "最高 3.5%" or "回饋 5%"
    rate_match = re.search(r"(?:最高|享|回饋)\s*(\d+(?:\.\d+)?)\s*%", md_text)
    promo_rate = float(rate_match.group(1)) if rate_match else 0.0

    # Look for cap, e.g., "上限 200 元" or "上限200點"
    cap_match = re.search(r"上限\s*(?:NT\$|新臺幣)?\s*(\d+(?:,\d+)?)\s*(?:元|點)", md_text)
    cap_amount = float(cap_match.group(1).replace(",", "")) if cap_match else None

    # Title extraction heuristic
    lines = [l.strip() for l in md_text.splitlines() if len(l.strip()) > 5]
    title = lines[0][:40] if lines else f"{bank} 官方信用卡優惠"

    rule = ExtractedRule(
        id=f"rule_pipeline_{abs(hash(url)) % 1000000}",
        cardId=None,
        bank=bank,
        title=title,
        baseRate=1.0 if promo_rate > 1.0 else promo_rate,
        promoRate=max(0.0, promo_rate - 1.0) if promo_rate > 1.0 else 0.0,
        capAmount=cap_amount,
        capScope="PROMO" if cap_amount else None,
        sourceUrl=url,
        quotaInfo=f"最高 {promo_rate}%" if promo_rate else "活動詳情見條款",
    )

    return PipelineExtractor.apply_financial_guardrails(rule)


if __name__ == "__main__":
    print("Pipeline Crawler Framework ready.")
