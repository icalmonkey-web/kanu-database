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

RUN_STATS = {
    "pages_fetched": 0,
    "page_failures": 0,
    "ai_successes": 0,
    "ai_failures": 0,
    "new_cards": 0,
    "new_rules": 0,
}

CANDIDATE_MODELS = [
    os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    "gemini-2.5-flash-lite",
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
    },
    # 第二階段擴充：每家銀行至少有信用卡入口與活動/登錄入口；抓不到時會記錄失敗，
    # 不會清空既有可用資料。來源必須是銀行官方網域。
    {"bank": "星展銀行", "card_urls": ["https://www.dbs.com.tw/personal-zh/cards.html"], "event_portals": ["https://www.dbs.com.tw/personal-zh/promotions.html"], "event_link_pattern": r"/(cards|promotions|campaigns)/[^\"']+"},
    {"bank": "滙豐銀行", "card_urls": ["https://www.hsbc.com.tw/credit-cards/"], "event_portals": ["https://www.hsbc.com.tw/credit-cards/offers/"], "event_link_pattern": r"/credit-cards/[^\"']+"},
    {"bank": "渣打銀行", "card_urls": ["https://www.sc.com/tw/credit-cards/"], "event_portals": ["https://www.sc.com/tw/credit-cards/offers/"], "event_link_pattern": r"/tw/(credit-cards|promotions)/[^\"']+"},
    {"bank": "聯邦銀行", "card_urls": ["https://www.ubot.com.tw/personal-banking/credit-card/"], "event_portals": ["https://www.ubot.com.tw/personal-banking/credit-card/discount/"], "event_link_pattern": r"/personal-banking/credit-card/[^\"']+"},
    {"bank": "元大銀行", "card_urls": ["https://www.yuantabank.com.tw/bank-web/personal/credit-card/"], "event_portals": ["https://www.yuantabank.com.tw/bank-web/personal/credit-card/discount/"], "event_link_pattern": r"/bank-web/personal/credit-card/[^\"']+"},
    {"bank": "華南銀行", "card_urls": ["https://www.hncb.com.tw/wps/portal/HNCB/creditcard"], "event_portals": ["https://www.hncb.com.tw/wps/portal/HNCB/creditcard"], "event_link_pattern": r"/(creditcard|credit-card)/[^\"']+"},
    {"bank": "第一銀行", "card_urls": ["https://card.firstbank.com.tw/"], "event_portals": ["https://card.firstbank.com.tw/"], "event_link_pattern": r"/(card|event|activity|discount)[^\"']*"},
    {"bank": "彰化銀行", "card_urls": ["https://www.bankchb.com/frontend/mashup.jsp?funcId=33"], "event_portals": ["https://www.bankchb.com/frontend/mashup.jsp?funcId=33"], "event_link_pattern": r"/(credit|card|event|activity)[^\"']*"},
    {"bank": "兆豐銀行", "card_urls": ["https://www.megabank.com.tw/personal/credit-card"], "event_portals": ["https://www.megabank.com.tw/personal/credit-card"], "event_link_pattern": r"/(credit-card|creditcard|event|activity)[^\"']*"},
    {"bank": "合作金庫", "card_urls": ["https://www.tcb-bank.com.tw/personal-banking/credit-card"], "event_portals": ["https://www.tcb-bank.com.tw/personal-banking/credit-card"], "event_link_pattern": r"/personal-banking/credit-card/[^\"']+"},
    {"bank": "上海商銀", "card_urls": ["https://www.scsb.com.tw/content/card/card.html"], "event_portals": ["https://www.scsb.com.tw/content/card/discount.html"], "event_link_pattern": r"/content/card/[^\"']+"},
    {"bank": "遠東商銀", "card_urls": ["https://www.feib.com.tw/"], "event_portals": ["https://www.feib.com.tw/"], "event_link_pattern": r"/(credit|card|event|activity|campaign)[^\"']*"},
    {"bank": "凱基銀行", "card_urls": ["https://www.kgibank.com/TW/Personal/CreditCard"], "event_portals": ["https://www.kgibank.com/TW/Personal/CreditCard"], "event_link_pattern": r"/TW/Personal/CreditCard[^\"']*"},
    {"bank": "安泰銀行", "card_urls": ["https://www.entiebank.com.tw/"], "event_portals": ["https://www.entiebank.com.tw/"], "event_link_pattern": r"/(credit|card|event|activity)[^\"']*"},
    {"bank": "樂天信用卡", "card_urls": ["https://www.rakuten.com.tw/card/"], "event_portals": ["https://www.rakuten.com.tw/card/"], "event_link_pattern": r"/card/[^\"']+"},
    {"bank": "陽信銀行", "card_urls": ["https://www.sunnybank.com.tw/"], "event_portals": ["https://www.sunnybank.com.tw/"], "event_link_pattern": r"/(credit|card|event|activity)[^\"']*"},
    {"bank": "三信商銀", "card_urls": ["https://www.cotabank.com.tw/"], "event_portals": ["https://www.cotabank.com.tw/"], "event_link_pattern": r"/(credit|card|event|activity)[^\"']*"},
]

def normalize_card_name(name):
    if not name:
        return ""
    n = re.sub(r"\s+", "", name).upper()
    n = re.sub(r"(信用卡|御璽卡|鈦金卡|晶緻卡|無限卡|世界卡|白金卡|商務卡|聯名卡|卡)$", "", n)
    return n

def parse_explicit_date(value):
    """只解析 YYYY/MM/DD 或 YYYY-MM-DD，避免把「每月 1 日開放」誤判成過期。"""
    if not value:
        return None
    matches = re.findall(r"(20\d{2})\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})", str(value))
    if not matches:
        return None
    year, month, day = matches[-1]
    try:
        return datetime(int(year), int(month), int(day), 23, 59, 59)
    except ValueError:
        return None

def enrich_reward_fields(rule, source_url):
    """補齊前端不再猜測 0% 的必要欄位，並保留官方來源與抓取時間。"""
    title = f"{rule.get('title', '')} {rule.get('quotaInfo', '')}"
    base_rate = float(rule.get("baseRate") or 0)
    promo_rate = float(rule.get("promoRate") or 0)
    cap = float(rule.get("capAmount") or 0)
    if not rule.get("rewardType"):
        if promo_rate or base_rate:
            rule["rewardType"] = "percent"
            rule.setdefault("rewardAmount", promo_rate or base_rate)
            rule.setdefault("rewardUnit", "percent")
        elif re.search(r"抽獎|抽出|驚喜抽", title):
            rule["rewardType"] = "draw"
            rule.setdefault("rewardAmount", cap)
            rule.setdefault("rewardUnit", "TWD")
        elif re.search(r"0利率|分期", title) and not cap:
            rule["rewardType"] = "installment"
            rule.setdefault("rewardUnit", "months")
        else:
            rule["rewardType"] = "cash"
            rule.setdefault("rewardAmount", cap)
            rule.setdefault("rewardUnit", "TWD")
    rule.setdefault("sourceUrl", source_url)
    rule["fetchedAt"] = datetime.utcnow().isoformat() + "Z"
    return rule

def fetch_page(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=25000)
        time.sleep(1.5)
        page.evaluate("window.scrollBy(0, 1500)")
        time.sleep(1)
        text = page.inner_text("body")
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 150:
            RUN_STATS["page_failures"] += 1
            print(f"    ⚠️ 頁面內容不足，略過：{url} ({len(text)} 字)")
            return ""
        RUN_STATS["pages_fetched"] += 1
        return text
    except Exception as e:
        RUN_STATS["page_failures"] += 1
        print(f"    ⚠️ 網頁抓取失敗：{url} | {type(e).__name__}: {e}")
        return ""

def discover_event_links(page, portal_url, pattern, max_links=25):
    """從官方活動大廳擷取活動子頁；上限可由環境變數調整，避免每家固定只有 6 頁。"""
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

def extract_with_gemini(bank_name, content, source_url, is_event_detail=False):
    role_desc = "活動詳情分析專家" if is_event_detail else "信用卡型錄審查專家"
    prompt = f"""
你現在是台灣頂尖金融條款與信用卡精算專家。
以下是透過瀏覽器抓取自【{bank_name}】官方網頁的純文字內容。

請研讀內容，提取信用卡與權益規則，並依據以下【精確關聯與防幻覺鐵律】處理 searchKeywords：

【嚴格邊界約束（防止胡亂腦補）】：
1. 若活動為「指定特店 / 百大特店 / 特約通路」（scope: SPECIFIC）：
   - matchedMerchants：必須完全依據內文列出官方特約店家（例如有 LINE Pay、街口、momo，就只列這些）。
   - searchKeywords 聯想範圍【嚴格受限於特約名單內】：
     * 只能為名單內確有的店家展開別名、中英文、縮寫、支付形態與拼音（例如：名單有 LINE Pay -> 展開 linepay, 連線支付, 行動支付；名單有 momo -> 展開 富邦momo, momo購物, 網購）。
     * 【嚴禁憑空捏造】：若特約名單中【沒有】悠遊卡、一卡通、全聯、家樂福，就【絕對不能】出現在 searchKeywords 裡！
2. 若活動為「廣義全通路」（scope: ALL，例如不限店家之海外實體消費、全台一般消費）：
   - 才能自主展開該情境的大範圍生活詞（如出國、免稅店、外幣、日幣、韓元、機票、飯店）。
3. 方案門檻必須誠實交代（quotaInfo）：
   - 卡片若有方案分級（如簡單選、任意選、UP選，或集精選、切換方案）：
   - 必須清楚註明各方案門檻與加碼差異，不可只寫最高趴數。

嚴格輸出合法純 JSON 格式：
{{
  "cards": [
    {{
      "id": "英數唯一碼",
      "bank": "{bank_name}",
      "cardName": "信用卡全名或全卡友",
      "themeBg": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
      "textColor": "#ffffff",
      "descTag": "核心特色簡述(10字內)"
    }}
  ],
  "rules": [
    {{
      "id": "規則唯一碼",
      "cardId": "對應卡片的id",
      "title": "回饋活動名稱(方案標明)",
      "activityType": "BASE_BENEFIT 或 DIRECT_PROMOTION 或 REG_PROMOTION 或 EXTRA_BOOST",
      "scope": "ALL 或 SPECIFIC",
      "matchedMerchants": ["條款內確實出現之特約品牌清單"],
      "searchKeywords": "依據名單實體展開之精確別名、中英文與生活情境詞(嚴禁無中生有，以逗號隔開)",
      "baseRate": 1.0,
      "promoRate": 2.0,
      "rewardType": "percent 或 cash 或 points 或 draw 或 installment",
      "rewardAmount": 200,
      "rewardUnit": "percent 或 TWD 或 points 或 chance",
      "capAmount": 500,
      "needReg": false,
      "regDeadline": "登錄時間或方案適用期",
      "validUntil": "YYYY-MM-DD；未明示則留空字串",
      "sourceUrl": "{source_url}",
      "quotaInfo": "明確門檻說明(例: 簡單選人人享/任意選需指定特店/UP選需任務門檻)",
      "excludedKeywords": ["明確排除項目"]
    }}
  ]
}}

網頁文字如下：
{content[:14000]}
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
        except Exception as exc:
            print(f"    ⚠️ Gemini 模型 {model_name} 呼叫失敗：{type(exc).__name__}: {exc}")
            continue

    if not response_text:
        RUN_STATS["ai_failures"] += 1
        print(f"    ⚠️ AI 未產生可用 JSON：{source_url}")
        return None

    try:
        result = json.loads(response_text.strip())
        RUN_STATS["ai_successes"] += 1
        return result
    except Exception as exc:
        RUN_STATS["ai_failures"] += 1
        print(f"    ⚠️ AI JSON 解析失敗：{source_url} | {type(exc).__name__}: {exc}")
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
                    res = extract_with_gemini(bank, text, curl, is_event_detail=False)
                    if res:
                        merge_data(bank, res, cards_map, rules_map, curl)

            # 2. 探索活動大廳並自動挖出子活動頁面
            for e_portal in config.get("event_portals", []):
                print(f"  🎪 進入活動大廳: {e_portal}")
                max_pages = int(os.environ.get("MAX_EVENT_PAGES_PER_BANK", "25"))
                child_urls = discover_event_links(page, e_portal, config["event_link_pattern"], max_links=max_pages)
                print(f"    🔎 自動挖掘出 {len(child_urls)} 個最新活動專頁！")

                for sub_url in child_urls:
                    print(f"      👉 深入分析活動頁: {sub_url}")
                    sub_text = fetch_page(page, sub_url)
                    if sub_text and len(sub_text) > 150:
                        res = extract_with_gemini(bank, sub_text, sub_url, is_event_detail=True)
                        if res:
                            merge_data(bank, res, cards_map, rules_map, sub_url)

        browser.close()

    now = datetime.utcnow()
    active_rules = []
    for rule in rules_map.values():
        explicit_end = parse_explicit_date(rule.get("validUntil")) or parse_explicit_date(rule.get("regDeadline"))
        if explicit_end and explicit_end < now:
            continue
        active_rules.append(enrich_reward_fields(rule, rule.get("sourceUrl", "")))

    data["cards"] = list(cards_map.values())
    data["rules"] = active_rules
    data["version"] = datetime.utcnow().strftime("%Y.%m.%d-v%H%M%S")
    data["lastUpdated"] = datetime.utcnow().isoformat() + "Z"

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_reg = sum(1 for r in data["rules"] if r.get("needReg"))
    total_direct = sum(1 for r in data["rules"] if not r.get("needReg"))
    print(f"[掃描統計] 頁面成功: {RUN_STATS['pages_fetched']} | 頁面失敗: {RUN_STATS['page_failures']} | AI 成功: {RUN_STATS['ai_successes']} | AI 失敗: {RUN_STATS['ai_failures']} | 新卡: {RUN_STATS['new_cards']} | 新規則: {RUN_STATS['new_rules']}")
    if RUN_STATS["ai_successes"] == 0:
        raise RuntimeError("本次沒有任何官方頁面成功完成 AI 結構化；拒絕發布可能不完整的資料庫。")
    print(f"\n==============================")
    print(f"[完成] 全市場資料庫深度自動探索完成！")
    print(f"總卡片數: {len(data['cards'])}, 總規則/活動數: {len(data['rules'])}")
    print(f"需登錄活動: {total_reg} 項, 免登錄與常態活動: {total_direct} 項")

def merge_data(bank, result, cards_map, rules_map, source_url):
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
            RUN_STATS["new_cards"] += 1
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

        r = enrich_reward_fields(r, source_url)
        r["sourceUrl"] = source_url
        rule_key = f"{r.get('cardId')}_{title}"
        if rule_key not in rules_map:
            RUN_STATS["new_rules"] += 1
        rules_map[rule_key] = r
        status = "🔥需登錄" if r.get("needReg") else "✨免登錄"
        print(f"      {status} [{r.get('activityType', 'PROMO')}]: {title}")

if __name__ == "__main__":
    main()
