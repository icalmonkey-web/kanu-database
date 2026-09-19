import os
import json
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from google import genai
from google.genai import types

# ==================== 1. 初始化 AI 客戶端 ====================
api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    raise ValueError("GEMINI_API_KEY 環境變數未設定！")

client = genai.Client(api_key=api_key)
TARGET_MODEL = "gemini-2.5-flash"

# 各大銀行官方信用卡總覽入口
FULL_MARKET_PORTALS = [
    {"bank": "國泰世華", "url": "https://www.cathaybk.com.tw/cathaybk/personal/product/credit-card/cards/"},
    {"bank": "玉山銀行", "url": "https://www.esunbank.com/zh-tw/personal/credit-card/intro/bank-card"},
    {"bank": "台新銀行", "url": "https://www.taishinbank.com.tw/TSB/personal/credit/intro/overview/cg021/card001/"},
    {"bank": "台北富邦", "url": "https://www.fubon.com/banking/personal/credit_card/all_card/all_card.htm"},
    {"bank": "永豐銀行", "url": "https://bank.sinopac.com/sinopacBT/personal/credit-card/introduction/list.html"},
    {"bank": "中國信託", "url": "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/index.html"},
    {"bank": "聯邦銀行", "url": "https://activity.ubot.com.tw/2023JiHeCard/index.htm"},
    {"bank": "星展銀行", "url": "https://www.dbs.com.tw/personal-zh/cards/ecocard/default.page"},
    {"bank": "滙豐銀行", "url": "https://www.hsbc.com.tw/credit-cards/products/live-plus/"}
]

def normalize_card_name(name):
    if not name:
        return ""
    n = re.sub(r"\s+", "", name).upper()
    n = re.sub(r"(信用卡|御璽卡|鈦金卡|晶緻卡|無限卡|世界卡|白金卡|商務卡|聯名卡|卡)$", "", n)
    return n

# ==================== 2. Playwright 抓取真實渲染文字 ====================
def fetch_page_content(page, target_url):
    try:
        page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        # 滾動觸發動態資料
        page.evaluate("window.scrollBy(0, 1500)")
        time.sleep(1.5)
        page.evaluate("window.scrollBy(0, 2500)")
        time.sleep(1.5)
        
        visible_text = page.inner_text("body")
        clean_text = re.sub(r"\s+", " ", visible_text).strip()
        return clean_text
    except Exception as e:
        print(f"    ⚠️ 瀏覽器抓取異常: {e}")
        return ""

# ==================== 3. Gemini 結構化解析 ====================
def extract_cards_with_gemini(bank_name, web_text):
    prompt = f"""
你現在是專業金融信用卡資料分析專家。以下是透過瀏覽器完整抓取自【{bank_name}】官方網頁的文字內容。
請仔細研讀文字，提取出該頁面介紹的所有「信用卡名稱」與「回饋權益/加碼登錄活動」。

請嚴格輸出合法純 JSON 格式：
{{
  "cards": [
    {{
      "id": "英數唯一碼(例: {bank_name}_1)",
      "bank": "{bank_name}",
      "cardName": "信用卡全名",
      "themeBg": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
      "textColor": "#ffffff",
      "descTag": "核心特色簡述(10字內)"
    }}
  ],
  "rules": [
    {{
      "id": "規則唯一碼",
      "cardId": "對應卡片的id",
      "title": "回饋活動名稱",
      "scope": "ALL 或 SPECIFIC",
      "matchedMerchants": ["特約店家名單"],
      "searchKeywords": "AI自主聯想之生活搜尋情境詞與代表品牌(以逗號隔開)",
      "baseRate": 1.0,
      "promoRate": 2.0,
      "capAmount": 500,
      "needReg": false,
      "regDeadline": "登錄說明",
      "quotaInfo": "名額限制",
      "excludedKeywords": ["明確排除項目"]
    }}
  ]
}}

原則：
1. 請至少找出 1 張信用卡與其對應之回饋。
2. 數值請填純數字或 null。
3. 若需登錄請將 needReg 標記為 true。

網頁文字內容如下：
{web_text[:12000]}
"""
    try:
        response = client.models.generate_content(
            model=TARGET_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1
            )
        )
        if not response or not response.text:
            print(f"    ❌ AI 回應為空 ({bank_name})")
            return None

        return json.loads(response.text.strip())
    except Exception as e:
        print(f"    ❌ AI 解析或 JSON 轉換失敗 ({bank_name}): {e}")
        return None

# ==================== 4. 主程式 ====================
def main():
    db_path = "data.json"
    data = {
        "version": "2026.09.20-v0",
        "cards": [],
        "rules": [],
        "commonExclusions": [
            {"keywords": ["全聯", "pxmart"], "message": "全聯福利中心多數信用卡列為「非一般消費」無回饋。"},
            {"keywords": ["7-11", "全家", "超商", "便利商店"], "message": "超商實體刷卡多列為排除名單，建議搭配指定行動支付。"},
            {"keywords": ["水費", "電費", "瓦斯", "公用事業", "學費", "稅款"], "message": "政府規費、公用事業水電瓦斯多數信用卡皆排除回饋。"}
        ]
    }

    cards_map = {}
    rules_map = {}
    if os.path.exists(db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                for c in old_data.get("cards", []):
                    key = f"{c.get('bank')}_{normalize_card_name(c.get('cardName'))}"
                    cards_map[key] = c
                for r in old_data.get("rules", []):
                    rules_map[r.get("id")] = r
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="zh-TW",
            viewport={"width": 1440, "height": 900}
        )
        page = context.new_page()

        for portal in FULL_MARKET_PORTALS:
            bank = portal["bank"]
            url = portal["url"]
            print(f"\n==============================")
            print(f"瀏覽器動態加載: [{bank}] {url}")

            web_text = fetch_page_content(page, url)
            if not web_text or len(web_text) < 150:
                print(f"  - 跳過 {bank}（未能取得網頁文字內容）")
                continue

            print(f"  🌐 成功抓取 {len(web_text)} 字元，交付 Gemini 結構化...")
            result = extract_cards_with_gemini(bank, web_text)
            if not result or not result.get("cards"):
                print(f"  - 跳過 {bank}（未能成功提取卡片）")
                continue

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
                    print(f"  + 新卡入庫: [{bank}] {raw_name}")
                id_map[c.get("id")] = cards_map[norm_key]["id"]

            for r in result.get("rules", []):
                title = r.get("title", "").strip()
                if not title:
                    continue
                if r.get("cardId") in id_map:
                    r["cardId"] = id_map[r["cardId"]]
                rule_key = f"{r.get('cardId')}_{title}"
                rules_map[rule_key] = r
                if r.get("needReg"):
                    print(f"  🔥 登錄活動: {title}")
                else:
                    print(f"  + 權益條款: {title}")

        browser.close()

    data["cards"] = list(cards_map.values())
    data["rules"] = list(rules_map.values())
    data["version"] = datetime.utcnow().strftime("%Y.%m.%d-v%H%M%S")
    data["lastUpdated"] = datetime.utcnow().isoformat() + "Z"

    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total_reg = sum(1 for r in data["rules"] if r.get("needReg"))
    print(f"\n==============================")
    print(f"[完成] 全市場資料庫更新完畢！")
    print(f"總卡片數: {len(data['cards'])}, 總規則數: {len(data['rules'])}, 需登錄活動數: {total_reg}")

if __name__ == "__main__":
    main()
