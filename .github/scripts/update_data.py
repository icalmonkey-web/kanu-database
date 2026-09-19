.github/scripts/update_data.py
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

# ==================== 2. 全行信用卡目錄入口清單 ====================
FULL_MARKET_PORTALS = [
    {
        "bank": "國泰世華",
        "url": "https://www.cathaybk.com.tw/cathaybk/personal/product/credit-card/cards/"
    },
    {
        "bank": "玉山銀行",
        "url": "https://www.esunbank.com/zh-tw/personal/credit-card/intro/bank-card"
    },
    {
        "bank": "台新銀行",
        "url": "https://www.taishinbank.com.tw/TSB/personal/credit/intro/overview/cg021/card001/"
    },
    {
        "bank": "台北富邦",
        "url": "https://www.fubon.com/banking/personal/credit_card/all_card/all_card.htm"
    },
    {
        "bank": "永豐銀行",
        "url": "https://bank.sinopac.com/sinopacBT/personal/credit-card/introduction/list.html"
    },
    {
        "bank": "聯邦銀行",
        "url": "https://card.ubot.com.tw/eCard/Card/List.aspx"
    },
    {
        "bank": "中國信託",
        "url": "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/index.html"
    },
    {
        "bank": "星展銀行",
        "url": "https://www.dbs.com.tw/personal-zh/cards/default.page"
    },
    {
        "bank": "滙豐銀行",
        "url": "https://www.hsbc.com.tw/credit-cards/products/"
    }
]

def normalize_card_name(name):
    """卡片名稱正規化，過濾冗贅後綴以精確去重"""
    if not name:
        return ""
    n = re.sub(r"\s+", "", name).upper()
    n = re.sub(r"(信用卡|御璽卡|鈦金卡|晶緻卡|無限卡|世界卡|白金卡|商務卡|卡)$", "", n)
    return n

# ==================== 3. Playwright 真實瀏覽器動態渲染核心 ====================
def fetch_dynamic_content(page, target_url):
    """使用無頭 Chrome 完整執行 JavaScript 並取得渲染後的網頁純文字"""
    try:
        # 設定模擬真實使用者的 User-Agent 與語系
        page.set_extra_http_headers({
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        })
        
        # 前往目標網址，等待 DOM 加載完成
        response = page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
        
        # 針對 SPA 框架給予 3 秒等待動態內容載入完成
        time.sleep(3)
        
        # 模擬向下滑動以觸發可能存在的懶加載 (Lazy loading)
        page.evaluate("window.scrollTo(0, 800)")
        time.sleep(1)

        # 抓取頁面所有可見的文字內容
        visible_text = page.inner_text("body")
        
        # 清除過多連續空白與換行
        clean_text = re.sub(r"\s+", " ", visible_text).strip()
        return clean_text[:15000]
    except Exception as e:
        print(f"  ❌ Playwright 渲染失敗 ({target_url}): {e}")
        return ""

# ==================== 4. AI 語意提取核心 ====================
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
你現在是專業金融與消費語意理解專家。請自主研讀以下【{bank_name}】的網頁文字（已由瀏覽器完整渲染完成）。
請提取此頁面中所有出現的信用卡、權益回饋與需要登錄的活動。

特別要求：所有回饋通路的關聯詞與搜尋關鍵字，請【完全由你自主研判與聯想】，絕不設限：
1. 通路特徵萃取：從條款中找出該回饋所屬的消費領域、官方提及的品牌、適用範圍（全領域通用或限定名單）。
2. 自主語意聯想（searchKeywords）：請站在台灣消費者的角度，自主發想若有人想享受這項權益，會在搜尋框輸入什麼詞彙？
   - 請自主聯想相關的所有中文詞、英文詞、常用口語、生活消費情境、該領域的代表性品牌與店家名稱（以逗號分隔，控制在10~15詞）。
3. 排除條件萃取（excludedKeywords）：自主找出條款中明確說明「不計入回饋」的消費項目或特店。

嚴格輸出純 JSON 格式：
{{
  "cards": [
    {{
      "id": "英數唯一識別碼",
      "bank": "{bank_name}",
      "cardName": "信用卡全名",
      "themeBg": "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)",
      "textColor": "#ffffff",
      "descTag": "特色簡述"
    }}
  ],
  "rules": [
    {{
      "id": "規則唯一識別碼",
      "cardId": "對應卡片id",
      "title": "回饋活動名稱",
      "scope": "ALL 或 SPECIFIC",
      "matchedMerchants": ["條款中提及之店家名單"],
      "searchKeywords": "AI自主聯想之搜尋詞、情境詞、品牌名(以逗號分隔)",
      "baseRate": 1.0,
      "promoRate": 2.0,
      "capAmount": 500,
      "needReg": false,
      "regDeadline": "登錄時間或截止說明",
      "quotaInfo": "名額限制",
      "excludedKeywords": ["明確排除不給回饋項目"]
    }}
  ]
}}

注意事項：
1. 請盡可能列出所有識別到的卡片與規則。
2. 數值（baseRate, promoRate, capAmount）請填數字或 null。
3. 若有「登錄」或「名額限制」，務必將 needReg 設為 true。
4. 輸出必須是合法純 JSON，絕不包含 ```json 或額外開場白。

網頁內容如下：
{content[:12000]}
"""
    raw_response = call_gemini(prompt)
    if not raw_response:
        return None

    try:
        clean = re.sub(r"^```(json)?", "", raw_response.strip(), flags=re.IGNORECASE)
        clean = re.sub(r"```$", "", clean.strip())
        return json.loads(clean.strip())
    except Exception as e:
        print(f"解析 JSON 失敗 ({bank_name}): {e}")
        return None

# ==================== 5. 主程式入口 ====================
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

    # 累計模式：讀取本地既有資料庫，避免爬蟲因偶發網路中斷造成資料丟失
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

    # 啟動 Playwright 無頭瀏覽器
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = context.new_page()

        for portal in FULL_MARKET_PORTALS:
            bank = portal["bank"]
            print(f"\n==============================")
            print(f"開始無頭瀏覽器探索: {bank}...")
            
            content = fetch_dynamic_content(page, portal["url"])
            if not content or len(content) < 150:
                print(f"  - 跳過 {bank}（未能取得有效渲染文字）")
                continue

            print(f"  🌐 成功渲染網頁，文字長度: {len(content)} 字元，交付 AI 分析中...")
            result = parse_bank_data(bank, content)
            if not result:
                print(f"  - 跳過 {bank}（AI 解析無有效輸出）")
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
                    print(f"  + 新卡片入庫: [{bank}] {raw_name}")
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
    print(f"\n[完成] 全市場資料庫更新完畢！")
    print(f"總卡片數: {len(data['cards'])}, 總規則數: {len(data['rules'])}, 需登錄活動數: {total_reg}")

if __name__ == "__main__":
    main()
