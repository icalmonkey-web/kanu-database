import os
import json
import re
from datetime import datetime
import requests
from google import genai

# 1. 初始化 Gemini Client
api_key = os.environ.get("GEMINI_API_KEY", "")
if not api_key:
    raise ValueError("GEMINI_API_KEY is not set!")

client = genai.Client(api_key=api_key)

CANDIDATE_MODELS = [
    "gemini-3.5-flash",
    "gemini-2.5-flash",
    "gemini-1.5-flash"
]

# 2. 全台灣主流發卡銀行「全卡片總覽入口」
FULL_MARKET_PORTALS = [
    # 國泰世華信用卡全產品總覽
    {
        "bank": "國泰世華",
        "url": "https://www.cathaybk.com.tw/cathaybk/personal/product/credit-card/cards/"
    },
    # 玉山銀行全卡片總覽
    {
        "bank": "玉山銀行",
        "url": "https://www.esunbank.com/zh-tw/personal/credit-card/intro/bank-card"
    },
    # 台新銀行信用卡全產品總覽
    {
        "bank": "台新銀行",
        "url": "https://www.taishinbank.com.tw/TSB/personal/credit/intro/overview/"
    },
    # 台北富邦信用卡全列表
    {
        "bank": "台北富邦",
        "url": "https://www.fubon.com/banking/personal/credit_card/all_card/all_card.htm"
    },
    # 中國信託信用卡總覽
    {
        "bank": "中國信託",
        "url": "https://www.ctbcbank.com/content/dam/minisite/long/creditcard/index.html"
    },
    # 聯邦銀行信用卡總覽
    {
        "bank": "聯邦銀行",
        "url": "https://card.ubot.com.tw/eCard/Card/List.aspx"
    },
    # 永豐銀行信用卡總覽
    {
        "bank": "永豐銀行",
        "url": "https://bank.sinopac.com/sinopacBT/personal/credit-card/introduction/list.html"
    },
    # 星展銀行信用卡總覽
    {
        "bank": "星展銀行",
        "url": "https://www.dbs.com.tw/personal-zh/cards/default.page"
    },
    # 滙豐銀行信用卡總覽
    {
        "bank": "滙豐銀行",
        "url": "https://www.hsbc.com.tw/credit-cards/products/"
    },
    # 兆豐銀行信用卡總覽
    {
        "bank": "兆豐銀行",
        "url": "https://www.megabank.com.tw/personal/credit-card/card"
    }
]

def normalize_card_name(name):
    """卡片名稱正規化，清除空格與修飾詞以避免重複"""
    if not name:
        return ""
    n = re.sub(r"\s+", "", name).upper()
    n = re.sub(r"(信用卡|御璽卡|鈦金卡|晶緻卡|無限卡|世界卡|白金卡|卡)$", "", n)
    return n

def fetch_markdown_or_html(target_url):
    """優先透過 Jina Reader 獲取 Markdown，備援直連抓取"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,text/plain"
    }
    # 嘗試 Jina Reader
    try:
        jina_url = f"https://r.jina.ai/{target_url}"
        res = requests.get(jina_url, headers=headers, timeout=25)
        if res.status_code == 200 and len(res.text.strip()) > 300:
            return res.text
    except Exception:
        pass

    # 備援直連
    try:
        res = requests.get(target_url, headers=headers, timeout=20)
        if res.status_code == 200:
            clean_html = re.sub(r"<(script|style).*?</\1>", "", res.text, flags=re.DOTALL | re.IGNORECASE)
            return clean_html[:15000]
    except Exception:
        pass
    return ""

def call_gemini(prompt):
    """支援最新模型順序嘗試"""
    for model_name in CANDIDATE_MODELS:
        try:
            res = client.models.generate_content(model=model_name, contents=prompt)
            if res and res.text:
                return res.text
        except Exception:
            continue
    return None

def parse_full_bank_cards(bank_name, raw_content):
    """指示 AI 提取整家銀行的所有信用卡及權益規則"""
    prompt = f"""
你現在是專業金融與信用卡條款審查專家。請自主研讀以下【{bank_name}】的網頁文字，並提取出所有信用卡、權益回饋與需登錄活動。

請特別依據銀行條款原文，【自主判斷】每項回饋的適用範圍：
1. 若條款表明「全通路/不限通路/所有網路交易/一般消費全涵蓋」：
   - 請將 scope 設定為 "ALL"。
   - 請由你發揮專業知識，自由聯想並展開台灣消費者常用的相關搜尋詞（包含中文、英文、同義詞、常見知名店家），填入 searchKeywords。
2. 若條款表明「限指定特店/精選通路/僅下列商家適用」：
   - 請將 scope 設定為 "SPECIFIC"。
   - matchedMerchants 請嚴格依據內文列出官方特約店家清單（不可自行捏造未列出的商家）。
   - searchKeywords 僅展開這些被列入的特約店家名稱及其常見簡稱或同義詞。

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
      "title": "回饋活動或權益名稱",
      "scope": "ALL 或 SPECIFIC",
      "matchedMerchants": ["此規則適用的特約店家或通路名稱"],
      "searchKeywords": "AI 自主發想展開的搜尋詞(以逗號分隔)",
      "baseRate": 1.0,
      "promoRate": 2.0,
      "capAmount": 500,
      "needReg": false,
      "regDeadline": "登錄時間或截止說明",
      "quotaInfo": "名額限制或門檻說明",
      "excludedKeywords": ["條款中明確排除不給回饋的項目(如超商、全聯、水電公用事業、稅款)"]
    }}
  ]
}}

注意事項：
1. 數值（baseRate, promoRate, capAmount）請填數字或 null。
2. 若有「登錄」或「名額限制」，務必將 needReg 設為 true。
3. 輸出必須是合法純 JSON，絕不包含任何額外開場白或 markdown 語法。

網頁內容如下：
{raw_content[:12000]}
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

def main():
    db_path = "data.json"
    data = {
        "version": "2026.09.20-v0",
        "cards": [],
        "rules": [],
        "commonExclusions": [
            {"keywords": ["全聯", "pxmart"], "message": "全聯福利中心多數銀行排除一般消費回饋。"},
            {"keywords": ["7-11", "全家", "萊爾富", "OK", "超商"], "message": "超商實體刷卡多數排除一般回饋，需搭配指定行動支付或特定卡片。"},
            {"keywords": ["繳稅", "水電", "瓦斯", "學費", "停車費"], "message": "公用事業規費與稅款多數全額排除回饋。"}
        ]
    }

    # 讀取現有資料庫進行累積式儲存
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

    # 逐一爬取全市場各家銀行的卡片總覽目錄
    for portal in FULL_MARKET_PORTALS:
        bank = portal["bank"]
        print(f"\n==============================")
        print(f"開始全量探索: {bank} 信用卡目錄...")
        content = fetch_markdown_or_html(portal["url"])
        if not content:
            print(f"  - 跳過 {bank}（無法取得網頁文字內容）")
            continue

        result = parse_full_bank_cards(bank, content)
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
