.github/scripts/update_data.py
import os
import json
import re
import time
from urllib.parse import urljoin
from datetime import datetime
from playwright.sync_api import sync_playwright
from google import genai
from google.genai import types

# 1. 初始化 AI 客戶端
api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    raise ValueError("GEMINI_API_KEY 環境變數未設定！")

client = genai.Client(api_key=api_key)

CANDIDATE_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3-flash-preview",
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-live-preview",
    "gemini-2.5-flash-lite"
]

# 核心入口：包含卡片總覽與活動大廳
PORTAL_CONFIGS = [
    {
        "bank": "永豐銀行",
        "card_urls": [
            "https://bank.sinopac.com/sinopacBT/personal/credit-card/introduction/list.html"
        ],
        "event_portals": [
            "https://bank.sinopac.com/sinopacBT/personal/credit-card/discount/list.html"
        ],
        "event_link_pattern": r"discount/(?!list)[^\"']+\.html"
    },
    {
        "bank": "國泰世華",
        "card_urls": [
            "https://www.cathaybk.com.tw/cathaybk/personal/product/credit-card/cards/"
        ],
        "event_portals": [
            "https://www.cathaybk.com.tw/cathaybk/personal/event/overview/"
        ],
        "event_link_pattern": r"/personal/event/[^\"']+"
    },
    {
        "bank": "玉山銀行",
        "card_urls": [
            "https://www.esunbank.com/zh-tw/personal/credit-card/intro/bank-card"
        ],
        "event_portals": [
            "https://www.esunbank.com/zh-tw/personal/credit-card/discount/shops",
            "https://www.esunbank.com/zh-tw/personal/credit-card/tools/sign-up"
        ],
        "event_link_pattern": r"/personal/credit-card/(discount|tools)/[^\"']+"
    },
    {
        "bank": "台北富邦",
        "card_urls": [
            "https://www.fubon.com/banking/personal/credit_card/all_card/all_card.htm"
        ],
        "event_portals": [
            "https://www.fubon.com/banking/personal/credit_card/event/event.htm"
        ],
        "event_link_pattern": r"/event/[^\"']+\.htm"
    },
    {
        "bank": "台新銀行",
        "card_urls": [
            "https://www.taishinbank.com.tw/TSB/personal/credit/intro/overview/cg021/card001/"
        ],
        "event_portals": [
            "https://www.taishinbank.com.tw/TSB/personal/credit/discount/"
        ],
        "event_link_pattern": r"/personal/credit/discount/[^\"']+"
    },
    {
        "bank": "中國信託",
        "card_urls": [
            "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/index.html"
        ],
        "event_portals": [
            "https://www.ctbcbank.com/twrbo/zh_tw/cc_index/cc_offer/cc_offer_register.html"
        ],
        "event_link_pattern": r"/cc_offer/[^\"']+"
    }
]

def normalize_card_name(name):
    if not name:
        return ""
    n = re.sub(r"\s+", "", name).upper()
    n = re.sub(r"(信用卡|御璽卡|鈦金卡|晶緻卡|無限卡|世界卡|白金卡|商務卡|聯名卡|卡)$", "", n)
    return n

def fetch_page(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        page.evaluate("window.scrollBy(0, 1500)")
        time.sleep(1)
        text = page.inner_text("body")
        return re.sub(r"\s+", " ", text).strip()
    except Exception as e:
        return ""

def discover_event_links(page, portal_url, pattern, max_links=8):
    """第 1 層：自動從大廳頁面挖掘所有子活動連結"""
    found_urls = set()
    try:
        page.goto(portal_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        page.evaluate("window.scrollBy(0, 2000)")
        time.sleep(1)

        links = page.eval_on_selector_all("a[href]", "elements => elements.map(e => e.getAttribute('href'))")
        for href in links:
            if not href or href.startswith("javascript") or href.startswith("#"):
                continue
            full_url = urljoin(portal_url, href)
            if re.search(pattern, full_url, re.IGNORECASE) and full_url != portal_url:
                found_urls.add(full_url)
                if len(found_urls) >= max_links:
                    break
    except Exception as e:
        print(f"    ⚠️ 探索子連結失敗: {e}")
    return list(found_urls)

def extract_with_gemini(bank_name, content, is_event_detail=False):
    role_desc = "活動詳情分析專家" if is_event_detail else "信用卡型錄審查專家"
    prompt = f"""
你現在是台灣信用卡{role_desc}。以下是自【{bank_name}】官方網頁抓取的純文字。
請分析提取「信用卡名稱」與「回饋權益/加碼活動」。

包含四類活動：
1. 基礎常態權益 (BASE_BENEFIT, needReg: false)
2. 免登錄最新促銷活動 (DIRECT_PROMOTION, needReg: false)
3. 需登錄之活動 (REG_PROMOTION, needReg: true)
4. 特定地區加碼(如日本、韓國、海外加碼) (EXTRA_BOOST)

【searchKeywords 強制展開】：
每筆規則必須自主聯想至少 10 個常用搜尋字詞（以逗號隔開）：
- 現金回饋、點數、刷卡金
- 若為國外/指定國家，必須展開 [國外, 海外, 出國, 日本, 韓國, 機票, 飯店, 免稅店, 國外回饋]
- 日常消費場景 [餐廳, 吃飯, 外送, 加油, 網購, 無腦刷]

嚴格輸出純 JSON 格式：
{{
  "cards": [
    {{
      "id": "英數唯一碼",
      "bank": "{bank_name}",
      "cardName": "信用卡全名或全卡友",
      "themeBg": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
      "textColor": "#ffffff",
      "descTag": "特色簡述"
    }}
  ],
  "rules": [
    {{
      "id": "規則唯一碼",
      "cardId": "對應卡片的id",
      "title": "回饋活動名稱",
      "activityType": "BASE_BENEFIT 或 DIRECT_PROMOTION 或 REG_PROMOTION 或 EXTRA_BOOST",
      "scope": "ALL 或 SPECIFIC",
      "matchedMerchants": ["特約品牌或適用國家清單"],
      "searchKeywords": "至少10個深度聯想詞、國家名、口語詞(以逗號隔開)",
      "baseRate": 1.0,
      "promoRate": 2.0,
      "capAmount": 500,
      "needReg": false,
      "regDeadline": "登錄時間或活動期限",
      "quotaInfo": "名額限制說明",
      "excludedKeywords": ["明確排除項目"]
    }}
  ]
}}

網頁文字：
{content[:12000]}
"""
    response_text = None
    for model_name in CANDIDATE_MODELS:
        try:
            res = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2
                )
            )
            if res and res.text:
                response_text = res.text
                break
        except Exception:
            continue

    if not response_text:
        return None

    try:
        return json.loads(response_text.strip())
    except Exception:
        return None

def main():
    db_path = "data.json"
    data = {
        "version": "2026.09.20-v0",
        "cards": [],
        "rules": [],
        "commonExclusions": [
            {"keywords": ["全聯", "pxmart"], "message": "全聯大部分信用卡列為「非一般消費」無回饋。"},
            {"keywords": ["7-11", "全家", "超商", "便利商店"], "message": "超商實體刷卡多列為排除名單，建議搭配指定行動支付。"},
            {"keywords": ["水費", "電費", "瓦斯", "公用事業", "學費", "稅款"], "message": "政府規費、公用事業水電瓦斯多數信用卡皆排除回饋。"}
        ]
    }

    cards_map = {}
    rules_map = {}
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                old = json.load(f)
                for c in old.get("cards", []):
                    cards_map[f"{c.get('bank')}_{normalize_card_name(c.get('cardName'))}"] = c
                for r in old.get("rules", []):
                    rules_map[r.get("id")] = r
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled", "--no-sandbox"])
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="zh-TW",
            viewport={"width": 1440, "height": 900}
        )
        page = context.new_page()

        for config in PORTAL_CONFIGS:
            bank = config["bank"]
            print(f"\n==============================")
            print(f"🚀 開始全面探索銀行: {bank}")

            # 1. 爬卡片型錄
            for curl in config.get("card_urls", []):
                print(f"  💳 抓取卡片型錄: {curl}")
                text = fetch_page(page, curl)
                if text and len(text) > 200:
                    res = extract_with_gemini(bank, text, is_event_detail=False)
                    if res:
                        merge_data(bank, res, cards_map, rules_map)

            # 2. 探索活動大廳並自動挖出子活動頁面
            for e_portal in config.get("event_portals", []):
                print(f"  🎪 進入活動大廳: {e_portal}")
                child_urls = discover_event_links(page, e_portal, config["event_link_pattern"], max_links=6)
                print(f"    🔎 自動挖掘出 {len(child_urls)} 個最新活動專頁！")

                for sub_url in child_urls:
                    print(f"      👉 深入分析活動頁: {sub_url}")
                    sub_text = fetch_page(page, sub_url)
                    if sub_text and len(sub_text) > 150:
                        res = extract_with_gemini(bank, sub_text, is_event_detail=True)
                        if res:
                            merge_data(bank, res, cards_map, rules_map)

        browser.close()

    data["cards"] = list(cards_map.values())
    data["rules"] = list(rules_map.values())
    data["version"] = datetime.utcnow().strftime("%Y.%m.%d-v%H%M%S")
    data["lastUpdated"] = datetime.utcnow().isoformat() + "Z"

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_reg = sum(1 for r in data["rules"] if r.get("needReg"))
    total_direct = sum(1 for r in data["rules"] if not r.get("needReg"))
    print(f"\n==============================")
    print(f"[完成] 全市場資料庫深度自動探索完成！")
    print(f"總卡片數: {len(data['cards'])}, 總規則/活動數: {len(data['rules'])}")
    print(f"需登錄活動: {total_reg} 項, 免登錄與常態活動: {total_direct} 項")

def merge_data(bank, result, cards_map, rules_map):
    id_map = {}
    for c in result.get("cards", []):
        raw_name = c.get("cardName", "").strip()
        if not raw_name:
            continue
        norm_key = f"{bank}_{normalize_card_name(raw_name)}"
        if norm_key not in cards_map:
            std_id = f"card_{bank}_{len(cards_map) + 1}"
            c["id"] = std_id
            cards_map[norm_key] = c
            print(f"      + 新卡入庫: [{bank}] {raw_name}")
        id_map[c.get("id")] = cards_map[norm_key]["id"]

    for r in result.get("rules", []):
        title = r.get("title", "").strip()
        if not title:
            continue
        if r.get("cardId") in id_map:
            r["cardId"] = id_map[r["cardId"]]
        elif not r.get("cardId") and cards_map:
            first_card = next((c for c in cards_map.values() if c.get("bank") == bank), None)
            if first_card:
                r["cardId"] = first_card["id"]

        rule_key = f"{r.get('cardId')}_{title}"
        rules_map[rule_key] = r
        status = "🔥需登錄" if r.get("needReg") else "✨免登錄"
        print(f"      {status} [{r.get('activityType', 'PROMO')}]: {title}")

if __name__ == "__main__":
    main()
