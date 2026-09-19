import os
import json
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from google import genai

# ==================== 1. 初始化 AI 客戶端 ====================
api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    raise ValueError("GEMINI_API_KEY 環境變數未設定！")

client = genai.Client(api_key=api_key)
CANDIDATE_MODELS = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-1.5-flash"]

# ==================== 2. 全行信用卡專屬入口 (涵蓋總覽與主力卡) ====================
FULL_MARKET_PORTALS = [
    # 國泰世華
    {"bank": "國泰世華", "url": "https://www.cathaybk.com.tw/cathaybk/personal/product/credit-card/cards/"},
    {"bank": "國泰世華", "url": "https://www.cathaybk.com.tw/cathaybk/personal/product/credit-card/cards/cube/"},

    # 玉山銀行
    {"bank": "玉山銀行", "url": "https://www.esunbank.com/zh-tw/personal/credit-card/intro/bank-card"},
    {"bank": "玉山銀行", "url": "https://www.esunbank.com/zh-tw/personal/credit-card/intro/bank-card/u-bear"},

    # 台新銀行
    {"bank": "台新銀行", "url": "https://www.taishinbank.com.tw/TSB/personal/credit/intro/overview/cg021/card001/"},
    {"bank": "台新銀行", "url": "https://www.taishinbank.com.tw/TSB/personal/credit/intro/overview/index.html"},

    # 台北富邦
    {"bank": "台北富邦", "url": "https://www.fubon.com/banking/personal/credit_card/all_card/costco/costco.htm"},
    {"bank": "台北富邦", "url": "https://www.fubon.com/banking/personal/credit_card/all_card/jcard/jcard.htm"},
    {"bank": "台北富邦", "url": "https://www.fubon.com/banking/personal/credit_card/all_card/momo/momo.htm"},

    # 永豐銀行
    {"bank": "永豐銀行", "url": "https://bank.sinopac.com/sinopacBT/personal/credit-card/introduction/bank-card/sport-card.html"},
    {"bank": "永豐銀行", "url": "https://bank.sinopac.com/sinopacBT/personal/credit-card/introduction/bank-card/daway.html"},

    # 聯邦銀行
    {"bank": "聯邦銀行", "url": "https://activity.ubot.com.tw/2023JiHeCard/index.htm"},
    {"bank": "聯邦銀行", "url": "https://card.ubot.com.tw/eCard/Card/List.aspx"},

    # 中國信託
    {"bank": "中國信託", "url": "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/LINEPay/index.html"},
    {"bank": "中國信託", "url": "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/ALLMe/index.html"},

    # 星展銀行
    {"bank": "星展銀行", "url": "https://www.dbs.com.tw/personal-zh/cards/ecocard/default.page"},
    {"bank": "星展銀行", "url": "https://www.dbs.com.tw/personal-zh/cards/default.page"},

    # 滙豐銀行
    {"bank": "滙豐銀行", "url": "https://www.hsbc.com.tw/credit-cards/products/live-plus/"},
    {"bank": "滙豐銀行", "url": "https://www.hsbc.com.tw/credit-cards/products/cash-back-titanium/"}
]

def normalize_card_name(name):
    if not name:
        return ""
    n = re.sub(r"\s+", "", name).upper()
    n = re.sub(r"(信用卡|御璽卡|鈦金卡|晶緻卡|無限卡|世界卡|白金卡|商務卡|聯名卡|卡)$", "", n)
    return n

# ==================== 3. 深度滾動與 SPA 完整加載核心 ====================
def fetch_dynamic_content(page, target_url):
    try:
        # 放寬載入逾時，並等待網路請求靜止 (networkidle)
        page.goto(target_url, wait_until="load", timeout=40000)
        time.sleep(2)

        # 連續滾動以觸發動態加載
        for scroll_step in [600, 1500, 2500, 4000]:
            page.evaluate(f"window.scrollTo(0, {scroll_step})")
            time.sleep(1)

        # 抓取渲染後的完整 Body 純文字
        visible_text = page.inner_text("body")
        clean_text = re.sub(r"\s+", " ", visible_text).strip()
        return clean_text[:20000]
    except Exception:
        # 若 networkidle 逾時，嘗試降級抓取目前已渲染的內容
        try:
            visible_text = page.inner_text("body")
            clean_text = re.sub(r"\s+", " ", visible_text).strip()
            if len(clean_text) > 300:
                return clean_text[:20000]
        except Exception:
            pass
        return ""

# ==================== 4. AI 結構化提取核心 ====================
def call_gemini(prompt):
    for model_name in CANDIDATE_MODELS:
        try:
            res = client.models.generate_content(model=model_name, contents=prompt)
            if res and res.text:
                return res.text
        except Exception:
            continue
    return None

def parse_bank_data(bank_name, content):
    prompt = f"""
你現在是專業金融信用卡專家。以下是透過瀏覽器完整渲染之【{bank_name}】官方網頁純文字。
請仔細研讀內文，提取出所有出現的信用卡卡片資訊、各項消費回饋趴數、以及需登錄的優惠活動。

嚴格輸出純 JSON 格式如下：
{{
  "cards": [
    {{
      "id": "英數唯一識別碼",
      "bank": "{bank_name}",
      "cardName": "信用卡名稱",
      "themeBg": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
      "textColor": "#ffffff",
      "descTag": "核心亮點(10字內)"
    }}
  ],
  "rules": [
    {{
      "id": "規則唯一識別碼",
      "cardId": "對應卡片id",
      "title": "回饋活動名稱",
      "scope": "ALL 或 SPECIFIC",
      "matchedMerchants": ["條款提及之特約商家"],
      "searchKeywords": "AI自主發想展開之搜尋詞、情境詞、通路名(以逗號隔開)",
      "baseRate": 1.0,
      "promoRate": 2.0,
      "capAmount": 500,
      "needReg": false,
      "regDeadline": "截止時間或說明",
      "quotaInfo": "名額限制或門檻",
      "excludedKeywords": ["明確排除不回饋項目"]
    }}
  ]
}}

原則：
1. 只要文字有提到信用卡或回饋內容，請務必至少提取 1 張卡與其權益，不可回傳空陣列。
2. 數值（baseRate, promoRate, capAmount）請填純數字或 null。
3. 若需登錄請設定 needReg 為 true。
4. 輸出必須為合法純 JSON，絕不包含 ```json 或額外解釋。

網頁內容如下：
{content[:14000]}
"""
    raw = call_gemini(prompt)
    if not raw:
        return None

    try:
        clean = re.sub(r"^```(json)?", "", raw.strip(), flags=re.IGNORECASE)
        clean = re.sub(r"```$", "", clean.strip())
        return json.loads(clean.strip())
    except Exception as e:
        print(f"  ❌ 解析 JSON 失敗 ({bank_name}): {e}")
        return None

# ==================== 5. 主程序 ====================
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

    # 累計模式：讀取既有資料庫，永不刪除已有資料
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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900}
        )
        page = context.new_page()

        for portal in FULL_MARKET_PORTALS:
            bank = portal["bank"]
            url = portal["url"]
            print(f"\n==============================")
            print(f"開始渲染探索: [{bank}] {url[:50]}...")

            content = fetch_dynamic_content(page, url)
            if not content or len(content) < 200:
                print(f"  - 跳過 {bank}（內容不足或連線失敗）")
                continue

            print(f"  🌐 成功加載完整渲染文字: {len(content)} 字元，交付 AI 分析中...")
            result = parse_bank_data(bank, content)
            if not result or not result.get("cards"):
                print(f"  - 跳過 {bank}（無有效卡片回傳）")
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
